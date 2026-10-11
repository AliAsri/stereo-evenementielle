"""Associate a native YOLO box with a predicted rectified visible surface.

This estimates a sampled surface point, never an object centre or world pose.
No ground-truth box, depth or mobility annotation is accepted.
"""
from dataclasses import asdict, dataclass
import numpy as np
from .geometry import reproject_q


@dataclass(frozen=True)
class SurfaceConfig:
    inner_fraction: float = 0.6
    min_pixels: int = 12
    min_support: float = 0.1
    min_z_m: float = 1.0
    max_z_m: float = 80.0
    max_relative_iqr: float = 0.35
    mad_multiplier: float = 3.0
    min_tolerance_m: float = 0.25


def mapped_roi(box, mapping, shape, fraction=1.0):
    """Map all interior native pixel centres; deduplicate nearest rectified pixels."""
    box = np.asarray(box, dtype=float)
    mapping = np.asarray(mapping)
    if (box.shape != (4,) or not np.isfinite(box).all() or
            np.any(box[2:] <= box[:2]) or not 0 < fraction <= 1 or
            mapping.ndim != 3 or mapping.shape[2] != 2 or
            len(shape) != 2 or min(shape) <= 0):
        raise ValueError('Valid native xyxy box, H,W,2 map and target shape required')
    centre = (box[:2]+box[2:])/2
    half = (box[2:]-box[:2])*fraction/2
    low = np.maximum(np.ceil(centre-half).astype(int), 0)
    high = np.minimum(np.ceil(centre+half).astype(int), mapping.shape[1::-1])
    if np.any(high <= low):
        return np.empty((0, 2), dtype=int)
    xy = mapping[low[1]:high[1], low[0]:high[0]].reshape(-1, 2)
    inside = (np.isfinite(xy).all(axis=1) & (xy >= 0).all(axis=1)
              & (xy <= [shape[1]-1, shape[0]-1]).all(axis=1))
    return np.unique(np.rint(xy[inside]).astype(int), axis=0)


def associate_surface(box, mapping, disparity, valid, q, *, detection_us,
                      depth_us, config=SurfaceConfig()):
    """Require same-date depth; abstain on sparse or widely dispersed ROI support."""
    if type(detection_us) is not int or type(depth_us) is not int or detection_us != depth_us:
        raise ValueError('Detection and predicted depth must have the same integer timestamp')
    disparity, valid = np.asarray(disparity), np.asarray(valid)
    if disparity.ndim != 2 or valid.shape != disparity.shape or valid.dtype != bool:
        raise ValueError('Matching disparity and boolean validity mask required')
    if not (0 < config.inner_fraction <= 1 and config.min_pixels > 0
            and 0 <= config.min_support <= 1 and 0 < config.min_z_m < config.max_z_m
            and config.max_relative_iqr >= 0 and config.mad_multiplier > 0
            and config.min_tolerance_m > 0):
        raise ValueError('Invalid surface configuration')
    xy = mapped_roi(box, mapping, disparity.shape, config.inner_fraction)
    result = dict(status='INSUFFICIENT_DEPTH', timestamp_us=detection_us,
                  frame='camRect0', meaning='sampled_visible_surface_not_object_centre',
                  xyz_m=None, radial_distance_m=None, mapped_pixels=len(xy),
                  valid_pixels=0, retained_pixels=0, support_fraction=0.0,
                  config=asdict(config))
    if not len(xy):
        result['status'] = 'EMPTY_ROI'
        return result
    d = disparity[xy[:, 1], xy[:, 0]]
    xyz = reproject_q(xy[:, 0], xy[:, 1], d, q)
    keep = (valid[xy[:, 1], xy[:, 0]] & np.isfinite(d) & (d > 0)
            & np.isfinite(xyz).all(axis=1) & (xyz[:, 2] >= config.min_z_m)
            & (xyz[:, 2] <= config.max_z_m))
    z = xyz[keep, 2]
    result.update(valid_pixels=len(z), support_fraction=len(z)/len(xy))
    if len(z) < config.min_pixels or len(z)/len(xy) < config.min_support:
        return result
    median = float(np.median(z)); mad = float(np.median(np.abs(z-median)))
    iqr = float(np.percentile(z, 75)-np.percentile(z, 25))
    result.update(median_z_m=median, mad_z_m=mad, iqr_z_m=iqr)
    if iqr/median > config.max_relative_iqr:
        result['status'] = 'DISPERSED_DEPTH'
        return result
    ids = np.flatnonzero(keep)
    ids = ids[np.abs(xyz[ids, 2]-median) <= max(config.min_tolerance_m, config.mad_multiplier*mad)]
    result['retained_pixels'] = len(ids)
    if len(ids) < config.min_pixels or len(ids)/len(xy) < config.min_support:
        return result
    # A real sampled ray near the median surface, closest to the mapped ROI centre.
    near = ids[np.abs(xyz[ids, 2]-median) <= max(config.min_tolerance_m, 0.02*median)]
    if not len(near):
        near = ids[np.argsort(np.abs(xyz[ids, 2]-median))[:1]]
    centre = np.median(xy, axis=0)
    chosen = int(near[np.argmin(np.sum((xy[near]-centre)**2, axis=1))])
    result.update(status='SURFACE_ESTIMATE', xyz_m=xyz[chosen].tolist(),
                  radial_distance_m=float(np.linalg.norm(xyz[chosen])),
                  rectified_pixel=xy[chosen].tolist(), disparity_px=float(d[chosen]))
    return result


def region_motion_support(box, mapping, shape, points, statuses):
    """Count cached current-time tracks inside mapped box; do not assert mobility."""
    points = np.asarray(points, dtype=float)
    allowed = {'UNKNOWN', 'RESIDUAL_CANDIDATE', 'MODEL_CONSISTENT'}
    if (points.ndim != 2 or points.shape[1:] != (2,) or len(points) != len(statuses)
            or not np.isfinite(points).all() or not set(statuses) <= allowed):
        raise ValueError('Finite Nx2 points and matching known statuses required')
    pixels = mapped_roi(box, mapping, shape)
    mask = np.zeros(shape, dtype=bool)
    mask[pixels[:, 1], pixels[:, 0]] = True
    indices = np.rint(points).astype(int)
    inside = ((indices >= 0).all(axis=1) & (indices < [shape[1], shape[0]]).all(axis=1))
    selected = np.flatnonzero(inside)
    selected = selected[mask[indices[selected, 1], indices[selected, 0]]]
    return {'mobility': 'UNCONFIRMED', 'tracked_points': len(selected),
            **{s: sum(statuses[i] == s for i in selected) for s in sorted(allowed)}}
