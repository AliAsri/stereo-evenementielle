"""Spatially balanced sampling for the existing rigid estimator.

No semantic/reference mask, temporal smoothing, or verified-camera-pose claim.
Unselected points are still evaluated using their original predicted depth.
"""
import numpy as np
from .rigid_motion import estimate_rigid_motion, RigidMotionConfig


def balanced_indices(points, depth, fb_error, frame_size=(640, 480)):
    """Fixed 8x6 grid, at most four lowest-FB-error points per cell."""
    p, z, fb = np.asarray(points), np.asarray(depth), np.asarray(fb_error)
    if (p.ndim != 2 or p.shape[1:] != (2,) or z.shape != (len(p),)
            or fb.shape != (len(p),) or not np.isfinite(p).all()
            or not np.isfinite(fb).all() or np.any(fb < 0)
            or len(frame_size) != 2 or any(type(v) is not int or v <= 0 for v in frame_size)
            or np.any(p < 0) or np.any(p >= frame_size)):
        raise ValueError('Finite in-bounds points, depths and nonnegative FB errors required')
    cells = np.floor(p / np.asarray(frame_size) * [8, 6]).astype(int)
    cell_id = cells[:, 1]*8 + cells[:, 0]
    selected = []
    for cell in range(48):
        ids = np.flatnonzero((cell_id == cell) & np.isfinite(z) & (z > 0))
        selected.extend(ids[np.lexsort((ids, fb[ids]))][:4])
    return np.sort(np.asarray(selected, dtype=int))


def estimate_balanced_motion(previous, current, depth_m, intrinsic, fb_error, *,
                             previous_us, current_us, depth_us, depth_source,
                             frame_size=(640, 480), config=RigidMotionConfig()):
    p, q = np.asarray(previous, dtype=float), np.asarray(current, dtype=float)
    z, k = np.asarray(depth_m, dtype=float), np.asarray(intrinsic, dtype=float)
    ids = balanced_indices(p, z, fb_error, frame_size)
    fit_depth = np.full(z.shape, np.nan); fit_depth[ids] = z[ids]
    result = estimate_rigid_motion(p, q, fit_depth, k, previous_us=previous_us,
        current_us=current_us, depth_us=depth_us, depth_source=depth_source,
        frame_size=frame_size, config=config)
    result['sampling'] = {'grid': [8, 6], 'max_per_cell': 4,
                          'order': 'lowest_forward_backward_error_then_input_index',
                          'selected_indices': ids.tolist(),
                          'available_depth_points': int((np.isfinite(z) & (z > 0)).sum())}
    # Original inliers/fraction/hull describe the fit subset, never all points.
    result['support_scope'] = 'SPATIALLY_BALANCED_FIT_SUBSET'
    if not result['valid']:
        return result
    usable = np.flatnonzero(np.isfinite(z) & (z > 0))
    xyz = np.column_stack(((p[usable, 0]-k[0, 2])/k[0, 0]*z[usable],
                           (p[usable, 1]-k[1, 2])/k[1, 1]*z[usable], z[usable]))
    transform = np.asarray(result['transform_previous_to_current'])
    mapped = xyz @ transform[:3, :3].T + transform[:3, 3]
    front = np.isfinite(mapped).all(axis=1) & (mapped[:, 2] > 1e-6)
    projected = np.full((len(usable), 2), np.nan)
    projected[front] = (mapped[front] @ k.T)[:, :2] / mapped[front, 2, None]
    front &= np.isfinite(projected).all(axis=1)
    result.update(point_status=['UNKNOWN']*len(p), residual_px=[None]*len(p),
                  predicted_pixels=[None]*len(p), evaluated_points=int(front.sum()))
    for local in np.flatnonzero(front):
        index = int(usable[local]); error = float(np.linalg.norm(q[index]-projected[local]))
        result['residual_px'][index] = error
        result['predicted_pixels'][index] = projected[local].tolist()
        result['point_status'][index] = ('RESIDUAL_CANDIDATE' if error > config.residual_px else 'MODEL_CONSISTENT')
    result['status'] = 'VALID_SPATIALLY_BALANCED_RIGID_MODEL'
    return result
