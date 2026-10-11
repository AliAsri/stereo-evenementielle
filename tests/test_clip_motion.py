import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.clip_motion import track_seeds,infer_clip_motion


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

    def test_incomplete_history_rejected_before_read(self):
        readers=[SimpleNamespace(first_us=100,last_us=500000)]*2
        for end in (150099,500001):
            with self.assertRaises(ValueError):
                infer_clip_motion(readers,[None,None],{}, {},None,end_us=end)

    def test_invalid_seed_or_image_rejected(self):
        a=np.zeros((100,100),np.uint8)
        with self.assertRaises(ValueError): track_seeds(a,a,[[np.nan,2]])
        with self.assertRaises(ValueError): track_seeds(a,a.astype(float),[[20,20]])


if __name__=='__main__': unittest.main()
