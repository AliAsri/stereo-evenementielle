"""Read EVIMO metadata without importing callable globals from its pickle.

Only the legacy NumPy scalar-object envelope is supported. Its constructors
are replaced with inert local containers; nested payloads must be plain data.
This is a format-specific reader, not a general-purpose pickle sandbox.
"""
import io
import pickle
import zipfile

import numpy as np


class _Dtype:
    def __init__(self, code, align=False, copy=True):
        if code not in ('O8', 'O4'):
            raise ValueError('Only object metadata envelopes are supported')

    def __setstate__(self, state):
        pass


class _Array:
    def __setstate__(self, state):
        if (not isinstance(state, tuple) or len(state) != 5 or state[0] != 1
                or state[1] != () or not isinstance(state[2], _Dtype)
                or state[3] is not False or not isinstance(state[4], list)
                or len(state[4]) != 1 or not isinstance(state[4][0], dict)):
            raise ValueError('Unexpected metadata envelope')
        self.value = state[4][0]


def _reconstruct(subtype, shape, code):
    if subtype is not _Array or shape != (0,) or code != b'b':
        raise ValueError('Unexpected array reconstruction')
    return _Array()


class _MetadataUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {
            ('numpy.core.multiarray', '_reconstruct'): _reconstruct,
            ('numpy._core.multiarray', '_reconstruct'): _reconstruct,
            ('numpy', 'ndarray'): _Array,
            ('numpy', 'dtype'): _Dtype,
        }
        if (module, name) not in allowed:
            raise ValueError(f'Unsupported metadata global: {module}.{name}')
        return allowed[module, name]


def _plain_data(value, ancestors=None):
    if value is None or type(value) in (str, int, float, bool, bytes):
        return
    if type(value) not in (dict, list, tuple):
        raise ValueError('Metadata contains non-plain data')
    ancestors = set() if ancestors is None else ancestors
    if id(value) in ancestors:
        raise ValueError('Cyclic metadata')
    ancestors.add(id(value))
    if isinstance(value, dict):
        for key in value:
            if type(key) not in (str, int):
                raise ValueError('Unexpected metadata key')
        values = value.values()
    else:
        values = value
    for item in values:
        _plain_data(item, ancestors)
    ancestors.remove(id(value))


def read_metadata(info_path):
    with zipfile.ZipFile(info_path) as archive:
        if archive.namelist().count('meta.npy') != 1:
            raise ValueError('Missing or duplicate meta.npy')
        if archive.getinfo('meta.npy').file_size > 32 * 1024**2:
            raise ValueError('Metadata exceeds 32 MiB budget')
        stream = io.BytesIO(archive.read('meta.npy'))
    version = np.lib.format.read_magic(stream)
    if version != (1, 0):
        raise ValueError('Unsupported metadata NPY version')
    shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream)
    if shape != () or fortran or dtype != np.dtype(object):
        raise ValueError('Expected scalar object metadata')
    array = _MetadataUnpickler(stream).load()
    if type(array) is not _Array or not hasattr(array, 'value') or stream.read(1):
        raise ValueError('Invalid metadata payload')
    _plain_data(array.value)
    return array.value


def timestamp_summary(times):
    values = np.asarray(times, dtype=np.float64)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError('At least two finite timestamps required')
    delta = np.diff(values)
    if np.any(delta <= 0):
        raise ValueError('Reference timestamps must be strictly increasing')
    return {'count': len(values), 'first_s': float(values[0]), 'last_s': float(values[-1]),
            'median_step_ms': float(np.median(delta) * 1000),
            'max_step_ms': float(delta.max() * 1000)}
