"""Count representations, bilinear rectification, and frozen log normalization."""

import numpy as np


def _event_indices(events, width, height):
    """Validate coordinates without allocating a native count image."""
    if width <= 0 or height <= 0:
        raise ValueError("Positive dimensions required")
    x, y, p = (np.asarray(events[key]) for key in ("x", "y", "p"))
    if x.ndim != 1 or x.shape != y.shape or x.shape != p.shape:
        raise ValueError("Equal-length 1D event fields required")
    if any(a.dtype.kind not in "uib" for a in (x, y, p)):
        raise TypeError("Integer pixel indices and polarities required")
    if np.any(x < 0) or np.any(x >= width) or np.any(y < 0) or np.any(y >= height) or not np.isin(p, [0, 1]).all():
        raise ValueError("Invalid pixel coordinates or polarities")
    return tuple(a.astype(np.intp, copy=False) for a in (x, y, p))


def polarity_counts(events, width=640, height=480):
    """Return uint32 [2,H,W] counts (channel 0 negative, 1 positive)."""
    x, y, p = _event_indices(events, width, height)
    indices = (p * height + y) * width + x
    return np.bincount(indices, minlength=2*height*width).reshape(2, height, width).astype(np.uint32)


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
    mapping = np.asarray(mapping)
    if mapping.ndim != 3 or mapping.shape[2] != 2:
        raise ValueError("Expected a native H,W,2 map")
    if width <= 0 or height <= 0:
        raise ValueError("Positive output dimensions required")
    x, y, polarity = _event_indices(events, mapping.shape[1], mapping.shape[0])
    xy = mapping[y, x]
    keep = (np.isfinite(xy).all(axis=1) & (xy[:, 0] >= 0) &
            (xy[:, 0] <= width-1) & (xy[:, 1] >= 0) & (xy[:, 1] <= height-1))
    xy = xy[keep].astype(np.float64)
    p = polarity[keep]
    floor = np.floor(xy)
    x0, y0 = floor.astype(np.intp).T
    dx, dy = (xy - floor).T
    # Reuse the flat destination base for the four bilinear offsets.
    base = (p * height + y0) * width + x0
    indices, weights = [], []
    for ox, oy, weight in ((0, 0, (1-dx)*(1-dy)), (1, 0, dx*(1-dy)),
                          (0, 1, (1-dx)*dy), (1, 1, dx*dy)):
        active = weight > 0
        indices.append(base[active] + oy*width + ox)
        weights.append(weight[active])
    # Keep the original offset/event order, including collisions across offsets.
    # Summing four separate histograms would reorder floating-point additions.
    counts = np.bincount(np.concatenate(indices), weights=np.concatenate(weights),
                         minlength=2*height*width).reshape(2, height, width)
    if not np.isclose(counts.sum(), keep.sum(), rtol=1e-10, atol=1e-8):
        raise ValueError("Bilinear splat lost event mass")
    return counts.astype(np.float32), int((~keep).sum())


