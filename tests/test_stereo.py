"""Synthetic analytical checks, not experimental accuracy claims."""

import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pfe_events.pilot import load_manifest
from pfe_events.representations import rectified_counts, fit_log_normalizer, normalized_event_image
from pfe_events.stereo import StereoConfig, decode_sgbm, predict_stereo, disparity_metrics, aggregate_metrics


class ConcurrentStereoTests(unittest.TestCase):
    def test_parallel_matches_reference_and_reuses_worker(self):
        rng = np.random.default_rng(743)
        config = StereoConfig(num_disparities=16, speckle_window_size=0)
        with ThreadPoolExecutor(max_workers=1) as executor:
            for shift in (4, 7, 0):
                left = rng.integers(0, 256, (64, 160), dtype=np.uint8)
                right = np.roll(left, -shift, axis=1)
                left[:8] = 0
                right[:8] = 0
                expected = predict_stereo(left, right, config)
                actual = predict_stereo(left, right, config, executor=executor)
                for a, b in zip(expected[:3], actual[:3]):
                    np.testing.assert_array_equal(a, b)
                self.assertEqual(expected[3], actual[3])

    def test_worker_failure_is_not_silently_ignored(self):
        image = np.zeros((32, 160), dtype=np.uint8)
        with ThreadPoolExecutor(max_workers=1) as executor:
            with patch('pfe_events.stereo._reverse_match', side_effect=RuntimeError('reverse failed')):
                with self.assertRaisesRegex(RuntimeError, 'reverse failed'):
                    predict_stereo(image, image, StereoConfig(num_disparities=16), executor=executor)


class SplatTests(unittest.TestCase):
    def test_collision_accumulation_matches_sequential_reference_exactly(self):
        rng = np.random.default_rng(914)
        events = {'x': rng.integers(0, 9, 20000, dtype=np.uint16),
                  'y': rng.integers(0, 7, 20000, dtype=np.uint16),
                  'p': rng.integers(0, 2, 20000, dtype=np.uint8)}
        for dtype in (np.float32, np.float64):
            # Several native pixels map into the same cells; test collisions
            # both within one offset and between all four bilinear offsets.
            mapping = rng.uniform(.001, 2.999, (7, 9, 2)).astype(dtype)
            mapping[0, :3] = [[np.nan, 0], [-.01, 1], [4, 3]]
            xy = mapping[events['y'], events['x']]
            keep = np.isfinite(xy).all(axis=1) & (xy >= 0).all(axis=1) & (xy <= [4, 3]).all(axis=1)
            xy = xy[keep].astype(np.float64)
            floor = np.floor(xy); dx, dy = (xy-floor).T
            x, y = floor.astype(int).T; p = events['p'][keep]
            expected = np.zeros((2, 4, 5), np.float64)
            for ox, oy, weight in ((0,0,(1-dx)*(1-dy)), (1,0,dx*(1-dy)),
                                   (0,1,(1-dx)*dy), (1,1,dx*dy)):
                active = weight > 0
                np.add.at(expected, (p[active], y[active]+oy, x[active]+ox), weight[active])
            with self.subTest(dtype=dtype):
                actual, dropped = rectified_counts(events, mapping, 5, 4)
                np.testing.assert_array_equal(actual, expected.astype(np.float32))
                self.assertEqual(dropped, int((~keep).sum()))

    def test_rectification_still_rejects_invalid_events_without_native_counts(self):
        mapping = np.zeros((2, 2, 2), np.float32)
        for field, bad in [('x', [-1]), ('y', [2]), ('p', [2])]:
            events = {key: np.array([0]) for key in ('x', 'y', 'p')}
            events[field] = np.array(bad)
            with self.subTest(field=field), self.assertRaises(ValueError):
                rectified_counts(events, mapping, 2, 2)
        with self.assertRaises(TypeError):
            rectified_counts({'x': np.array([.5]), 'y': np.array([0]), 'p': np.array([0])}, mapping, 2, 2)

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

    def test_total_channel_exactly_matches_rgb_without_mutating_inputs(self):
        rng = np.random.default_rng(161)
        normalizer = {'scales': [2.1, 3.2, 4.3]}
        threshold = np.expm1((np.arange(255, dtype=np.float32)+.5)/255*np.float32(4.3))
        near_rounding = np.concatenate((np.nextafter(threshold, np.float32(0)),
                                       threshold, np.nextafter(threshold, np.float32(np.inf))))
        cases = [rng.integers(0, 100, (2, 19, 23), dtype=np.uint32),
                 rng.uniform(0, 10, (2, 19, 23)).astype(np.float32),
                 rng.uniform(0, 1e3, (2, 19, 23)),
                 np.stack((near_rounding, np.zeros_like(near_rounding)))[:, None, :],
                 np.zeros((2, 1, 1), np.float32),
                 np.empty((2, 0, 3), np.float32)]
        frozen = json.dumps(normalizer)
        for counts in cases:
            counts = counts[..., ::-1]  # Include noncontiguous inputs.
            before = counts.copy()
            with self.subTest(shape=counts.shape, dtype=counts.dtype):
                expected = normalized_event_image(counts, normalizer)[..., 2]
                actual = normalized_event_image(counts, normalizer, total_only=True)
                np.testing.assert_array_equal(actual, expected)
                np.testing.assert_array_equal(counts, before)
                self.assertEqual(actual.dtype, np.uint8)
                self.assertTrue(actual.flags.c_contiguous)
        self.assertEqual(json.dumps(normalizer), frozen)

    def test_total_channel_keeps_count_and_all_scale_checks(self):
        good = np.ones((2, 3, 4), np.float32)
        for counts in (good[0], np.full_like(good, -1),
                       np.full_like(good, np.nan), np.full_like(good, np.inf)):
            with self.assertRaises(ValueError):
                normalized_event_image(counts, {'scales': [1, 2, 3]}, total_only=True)
        # The complete frozen normalizer contract still applies, including
        # polarity scales even though the total-only path does not use them.
        for scales in ([1, 2], [0, 2, 3], [1, np.nan, 3], [1, 2, -3]):
            with self.subTest(scales=scales), self.assertRaises(ValueError):
                normalized_event_image(good, {'scales': scales}, total_only=True)


