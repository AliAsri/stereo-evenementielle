"""Format-specific DSEC-MOD cache reader; no upstream pickle code is executed.

NumPy constructors are replaced by inert byte envelopes. Only explicitly chosen
train sequences become numeric arrays; test tubes are discarded unread. This
bounded reader is not a general-purpose pickle sandbox.
"""
import io
import pickle

import numpy as np

MAX_BYTES = 2 * 1024**2


class _Dtype:
    def __init__(self, code, align=False, copy=True):
        if code not in ('f4', 'f8'):
            raise ValueError('Unsupported tube dtype')
        self.code = code
        self.endian = None

    def __setstate__(self, state):
        if (not isinstance(state, tuple) or len(state) != 8 or state[0] != 3
                or state[1] not in ('<', '>') or state[2:] != (None, None, None, -1, -1, 0)):
            raise ValueError('Unsupported dtype state')
        self.endian = state[1]


class _Array:
    def __setstate__(self, state):
        if (not isinstance(state, tuple) or len(state) != 5 or state[0] != 1
                or not isinstance(state[1], tuple) or len(state[1]) != 2
                or type(state[1][0]) is not int or not 0 < state[1][0] <= 100_000
                or state[1][1] != 5 or type(state[2]) is not _Dtype
                or state[2].endian is None or type(state[3]) is not bool
                or type(state[4]) is not bytes):
            raise ValueError('Unsupported tube envelope')
        _, self.shape, self.dtype, self.fortran, self.raw = state
        if len(self.raw) != self.shape[0] * 5 * int(self.dtype.code[1:]):
            raise ValueError('Tube byte length mismatch')

    def numeric(self):
        return np.frombuffer(self.raw, dtype=self.dtype.endian + self.dtype.code).reshape(
            self.shape, order='F' if self.fortran else 'C')


def _reconstruct(subtype, shape, code):
    if subtype is not _Array or shape != (0,) or code != b'b':
        raise ValueError('Unsupported tube reconstruction')
    return _Array()


class _CacheUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {('numpy.core.multiarray', '_reconstruct'): _reconstruct,
                   ('numpy._core.multiarray', '_reconstruct'): _reconstruct,
                   ('numpy', 'ndarray'): _Array, ('numpy', 'dtype'): _Dtype}
        if (module, name) not in allowed:
            raise ValueError(f'Unsupported cache global: {module}.{name}')
        return allowed[module, name]


def _split(value):
    if (type(value) is not list or len(value) != 1 or type(value[0]) is not list
            or not value[0] or any(type(s) is not str for s in value[0])
            or len(set(value[0])) != len(value[0])):
        raise ValueError('Expected one unique sequence split')
    return value[0]


def read_train_cache(stream, sequences):
    """Return split metadata and selected train tubes, never test box values."""
    payload = stream.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError('Cache exceeds 2 MiB budget')
    source = io.BytesIO(payload)
    root = _CacheUnpickler(source).load()
    keys = {'labels', 'train_videos', 'test_videos', 'nframes', 'resolution', 'gttubes'}
    if type(root) is not dict or root.keys() != keys or source.read(1):
        raise ValueError('Unexpected cache schema or trailing bytes')
    if root['labels'] != ['Moving']:
        raise ValueError('Expected one Moving class')
    train, test = _split(root['train_videos']), _split(root['test_videos'])
    all_names = set(train) | set(test)
    if set(train) & set(test):
        raise ValueError('Train/test overlap')
    selected = tuple(sequences)
    if not selected or len(set(selected)) != len(selected) or not set(selected) <= set(train):
        raise ValueError('Select unique train sequences only')
    for field in ('nframes', 'resolution', 'gttubes'):
        if type(root[field]) is not dict or root[field].keys() != all_names:
            raise ValueError('Sequence metadata mismatch')
    metadata = {}
    for name in train + test:
        count, resolution = root['nframes'][name], root['resolution'][name]
        if (type(count) is not int or not 0 < count <= 100_000
                or type(resolution) not in (list, tuple) or len(resolution) != 2
                or any(type(v) is not int or not 0 < v <= 10000 for v in resolution)):
            raise ValueError('Invalid frame metadata')
        metadata[name] = {'frames': count, 'height': resolution[0], 'width': resolution[1]}
    tubes = {}
    for name in selected:
        classes = root['gttubes'][name]
        if type(classes) is not dict or classes.keys() != {0} or type(classes[0]) is not list:
            raise ValueError('Unexpected train classes')
        tubes[name] = []
        for envelope in classes[0]:
            if type(envelope) is not _Array or not hasattr(envelope, 'raw'):
                raise ValueError('Unexpected train tube')
            values = envelope.numeric()
            frames = values[:, 0]
            if (not np.isfinite(values).all() or np.any(frames != np.floor(frames))
                    or np.any(frames < 1) or np.any(frames > metadata[name]['frames'])
                    or np.any(np.diff(frames) <= 0)):
                raise ValueError('Invalid train frame values')
            if np.any(values[:, 3:5] <= values[:, 1:3]):
                raise ValueError('Degenerate train box')
            tubes[name].append(values.copy())
    return {'labels': ['Moving'], 'train': train, 'test': test,
            'metadata': metadata, 'tubes': tubes}


def audit_tubes(tubes, metadata):
    """Audit coordinates without clipping them or assuming an image convention."""
    rows = np.concatenate(tubes) if tubes else np.empty((0, 5))
    h, w = metadata['height'], metadata['width']
    outside = (np.any(rows[:, 1:3] < 0, axis=1)
               | (rows[:, 3] > w) | (rows[:, 4] > h))
    frames = np.unique(rows[:, 0]).astype(int)
    return {'tube_count': len(tubes), 'box_count': len(rows),
            'frames_with_boxes': len(frames),
            'frames_without_boxes': metadata['frames'] - len(frames),
            'first_box_frame': int(frames[0]) if len(frames) else None,
            'last_box_frame': int(frames[-1]) if len(frames) else None,
            'boxes_outside_0_width_height': int(outside.sum()),
            'nonconsecutive_tube_steps': sum(int(np.sum(np.diff(t[:, 0]) != 1)) for t in tubes),
            'timestamp_mapping': 'UNRESOLVED', 'coordinate_mapping': 'UNRESOLVED',
            'empty_frames_are_verified_negatives': False}
