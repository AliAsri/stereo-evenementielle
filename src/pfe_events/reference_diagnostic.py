"""Post-hoc box support diagnostics; never feed annotations into the detector."""
import numpy as np


def box_support(boxes, points, depths, statuses, counts, *, margin=0, unavailable=None):
    """Current endpoints versus reference boxes, with shared support explicit.

    Counts are current-window bilinear event mass. Sampled depths belong to
    previous endpoints. An inside point is not certified to lie on the object.
    Margins are sensitivity probes, not a calibrated parallax correction.
    """
    p, z, c = np.asarray(points), np.asarray(depths), np.asarray(counts)
    states = np.asarray(statuses, dtype=str)
    if (p.ndim != 2 or p.shape[1:] != (2,) or z.shape != (len(p),)
            or states.shape != (len(p),) or not np.isfinite(p).all()
            or c.ndim != 2 or not np.isfinite(c).all() or np.any(c < 0)
            or not np.isfinite(margin)
            or not np.isin(states, ['UNKNOWN', 'MODEL_CONSISTENT', 'RESIDUAL_CANDIDATE']).all()):
        raise ValueError('Invalid diagnostic inputs')
    height, width = c.shape
    if (np.any(p < 0) or np.any(p >= [width, height])
            or np.any((states != 'UNKNOWN') & (~np.isfinite(z) | (z <= 0)))):
        raise ValueError('Evaluated tracks require positive depth and in-bounds endpoints')
    regions, membership = [], []
    for box in boxes:
        xy = np.asarray(box['xyxy'], dtype=float)
        if xy.shape != (4,) or not np.isfinite(xy).all() or np.any(xy[2:] <= xy[:2]):
            raise ValueError('Invalid reference box')
        x1, y1, x2, y2 = xy + [-margin, -margin, margin, margin]
        x1, x2 = np.clip([x1, x2], 0, width); y1, y2 = np.clip([y1, y2], 0, height)
        regions.append((x1, y1, x2, y2))
        membership.append((p[:, 0] >= x1) & (p[:, 0] < x2) & (p[:, 1] >= y1) & (p[:, 1] < y2))
    membership = np.asarray(membership, dtype=bool).reshape(len(boxes), len(p))
    owners = membership.sum(axis=0)
    rows = []
    usable = np.isfinite(z) & (z > 0)
    for box, bounds, inside in zip(boxes, regions, membership):
        x1, y1, x2, y2 = bounds
        empty = x2 <= x1 or y2 <= y1
        ix1, iy1, ix2, iy2 = np.ceil(bounds).astype(int)
        patch = c[iy1:iy2, ix1:ix2] if not empty else np.empty((0, 0))
        n = int(inside.sum()); supported = inside & usable
        candidates = inside & (states == 'RESIDUAL_CANDIDATE')
        exclusive_candidates = candidates & (owners == 1)
        evaluated = inside & (states != 'UNKNOWN')
        active = int(np.count_nonzero(patch))
        reason = (unavailable if unavailable else 'EMPTY_ROI' if empty else
                  'NO_CHECKED_TRACKS' if n == 0 else 'NO_USABLE_DEPTH' if not supported.any() else
                  'MODEL_OR_PROJECTION_UNAVAILABLE' if not evaluated.any() else
                  'EXCLUSIVE_RESIDUAL_PRESENT' if exclusive_candidates.any() else
                  'SHARED_RESIDUAL_ONLY' if candidates.any() else 'NO_RESIDUAL_OBSERVED')
        rows.append({'tube_index': box['tube_index'], 'reference_xyxy': box['xyxy'],
                     'margin_px': margin, 'clipped_roi_xyxy': list(map(float, bounds)),
                     'roi_pixels': int(patch.size), 'active_pixels': active,
                     'active_fraction': active/patch.size if patch.size else None,
                     'event_mass': float(patch.sum()), 'checked_tracks': n,
                     'tracks_with_previous_depth': int(supported.sum()),
                     'evaluated_tracks': int(evaluated.sum()),
                     'unknown_tracks': int((inside & (states == 'UNKNOWN')).sum()),
                     'model_consistent_tracks': int((inside & (states == 'MODEL_CONSISTENT')).sum()),
                     'residual_tracks': int(candidates.sum()),
                     'shared_tracks': int((inside & (owners > 1)).sum()),
                     'exclusive_residual_tracks': int(exclusive_candidates.sum()),
                     'diagnostic': reason, 'object_motion_prediction': None})
    outside = owners == 0
    return {'boxes': rows, 'outside_reference_tracks': int(outside.sum()),
            'outside_reference_residual_tracks': int((outside & (states == 'RESIDUAL_CANDIDATE')).sum()),
            'shared_reference_tracks': int((owners > 1).sum()),
            'outside_reference_is_verified_negative': False}
