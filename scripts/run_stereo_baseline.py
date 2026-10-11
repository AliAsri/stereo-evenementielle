"""Reproducible local SGBM pilot: train-only codec, predicted depth, honest coverage."""

import argparse
import importlib.metadata
import json
import platform
import sys
import time
from contextlib import ExitStack
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pfe_events.artifacts import sha256_file as digest, write_unicode_json
from pfe_events.dsec import DSECReader, load_rectify_map
from pfe_events.geometry import audit_calibration, decode_dsec_disparity, reproject_q
from pfe_events.pilot import load_manifest, unique_file, reference_frames, sample_indices
from pfe_events.representations import polarity_counts, rectified_counts, fit_log_normalizer, normalized_event_image
from pfe_events.stereo import StereoConfig, predict_stereo, disparity_metrics, aggregate_metrics

CLASSES = ("pedestrian", "rider", "car", "bus", "truck", "bicycle", "motorcycle", "train")


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    write_unicode_json(path, data)


def open_pair(stack, folder):
    calibration = audit_calibration(unique_file(folder / "calibration", "cam_to_cam.yaml"))
    w, h = calibration["resolution"]
    readers, maps = [], []
    for side in ("left", "right"):
        readers.append(stack.enter_context(DSECReader(unique_file(folder/f"events_{side}", "events.h5"), w, h)))
        maps.append(load_rectify_map(unique_file(folder/f"events_{side}", "rectify_map*.h5"), w, h))
    return readers, maps, calibration


def training_frames(manifest, window_us, provenance):
    for entry in manifest["sequences"]:
        if entry["split"] != "train":
            continue
        folder = ROOT / "data/raw" / entry["name"]
        timestamps, _ = reference_frames(folder)
        with ExitStack() as stack:
            readers, maps, calibration = open_pair(stack, folder)
            w, h = calibration["resolution"]
            indices = sample_indices(timestamps, *readers, window_us, 4)
            provenance.append({"sequence": entry["name"], "gt_indices": indices.tolist(),
                               "window_end_us": timestamps[indices].tolist(), "views": "left and right; native and bilinear rectified"})
            for index in indices:
                end = int(timestamps[index])
                for reader, mapping in zip(readers, maps):
                    events = reader.window(end-window_us, end)
                    yield polarity_counts(events, w, h)
                    yield rectified_counts(events, mapping, w, h)[0]


