"""Adaptive activity controls, not motion-accuracy evidence."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.motion import ActivityConfig
from pfe_events.adaptive_activity import AdaptiveConfig, AdaptiveActivityDetector
from pfe_events.motion_controls import make_control


def window(events, start, end):
    lo, hi = np.searchsorted(events['t_us'], [start, end])
    return {k: v[lo:hi] for k, v in events.items()}


class AdaptiveActivityTests(unittest.TestCase):
    def detector(self, mode='relative_history'):
        return AdaptiveActivityDetector(ActivityConfig(width=128, height=96), AdaptiveConfig(mode=mode))

    def test_uniform_burst_suppressed_and_local_onset_kept(self):
        for kind in ('global_burst', 'local_onset'):
            detector = self.detector(); events = make_control(kind)
            active = []
            for start in range(0, 600000, 10000):
                result = detector.update(window(events, start, start+10000), start, start+10000)
                if start >= 400000: active.append(bool(result['regions']))
            self.assertEqual(any(active), kind == 'local_onset')

    def test_warmup_is_unknown_and_cannot_accumulate_persistence(self):
        detector = self.detector('relative'); events = make_control('local_onset', onset_us=0, strength=24)
        for start in range(0, 210000, 10000):
            result = detector.update(window(events, start, start+10000), start, start+10000)
            if start < 200000:
                self.assertFalse(result['valid']); self.assertFalse(result['regions'])
        self.assertTrue(result['valid']); self.assertFalse(result['regions'])
        self.assertTrue(detector.update(window(events,210000,220000),210000,220000)['regions'])

    def test_first_onset_threshold_uses_past_history_only(self):
        detector = self.detector(); events = make_control('local_onset', onset_us=400000, strength=24, noise_rate=0)
        for start in range(0, 400000, 10000):
            detector.update(window(events,start,start+10000),start,start+10000)
        out = detector.update(window(events,400000,410000),400000,410000)
        self.assertEqual(float(out['threshold_excess'][2,1]), 20)
        self.assertTrue(out['candidate'][2,1])
        self.assertGreater(detector.history[2,1], 0)

    def test_future_event_rejection_preserves_history(self):
        detector = self.detector(); old = detector.history.copy()
        events = {'x': np.array([1]), 'y': np.array([1]), 't_us': np.array([10000])}
        with self.assertRaises(ValueError): detector.update(events,0,10000)
        np.testing.assert_array_equal(detector.history,old)
        self.assertEqual(detector.seen_us,0)

    def test_history_can_absorb_persistent_source_must_not_claim_tracking(self):
        detector = self.detector(); events = make_control('local_onset', strength=24, noise_rate=0)
        outputs = []
        for start in range(0,1000000,10000):
            out = detector.update(window(events,start,start+10000),start,start+10000)
            outputs.append(bool(out['regions']))
        self.assertTrue(any(outputs[40:60])); self.assertFalse(outputs[-1])

    def test_invalid_parameters(self):
        for config in (AdaptiveConfig(mode='unknown'), AdaptiveConfig(history_tau_us=0),
                       AdaptiveConfig(global_mad_factor=float('nan'))):
            with self.assertRaises(ValueError): AdaptiveActivityDetector(adaptive=config)


if __name__ == '__main__': unittest.main()
