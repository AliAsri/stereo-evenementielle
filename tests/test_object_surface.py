import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.object_surface import associate_surface, mapped_roi, region_motion_support


class SurfaceTests(unittest.TestCase):
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
        self.assertEqual(self.infer()['status'], 'DISPERSED_DEPTH')

    def test_invalid_depth_abstains(self):
        for value in (np.nan, -1, 0, .1):
            self.disparity[:] = value
            self.assertIsNone(self.infer()['xyz_m'])

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


if __name__ == '__main__': unittest.main()
