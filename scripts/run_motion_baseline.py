"""M01: CPU activity proposals and replay cost on fixed DSEC segments.

No YOLO, disparity GT, object labels, motion GT or model weights are consumed.
"""

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from pfe_events.artifacts import sha256_file as digest
from pfe_events.reporting import activity_distribution as distribution
from pfe_events.dsec import DSECReader
from pfe_events.dsec_indexed import IndexedDSECReader
from pfe_events.motion import ActivityDetector
from pfe_events.pilot import load_manifest, unique_file


def panel(result, sequence, read_ms, process_ms, relative_ms):
    w, h = 640, 480
    frame = Image.new("RGB", (1280, 584), "#101925")
    draw = ImageDraw.Draw(frame)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    draw.text((12, 8), f"M01 | {sequence} | replay +{relative_ms:.0f} ms | 10 ms windows", font=font, fill="white")
    draw.text((12, 33), "EVENT ACTIVITY: camera motion / illumination may contribute; no object identity", font=font, fill="#ffd166")
    pixels = np.zeros(w*h, dtype=np.uint8)
    pixels[result["occupied_pixels"]] = 225
    frame.paste(Image.fromarray(pixels.reshape(h, w)).convert("RGB"), (0, 76))
    # One fixed heat scale for the whole run: 0..100 events/(s*pixel).
    values = np.uint8(np.clip(result["rate"]/100, 0, 1)*255)
    heat = cv2.cvtColor(cv2.applyColorMap(values, cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB)
    frame.paste(Image.fromarray(heat).resize((w, h), Image.Resampling.NEAREST), (640, 76))
    draw.text((12, 56), "Native event support + persistent activity regions", font=font, fill="white")
    draw.text((652, 56), "Grid rate: fixed scale 0..100 events/(s*pixel)", font=font, fill="white")
    for region in result["regions"]:
        x1, y1, x2, y2 = region["xyxy"]
        draw.rectangle((x1, y1+76, x2-1, y2+75), outline="#ffb000", width=2)
    draw.text((12, 560), f"Read {read_ms:.2f} ms | activity {process_ms:.2f} ms | zones {len(result['regions'])} | display 20 Hz", font=font, fill="white")
    return frame


def run_case(entry, window_us, output, duration_us, warmup_us, reader_class=DSECReader):
    source = unique_file(ROOT/"data/raw"/entry["name"]/"events_left", "events.h5")
    case_dir = output/entry["name"]/f"{window_us//1000}ms"
    case_dir.mkdir(parents=True)
    detector = ActivityDetector()
    rows, grids, masks, pictures = [], [], [], []
    event_hash = hashlib.sha256()
    with reader_class(source) as reader:
        # Fixed centered segment, chosen without looking at detections or labels.
        start = (reader.first_us+reader.last_us-duration_us)//2 - warmup_us
        stop = start+warmup_us+duration_us
        if start < reader.first_us or stop > reader.last_us:
            raise ValueError("Sequence shorter than requested benchmark segment")
        finish_ms = 0.0
        for begin in range(start, stop, window_us):
            end = begin+window_us
            before = time.perf_counter_ns()
            events = reader.window(begin, end)
            loaded = time.perf_counter_ns()
            result = detector.update(events, begin, end)
            done = time.perf_counter_ns()
            read_ms, process_ms = (loaded-before)/1e6, (done-loaded)/1e6
            total_ms = read_ms+process_ms
            relative_end_ms = (end-start)/1000
            finish_ms = max(finish_ms, relative_end_ms)+total_ms
            row = {"end_us_exclusive": end, "events": result["events"], "read_ms": read_ms,
                   "activity_ms": process_ms, "read_activity_ms": total_ms,
                   "simulated_completion_delay_after_window_end_ms": finish_ms-relative_end_ms,
                   "active_fraction": result["active_fraction"], "regions": len(result["regions"]),
                   "widespread_activity": int(result["widespread_activity"]),
                   "warmup": int(end <= start+warmup_us)}
            rows.append(row)
            grids.append(result["rate"].astype(np.float32))
            masks.append(result["active"])
            for key in ("x", "y", "t_us", "p"):
                event_hash.update(events[key].tobytes())
            if window_us == 10_000 and end > start+warmup_us and (end-start-warmup_us) % 50_000 == 0:
                pictures.append(panel(result, entry["name"], read_ms, process_ms, (end-start-warmup_us)/1000))
        metadata = {"path": source.relative_to(ROOT).as_posix(), "bytes": source.stat().st_size,
                    "t_offset_us": reader.offset_us, "file_time_range_us": [reader.first_us, reader.last_us],
                    "reader": reader_class.__name__, "fallback_windows": getattr(reader, "fallback_windows", None)}
    with (case_dir/"windows.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    np.savez_compressed(case_dir/"activity.npz", end_us=np.array([r["end_us_exclusive"] for r in rows]),
                        rate=np.asarray(grids), active=np.asarray(masks))
    if pictures:
        pictures[len(pictures)//2].save(case_dir/"example.png")
        pictures[0].save(case_dir/"replay.gif", save_all=True, append_images=pictures[1:], duration=50, loop=0)
    measured = [r for r in rows if not r["warmup"]]
    summary = {"sequence": entry["name"], "split": entry["split"], "view": "left native",
               "window_us": window_us, "step_us": window_us, "warmup_us": warmup_us,
               "segment_start_us": start, "segment_end_us_exclusive": stop,
               "selection": "centered two-second segment plus preceding warmup; no label/metric selection",
               "source": metadata, "window_arrays_sha256": event_hash.hexdigest(),
               "parameters": detector.parameters(), "measured_windows": len(measured),
               "measured_events": sum(r["events"] for r in measured),
               "timing_ms": {key: distribution([r[key] for r in measured]) for key in
                             ("read_ms", "activity_ms", "read_activity_ms", "simulated_completion_delay_after_window_end_ms")},
               "fraction_compute_over_step": float(np.mean([r["read_activity_ms"] > window_us/1000 for r in measured])),
               "fraction_windows_with_regions": float(np.mean([r["regions"] > 0 for r in measured])),
               "mean_active_fraction": float(np.mean([r["active_fraction"] for r in measured])),
               "fraction_widespread_activity": float(np.mean([r["widespread_activity"] for r in measured])),
               "real_motion_onset_delay_ms": None, "false_alerts_per_second": None,
               "accuracy_status": "NOT MEASURED: no motion-onset or independent-motion annotations"}
    (case_dir/"summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"outputs/motion/M01")
    parser.add_argument("--reader", choices=("reference", "indexed"), default="reference")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a fresh output folder; existing experiment preserved")
    manifest = load_manifest(ROOT/"configs/pilot.json")
    entries = [e for e in manifest["sequences"] if e["name"] in ("zurich_city_04_b", "thun_00_a")]
    if len(entries) != 2 or any(e["split"] == "test_reserved" for e in entries):
        raise ValueError("Expected train/debug and validation, never reserved test")
    cv2.setNumThreads(1)
    args.output.mkdir(parents=True)
    report = {"experiment": "M01" if args.reader == "reference" else "M02_INDEXED_REPLAY", "reader": args.reader,
              "status": "RUNNING", "utc": datetime.now(timezone.utc).isoformat(),
              "purpose": "Causal event activity proposals and CPU replay cost; NOT independent object motion",
              "python": platform.python_version(), "platform": platform.platform(),
              "versions": {k: importlib.metadata.version(k) for k in ("numpy", "opencv-python-headless", "h5py", "Pillow")},
              "code_sha256": {p: digest(ROOT/p) for p in ['src/pfe_events/artifacts.py','src/pfe_events/reporting.py',"scripts/run_motion_baseline.py", "src/pfe_events/motion.py", "src/pfe_events/dsec.py", "src/pfe_events/dsec_indexed.py", "configs/pilot.json"]},
              "timing_protocol": "Sequential uncapped disk replay, 200 ms dataset warmup; read includes timestamp lookup and validation; activity includes proposals; rendering/hashing/writes excluded. Cache/order effects remain. Queue delays are a simulation at 1x, not observed live latency.",
              "cases": []}
    target = args.output/"summary.json"
    try:
        for name, expected in report["code_sha256"].items():
            destination = args.output/"source_snapshot"/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT/name).read_bytes())
            if digest(destination) != expected:
                raise IOError(f"Source changed during snapshot: {name}")
        for entry in entries:
            for window in (10_000, 20_000, 50_000):
                reader_class = IndexedDSECReader if args.reader == "indexed" else DSECReader
                report["cases"].append(run_case(entry, window, args.output, 2_000_000, 200_000, reader_class))
                target.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
                print(entry["name"], window, report["cases"][-1]["timing_ms"]["read_activity_ms"], flush=True)
        report["status"] = "COMPLETE_ACTIVITY_BASELINE_ONLY"
    except Exception as error:
        report.update(status="FAILED", error=repr(error))
        raise
    finally:
        target.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
