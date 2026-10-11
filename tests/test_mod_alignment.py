import io
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pfe_events.http_range import HTTPRangeReader
from pfe_events.mod_alignment import (rgb_to_event_homography, compare_projected_rgb,
                                      select_verified_frame, verified_timestamp)


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
