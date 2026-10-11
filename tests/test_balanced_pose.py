import unittest
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.balanced_pose import balanced_indices, estimate_balanced_motion


class BalancedPoseTests(unittest.TestCase):
    def setUp(self):
        self.k = np.array([[400., 0, 320], [0, 400, 240], [0, 0, 1]])
        self.p = np.array([(x, y) for y in range(60, 421, 30)
                          for x in range(60, 581, 20)], dtype=float)
        self.z = 8 + np.arange(len(self.p)) % 13
        xyz = np.column_stack(((self.p[:, 0]-320)/400*self.z,
                               (self.p[:, 1]-240)/400*self.z, self.z))
        xyz += [0.03, -0.02, 0.01]
        self.q = (xyz @ self.k.T)[:, :2]/xyz[:, 2, None]
        self.kw = dict(previous_us=100000, current_us=200000,
                       depth_us=100000, depth_source='synthetic_reference')

    def test_recovers_known_translation_and_evaluates_unselected(self):
        r = estimate_balanced_motion(self.p, self.q, self.z, self.k,
                                    np.zeros(len(self.p)), **self.kw)
        self.assertTrue(r['valid'])
        self.assertEqual(r['evaluated_points'], len(self.p))
        self.assertLess(len(r['sampling']['selected_indices']), len(self.p))
        np.testing.assert_allclose(np.asarray(r['transform_previous_to_current'])[:3, 3],
                                   [0.03, -0.02, 0.01], atol=1e-5)
        self.assertLess(max(r['residual_px']), 1e-4)

    def test_missing_depth_stays_unknown(self):
        z = self.z.astype(float); z[0] = np.nan
        r = estimate_balanced_motion(self.p, self.q, z, self.k, np.zeros(len(z)), **self.kw)
        self.assertTrue(r['valid']); self.assertEqual(r['point_status'][0], 'UNKNOWN')
        self.assertIsNone(r['residual_px'][0])

    def test_concentrated_support_abstains(self):
        p = np.array([(10+i, 10+i%3) for i in range(30)], float)
        r = estimate_balanced_motion(p, p, np.ones(30)*10, self.k, np.zeros(30), **self.kw)
        self.assertFalse(r['valid']); self.assertEqual(r['evaluated_points'], 0)
        self.assertTrue(all(s == 'UNKNOWN' for s in r['point_status']))

    def test_selection_is_capped_and_uses_fb_order(self):
        p = np.array([(10+i, 10) for i in range(10)], float)
        selected = balanced_indices(p, np.ones(10), np.arange(10)[::-1])
        np.testing.assert_array_equal(selected, [6, 7, 8, 9])

    def test_future_depth_rejected(self):
        kw = dict(self.kw, depth_us=100001)
        with self.assertRaises(ValueError):
            estimate_balanced_motion(self.p, self.q, self.z, self.k, np.zeros(len(self.p)), **kw)

    def test_invalid_coordinates_or_fb_rejected(self):
        with self.assertRaises(ValueError):balanced_indices([[-1., 1]], [10], [0])
        with self.assertRaises(ValueError):balanced_indices([[1., 1]], [10], [np.nan])


if __name__ == '__main__': unittest.main()
