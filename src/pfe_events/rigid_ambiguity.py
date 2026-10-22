"""Conservative two-model abstention; neither model is verified camera motion.

The frozen defaults and two-fit limit match the isolated synthetic protocol.
Raw models remain available for audit, never as a fallback for an ambiguous final.
"""
import copy
import numpy as np
from .rigid_motion import estimate_rigid_motion, RigidMotionConfig


def project_transform(xyz, intrinsic, transform):
    t = np.asarray(transform)
    moved = xyz @ t[:3, :3].T + t[:3, 3]
    good = np.isfinite(moved).all(axis=1) & (moved[:, 2] > 1e-6)
    pixels = np.full((len(xyz), 2), np.nan)
    homogeneous = moved[good] @ intrinsic.T
    pixels[good] = homogeneous[:, :2] / homogeneous[:, 2, None]
    good &= np.isfinite(pixels).all(axis=1)
    return pixels, good


def guarded_rigid_motion(previous, current, depth_m, intrinsic, *, previous_us, current_us,
             depth_us, depth_source):
    """At most two fits; accepts observations only, never reference labels/pose."""
    config = RigidMotionConfig()
    p, q, z, k = (np.asarray(a) for a in (previous, current, depth_m, intrinsic))
    times = dict(previous_us=previous_us, current_us=current_us,
                 depth_us=depth_us, depth_source=depth_source)
    primary = estimate_rigid_motion(p, q, z, k, **times)
    out = dict(primary=primary, secondary=None, secondary_indices=[],
               secondary_denominator=0, common_projectable_points=0,
               median_model_separation_px=None, fits=1,
               ambiguity='AMBIGUITY_NOT_DETECTED', reason='PRIMARY_REJECTED',
               final=copy.deepcopy(primary))
    if not primary['valid']:
        return out
    residual = np.array([np.nan if e is None else e for e in primary['residual_px']])
    ids = np.flatnonzero(np.isfinite(z) & (z > 0) & np.isfinite(residual)
                        & (residual > config.residual_px))
    out.update(secondary_indices=ids.tolist(), secondary_denominator=len(ids),
               reason='SECONDARY_TOO_SMALL')
    if len(ids) < config.min_points:
        return out
    secondary = estimate_rigid_motion(p[ids], q[ids], z[ids], k, **times)
    out.update(secondary=secondary, fits=2, reason='SECONDARY_REJECTED')
    if not secondary['valid']:
        return out
    usable = np.isfinite(z) & (z > 0)
    xyz = np.column_stack(((p[usable, 0]-k[0, 2])/k[0, 0]*z[usable],
                           (p[usable, 1]-k[1, 2])/k[1, 1]*z[usable], z[usable]))
    a, good_a = project_transform(xyz, k, primary['transform_previous_to_current'])
    b, good_b = project_transform(xyz, k, secondary['transform_previous_to_current'])
    common = good_a & good_b
    out.update(common_projectable_points=int(common.sum()), reason='TOO_FEW_COMMON_POINTS')
    if common.sum() < config.min_points:
        return out
    separation = float(np.median(np.linalg.norm(a[common]-b[common], axis=1)))
    out.update(median_model_separation_px=separation, reason='MODELS_NOT_DISTINCT')
    if separation > config.residual_px:
        out.update(ambiguity='AMBIGUOUS_RIGID_MODELS', reason='COMPETING_SUPPORTED_MODELS')
        out['final'].update(valid=False, status='AMBIGUOUS_RIGID_MODELS',
                            transform_previous_to_current=None, evaluated_points=0,
                            residual_px=[None]*len(p), predicted_pixels=[None]*len(p),
                            point_status=['UNKNOWN']*len(p))
    return out
