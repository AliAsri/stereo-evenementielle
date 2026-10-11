"""Checks the artificial control generation and source-onset measurements."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.motion import ActivityConfig
from pfe_events.motion_controls import make_control, replay_control


class MotionControlTests(unittest.TestCase):
    def config(self, **kwargs):
        return ActivityConfig(width=128, height=96, **kwargs)

    def test_no_source_events_before_onset_and_exact_counts(self):
        e = make_control('local_onset', onset_us=405000, strength=8, noise_rate=0)
        self.assertEqual(e['t_us'][0], 405000)
        self.assertTrue(np.all(e['t_us'][1:] >= e['t_us'][:-1]))
        self.assertEqual(len(e['x']), 595*16)
        self.assertEqual(set(e['y']), {33})

    def test_seeded_background_and_sources_are_reproducible(self):
        a = make_control('local_onset'); b = make_control('local_onset')
        for key in a: np.testing.assert_array_equal(a[key], b[key])

    def test_phase_changes_delay_and_persistence_is_not_a_delay_floor(self):
        delays = []
        for onset in (400000, 405000):
            e = make_control('local_onset', onset_us=onset, strength=24, noise_rate=0)
            result, _ = replay_control(e, self.config(), 10000, 1000000, onset_us=onset)
            self.assertTrue(result['response']); delays.append(result['delay_event_ms'])
        self.assertEqual(delays, [20, 15])

    def test_weak_source_miss_has_no_zero_delay(self):
        e = make_control('local_onset', strength=2, noise_rate=0)
        result, _ = replay_control(e, self.config(), 10000, 1000000, onset_us=400000)
        self.assertFalse(result['response']); self.assertIsNone(result['delay_event_ms'])

    def test_empty_and_hot_pixel_are_negative_but_global_burst_confounds(self):
        for kind in ('empty', 'hot_pixel', 'global_burst'):
            result, _ = replay_control(make_control(kind), self.config(), 10000, 1000000)
            if kind == 'global_burst':
                self.assertEqual(result['false_alert_starts'], 1)
                self.assertGreater(result['false_alert_active_seconds'], 0)
            else:
                self.assertEqual(result['false_alert_frame_fraction'], 0)


if __name__ == '__main__': unittest.main()
