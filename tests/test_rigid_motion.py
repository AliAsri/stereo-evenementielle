"""Geometric contracts and explicit counterexamples for M11."""
from pathlib import Path
import sys
import unittest

import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.rigid_motion import estimate_rigid_motion, RigidMotionConfig
from pfe_events.rigid_controls import make_scene
from pfe_events.global_motion import fit_apparent_motion


def run(scene, **kwargs):
    parameters = dict(previous_us=0, current_us=20000, depth_us=0, depth_source='synthetic_reference')
    parameters.update(kwargs)
    return estimate_rigid_motion(scene['previous'], scene['current'], scene['depth_m'],
                                 scene['intrinsic'], **parameters)


class RigidMotionTests(unittest.TestCase):
    def test_unsupported_seed_is_not_silently_accepted(self):
        with self.assertRaisesRegex(ValueError, 'does not expose'):
            run(make_scene('combined'), config=RigidMotionConfig(seed=43))

    def test_fit_preserves_global_opencv_random_stream(self):
        scene = make_scene('combined')
        expected = np.empty((8, 2), np.float64)
        actual = np.empty_like(expected)
        cv2.setRNGSeed(123)
        cv2.randn(expected, 0, 1)
        cv2.setRNGSeed(123)
        first = run(scene)
        cv2.randn(actual, 0, 1)
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual(first, run(scene))

    def test_static_scene_and_camera_motion_have_no_residual_candidates(self):
        for kind in ('static', 'camera_translation', 'camera_rotation'):
            with self.subTest(kind=kind):
                s=make_scene(kind); out=run(s)
                self.assertTrue(out['valid'])
                self.assertEqual(set(out['point_status']), {'MODEL_CONSISTENT'})
                np.testing.assert_allclose(out['transform_previous_to_current'], s['transform'], atol=1e-5)

    def test_parallax_rejected_where_image_similarity_leaves_residuals(self):
        s=make_scene('camera_translation')
        raw=fit_apparent_motion(s['previous']/2, s['current']/2)
        self.assertTrue(raw['valid'])
        self.assertTrue(any(v>3 for v in raw['residual_native_px']))
        self.assertNotIn('RESIDUAL_CANDIDATE',run(s)['point_status'])

    def test_translation_and_rotation_detected_without_direction_gate(self):
        for kind in ('object_translation','combined','object_rotation'):
            s=make_scene(kind); out=run(s)
            self.assertTrue(out['valid'])
            np.testing.assert_array_equal(np.array(out['point_status'])=='RESIDUAL_CANDIDATE',s['moving'])

    def test_small_localization_noise_preserves_control_result(self):
        s=make_scene('combined',seed=7,noise_px=.2);out=run(s)
        self.assertTrue(out['valid'])
        np.testing.assert_array_equal(np.array(out['point_status'])=='RESIDUAL_CANDIDATE',s['moving'])

    def test_missing_depth_abstains_and_partial_depth_stays_unknown(self):
        out=run(make_scene('missing_depth'))
        self.assertFalse(out['valid']);self.assertEqual(set(out['point_status']),{'UNKNOWN'})
        self.assertIsNone(out['transform_previous_to_current'])
        s=make_scene('combined');s['depth_m'][[0,1,2,3]]=[np.nan,0,-1,np.inf]
        out=run(s);self.assertTrue(out['valid'])
        self.assertEqual(out['point_status'][:4],['UNKNOWN']*4)
        self.assertEqual(out['residual_px'][:4],[None]*4)

    def test_biased_depth_can_create_false_motion_candidates(self):
        s=make_scene('biased_near_depth');out=run(s)
        self.assertTrue(out['valid']);self.assertFalse(s['moving'].any())
        self.assertIn('RESIDUAL_CANDIDATE',out['point_status'])

    def test_dominant_moving_layer_is_not_verified_camera_pose(self):
        s=make_scene('dominant_moving_layer');out=run(s)
        self.assertTrue(out['valid'])
        self.assertTrue(all(v=='MODEL_CONSISTENT' for v in np.array(out['point_status'])[s['moving']]))
        self.assertFalse(np.allclose(out['transform_previous_to_current'],s['transform'],atol=.01))

    def test_contract_rejects_stale_future_depth_and_bad_time(self):
        s=make_scene('static')
        for args in ({'depth_us':-1},{'depth_us':20000},{'current_us':0},
                     {'current_us':100001},{'previous_us':False},{'depth_source':'unknown'}):
            with self.subTest(args=args),self.assertRaises(ValueError):run(s,**args)

    def test_bad_inputs_and_config(self):
        s=make_scene('static')
        for change in ('nonfinite_pixel','outside_pixel','bad_intrinsic','wrong_depth_shape'):
            bad={k:v.copy() if isinstance(v,np.ndarray) else v for k,v in s.items()}
            if change=='nonfinite_pixel':bad['current'][0,0]=np.nan
            if change=='outside_pixel':bad['previous'][0,0]=640
            if change=='bad_intrinsic':bad['intrinsic'][0,0]=0
            if change=='wrong_depth_shape':bad['depth_m']=bad['depth_m'][:,None]
            with self.subTest(change=change),self.assertRaises(ValueError):run(bad)
        with self.assertRaises(ValueError):run(s,config=RigidMotionConfig(min_points=5))

    def test_collinear_geometry_abstains(self):
        s=make_scene('static');s['previous'][:,1]=240;s['current']=s['previous'].copy();s['depth_m'][:]=10
        out=run(s);self.assertFalse(out['valid']);self.assertEqual(out['status'],'DEGENERATE_3D_SUPPORT')

    def test_small_spatial_support_abstains(self):
        s=make_scene('static')
        s['previous']=(s['previous']-[320,240])*.05+[320,240];s['current']=s['previous'].copy()
        out=run(s);self.assertFalse(out['valid']);self.assertEqual(out['status'],'INSUFFICIENT_RIGID_SUPPORT')

    def test_provenance_and_inputs_preserved(self):
        s=make_scene('combined');before={k:v.copy() for k,v in s.items() if isinstance(v,np.ndarray)}
        self.assertTrue(run(s)['oracle']);self.assertFalse(run(s,depth_source='predicted')['oracle'])
        for k,v in before.items():np.testing.assert_array_equal(s[k],v)


if __name__=='__main__':unittest.main()
