from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.rectified_tracking import checked_tracks, sample_masked_depth, TrackingConfig


class RectifiedTrackingTests(unittest.TestCase):
    def test_known_translation_and_input_preservation(self):
        rng=np.random.default_rng(42)
        a=cv2.GaussianBlur(rng.integers(0,256,(128,160),dtype=np.uint8),(5,5),0)
        b=cv2.warpAffine(a,np.array([[1.,0,3],[0,1,-2]]),(160,128))
        before=a.copy();p,q,stats=checked_tracks(a,b)
        self.assertGreater(len(p),40)
        np.testing.assert_allclose(np.median(q-p,axis=0),[3,-2],atol=.1)
        self.assertEqual(stats['checked_tracks'],len(p));np.testing.assert_array_equal(a,before)

    def test_blank_images_are_no_evidence(self):
        p,q,stats=checked_tracks(np.zeros((60,80),np.uint8),np.zeros((60,80),np.uint8))
        self.assertEqual(p.shape,(0,2));self.assertEqual(q.shape,(0,2));self.assertEqual(stats['status'],'NO_FEATURES')

    def test_image_and_configuration_contracts(self):
        a=np.zeros((60,80),np.uint8)
        for b in (a.astype(float),a[:50],a[:,:,None]):
            with self.assertRaises(ValueError):checked_tracks(a,b)
        with self.assertRaises(ValueError):checked_tracks(a,a,TrackingConfig(fb_max_px=0))

    def test_sampling_xy_mask_and_nearest_pixel(self):
        depth=np.arange(12,dtype=float).reshape(3,4)+1;valid=np.ones((3,4),bool)
        valid[2,1]=False
        z,stats=sample_masked_depth([[2.49,1.49],[2.5,.5],[1,2]],depth,valid)
        np.testing.assert_allclose(z[:2],[7,8]);self.assertTrue(np.isnan(z[2]))
        self.assertEqual(stats['usable_depths'],2)

    def test_no_border_clamp_no_hole_fill_or_duplicate_support(self):
        depth=np.full((3,4),10.);valid=np.ones((3,4),bool);depth[1,1]=np.nan
        z,stats=sample_masked_depth([[-.1,1],[3.6,1],[1,1],[0,0],[.1,.1]],depth,valid)
        self.assertTrue(np.isnan(z[[0,1,2,4]]).all());self.assertEqual(z[3],10.)
        self.assertEqual(stats['outside_rounded_map'],2);self.assertEqual(stats['duplicate_pixels'],1)

    def test_invalid_depth_and_input_errors(self):
        depth=np.array([[0.,-1.,np.inf]]);mask=np.ones_like(depth,dtype=bool)
        z,_=sample_masked_depth([[0,0],[1,0],[2,0]],depth,mask)
        self.assertTrue(np.isnan(z).all())
        with self.assertRaises(ValueError):sample_masked_depth([[np.nan,0]],depth,mask)
        with self.assertRaises(ValueError):sample_masked_depth([[0,0]],depth,mask.astype(int))


if __name__=='__main__':unittest.main()
