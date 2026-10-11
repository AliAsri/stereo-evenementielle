"""Inspect real stereo events and GT geometry; this is NOT model inference."""

import argparse
import importlib.metadata
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pfe_events.dsec import DSECReader, load_rectify_map, rectify_events
from pfe_events.geometry import audit_calibration, decode_dsec_disparity, reproject_q
from pfe_events.representations import polarity_counts, render_counts


def unique_file(folder, pattern):
    paths = list(folder.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"Expected one {pattern} in {folder}, found {len(paths)}")
    return paths[0]


def inspect(folder, output, window_us, full_audit):
    if window_us <= 0:
        raise ValueError("Positive window duration required")
    output.mkdir(parents=True, exist_ok=True)
    calibration = audit_calibration(unique_file(folder / "calibration", "cam_to_cam.yaml"))
    width, height = calibration["resolution"]
    timestamps = np.atleast_1d(np.loadtxt(unique_file(folder, "*_disparity_timestamps.txt"), dtype=np.int64))
    gt_paths = sorted((folder / "disparity_event").rglob("*.png"))
    if len(gt_paths) != len(timestamps) or not len(gt_paths):
        raise ValueError("Reference PNG count must match disparity timestamps")
    if np.any(timestamps[1:] <= timestamps[:-1]):
        raise ValueError("Reference timestamps must increase strictly")
    report = {"purpose": "REAL DATA INSPECTION; GT IS NOT A PREDICTION", "sequence": folder.name, "python": platform.python_version(), "platform": platform.platform(), "calibration": calibration, "versions": {name: importlib.metadata.version(name) for name in ("numpy", "h5py", "hdf5plugin", "Pillow", "PyYAML")}, "model_inference": "NOT RUN"}
    panels = []
    with DSECReader(unique_file(folder / "events_left", "events.h5"), width, height) as left, DSECReader(unique_file(folder / "events_right", "events.h5"), width, height) as right:
        common_start = max(left.first_us, right.first_us)
        common_end = min(left.last_us, right.last_us)
        indices = np.flatnonzero((timestamps - window_us >= common_start) & (timestamps <= common_end))
        if not len(indices):
            raise ValueError("No complete causal window within the stereo overlap")
        index = int(indices[len(indices)//2])
        end = int(timestamps[index])
        start = end - window_us
        report.update({"window_start_us": start, "window_end_us_exclusive": end, "window_us": window_us, "gt_index": index, "gt_file": str(gt_paths[index].relative_to(ROOT)), "overlap_us": [common_start, common_end]})
        for side, reader in (("left", left), ("right", right)):
            audit = reader.audit_timestamps() if full_audit else {"status": "WINDOW_ONLY; full order NOT CHECKED"}
            begin = time.perf_counter()
            events = reader.window(start, end)
            read_ms = (time.perf_counter() - begin)*1000
            counts = polarity_counts(events, width, height)
            mapping = load_rectify_map(unique_file(folder / f"events_{side}", "rectify_map*.h5"), width, height)
            rectified, dropped = rectify_events(events, mapping, width, height)
            rect_counts = polarity_counts(rectified, width, height)
            stats = {"file_events": reader.count, "t_offset_us": reader.offset_us, "file_first_us": reader.first_us, "file_last_us": reader.last_us, "window_events": len(events["x"]), "window_rate_events_s": len(events["x"])*1e6/window_us, "positive_events": int((events["p"] == 1).sum()), "rectification_dropped_events": dropped, "active_native_pixels": int((counts.sum(axis=0) > 0).sum()), "single_window_read_ms_not_benchmark": read_ms, "timestamp_audit": audit}
            if int(counts.sum()) != len(events["x"]) or int(rect_counts.sum()) + dropped != len(events["x"]):
                raise ValueError("Count conservation failure")
            report[side] = stats
            native = Image.fromarray(render_counts(counts))
            rect = Image.fromarray(render_counts(rect_counts))
            native.save(output / f"{side}_native.png")
            rect.save(output / f"{side}_rectified.png")
            panels.extend([(f"{side.upper()} NATIVE | {len(events['x']):,} events", native), (f"{side.upper()} RECTIFIED | same time window", rect)])
    encoded = np.asarray(Image.open(gt_paths[index]))
    disparity, valid = decode_dsec_disparity(encoded)
    if disparity.shape != (height, width):
        raise ValueError("GT and calibration resolutions differ")
    yy, xx = np.indices(disparity.shape)
    xyz = reproject_q(xx, yy, disparity, calibration["q"])
    finite = np.isfinite(xyz).all(axis=-1)
    if not finite.any():
        raise ValueError("No valid reference depths")
    report["gt_diagnostic"] = {"valid_pixels": int(valid.sum()), "coverage": float(valid.mean()), "depth_percentiles_m": np.percentile(xyz[..., 2][finite], [5, 50, 95]).tolist(), "meaning": "Reference visible-scene surface depth, NOT object estimates, NOT predicted depth"}
    label_root = folder / "detection_labels"
    labels = [p for p in label_root.rglob("tracks.npy") if folder.name in p.relative_to(label_root).parts]
    if len(labels) > 1:
        raise ValueError("Ambiguous object labels")
    if labels:
        boxes = np.load(labels[0], allow_pickle=False)
        names = ("pedestrian", "rider", "car", "bus", "truck", "bicycle", "motorcycle", "train")
        required = {"t", "x", "y", "w", "h", "class_id"}
        if not required.issubset(boxes.dtype.names or ()):
            raise ValueError("Unexpected label schema")
        if not np.isin(boxes["class_id"], np.arange(len(names))).all():
            raise ValueError("Unknown detection class id")
        report["labels"] = {"path": str(labels[0].relative_to(ROOT)), "sequence_boxes_by_class": {name: int((boxes["class_id"] == i).sum()) for i, name in enumerate(names)}, "boxes_at_exact_gt_time": int((boxes["t"] == end).sum()), "alignment": "Native view; overlay inspection only, NOT detection evaluation"}
        annotated = panels[0][1].copy()
        draw = ImageDraw.Draw(annotated)
        for box in boxes[boxes["t"] == end]:
            x, y, w, h = [float(box[key]) for key in ("x", "y", "w", "h")]
            draw.rectangle((x, y, x+w, y+h), outline=(0, 120, 0), width=2)
            draw.text((x, max(0, y-12)), names[int(box["class_id"])], fill=(0, 90, 0))
        annotated.save(output / "left_official_labels.png")
        panels.append(("OFFICIAL LABELS | native left | NOT YOLO", annotated))
    else:
        report["labels"] = {"status": "NOT AVAILABLE in downloaded sample"}
    gray = np.zeros_like(encoded, dtype=np.uint8)
    display_max = float(np.percentile(disparity[valid], 95))
    gray[valid] = np.clip(disparity[valid] / display_max * 255, 0, 255).astype(np.uint8)
    panels.append(("GROUND TRUTH DISPARITY | NOT A PREDICTION", Image.fromarray(gray).convert("RGB")))
    rows = (len(panels)+1)//2
    sheet = Image.new("RGB", (width*2, (height+32)*rows+50), "#142031")
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 10), f"DSEC {folder.name} | REAL DATA AUDIT | [{start}, {end}) us | {window_us/1000:g} ms", fill="white")
    for i, (title, panel) in enumerate(panels):
        x, y = (i % 2)*width, 50+(i//2)*(height+32)
        draw.text((x+8, y+8), title, fill="white")
        sheet.paste(panel, (x, y+32))
    sheet.save(output / "inspection.png")
    (output / "inspection.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-us", type=int, default=50_000)
    parser.add_argument("--full-timestamp-audit", action="store_true")
    args = parser.parse_args()
    inspect(ROOT / "data/raw/zurich_city_04_e", ROOT / "outputs/inspection", args.window_us, args.full_timestamp_audit)
