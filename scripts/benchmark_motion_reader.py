"""M02: paired reference/indexed reader benchmark with exact M01 equivalence."""

import argparse
from contextlib import ExitStack
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from pfe_events.dsec import DSECReader
from pfe_events.dsec_indexed import IndexedDSECReader
from pfe_events.motion import ActivityDetector
from pfe_events.pilot import load_manifest, unique_file
from pfe_events.artifacts import sha256_file as digest
from pfe_events.reporting import activity_distribution as distribution


READERS = {"reference": DSECReader, "indexed": IndexedDSECReader}


def compare_case(case, output):
    entry_dir = output/case["sequence"]/f"{case['window_us']//1000}ms"
    entry_dir.mkdir(parents=True)
    source = ROOT/case["source"]["path"]
    baseline_path = ROOT/"outputs/motion/M01"/case["sequence"]/f"{case['window_us']//1000}ms/activity.npz"
    rows, passes = [], []
    with np.load(baseline_path, allow_pickle=False) as baseline:
        for repeat in range(2):
            with ExitStack() as stack:
                readers, setup = {}, {}
                for name, reader_class in READERS.items():
                    started = time.perf_counter_ns()
                    readers[name] = stack.enter_context(reader_class(source))
                    setup[name] = (time.perf_counter_ns()-started)/1e6
                detectors = {name: ActivityDetector() for name in readers}
                hashes = {name: hashlib.sha256() for name in readers}
                finish = dict.fromkeys(readers, 0.0)
                count = 0
                for i, start in enumerate(range(case["segment_start_us"], case["segment_end_us_exclusive"], case["window_us"])):
                    end = start+case["window_us"]
                    order = ("reference", "indexed") if (i+repeat) % 2 == 0 else ("indexed", "reference")
                    events, results = {}, {}
                    for name in order:
                        before = time.perf_counter_ns()
                        events[name] = readers[name].window(start, end)
                        loaded = time.perf_counter_ns()
                        results[name] = detectors[name].update(events[name], start, end)
                        done = time.perf_counter_ns()
                        read_ms, activity_ms = (loaded-before)/1e6, (done-loaded)/1e6
                        duration = read_ms+activity_ms
                        arrived = (end-case["segment_start_us"])/1000
                        finish[name] = max(finish[name], arrived)+duration
                        rows.append({"pass": repeat, "reader": name, "first_in_pair": int(name == order[0]),
                                     "end_us": end, "events": len(events[name]["x"]),
                                     "warmup": int(end <= case["segment_start_us"]+case["warmup_us"]),
                                     "read_ms": read_ms, "activity_ms": activity_ms, "total_ms": duration,
                                     "simulated_completion_delay_ms": finish[name]-arrived})
                    # Equivalence and artifact hashing are outside both timed sections.
                    for field in ("x", "y", "t_us", "p"):
                        if not np.array_equal(events["reference"][field], events["indexed"][field]):
                            raise AssertionError(f"Different {field} at {start}")
                        for name in readers:
                            hashes[name].update(events[name][field].tobytes())
                    for field in ("rate", "active", "candidate"):
                        if not np.array_equal(results["reference"][field], results["indexed"][field]):
                            raise AssertionError(f"Different activity {field} at {start}")
                    if results["reference"]["regions"] != results["indexed"]["regions"]:
                        raise AssertionError("Different proposed regions")
                    if not np.array_equal(baseline["rate"][i], results["indexed"]["rate"].astype(np.float32)):
                        raise AssertionError("M01 rate changed")
                    if not np.array_equal(baseline["active"][i], results["indexed"]["active"]):
                        raise AssertionError("M01 mask changed")
                    if int(baseline["end_us"][i]) != end:
                        raise AssertionError("M01 timestamp changed")
                    count += 1
                for name in readers:
                    if hashes[name].hexdigest() != case["window_arrays_sha256"]:
                        raise AssertionError("Event stream differs from original M01")
                passes.append({"pass": repeat, "windows_compared": count, "setup_ms": setup,
                               "event_sha256": {k: v.hexdigest() for k, v in hashes.items()},
                               "indexed_fallback_windows": readers["indexed"].fallback_windows,
                               "index_bytes": readers["indexed"].ms_index.nbytes,
                               "checked_index_boundaries": len(readers["indexed"].checked_boundaries)})
    with (entry_dir/"paired_windows.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    measurements = {}
    for name in READERS:
        selected = [r for r in rows if r["reader"] == name and not r["warmup"]]
        measurements[name] = {
            "timing_ms": {key: distribution([r[key] for r in selected]) for key in
                          ("read_ms", "activity_ms", "total_ms", "simulated_completion_delay_ms")},
            "fraction_over_step": float(np.mean([r["total_ms"] > case["window_us"]/1000 for r in selected])),
            "total_ms_by_pass": [distribution([r["total_ms"] for r in selected if r["pass"] == n]) for n in range(2)],
        }
    summary = {"sequence": case["sequence"], "split": case["split"], "window_us": case["window_us"],
               "start_us": case["segment_start_us"], "end_us": case["segment_end_us_exclusive"],
               "parameters": ActivityDetector().parameters(), "equivalence": "PASS: exact events, maps, masks, regions; M01 hashes/maps/timestamps unchanged",
               "passes": passes, "measurements": measurements,
               "read_median_speedup": measurements["reference"]["timing_ms"]["read_ms"]["median"]/measurements["indexed"]["timing_ms"]["read_ms"]["median"],
               "total_median_speedup": measurements["reference"]["timing_ms"]["total_ms"]["median"]/measurements["indexed"]["timing_ms"]["total_ms"]["median"]}
    (entry_dir/"summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"outputs/motion/M02")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a fresh directory; previous evidence stays unchanged")
    m01 = ROOT/"outputs/motion/M01/summary.json"
    previous = json.loads(m01.read_text(encoding="utf-8"))
    allowed = {e["name"]: e["split"] for e in load_manifest(ROOT/"configs/pilot.json")["sequences"] if e["split"] != "test_reserved"}
    for c in previous["cases"]:
        if c["sequence"] not in allowed or c["split"] != allowed[c["sequence"]]:
            raise ValueError("Invalid/reserved sequence in reference report")
        expected_source = unique_file(ROOT/"data/raw"/c["sequence"]/"events_left", "events.h5").resolve()
        if (ROOT/c["source"]["path"]).resolve() != expected_source:
            raise ValueError("Source path differs from sequence")
    cv2.setNumThreads(1)
    args.output.mkdir(parents=True)
    report = {"experiment": "M02", "status": "RUNNING", "utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "platform": platform.platform(),
              "versions": {k: importlib.metadata.version(k) for k in previous["versions"]}, "reference_m01_sha256": digest(m01),
              "protocol": "Two paired passes, alternate reader order each window and reverse in pass 2. 200ms dataset warmup per pass. Same M01 windows and activity. Setup recorded separately; compare/hash/write excluded. OS/cache/order effects not eliminated. Queue is simulated, not actual live latency.",
              "code_sha256": {p: digest(ROOT/p) for p in ['src/pfe_events/artifacts.py','src/pfe_events/reporting.py',"src/pfe_events/dsec.py", "src/pfe_events/dsec_indexed.py", "src/pfe_events/motion.py", "scripts/benchmark_motion_reader.py", "scripts/run_motion_baseline.py"]},
              "real_motion_onset_delay_ms": None, "false_alerts_per_second": None, "cases": []}
    target = args.output/"summary.json"
    try:
        for name, expected in report["code_sha256"].items():
            destination = args.output/"source_snapshot"/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT/name).read_bytes())
            if digest(destination) != expected:
                raise IOError(f"Source changed during snapshot: {name}")
        for case in previous["cases"]:
            result = compare_case(case, args.output)
            report["cases"].append(result)
            target.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
            print(result["sequence"], result["window_us"], {k: v["timing_ms"]["total_ms"] for k, v in result["measurements"].items()}, flush=True)
        report["status"] = "PASS_EQUIVALENCE_AND_BENCHMARK"
    except Exception as error:
        report.update(status="FAILED", error=repr(error))
        raise
    finally:
        target.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
