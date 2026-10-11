"""Causal rate-outlier proposals; no camera pose or independent motion claim."""
from dataclasses import asdict, dataclass
import math
import cv2
import numpy as np
from .motion import ActivityConfig, ActivityDetector


@dataclass(frozen=True)
class AdaptiveConfig:
    mode: str = 'relative_history'
    global_mad_factor: float = 3.0
    history_deviation_factor: float = 3.0
    history_tau_us: int = 200_000
    warmup_us: int = 200_000


class AdaptiveActivityDetector:
    """Use M01's checked counts/support, then independent adaptive persistence.

    The reference detector also computes its own regions internally. This
    deliberately keeps M01 unchanged; measured adaptive cost includes that work.
    History is read before its update. Warm-up produces invalid/unknown outputs.
    """
    def __init__(self, activity=ActivityConfig(), adaptive=AdaptiveConfig()):
        a = adaptive
        if a.mode not in ('relative', 'relative_history'):
            raise ValueError('Unknown adaptive mode')
        if any(not math.isfinite(v) or v < 0 for v in (a.global_mad_factor, a.history_deviation_factor)):
            raise ValueError('Finite nonnegative scale factors required')
        if any(type(v) is not int or v <= 0 for v in (a.history_tau_us, a.warmup_us)):
            raise ValueError('Positive integer history and warm-up required')
        self.config = activity; self.adaptive = a
        self.reference = ActivityDetector(activity)
        self.elapsed = np.zeros(self.reference.shape, dtype=np.int64)
        self.history = np.zeros(self.reference.shape)
        self.deviation = np.zeros(self.reference.shape)
        self.seen_us = 0

    def parameters(self):
        return {'activity': asdict(self.config), 'adaptive': asdict(self.adaptive)}

    def update(self, events, start_us, end_us):
        # M01 validates all inputs before state changes; errors leave us unchanged.
        base = self.reference.update(events, start_us, end_us)
        c, a = self.config, self.adaptive
        duration = int(end_us)-int(start_us)
        rate = base['rate']
        median = float(np.median(rate))
        mad = float(np.median(np.abs(rate-median)))
        excess = rate-median
        spatial_floor = max(c.min_rate, a.global_mad_factor*1.4826*mad)
        threshold = np.full(rate.shape, spatial_floor)
        if a.mode == 'relative_history':
            threshold = np.maximum(threshold, self.history+np.maximum(c.min_rate, a.history_deviation_factor*self.deviation))
        candidate = base['candidate'] & (excess > threshold)
        valid = self.seen_us >= a.warmup_us
        self.elapsed = (np.where(candidate, np.minimum(self.elapsed+duration, c.persistence_us), 0)
                        if valid else np.zeros_like(self.elapsed))
        active = candidate & (self.elapsed >= c.persistence_us) if valid else np.zeros_like(candidate)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(active.astype(np.uint8), connectivity=8)
        retained = np.zeros_like(active); regions = []
        for i in range(1, n):
            gx, gy, gw, gh, cells = map(int, stats[i])
            if cells < c.min_region_cells: continue
            retained |= labels == i
            regions.append({'xyxy': [gx*c.cell_px, gy*c.cell_px,
                min((gx+gw)*c.cell_px, c.width), min((gy+gh)*c.cell_px, c.height)],
                'cells': cells, 'timestamp_us': int(end_us), 'kind': 'ADAPTIVE_ACTIVITY_NOT_OBJECT_MOTION'})
        # EMA is a causal local history, not a robust motion or illumination model.
        alpha = -math.expm1(-duration/a.history_tau_us)
        innovation = excess-self.history
        self.history += alpha*innovation
        self.deviation += alpha*(np.abs(innovation)-self.deviation)
        self.seen_us += duration
        return {'regions': regions, 'active': retained, 'active_fraction': float(retained.mean()),
                'valid': valid, 'status': 'VALID_ACTIVITY' if valid else 'WARMUP',
                'global_median_rate': median, 'global_mad_rate': mad,
                'candidate': candidate, 'threshold_excess': threshold,
                'start_us': int(start_us), 'end_us_exclusive': int(end_us)}
