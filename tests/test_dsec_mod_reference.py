import io
import pickle
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pfe_events.dsec_mod_reference import read_train_cache, audit_tubes, _Array, MAX_BYTES


class DsecModReferenceTests(unittest.TestCase):
    def fixture(self):
        return {'labels': ['Moving'], 'train_videos': [['train']], 'test_videos': [['reserved']],
                'nframes': {'train': 4, 'reserved': 2},
                'resolution': {'train': (480, 640), 'reserved': (480, 640)},
                'gttubes': {'train': {0: [np.array([[1, 2, 3, 8, 9], [3, 4, 5, 10, 12]], dtype='f4')]},
                            'reserved': {0: [np.full((1, 5), np.nan, dtype='f4')]}}}

    def read(self, data, names=('train',)):
        return read_train_cache(io.BytesIO(pickle.dumps(data, protocol=3)), names)

    def test_reads_train_preserves_frame_gaps_and_audits(self):
        r = self.read(self.fixture())
        s = audit_tubes(r['tubes']['train'], r['metadata']['train'])
        self.assertEqual(s['box_count'], 2)
        self.assertEqual(s['nonconsecutive_tube_steps'], 1)
        self.assertEqual(s['frames_without_boxes'], 2)
        self.assertEqual(s['timestamp_mapping'], 'UNRESOLVED')
        self.assertFalse(s['empty_frames_are_verified_negatives'])

    def test_test_boxes_never_materialized(self):
        original = _Array.numeric
        calls = []
        def observe(array):
            calls.append(array.shape)
            return original(array)
        with patch.object(_Array, 'numeric', observe):
            result = self.read(self.fixture())
        self.assertEqual(calls, [(2, 5)])
        self.assertNotIn('reserved', result['tubes'])

    def test_rejects_test_selection_and_overlap(self):
        with self.assertRaisesRegex(ValueError, 'train sequences only'):
            self.read(self.fixture(), ['reserved'])
        d = self.fixture(); d['test_videos'] = [['train']]
        with self.assertRaisesRegex(ValueError, 'overlap'):
            self.read(d)

    def test_rejects_code_payload(self):
        class Payload:
            def __reduce__(self): return (eval, ('1 + 1',))
        with self.assertRaisesRegex(ValueError, 'Unsupported cache global'):
            self.read(Payload())

    def test_rejects_object_dtype_and_wrong_shape(self):
        for array in (np.array([[1, 2, 3, 4, 5]], dtype=object), np.ones((2, 6), dtype='f4')):
            d = self.fixture(); d['gttubes']['train'][0] = [array]
            with self.assertRaises(ValueError): self.read(d)

    def test_rejects_invalid_train_frames_and_boxes(self):
        for row in ([1.5, 2, 3, 8, 9], [0, 2, 3, 8, 9], [5, 2, 3, 8, 9],
                    [1, 2, 3, 2, 9], [1, 2, 3, 8, np.nan]):
            d = self.fixture(); d['gttubes']['train'][0] = [np.array([row], dtype='f4')]
            with self.subTest(row=row), self.assertRaises(ValueError): self.read(d)
        d = self.fixture(); d['gttubes']['train'][0][0][1, 0] = 1
        with self.assertRaises(ValueError): self.read(d)

    def test_outside_boxes_reported_without_clipping(self):
        d = self.fixture(); d['gttubes']['train'][0][0][0, 1] = -2
        r = self.read(d)
        self.assertEqual(audit_tubes(r['tubes']['train'], r['metadata']['train'])['boxes_outside_0_width_height'], 1)
        self.assertEqual(r['tubes']['train'][0][0, 1], -2)

    def test_rejects_oversize_trailing_bytes_and_wrong_class(self):
        with self.assertRaisesRegex(ValueError, 'budget'):
            read_train_cache(io.BytesIO(b'0' * (MAX_BYTES + 1)), ['train'])
        with self.assertRaisesRegex(ValueError, 'trailing'):
            read_train_cache(io.BytesIO(pickle.dumps(self.fixture(), protocol=3) + b'x'), ['train'])
        d = self.fixture(); d['labels'] = ['Car']
        with self.assertRaises(ValueError): self.read(d)

    def test_endianness_and_fortran_preserved(self):
        d = self.fixture()
        expected = np.array([[1, 2, 3, 8, 9], [3, 4, 5, 10, 12]], dtype='>f8', order='F')
        d['gttubes']['train'][0] = [expected]
        np.testing.assert_array_equal(self.read(d)['tubes']['train'][0], expected)


if __name__ == '__main__':
    unittest.main()
