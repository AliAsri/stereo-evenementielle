"""Bounded-memory DSEC inspection with a reference binary-search time slicer."""

from pathlib import Path

import h5py
import hdf5plugin  # Registers the compression filters used by DSEC.
import numpy as np


class DSECReader:
    """Context-managed reader. Times exposed by this class are absolute integer µs."""

    def __init__(self, path: str | Path, width=640, height=480):
        self.path = Path(path)
        self.width, self.height = width, height
        self.file = None

    def __enter__(self):
        self.file = h5py.File(self.path, "r")
        try:
            for key in ("events/x", "events/y", "events/t", "events/p", "t_offset", "ms_to_idx"):
                if key not in self.file:
                    raise ValueError(f"Missing DSEC field: {key}")
            self.events = self.file["events"]
            sizes = {self.events[key].shape for key in ("x", "y", "t", "p")}
            if len(sizes) != 1 or len(next(iter(sizes))) != 1:
                raise ValueError("Event fields must be equal-length 1D datasets")
            for key in ("x", "y", "t", "p"):
                if self.events[key].dtype.kind not in "uib":
                    raise ValueError(f"Expected integer field: {key}")
            self.offset_us = int(self.file["t_offset"][()])
            self.count = len(self.events["t"])
            if self.count == 0:
                raise ValueError("Empty event file")
            self.first_us = int(self.events["t"][0]) + self.offset_us
            self.last_us = int(self.events["t"][-1]) + self.offset_us
            if not (0 <= self.first_us <= self.last_us < np.iinfo(np.int64).max):
                raise ValueError("Invalid or overflowing timestamp range")
        except Exception:
            self.file.close()
            self.file = None
            raise
        return self

    def __exit__(self, *_):
        self.file.close()
        self.file = None

    def _lower_bound(self, local_us):
        """First index t>=local_us, without loading the complete timestamp vector."""
        low, high = 0, self.count
        times = self.events["t"]
        while low < high:
            middle = (low + high) // 2
            if int(times[middle]) < local_us:
                low = middle + 1
            else:
                high = middle
        return low

    def window(self, start_us: int, end_us: int, max_events=2_000_000):
        """Return x/y/t_us/p arrays for [start,end); error on excessive allocation."""
        if not isinstance(start_us, (int, np.integer)) or not isinstance(end_us, (int, np.integer)):
            raise TypeError("Window times must be integer microseconds")
        if start_us >= end_us or max_events <= 0:
            raise ValueError("Window must have positive duration and event budget")
        first = self._lower_bound(int(start_us) - self.offset_us)
        last = self._lower_bound(int(end_us) - self.offset_us)
        if last - first > max_events:
            raise MemoryError("Window exceeds max_events; shorten it explicitly")
        result = {key: self.events[key][first:last] for key in ("x", "y", "p")}
        times = self.events["t"][first:last].astype(np.int64) + self.offset_us
        result["t_us"] = times
        if times.size and (np.any(times[1:] < times[:-1]) or times[0] < start_us or times[-1] >= end_us):
            raise ValueError("Unsorted or out-of-window timestamps")
        if np.any(result["x"] < 0) or np.any(result["x"] >= self.width) or np.any(result["y"] < 0) or np.any(result["y"] >= self.height):
            raise ValueError("Event coordinates outside sensor bounds")
        if not np.isin(result["p"], [0, 1]).all():
            raise ValueError("Expected DSEC polarities 0/1")
        return result

    def audit_timestamps(self, chunk_size=1_000_000):
        """Check monotonicity over the entire file using bounded chunks."""
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        previous = None
        for start in range(0, self.count, chunk_size):
            times = self.events["t"][start:start + chunk_size]
            if np.any(times[1:] < times[:-1]) or (previous is not None and int(times[0]) < previous):
                raise ValueError(f"Unsorted timestamps near index {start}")
            previous = int(times[-1])
        return {"checked_timestamps": self.count, "nondecreasing": True}


def load_rectify_map(path: str | Path, width=640, height=480):
    with h5py.File(path, "r") as stream:
        mapping = stream["rectify_map"][:]
    if mapping.shape != (height, width, 2):
        raise ValueError(f"Unexpected map shape: {mapping.shape}")
    return mapping


def rectify_events(events, mapping, width=640, height=480):
    """Nearest-pixel rectification for inspection; return events and dropped count."""
    xy = mapping[events["y"], events["x"]]
    finite = np.isfinite(xy).all(axis=1)
    rounded = np.zeros_like(xy, dtype=np.int64)
    rounded[finite] = np.rint(xy[finite]).astype(np.int64)
    keep = finite & (rounded[:, 0] >= 0) & (rounded[:, 0] < width) & (rounded[:, 1] >= 0) & (rounded[:, 1] < height)
    result = {"x": rounded[keep, 0], "y": rounded[keep, 1], "t_us": events["t_us"][keep], "p": events["p"][keep]}
    return result, int((~keep).sum())