class StereoTests(unittest.TestCase):
    def test_search_depth_limit_uses_calibration_and_last_hypothesis(self):
        q = np.array([[1,0,0,-25],[0,1,0,-20],[0,0,0,570],[0,0,1/.6,0]],float)
        limit = StereoConfig().depth_range(q)
        self.assertEqual(limit['max_disparity_px'], 95)
        self.assertAlmostEqual(limit['min_z_m'], 3.6)
        self.assertFalse(limit['coverage_guaranteed'])
        self.assertAlmostEqual(StereoConfig(num_disparities=32).depth_range(q)['min_z_m'],342/31)
        q[2,3] *= 2
        self.assertAlmostEqual(StereoConfig().depth_range(q)['min_z_m'], 7.2)

    def test_unsupported_q_cannot_publish_a_false_depth_limit(self):
        q = np.array([[1,0,0,-25],[0,1,0,-20],[0,0,0,570],[0,0,1/.6,0]],float)
        for index,value in (((3,3),1.),((2,3),0.),((3,2),-1.),((0,1),.2),((0,0),np.nan)):
            bad=q.copy(); bad[index]=value
            with self.subTest(index=index), self.assertRaises(ValueError):
                StereoConfig().depth_range(bad)

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

    def test_search_border_recovers_known_planes_without_padding_depth(self):
        # Correspondences exist at x >= shift, including x < the search range.
        # Pixels x < shift have no true corresponding right pixel. Nearest-pixel
        # LR consistency can accept a few ambiguous pixels at the occlusion edge;
        # require abstention away from that edge and bound the accepted errors.
        for shift in (8, 32, 80):
            rng = np.random.default_rng(123)
            left = rng.integers(1, 256, (128, 320), dtype=np.uint8)
            right = np.zeros_like(left)
            right[:, :-shift] = left[:, shift:]
            with self.subTest(shift=shift):
                d, valid, _, _ = predict_stereo(left, right)
                roi = d[4:-4, shift:96]
                self.assertGreater(np.isfinite(roi).mean(), .85)
                self.assertLess(np.nanmean(np.abs(roi-shift)), .05)
                self.assertFalse(valid[:, :shift-1].any())
                self.assertLess(valid[:, :shift].mean(), .01)
                self.assertTrue(np.all(np.abs(d[:, :shift][valid[:, :shift]]-shift) <= 1.5))
                self.assertTrue(np.isnan(d[~valid]).all())

    def test_search_border_preserves_interior_and_preexisting_depths(self):
        rng = np.random.default_rng(724)
        left = rng.integers(1, 256, (128, 320), dtype=np.uint8)
        right = np.zeros_like(left)
        right[:, :-8] = left[:, 8:]
        left[20:70, 10:40] = 0
        right[50:100, 45:75] = 0  # Absent support within the corrected band.
        originals = left.copy(), right.copy()
        factory = cv2.StereoSGBM_create

        class WithoutBorder:
            def __init__(self, *args, **kwargs):
                self.matcher = factory(*args, **kwargs)

            def compute(self, a, b):
                # Keep real full-image forward/reverse passes, but suppress
                # candidates from the additional cropped pass for the control.
                if a.shape != left.shape:
                    return np.full(a.shape, -16, np.int16)
                return self.matcher.compute(a, b)

        with patch('pfe_events.stereo.cv2.StereoSGBM_create', WithoutBorder):
            control = predict_stereo(left, right)
        actual = predict_stereo(left, right)
        self.assertGreater(actual[1].sum(), control[1].sum())
        for before, after in zip(control[:3], actual[:3]):
            np.testing.assert_array_equal(before[:, 96:], after[:, 96:])
        np.testing.assert_array_equal(control[0][control[1]], actual[0][control[1]])
        self.assertFalse(actual[1][23:67, 13:37].any())
        for before, after in zip(originals, (left, right)):
            np.testing.assert_array_equal(before, after)

    def test_two_threads_preserve_disparity_and_abstentions(self):
        rng = np.random.default_rng(802)
        left = rng.integers(0, 256, size=(96, 192), dtype=np.uint8)
        right = np.zeros_like(left)
        right[:, :-8] = left[:, 8:]
        # Missing support and occlusion must preserve abstentions too.
        left[20:45, 70:100] = 0
        right[50:75, 100:130] = 0
        original_threads = cv2.getNumThreads()
        try:
            cv2.setNumThreads(1)
            reference = predict_stereo(left, right, StereoConfig(num_disparities=32))
            cv2.setNumThreads(2)
            actual = predict_stereo(left, right, StereoConfig(num_disparities=32))
        finally:
            cv2.setNumThreads(original_threads)
        self.assertTrue(reference[1].any())
        self.assertTrue((~reference[1]).any())
        for expected, observed in zip(reference[:3], actual[:3]):
            np.testing.assert_array_equal(expected, observed)
        self.assertEqual(reference[3], actual[3])

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
