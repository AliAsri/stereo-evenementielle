"""Synthetic annotations test metric semantics; never real movement GT."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.motion_evaluation import SCHEMA, evaluate_annotations


class MotionEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {'schema': SCHEMA, 'width': 640, 'height': 480, 'clips': [
            {'id': 'synthetic', 'split': 'synthetic', 'start_us': 0, 'end_us': 300000,
             'step_us': 20000, 'frames': [{'end_us': t} for t in range(20000, 300001, 20000)]}]}
        self.annotation = {'clip_id': 'synthetic', 'kind': 'onset', 'roi_xyxy': [10, 10, 100, 100],
                           'onset_interval_us': [40000, 60000], 'annotator': 'SYNTHETIC_TEST',
                           'reviewed': True, 'source': 'manual_blind_event_clip'}

    def run_metric(self, states, annotation=None):
        states = states+[False]*(15-len(states))
        rows = [{'end_us': (i+1)*20000, 'warmup': False,
                 'motion': {'valid': s is not None,
                            'regions': [{'xyxy': [20, 20, 40, 40]}] if s is True else []}}
                for i, s in enumerate(states)]
        return evaluate_annotations(self.manifest,
            {'schema': SCHEMA, 'annotations': [annotation or self.annotation]}, {'synthetic': rows})

    def test_uncertain_onset_delay_is_an_interval(self):
        result = self.run_metric([False, False, False, True])['results'][0]
        self.assertEqual(result['status'], 'RESPONSE_OBSERVED')
        self.assertEqual(result['delay_interval_ms'], [20, 40])

    def test_abstention_is_not_inactivity_or_a_missed_onset(self):
        result = self.run_metric([False, False, None, True])['results'][0]
        self.assertEqual(result['status'], 'INSUFFICIENT_COVERAGE')
        self.assertIsNone(result['delay_interval_ms'])
        result = self.run_metric([False, None, True])['results'][0]
        self.assertEqual(result['status'], 'UNKNOWN_PRE_ONSET_STATE')

    def test_preexisting_alert_is_not_a_correct_onset(self):
        result = self.run_metric([False, True, True])['results'][0]
        self.assertEqual(result['status'], 'ALREADY_ACTIVE_BEFORE_ONSET_INTERVAL')

    def test_negative_episodes_and_censoring_are_separate(self):
        annotation = dict(self.annotation, kind='negative', onset_interval_us=None)
        result = self.run_metric([True, True, False, True, True, None, True, False], annotation)['results'][0]
        self.assertEqual(result['confirmed_false_alert_starts'], 1)
        self.assertEqual(result['left_censored_active_segments'], 2)
        self.assertAlmostEqual(result['valid_roi_seconds'], .28)
        self.assertAlmostEqual(result['observable_transition_seconds'], .24)
        self.assertAlmostEqual(result['false_alert_frame_fraction'], 5/14)

    def test_unreviewed_and_uncertain_do_not_become_negatives(self):
        for annotation in (dict(self.annotation, reviewed=False), dict(self.annotation, kind='uncertain')):
            report = self.run_metric([True]*15, annotation)
            self.assertEqual(report['results'], [])
            self.assertEqual(len(report['excluded_annotations']), 1)

    def test_roi_matching_and_no_valid_exposure(self):
        annotation = dict(self.annotation, kind='negative', roi_xyxy=[200, 200, 300, 300])
        result = self.run_metric([True]*15, annotation)['results'][0]
        self.assertEqual(result['false_alert_frame_fraction'], 0)
        result = self.run_metric([None]*15, annotation)['results'][0]
        self.assertIsNone(result['false_alert_frame_fraction'])
        self.assertIsNone(result['false_alert_starts_per_observable_second'])

    def test_rejects_invalid_annotations_and_timestamp_mismatch(self):
        for annotation in (dict(self.annotation, roi_xyxy=[0, 0, 641, 480]),
                           dict(self.annotation, onset_interval_us=[40001, 60000]),
                           dict(self.annotation, reviewed='yes'), dict(self.annotation, annotator='')):
            with self.assertRaises(ValueError): self.run_metric([], annotation)
        self.manifest = copy.deepcopy(self.manifest)
        self.manifest['clips'][0]['frames'][0]['end_us'] += 1
        with self.assertRaises(ValueError): self.run_metric([])

    def test_no_response_and_end_of_clip_truncation(self):
        result = self.run_metric([])['results'][0]
        self.assertEqual(result['status'], 'NO_RESPONSE_WITHIN_HORIZON')
        annotation = dict(self.annotation, onset_interval_us=[260000, 280000])
        result = self.run_metric([], annotation)['results'][0]
        self.assertEqual(result['status'], 'TRUNCATED_WITHOUT_RESPONSE')


if __name__ == '__main__': unittest.main()
