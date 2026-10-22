"""Associate a native YOLO box with a predicted rectified visible surface.

This estimates a sampled surface point, never an object centre or world pose.
No ground-truth box, depth or mobility annotation is accepted.
"""
from dataclasses import asdict, dataclass
import numpy as np
from .geometry import reproject_q
from .stereo import StereoConfig
from .rectified_tracking import sample_disparity_depth


def _finite_numbers(values):
    return all(isinstance(value, (int, float, np.integer, np.floating))
               and not isinstance(value, (bool, np.bool_)) and np.isfinite(value)
               for value in values)


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

    def __post_init__(self):
        values = (self.inner_fraction, self.min_support, self.min_z_m, self.max_z_m,
                  self.max_relative_iqr, self.mad_multiplier, self.min_tolerance_m)
        if (type(self.min_pixels) is not int or self.min_pixels < 1
                or not _finite_numbers(values)
                or not 0 < self.inner_fraction <= 1 or not 0 <= self.min_support <= 1
                or not 0 < self.min_z_m < self.max_z_m or self.max_relative_iqr < 0
                or self.mad_multiplier <= 0 or self.min_tolerance_m <= 0):
            raise ValueError('Finite surface thresholds and positive integer pixel support required')


@dataclass(frozen=True)
class ObjectMotionConfig:
    """Engineering decision rules, not fitted or independently validated."""
    min_tracks: int = 3
    min_evaluated_fraction: float = 0.8
    min_agreement: float = 0.8

    def __post_init__(self):
        if (type(self.min_tracks) is not int or self.min_tracks < 3
                or not _finite_numbers((self.min_evaluated_fraction, self.min_agreement))
                or not 0 < self.min_evaluated_fraction <= 1
                or not .5 < self.min_agreement <= 1):
            raise ValueError('Positive support and strict majority agreement required')


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
    pixels = np.rint(xy[inside]).astype(int)
    # Scalar integer sorting avoids the expensive structured (x,y) row sort.
    # Encode x first to preserve np.unique(axis=0)'s lexicographic order: the
    # downstream nearest-surface tie break depends on this exact ordering.
    height = int(np.ceil(shape[0]))
    keys = np.unique(pixels[:, 0]*height + pixels[:, 1])
    return np.column_stack((keys//height, keys%height))


def _supported_depth_layers(z, mapped_pixels, config):
    """Describe separated depth groups; no object identity is assigned."""
    ordered = np.sort(z)
    gaps = np.diff(ordered)
    boundaries = np.flatnonzero(gaps > np.maximum(
        config.min_tolerance_m, config.max_relative_iqr*ordered[:-1])) + 1
    layers = []
    for layer in np.split(ordered, boundaries):
        if len(layer) < config.min_pixels:
            continue
        centre_z = float(np.median(layer))
        layer_iqr = float(np.percentile(layer, 75)-np.percentile(layer, 25))
        if layer_iqr/centre_z <= config.max_relative_iqr:
            layers.append(dict(pixels=len(layer), median_z_m=centre_z,
                               iqr_z_m=layer_iqr,
                               support_fraction=len(layer)/mapped_pixels))
    return layers


def associate_surface(box, mapping, disparity, valid, q, *, detection_us,
                      depth_us, config=SurfaceConfig(), stereo_config=StereoConfig()):
    """Require same-date depth; abstain on sparse, layered or dispersed support.

    Depth layers have no semantic identity: the nearer one may be an occluder.
    A single surviving layer still does not certify ownership by the detection.
    """
    if type(detection_us) is not int or type(depth_us) is not int or detection_us != depth_us:
        raise ValueError('Detection and predicted depth must have the same integer timestamp')
    disparity, valid = np.asarray(disparity), np.asarray(valid)
    if disparity.ndim != 2 or valid.shape != disparity.shape or valid.dtype != bool:
        raise ValueError('Matching disparity and boolean validity mask required')
    search_range = stereo_config.depth_range(q)
    effective_min = max(config.min_z_m, search_range['min_z_m'])
    xy = mapped_roi(box, mapping, disparity.shape, config.inner_fraction)
    result = dict(status='INSUFFICIENT_DEPTH', timestamp_us=detection_us,
                  frame='camRect0', meaning='sampled_visible_surface_not_object_centre',
                  xyz_m=None, radial_distance_m=None, mapped_pixels=len(xy),
                  valid_pixels=0, retained_pixels=0, support_fraction=0.0,
                  config=asdict(config),
                  depth_range={**search_range, 'surface_filter_min_z_m':config.min_z_m,
                               'effective_min_z_m':effective_min, 'max_z_m':config.max_z_m},
                  search_range_rejected_pixels=0,
                  depth_absence_cause='UNDETERMINED')
    if not len(xy):
        result['status'] = 'EMPTY_ROI'
        return result
    d = disparity[xy[:, 1], xy[:, 0]]
    xyz = reproject_q(xy[:, 0], xy[:, 1], d, q)
    candidate = (valid[xy[:, 1], xy[:, 0]] & np.isfinite(d) & (d > 0)
                 & np.isfinite(xyz).all(axis=1))
    in_search = d <= search_range['max_disparity_px']
    rejected = int((candidate & ~in_search).sum())
    result['search_range_rejected_pixels'] = rejected
    # d<=D-1 enforces the near bound without round-off at Z=f*B/(D-1).
    keep = (candidate & in_search & (xyz[:, 2] >= config.min_z_m)
            & (xyz[:, 2] <= config.max_z_m))
    z = xyz[keep, 2]
    result.update(valid_pixels=len(z), support_fraction=len(z)/len(xy))
    if len(z) < config.min_pixels or len(z)/len(xy) < config.min_support:
        if rejected and rejected == int(candidate.sum()):
            # Invalid supplied depths, not proof that the physical object is near.
            result['status'] = 'OUTSIDE_STEREO_SEARCH_RANGE'
        return result
    median = float(np.median(z)); mad = float(np.median(np.abs(z-median)))
    iqr = float(np.percentile(z, 75)-np.percentile(z, 25))
    result.update(median_z_m=median, mad_z_m=mad, iqr_z_m=iqr)
    # Inspect all valid depths BEFORE MAD removes a minority as outliers.
    # Split only at gaps beyond both the existing absolute tolerance and
    # relative dispersion allowance. This is a conservative ambiguity check,
    # not foreground selection or a learned segmentation of the object.
    layers = _supported_depth_layers(z, len(xy), config)
    if len(layers) > 1:
        result.update(status='AMBIGUOUS_DEPTH_LAYERS', depth_layers=layers,
                      ambiguity='OBJECT_BACKGROUND_OR_OCCLUDER_UNRESOLVED')
        return result
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
                  rectified_pixel=xy[chosen].tolist(), disparity_px=float(d[chosen]),
                  depth_absence_cause=None)
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


def object_motion_decision(box, mapping, disparity, valid, q, points, model, surface,
                           *, detection_us, depth_us, config=ObjectMotionConfig(),
                           stereo_config=StereoConfig()):
    """Three conditional states for this detection over the model's interval.

    Only current depth is sampled. No previous-depth vector or reference label
    is accepted. Agreement with a dominant rigid model is not physical proof
    of an immobile object, and this function does not track object identities.
    """
    stamps = (detection_us, depth_us, surface['timestamp_us'], model['current_us'])
    if any(type(t) is not int for t in stamps) or len(set(stamps)) != 1:
        raise ValueError('Detection, surface, current tracks and depth dates must match')
    if surface['frame'] != 'camRect0':
        raise ValueError('Current surface and tracked points must use camRect0')
    if type(model['previous_us']) is not int or not 0 < detection_us-model['previous_us'] <= 100000:
        raise ValueError('Positive bounded model interval required')
    disparity, valid = np.asarray(disparity), np.asarray(valid)
    if disparity.ndim != 2 or valid.shape != disparity.shape or valid.dtype != bool:
        raise ValueError('Matching current disparity and boolean validity required')
    points = np.asarray(points, dtype=float)
    statuses = model['point_status']
    raw = region_motion_support(box, mapping, disparity.shape, points, statuses)
    result = dict(mobility='INDETERMINATE', physical_mobility='UNCONFIRMED',
                  decision_scope='CONDITIONAL_ON_DOMINANT_MODEL_AND_SURFACE',
                  timestamp_us=detection_us, previous_us=model['previous_us'],
                  depth_us=depth_us, config=asdict(config), roi_support=raw,
                  tracked_points=0, evaluated_points=0, evaluated_fraction=0.,
                  UNKNOWN=0, RESIDUAL_CANDIDATE=0, MODEL_CONSISTENT=0,
                  surface_track_indices=[], reason='SURFACE_UNAVAILABLE')
    if surface['status'] != 'SURFACE_ESTIMATE' or surface['xyz_m'] is None:
        return result
    if not model['valid'] or model['transform_previous_to_current'] is None:
        result['reason'] = 'RIGID_MODEL_UNAVAILABLE'
        return result
    sc = surface['config']
    centre_z, mad = surface['median_z_m'], surface['mad_z_m']
    if not np.isfinite([centre_z, mad]).all() or centre_z <= 0 or mad < 0:
        raise ValueError('Finite positive surface depth and nonnegative dispersion required')
    tolerance = max(sc['min_tolerance_m'], sc['mad_multiplier']*mad)
    limit = stereo_config.depth_range(q)
    current_valid = (valid & np.isfinite(disparity) & (disparity > 0)
                     & (disparity <= limit['max_disparity_px']))
    # The sampler excludes repeated rounded pixels and preserves missing depths.
    z, sampling = sample_disparity_depth(points, disparity, current_valid, q)
    pixels = np.asarray(sampling['sampled_pixels'], dtype=int).reshape(-1, 2)
    roi = mapped_roi(box, mapping, disparity.shape, sc['inner_fraction'])
    mask = np.zeros(disparity.shape, bool)
    mask[roi[:,1], roi[:,0]] = True
    eligible = np.flatnonzero(np.isfinite(z) & (z >= sc['min_z_m']) & (z <= sc['max_z_m'])
                              & (np.abs(z-centre_z) <= tolerance))
    eligible = eligible[mask[pixels[eligible,1], pixels[eligible,0]]]
    votes = np.asarray(statuses)[eligible]
    counts = {name:int((votes == name).sum()) for name in
              ('UNKNOWN', 'RESIDUAL_CANDIDATE', 'MODEL_CONSISTENT')}
    n = len(eligible); evaluated = n-counts['UNKNOWN']
    result.update(**counts, tracked_points=n, evaluated_points=evaluated,
                  evaluated_fraction=evaluated/n if n else 0.,
                  surface_track_indices=eligible.tolist(), reason='INSUFFICIENT_SURFACE_TRACKS')
    if evaluated < config.min_tracks or result['evaluated_fraction'] < config.min_evaluated_fraction:
        return result
    if counts['RESIDUAL_CANDIDATE']/evaluated >= config.min_agreement:
        result.update(mobility='MOBILE', reason='RESIDUAL_AGREEMENT_WITH_SURFACE_SUPPORT')
    elif counts['MODEL_CONSISTENT']/evaluated >= config.min_agreement:
        result.update(mobility='IMMOBILE', reason='DOMINANT_MODEL_AGREEMENT_WITH_SURFACE_SUPPORT')
    else:
        result['reason'] = 'MIXED_SURFACE_EVIDENCE'
    return result
