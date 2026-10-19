import importlib.util
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('saved_mask_support',ROOT/'scripts/diagnostics/analyze_saved_mask_support.py')
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class SavedMaskSupportTests(unittest.TestCase):
    def test_bottom_rows_and_rounded_outside_pixels_are_unknown(self):
        mask=np.ones((440,640),bool)
        p=np.array([[20,439],[20,439.5],[20,440],[20,479],[639.6,30]])
        strata=diagnostic.mask_strata(p,mask)
        np.testing.assert_array_equal(strata['positive_mask_provisional'],[True,False,False,False,False])
        self.assertEqual(strata['outside_mask_unknown'].sum(),4)
        self.assertFalse(strata['zero_mask_unknown'].any())
        self.assertTrue(strata['positive_boundary_3x3'][0])

    def test_pixel_centres_zero_unknown_and_boundary_do_not_mutate_mask(self):
        mask=np.zeros((440,640),bool);mask[10:13,10:13]=True
        before=mask.copy()
        p=np.array([[9.49,11],[9.5,11],[11,11]])
        strata=diagnostic.mask_strata(p,mask)
        np.testing.assert_array_equal(strata['zero_mask_unknown'],[True,False,False])
        np.testing.assert_array_equal(strata['positive_mask_provisional'],[False,True,True])
        np.testing.assert_array_equal(strata['positive_boundary_3x3'],[False,True,False])
        np.testing.assert_array_equal(mask,before)

    def test_invalid_shapes_types_and_coordinates_rejected(self):
        mask=np.zeros((440,640),bool)
        for p in ([[np.nan,0]],[[-1,0]],[[640,0]],[[0,480]]):
            with self.assertRaises(ValueError): diagnostic.mask_strata(np.array(p),mask)
        with self.assertRaises(ValueError): diagnostic.mask_strata(np.empty((0,2)),np.zeros((480,640),bool))
        with self.assertRaises(ValueError): diagnostic.mask_strata(np.empty((0,2)),mask.astype(np.uint8))

    def test_common_point_comparison_preserves_depth_abstention(self):
        mask=np.ones((440,640),bool)
        p=np.array([[20.,20.],[30.,30.],[40.,40.]])
        q=p+np.array([3,4])
        model=dict(valid=True,point_status=['RESIDUAL_CANDIDATE','UNKNOWN','MODEL_CONSISTENT'],
                   residual_px=[4,None,1],evaluated_points=2)
        result,_,_=diagnostic.support(p,q,np.array([2,np.nan,3]),model,mask)
        row=result['positive_mask_provisional']
        self.assertEqual((row['tracks'],row['usable_depth'],row['evaluated'],row['abstentions']),(3,2,2,1))
        self.assertEqual(row['residual_candidates'],1)
        self.assertEqual(row['c0_displacement_common_points']['count'],2)
        self.assertEqual(row['c0_displacement_common_points']['median_px'],5)
        self.assertEqual(row['c1_residual_common_points']['median_px'],2.5)

    def test_rejected_model_and_empty_history_do_not_create_zero_scores(self):
        mask=np.zeros((440,640),bool)
        p=np.array([[20.,20.]])
        model=dict(valid=False,point_status=['UNKNOWN'],residual_px=[None],evaluated_points=0)
        result,_,_=diagnostic.support(p,p,np.array([2]),model,mask)
        row=result['zero_mask_unknown']
        self.assertEqual(row['usable_depth'],1);self.assertEqual(row['abstentions'],1)
        self.assertIsNone(row['c1_residual_common_points']['median_px'])
        empty,_,_=diagnostic.support(np.empty((0,2)),np.empty((0,2)),np.empty(0),
                                    dict(valid=False,point_status=[]),mask)
        self.assertEqual(empty['outside_mask_unknown']['tracks'],0)

    def test_inconsistent_finite_residual_or_classification_rejected(self):
        p=np.array([[20.,20.]])
        for model in (
            dict(valid=False,point_status=['UNKNOWN'],residual_px=[0],evaluated_points=0),
            dict(valid=True,point_status=['RESIDUAL_CANDIDATE'],residual_px=[None],evaluated_points=0),
            dict(valid=True,point_status=['MODEL_CONSISTENT'],residual_px=[1],evaluated_points=0)):
            with self.assertRaises(ValueError): diagnostic.support(p,p,np.array([2]),model,np.ones((440,640),bool))


if __name__=='__main__': unittest.main()
