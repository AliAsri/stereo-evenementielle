"""Shared pilot manifest validation and strict DSEC asset discovery."""

import json

import numpy as np


def load_manifest(path):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    groups, names = {}, set()
    for entry in manifest["sequences"]:
        name, group, split = entry["name"], entry["group"], entry["split"]
        # DSEC subdivision letters of one recording may never cross partitions.
        if group != name.rsplit("_", 1)[0] or name in names:
            raise ValueError("Duplicate sequence or invalid drive group")
        if split not in ("train", "validation", "test_reserved"):
            raise ValueError("Unknown split")
        if group in groups and groups[group] != split:
            raise ValueError("Drive group leaks across partitions")
        groups[group] = split
        names.add(name)
    return manifest


def unique_file(folder, pattern):
    paths = list(folder.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"Expected one {pattern} in {folder}, got {len(paths)}")
    return paths[0]


def reference_frames(folder):
    timestamps = np.atleast_1d(np.loadtxt(unique_file(folder, "*_disparity_timestamps.txt"), dtype=np.int64))
    paths = sorted((folder / "disparity_event").rglob("*.png"))
    if len(timestamps) != len(paths) or not len(paths) or np.any(np.diff(timestamps) <= 0):
        raise ValueError("Invalid one-to-one ordered GT timestamp/PNG mapping")
    return timestamps, paths


def sample_indices(timestamps, left, right, window_us, count):
    if window_us <= 0 or count <= 0:
        raise ValueError("Positive window and sample count required")
    eligible = np.flatnonzero((timestamps-window_us >= max(left.first_us, right.first_us)) &
                             (timestamps <= min(left.last_us, right.last_us)))
    if not len(eligible):
        raise ValueError("No complete stereo windows")
    return eligible[np.unique(np.linspace(0, len(eligible)-1, min(count, len(eligible)), dtype=int))]
