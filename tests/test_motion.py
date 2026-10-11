"""Analytical activity timing/causality; these are not DSEC motion accuracy tests."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from pfe_events.motion import ActivityConfig, ActivityDetector


def events(x=(), y=(), t=()):
    return {"x": np.asarray(x, dtype=np.int64), "y": np.asarray(y, dtype=np.int64),
            "t_us": np.asarray(t, dtype=np.int64)}


def cluster(t):
    return events([1, 2, 3, 4, 17, 18, 19, 20]*20, [1]*160, [t]*160)


class MotionTests(unittest.TestCase):
    def test_onset_and_persistence(self):
        detector = ActivityDetector()
        first = detector.update(cluster(5000), 0, 10_000)
        self.assertFalse(first["regions"])
        second = detector.update(cluster(15_000), 10_000, 20_000)
        self.assertEqual(second["regions"][0]["xyxy"], [0, 0, 32, 16])
        self.assertEqual(second["regions"][0]["timestamp_us"]-5000, 15_000)
        self.assertFalse(detector.update(events(), 20_000, 30_000)["regions"])

    def test_hot_pixel_rejected_even_with_many_events(self):
        detector = ActivityDetector()
        e = events([1]*10_000, [1]*10_000, [1]*10_000)
        self.assertFalse(detector.update(e, 0, 50_000)["candidate"].any())

    def test_no_future_events_no_state_change_on_error(self):
        detector = ActivityDetector()
        with self.assertRaises(ValueError):
            detector.update(cluster(10_000), 0, 10_000)
        self.assertIsNone(detector.previous_end)
        detector.update(cluster(5000), 0, 10_000)
        with self.assertRaises(ValueError):
            detector.update(cluster(25_000), 20_000, 30_000)

    def test_rate_units_and_partial_border_cell(self):
        detector = ActivityDetector(ActivityConfig(width=18, height=18))
        e = events([16, 17, 16, 17], [16, 16, 17, 17], [5]*4)
        out = detector.update(e, 0, 10_000)
        self.assertAlmostEqual(out["rate"][1, 1], 100)
        self.assertAlmostEqual(float((out["rate"]*detector.area*.01).sum()), 4)

    def test_widespread_activity_is_not_ego_motion_compensation(self):
        detector = ActivityDetector(ActivityConfig(width=32, height=16))
        out = detector.update(cluster(1000), 0, 10_000)
        self.assertTrue(out["widespread_activity"])
        self.assertFalse(out["regions"])  # persistence still required

    def test_invalid_time_order_coordinates_and_configuration(self):
        for e in [events([1, 2], [1, 1], [3, 2]), events([640], [1], [1])]:
            with self.assertRaises(ValueError):
                ActivityDetector().update(e, 0, 10_000)
        with self.assertRaises(ValueError):
            ActivityDetector(ActivityConfig(min_rate=float("nan")))


if __name__ == "__main__":
    unittest.main()
