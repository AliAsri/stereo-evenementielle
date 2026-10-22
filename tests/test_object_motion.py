"""Conditional mobility decisions, not a validation of physical object motion."""
import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.object_surface import associate_surface, object_motion_decision, ObjectMotionConfig


class ObjectMotionTests(unittest.TestCase):
    def setUp(self):
        y,x=np.indices((40,50))
        self.mapping=np.stack([x,y],axis=-1).astype(float)
        self.d=np.full((40,50),10.)
        self.valid=np.ones(self.d.shape,bool)
        self.q=np.array([[1,0,0,-25],[0,1,0,-20],[0,0,0,100],[0,0,2,0]],float)
        self.box=[5,5,45,35]
        self.points=np.array([[18,16],[20,16],[22,16],[24,16],[26,16]],float)
        self.model=dict(valid=True,previous_us=0,current_us=100000,
                        transform_previous_to_current=np.eye(4).tolist(),
                        point_status=['MODEL_CONSISTENT']*5)

    def decision(self, **kwargs):
        surface=associate_surface(self.box,self.mapping,self.d,self.valid,self.q,
                                  detection_us=100000,depth_us=100000)
        args=dict(box=self.box,mapping=self.mapping,disparity=self.d,valid=self.valid,q=self.q,
                  points=self.points,model=self.model,surface=surface,
                  detection_us=100000,depth_us=100000)
        args.update(kwargs)
        return object_motion_decision(**args)

    def test_three_states_and_explicit_unconfirmed_physical_interpretation(self):
        self.assertEqual(self.decision()['mobility'],'IMMOBILE')
        self.model['point_status']=['RESIDUAL_CANDIDATE']*5
        result=self.decision()
        self.assertEqual(result['mobility'],'MOBILE')
        self.assertEqual(result['physical_mobility'],'UNCONFIRMED')
        self.model['point_status']=['RESIDUAL_CANDIDATE']*3+['MODEL_CONSISTENT']*2
        self.assertEqual(self.decision()['mobility'],'INDETERMINATE')

    def test_background_residuals_cannot_outvote_surface_tracks(self):
        extra=np.array([[18,20],[20,20],[22,20],[24,20],[26,20]],float)
        self.points=np.vstack([self.points[:3],extra])
        self.d[extra[:,1].astype(int),extra[:,0].astype(int)]=2.5
        self.model['point_status']=['MODEL_CONSISTENT']*3+['RESIDUAL_CANDIDATE']*5
        result=self.decision()
        self.assertEqual(result['roi_support']['RESIDUAL_CANDIDATE'],5)
        self.assertEqual(result['surface_track_indices'],[0,1,2])
        self.assertEqual(result['RESIDUAL_CANDIDATE'],0)
        self.assertEqual(result['mobility'],'IMMOBILE')

    def test_absent_or_ambiguous_surface_abstains(self):
        self.valid[:]=False
        self.assertEqual(self.decision()['reason'],'SURFACE_UNAVAILABLE')
        self.valid[:]=True
        self.d[:]=2.5;self.d[16:24,21:29]=10.
        self.assertEqual(self.decision()['mobility'],'INDETERMINATE')

    def test_invalid_rigid_final_never_falls_back_to_primary(self):
        self.model.update(valid=False,transform_previous_to_current=None,
                          status='AMBIGUOUS_RIGID_MODELS',primary={'valid':True})
        result=self.decision()
        self.assertEqual(result['mobility'],'INDETERMINATE')
        self.assertEqual(result['reason'],'RIGID_MODEL_UNAVAILABLE')

    def test_missing_current_depth_abstains_even_with_valid_past_motion(self):
        for x,y in self.points.astype(int):self.valid[y,x]=False
        self.model['point_status']=['RESIDUAL_CANDIDATE']*5
        self.assertEqual(self.decision()['tracked_points'],0)
        self.assertEqual(self.decision()['mobility'],'INDETERMINATE')

    def test_duplicate_pixel_samples_do_not_multiply_evidence(self):
        self.points[:]=[20,16]
        self.assertEqual(self.decision()['tracked_points'],1)
        self.assertEqual(self.decision()['mobility'],'INDETERMINATE')

    def test_unknowns_are_in_coverage_denominator(self):
        self.model['point_status']=['MODEL_CONSISTENT']*3+['UNKNOWN']*2
        r=self.decision()
        self.assertEqual(r['evaluated_fraction'],.6)
        self.assertEqual(r['mobility'],'INDETERMINATE')

    def test_fixed_agreement_boundary_is_inclusive(self):
        self.model['point_status']=['RESIDUAL_CANDIDATE']*4+['MODEL_CONSISTENT']
        self.assertEqual(self.decision()['mobility'],'MOBILE')

    def test_points_outside_inner_roi_cannot_vote(self):
        self.points[:]=[[1,1],[2,2],[3,3],[4,4],[5,5]]
        self.assertEqual(self.decision()['tracked_points'],0)

    def test_dates_must_match_even_when_depth_is_absent(self):
        self.valid[:]=False
        for stamp in (0,100001):
            with self.subTest(stamp=stamp),self.assertRaises(ValueError):
                self.decision(depth_us=stamp)
        self.model['current_us']=99999
        with self.assertRaises(ValueError):self.decision()

    def test_supplied_disparity_outside_search_cannot_vote(self):
        for x,y in self.points.astype(int):self.d[y,x]=114.
        self.assertEqual(self.decision()['tracked_points'],0)

    def test_no_tracks_is_not_an_immobility_decision(self):
        self.points=np.empty((0,2));self.model['point_status']=[]
        self.assertEqual(self.decision()['mobility'],'INDETERMINATE')

    def test_unsafe_decision_configuration_rejected(self):
        for kw in (dict(min_tracks=0),dict(min_tracks=True),dict(min_agreement=.5),
                   dict(min_evaluated_fraction=float('nan')),dict(min_agreement=True),
                   dict(min_evaluated_fraction='0.8')):
            with self.assertRaises(ValueError):ObjectMotionConfig(**kw)


if __name__=='__main__':unittest.main()
