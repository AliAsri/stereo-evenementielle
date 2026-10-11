"""Diagnostic renderers; these pictures do not establish independent motion."""
import numpy as np
from PIL import Image

def native_event_image(events):
    ids = events['y'].astype(np.intp)*640+events['x'].astype(np.intp)
    counts = np.bincount(ids, minlength=640*480).reshape(480, 640)
    return Image.fromarray(np.uint8(np.rint(np.clip(np.log1p(counts)/np.log1p(20), 0, 1)*255))).convert('RGB')
