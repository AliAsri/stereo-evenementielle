"""Corrupt saved arrays must not silently hide tracks in the offline viewer."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inspection_builder', ROOT / 'scripts/build_inspection_viewer.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ViewerAlignmentTests(unittest.TestCase):
    def fixture(self):
        return ({'current': np.zeros((2, 2)), 'previous': np.zeros((2, 2)),
                 'depth_samples': np.array([1., np.nan])},
                {'point_status': ['MODEL_CONSISTENT', 'UNKNOWN'],
                 'predicted_pixels': [[0., 0.], None], 'residual_px': [0., None]})

    def test_missing_depth_is_a_value_not_a_missing_track(self):
        arrays, model = self.fixture()
        builder.validate_track_alignment(arrays, model)

    def test_truncated_or_extra_array_tracks_rejected(self):
        for key in ('previous', 'depth_samples'):
            for count in (1, 3):
                arrays, model = self.fixture()
                arrays[key] = np.zeros((count, 2) if key == 'previous' else (count,))
                with self.subTest(key=key, count=count), self.assertRaises(ValueError):
                    builder.validate_track_alignment(arrays, model)

    def test_model_vectors_cannot_be_truncated(self):
        for key in ('point_status', 'predicted_pixels', 'residual_px'):
            arrays, model = self.fixture()
            model[key] = model[key][:1]
            with self.subTest(key=key), self.assertRaises(ValueError):
                builder.validate_track_alignment(arrays, model)


if __name__ == '__main__':
    unittest.main()
