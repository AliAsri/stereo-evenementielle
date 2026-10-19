from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.rectified_tracking import checked_tracks, sample_masked_depth, sample_disparity_depth, TrackingConfig, select_features
from pfe_events.geometry import reproject_q


class SpatialSelectionTests(unittest.TestCase):
    @staticmethod
    def scene():
        image = np.zeros((480, 640), np.uint8)
        for y in range(90, 460, 12):
            for x in range(10, 630, 12):
                image[y:y+5, x:x+5] = 255
        image[25:32, 340:347] = 60
        return image

    def test_default_is_exact_original_opencv_selection(self):
        image = self.scene()
        expected = cv2.goodFeaturesToTrack(image, maxCorners=400, qualityLevel=.01, minDistance=6, blockSize=5)
        np.testing.assert_array_equal(select_features(image), expected)

    def test_spatial_budget_recovers_weaker_region_without_extra_tracks(self):
        image = self.scene(); before = image.copy()
        global_points = select_features(image).reshape(-1, 2)
        spatial = select_features(image, TrackingConfig(selection='spatial_8x6')).reshape(-1, 2)
        self.assertEqual(len(spatial), 400)
        self.assertFalse(np.any(global_points[:, 1] < 70))
        self.assertTrue(np.any(spatial[:, 1] < 70))
        np.testing.assert_array_equal(image, before)

    def test_spatial_selection_keeps_global_spacing_quality_and_order(self):
        image = self.scene()
        all_points = cv2.goodFeaturesToTrack(image, maxCorners=0, qualityLevel=.01, minDistance=6, blockSize=5).reshape(-1, 2)
        selected = select_features(image, TrackingConfig(selection='spatial_8x6')).reshape(-1, 2)
        rank = {tuple(p): i for i, p in enumerate(all_points)}
        indices = [rank[tuple(p)] for p in selected]
        self.assertEqual(indices, sorted(indices))
        distance = np.linalg.norm(selected[:, None]-selected[None, :], axis=2)
        np.fill_diagonal(distance, np.inf)
        self.assertGreaterEqual(distance.min(), 6)

    def test_empty_cells_and_small_budget_do_not_loop_or_exceed_budget(self):
        image = np.zeros((80, 100), np.uint8)
        self.assertIsNone(select_features(image, TrackingConfig(selection='spatial_8x6')))
        image[20:25, 20:25] = 255
        points = select_features(image, TrackingConfig(max_features=1, selection='spatial_8x6'))
        self.assertEqual(len(points), 1)
        with self.assertRaises(ValueError):
            select_features(image, TrackingConfig(selection='unknown'))

    def test_spatial_checked_tracks_preserve_known_translation(self):
        rng = np.random.default_rng(63)
        image = cv2.GaussianBlur(rng.integers(0, 256, (128, 160), dtype=np.uint8), (5, 5), 0)
        moved = cv2.warpAffine(image, np.array([[1., 0, 2], [0, 1, -1]]), (160, 128))
        p, q, stats = checked_tracks(image, moved, TrackingConfig(max_features=40, selection='spatial_8x6'))
        self.assertLessEqual(stats['features'], 40)
        self.assertGreater(len(p), 10)
        np.testing.assert_allclose(np.median(q-p, axis=0), [2, -1], atol=.1)


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

    def test_sparse_projection_matches_full_map_with_rounding_and_unknowns(self):
        rng = np.random.default_rng(791)
        disparity = rng.uniform(.2, 30, (21, 23)).astype(np.float32)
        disparity[0, :4] = [0, -1, np.nan, np.inf]
        mask = rng.random(disparity.shape) > .2
        mask[0, :4] = True
        points = np.vstack(([[0, 0], [.1, .1], [1, 0], [2, 0], [3, 0],
                             [-.01, 1], [22.5, 1], [1, 20.5],
                             [2.49, 1.49], [2.5, 1.5]],
                            rng.uniform([-1, -1], [24, 22], (400, 2))))
        canonical = np.array([[1, 0, 0, -11], [0, 1, 0, -10],
                              [0, 0, 0, 100], [0, 0, 10, 0]], float)
        general = canonical.copy()
        general[2, :2] = [.3, -.2]
        general[3, [0, 1, 3]] = [.01, .03, 2]
        singular = canonical.copy(); singular[3] = 0
        behind = canonical.copy(); behind[2, 3] = -100
        yy, xx = np.indices(disparity.shape)
        for name, q in [('canonical', canonical), ('general', general),
                        ('singular', singular), ('behind', behind)]:
            with self.subTest(q=name), np.errstate(invalid='ignore'):
                full = reproject_q(xx, yy, disparity, q)[..., 2].astype(np.float32)
                expected, stats = sample_masked_depth(points, full, mask)
                actual, actual_stats = sample_disparity_depth(points, disparity, mask, q)
                np.testing.assert_array_equal(actual, expected)
                self.assertEqual(actual_stats, stats)
                self.assertEqual(actual.dtype, np.float64)
        with np.errstate(invalid='ignore'):
            self.assertGreater(sample_disparity_depth(points, disparity, mask, canonical)[1]['usable_depths'], 0)

    def test_sparse_depth_empty_and_invalid_inputs(self):
        disparity = np.ones((3, 4), np.float32)
        mask = np.ones_like(disparity, dtype=bool)
        q = np.array([[1, 0, 0, -2], [0, 1, 0, -1],
                      [0, 0, 0, 100], [0, 0, 10, 0]], float)
        result, stats = sample_disparity_depth(np.empty((0, 2)), disparity, mask, q)
        self.assertEqual(result.shape, (0,))
        self.assertEqual(stats['usable_depths'], 0)
        for points, values, valid, matrix in (
                ([[np.nan, 0]], disparity, mask, q),
                ([[0, 0]], disparity, mask.astype(int), q),
                ([[0, 0]], disparity[:2], mask, q),
                (np.empty((0, 2)), disparity, mask, np.eye(3))):
            with self.assertRaises(ValueError):
                sample_disparity_depth(points, values, valid, matrix)


if __name__=='__main__':unittest.main()
