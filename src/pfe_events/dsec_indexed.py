"""Bounded indexed DSEC slicing, with DSECReader kept as the reference.

ms_to_idx brackets timestamps; exact half-open membership is still determined
from the original timestamps. No future event is passed to a consumer.
"""

import numpy as np

from .dsec import DSECReader


class IndexedDSECReader(DSECReader):
    def __enter__(self):
        super().__enter__()
        try:
            index = self.file["ms_to_idx"]
            if index.ndim != 1 or index.dtype.kind not in "iu" or not len(index):
                raise ValueError("Expected nonempty integer millisecond index")
            if len(index) > 10_000_000:
                raise MemoryError("Millisecond index exceeds 80 MB budget")
            values = index[:]
            if (values[0] != 0 or np.any(values < 0) or np.any(values > self.count)
                    or np.any(values[1:] < values[:-1])):
                raise ValueError("Invalid millisecond index range/order")
            self.ms_index = values.astype(np.int64)
            self.checked_boundaries = set()
            self.fallback_windows = 0
        except Exception:
            super().__exit__()
            raise
        return self

    def _boundary(self, ms):
        """Validate each used entry against its adjacent event timestamps once."""
        position = int(self.ms_index[ms])
        if ms not in self.checked_boundaries:
            target = ms*1000
            times = self.events["t"]
            if ((position > 0 and int(times[position-1]) >= target)
                    or (position < self.count and int(times[position]) < target)):
                raise ValueError(f"Incorrect ms_to_idx boundary at {ms} ms")
            self.checked_boundaries.add(ms)
        return position

    def window(self, start_us, end_us, max_events=2_000_000):
        if not isinstance(start_us, (int, np.integer)) or not isinstance(end_us, (int, np.integer)):
            raise TypeError("Window times must be integer microseconds")
        if start_us >= end_us or max_events <= 0:
            raise ValueError("Window must have positive duration and event budget")
        start, end = int(start_us)-self.offset_us, int(end_us)-self.offset_us
        lower_ms, upper_ms = start//1000, (end+999)//1000
        if lower_ms < 0 or upper_ms >= len(self.ms_index):
            self.fallback_windows += 1
            return super().window(start_us, end_us, max_events)
        first, last = self._boundary(lower_ms), self._boundary(upper_ms)
        if last-first > max_events:
            # The conservative envelope can exceed the budget even if the exact
            # interval fits. Reference search avoids allocating that envelope.
            self.fallback_windows += 1
            return super().window(start_us, end_us, max_events)
        local_times = self.events["t"][first:last]
        if np.any(local_times[1:] < local_times[:-1]):
            raise ValueError("Unsorted timestamps in indexed envelope")
        lo, hi = np.searchsorted(local_times, [start, end], side="left")
        times = local_times[lo:hi].astype(np.int64)+self.offset_us
        result = {key: self.events[key][first+int(lo):first+int(hi)] for key in ("x", "y", "p")}
        result["t_us"] = times
        if times.size and (times[0] < start_us or times[-1] >= end_us):
            raise ValueError("Out-of-window timestamps")
        if (np.any(result["x"] < 0) or np.any(result["x"] >= self.width)
                or np.any(result["y"] < 0) or np.any(result["y"] >= self.height)):
            raise ValueError("Event coordinates outside sensor bounds")
        if not np.isin(result["p"], [0, 1]).all():
            raise ValueError("Expected DSEC polarities 0/1")
        return result
