"""Portable CPU verification; copied into the Colab bundle, no project imports."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def contained(root, relative):
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Path outside dataset: {relative}")
    return target


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "COMPLETE":
        raise ValueError("Incomplete export")
    class_names = {int(k): v for k, v in manifest["names"].items()}
    nc = len(class_names)
    if sorted(class_names) != list(range(nc)) or nc not in (2, 3):
        raise ValueError("Expected contiguous two/three-class pilot names")
    expected_names = {0: 'person', 1: 'car', **({2: 'truck'} if nc == 3 else {})}
    expected_map = {0: 0, 2: 1, **({4: 2} if nc == 3 else {})}
    if (class_names != expected_names
            or {int(k): v for k, v in manifest['class_mapping'].items()} != expected_map):
        raise ValueError("Unexpected DSEC/YOLO class mapping")
    data = yaml.safe_load((root/'data.yaml').read_text())
    if data['names'] != class_names or data['train'] != 'images/train' or data['val'] != 'images/val':
        raise ValueError("YAML and manifest disagree")
    allowed_missing = manifest.get('allowed_missing_validation_classes', [])
    if allowed_missing not in ([], [2]) or (allowed_missing and nc != 3):
        raise ValueError("Only truck may be explicitly unevaluated in this pilot")
    checksums = json.loads((root / "checksums.json").read_text())
    for relative, expected in checksums.items():
        if sha256(contained(root, relative)) != expected:
            raise ValueError(f"Hash mismatch: {relative}")
    groups, names, content_splits = {}, set(), {}
    counts = {split: {"images": 0, "boxes": [0]*nc, "negative_images": 0} for split in ('train', 'val')}
    for frame in manifest["frames"]:
        split, group, relative = frame["split"], frame["group"], frame["image"]
        if split not in counts or relative in names or group != frame["sequence"].rsplit("_", 1)[0]:
            raise ValueError("Unknown split, duplicate image, or invalid group")
        if group in groups and groups[group] != split:
            raise ValueError("Drive group appears in both splits")
        groups[group] = split
        names.add(relative)
        if not relative.startswith(f"images/{split}/") or not frame["label"].startswith(f"labels/{split}/"):
            raise ValueError("Image/label split mismatch")
        for key in ("image", "label"):
            if frame[key] not in checksums:
                raise ValueError("Unhashed payload")
        image_path = contained(root, relative)
        with Image.open(image_path) as pil:
            if pil.mode != "RGB" or pil.size != (640, 480):
                raise ValueError("Unexpected PNG mode or size")
            rgb = np.asarray(pil)
        bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if bgr is None or not np.array_equal(rgb, bgr[..., ::-1]):
            raise ValueError("Pillow/OpenCV channel round-trip mismatch")
        # Byte-identical imagery across splits would undermine independence.
        image_hash = checksums[relative]
        if image_hash in content_splits and content_splits[image_hash] != split:
            raise ValueError("Identical image in train and validation")
        content_splits[image_hash] = split
        text = contained(root, frame["label"]).read_text().strip()
        labels = np.array([[float(v) for v in line.split()] for line in text.splitlines()], dtype=float).reshape(-1, 5)
        if not np.isfinite(labels).all() or not np.isin(labels[:, 0], range(nc)).all():
            raise ValueError("Nonfinite or unknown YOLO label")
        xywh = labels[:, 1:]
        if np.any(xywh < 0) or np.any(xywh > 1) or np.any(xywh[:, 2:] <= 0):
            raise ValueError("Invalid normalized label")
        if np.any(xywh[:, :2]-xywh[:, 2:]/2 < -1e-8) or np.any(xywh[:, :2]+xywh[:, 2:]/2 > 1+1e-8):
            raise ValueError("Box extends beyond image")
        if len(np.unique(labels, axis=0)) != len(labels) or len(labels) != frame["conversion"]["kept"]:
            raise ValueError("Duplicate label or count mismatch")
        if frame["window_end_us"]-frame["window_start_us"] != manifest["window_us"]:
            raise ValueError("Window mismatch")
        counts[split]["images"] += 1
        counts[split]["negative_images"] += int(not len(labels))
        for i in range(nc):
            counts[split]["boxes"][i] += int((labels[:, 0] == i).sum())
    actual_images = {p.relative_to(root).as_posix() for p in (root/"images").rglob("*.png")}
    actual_labels = {p.relative_to(root).as_posix() for p in (root/"labels").rglob("*.txt")}
    if names != actual_images or {f["label"] for f in manifest["frames"]} != actual_labels:
        raise ValueError("Unlisted/missing image or label")
    for split, info in counts.items():
        if not info["images"] or any(not count and (split == 'train' or cls not in allowed_missing)
                                     for cls, count in enumerate(info['boxes'])):
            raise ValueError(f"Missing pilot class/split: {split}")
    overfit = (root/"overfit.txt").read_text().splitlines()
    if len(overfit) != 8 or len(set(overfit)) != 8 or any(p.removeprefix("./") not in names or not p.startswith("./images/train/") for p in overfit):
        raise ValueError("Overfit subset must contain eight unique train images")
    overfit_classes = set()
    for relative in overfit:
        label = root / relative.removeprefix('./').replace('images/', 'labels/')
        overfit_classes.update(int(line.split()[0]) for line in label.with_suffix('.txt').read_text().splitlines())
    if overfit_classes != set(range(nc)):
        raise ValueError("Overfit subset must cover every exported class")
    return {"status": "PASS", "counts": counts, "hashed_files": len(checksums),
            "channel_check": "All PNGs: Pillow RGB == reversed OpenCV BGR; actual Ultralytics tensor check deferred to notebook",
            "group_partition": groups, "overfit_images": len(overfit), "model_training": "NOT RUN",
            "validation_missing_classes": [class_names[i] for i, count in enumerate(counts['val']['boxes']) if not count]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify(args.dataset)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
