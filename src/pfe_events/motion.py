"""Causal activity proposals, independent of object classes and neural inference.

Activity is not independently moving object segmentation: ego-motion and light
changes also generate events. Thresholds are engineering defaults, not fitted.
"""

from dataclasses import dataclass, asdict

import cv2
import numpy as np


@dataclass(frozen=True)
class ActivityConfig:
    width: int = 640
    height: int = 480
    cell_px: int = 16
    min_rate: float = 20.0  # events / second / sensor pixel
    min_active_pixels: int = 4
    persistence_us: int = 20_000
    min_region_cells: int = 2
    widespread_fraction: float = 0.6


class ActivityDetector:
    """One update per contiguous [start,end) window, in native left coordinates."""

    def __init__(self, config=ActivityConfig()):
        c = config
        integer_fields = (c.width, c.height, c.cell_px, c.min_active_pixels,
                          c.persistence_us, c.min_region_cells)
        if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in integer_fields):
            raise ValueError("Positive integer geometry/support/persistence required")
        if not np.isfinite(c.min_rate) or c.min_rate <= 0 or not 0 < c.widespread_fraction <= 1:
            raise ValueError("Invalid rate or widespread fraction")
        self.config = c
        self.shape = ((c.height+c.cell_px-1)//c.cell_px, (c.width+c.cell_px-1)//c.cell_px)
        heights = np.minimum(c.cell_px, c.height-np.arange(self.shape[0])*c.cell_px)
        widths = np.minimum(c.cell_px, c.width-np.arange(self.shape[1])*c.cell_px)
        self.area = heights[:, None]*widths[None, :]
        self.elapsed = np.zeros(self.shape, dtype=np.int64)
        self.previous_end = None

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
        pixel_id = y.astype(np.intp)*c.width+x.astype(np.intp)
        pixel_counts = np.bincount(pixel_id, minlength=c.width*c.height)
        occupied = np.flatnonzero(pixel_counts)
        cell_id = (occupied//c.width//c.cell_px)*self.shape[1]+(occupied%c.width//c.cell_px)
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

    def parameters(self):
        return asdict(self.config)
