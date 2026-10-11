"""Temporal uncertainty and coverage controls, using synthetic annotations only."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.multirate_evaluation import evaluate_multirate
from pfe_events.motion_evaluation import evaluate_annotations


class MultirateEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.manifest={'schema':'pfe-motion-annotation-v1','target':'synthetic','width':640,'height':480,
            'clips':[{'id':'toy','split':'synthetic','start_us':0,'end_us':300000,'step_us':20000,
                      'frames':[{'end_us':t} for t in range(20000,300001,20000)]}]}
        self.annotation={'clip_id':'toy','kind':'onset','roi_xyxy':[10,10,100,100],
            'onset_interval_us':[40000,60000],'reviewed':True,'annotator':'SYNTHETIC_TEST',
            'source':'manual_blind_event_clip'}

    def bundle(self,annotations=None):
        return {'schema':self.manifest['schema'],'target':'synthetic',
                'annotations':[self.annotation] if annotations is None else annotations}

    def rows(self,step=10000,active=(50000,),invalid=()):
        return [{'end_us':t,'warmup':False,'motion':{'valid':t not in invalid,
            'regions':[{'xyxy':[20,20,40,40]}] if t in active else []}} for t in range(step,300001,step)]

    def run_eval(self,step=10000,rows=None,annotations=None):
        return evaluate_multirate(self.manifest,self.bundle(annotations),
            {'toy':self.rows(step) if rows is None else rows},{'toy':step})

    def test_finer_predictions_do_not_shrink_onset_uncertainty(self):
        r=self.run_eval()['results'][0]
        self.assertEqual(r['delay_interval_ms'],[-10,10])
        self.assertEqual(r['onset_interval_us'],[40000,60000])
        self.assertEqual(r['first_response_us'],50000)
        self.assertEqual((r['annotation_step_us'],r['prediction_step_us']),(20000,10000))

    def test_equal_cadence_retains_v1_metrics(self):
        rows=self.rows(20000,active=(80000,))
        before=evaluate_annotations(self.manifest,self.bundle(),{'toy':rows})['results'][0]
        after=self.run_eval(20000,rows)['results'][0]
        for key,value in before.items(): self.assertEqual(after[key],value)

    def test_no_duration_inferred_from_an_onset(self):
        self.assertEqual(self.run_eval()['results'][0]['continuous_motion']['status'],'NOT_ANNOTATED')

    def test_continuous_interval_counts_abstention_separately(self):
        self.annotation.update(active_interval_us=[60000,120000],continuous_motion_reviewed=True)
        rows=self.rows(active=(50000,80000,100000),invalid=(90000,))
        r=self.run_eval(rows=rows)['results'][0]['continuous_motion']
        self.assertEqual((r['evaluated_windows'],r['valid_windows'],r['alert_windows']),(6,5,2))
        self.assertAlmostEqual(r['window_alert_fraction'],.4)
        self.assertAlmostEqual(r['valid_fraction'],5/6)

    def test_continuous_interval_requires_review_and_coarse_boundaries(self):
        for extra in ({'active_interval_us':[60000,120000]},
                      {'active_interval_us':[60000,110000],'continuous_motion_reviewed':True},
                      {'active_interval_us':[40000,120000],'continuous_motion_reviewed':True}):
            annotation=dict(self.annotation,**extra)
            with self.assertRaises(ValueError): self.run_eval(annotations=[annotation])

    def test_missing_or_duplicate_frame_is_rejected_even_without_annotations(self):
        for rows in (self.rows()[1:],self.rows()+[self.rows()[-1]]):
            with self.assertRaises(ValueError): self.run_eval(rows=rows,annotations=[])

    def test_finer_annotation_bound_is_rejected(self):
        self.annotation['onset_interval_us']=[50000,60000]
        with self.assertRaises(ValueError): self.run_eval()

    def test_unsupported_coarser_grid_rejected(self):
        with self.assertRaises(ValueError): self.run_eval(50000)

    def test_prior_alert_and_abstention_are_not_correct_onsets(self):
        result=self.run_eval(rows=self.rows(active=(40000,50000)))['results'][0]
        self.assertEqual(result['status'],'ALREADY_ACTIVE_BEFORE_ONSET_INTERVAL')
        result=self.run_eval(rows=self.rows(invalid=(40000,)))['results'][0]
        self.assertEqual(result['status'],'UNKNOWN_PRE_ONSET_STATE')

    def test_negative_exposure_uses_prediction_step(self):
        self.annotation.update(kind='negative',onset_interval_us=None)
        result=self.run_eval(rows=self.rows(active=(20000,30000),invalid=(40000,)))['results'][0]
        self.assertAlmostEqual(result['valid_roi_seconds'],.29)
        self.assertEqual(result['confirmed_false_alert_starts'],1)
        self.assertAlmostEqual(result['false_alert_seconds'],.02)

    def test_target_duplicate_and_empty_controls(self):
        with self.assertRaises(ValueError): self.run_eval(annotations=[self.annotation,self.annotation])
        manifest=deepcopy(self.manifest); manifest['target']='wrong'
        with self.assertRaises(ValueError): evaluate_multirate(manifest,self.bundle(),{'toy':self.rows()},{'toy':10000})
        empty=self.run_eval(annotations=[])
        self.assertEqual(empty['results'],[]); self.assertEqual(empty['streams_checked'],1)


if __name__=='__main__': unittest.main()
