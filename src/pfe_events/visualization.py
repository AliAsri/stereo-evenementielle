"""Diagnostic renderers; these pictures do not establish independent motion."""
import numpy as np
from PIL import Image


def load_demo_font(size):
    """Keep the Windows rendering when available, otherwise use a local fallback."""
    from PIL import ImageFont

    for name in ('C:/Windows/Fonts/arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def native_event_image(events):
    ids = events['y'].astype(np.intp)*640+events['x'].astype(np.intp)
    counts = np.bincount(ids, minlength=640*480).reshape(480, 640)
    return Image.fromarray(np.uint8(np.rint(np.clip(np.log1p(counts)/np.log1p(20), 0, 1)*255))).convert('RGB')
