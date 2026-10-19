"""Export a bounded DSEC event-frame dataset and portable Colab ZIP."""

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pfe_events.artifacts import write_unicode_json as save_json
from pfe_events.dsec import DSECReader
from pfe_events.detection import CLASS_MAP, CLASS_NAMES, TRUCK_CLASS_MAP, TRUCK_CLASS_NAMES, convert_boxes, labels_to_text
from pfe_events.pilot import load_manifest, unique_file
from pfe_events.representations import polarity_counts, normalized_event_image
from verify_yolo_export import sha256, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"data/processed/dsec_yolo_pilot_v1")
    parser.add_argument("--manifest", type=Path, default=ROOT/"configs/pilot.json")
    parser.add_argument("--normalizer", type=Path, default=ROOT/"outputs/stereo/S01/normalizer.json")
    parser.add_argument("--include-truck", action="store_true", help="Prepare person/car/truck; truck validation may be unavailable")
    args = parser.parse_args()
    class_map = TRUCK_CLASS_MAP if args.include_truck else CLASS_MAP
    class_names = TRUCK_CLASS_NAMES if args.include_truck else CLASS_NAMES
    output = args.output.resolve()
    archive = output.with_suffix(".zip")
    if output.exists() or archive.exists():
        raise FileExistsError("Use a fresh destination; existing exports are preserved")
    source_manifest = load_manifest(args.manifest)
    normalizer = json.loads(args.normalizer.read_text())
    train_names = {e["name"] for e in source_manifest["sequences"] if e["split"] == "train"}
    if normalizer["source_split"] != "train" or normalizer["channels"] != ["positive", "negative", "total"] or not normalizer.get("provenance"):
        raise ValueError("Expected a traceable train-only positive/negative/total normalizer")
    if any(p["sequence"] not in train_names for p in normalizer["provenance"]):
        raise ValueError("Normalizer provenance leaks outside train")
    output.mkdir(parents=True)
    for split in ("train", "val"):
        for kind in ("images", "labels"):
            (output/kind/split).mkdir(parents=True)
    (output/"previews").mkdir()
    frames, sequences, overfit = [], [], []
    for entry in source_manifest["sequences"]:
        if entry["split"] == "test_reserved":
            continue
        name = entry["name"]
        split = "val" if entry["split"] == "validation" else "train"
        label_path = ROOT/source_manifest["labels_root"]/name/"object_detections/left/tracks.npy"
        boxes = np.load(label_path, allow_pickle=False)
        if not {"t", "track_id"}.issubset(boxes.dtype.names or ()) or boxes["t"].dtype.kind not in "ui":
            raise ValueError("Expected official integer-time DSEC labels")
        times = np.unique(boxes["t"]).astype(np.int64)
        folder = ROOT/"data/raw"/name
        seq_frames, totals, preview_best = [], {}, -1
        with DSECReader(unique_file(folder/"events_left", "events.h5")) as reader:
            eligible = times[(times-50_000 >= reader.first_us) & (times <= reader.last_us)]
            if not len(eligible) or len(eligible) > 1000:
                raise ValueError("No eligible windows or pilot exceeds 1000 frames/sequence")
            for i, end in enumerate(eligible):
                end = int(end)
                source_indices = np.flatnonzero(boxes["t"] == end)
                selected = boxes[source_indices]
                labels, kept, stats = convert_boxes(selected, class_map=class_map)
                events = reader.window(end-50_000, end)
                counts = polarity_counts(events)
                image = normalized_event_image(counts, normalizer)
                stem = f"{name}_{end}"
                image_relative, label_relative = f"images/{split}/{stem}.png", f"labels/{split}/{stem}.txt"
                Image.fromarray(image).save(output/image_relative)
                (output/label_relative).write_text(labels_to_text(labels), encoding="utf-8")
                row = {"sequence": name, "group": entry["group"], "split": split,
                       "window_start_us": end-50_000, "window_end_us": end,
                       "image": image_relative, "label": label_relative, "event_count": len(events["x"]),
                       "conversion": stats, "source_rows_kept": source_indices[kept].tolist(),
                       "source_track_ids_kept": selected["track_id"][kept].tolist(),
                       "source_class_ids_kept": selected["class_id"][kept].tolist()}
                frames.append(row)
                seq_frames.append(image_relative)
                for key, count in stats.items():
                    totals[key] = totals.get(key, 0)+count
                pedestrian_count = int((labels[:, 0] == 0).sum())
                if pedestrian_count > preview_best:
                    preview_best = pedestrian_count
                    canvas = Image.fromarray(image)
                    draw = ImageDraw.Draw(canvas)
                    for cls, cx, cy, w, h in labels:
                        x1, y1, x2, y2 = (cx-w/2)*640, (cy-h/2)*480, (cx+w/2)*640, (cy+h/2)*480
                        draw.rectangle((x1, y1, x2, y2), outline=(0, 255, 0), width=2)
                        draw.text((x1, max(0, y1-12)), class_names[int(cls)], fill="white")
                    canvas.save(output/"previews"/f"{name}.png")
                    save_json(output/"previews"/f"{name}.json", {"image": image_relative, "person_boxes": pedestrian_count, "meaning": "official labels after class conversion, NOT predictions"})
                if (i+1) % 50 == 0 or i+1 == len(eligible):
                    print(f"{name}: {i+1}/{len(eligible)}", flush=True)
        if split == "train":
            overfit.extend(seq_frames[i] for i in np.linspace(0, len(seq_frames)-1, 4, dtype=int))
        sequences.append({**entry, "export_split": split, "source_timestamps": len(times), "exported_frames": len(seq_frames),
                          "incomplete_windows_skipped": len(times)-len(seq_frames), "conversion": totals,
                          "source_labels_sha256": sha256(label_path), "source_labels": str(label_path.relative_to(ROOT)),
                          "archives": json.loads((folder/"downloads.json").read_text())})
    (output/"data.yaml").write_text(yaml.safe_dump({"train": "images/train", "val": "images/val", "names": class_names}), encoding="utf-8")
    (output/"overfit.txt").write_text("".join(f"./{p}\n" for p in overfit), encoding="utf-8")
    shutil.copy2(args.normalizer, output/"normalizer.json")
    shutil.copy2(Path(__file__).with_name("verify_yolo_export.py"), output/"verify_yolo_export.py")
    (output/"NOTICE.txt").write_text("Derived from DSEC and DSEC-Detection, University of Zurich/ETH Zurich.\nSources: https://dsec.ifi.uzh.ch/ and https://github.com/uzh-rpg/dsec-det\nDSEC data: CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/\nLocal event accumulations and YOLO label conversion; no RGB camera images.\nExcluded classes become background. Not the official benchmark split.\nClasses: "+", ".join(class_names.values())+"\nMissing validation classes cannot be evaluated.\n", encoding="utf-8")
    code = [Path(__file__), Path(__file__).with_name("verify_yolo_export.py"), *sorted((ROOT/"src/pfe_events").glob("*.py"))]
    manifest = {"experiment": "Y00", "status": "COMPLETE", "window_us": 50_000, "resolution": [640, 480],
                "coordinate_frame": "native event-left", "png_rgb_channels": ["positive", "negative", "total"],
                "class_mapping": class_map, "names": class_names, "other_classes": "excluded labels become background; rider is not person",
                "allowed_missing_validation_classes": [2] if args.include_truck else [],
                "box_policy": "clip to sensor; reject invalid/empty; remove exact rounded duplicates; no minimum size",
                "date_policy": "all distinct official annotation timestamps with full left window; no synthesized unlabelled negatives",
                "normalizer_sha256": sha256(args.normalizer), "source_manifest": source_manifest,
                "code_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in code}, "sequences": sequences, "frames": frames}
    save_json(output/"manifest.json", manifest)
    save_json(output/"checksums.json", {p.relative_to(output).as_posix(): sha256(p) for p in sorted(output.rglob("*")) if p.is_file()})
    verification = verify(output)
    # Archive only after the complete payload has passed verification.
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                z.write(path, (Path(output.name)/path.relative_to(output)).as_posix())
    report = {"experiment": "Y00_TRUCK" if args.include_truck else "Y00", "status": "EXPORTED_AND_VERIFIED", "verification": verification,
              "names": class_names,
              "sequences": sequences, "normalizer_sha256": sha256(args.normalizer),
              "archive": str(archive.relative_to(ROOT)), "archive_bytes": archive.stat().st_size,
              "archive_sha256": sha256(archive), "manifest_sha256": sha256(output/"manifest.json"),
              "model_training": "NOT RUN"}
    report_name = "Y00_truck_export.json" if args.include_truck else "Y00_export.json"
    save_json(ROOT/"outputs/reports"/report_name, report)
    print(json.dumps({k: v for k, v in report.items() if k != "sequences"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
