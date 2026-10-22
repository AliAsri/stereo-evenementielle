"""Contract checks for the isolated diagnostic, without fitting the frozen cases."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

SPEC = importlib.util.spec_from_file_location(
    'rigid_ambiguity_diagnostic', Path(__file__).resolve().parents[1]
    / 'scripts/diagnostics/check_rigid_ambiguity.py')
diagnostic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostic)


class AmbiguityContractTests(unittest.TestCase):
    def setUp(self):
        self.p = np.tile([100., 100.], (24, 1))
        self.z = np.ones(24)
        self.k = np.eye(3)
        self.times = dict(previous_us=0, current_us=100000, depth_us=0,
                          depth_source='synthetic_reference')

    def model(self, residual=4., translation=0., valid=True):
        transform = np.eye(4)
        transform[0, 3] = translation
        return dict(valid=valid, status='ACCEPTED' if valid else 'REJECTED',
                    residual_px=[residual]*24, point_status=['RESIDUAL_CANDIDATE']*24,
                    transform_previous_to_current=transform.tolist(),
                    evaluated_points=24, predicted_pixels=self.p.tolist())

    def run_models(self, *models):
        with patch.object(diagnostic, 'estimate_rigid_motion', side_effect=models) as fit:
            result = diagnostic.diagnose(self.p, self.p, self.z, self.k, **self.times)
        return result, fit

    def test_rejected_primary_stops(self):
        result, fit = self.run_models(self.model(valid=False))
        self.assertEqual(fit.call_count, 1)
        self.assertEqual(result['primary'], result['final'])

    def test_strict_threshold_and_missing_depth_excluded(self):
        primary = self.model()
        primary['residual_px'][:3] = [3., None, float('nan')]
        self.z[3:6] = [0., -1., np.nan]
        result, fit = self.run_models(primary)
        self.assertEqual(result['secondary_indices'], list(range(6, 24)))
        self.assertEqual(fit.call_count, 1)

    def test_secondary_rejection_preserves_primary_without_retry(self):
        result, fit = self.run_models(self.model(), self.model(valid=False))
        self.assertEqual(fit.call_count, 2)
        self.assertEqual(result['primary'], result['final'])
        self.assertEqual(fit.call_args.kwargs, self.times)

    def test_three_pixel_separation_is_not_ambiguity(self):
        result, fit = self.run_models(self.model(), self.model(translation=3.))
        self.assertEqual(result['median_model_separation_px'], 3.)
        self.assertEqual(result['primary'], result['final'])

    def test_competing_models_remove_pose_and_all_classifications(self):
        result, fit = self.run_models(self.model(), self.model(translation=4.))
        self.assertEqual(fit.call_count, 2)
        self.assertFalse(result['final']['valid'])
        self.assertIsNone(result['final']['transform_previous_to_current'])
        self.assertEqual(result['final']['point_status'], ['UNKNOWN']*24)
        self.assertTrue(result['primary']['valid'])

    def test_points_behind_either_camera_are_excluded(self):
        secondary = self.model()
        secondary['transform_previous_to_current'][2][3] = -2.
        result, _ = self.run_models(self.model(), secondary)
        self.assertEqual(result['common_projectable_points'], 0)
        self.assertEqual(result['primary'], result['final'])

    def test_two_physical_worlds_have_identical_observations(self):
        a, b = diagnostic.concurrent_worlds()
        for key in ('previous', 'current', 'depth_m', 'intrinsic'):
            np.testing.assert_array_equal(a[key], b[key])
        self.assertFalse(np.array_equal(a['transform'], b['transform']))
        np.testing.assert_array_equal(a['moving'], ~b['moving'])


if __name__ == '__main__':
    unittest.main()
