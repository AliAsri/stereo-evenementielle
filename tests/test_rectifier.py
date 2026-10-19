"""Exact regression against the independent event-wise bilinear reference."""
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.representations import (BilinearRectifier, rectified_counts,
                                      polarity_counts, normalized_event_image,
                                      stereo_event_images)


class RectifierTests(unittest.TestCase):
    def test_zero_weight_border_offsets_do_not_wrap_or_expand_histogram(self):
        # Integer centers generate three zero weights per event, including
        # destinations beyond the final bin for positive bottom/right events.
        for height, width in ((1, 1), (1, 4), (4, 1), (4, 6)):
            y, x = np.indices((height, width))
            mapping = np.stack((x, y), axis=-1).astype(np.float64)
            events = dict(x=np.tile(x.ravel(), 8), y=np.tile(y.ravel(), 8),
                          p=np.repeat(np.arange(8) % 2, height*width))
            counts, dropped = BilinearRectifier(mapping, width, height).counts(events)
            np.testing.assert_array_equal(counts, polarity_counts(events, width, height))
            self.assertEqual(dropped, 0)

    def test_collisions_polarities_invalid_centers_and_edges(self):
        rng = np.random.default_rng(42)
        for dtype in (np.float32, np.float64):
            mapping = rng.uniform(-1, 6, (5, 7, 2)).astype(dtype)
            mapping[0, :5] = [[0, 0], [6, 4], [np.nan, 1], [1, np.inf], [2.25, 1.75]]
            events = dict(x=rng.integers(0, 7, 10000), y=rng.integers(0, 5, 10000),
                          p=rng.integers(0, 2, 10000))
            expected, dropped = rectified_counts(events, mapping, 7, 5)
            actual, actual_dropped = BilinearRectifier(mapping, 7, 5).counts(events)
            np.testing.assert_array_equal(actual, expected)
            self.assertEqual(actual_dropped, dropped)

    def test_empty_and_all_rejected(self):
        mapping = np.full((2, 3, 2), np.nan)
        rectifier = BilinearRectifier(mapping, 3, 2)
        for size in (0, 3):
            events = {k: np.zeros(size, dtype=np.int64) for k in ('x', 'y', 'p')}
            counts, dropped = rectifier.counts(events)
            self.assertFalse(counts.any())
            self.assertEqual(dropped, size)

    def test_calibration_snapshot_and_validation(self):
        mapping = np.zeros((2, 3, 2))
        rectifier = BilinearRectifier(mapping, 3, 2)
        mapping[:] = np.nan
        events = {k: np.array([0]) for k in ('x', 'y', 'p')}
        self.assertEqual(rectifier.counts(events)[0].sum(), 1)
        for key, value in (('x', 3), ('y', -1), ('p', 2)):
            with self.assertRaises(ValueError):
                rectifier.counts({**events, key: np.array([value])})
        with self.assertRaises(TypeError):
            rectifier.counts({**events, 'x': np.array([0.5])})

    def test_parallel_images_equal_independent_reference_and_leave_inputs_intact(self):
        rng = np.random.default_rng(318)
        maps = [rng.uniform(-1, 6, (5, 7, 2)).astype(np.float32) for _ in range(2)]
        maps[0][0, 0] = [np.nan, 1]
        rectifiers = [BilinearRectifier(m, 7, 5) for m in maps]
        normalizer = {'scales': [2., 3., 4.]}
        with ThreadPoolExecutor(max_workers=1) as worker:
            for size in (0, 10000):
                events = [dict(x=rng.integers(0, 7, size), y=rng.integers(0, 5, size),
                               p=rng.integers(0, 2, size)) for _ in range(2)]
                originals = [{k: a.copy() for k, a in e.items()} for e in events]
                expected = [normalized_event_image(polarity_counts(events[0], 7, 5), normalizer),
                            *[normalized_event_image(rectified_counts(e, m, 7, 5)[0], normalizer,
                                                     total_only=True) for e, m in zip(events, maps)]]
                for executor in (None, worker):
                    native, rectified = stereo_event_images(events, rectifiers, normalizer, executor=executor)
                    for actual, reference in zip([native, *rectified], expected):
                        np.testing.assert_array_equal(actual, reference)
                for old, new in zip(originals, events):
                    for key in old:
                        np.testing.assert_array_equal(old[key], new[key])

    def test_right_failure_propagates_and_worker_can_be_reused(self):
        mapping = np.zeros((2, 3, 2))
        rectifiers = [BilinearRectifier(mapping, 3, 2) for _ in range(2)]
        events = [{k: np.array([0]) for k in ('x', 'y', 'p')} for _ in range(2)]
        with ThreadPoolExecutor(max_workers=1) as worker:
            with patch.object(rectifiers[1], 'counts', side_effect=ValueError('right failure')):
                with self.assertRaisesRegex(ValueError, 'right failure'):
                    stereo_event_images(events, rectifiers, {'scales': [1, 1, 1]}, executor=worker)
            stereo_event_images(events, rectifiers, {'scales': [1, 1, 1]}, executor=worker)

    def test_deferred_native_skips_rgb_work_and_preserves_rectified_images(self):
        rng = np.random.default_rng(619)
        maps = [rng.uniform(-1, 6, (5, 7, 2)) for _ in range(2)]
        rectifiers = [BilinearRectifier(m, 7, 5) for m in maps]
        normalizer = {'scales': [2., 3., 4.]}
        events = [dict(x=rng.integers(0, 7, 1000), y=rng.integers(0, 5, 1000),
                       p=rng.integers(0, 2, 1000)) for _ in range(2)]
        with ThreadPoolExecutor(max_workers=1) as worker:
            expected_native, expected = stereo_event_images(events, rectifiers, normalizer,
                                                            executor=worker)
            for executor in (None, worker):
                with patch('pfe_events.representations.polarity_counts',
                           side_effect=AssertionError('RGB must be deferred')):
                    native, actual = stereo_event_images(events, rectifiers, normalizer,
                                                         executor=executor, include_native=False)
                self.assertIsNone(native)
                for image, reference in zip(actual, expected):
                    np.testing.assert_array_equal(image, reference)
            np.testing.assert_array_equal(
                normalized_event_image(polarity_counts(events[0], 7, 5), normalizer), expected_native)

    def test_left_failure_waits_for_right_worker_before_returning(self):
        mapping = np.zeros((2, 3, 2))
        rectifiers = [BilinearRectifier(mapping, 3, 2) for _ in range(2)]
        events = [{k: np.array([0]) for k in ('x', 'y', 'p')} for _ in range(2)]
        started, release, finished = Event(), Event(), Event()
        original = rectifiers[1].counts
        def right(values):
            started.set()
            if not release.wait(timeout=5):
                raise RuntimeError('test synchronization failed')
            try:
                return original(values)
            finally:
                finished.set()
        def fail_left(values):
            if not started.wait(timeout=5):
                raise RuntimeError('worker did not start')
            release.set()
            raise ValueError('left failure')
        with ThreadPoolExecutor(max_workers=1) as worker, \
                patch.object(rectifiers[0], 'counts', side_effect=fail_left), \
                patch.object(rectifiers[1], 'counts', side_effect=right):
            with self.assertRaisesRegex(ValueError, 'left failure'):
                stereo_event_images(events, rectifiers, {'scales': [1, 1, 1]}, executor=worker)
            self.assertTrue(finished.is_set())


if __name__ == '__main__':
    unittest.main()
