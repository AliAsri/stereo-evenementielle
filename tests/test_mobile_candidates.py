"""M10 analytic controls: persistence is not proof of independent object motion."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.mobile_candidates import ResidualCandidateTracker,ImageCandidateDetector,CandidateConfig,iou,warped_box
from pfe_events.mobile_controls import control_points


class MobileCandidateTests(unittest.TestCase):
    def test_static_and_camera_translation_rejected(self):
        for kind in ['fixed_static','global_translation']:
            detector=ResidualCandidateTracker()
            for i in range(1,6):
                out=detector.update(*control_points(kind),i*20000)
                self.assertTrue(out['valid']);self.assertFalse(out['regions'] or out['tentative_regions'])

    def test_local_motion_persistence_and_immediate_stop_of_signal(self):
        for kind in ['local_motion','combined_motion']:
            detector=ResidualCandidateTracker();results=[]
            for i in range(1,9): results.append(detector.update(*control_points(kind,3<=i<=6),i*20000))
            self.assertTrue(results[2]['tentative_regions']);self.assertFalse(results[3]['regions'])
            self.assertEqual(results[4]['regions'][0]['consecutive_observations'],3)
            self.assertEqual(results[4]['regions'][0]['first_seen_us'],60000)
            self.assertEqual(results[4]['regions'][0]['status'],'PERSISTENT_CANDIDATE')
            self.assertFalse(results[6]['regions'] or results[6]['tentative_regions'])

    def test_incoherent_correspondences_filtered(self):
        detector=ResidualCandidateTracker()
        for i in range(1,5):
            out=detector.update(*control_points('incoherent_noise'),i*20000)
            self.assertFalse(out['regions'] or out['tentative_regions'])
            self.assertTrue(any('INCOHERENT_DIRECTIONS' in r['reasons'] for r in out['rejections']))

    def test_parallax_is_explicit_counterexample(self):
        for a,b in zip(control_points('combined_motion'),control_points('parallax_counterexample')):
            np.testing.assert_array_equal(a,b)
        detector=ResidualCandidateTracker()
        for i in range(1,4): out=detector.update(*control_points('parallax_counterexample'),i*20000)
        self.assertTrue(out['regions'])  # Known failure: near static layer can look like a moving patch.
        self.assertIn('NOT_CONFIRMED',out['claim'])

    def test_local_rotation_can_be_missed_by_direction_coherence(self):
        detector=ResidualCandidateTracker()
        for i in range(1,4): out=detector.update(*control_points('local_rotation'),i*20000)
        self.assertFalse(out['regions'])  # Known scope limit, not a successful moving-object detector.

    def test_abstention_resets_persistence(self):
        detector=ResidualCandidateTracker();p,q=control_points('local_motion')
        detector.update(p,q,20000);detector.update(p,q,40000)
        empty=np.empty((0,2),np.float32);out=detector.update(empty,empty,60000)
        self.assertFalse(out['valid'])
        out=detector.update(p,q,80000)
        self.assertFalse(out['regions']);self.assertEqual(out['tentative_regions'][0]['consecutive_observations'],1)

    def test_bad_timestamp_or_points_preserve_state(self):
        detector=ResidualCandidateTracker();p,q=control_points('local_motion');detector.update(p,q,20000)
        with self.assertRaises(ValueError): detector.update(p,q,60000)
        bad=q.copy();bad[0,0]=np.nan
        with self.assertRaises(ValueError): detector.update(p,bad,40000)
        self.assertEqual(detector.previous_end,20000)
        self.assertEqual(detector.previous[0]['consecutive_observations'],1)

    def test_geometry_and_broad_region_filter(self):
        self.assertEqual(iou([0,0,10,10],[0,0,10,10]),1)
        np.testing.assert_array_equal(warped_box([10,20,30,40],np.array([[1,0,2],[0,1,-1]]),2),[14,18,34,38])
        detector=ResidualCandidateTracker(config=CandidateConfig(max_box_area_fraction=.001))
        out=detector.update(*control_points('local_motion'),20000)
        self.assertTrue(any('BROAD_REGION' in r['reasons'] for r in out['rejections']))

    def test_images_warmup_abstention_and_invalid_configuration(self):
        detector=ImageCandidateDetector();im=np.zeros((240,320),np.uint8)
        self.assertEqual(detector.update(im,20000)['status'],'WARMUP')
        self.assertFalse(detector.update(im,40000)['valid'])
        with self.assertRaises(ValueError): ResidualCandidateTracker(config=CandidateConfig(consecutive_observations=0))


if __name__=='__main__': unittest.main()
