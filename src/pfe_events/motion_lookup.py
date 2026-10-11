"""M09: precomputed pixel-to-cell lookup with exact reference activity outputs.

The update body follows motion.ActivityDetector deliberately: reference remains
archived and directly comparable. Change validation/state logic in both only
with equivalence tests. No thresholds, persistence or region rules are changed.
"""
import cv2
import numpy as np
from .motion import ActivityConfig, ActivityDetector


class LookupActivityDetector(ActivityDetector):
    def __init__(self, config=ActivityConfig()):
        super().__init__(config)
        pixels = np.arange(config.width*config.height, dtype=np.intp)
        self.pixel_to_cell = ((pixels//config.width//config.cell_px)*self.shape[1]
                              + pixels%config.width//config.cell_px)
        self.pixel_to_cell.flags.writeable = False

    def update(self, events, start_us, end_us):
        c = self.config
        if any(not isinstance(v, (int, np.integer)) for v in (start_us, end_us)):
            raise TypeError("Integer microsecond boundaries required")
        duration = int(end_us)-int(start_us)
        if duration <= 0 or (self.previous_end is not None and start_us != self.previous_end):
            raise ValueError("Positive contiguous windows required; reset detector for another segment")
        x, y, t = (np.asarray(events[k]) for k in ("x", "y", "t_us"))
        if any(v.ndim != 1 or v.dtype.kind not in "iu" for v in (x, y, t)) or not (x.shape == y.shape == t.shape):
            raise ValueError("Equal-length integer event vectors required")
        if (np.any(x < 0) or np.any(x >= c.width) or np.any(y < 0) or np.any(y >= c.height)
                or (t.size and (np.any(t[1:] < t[:-1]) or t[0] < start_us or t[-1] >= end_us))):
            raise ValueError("Invalid coordinates, order or half-open window membership")
        pixel_id = y.astype(np.intp, copy=False)*c.width+x.astype(np.intp, copy=False)
        pixel_counts = np.bincount(pixel_id, minlength=c.width*c.height)
        occupied = np.flatnonzero(pixel_counts != 0)
        cell_id = self.pixel_to_cell[occupied]
        n_cells = int(np.prod(self.shape))
        counts = np.bincount(cell_id, weights=pixel_counts[occupied], minlength=n_cells).reshape(self.shape)
        support = np.bincount(cell_id, minlength=n_cells).reshape(self.shape)
        rate = counts/(self.area*(duration/1e6))
        candidate = (rate >= c.min_rate) & (support >= c.min_active_pixels)
        self.elapsed = np.where(candidate, np.minimum(self.elapsed+duration, c.persistence_us), 0)
        active = candidate & (self.elapsed >= c.persistence_us)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(active.astype(np.uint8), connectivity=8)
        regions = []
        retained = np.zeros(self.shape, dtype=bool)
        for index in range(1, n):
            gx, gy, gw, gh, area = map(int, stats[index])
            if area < c.min_region_cells:
                continue
            mask = labels == index
            retained |= mask
            regions.append({"xyxy": [gx*c.cell_px, gy*c.cell_px, min((gx+gw)*c.cell_px, c.width),
                                     min((gy+gh)*c.cell_px, c.height)],
                            "cells": area, "events": int(counts[mask].sum()),
                            "timestamp_us": int(end_us), "kind": "EVENT_ACTIVITY_NOT_OBJECT_CLASS"})
        self.previous_end = int(end_us)
        return {"rate": rate, "candidate": candidate, "active": retained,
                "occupied_pixels": occupied, "regions": regions, "events": len(t),
                "active_fraction": float(retained.mean()),
                "widespread_activity": bool(candidate.mean() >= c.widespread_fraction),
                "start_us": int(start_us), "end_us_exclusive": int(end_us)}

