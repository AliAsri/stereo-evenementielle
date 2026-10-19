"""Depth-assisted apparent motion. Consensus is not proof of a static background.

Inputs are matched rectified pixels and axial depth at the PREVIOUS timestamp.
The returned transform maps previous-camera coordinates into current-camera
coordinates. Reference depth must be explicitly marked as diagnostic/oracle.
"""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class RigidMotionConfig:
    min_points: int = 20
    min_inliers: int = 16
    min_inlier_fraction: float = 0.6
    min_hull_fraction: float = 0.1
    ransac_px: float = 1.5
    residual_px: float = 3.0
    iterations: int = 500
    seed: int = 42  # Legacy metadata only; classic OpenCV PnP owns its fixed RNG.
    max_interval_us: int = 100_000


def estimate_rigid_motion(previous, current, depth_m, intrinsic, *, previous_us,
                          current_us, depth_us, depth_source, frame_size=(640, 480),
                          config=RigidMotionConfig()):
    """Estimate dominant rigid transform; classify only points with usable depth.

    Missing depths yield UNKNOWN, small residuals MODEL_CONSISTENT, large
    residuals RESIDUAL_CANDIDATE. No point is asserted to be moving or static.
    Timestamps/calibration/shape errors raise; insufficient evidence abstains.
    No future frame, depth interpolation or stale-depth reuse is performed.
    """
    c = config
    if type(c.seed) is not int or c.seed != 42:
        raise ValueError('seed is legacy metadata fixed at 42; this OpenCV PnP backend does not expose its RANSAC seed')
    integers = (c.min_points, c.min_inliers, c.iterations, c.seed, c.max_interval_us)
    if (any(type(v) is not int for v in integers) or c.min_points < 6
            or c.min_inliers < 6 or c.min_inliers > c.min_points
            or c.iterations < 1 or not 0 <= c.seed < 2**31 or c.max_interval_us < 1
            or not 0 < c.min_inlier_fraction <= 1 or not 0 < c.min_hull_fraction <= 1
            or not np.isfinite([c.ransac_px, c.residual_px]).all()
            or not 0 < c.ransac_px < c.residual_px):
        raise ValueError('Invalid rigid motion configuration')
    if (any(type(t) is not int for t in (previous_us, current_us, depth_us))
            or not 0 < current_us - previous_us <= c.max_interval_us
            or depth_us != previous_us):
        raise ValueError('Depth must match previous time; positive bounded interval required')
    if depth_source not in ('predicted', 'synthetic_reference', 'dataset_reference'):
        raise ValueError('Explicit depth provenance required')
    if len(frame_size) != 2 or any(type(v) is not int or v <= 0 for v in frame_size):
        raise ValueError('Positive integer frame size required')
    width, height = frame_size
    p, q = np.asarray(previous, dtype=float), np.asarray(current, dtype=float)
    z, k = np.asarray(depth_m, dtype=float), np.asarray(intrinsic, dtype=float)
    if (p.ndim != 2 or p.shape[1:] != (2,) or q.shape != p.shape or z.shape != (len(p),)
            or not np.isfinite(p).all() or not np.isfinite(q).all()
            or np.any(p < 0) or np.any(q < 0) or np.any(p >= frame_size) or np.any(q >= frame_size)):
        raise ValueError('Matching in-bounds rectified Nx2 pixels and N depths required')
    if (k.shape != (3, 3) or not np.isfinite(k).all() or k[0, 0] <= 0 or k[1, 1] <= 0
            or not np.allclose(k, [[k[0, 0], 0, k[0, 2]], [0, k[1, 1], k[1, 2]], [0, 0, 1]])):
        raise ValueError('Rectified pinhole intrinsic matrix required')
    usable = np.isfinite(z) & (z > 0)
    ids = np.flatnonzero(usable)
    out = dict(valid=False, status='INSUFFICIENT_DEPTH_SUPPORT',
               previous_us=previous_us, current_us=current_us, depth_us=depth_us,
               depth_source=depth_source, oracle=depth_source != 'predicted',
               tracks=len(p), depth_points=len(ids), evaluated_points=0,
               inliers=0, inlier_fraction=0., hull_fraction=0.,
               transform_previous_to_current=None,
               residual_px=[None] * len(p), predicted_pixels=[None] * len(p),
               point_status=['UNKNOWN'] * len(p),
               claim='DOMINANT_RIGID_MODEL_NOT_VERIFIED_CAMERA_POSE_OR_OBJECT_MOTION')
    if len(ids) < c.min_points:
        return out
    xyz = np.column_stack(((p[ids, 0] - k[0, 2]) / k[0, 0] * z[ids],
                           (p[ids, 1] - k[1, 2]) / k[1, 1] * z[ids], z[ids]))
    if not np.isfinite(xyz).all():
        raise ValueError('Nonfinite backprojection')
    singular = np.linalg.svd(xyz - xyz.mean(axis=0), compute_uv=False)
    if singular[0] <= 0 or singular[1] / singular[0] < 1e-4:
        out['status'] = 'DEGENERATE_3D_SUPPORT'
        return out
    # OpenCV 4.14 classic RANSACPointSetRegistrator uses a local RNG(-1).
    # setRNGSeed would reset unrelated global randomness without controlling it.
    try:
        ok, rotation, translation, inliers = cv2.solvePnPRansac(
            xyz, np.ascontiguousarray(q[ids]), k, None,
            iterationsCount=c.iterations, reprojectionError=c.ransac_px,
            confidence=.999, flags=cv2.SOLVEPNP_EPNP)
        if not ok or inliers is None or len(inliers) < 6:
            out['status'] = 'POSE_FIT_FAILED'
            return out
        fit_ids = inliers.ravel()
        rotation, translation = cv2.solvePnPRefineLM(
            xyz[fit_ids], np.ascontiguousarray(q[ids][fit_ids]), k, None, rotation, translation)
        matrix, _ = cv2.Rodrigues(rotation)
    except cv2.error:
        out['status'] = 'POSE_FIT_FAILED'
        return out
    if not np.isfinite(matrix).all() or not np.isfinite(translation).all():
        out['status'] = 'NONFINITE_POSE'
        return out
    transformed = xyz @ matrix.T + translation.ravel()
    front = np.isfinite(transformed).all(axis=1) & (transformed[:, 2] > 1e-6)
    projected = np.full((len(ids), 2), np.nan)
    projected[front] = (transformed[front] @ k.T)[:, :2] / transformed[front, 2, None]
    front &= np.isfinite(projected).all(axis=1)
    error = np.linalg.norm(q[ids] - projected, axis=1)
    support = front & (error <= c.ransac_px)
    count = int(support.sum())
    hull = (float(cv2.contourArea(cv2.convexHull(p[ids][support].astype(np.float32))))
            / (width * height)) if count >= 3 else 0.
    out.update(inliers=count, inlier_fraction=count / len(ids), hull_fraction=hull)
    if count < c.min_inliers or count / len(ids) < c.min_inlier_fraction or hull < c.min_hull_fraction:
        out['status'] = 'INSUFFICIENT_RIGID_SUPPORT'
        return out
    transform = np.eye(4)
    transform[:3, :3], transform[:3, 3] = matrix, translation.ravel()
    for local in np.flatnonzero(front):
        index = int(ids[local])
        out['residual_px'][index] = float(error[local])
        out['predicted_pixels'][index] = projected[local].tolist()
        out['point_status'][index] = 'RESIDUAL_CANDIDATE' if error[local] > c.residual_px else 'MODEL_CONSISTENT'
    out.update(valid=True, status='VALID_DOMINANT_RIGID_MODEL',
               evaluated_points=int(front.sum()), transform_previous_to_current=transform.tolist())
    return out
