"""Isolated baseline contracts; these mocks do not run the comparison scenes."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np

SPEC = importlib.util.spec_from_file_location('homography_comparison',
    Path(__file__).resolve().parents[1]/'scripts/diagnostics/compare_homography_compensation.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class HomographyTests(unittest.TestCase):
    def setUp(self):
        x, y = np.meshgrid(np.linspace(40, 600, 6), np.linspace(40, 440, 5))
        self.p = np.column_stack((x.ravel(), y.ravel()))
        self.config = dict(frame_size=[640,480], min_points=20, min_inliers=16,
                           min_fraction=.6, min_hull_fraction=.1, rng_seed=42,
                           ransac_px=1.5, residual_px=3., iterations=500, confidence=.999)

    def test_insufficient_points_do_not_fit(self):
        with patch.object(module.cv2, 'findHomography') as fit:
            out = module.estimate(self.p[:19], self.p[:19], self.config)
        fit.assert_not_called()
        self.assertFalse(out['valid'])

    def test_singular_model_rejected(self):
        with patch.object(module.cv2, 'findHomography', return_value=(np.zeros((3,3)), None)):
            self.assertFalse(module.estimate(self.p, self.p, self.config)['valid'])

    def test_recomputes_support_and_strict_candidate_threshold(self):
        q = self.p.copy()
        q[0,0] += 3.
        q[1,0] += 3.01
        with patch.object(module.cv2, 'findHomography', return_value=(np.eye(3), None)) as fit:
            out = module.estimate(self.p, q, self.config)
        self.assertEqual(fit.call_count, 1)
        self.assertTrue(out['valid'])
        self.assertEqual(out['inliers'], 28)
        self.assertEqual(out['point_status'][:2], ['MODEL_CONSISTENT','RESIDUAL_CANDIDATE'])

    def test_invalid_observations_rejected(self):
        q = self.p.copy()
        q[0,0] = np.nan
        with self.assertRaises(ValueError):
            module.estimate(self.p, q, self.config)


if __name__ == '__main__':
    unittest.main()
