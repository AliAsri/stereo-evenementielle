"""Count representations, bilinear rectification, and frozen log normalization."""

import numpy as np


def polarity_counts(events, width=640, height=480):
    """Return uint32 [2,H,W] counts (channel 0 negative, 1 positive)."""
    if width <= 0 or height <= 0:
        raise ValueError("Positive dimensions required")
    x, y, p = (np.asarray(events[key]) for key in ("x", "y", "p"))
    if x.ndim != 1 or x.shape != y.shape or x.shape != p.shape:
        raise ValueError("Equal-length 1D event fields required")
    if any(a.dtype.kind not in "uib" for a in (x, y, p)):
        raise TypeError("Integer pixel indices and polarities required")
    if np.any(x < 0) or np.any(x >= width) or np.any(y < 0) or np.any(y >= height) or not np.isin(p, [0, 1]).all():
        raise ValueError("Invalid pixel coordinates or polarities")
    counts = np.zeros((2, height, width), dtype=np.uint32)
    np.add.at(counts, (p.astype(np.intp), y.astype(np.intp), x.astype(np.intp)), 1)
    return counts


def render_counts(counts):
    """White background, negative blue, positive red, overlap purple; no normalization."""
    if counts.ndim != 3 or counts.shape[0] != 2:
        raise ValueError("Expected [2,H,W]")
    image = np.full((*counts.shape[1:], 3), 255, dtype=np.uint8)
    negative, positive = counts[0] > 0, counts[1] > 0
    image[negative] = [35, 85, 210]
    image[positive] = [220, 55, 45]
    image[negative & positive] = [135, 45, 175]
    return image


def rectified_counts(events, mapping, width=640, height=480):
    """Forward bilinear splat; reject mapped centers outside the output image.

    Each retained event contributes exactly one unit split among <=4 pixels.
    No image interpolation or filling across empty regions is applied afterward.
    """
    native = polarity_counts(events, mapping.shape[1], mapping.shape[0])
    if mapping.shape != (*native.shape[1:], 2):
        raise ValueError("Expected a native H,W,2 map")
    xy = mapping[events["y"], events["x"]]
    keep = (np.isfinite(xy).all(axis=1) & (xy[:, 0] >= 0) &
            (xy[:, 0] <= width-1) & (xy[:, 1] >= 0) & (xy[:, 1] <= height-1))
    xy = xy[keep].astype(np.float64)
    p = events["p"][keep].astype(np.intp)
    x0, y0 = np.floor(xy).astype(np.intp).T
    dx, dy = (xy - np.floor(xy)).T
    counts = np.zeros((2, height, width), dtype=np.float64)
    for ox, oy, weight in ((0, 0, (1-dx)*(1-dy)), (1, 0, dx*(1-dy)),
                          (0, 1, (1-dx)*dy), (1, 1, dx*dy)):
        active = weight > 0
        np.add.at(counts, (p[active], y0[active]+oy, x0[active]+ox), weight[active])
    if not np.isclose(counts.sum(), keep.sum(), rtol=1e-10, atol=1e-8):
        raise ValueError("Bilinear splat lost event mass")
    return counts.astype(np.float32), int((~keep).sum())


def log_channels(counts):
    """HWC float32: log1p(positive), log1p(negative), log1p(total)."""
    counts = np.asarray(counts, dtype=np.float32)
    if counts.ndim != 3 or counts.shape[0] != 2 or not np.isfinite(counts).all() or np.any(counts < 0):
        raise ValueError("Expected finite nonnegative [2,H,W] counts")
    return np.log1p(np.stack([counts[1], counts[0], counts.sum(axis=0)], axis=-1))


def fit_log_normalizer(count_frames, *, source_split, percentile=99.5, seed=42):
    """Fit on train only; deterministic reservoir per frame/channel (<=10k values).

    Percentile is over positive samples; absent channels use log(2).
    The caller records exact sequences/windows. Never fit on validation/test.
    """
    if source_split != "train" or not 0 < percentile <= 100:
        raise ValueError("Normalizer must be fitted on train with a valid percentile")
    rng = np.random.default_rng(seed)
    samples = [[], [], []]
    frames = 0
    for counts in count_frames:
        frame = log_channels(counts)
        frames += 1
        for channel in range(3):
            values = frame[..., channel]
            values = values[values > 0]
            if values.size > 10_000:
                values = rng.choice(values, size=10_000, replace=False)
            samples[channel].append(values)
    if not frames:
        raise ValueError("No training frames supplied")
    merged = [np.concatenate(values) for values in samples]
    scales = [max(float(np.percentile(v, percentile)) if v.size else 0, float(np.log(2))) for v in merged]
    return {"channels": ["positive", "negative", "total"], "scales": scales,
            "source_split": source_split, "percentile": percentile, "seed": seed,
            "frames": frames, "sampled_positive_values": [int(v.size) for v in merged],
            "method": "positive log1p values; up to 10000 random samples/frame/channel; scale floor log(2)"}


def normalized_event_image(counts, normalizer):
    """Frozen shared scales -> HWC uint8; no per-image auto-contrast."""
    scales = np.asarray(normalizer["scales"], dtype=np.float32)
    if scales.shape != (3,) or not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError("Three finite positive scales required")
    return np.rint(np.clip(log_channels(counts) / scales, 0, 1) * 255).astype(np.uint8)
