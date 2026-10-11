"""Annotation inventory must not turn missing data into evaluation evidence."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from check_motion_annotations import readiness


class AnnotationReadinessTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {'schema': 'pfe-motion-annotation-v1', 'target': 'synthetic test',
            'width': 32, 'height': 32, 'clips': [{'id': 'test', 'split': 'synthetic',
            'start_us': 0, 'end_us': 40000, 'step_us': 20000,
            'frames': [{'end_us': 20000}, {'end_us': 40000}]}]}
        self.annotations = {'schema': self.manifest['schema'], 'target': self.manifest['target'], 'annotations': []}
        self.predictions = {'test': [{'end_us': t, 'warmup': False, 'motion': {'valid': True, 'regions': []}}
                                     for t in (20000, 40000)]}

    def test_empty_export_is_pending_not_a_negative_scene(self):
        report = readiness(self.manifest, self.annotations, self.predictions)
        self.assertEqual(report['status'], 'PENDING_REVIEWED_ANNOTATIONS')
        self.assertEqual(report['clips'][0]['reviewed_negative_rois'], 0)

    def test_duplicate_review_rejected(self):
        annotation = {'clip_id': 'test', 'kind': 'negative', 'roi_xyxy': [0, 0, 16, 16],
                      'onset_interval_us': None, 'reviewed': True, 'annotator': 'SYNTHETIC_TEST',
                      'source': 'manual_blind_event_clip'}
        self.annotations['annotations'] = [annotation]
        self.assertEqual(readiness(self.manifest, self.annotations, self.predictions)['reviewed_eligible_rois'], 1)
        self.annotations['annotations'].append(annotation)
        with self.assertRaises(ValueError): readiness(self.manifest, self.annotations, self.predictions)

    def test_wrong_target_rejected(self):
        self.annotations['target'] = 'different target'
        with self.assertRaises(ValueError): readiness(self.manifest, self.annotations, self.predictions)


if __name__ == '__main__': unittest.main()
