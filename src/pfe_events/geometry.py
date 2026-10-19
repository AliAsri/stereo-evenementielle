"""Geometry checks and explicit reference-disparity decoding; no depth predictor."""

from pathlib import Path

import numpy as np
import yaml


def audit_calibration(path: str | Path, *, require_canonical=False):
    """Validate the DSEC event pair and return measured calibration parameters."""
    calibration = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    extrinsics = calibration["extrinsics"]
    chain = np.eye(4)
    for key in ("T_10", "T_21", "T_32"):
        transform = np.asarray(extrinsics[key], dtype=np.float64)
        if transform.shape != (4, 4) or not np.isfinite(transform).all() or not np.allclose(transform[3], [0, 0, 0, 1]):
            raise ValueError(f"Invalid transform {key}")
        rotation = transform[:3, :3]
        if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-5) or not np.isclose(np.linalg.det(rotation), 1, atol=1e-5):
            raise ValueError(f"Invalid rotation {key}")
        chain = transform @ chain
    q = np.asarray(calibration["disparity_to_depth"]["cams_03"], dtype=np.float64)
    left = calibration["intrinsics"]["camRect0"]
    right = calibration["intrinsics"]["camRect3"]
    for camera in (left, right):
        intrinsics = np.asarray(camera["camera_matrix"], dtype=float)
        resolution = np.asarray(camera["resolution"])
        if (intrinsics.shape != (4,) or not np.isfinite(intrinsics).all()
                or np.any(intrinsics[:2] <= 0)):
            raise ValueError("Finite positive focal lengths and finite principal point required")
        if (resolution.shape != (2,) or resolution.dtype.kind not in 'iu'
                or np.any(resolution <= 0)):
            raise ValueError("Positive integer camera resolution required")
    if left['resolution'] != right['resolution']:
        raise ValueError("Rectified event cameras must have the same resolution")
    fx, fy, cx, cy = left["camera_matrix"]
    if q.shape != (4, 4) or not np.isfinite(q).all() or q[3, 2] <= 0:
        raise ValueError("Unsupported or invalid event Q matrix")
    baseline = float(np.linalg.norm(chain[:3, 3]))
    if not np.isfinite(baseline) or baseline <= 0:
        raise ValueError("Positive finite stereo baseline required")
    baseline_q = float(1 / q[3, 2])
    if not np.isclose(baseline, baseline_q, rtol=1e-5):
        raise ValueError("Extrinsics and Q imply different baselines")
    expected_q = np.array([[1, 0, 0, -cx], [0, 1, 0, -cy], [0, 0, 0, fx], [0, 0, 1/baseline, 0]], dtype=float)
    canonical = bool(np.allclose(q, expected_q) and np.isclose(fx, fy) and np.allclose(left["camera_matrix"], right["camera_matrix"]))
    if require_canonical and not canonical:
        raise ValueError("Unsupported event geometry: canonical Q and equal rectified intrinsics required")
    return {"fx_px": fx, "fy_px": fy, "cx_px": cx, "cy_px": cy, "baseline_m": baseline, "baseline_from_q_m": baseline_q, "canonical_equal_intrinsics": canonical, "q": q.tolist(), "resolution": left["resolution"]}


def decode_dsec_disparity(encoded):
    """Decode integer PNG storage; return pixels and valid mask, invalid values NaN."""
    encoded = np.asarray(encoded)
    if encoded.ndim != 2 or encoded.dtype.kind not in "ui" or np.any(encoded < 0) or np.any(encoded > 65535):
        raise ValueError("Expected a 2D unsigned-16-bit-compatible integer image")
    valid = encoded > 0
    disparity = encoded.astype(np.float64) / 256.0
    disparity[~valid] = np.nan
    return disparity, valid


def reproject_q(u, v, disparity, q):
    """Broadcast pixel/disparity arrays to [...,3] XYZ; invalid or behind -> NaN."""
    q = np.asarray(q, dtype=np.float64)
    if q.shape != (4, 4) or not np.isfinite(q).all():
        raise ValueError("Q must be a finite 4x4 matrix")
    u, v, disparity = np.broadcast_arrays(np.asarray(u, dtype=float), np.asarray(v, dtype=float), np.asarray(disparity, dtype=float))
    coordinates = np.stack([u, v, disparity, np.ones_like(u)], axis=-1)
    homogeneous = coordinates @ q.T
    valid = np.isfinite(coordinates).all(axis=-1) & (np.abs(homogeneous[..., 3]) > 1e-12)
    xyz = np.full((*u.shape, 3), np.nan)
    np.divide(homogeneous[..., :3], homogeneous[..., 3, None], out=xyz, where=valid[..., None])
    xyz[~np.isfinite(xyz).all(axis=-1) | (xyz[..., 2] <= 0)] = np.nan
    return xyz
