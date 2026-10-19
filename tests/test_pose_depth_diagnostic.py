"""Guard the denominators and reciprocal-disparity metric of the offline control."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'diagnostics'))
from analyze_pose_components import depth_reference_metrics, project_fixed_pose


class DepthReferenceMetricsTests(unittest.TestCase):
    def test_missing_predictions_are_not_hidden_in_coverage(self):
        result = depth_reference_metrics([10, np.nan, 8, 0], [5, 4, np.nan, -1], focal_baseline=100)
        self.assertEqual((result['tracks'], result['predicted'], result['reference'], result['paired']), (4, 2, 2, 1))
        self.assertEqual(result['paired_fraction_of_reference'], .5)
        self.assertEqual(result['reference_without_prediction'], 1)
        self.assertEqual(result['predicted_without_reference'], 1)
        self.assertEqual(result['disparity_mae_px'], 10)
        self.assertEqual(result['depth_mae_m'], 5)
        self.assertEqual(result['depth_median_relative_error'], 1)

    def test_empty_support_is_not_zero_error(self):
        for p, r in [([], []), ([np.nan], [10]), ([10], [np.nan])]:
            result = depth_reference_metrics(p, r, focal_baseline=100)
            self.assertIsNone(result['disparity_mae_px'])
            self.assertIsNone(result['depth_mae_m'])
            self.assertIsNone(result['disparity_bad3_fraction'])
        self.assertIsNone(result['paired_fraction_of_reference'])

    def test_bad3_is_strict_and_inputs_are_validated(self):
        result = depth_reference_metrics([1], [4], focal_baseline=4)
        self.assertEqual(result['disparity_mae_px'], 3)
        self.assertEqual(result['disparity_bad3_count'], 0)
        for p, r, fb in [([1], [], 1), ([[1]], [[1]], 1), ([1], [1], 0), ([1], [1], np.nan)]:
            with self.assertRaises(ValueError):
                depth_reference_metrics(p, r, focal_baseline=fb)


class FixedPoseProjectionTests(unittest.TestCase):
    def test_lateral_translation_has_known_inverse_depth_effect(self):
        k=np.diag([100.,100.,1.]); t=np.eye(4); t[0,3]=1
        uv,valid=project_fixed_pose([[0,0],[0,0]],[10,20],k,t)
        np.testing.assert_allclose(uv,[[10,0],[5,0]])
        self.assertTrue(valid.all())

    def test_pure_rotation_is_independent_of_depth(self):
        k=np.array([[100.,0,32],[0,100,24],[0,0,1]])
        a=.1;t=np.eye(4)
        t[:3,:3]=[[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]]
        first,_=project_fixed_pose([[40,30]],[2],k,t)
        second,_=project_fixed_pose([[40,30]],[200],k,t)
        np.testing.assert_allclose(first,second,atol=1e-12)

    def test_missing_and_behind_camera_points_remain_unknown(self):
        t=np.eye(4);t[2,3]=-5
        uv,valid=project_fixed_pose(np.zeros((5,2)),[np.nan,0,4,5,10],np.eye(3),t)
        np.testing.assert_array_equal(valid,[False,False,False,False,True])
        self.assertTrue(np.isnan(uv[:4]).all())
        empty,mask=project_fixed_pose(np.empty((0,2)),[],np.eye(3),t)
        self.assertEqual(empty.shape,(0,2));self.assertEqual(mask.shape,(0,))

    def test_nonrigid_transform_is_rejected(self):
        t=np.eye(4);t[0,0]=2
        with self.assertRaises(ValueError):
            project_fixed_pose([[0,0]],[1],np.eye(3),t)


if __name__ == '__main__':
    unittest.main()
