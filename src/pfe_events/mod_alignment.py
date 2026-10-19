"""Image-based DSEC-MOD alignment checks, independent of mobility predictions."""
import cv2
import numpy as np


def _intrinsic(values):
    values = np.asarray(values, dtype=float)
    if values.shape != (4,) or not np.isfinite(values).all() or np.any(values[:2] <= 0):
        raise ValueError('Invalid pinhole intrinsics')
    fx, fy, cx, cy = values
    return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.]])


def _rotation(value):
    matrix = np.asarray(value, dtype=float)
    if (matrix.shape != (3, 3) or not np.isfinite(matrix).all()
            or not np.allclose(matrix.T @ matrix, np.eye(3), atol=1e-6)
            or not np.isclose(np.linalg.det(matrix), 1, atol=1e-6)):
        raise ValueError('Invalid rotation')
    return matrix


def rgb_to_event_homography(calibration):
    """Rectified RGB1 -> rectified event0, rotation-only (infinite depth).

    Translation between the physical cameras is intentionally NOT represented.
    This describes an image warp; it is not exact finite-depth reprojection.
    """
    intrinsics, extrinsics = calibration['intrinsics'], calibration['extrinsics']
    transform = np.asarray(extrinsics['T_10'], dtype=float)
    if (transform.shape != (4, 4) or not np.isfinite(transform).all()
            or not np.allclose(transform[3], [0, 0, 0, 1])):
        raise ValueError('Invalid T_10')
    r10 = _rotation(transform[:3, :3])
    r0 = _rotation(extrinsics['R_rect0'])
    r1 = _rotation(extrinsics['R_rect1'])
    k0 = _intrinsic(intrinsics['camRect0']['camera_matrix'])
    k1 = _intrinsic(intrinsics['camRect1']['camera_matrix'])
    h = k0 @ r0 @ r10.T @ r1.T @ np.linalg.inv(k1)
    if abs(h[2, 2]) < 1e-12:
        raise ValueError('Degenerate homography normalization')
    return h / h[2, 2]


def parallax_mask_reachability(points, mask, calibration):
    """Conservative geometric intersection, NOT mobility labels or a depth warp.

    An event-rectified point q at axial depth Z maps into the rotation-warped
    RGB grid as q + d/(Z+v_z), with v=R_rect0 R_10.T t_10 and
    d=(fx*v_x-(q_x-cx)*v_z, fy*v_y-(q_y-cy)*v_z).
    Check every Z>0 (except the projective singularity) against closed unit
    squares of positive mask pixels. Closed edges deliberately over-admit
    boundary contacts. RGB visibility/occlusion is not certified; a possible
    intersection is only necessary, and a miss is conditional on exact masks,
    calibration and the instantaneous pinhole model.
    """
    rgb_to_event_homography(calibration)  # Validate the same camera conventions.
    points = np.asarray(points,dtype=float)
    if (points.ndim != 2 or points.shape[1:] != (2,) or not np.isfinite(points).all()
            or mask.ndim != 2 or mask.dtype != bool or min(mask.shape) <= 0):
        raise ValueError('Finite Nx2 rectified pixels and a nonempty boolean mask required')
    ext = calibration['extrinsics']
    t = np.asarray(ext['T_10'],float)
    v = np.asarray(ext['R_rect0'],float) @ t[:3,:3].T @ t[:3,3]
    fx,fy,cx,cy = calibration['intrinsics']['camRect0']['camera_matrix']
    directions = np.array([fx,fy])*v[:2] - (points-[cx,cy])*v[2]
    yy,xx = np.nonzero(mask)
    centres = np.column_stack((xx,yy)).astype(float)
    branches = [(0.,1/v[2] if v[2]>0 else np.inf)]
    if v[2]<0: branches.append((-np.inf,1/v[2]))
    rows = []
    for point,direction in zip(points,directions):
        lower,upper = np.full(len(centres),-np.inf),np.full(len(centres),np.inf)
        for axis in range(2):
            low,high = centres[:,axis]-.5,centres[:,axis]+.5
            if direction[axis] == 0:
                outside = (point[axis]<low)|(point[axis]>high)
                lower[outside],upper[outside] = np.inf,-np.inf
            else:
                a,b = (low-point[axis])/direction[axis],(high-point[axis])/direction[axis]
                lower,upper = np.maximum(lower,np.minimum(a,b)),np.minimum(upper,np.maximum(a,b))
        hit = np.zeros(len(centres),bool)
        max_depths = []
        unbounded = False
        for start,stop in branches:
            lo,hi = np.maximum(lower,start),np.minimum(upper,stop)
            valid = (lo<=hi)&(hi>start)&(lo<stop)
            hit |= valid
            for a in lo[valid]:
                if a == 0:
                    unbounded = True
                else:
                    max_depths.append(float(-v[2] if np.isneginf(a) else 1/a-v[2]))
        distance = (np.linalg.norm(np.maximum(np.abs(centres-point)-.5,0),axis=1).min()
                    if len(centres) else None)
        rows.append(dict(possible_positive_pixels=int(hit.sum()),
            possible=bool(hit.any()),max_compatible_depth_m=(None if unbounded or not max_depths else max(max_depths)),
            unbounded_max_depth=unbounded,distance_to_positive_pixel_squares_px=None if distance is None else float(distance),
            direction_px_m=direction.tolist()))
    return dict(effective_translation_m=v.tolist(),points=rows,
                interpretation='Conservative spatial compatibility only; no observed depth, visibility or mobility guarantee')


