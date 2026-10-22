"""CPU stereo baseline with explicit fixed-point decoding and abstention."""

from dataclasses import asdict, dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class StereoConfig:
    num_disparities: int = 96
    block_size: int = 5
    uniqueness_ratio: int = 10
    speckle_window_size: int = 50
    speckle_range: int = 2
    lr_tolerance_px: float = 1.5

    def __post_init__(self):
        if any(type(value) is not int for value in (
                self.num_disparities, self.block_size, self.uniqueness_ratio,
                self.speckle_window_size, self.speckle_range)):
            raise ValueError("Integer SGBM parameters required")
        if self.num_disparities <= 0 or self.num_disparities % 16:
            raise ValueError("num_disparities must be positive and divisible by 16")
        if self.block_size < 3 or self.block_size % 2 == 0:
            raise ValueError("block_size must be odd and >=3")
        if min(self.uniqueness_ratio, self.speckle_window_size, self.speckle_range) < 0:
            raise ValueError("Nonnegative SGBM filtering parameters required")
        if not np.isfinite(self.lr_tolerance_px) or self.lr_tolerance_px < 0:
            raise ValueError("Finite nonnegative consistency tolerance required")

    def to_dict(self):
        return {**asdict(self), "min_disparity": 0, "mode": "SGBM_3WAY",
                "border_policy": "fill invalid left search band with padded crop; native support and LR checks",
                "input": "rectified total-event log channel, uint8",
                "P1": 8*self.block_size**2, "P2": 32*self.block_size**2,
                "threads": cv2.getNumThreads()}

    def depth_range(self, q):
        """Nominal near limit for this search and canonical rectified Q.

        Integer hypotheses are 0..D-1. SGBM does not refine the endpoint
        beyond D-1; zero disparity is rejected by this pipeline. This is a
        geometric search limit, not a guarantee of valid depth or accuracy.
        """
        q = np.asarray(q, dtype=float)
        if q.shape != (4, 4) or not np.isfinite(q).all():
            raise ValueError('Finite canonical rectified Q required for depth range')
        expected = np.array([[1,0,0,q[0,3]], [0,1,0,q[1,3]],
                             [0,0,0,q[2,3]], [0,0,q[3,2],0]], dtype=float)
        if not np.allclose(q, expected) or q[2,3] <= 0 or q[3,2] <= 0:
            raise ValueError('Canonical positive-focal, positive-baseline Q required for depth range')
        max_disparity = self.num_disparities-1
        return dict(min_disparity_px=0, max_disparity_px=max_disparity,
                    min_z_m=float(q[2,3]/q[3,2]/max_disparity),
                    coverage_guaranteed=False,
                    meaning='NOMINAL_SEARCH_LIMIT_NOT_OBJECT_DISTANCE_OR_ACCURACY_GUARANTEE')


def decode_sgbm(raw):
    """OpenCV signed Q4 disparity -> pixels. Zero/negative cannot yield depth."""
    raw = np.asarray(raw)
    if raw.dtype != np.int16 or raw.ndim != 2:
        raise ValueError("Expected OpenCV int16 disparity image")
    disparity = raw.astype(np.float32) / 16.0
    disparity[raw <= 0] = np.nan
    return disparity


def _matcher(config):
    return cv2.StereoSGBM_create(
        minDisparity=0, numDisparities=config.num_disparities, blockSize=config.block_size,
        P1=8*config.block_size**2, P2=32*config.block_size**2, disp12MaxDiff=1,
        uniquenessRatio=config.uniqueness_ratio, speckleWindowSize=config.speckle_window_size,
        speckleRange=config.speckle_range, preFilterCap=31, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)


def _reverse_match(left, right, config):
    # A separate matcher owns its mutable OpenCV buffers on the worker thread.
    return _matcher(config).compute(np.ascontiguousarray(right[:, ::-1]),
                                    np.ascontiguousarray(left[:, ::-1]))


