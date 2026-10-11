"""Import Y01 evidence from Colab ZIP parts without loading model checkpoints.

Keep metadata, figures and best/last/initial weights; leave epoch snapshots in ZIPs.
Usage: python scripts/import_y01_results.py archive-001.zip archive-002.zip
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RUN = "Y01_20261003T191753Z"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", type=Path, nargs="+")
    args = parser.parse_args()
    destination = ROOT / "outputs" / "colab"
    destination.mkdir(parents=True, exist_ok=True)
    if not destination.resolve().is_relative_to(ROOT):
        raise ValueError("Destination outside project")
    report = {"run": RUN, "audited_utc": datetime.now(timezone.utc).isoformat(),
              "method": "ZIP inventory, selective CRC-checked extraction and SHA256; no checkpoint deserialization or local model evaluation",
              "archives": [], "files": [], "checks": []}
    seen = set()
    for archive in args.archives:
        entry = {"path": str(archive.resolve()), "bytes": archive.stat().st_size,
                 "sha256": sha256(archive), "members": 0, "uncompressed_bytes": 0}
        with zipfile.ZipFile(archive) as zipped:
            for info in zipped.infolist():
                path = PurePosixPath(info.filename)
                if (path.is_absolute() or ".." in path.parts or "\\" in info.filename
                        or ":" in info.filename or not path.parts or path.parts[0] != RUN
                        or stat.S_ISLNK(info.external_attr >> 16)):
                    raise ValueError(f"Unsafe ZIP member: {info.filename}")
                if info.is_dir():
                    continue
                if info.filename in seen:
                    raise ValueError(f"Duplicate ZIP member: {info.filename}")
                seen.add(info.filename)
                entry["members"] += 1
                entry["uncompressed_bytes"] += info.file_size
                keep = (path.suffix.lower() in {".json", ".yaml", ".csv", ".png", ".jpg", ".txt"}
                        or path.name in {"best.pt", "last.pt", "yolo11n.pt"})
                record = {"archive": archive.name, "member": info.filename,
                          "bytes": info.file_size, "zip_crc32": f"{info.CRC:08x}",
                          "retained": keep, "crc_verified": False}
                if keep:
                    if info.file_size > 100_000_000:
                        raise ValueError(f"Unexpected large retained member: {info.filename}")
                    target = destination.joinpath(*path.parts)
                    if not target.resolve().is_relative_to(destination.resolve()):
                        raise ValueError(f"Destination escape: {target}")
                    data = zipped.read(info)  # zipfile verifies CRC on the complete member.
                    digest = hashlib.sha256(data).hexdigest()
                    if target.exists() and sha256(target) != digest:
                        raise ValueError(f"Refusing to replace different existing file: {target}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        target.write_bytes(data)
                    if sha256(target) != digest:
                        raise IOError(f"Extraction hash mismatch: {target}")
                    record.update(sha256=digest, crc_verified=True,
                                  local_path=target.relative_to(ROOT).as_posix())
                report["files"].append(record)
        report["archives"].append(entry)
    run = destination / RUN

    def read(name):
        return json.loads((run / name).read_text(encoding="utf-8"))

    def check(label, path, expected):
        actual = sha256(path)
        report["checks"].append({"label": label, "path": str(path.relative_to(ROOT)),
                                 "expected": expected, "actual": actual, "passed": actual == expected})

    provenance = read("dataset-provenance.json")
    report["dataset_provenance"] = provenance
    report["environment"] = read("environment.json")
    report["run_status"] = read("status.json")
    report["pilot_metrics"] = read("pilot-metrics.json")
    report["overfit_initial_metrics"] = read("overfit-metrics.json")
    report["tensor_check"] = read("tensor-check.json")
    report["dataset_verification"] = read("dataset-verification.json")
    retries = sorted(run.glob("overfit_retry_*/metrics.json"))
    report["overfit_retries"] = [{"directory": p.parent.name,
                                  "metrics": json.loads(p.read_text(encoding="utf-8"))} for p in retries]
    # Compare the copied manifest and normalizer byte-for-byte with the local export.
    for name in ["manifest.json", "normalizer.json"]:
        check(f"local_export_{name}", run / name,
              sha256(ROOT / "data/processed/dsec_yolo_pilot_v1" / name))
        check(f"declared_{name}", run / name, provenance[f"{Path(name).stem}_sha256"])
    check("dataset_zip", ROOT / "data/processed/dsec_yolo_pilot_v1.zip", provenance["archive_sha256"])
    check("initial_checkpoint", run / "initial_weights/yolo11n.pt", read("checkpoint-provenance.json")["sha256"])
    pilot = report["pilot_metrics"]
    for name in ["best", "last"]:
        check(f"pilot_{name}", run / f"pilot/weights/{name}.pt", pilot[f"{name}_sha256"])
    for retry in report["overfit_retries"]:
        check("retry_best", run / retry["directory"] / "fit/weights/best.pt",
              retry["metrics"]["best_sha256"])
    report["csv_training_summaries"] = []
    for path in sorted(run.rglob("results.csv")):
        with path.open(encoding="utf-8", newline="") as stream:
            rows = [{k.strip(): float(v) for k, v in row.items()} for row in csv.DictReader(stream)]
        report["csv_training_summaries"].append({
            "path": path.relative_to(ROOT).as_posix(), "epochs": len(rows),
            "first": rows[0], "last": rows[-1],
            "best_map50_epoch": int(max(rows, key=lambda r: r["metrics/mAP50(B)"])["epoch"]),
            "best_map50_95_epoch": int(max(rows, key=lambda r: r["metrics/mAP50-95(B)"])["epoch"]),
        })
    report["retained_files"] = sum(f["retained"] for f in report["files"])
    report["retained_bytes"] = sum(f["bytes"] for f in report["files"] if f["retained"])
    report["status"] = "PASS" if all(c["passed"] for c in report["checks"]) else "FAIL"
    output = ROOT / "outputs/reports/Y01_colab_audit.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["status", "retained_files", "retained_bytes", "checks"]}, indent=2))
    if report["status"] != "PASS":
        raise SystemExit("Evidence mismatch: see audit report")


if __name__ == "__main__":
    main()
