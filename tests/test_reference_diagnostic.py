import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pfe_events.reference_diagnostic import box_support


class ReferenceDiagnosticTests(unittest.TestCase):
    def run_case(self, points=(), depths=(), states=(), *, boxes=None, margin=0, unavailable=None):
        if boxes is None: boxes = [{'tube_index': 7, 'xyxy': [2, 2, 8, 8]}]
        return box_support(boxes, np.asarray(points, dtype=float).reshape(-1, 2),
                           np.asarray(depths), states, np.ones((10, 10)),
                           margin=margin, unavailable=unavailable)

    def test_half_open_boxes_and_pixel_centers(self):
        r = self.run_case([(2, 2), (8, 5), (7.9, 7.9)], [2, 2, 2], ['MODEL_CONSISTENT']*3)
        self.assertEqual(r['boxes'][0]['checked_tracks'], 2)
        self.assertEqual(r['boxes'][0]['roi_pixels'], 36)
        self.assertEqual(r['outside_reference_tracks'], 1)
        self.assertFalse(r['outside_reference_is_verified_negative'])

    def test_no_tracks_is_unknown_not_static(self):
        r = self.run_case()['boxes'][0]
        self.assertEqual(r['diagnostic'], 'NO_CHECKED_TRACKS')
        self.assertIsNone(r['object_motion_prediction'])
        self.assertEqual(r['active_pixels'], 36)

    def test_missing_depth_and_model_failure_are_separate(self):
        a = self.run_case([(4, 4)], [np.nan], ['UNKNOWN'])['boxes'][0]
        b = self.run_case([(4, 4)], [2], ['UNKNOWN'])['boxes'][0]
        self.assertEqual(a['diagnostic'], 'NO_USABLE_DEPTH')
        self.assertEqual(b['diagnostic'], 'MODEL_OR_PROJECTION_UNAVAILABLE')

    def test_no_residual_is_not_static_classification(self):
        r = self.run_case([(4, 4)], [2], ['MODEL_CONSISTENT'])['boxes'][0]
        self.assertEqual(r['diagnostic'], 'NO_RESIDUAL_OBSERVED')
        self.assertIsNone(r['object_motion_prediction'])

    def test_overlapping_boxes_do_not_create_exclusive_detections(self):
        boxes = [{'tube_index': 1, 'xyxy': [2, 2, 8, 8]}, {'tube_index': 2, 'xyxy': [3, 3, 6, 6]}]
        r = self.run_case([(4, 4)], [2], ['RESIDUAL_CANDIDATE'], boxes=boxes)
        self.assertEqual(r['shared_reference_tracks'], 1)
        for row in r['boxes']:
            self.assertEqual(row['diagnostic'], 'SHARED_RESIDUAL_ONLY')
            self.assertEqual(row['exclusive_residual_tracks'], 0)

    def test_margin_sensitivity_changes_membership_not_input(self):
        points = [(1, 4)]
        a = self.run_case(points, [2], ['RESIDUAL_CANDIDATE'], margin=0)
        b = self.run_case(points, [2], ['RESIDUAL_CANDIDATE'], margin=2)
        self.assertEqual(a['boxes'][0]['residual_tracks'], 0)
        self.assertEqual(b['boxes'][0]['exclusive_residual_tracks'], 1)
        self.assertEqual(points, [(1, 4)])

    def test_empty_shrunk_and_clipped_regions(self):
        a = self.run_case(margin=-5)['boxes'][0]
        b = self.run_case(margin=5)['boxes'][0]
        self.assertEqual(a['diagnostic'], 'EMPTY_ROI')
        self.assertIsNone(a['active_fraction'])
        self.assertEqual(b['roi_pixels'], 100)

    def test_startup_abstention_takes_precedence(self):
        r = self.run_case(unavailable='INSUFFICIENT_HISTORY')['boxes'][0]
        self.assertEqual(r['diagnostic'], 'INSUFFICIENT_HISTORY')

    def test_rejects_invalid_status_depth_points_and_box(self):
        for args in (([(4, 4)], [np.nan], ['MODEL_CONSISTENT']),
                     ([(10, 4)], [2], ['UNKNOWN']), ([(4, 4)], [2], ['STATIC'])):
            with self.subTest(args=args), self.assertRaises(ValueError): self.run_case(*args)
        with self.assertRaises(ValueError):
            self.run_case(boxes=[{'tube_index': 0, 'xyxy': [5, 5, 4, 8]}])

    def test_no_boxes_or_no_points_are_supported(self):
        r = self.run_case([(1, 1)], [2], ['RESIDUAL_CANDIDATE'], boxes=[])
        self.assertEqual(r['outside_reference_residual_tracks'], 1)
        self.assertEqual(self.run_case(boxes=[])['boxes'], [])


if __name__ == '__main__': unittest.main()
