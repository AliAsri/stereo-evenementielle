"""Analytical image-motion controls, not real-world independent motion accuracy."""
import sys
import unittest
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from pfe_events.global_motion import GlobalMotionDetector, event_gray, fit_apparent_motion


class GlobalMotionTests(unittest.TestCase):
    def points(self):
        x, y = np.meshgrid(np.linspace(20, 290, 10), np.linspace(20, 210, 8))
        return np.column_stack([x.ravel(), y.ravel()]).astype(np.float32)

    def test_global_translation_has_no_residual_regions(self):
        p = self.points()
        result = fit_apparent_motion(p, p+[2, -1])
        self.assertTrue(result['valid'])
        np.testing.assert_allclose(np.array(result['matrix_working_pixels'])[:, 2], [2, -1], atol=1e-4)
        self.assertFalse(result['regions'])

    def test_local_extra_translation_is_a_residual_candidate(self):
        p = self.points(); q = p+np.array([2, -1], np.float32)
        q[22:26] += [5, 0]
        result = fit_apparent_motion(p, q)
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['residual_points_native']), 4)
        self.assertTrue(result['regions'])

    def test_local_support_is_not_a_valid_global_model(self):
        p = self.points()*.05
        result = fit_apparent_motion(p, p+[2, 0])
        self.assertFalse(result['valid'])
        self.assertEqual(result['status'], 'INSUFFICIENT_GLOBAL_SUPPORT')
        self.assertFalse(result['regions'])

    def test_empty_image_abstains_and_timestamp_gap_is_rejected(self):
        detector = GlobalMotionDetector(); image = np.zeros((240, 320), np.uint8)
        self.assertEqual(detector.update(image, 20000)['status'], 'WARMUP')
        self.assertEqual(detector.update(image, 40000)['status'], 'NO_FEATURES')
        with self.assertRaises(ValueError): detector.update(image, 80000)

    def test_lk_translation_on_synthetic_texture(self):
        rng = np.random.default_rng(42)
        im = cv2.GaussianBlur(rng.integers(0, 256, (240, 320), dtype=np.uint8), (5, 5), 0)
        shifted = cv2.warpAffine(im, np.float32([[1, 0, 2], [0, 1, 1]]), (320, 240))
        detector = GlobalMotionDetector(); detector.update(im, 20000)
        result = detector.update(shifted, 40000)
        self.assertTrue(result['valid'])
        np.testing.assert_allclose(np.array(result['matrix_working_pixels'])[:, 2], [2, 1], atol=.25)

    def test_event_frame_uses_fixed_scale_and_checks_bounds(self):
        empty = {'x': np.array([], dtype=int), 'y': np.array([], dtype=int)}
        self.assertFalse(event_gray(empty).any())
        with self.assertRaises(ValueError): event_gray({'x': np.array([640]), 'y': np.array([0])})


if __name__ == '__main__': unittest.main()
