"""Synthetic integration controls for the archived-stream comparison adapter."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_motion_annotations import compare, VARIANTS


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        clip = {'id': 'toy', 'split': 'train', 'start_us': 0, 'end_us': 300000,
                'step_us': 20000, 'frames': [{'end_us': t} for t in range(20000,300001,20000)]}
        self.manifest = {'schema': 'pfe-motion-annotation-v1', 'target': 'synthetic',
                         'width': 64, 'height': 48, 'clips': [clip, dict(clip,id='excluded',split='validation')]}
        self.annotation = {'clip_id': 'toy', 'kind': 'onset', 'roi_xyxy': [0,0,30,30],
            'onset_interval_us': [40000,60000], 'reviewed': True, 'annotator': 'SYNTHETIC_TEST',
            'source': 'manual_blind_event_clip'}
        self.bundle = {'schema': self.manifest['schema'], 'target': 'synthetic',
                       'annotations': [dict(self.annotation,clip_id='excluded'), self.annotation]}
        self.steps = {v: {'toy': 20000 if v==VARIANTS[-1] else 10000} for v in VARIANTS}
        self.streams = {v: {'toy': [{'end_us': t, 'warmup': False, 'motion': {'valid': True,
            'regions': [{'xyxy': [10,10,20,20]}] if t==80000 else []}}
            for t in range(self.steps[v]['toy'],300001,self.steps[v]['toy'])]} for v in VARIANTS}

    def test_native_cadences_and_original_annotation_indices(self):
        summary, reports, subset = compare(self.manifest,self.bundle,self.streams,self.steps)
        self.assertEqual(summary['eligible_reviewed_rois'],1)
        self.assertEqual(summary['excluded_outside_comparison'][0]['annotation_index'],0)
        self.assertEqual(len(subset['clips']),1)
        for v, report in reports.items():
            self.assertEqual(report['results'][0]['annotation_index'],1)
            self.assertEqual(report['results'][0]['delay_interval_ms'],[20,40])
            self.assertEqual(report['measured_prediction_rows'],300000//self.steps[v]['toy'])

    def test_empty_input_has_no_quality_score(self):
        bundle = dict(self.bundle,annotations=[])
        summary, reports, _ = compare(self.manifest,bundle,self.streams,self.steps)
        self.assertEqual(summary['status'],'PENDING_ANNOTATIONS')
        self.assertIsNone(summary['aggregate_quality_score'])
        self.assertTrue(all(not r['results'] for r in reports.values()))

    def test_mismatched_streams_unknown_clip_and_wrong_target_rejected(self):
        streams = deepcopy(self.streams); streams['relative']={}
        with self.assertRaises(ValueError): compare(self.manifest,self.bundle,streams,self.steps)
        bundle = deepcopy(self.bundle); bundle['annotations'][0]['clip_id']='unknown'
        with self.assertRaises(ValueError): compare(self.manifest,bundle,self.streams,self.steps)
        with self.assertRaises(ValueError): compare(self.manifest,dict(self.bundle,target='wrong'),self.streams,self.steps)


if __name__ == '__main__': unittest.main()
