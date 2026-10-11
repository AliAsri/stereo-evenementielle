"""Sparse apparent-flow residuals. Not calibrated ego-motion or object motion GT."""

from dataclasses import asdict, dataclass
import cv2
import numpy as np


@dataclass(frozen=True)
class GlobalMotionConfig:
    width: int = 640
    height: int = 480
    downsample: int = 2
    step_us: int = 20_000
    max_features: int = 400
    min_tracks: int = 20
    min_inliers: int = 12
    min_inlier_fraction: float = 0.5
    min_hull_fraction: float = 0.10
    fb_max_px: float = 1.0  # working-image pixels
    ransac_px: float = 1.0
    residual_native_px: float = 3.0
    min_cluster_points: int = 3
    cell_native_px: int = 32
    seed: int = 42


def event_gray(events, config=GlobalMotionConfig()):
    """Fixed log count scale, no per-frame contrast fitting; grayscale at 320x240."""
    c = config
    x, y = (np.asarray(events[k]) for k in ("x", "y"))
    if x.ndim != 1 or x.shape != y.shape or x.dtype.kind not in "iu" or y.dtype.kind not in "iu":
        raise ValueError("Integer coordinate vectors required")
    if np.any(x < 0) or np.any(x >= c.width) or np.any(y < 0) or np.any(y >= c.height):
        raise ValueError("Coordinates outside image")
    w, h = c.width//c.downsample, c.height//c.downsample
    ids = (y.astype(np.intp)//c.downsample)*w+x.astype(np.intp)//c.downsample
    counts = np.bincount(ids, minlength=w*h).reshape(h, w)
    gray = np.uint8(np.rint(np.clip(np.log1p(counts)/np.log1p(50), 0, 1)*255))
    return cv2.GaussianBlur(gray, (3, 3), 0)


def fit_apparent_motion(previous, current, config=GlobalMotionConfig()):
    """Fit a 4-DOF image similarity with RANSAC to checked LK correspondences."""
    c = config
    p, q = np.asarray(previous, dtype=np.float32), np.asarray(current, dtype=np.float32)
    if p.ndim != 2 or p.shape[1:] != (2,) or p.shape != q.shape or not np.isfinite(p).all() or not np.isfinite(q).all():
        raise ValueError("Finite matching Nx2 point arrays required")
    out = {"status": "TOO_FEW_TRACKS", "valid": False, "tracks": len(p), "inliers": 0,
           "inlier_fraction": 0.0, "hull_fraction": 0.0, "matrix_working_pixels": None,
           "regions": [], "residual_points_native": [], "residual_native_px": []}
    if len(p) < c.min_tracks:
        return out
    cv2.setRNGSeed(c.seed)
    matrix, mask = cv2.estimateAffinePartial2D(p, q, method=cv2.RANSAC,
        ransacReprojThreshold=c.ransac_px, maxIters=1000, confidence=.99, refineIters=10)
    if matrix is None or mask is None or not np.isfinite(matrix).all():
        out["status"] = "FIT_FAILED"
        return out
    inliers = mask.ravel().astype(bool)
    count = int(inliers.sum())
    coverage = float(cv2.contourArea(cv2.convexHull(p[inliers]))) / ((c.width/c.downsample)*(c.height/c.downsample)) if count >= 3 else 0.0
    fraction = count/len(p)
    out.update(inliers=count, inlier_fraction=fraction, hull_fraction=coverage)
    if count < c.min_inliers or fraction < c.min_inlier_fraction or coverage < c.min_hull_fraction:
        out["status"] = "INSUFFICIENT_GLOBAL_SUPPORT"
        return out
    scale = float(np.sqrt(np.linalg.det(matrix[:, :2])))
    if not .8 <= scale <= 1.2:
        out["status"] = "IMPLAUSIBLE_SCALE"
        return out
    predicted = p@matrix[:, :2].T+matrix[:, 2]
    residual = np.linalg.norm(q-predicted, axis=1)*c.downsample
    unusual = residual > c.residual_native_px
    points = q[unusual]*c.downsample
    rows = (c.height+c.cell_native_px-1)//c.cell_native_px
    cols = (c.width+c.cell_native_px-1)//c.cell_native_px
    grid = np.zeros((rows, cols), np.uint8)
    if len(points):
        gx = np.clip((points[:, 0]/c.cell_native_px).astype(int), 0, cols-1)
        gy = np.clip((points[:, 1]/c.cell_native_px).astype(int), 0, rows-1)
        grid[gy, gx] = 1
        # Nearby residual tracks may support a proposal; box spans observed points.
        _, labels = cv2.connectedComponents(cv2.dilate(grid, np.ones((3, 3), np.uint8)), connectivity=8)
        for label in np.unique(labels[gy, gx]):
            selected = points[labels[gy, gx] == label]
            if label == 0 or len(selected) < c.min_cluster_points:
                continue
            lo = np.maximum(np.floor(selected.min(axis=0)-8), [0, 0]).astype(int)
            hi = np.minimum(np.ceil(selected.max(axis=0)+8), [c.width, c.height]).astype(int)
            out["regions"].append({"xyxy": [*lo.tolist(), *hi.tolist()], "support_points": len(selected),
                                   "kind": "APPARENT_RESIDUAL_CANDIDATE_NOT_OBJECT_MOTION"})
    out.update(status="VALID_IMAGE_MODEL", valid=True, matrix_working_pixels=matrix.tolist(),
               residual_points_native=points.tolist(), residual_native_px=residual.tolist())
    return out


class GlobalMotionDetector:
    def __init__(self, config=GlobalMotionConfig()):
        self.config = config
        c = config
        if (c.width <= 0 or c.height <= 0 or c.downsample <= 0 or c.width % c.downsample
                or c.height % c.downsample or c.step_us <= 0 or c.min_tracks < 3):
            raise ValueError("Invalid image geometry or tracking configuration")
        self.previous = None
        self.previous_end = None

    def parameters(self):
        return asdict(self.config)

    def update(self, gray, end_us):
        c = self.config
        if gray.dtype != np.uint8 or gray.shape != (c.height//c.downsample, c.width//c.downsample):
            raise ValueError("Expected configured uint8 grayscale image")
        if not isinstance(end_us, (int, np.integer)):
            raise TypeError("Integer timestamp required")
        if self.previous_end is not None and end_us-self.previous_end != c.step_us:
            raise ValueError("Noncontiguous image timestamps; create a new detector")
        previous = self.previous
        self.previous = gray.copy()
        self.previous_end = int(end_us)
        if previous is None:
            return {"status": "WARMUP", "valid": False, "regions": [], "tracks": 0}
        points = cv2.goodFeaturesToTrack(previous, maxCorners=c.max_features, qualityLevel=.01,
                                         minDistance=6, blockSize=5)
        if points is None:
            return {"status": "NO_FEATURES", "valid": False, "regions": [], "tracks": 0}
        lk = dict(winSize=(21, 21), maxLevel=2,
                  criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 20, .01))
        forward, status, _ = cv2.calcOpticalFlowPyrLK(previous, gray, points, None, **lk)
        if forward is None:
            return {"status": "TRACKING_FAILED", "valid": False, "regions": [], "tracks": 0}
        backward, reverse_status, _ = cv2.calcOpticalFlowPyrLK(gray, previous, forward, None, **lk)
        if backward is None:
            return {"status": "TRACKING_FAILED", "valid": False, "regions": [], "tracks": 0}
        p, q, back = points.reshape(-1, 2), forward.reshape(-1, 2), backward.reshape(-1, 2)
        keep = ((status.ravel() == 1) & (reverse_status.ravel() == 1)
                & np.isfinite(q).all(axis=1) & np.isfinite(back).all(axis=1)
                & (np.linalg.norm(p-back, axis=1) <= c.fb_max_px)
                & (q[:, 0] >= 0) & (q[:, 0] < gray.shape[1]) & (q[:, 1] >= 0) & (q[:, 1] < gray.shape[0]))
        return fit_apparent_motion(p[keep], q[keep], c)
