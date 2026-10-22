import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.object_surface import associate_surface, mapped_roi, region_motion_support, SurfaceConfig
from pfe_events.stereo import StereoConfig


class SurfaceTests(unittest.TestCase):
    def test_nonfinite_and_noninteger_surface_configuration_rejected(self):
        for field in ('inner_fraction', 'min_support', 'min_z_m', 'max_z_m',
                      'max_relative_iqr', 'mad_multiplier', 'min_tolerance_m'):
            for bad in (float('nan'), float('inf'), -float('inf'), True, '1'):
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                    SurfaceConfig(**{field: bad})
        for count in (True, 1.5, 0, -1):
            with self.subTest(count=count), self.assertRaises(ValueError):
                SurfaceConfig(min_pixels=count)

    def setUp(self):
        y, x = np.indices((40, 50))
        self.mapping = np.stack([x, y], axis=-1).astype(float)
        self.disparity = np.full((40, 50), 10.0)
        self.valid = np.ones((40, 50), bool)
        self.q = np.array([[1,0,0,-25], [0,1,0,-20], [0,0,0,100], [0,0,2,0]], float)
        self.box = [5,5,45,35]

    def infer(self, **kw):
        args = dict(box=self.box, mapping=self.mapping, disparity=self.disparity,
                    valid=self.valid, q=self.q, detection_us=100, depth_us=100)
        args.update(kw)
        return associate_surface(**args)

    def test_known_surface_actual_ray_and_axes(self):
        result = self.infer()
        self.assertEqual(result['status'], 'SURFACE_ESTIMATE')
        u,v = result['rectified_pixel']
        np.testing.assert_allclose(result['xyz_m'], [(u-25)*.05, (v-20)*.05, 5])
        self.assertGreaterEqual(result['radial_distance_m'], 5)

    def test_stale_and_future_depth_rejected(self):
        for stamp in (99,101):
            with self.assertRaises(ValueError): self.infer(depth_us=stamp)

    def test_no_depth_and_sparse_depth_abstain(self):
        self.valid[:] = False
        self.assertIsNone(self.infer()['xyz_m'])
        self.valid[20,25] = True
        self.assertEqual(self.infer()['status'], 'INSUFFICIENT_DEPTH')

    def test_zero_mad_and_outlier(self):
        self.disparity[20,25] = .7
        result = self.infer()
        self.assertEqual(result['status'], 'SURFACE_ESTIMATE')
        self.assertEqual(result['xyz_m'][2], 5)
        self.assertLess(result['retained_pixels'], result['valid_pixels'])

    def test_balanced_foreground_background_abstains(self):
        self.disparity[:,25:] = 2.5
        self.assertEqual(self.infer()['status'], 'AMBIGUOUS_DEPTH_LAYERS')

    def test_minority_target_at_five_metres_does_not_return_twenty_metre_background(self):
        self.disparity[:] = 2.5  # Z=20 m
        self.disparity[16:24,21:29] = 10.  # 64/432 ROI pixels at Z=5 m
        result = self.infer()
        self.assertEqual(result['median_z_m'], 20.)
        self.assertEqual(result['iqr_z_m'], 0.)
        self.assertEqual(result['status'], 'AMBIGUOUS_DEPTH_LAYERS')
        self.assertIsNone(result['xyz_m'])
        self.assertIsNone(result['radial_distance_m'])
        self.assertNotIn('rectified_pixel', result)
        self.assertEqual([v['pixels'] for v in result['depth_layers']], [64,368])
        self.assertEqual([v['median_z_m'] for v in result['depth_layers']], [5.,20.])

    def test_nearer_occluder_is_not_automatically_assigned_to_target(self):
        self.disparity[16:24,21:29] = 2.5  # target behind a majority near layer
        result = self.infer()
        self.assertEqual(result['median_z_m'], 5.)
        self.assertEqual(result['status'], 'AMBIGUOUS_DEPTH_LAYERS')
        self.assertIsNone(result['xyz_m'])

    def test_supported_layer_below_ten_percent_is_not_discarded_as_outlier(self):
        self.disparity[:] = 2.5
        self.disparity[18:21,23:27] = 10.  # 12/432 pixels
        result = self.infer()
        self.assertEqual(result['status'], 'AMBIGUOUS_DEPTH_LAYERS')
        self.assertLess(result['depth_layers'][0]['support_fraction'], .1)

    def test_single_smooth_surface_is_retained(self):
        depths = np.broadcast_to(np.linspace(4.5,5.5,50), self.disparity.shape)
        self.disparity[:] = 50/depths
        self.assertEqual(self.infer()['status'], 'SURFACE_ESTIMATE')

    def test_invalid_near_layer_cannot_create_ambiguity(self):
        self.disparity[:] = 2.5
        self.disparity[16:24,21:29] = 10.
        self.valid[16:24,21:29] = False
        result = self.infer()
        self.assertEqual(result['status'], 'SURFACE_ESTIMATE')
        self.assertEqual(result['xyz_m'][2], 20.)

    def test_continuously_dispersed_depth_still_abstains(self):
        depths = np.broadcast_to(np.linspace(2,30,50), self.disparity.shape)
        self.disparity[:] = 50/depths
        self.assertEqual(self.infer()['status'], 'DISPERSED_DEPTH')

    def test_invalid_depth_abstains(self):
        for value in (np.nan, -1, 0, .1):
            self.disparity[:] = value
            self.assertIsNone(self.infer()['xyz_m'])

    def test_disparity_outside_search_does_not_yield_near_xyz(self):
        q = self.q.copy(); q[2,3] = 570; q[3,2] = 1/.6
        self.disparity[:] = 114.  # Z=3 m, outside the configured 0..95 search
        result = self.infer(q=q)
        self.assertEqual(result['status'], 'OUTSIDE_STEREO_SEARCH_RANGE')
        self.assertIsNone(result['xyz_m'])
        self.assertEqual(result['search_range_rejected_pixels'], result['mapped_pixels'])
        self.assertAlmostEqual(result['depth_range']['effective_min_z_m'], 3.6)
        self.assertEqual(result['depth_range']['surface_filter_min_z_m'], 1.)

    def test_disparity_endpoint_is_accepted_without_roundoff_rejection(self):
        q = self.q.copy(); q[2,3] = 570; q[3,2] = 1/.6
        self.disparity[:] = 95.
        result = self.infer(q=q)
        self.assertEqual(result['status'], 'SURFACE_ESTIMATE')
        self.assertAlmostEqual(result['xyz_m'][2], 3.6)
        self.assertEqual(result['search_range_rejected_pixels'], 0)

    def test_absence_of_disparity_cannot_identify_near_object_or_texture_failure(self):
        self.valid[:] = False
        self.disparity[:] = np.nan
        result = self.infer()
        self.assertEqual(result['status'], 'INSUFFICIENT_DEPTH')
        self.assertEqual(result['depth_absence_cause'], 'UNDETERMINED')
        self.assertEqual(result['search_range_rejected_pixels'], 0)

    def test_surface_uses_actual_search_configuration(self):
        self.disparity[:] = 20.
        result = self.infer(stereo_config=StereoConfig(num_disparities=16))
        self.assertEqual(result['status'], 'OUTSIDE_STEREO_SEARCH_RANGE')
        self.assertAlmostEqual(result['depth_range']['effective_min_z_m'], 50/15)
        self.assertEqual(self.infer()['status'], 'SURFACE_ESTIMATE')

    def test_stricter_surface_minimum_still_applies(self):
        self.assertEqual(self.infer(config=SurfaceConfig(min_z_m=6.))['status'], 'INSUFFICIENT_DEPTH')
        self.assertEqual(self.infer(config=SurfaceConfig(min_z_m=6.))['depth_range']['effective_min_z_m'], 6.)

    def test_outside_and_malformed_boxes(self):
        self.assertEqual(self.infer(box=[-30,-30,-10,-10])['status'], 'EMPTY_ROI')
        for box in ([1,2,1,3], [1,2,np.nan,3]):
            with self.assertRaises(ValueError): self.infer(box=box)
        self.assertEqual(self.infer(box=[-3,-3,30,30])['status'], 'SURFACE_ESTIMATE')

    def test_map_shift_dedup_and_out_of_field(self):
        self.mapping[...,0] += 5
        pixels = mapped_roi([0,0,10,10], self.mapping, (40,50))
        self.assertEqual(pixels[:,0].min(),5)
        self.assertEqual(pixels[:,0].max(),14)
        self.mapping[:] = [20,20]
        self.assertEqual(len(mapped_roi(self.box,self.mapping,(40,50))),1)
        self.assertEqual(self.infer()['status'], 'INSUFFICIENT_DEPTH')
        self.mapping[:] = [np.nan,-1]
        self.assertEqual(self.infer()['status'], 'EMPTY_ROI')

    def test_motion_association_uses_mapped_region(self):
        self.mapping[...,0] += 10
        result = region_motion_support([0,0,10,10], self.mapping, (40,50),
                                       [[12,5],[2,5],[18,5]],
                                       ['RESIDUAL_CANDIDATE','RESIDUAL_CANDIDATE','UNKNOWN'])
        self.assertEqual(result['tracked_points'],2)
        self.assertEqual(result['RESIDUAL_CANDIDATE'],1)
        self.assertEqual(result['UNKNOWN'],1)
        self.assertEqual(result['mobility'],'UNCONFIRMED')

    def test_pixel_dedup_matches_row_sort_with_rounding_and_invalid_maps(self):
        rng = np.random.default_rng(1510)
        for dtype in (np.float32, np.float64):
            mapping = rng.uniform([-2, -2], [52, 42], (25, 35, 2)).astype(dtype)
            mapping[0, :8] = [[.5, .5], [1.5, 1.5], [2.5, 2.5], [49, 39],
                              [49.01, 20], [20, 39.01], [np.nan, 2], [2, np.inf]]
            mapping[1:4] = mapping[0]  # Repeated coordinates and rounded collisions.
            mapping = mapping[:, ::-1]  # Noncontiguous native mapping.
            raw = mapping.reshape(-1, 2)
            keep = (np.isfinite(raw).all(axis=1) & (raw >= 0).all(axis=1)
                    & (raw <= [49, 39]).all(axis=1))
            expected = np.unique(np.rint(raw[keep]).astype(int), axis=0)
            before = mapping.copy()
            with self.subTest(dtype=dtype):
                actual = mapped_roi([0, 0, 35, 25], mapping, (40, 50))
                np.testing.assert_array_equal(actual, expected)
                self.assertEqual(actual.dtype, expected.dtype)
                np.testing.assert_array_equal(mapping, before)

    def test_inner_region_and_surface_ties_keep_x_then_y_order(self):
        pixels = mapped_roi([2, 2, 8, 6], self.mapping, (40, 50), fraction=.5)
        np.testing.assert_array_equal(pixels, [[4,3], [4,4], [5,3], [5,4], [6,3], [6,4]])
        # Four equidistant centre pixels: the original order selects x=24,y=19.
        self.assertEqual(self.infer()['rectified_pixel'], [24, 19])


if __name__ == '__main__': unittest.main()
