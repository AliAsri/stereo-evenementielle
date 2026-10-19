"""M12 adapters: checked image correspondences and masked rectified depth samples."""
from dataclasses import dataclass

import cv2
import numpy as np

from .geometry import reproject_q


@dataclass(frozen=True)
class TrackingConfig:
    max_features: int = 400
    quality: float = .01
    min_distance: float = 6.
    fb_max_px: float = 1.
    selection: str = 'global'  # Experimental spatial_8x6 must be explicitly enabled.


def select_features(image, config=TrackingConfig()):
    """Select at most max_features; spatial mode shares the global quality gate.

    Spatial selection enumerates all globally spaced GFTT candidates, then
    takes one per occupied 8x6 cell per round, preserving rank within cells.
    Empty cells consume no quota. Final order follows original response rank.
    Candidate enumeration is not bounded by max_features; LK input is bounded.
    No annotations, depth, future image or object locations enter selection.
    """
    c = config
    if (type(c.max_features) is not int or c.max_features < 1 or not 0 < c.quality <= 1
            or not np.isfinite([c.min_distance, c.fb_max_px]).all()
            or c.min_distance <= 0 or c.fb_max_px <= 0
            or c.selection not in ('global', 'spatial_8x6')):
        raise ValueError('Invalid tracking configuration')
    if image.ndim != 2 or image.dtype != np.uint8 or min(image.shape) < 24:
        raise ValueError('uint8 grayscale image required')
    features = cv2.goodFeaturesToTrack(image,
        maxCorners=c.max_features if c.selection == 'global' else 0,
        qualityLevel=c.quality, minDistance=c.min_distance, blockSize=5)
    if c.selection == 'global' or features is None or len(features) <= c.max_features:
        return features
    height, width = image.shape
    points = features.reshape(-1, 2)
    cell = (points[:, 1].astype(int)*6//height)*8 + points[:, 0].astype(int)*8//width
    buckets = [np.flatnonzero(cell == index) for index in range(48)]
    selected, level = [], 0
    while len(selected) < c.max_features:
        for bucket in buckets:
            if level < len(bucket):
                selected.append(int(bucket[level]))
                if len(selected) == c.max_features:
                    break
        level += 1
    return features[np.sort(selected)].copy()


def checked_tracks(previous, current, config=TrackingConfig()):
    """Native-resolution rectified LK, forward/backward checks, no depth filtering."""
    c = config
    if (type(c.max_features) is not int or c.max_features < 1 or not 0 < c.quality <= 1
            or not np.isfinite([c.min_distance, c.fb_max_px]).all()
            or c.min_distance <= 0 or c.fb_max_px <= 0
            or c.selection not in ('global', 'spatial_8x6')):
        raise ValueError('Invalid tracking configuration')
    if (previous.ndim != 2 or previous.dtype != np.uint8 or current.dtype != np.uint8
            or previous.shape != current.shape or min(previous.shape) < 24):
        raise ValueError('Matching uint8 grayscale images required')
    empty = np.empty((0, 2), np.float32)
    stats = dict(features=0, checked_tracks=0, status='NO_FEATURES')
    features = select_features(previous, c)
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


def _sample_pixels(points, values, valid):
    """Select valid first occurrences using the historical nearest-pixel rule."""
    points = np.asarray(points, dtype=float)
    values, valid = np.asarray(values), np.asarray(valid)
    if (points.ndim != 2 or points.shape[1:] != (2,) or not np.isfinite(points).all()
            or values.ndim != 2 or values.shape != valid.shape or valid.dtype != bool):
        raise ValueError('Finite Nx2 rectified points, 2D map and bool mask required')
    height, width = values.shape
    pixels = np.full((len(points), 2), -1, dtype=np.int64)
    in_bounds = (points[:, 0] >= 0) & (points[:, 1] >= 0) & (points[:, 0] < width-.5) & (points[:, 1] < height-.5)
    pixels[in_bounds] = np.floor(points[in_bounds]+.5).astype(np.int64)
    seen = set(); duplicates = 0; selected = []
    for index in np.flatnonzero(in_bounds):
        u, v = pixels[index]
        key = (int(u), int(v))
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        if valid[v, u]:
            selected.append(index)
    return values, pixels, np.asarray(selected, dtype=np.intp), dict(
        outside_rounded_map=int((~in_bounds).sum()), duplicate_pixels=duplicates,
        sampled_pixels=pixels.tolist())


def sample_masked_depth(points, depth, valid):
    """Nearest pixel floor(x+.5), no hole fill/clamping; keep only first duplicate.

    UNKNOWN depths remain NaN. Rounded pixels outside the map and repeat samples
    are excluded explicitly instead of creating extra independent depth support.
    """
    depth, pixels, selected, stats = _sample_pixels(points, depth, valid)
    result = np.full(len(pixels), np.nan)
    u, v = pixels[selected].T
    values = depth[v, u]
    usable = np.isfinite(values) & (values > 0)
    result[selected[usable]] = values[usable]
    stats['usable_depths'] = int(np.isfinite(result).sum())
    return result, stats


def sample_disparity_depth(points, disparity, valid, q):
    """Project only sampled integer pixels; match the former float32 depth map.

    Q is applied at the rounded pixel, not the subpixel tracking coordinate.
    Preserve the full XYZ validity check, float32 rounding, and unknown samples.
    No complete depth image is allocated.
    """
    disparity, pixels, selected, stats = _sample_pixels(points, disparity, valid)
    result = np.full(len(pixels), np.nan)
    u, v = pixels[selected].T
    values = reproject_q(u, v, disparity[v, u], q)[..., 2].astype(np.float32)
    usable = np.isfinite(values) & (values > 0)
    result[selected[usable]] = values[usable]
    stats['usable_depths'] = int(np.isfinite(result).sum())
    return result, stats