def predict_stereo(left, right, config=StereoConfig(), *, executor=None):
    """Return left disparity, valid mask, raw disparity and reason counts.

    Reverse matching uses horizontally flipped (right,left) so its positive
    disparity represents original u_left-u_right. No GT is accepted here.
    A padded crop recovers candidates in the left search band only. Existing
    positive disparities are preserved; padding never supplies activity support
    or reverse matches, and final coordinates must lie inside the native image.

    An optional caller-owned thread executor overlaps reverse matching with
    forward/border matching. Inputs must remain unchanged until this call ends.
    Both results are joined before consistency checks; no frames are skipped.
    """
    left, right = np.asarray(left), np.asarray(right)
    if left.shape != right.shape or left.ndim != 2 or left.dtype != np.uint8 or right.dtype != np.uint8:
        raise ValueError("Equal H,W uint8 grayscale images required")
    if left.shape[1] <= config.num_disparities + config.block_size:
        raise ValueError("Image too narrow for disparity search")
    reverse_job = (executor.submit(_reverse_match, left, right, config)
                   if executor is not None else None)
    matcher = _matcher(config)
    raw = matcher.compute(np.ascontiguousarray(left), np.ascontiguousarray(right))
    # SGBM skips the first D columns even where a smaller disparity is observable.
    # Limit the extra pass to that band plus block context, preserving the full
    # image solution elsewhere. Both images receive the same coordinate offset.
    border = config.num_disparities
    context_end = min(left.shape[1], border + config.block_size//2 + 1)
    crop_left = np.pad(left[:, :context_end], ((0, 0), (border, 0)))
    crop_right = np.pad(right[:, :context_end], ((0, 0), (border, 0)))
    border_raw = matcher.compute(crop_left, crop_right)[:, border:2*border]
    target = raw[:, :border]
    replace = (target <= 0) & (border_raw > 0)
    target[replace] = border_raw[replace]
    disparity = decode_sgbm(raw)
    reverse_raw = (reverse_job.result() if reverse_job is not None else
                   matcher.compute(np.ascontiguousarray(right[:, ::-1]),
                                   np.ascontiguousarray(left[:, ::-1])))
    reverse = decode_sgbm(reverse_raw)[:, ::-1]
    yy, xx = np.indices(left.shape)
    raw_valid = np.isfinite(disparity)
    xr = np.rint(xx - np.where(raw_valid, disparity, 0)).astype(np.intp)
    inside = (xr >= 0) & (xr < left.shape[1])
    xr = np.clip(xr, 0, left.shape[1]-1)
    kernel = np.ones((config.block_size, config.block_size), dtype=np.uint8)
    support_left = cv2.dilate((left > 0).astype(np.uint8), kernel).astype(bool)
    support_right = cv2.dilate((right > 0).astype(np.uint8), kernel).astype(bool)[yy, xr]
    consistent = np.abs(disparity - reverse[yy, xr]) <= config.lr_tolerance_px
    valid = raw_valid & inside & support_left & support_right & consistent
    predicted = np.where(valid, disparity, np.nan).astype(np.float32)
    return predicted, valid, raw, {"raw_positive": int(raw_valid.sum()),
                                  "positive_with_activity_support": int((raw_valid & inside & support_left & support_right).sum()),
                                  "final_valid": int(valid.sum())}


def disparity_metrics(prediction, gt):
    """Pixel-weighted additive statistics; missing predictions remain visible.

    EPE/RMSE/Bad3 use the intersection. Coverage denominator is ALL positive GT.
    Bad3 means absolute error >3px (not KITTI D1's joint absolute/relative rule).
    """
    prediction, gt = np.asarray(prediction), np.asarray(gt)
    if prediction.shape != gt.shape or prediction.ndim != 2:
        raise ValueError("Equal 2D prediction/GT shapes required")
    known = np.isfinite(gt) & (gt > 0)
    valid = np.isfinite(prediction) & (prediction > 0)
    evaluated = known & valid
    errors = np.abs(prediction[evaluated] - gt[evaluated])
    n, total, bad = int(evaluated.sum()), int(known.sum()), int((errors > 3).sum())
    return {"gt_pixels": total, "evaluated_pixels": n, "predicted_pixels": int(valid.sum()),
            "image_pixels": int(gt.size), "sum_abs_error": float(errors.sum()),
            "sum_squared_error": float(np.square(errors).sum()), "bad3_pixels": bad,
            "epe_px": float(errors.mean()) if n else None,
            "rmse_px": float(np.sqrt(np.square(errors).mean())) if n else None,
            "bad3_fraction": bad/n if n else None, "gt_coverage": n/total if total else None,
            "bad3_or_missing_fraction": (bad+total-n)/total if total else None}


def aggregate_metrics(rows):
    keys = ("gt_pixels", "evaluated_pixels", "predicted_pixels", "image_pixels",
            "sum_abs_error", "sum_squared_error", "bad3_pixels")
    sums = {key: sum(row[key] for row in rows) for key in keys}
    n, total = sums["evaluated_pixels"], sums["gt_pixels"]
    return {**sums, "epe_px": sums["sum_abs_error"]/n if n else None,
            "rmse_px": (sums["sum_squared_error"]/n)**.5 if n else None,
            "bad3_fraction": sums["bad3_pixels"]/n if n else None,
            "gt_coverage": n/total if total else None,
            "bad3_or_missing_fraction": (sums["bad3_pixels"]+total-n)/total if total else None}