def compare_projected_rgb(original, reference, homography):
    """Compare image intensities on valid projected support; no fitted geometry."""
    if (original.dtype != np.uint8 or reference.dtype != np.uint8
            or original.ndim != 3 or reference.ndim != 3
            or original.shape[2] != 3 or reference.shape[2] != 3):
        raise ValueError('Expected uint8 three-channel images in the same channel order')
    h = np.asarray(homography, dtype=float)
    if h.shape != (3, 3) or not np.isfinite(h).all() or abs(np.linalg.det(h)) < 1e-12:
        raise ValueError('Invalid homography')
    height, width = reference.shape[:2]
    warped = cv2.warpPerspective(original, h, (width, height), flags=cv2.INTER_LINEAR)
    support = cv2.warpPerspective(np.ones(original.shape[:2], np.float32), h,
                                  (width, height), flags=cv2.INTER_LINEAR) >= .999
    if not support.any():
        raise ValueError('No common image support')
    errors = np.abs(warped.astype(np.int16) - reference.astype(np.int16))[support]
    return {'mae_8bit': float(errors.mean()), 'p99_abs_error_8bit': float(np.percentile(errors, 99)),
            'fraction_channels_equal': float(np.mean(errors == 0)),
            'support_pixels': int(support.sum()), 'support_fraction': float(support.mean())}, warped


def select_verified_frame(scores, *, max_mae=1., min_margin=1.):
    """Strict photometric audit gate, not a detector-quality threshold."""
    if (len(scores) < 2 or len({s['dsec_index'] for s in scores}) != len(scores)
            or any(not np.isfinite(s['mae_8bit']) or s['mae_8bit'] < 0 for s in scores)):
        raise ValueError('At least two distinct finite candidate scores required')
    ordered = sorted(scores, key=lambda s: s['mae_8bit'])
    best, runner = ordered[:2]
    margin = runner['mae_8bit']-best['mae_8bit']
    if best['mae_8bit'] > max_mae or margin < min_margin:
        raise ValueError('Ambiguous or poorly reproduced reference image')
    return {'dsec_index': best['dsec_index'], 'mae_8bit': best['mae_8bit'],
            'runner_up_mae_8bit': runner['mae_8bit'], 'margin_8bit': margin}


def verified_timestamp(image_timestamps, exposures, index):
    """Keep the official unified clock and the left exposure interval separate."""
    times, exposure = np.asarray(image_timestamps), np.asarray(exposures)
    if (times.ndim != 1 or times.dtype.kind not in 'iu' or len(times) < 2
            or np.any(np.diff(times.astype(np.int64)) <= 0)
            or exposure.shape != (len(times), 2) or exposure.dtype.kind not in 'iu'
            or np.any(exposure[:, 1] <= exposure[:, 0])
            or not isinstance(index, (int, np.integer)) or not 0 <= index < len(times)):
        raise ValueError('Invalid timestamp/exposure mapping')
    start, end = map(int, exposure[index])
    return {'timestamp_us': int(times[index]), 'left_exposure_start_us': start,
            'left_exposure_end_us': end, 'exposure_duration_us': end-start,
            'unified_minus_left_midpoint_us': float(times[index]-(start+end)/2)}
