"""M12 adapters: checked image correspondences and masked rectified depth samples."""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class TrackingConfig:
    max_features: int = 400
    quality: float = .01
    min_distance: float = 6.
    fb_max_px: float = 1.


def checked_tracks(previous, current, config=TrackingConfig()):
    """Native-resolution rectified LK, forward/backward checks, no depth filtering."""
    c = config
    if (type(c.max_features) is not int or c.max_features < 1 or not 0 < c.quality <= 1
            or not np.isfinite([c.min_distance, c.fb_max_px]).all()
            or c.min_distance <= 0 or c.fb_max_px <= 0):
        raise ValueError('Invalid tracking configuration')
    if (previous.ndim != 2 or previous.dtype != np.uint8 or current.dtype != np.uint8
            or previous.shape != current.shape or min(previous.shape) < 24):
        raise ValueError('Matching uint8 grayscale images required')
    empty = np.empty((0, 2), np.float32)
    stats = dict(features=0, checked_tracks=0, status='NO_FEATURES')
    features = cv2.goodFeaturesToTrack(previous, maxCorners=c.max_features,
        qualityLevel=c.quality, minDistance=c.min_distance, blockSize=5)
    if features is None:
        return empty, empty.copy(), stats
    stats['features'] = len(features)
    lk = dict(winSize=(21, 21), maxLevel=2,
              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 20, .01))
    forward, good, _ = cv2.calcOpticalFlowPyrLK(previous, current, features, None, **lk)
    if forward is None:
        stats['status'] = 'FORWARD_FAILED'
        return empty, empty.copy(), stats
    backward, reverse_good, _ = cv2.calcOpticalFlowPyrLK(current, previous, forward, None, **lk)
    if backward is None:
        stats['status'] = 'BACKWARD_FAILED'
        return empty, empty.copy(), stats
    p, q, back = features.reshape(-1, 2), forward.reshape(-1, 2), backward.reshape(-1, 2)
    height, width = previous.shape
    keep = ((good.ravel() == 1) & (reverse_good.ravel() == 1)
            & np.isfinite(q).all(axis=1) & np.isfinite(back).all(axis=1)
            & (np.linalg.norm(back-p, axis=1) <= c.fb_max_px)
            & (q[:, 0] >= 0) & (q[:, 0] < width) & (q[:, 1] >= 0) & (q[:, 1] < height))
    stats.update(checked_tracks=int(keep.sum()), status='CHECKED' if keep.any() else 'NO_CHECKED_TRACKS')
    return p[keep].copy(), q[keep].copy(), stats


def sample_masked_depth(points, depth, valid):
    """Nearest pixel floor(x+.5), no hole fill/clamping; keep only first duplicate.

    UNKNOWN depths remain NaN. Rounded pixels outside the map and repeat samples
    are excluded explicitly instead of creating extra independent depth support.
    """
    points = np.asarray(points, dtype=float)
    depth, valid = np.asarray(depth), np.asarray(valid)
    if (points.ndim != 2 or points.shape[1:] != (2,) or not np.isfinite(points).all()
            or depth.ndim != 2 or depth.shape != valid.shape or valid.dtype != bool):
        raise ValueError('Finite Nx2 rectified points, depth map and bool mask required')
    result = np.full(len(points), np.nan)
    height, width = depth.shape
    pixels = np.full((len(points), 2), -1, dtype=np.int64)
    in_bounds = (points[:, 0] >= 0) & (points[:, 1] >= 0) & (points[:, 0] < width-.5) & (points[:, 1] < height-.5)
    pixels[in_bounds] = np.floor(points[in_bounds]+.5).astype(np.int64)
    seen = set(); duplicates = 0
    for index in np.flatnonzero(in_bounds):
        u, v = pixels[index]
        key = (int(u), int(v))
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        if valid[v, u] and np.isfinite(depth[v, u]) and depth[v, u] > 0:
            result[index] = depth[v, u]
    return result, dict(outside_rounded_map=int((~in_bounds).sum()), duplicate_pixels=duplicates,
                        usable_depths=int(np.isfinite(result).sum()), sampled_pixels=pixels.tolist())
