import io
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pfe_events.http_range import HTTPRangeReader
from pfe_events.mod_alignment import (rgb_to_event_homography, compare_projected_rgb,
                                      select_verified_frame, verified_timestamp,parallax_mask_reachability)


class AlignmentTests(unittest.TestCase):
    def calibration(self):
        t = np.eye(4); t[0, 3] = .04
        return {'intrinsics': {'camRect0': {'camera_matrix': [100, 100, 5, 6]},
                               'camRect1': {'camera_matrix': [200, 200, 20, 30]}},
                'extrinsics': {'T_10': t, 'R_rect0': np.eye(3), 'R_rect1': np.eye(3)}}

    def test_projection_uses_correct_ray_direction(self):
        c = self.calibration()
        a = .2; rotation = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
        c['extrinsics']['T_10'][:3, :3] = rotation
        h = rgb_to_event_homography(c)
        ray0 = np.array([.1, -.15, 1.]); ray1 = rotation @ ray0
        pixel1 = np.array([200*ray1[0]/ray1[2]+20, 200*ray1[1]/ray1[2]+30, 1])
        actual = h @ pixel1; actual /= actual[2]
        np.testing.assert_allclose(actual, [15, -9, 1], atol=1e-10)

    def test_translation_is_explicitly_not_a_depth_warp(self):
        c = self.calibration(); h = rgb_to_event_homography(c)
        c['extrinsics']['T_10'][0, 3] = 100
        np.testing.assert_array_equal(h, rgb_to_event_homography(c))

    def test_parallax_direction_and_positive_depth_range(self):
        c=self.calibration()
        mask=np.zeros((20,30),bool);mask[6,9]=True
        result=parallax_mask_reachability(np.array([[5,6],[15,6]]),mask,c)
        self.assertTrue(result['points'][0]['possible'])
        self.assertAlmostEqual(result['points'][0]['max_compatible_depth_m'],4/3.5)
        self.assertFalse(result['points'][1]['possible'])
        self.assertAlmostEqual(result['points'][1]['distance_to_positive_pixel_squares_px'],5.5)

    def test_parallax_formula_matches_full_three_dimensional_camera_chain(self):
        c=self.calibration()
        angle=.12
        rotation=np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
        c['extrinsics']['T_10'][:3,:3]=rotation
        c['extrinsics']['T_10'][:3,3]=[.04,.002,-.01]
        c['extrinsics']['R_rect0']=rotation.T
        b=.08
        c['extrinsics']['R_rect1']=np.array([[1,0,0],[0,np.cos(b),-np.sin(b)],[0,np.sin(b),np.cos(b)]])
        p=np.array([[8.,10.]])
        r=parallax_mask_reachability(p,np.ones((30,30),bool),c)
        v=np.asarray(r['effective_translation_m'])
        d=np.asarray(r['points'][0]['direction_px_m'])
        k1=np.array([[200,0,20],[0,200,30],[0,0,1]])
        h=rgb_to_event_homography(c)
        for depth in (1,3,20):
            rect0=np.array([(8-5)/100*depth,(10-6)/100*depth,depth])
            native0=np.asarray(c['extrinsics']['R_rect0']).T@rect0
            native1=rotation@native0+c['extrinsics']['T_10'][:3,3]
            rect1=np.asarray(c['extrinsics']['R_rect1'])@native1
            full=h@(k1@rect1)
            np.testing.assert_allclose(p[0]+d/(depth+v[2]),full[:2]/full[2],atol=1e-11)

    def test_parallax_checks_negative_projective_branch_for_positive_event_depth(self):
        c=self.calibration();c['extrinsics']['T_10'][:3,3]=[.01,0,-1]
        mask=np.zeros((20,20),bool);mask[6,3]=True
        row=parallax_mask_reachability(np.array([[5,6]]),mask,c)['points'][0]
        self.assertTrue(row['possible'])
        self.assertAlmostEqual(row['max_compatible_depth_m'],.6)

    def test_parallax_zero_translation_and_empty_foreground(self):
        c=self.calibration();c['extrinsics']['T_10'][:3,3]=0
        mask=np.zeros((20,20),bool);mask[6,5]=True
        rows=parallax_mask_reachability(np.array([[5,6],[10,6]]),mask,c)['points']
        self.assertTrue(rows[0]['possible']);self.assertTrue(rows[0]['unbounded_max_depth'])
        self.assertFalse(rows[1]['possible'])
        mask[:]=False
        row=parallax_mask_reachability(np.array([[5,6]]),mask,c)['points'][0]
        self.assertFalse(row['possible']);self.assertIsNone(row['distance_to_positive_pixel_squares_px'])

    def test_parallax_closed_pixel_boundary_is_conservative(self):
        c=self.calibration()
        mask=np.zeros((20,20),bool);mask[6,9]=True
        row=parallax_mask_reachability(np.array([[5.,6.5]]),mask,c)['points'][0]
        self.assertTrue(row['possible'])
        with self.assertRaises(ValueError): parallax_mask_reachability(np.array([[np.nan,0]]),mask,c)
        with self.assertRaises(ValueError): parallax_mask_reachability(np.array([[0.,0.]]),mask.astype(np.uint8),c)

    def test_parallax_positive_axial_translation_has_finite_projective_extent(self):
        c=self.calibration();c['extrinsics']['T_10'][2,3]=1
        mask=np.zeros((20,20),bool);mask[6,10]=True
        self.assertFalse(parallax_mask_reachability(np.array([[5,6]]),mask,c)['points'][0]['possible'])
        mask[:]=False;mask[6,9]=True
        row=parallax_mask_reachability(np.array([[5,6]]),mask,c)['points'][0]
        self.assertTrue(row['possible'])
        self.assertAlmostEqual(row['max_compatible_depth_m'],4/3.5-1)

    def test_rejects_invalid_calibration(self):
        c = self.calibration(); c['extrinsics']['R_rect0'][0, 0] = 2
        with self.assertRaises(ValueError): rgb_to_event_homography(c)
        c = self.calibration(); c['intrinsics']['camRect0']['camera_matrix'][0] = 0
        with self.assertRaises(ValueError): rgb_to_event_homography(c)

    def test_photometric_identity_and_support(self):
        a = np.arange(10*12*3, dtype=np.uint8).reshape(10, 12, 3)
        score, warped = compare_projected_rgb(a, a, np.eye(3))
        self.assertEqual(score['mae_8bit'], 0)
        self.assertEqual(score['support_pixels'], 120)
        np.testing.assert_array_equal(a, warped)
        h = np.eye(3); h[0, 2] = 1000
        with self.assertRaisesRegex(ValueError, 'support'): compare_projected_rgb(a, a, h)

    def test_frame_gate_abstains_on_tie_or_bad_match(self):
        def scores(a, b): return [{'dsec_index': 3, 'mae_8bit': a}, {'dsec_index': 4, 'mae_8bit': b}]
        self.assertEqual(select_verified_frame(scores(.2, 4))['dsec_index'], 3)
        for pair in ((.2, .2), (.2, .8), (3, 6), (np.nan, 6)):
            with self.subTest(pair=pair), self.assertRaises(ValueError): select_verified_frame(scores(*pair))

    def test_exposure_and_unified_timestamp_stay_distinct(self):
        result = verified_timestamp(np.array([100, 200]), np.array([[90, 104], [180, 208]]), 1)
        self.assertEqual(result['timestamp_us'], 200)
        self.assertEqual(result['exposure_duration_us'], 28)
        self.assertEqual(result['unified_minus_left_midpoint_us'], 6)
        for i in (-1, 2):
            with self.assertRaises(ValueError): verified_timestamp(np.array([100, 200]), np.array([[90, 104], [180, 208]]), i)


