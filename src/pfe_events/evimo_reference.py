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


def pose_matrix(record, timestamp_s):
    """EVIMO wxyz pose, with only six-decimal serialization tolerance (1.1 us).

    Camera records map camera to the fixed initial-camera/world frame;
    object records map object to camera. No timestamp interpolation is done.
    """
    offset = abs(float(record['ts']) - float(timestamp_s))
    q = np.array([record['pos']['q'][v] for v in ('w', 'x', 'y', 'z')], float)
    t = np.array([record['pos']['t'][v] for v in ('x', 'y', 'z')], float)
    norm = np.linalg.norm(q)
    if (not np.isfinite(timestamp_s) or not np.isfinite(offset) or offset > 1.1e-6
            or not np.isfinite(q).all() or not np.isfinite(t).all()
            or abs(norm - 1) > 1e-4):
        raise ValueError('Invalid or unsynchronized reference pose')
    w, x, y, z = q / norm  # Correct rounding only, not arbitrary quaternions.
    result = np.eye(4)
    result[:3, :3] = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    result[:3, 3] = t
    return result


def rotation_angle_deg(rotation):
    return float(np.degrees(np.arccos(np.clip((np.trace(rotation)-1)/2, -1, 1))))


def pose_pair_reference(previous, current):
    """Reference transforms and finite-interval motion, never mobility labels.

    Object displacement concerns its pose origin, not its visible centroid.
    Rotation is reported too: an unchanged origin does not imply no motion.
    """
    dt = float(current['ts']) - float(previous['ts'])
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError('Positive finite reference interval required')
    a = pose_matrix(previous['cam'], previous['ts'])
    b = pose_matrix(current['cam'], current['ts'])
    camera = np.linalg.inv(b) @ a
    names = lambda f: {k for k, v in f.items() if k != 'cam' and isinstance(v, dict) and 'pos' in v}
    before, after = names(previous), names(current)
    objects = {}
    for key in sorted(before & after, key=int):
        pa = pose_matrix(previous[key], previous['ts'])
        pb = pose_matrix(current[key], current['ts'])
        wa, wb = a @ pa, b @ pb
        objects[key] = dict(
            transform_previous_to_current=(pb @ np.linalg.inv(pa)).tolist(),
            apparent_origin_displacement_m=float(np.linalg.norm(pb[:3, 3]-pa[:3, 3])),
            world_origin_displacement_m=float(np.linalg.norm(wb[:3, 3]-wa[:3, 3])),
            world_rotation_deg=rotation_angle_deg(wb[:3, :3] @ wa[:3, :3].T))
    return dict(interval_s=dt, transform_previous_to_current=camera.tolist(),
                camera_origin_displacement_m=float(np.linalg.norm(b[:3, 3]-a[:3, 3])),
                camera_rotation_deg=rotation_angle_deg(camera[:3, :3]),
                missing_previous=sorted(after-before), missing_current=sorted(before-after),
                objects=objects)


def radtan_calibration(metadata):
    """Use named coefficients, not EVIMO's legacy D=[k1,k2,k3,k4].

    Producer dataset.h uses rational radial (k3 numerator, k4 denominator)
    and p1/p2 tangential terms. Return OpenCV's eight-coefficient ordering.
    """
    if metadata['dist_model'] != 'radtan':
        raise ValueError('This bounded control supports radtan only')
    k = np.array([[metadata['fx'], 0, metadata['cx']],
                  [0, metadata['fy'], metadata['cy']], [0, 0, 1]], float)
    d = np.array([metadata[v] for v in ('k1', 'k2', 'p1', 'p2', 'k3', 'k4')] + [0, 0], float)
    if not np.isfinite(k).all() or not np.isfinite(d).all() or min(k[0, 0], k[1, 1]) <= 0:
        raise ValueError('Invalid calibration')
    return k, d