def color_disparity(disparity, maximum=96):
    valid = np.isfinite(disparity) & (disparity > 0)
    encoded = np.rint(np.clip(np.nan_to_num(disparity)/maximum, 0, 1)*255).astype(np.uint8)
    rgb = cv2.cvtColor(cv2.applyColorMap(encoded, cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB)
    rgb[~valid] = (18, 24, 34)
    return Image.fromarray(rgb)


def make_sheet(left, gt, prediction, sequence, end, metrics, max_disp):
    h, w = gt.shape
    known, valid = np.isfinite(gt), np.isfinite(prediction)
    error = np.zeros((h, w, 3), dtype=np.uint8)
    error[known & ~valid] = (200, 30, 180)
    good = known & valid & (np.abs(gt-prediction) <= 3)
    bad = known & valid & ~good
    error[good], error[bad] = (35, 180, 90), (245, 65, 35)
    panels = [("RECTIFIED EVENTS | total log channel", Image.fromarray(left).convert("RGB")),
              (f"GROUND TRUTH | fixed scale 0..{max_disp} px", color_disparity(gt, max_disp)),
              (f"SGBM PREDICTION | fixed scale 0..{max_disp} px", color_disparity(prediction, max_disp)),
              ("GT: green <=3px / orange >3px / magenta missing / black no GT", Image.fromarray(error))]
    sheet = Image.new("RGB", (w*2, (h+34)*2+60), "#142031")
    draw = ImageDraw.Draw(sheet)
    epe = metrics["epe_px"]
    draw.text((12, 8), f"{sequence} | t={end} us | REAL CPU PREDICTION | S01", fill="white")
    draw.text((12, 28), f"EPE={epe:.3f}px | GT coverage={metrics['gt_coverage']:.1%} | conditional errors, all-GT coverage" if epe is not None else "No valid estimates on GT", fill="white")
    for i, (title, panel) in enumerate(panels):
        x, y = (i % 2)*w, 60+(i//2)*(h+34)
        draw.text((x+8, y+10), title, fill="white")
        sheet.paste(panel, (x, y+34))
    return sheet


def evaluate_sequence(entry, manifest, normalizer, config, args, output):
    name = entry["name"]
    folder = ROOT / "data/raw" / name
    destination = output / name
    destination.mkdir()
    timestamps, paths = reference_frames(folder)
    label_path = ROOT / manifest["labels_root"] / name / "object_detections/left/tracks.npy"
    boxes = np.load(label_path, allow_pickle=False)
    if not {"t", "x", "y", "w", "h", "class_id"}.issubset(boxes.dtype.names or ()) or not np.isin(boxes["class_id"], range(8)).all():
        raise ValueError("Invalid official label schema")
    rows, worst, median_sheet, best_pedestrians = [], None, None, -1
    with ExitStack() as stack:
        readers, maps, calibration = open_pair(stack, folder)
        w, h = calibration["resolution"]
        indices = sample_indices(timestamps, *readers, args.window_us, args.frames)
        audits = [reader.audit_timestamps() if args.full_timestamp_audit else
                  {"status": "WINDOW_ONLY; full order NOT CHECKED"} for reader in readers]
        for position, index in enumerate(indices):
            begin = time.perf_counter()
            end = int(timestamps[index])
            events = [reader.window(end-args.window_us, end) for reader in readers]
            after_read = time.perf_counter()
            rectified = [rectified_counts(e, m, w, h) for e, m in zip(events, maps)]
            images = [normalized_event_image(c, normalizer) for c, _ in rectified]
            after_repr = time.perf_counter()
            prediction, valid, raw, mask_stats = predict_stereo(images[0][..., 2], images[1][..., 2], config)
            after_stereo = time.perf_counter()
            yy, xx = np.indices(prediction.shape)
            # Only the PREDICTED disparity enters this depth branch.
            xyz = reproject_q(xx, yy, prediction, calibration["q"])
            depth = xyz[..., 2].astype(np.float32)
            after_depth = time.perf_counter()
            gt, known = decode_dsec_disparity(np.asarray(Image.open(paths[index])))
            metrics = disparity_metrics(prediction, gt)
            in_search = known & (gt < config.num_disparities)
            gt_depth = reproject_q(xx, yy, gt, calibration["q"])[..., 2]
            both = np.isfinite(depth) & np.isfinite(gt_depth)
            depth_error = np.abs(depth[both]-gt_depth[both])
            selected_boxes = boxes[boxes["t"] == end]
            row = {"gt_index": int(index), "gt_file": str(paths[index].relative_to(ROOT)),
                   "window_start_us": end-args.window_us, "window_end_us_exclusive": end,
                   "events_left_right": [len(e["x"]) for e in events],
                   "rectification_rejected_left_right": [d for _, d in rectified],
                   "boxes_at_exact_timestamp": len(selected_boxes),
                   "pedestrians_at_exact_timestamp": int((selected_boxes["class_id"] == 0).sum()),
                   "mask": mask_stats, "metrics": metrics,
                   "gt_outside_search_pixels": int((known & ~in_search).sum()),
                   "in_search_metrics": disparity_metrics(prediction, np.where(in_search, gt, np.nan)),
                   "depth_on_intersection": {"pixels": int(both.sum()), "sum_abs_error_m": float(depth_error.sum()),
                                              "mae_m": float(depth_error.mean()) if depth_error.size else None},
                   "timing_ms": {"read": (after_read-begin)*1000, "representation": (after_repr-after_read)*1000,
                                 "stereo_two_directions": (after_stereo-after_repr)*1000,
                                 "reproject": (after_depth-after_stereo)*1000,
                                 "read_to_depth_excludes_evaluation_io": (after_depth-begin)*1000}}
            rows.append(row)
            np.savez_compressed(destination / f"frame_{int(index):06d}.npz", disparity_px=prediction,
                                valid=valid, raw_sgbm_q4=raw, depth_m=depth, q=np.array(calibration["q"]),
                                window_end_us=np.int64(end), window_us=np.int64(args.window_us))
            score = metrics["bad3_or_missing_fraction"]
            if worst is None or (score is not None and score > worst[0]):
                worst = (score, row, make_sheet(images[0][..., 2], gt, prediction, name, end, metrics, config.num_disparities))
            if position == len(indices)//2:
                median_sheet = make_sheet(images[0][..., 2], gt, prediction, name, end, metrics, config.num_disparities)
            pedestrian_count = row["pedestrians_at_exact_timestamp"]
            if pedestrian_count > best_pedestrians:
                best_pedestrians = pedestrian_count
                native = normalized_event_image(polarity_counts(events[0], w, h), normalizer)
                Image.fromarray(native).save(destination / "native_log_channels.png")
                annotated = Image.fromarray(native)
                draw = ImageDraw.Draw(annotated)
                for box in selected_boxes:
                    x, y, bw, bh = [float(box[k]) for k in ("x", "y", "w", "h")]
                    draw.rectangle((x, y, x+bw, y+bh), outline=(0, 255, 0), width=2)
                    draw.text((x, max(0, y-12)), CLASSES[int(box["class_id"])], fill="white")
                annotated.save(destination / "native_official_labels.png")
                save_json(destination / "native_example.json", {"gt_index": int(index), "end_us": end,
                          "pedestrians": pedestrian_count, "boxes": len(selected_boxes),
                          "selection": "largest pedestrian count among sampled frames; illustration only, NOT YOLO",
                          "channels": normalizer["channels"], "coordinates": "native event-left"})
            print(f"{name} {position+1}/{len(indices)} EPE={metrics['epe_px']} coverage={metrics['gt_coverage']:.3f}", flush=True)
        median_sheet.save(destination / "example.png")
        worst[2].save(destination / "worst_coverage_or_error.png")
    timing = {key: {"median": float(np.median([r["timing_ms"][key] for r in rows])),
                    "p95": float(np.percentile([r["timing_ms"][key] for r in rows], 95))} for key in rows[0]["timing_ms"]}
    depth_count = sum(r["depth_on_intersection"]["pixels"] for r in rows)
    report = {"sequence": name, "split": entry["split"], "group": entry["group"], "frames": len(rows),
              "calibration": calibration, "timestamp_audits": audits,
              "labels_by_class_instances_not_unique_objects": {c: int((boxes["class_id"] == i).sum()) for i, c in enumerate(CLASSES)},
              "label_file": str(label_path.relative_to(ROOT)), "label_sha256": digest(label_path),
              "archive_provenance": json.loads((folder / "downloads.json").read_text()),
              "metrics": aggregate_metrics([r["metrics"] for r in rows]),
              "in_search_metrics": aggregate_metrics([r["in_search_metrics"] for r in rows]),
              "gt_outside_search_pixels": sum(r["gt_outside_search_pixels"] for r in rows),
              "depth_mae_m_on_intersection": sum(r["depth_on_intersection"]["sum_abs_error_m"] for r in rows)/depth_count if depth_count else None,
              "timing_ms_including_first_frame_not_benchmark": timing,
              "worst_frame_gt_index": worst[1]["gt_index"], "rows": rows}
    save_json(destination / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "configs/pilot.json")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/stereo/S01")
    parser.add_argument("--frames", type=int, default=20, help="Uniformly spaced GT times per acquired sequence")
    parser.add_argument("--window-us", type=int, default=50_000)
    parser.add_argument("--full-timestamp-audit", action="store_true")
    args = parser.parse_args()
    if args.frames <= 0 or args.window_us <= 0:
        parser.error("Positive frames and window-us required")
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("Choose a fresh output directory to preserve experiment evidence")
    manifest = load_manifest(args.manifest)
    # Fail early on unavailable acquired sequences; test_reserved is never opened.
    entries = [e for e in manifest["sequences"] if e["split"] != "test_reserved"]
    for entry in entries:
        reference_frames(ROOT / "data/raw" / entry["name"])
    cv2.setNumThreads(1)
    config = StereoConfig()
    output.mkdir(parents=True)
    provenance = []
    print("Fitting frozen normalization from TRAIN only", flush=True)
    normalizer = fit_log_normalizer(training_frames(manifest, args.window_us, provenance), source_split="train")
    normalizer["provenance"] = provenance
    save_json(output / "normalizer.json", normalizer)
    # Saved before any validation data are evaluated.
    save_json(output / "config.json", {"stereo": config.to_dict(), "window_us": args.window_us,
                                      "frames_per_sequence": args.frames, "manifest": manifest})
    reports = [evaluate_sequence(entry, manifest, normalizer, config, args, output) for entry in entries]
    code_files = [Path(__file__), *sorted((ROOT/"src/pfe_events").glob("*.py")), args.manifest, ROOT/"requirements.txt"]
    summary = {"experiment": "S01", "status": "RUN", "kind": "real event stereo CPU baseline; no learned model",
               "python": platform.python_version(), "platform": platform.platform(),
               "versions": {p: importlib.metadata.version(p) for p in ("numpy", "h5py", "hdf5plugin", "Pillow", "PyYAML", "opencv-python-headless")},
               "code_sha256": {str(p.resolve().relative_to(ROOT)): digest(p) for p in code_files},
               "config": config.to_dict(), "window_us": args.window_us, "normalizer": normalizer,
               "sequences": [{k: v for k, v in r.items() if k != "rows"} for r in reports],
               "limits": ["20 fixed samples per sequence by default, not full benchmark", "04_b and 04_e are TRAIN/debug",
                          "thun_00_a is local validation only, small and unrepresentative", "test_reserved never opened",
                          "EPE/depth MAE conditional on valid prediction and GT; coverage denominator all GT",
                          "Sparse GT cannot assess predictions outside GT", "CPU timings include first frame, exclude evaluation/export; not real-time FPS",
                          "YOLO, deep stereo, object XYZ, movement: NOT RUN"]}
    save_json(output / "summary.json", summary)
    print(f"Saved complete experiment: {output}", flush=True)


if __name__ == "__main__":
    main()
