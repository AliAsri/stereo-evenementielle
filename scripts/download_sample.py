"""Download a bounded, official DSEC sample; never download the full dataset."""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import http.client
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


SEQUENCE = "zurich_city_04_e"
BASE = f"https://download.ifi.uzh.ch/rpg/DSEC/train/{SEQUENCE}"
ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 600 * 1024**2


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(url, destination):
    """Stream at most 600 MiB to a .part file; record size and a local digest."""
    if destination.exists():
        raise FileExistsError(f"Untracked existing file: {destination}")
    partial = destination.with_suffix(destination.suffix + ".part")
    start = partial.stat().st_size if partial.exists() else 0
    request = urllib.request.Request(url, headers={"Range": f"bytes={start}-"} if start else {})
    with urllib.request.urlopen(request, timeout=45) as response:
        append = response.status == 206 and start > 0
        if append and not response.headers.get("Content-Range", "").startswith(f"bytes {start}-"):
            raise IOError("Server returned an inconsistent range")
        initial = start if append else 0
        length = int(response.headers.get("Content-Length", 0))
        if length + initial > MAX_BYTES:
            raise ValueError(f"File exceeds download budget: {length} bytes")
        size = initial
        with partial.open("ab" if append else "wb") as output:
            while chunk := response.read(1024**2):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("Download exceeded byte budget")
                output.write(chunk)
        if length and size != length + initial:
            raise IOError(f"Incomplete download: {size}/{length + initial}")
    partial.replace(destination)
    return {"url": url, "bytes": size, "sha256": sha256(destination)}


def extract_checked(archive_path, destination):
    """Extract only contained paths and refuse to overwrite existing data."""
    destination = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if sum(m.file_size for m in members) > 2 * 1024**3:
            raise ValueError("Archive exceeds extraction budget")
        for member in members:
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError(f"Unsafe archive path: {member.filename}")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if target.exists():
                # Re-running a completed extraction is safe only for identical bytes.
                with archive.open(member) as source:
                    expected = hashlib.file_digest(source, "sha256").hexdigest()
                if sha256(target) != expected:
                    raise FileExistsError(f"Existing data differs: {target}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # Publish only after the entire member (including its CRC) is read.
            # A failed extraction must not leave a final file that blocks retries.
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name + ".",
                                                 suffix=".part", delete=False) as output:
                    temporary = Path(output.name)
                    with archive.open(member) as source:
                        shutil.copyfileobj(source, output)
                # Windows rename refuses an existing target; POSIX rename would
                # overwrite it, so use exclusive hard-link creation there.
                if os.name == 'nt':
                    temporary.rename(target)
                else:
                    target.hardlink_to(temporary)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence", choices=("zurich_city_04_e", "zurich_city_04_b", "thun_00_a"), default=SEQUENCE,
                        help="Bounded pilot sequence; split recorded in configs/pilot.json")
    parser.add_argument("--events", action="store_true", help="Add both event streams (~488 MB published)")
    parser.add_argument("--disparity", action="store_true", help="Add reference disparity (~18 MB published)")
    parser.add_argument("--labels", action="store_true", help="Add official detection labels (~4.7 MB)")
    args = parser.parse_args()
    sequence = args.sequence
    base = f"https://download.ifi.uzh.ch/rpg/DSEC/train/{sequence}"
    folder = ROOT / "data" / "raw" / sequence
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "downloads.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    suffixes = ["calibration.zip", "disparity_timestamps.txt"]
    if args.events:
        suffixes.extend(["events_left.zip", "events_right.zip"])
    if args.disparity:
        suffixes.append("disparity_event.zip")
    entries = [(f"{sequence}_{s}", f"{base}/{sequence}_{s}", s.removesuffix(".zip")) for s in suffixes]
    if args.labels:
        name = "dsec-det_left_object_detections.zip"
        entries.append((name, f"https://download.ifi.uzh.ch/rpg/DSEC/detection/{name}", "detection_labels"))
    for name, url, extracted_folder in entries:
        path = folder / name
        if name in manifest and path.exists():
            if sha256(path) != manifest[name]["sha256"]:
                raise ValueError(f"Checksum changed: {path}")
        else:
            print(f"Downloading {name}", flush=True)
            for attempt in range(1, 4):
                try:
                    manifest[name] = download(url, path)
                    break
                except (TimeoutError, urllib.error.URLError, http.client.IncompleteRead) as error:
                    print(f"Attempt {attempt}/3 failed: {error}; partial file retained", flush=True)
                    if attempt == 3:
                        raise
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        if path.suffix == ".zip":
            extract_checked(path, folder / extracted_folder)
        if name == "dsec-det_left_object_detections.zip":
            # The official release is a ZIP of train/test ZIPs; only inspect train.
            extract_checked(folder / extracted_folder / "train_object_detections.zip", folder / extracted_folder / "train_labels")
        print(f"OK {name}: {manifest[name]['bytes']} bytes", flush=True)
    print("Local SHA256 digests detect later changes; they are not publisher checksums.")


if __name__ == "__main__":
    main()
