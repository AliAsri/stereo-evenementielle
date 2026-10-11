"""Synthetic analytical checks, not experimental accuracy claims."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pfe_events.pilot import load_manifest
from pfe_events.representations import rectified_counts, fit_log_normalizer, normalized_event_image
from pfe_events.stereo import StereoConfig, decode_sgbm, predict_stereo, disparity_metrics, aggregate_metrics


class SplatTests(unittest.TestCase):
    def test_subpixel_mass_and_boundary(self):
        mapping = np.array([[[.25, .5], [1., 1.], [-.01, 0.], [np.nan, 0.]]])
        events = {"x": np.arange(4), "y": np.zeros(4, dtype=int), "p": np.array([0, 1, 0, 0])}
        counts, dropped = rectified_counts(events, mapping, 2, 2)
        self.assertEqual(dropped, 2)
        np.testing.assert_allclose(counts[0], [[.375, .125], [.375, .125]])
        self.assertEqual(counts[1, 1, 1], 1)
        self.assertEqual(counts.sum(), 2)

    def test_empty_events(self):
        events = {k: np.array([], dtype=int) for k in ("x", "y", "p")}
        counts, dropped = rectified_counts(events, np.zeros((2, 2, 2)), 2, 2)
        self.assertEqual(counts.sum(), 0)
        self.assertEqual(dropped, 0)

    def test_train_only_shared_normalization(self):
        train = np.array([[[0, 3]], [[1, 0]]], dtype=float)
        fitted = fit_log_normalizer([train], source_split="train", percentile=100)
        np.testing.assert_allclose(fitted["scales"], np.log1p([1, 3, 3]))
        image = normalized_event_image(train, fitted)
        np.testing.assert_array_equal(image[0, 0, :2], [255, 0])
        np.testing.assert_array_equal(image[0, 1, :2], [0, 255])
        prior = json.dumps(fitted)
        self.assertTrue((normalized_event_image(train*100, fitted) <= 255).all())
        self.assertEqual(json.dumps(fitted), prior)
        with self.assertRaises(ValueError):
            fit_log_normalizer([train], source_split="validation")


class StereoTests(unittest.TestCase):
    def test_invalid_configuration_cannot_disable_consistency(self):
        for tolerance in (float('nan'), float('inf'), -float('inf'), -1):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                StereoConfig(lr_tolerance_px=tolerance)
        for field, value in [('num_disparities', 96.0), ('block_size', 5.0),
                             ('uniqueness_ratio', -1), ('speckle_window_size', -1),
                             ('speckle_range', -1), ('speckle_range', True)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                StereoConfig(**{field: value})

    def test_fixed_point_scale_and_invalids(self):
        d = decode_sgbm(np.array([[-16, 0, 16, 160]], dtype=np.int16))
        self.assertTrue(np.isnan(d[0, :2]).all())
        np.testing.assert_array_equal(d[0, 2:], [1, 10])

    def test_known_shift_and_right_consistency(self):
        # SYNTHETIC textured planes: x_right = x_left - 8, no scene complexity.
        rng = np.random.default_rng(123)
        left = rng.integers(0, 256, size=(64, 192), dtype=np.uint8)
        right = np.zeros_like(left)
        right[:, :-8] = left[:, 8:]
        cv2.setNumThreads(1)
        d, valid, _, _ = predict_stereo(left, right, StereoConfig(num_disparities=32))
        roi = d[8:-8, 48:144]
        self.assertGreater(np.isfinite(roi).mean(), .9)
        self.assertLess(np.nanmean(np.abs(roi-8)), .15)
        self.assertTrue(np.isnan(d[~valid]).all())

    def test_empty_images_produce_no_depth(self):
        image = np.zeros((32, 160), dtype=np.uint8)
        d, valid, _, _ = predict_stereo(image, image)
        self.assertFalse(valid.any())
        self.assertTrue(np.isnan(d).all())

    def test_metrics_include_missing_predictions_in_coverage(self):
        gt = np.array([[1., 2., 3., 4., np.nan]])
        pred = np.array([[1., 6., np.nan, 0., 2.]])
        row = disparity_metrics(pred, gt)
        self.assertEqual(row["epe_px"], 2)
        self.assertEqual(row["gt_coverage"], .5)
        self.assertEqual(row["bad3_fraction"], .5)
        self.assertEqual(row["bad3_or_missing_fraction"], .75)
        combined = aggregate_metrics([row, row])
        self.assertEqual(combined["epe_px"], 2)
        self.assertEqual(combined["gt_pixels"], 8)
        none = disparity_metrics(np.full_like(gt, np.nan), gt)
        self.assertIsNone(none["epe_px"])
        self.assertEqual(none["gt_coverage"], 0)
        self.assertEqual(none["bad3_or_missing_fraction"], 1)

    def test_group_leakage_rejected(self):
        temp_root = ROOT / "outputs/test-temp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as folder:
            path = Path(folder) / "manifest.json"
            path.write_text(json.dumps({"sequences": [
                {"name": "zurich_city_04_e", "group": "zurich_city_04", "split": "train"},
                {"name": "zurich_city_04_b", "group": "zurich_city_04", "split": "validation"}]}))
            with self.assertRaises(ValueError):
                load_manifest(path)


if __name__ == "__main__":
    unittest.main()