class RangeTests(unittest.TestCase):
    def reader(self, *, status=206, content_range='bytes 1-3/6', etags=None):
        self.calls = []
        def opener(request, timeout):
            self.calls.append(request)
            class Response(io.BytesIO): pass
            r = Response(b'bcd'); r.status = status
            r.headers = {'Content-Range': content_range, 'ETag': (etags or ['same'])[min(len(self.calls)-1, len(etags or ['same'])-1)]}
            return r
        return HTTPRangeReader('https://example.invalid/archive', 6, budget=6, opener=opener)

    def test_seek_and_exact_range(self):
        r = self.reader(); self.assertEqual(r.seek(-5, 2), 1)
        self.assertEqual(r.read(3), b'bcd'); self.assertEqual(r.tell(), 4)
        self.assertEqual(r.transferred, 3)
        self.assertEqual(self.calls[0].get_header('Range'), 'bytes=1-3')

    def test_refuses_full_response_wrong_range_before_body(self):
        for r in (self.reader(status=200), self.reader(content_range='bytes 0-2/6')):
            r.seek(1)
            with self.assertRaisesRegex(ValueError, 'exact byte range'): r.read(3)
            self.assertEqual(r.transferred, 0)

    def test_budget_prevents_request(self):
        r = self.reader(); r.budget = 2; r.seek(1)
        with self.assertRaisesRegex(ValueError, 'budget'): r.read(3)
        self.assertEqual(self.calls, [])

    def test_rejects_archive_change_and_short_read(self):
        r = self.reader(etags=['a', 'b']); r.seek(1); r.read(3); r.seek(1)
        with self.assertRaisesRegex(ValueError, 'changed'): r.read(3)
        r = self.reader(content_range='bytes 1-4/6'); r.seek(1)
        with self.assertRaisesRegex(ValueError, 'Truncated'): r.read(4)

    def test_eof_no_request_and_invalid_seek(self):
        r = self.reader(); r.seek(6); self.assertEqual(r.read(), b'')
        self.assertEqual(self.calls, [])
        with self.assertRaises(ValueError): r.seek(-1)


if __name__ == '__main__': unittest.main()