class BilinearRectifier:
    """Precompute a fixed calibration's splat geometry, not any event data.

    Own the derived arrays so later edits of the input map cannot invalidate
    them. Preserve the reference's offset/event accumulation order exactly.
    """

    def __init__(self, mapping, width=640, height=480):
        mapping = np.asarray(mapping)
        if mapping.ndim != 3 or mapping.shape[2] != 2:
            raise ValueError("Expected a native H,W,2 map")
        if width <= 0 or height <= 0:
            raise ValueError("Positive output dimensions required")
        self.native_height, self.native_width = mapping.shape[:2]
        self.width, self.height = width, height
        xy = mapping.reshape(-1, 2)
        self.keep = (np.isfinite(xy).all(axis=1) & (xy[:, 0] >= 0) &
                     (xy[:, 0] <= width-1) & (xy[:, 1] >= 0) & (xy[:, 1] <= height-1))
        # Invalid mapped centers are never indexed into the output histogram.
        xy = np.where(self.keep[:, None], xy, 0).astype(np.float64)
        floor = np.floor(xy)
        x0, y0 = floor.astype(np.intp).T
        dx, dy = (xy-floor).T
        self.base = y0*width+x0
        self.weights = ((1-dx)*(1-dy), dx*(1-dy), (1-dx)*dy, dx*dy)
        for array in (self.keep, self.base, *self.weights):
            array.setflags(write=False)

    def counts(self, events):
        x, y, p = _event_indices(events, self.native_width, self.native_height)
        source = y*self.native_width+x
        keep = self.keep[source]
        source = source[keep]
        base = self.base[source] + p[keep]*(self.height*self.width)
        # Allocate the four offset blocks once, preserving offset/event order.
        # Zero weights can stay: adding +0 leaves every nonnegative sum exact.
        # Clamp only destinations beyond the final pixel (their weight is zero
        # at retained border centers), so bincount cannot grow an extra bin.
        indices = np.empty((4, len(source)), dtype=np.intp)
        weights = np.empty((4, len(source)), dtype=np.float64)
        for i, (offset, lookup) in enumerate(zip((0, 1, self.width, self.width+1), self.weights)):
            np.add(base, offset, out=indices[i])
            weights[i] = lookup[source]
        np.minimum(indices, 2*self.height*self.width-1, out=indices)
        counts = np.bincount(indices.ravel(), weights=weights.ravel(),
                             minlength=2*self.height*self.width).reshape(2, self.height, self.width)
        if not np.isclose(counts.sum(), keep.sum(), rtol=1e-10, atol=1e-8):
            raise ValueError("Bilinear splat lost event mass")
        return counts.astype(np.float32), int((~keep).sum())


def _count_array(counts):
    """Shared float32 conversion and validation for both image formats."""
    counts = np.asarray(counts, dtype=np.float32)
    if counts.ndim != 3 or counts.shape[0] != 2 or not np.isfinite(counts).all() or np.any(counts < 0):
        raise ValueError("Expected finite nonnegative [2,H,W] counts")
    return counts


def log_channels(counts):
    """HWC float32: log1p(positive), log1p(negative), log1p(total)."""
    counts = _count_array(counts)
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


def normalized_event_image(counts, normalizer, *, total_only=False):
    """Frozen scales -> HWC uint8, or HW total channel for stereo/tracking.

    total_only skips the unused polarity channels without changing the total
    count sum, float32 logarithm, frozen scale, clipping or rounding.
    """
    # Scale-only synthetic callers remain supported; declared channel metadata
    # must agree with the representation, including the total-only fast path.
    if ('channels' in normalizer
            and normalizer['channels'] != ['positive', 'negative', 'total']):
        raise ValueError('Normalizer channel order must be positive, negative, total')
    scales = np.asarray(normalizer["scales"], dtype=np.float32)
    if scales.shape != (3,) or not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError("Three finite positive scales required")
    if total_only:
        channels = np.log1p(_count_array(counts).sum(axis=0))
        scales = scales[2]
    else:
        channels = log_channels(counts)
    return np.rint(np.clip(channels / scales, 0, 1) * 255).astype(np.uint8)


def stereo_event_images(events, rectifiers, normalizer, *, executor=None, include_native=True):
    """Native left RGB and rectified totals, with optional right-side overlap.

    The caller owns the executor and keeps inputs immutable until return.
    Event order and arithmetic within each image are identical to serial use.
    No extra frame, temporal cache or future event is introduced.
    With include_native=False, return None for the native image so its caller
    can compute it after publishing motion; rectified images are unchanged.
    """
    if len(events) != 2 or len(rectifiers) != 2:
        raise ValueError('Left/right events and rectifiers required')

    def rectified(side):
        return normalized_event_image(rectifiers[side].counts(events[side])[0],
                                      normalizer, total_only=True)

    right_job = executor.submit(rectified, 1) if executor is not None else None
    try:
        left = rectifiers[0]
        native = (normalized_event_image(polarity_counts(events[0], left.native_width,
                                                         left.native_height), normalizer)
                  if include_native else None)
        image_left = rectified(0)
    except BaseException:
        # Do not leave work using caller-owned arrays after a failed call.
        if right_job is not None and not right_job.cancel():
            try:
                right_job.result()
            except BaseException:
                pass  # Preserve the original left-side failure.
        raise
    image_right = right_job.result() if right_job is not None else rectified(1)
    return native, [image_left, image_right]
