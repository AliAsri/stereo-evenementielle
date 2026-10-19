import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.clip_motion import track_seeds,infer_clip_motion,ClipMotionCache


class ClipMotionTests(unittest.TestCase):
    def test_empty_seeds_abstain(self):
        a=np.zeros((100,100),np.uint8)
        q,keep,fb=track_seeds(a,a,np.empty((0,2)))
        self.assertEqual(q.shape,(0,2)); self.assertEqual(len(keep),0)

    def test_known_image_translation(self):
        rng=np.random.default_rng(42)
        a=cv2.GaussianBlur(rng.integers(0,256,(240,320),dtype=np.uint8),(5,5),0)
        b=cv2.warpAffine(a,np.array([[1,0,3],[0,1,-2]],np.float32),(320,240))
        p=np.array([[x,y] for y in (80,120,160) for x in (80,120,160,200,240)],np.float32)
        q,keep,fb=track_seeds(a,b,p)
        self.assertTrue(keep.all())
        np.testing.assert_allclose(q-p,np.tile([3,-2],(len(p),1)),atol=.05)
        explicit = track_seeds(a,b,p,max_level=2)
        for old, new in zip((q,keep,fb),explicit):
            np.testing.assert_array_equal(old,new)
        coarse,accepted,_=track_seeds(a,b,p,max_level=3)
        # The coarser diagnostic can lose support; surviving matches must still
        # agree with this known displacement. It is not promoted to the default.
        self.assertTrue(accepted.any())
        np.testing.assert_allclose((coarse-p)[accepted],np.tile([3,-2],(accepted.sum(),1)),atol=.05)

    def test_unsupported_pyramid_levels_rejected_even_for_empty_support(self):
        image=np.zeros((100,100),np.uint8)
        for level in (-1,0,4,3.0,True):
            with self.assertRaises(ValueError):
                track_seeds(image,image,np.empty((0,2)),max_level=level)

    def test_incomplete_history_rejected_before_read(self):
        readers=[SimpleNamespace(first_us=100,last_us=500000)]*2
        for end in (150099,500001):
            with self.assertRaises(ValueError):
                infer_clip_motion(readers,[None,None],{}, {},None,end_us=end)

    def test_invalid_seed_or_image_rejected(self):
        a=np.zeros((100,100),np.uint8)
        with self.assertRaises(ValueError): track_seeds(a,a,[[np.nan,2]])
        with self.assertRaises(ValueError): track_seeds(a,a.astype(float),[[20,20]])


class ClipMotionCacheTests(unittest.TestCase):
    def setUp(self):
        self.reads=[]
        rng=np.random.default_rng(73)
        self.base=cv2.GaussianBlur(rng.integers(0,256,(240,320),dtype=np.uint8),(5,5),0)
        def window(begin,end):
            self.reads.append((begin,end))
            return self.image(end)
        self.readers=[SimpleNamespace(first_us=0,last_us=500000,window=window) for _ in range(2)]
        self.maps=[object(),object()]
        self.calibration={'q':[[1,0,0,-160],[0,1,0,-120],[0,0,0,100],[0,0,10,0]],
                          'fx_px':100,'fy_px':100,'cx_px':160,'cy_px':120}
        self.normalizer={}
        self.cache=ClipMotionCache(self.readers,self.maps,self.calibration,self.normalizer)
        self.disparity=np.full(self.base.shape,10,np.float32)
        self.valid=np.ones(self.base.shape,bool)

    def image(self,end):
        shift=(end-200000)/20000
        return cv2.warpAffine(self.base,np.array([[1,0,shift],[0,1,0]],np.float32),(320,240))

    def remember(self,end):
        self.cache.remember(end,[self.image(end)]*2,self.disparity,self.valid)

    def infer(self,cache):
        with patch('pfe_events.clip_motion.rectified_counts',side_effect=lambda e,m:(e,0)), \
             patch('pfe_events.clip_motion.normalized_event_image',side_effect=lambda c,n,*,total_only=False:c if total_only else np.repeat(c[...,None],3,axis=2)), \
             patch('pfe_events.clip_motion.predict_stereo',return_value=(self.disparity,self.valid,None,{})) as stereo:
            result=infer_clip_motion(self.readers,self.maps,self.calibration,self.normalizer,
                                     self.image(300000),end_us=300000,history_cache=cache)
            return result,stereo.call_count

    def test_exact_reuse_preserves_tracks_and_model_without_recomputation(self):
        (expected,model,details),calls=self.infer(None)
        self.assertEqual(calls,1);self.assertEqual(len(self.reads),3)
        self.assertGreater(len(expected['current']),20)
        self.assertTrue(model['valid'])
        self.remember(200000);self.remember(220000);self.reads.clear()
        (actual,cached_model,cached_details),calls=self.infer(self.cache)
        self.assertEqual(calls,0);self.assertEqual(self.reads,[])
        for key in expected: np.testing.assert_array_equal(actual[key],expected[key])
        self.assertEqual(cached_model,model)
        self.assertEqual(cached_details['seed_tracking'],details['seed_tracking'])

    def test_nearby_date_never_substitutes_for_missing_depth(self):
        self.remember(199999);self.remember(220000)
        (_,_,details),calls=self.infer(self.cache)
        self.assertEqual(calls,1)
        self.assertEqual(self.reads,[(150000,200000)]*2)
        self.assertEqual(details['history_reuse'],{'previous_stereo':False,'short_image':True})

    def test_motion_does_not_need_current_stereo_at_startup_or_with_full_cache(self):
        # Compare publication before/after remembering current stereo. At steady
        # state, insertion also evicts t-120 ms; t-100 and t-80 must survive.
        for warm in (False, True):
            with self.subTest(warm=warm):
                self.cache=ClipMotionCache(self.readers,self.maps,self.calibration,self.normalizer)
                if warm:
                    for date in range(180000,300000,20000): self.remember(date)
                self.reads.clear()
                (early,early_model,early_details),early_calls=self.infer(self.cache)
                early_reads=self.reads.copy()
                self.remember(300000)
                self.reads.clear()
                (late,late_model,late_details),late_calls=self.infer(self.cache)
                for key in early: np.testing.assert_array_equal(early[key],late[key])
                self.assertEqual(early_model,late_model)
                for key in ('seed_tracking','history_reuse','history_windows_us'):
                    self.assertEqual(early_details[key],late_details[key])
                self.assertEqual(early_calls,late_calls)
                self.assertEqual(early_reads,self.reads)
                self.assertEqual(early_calls,0 if warm else 1)
                self.assertLessEqual(len(self.cache.frames),6)

    def test_future_and_foreign_context_rejected(self):
        self.remember(320000)
        with self.assertRaises(ValueError): self.infer(self.cache)
        self.assertEqual(self.reads,[])
        with self.assertRaises(ValueError):
            self.cache.check_context(self.readers,self.maps,dict(self.calibration),self.normalizer,320000)

    def test_owned_readonly_arrays_bounded_history_and_monotonic_dates(self):
        self.remember(200000)
        self.disparity[:]=20
        self.assertEqual(self.cache.get(200000)[2][0,0],10)
        with self.assertRaises(ValueError): self.cache.get(200000)[2][0,0]=30
        with self.assertRaises(ValueError): self.remember(200000)
        for date in range(201000,211000,1000): self.remember(date)
        self.assertEqual(len(self.cache.frames),6)
        self.assertIsNone(self.cache.get(200000))
        self.remember(400000)
        self.assertEqual(list(self.cache.frames),[400000])


if __name__=='__main__': unittest.main()
