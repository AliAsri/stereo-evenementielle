import io
import sys
import tarfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'scripts/diagnostics'))
from pfe_events.evimo_reference import (read_metadata, timestamp_summary, pose_matrix,
                                      pose_pair_reference, radtan_calibration)
from download_evimo_sample import BoundedReader, selected_name, SEQUENCE
from check_evimo_pose import (project, native_labels, native_seed_support,
                             support_retention, corner_budget_audit, chain_tracks,
                             validate_frozen_selection, VISIBLE_SEQUENCE, last_event_image,
                             orb_checked_matches,ORB_CONFIG)
import check_evimo_pose


class OrbCorrespondenceTests(unittest.TestCase):
    def detector(self):
        from unittest.mock import Mock
        source=[cv2.KeyPoint(60,60,31),cv2.KeyPoint(80,80,31),cv2.KeyPoint(100,100,31)]
        destination=[cv2.KeyPoint(110,110,31),cv2.KeyPoint(90,90,31)]
        a=np.array([[0]*32,[255]*32,[170]*32],np.uint8)
        b=np.array([[170]*32,[255]*32],np.uint8)
        orb=Mock();orb.detectAndCompute.side_effect=[(source,a),(destination,b)]
        return orb

    def test_mutual_match_preserves_source_ids_after_short_rejection(self):
        image=np.zeros((160,160),np.uint8)
        with patch.object(check_evimo_pose.cv2,'ORB_create',return_value=self.detector()) as create, \
             patch.object(check_evimo_pose,'track_seeds',return_value=(None,np.array([False,True,True]),np.array([2,.2,.3]))):
            p,q,fb,seeds,stats,arrays,timing=orb_checked_matches([image]*3)
        create.assert_called_once_with(**ORB_CONFIG)
        np.testing.assert_array_equal(p,[[80,80],[100,100]])
        np.testing.assert_array_equal(q,[[90,90],[110,110]])
        np.testing.assert_array_equal(arrays['matched_source_ids'],[1,2])
        np.testing.assert_array_equal(arrays['matched_destination_ids'],[1,0])
        np.testing.assert_array_equal(arrays['hamming_distance'],[0,0])
        np.testing.assert_array_equal(fb,[.2,.3])
        self.assertEqual(len(seeds),2);self.assertEqual(stats['long_matches'],2)
        self.assertAlmostEqual(sum(timing[k] for k in ('detection_descriptors','short_lk','global_matching')),timing['total'])

    def test_empty_real_images_abstain_without_matching(self):
        image=np.zeros((160,160),np.uint8)
        with patch.object(check_evimo_pose.cv2,'BFMatcher',side_effect=AssertionError('no descriptors')):
            p,q,fb,seeds,stats,arrays,_=orb_checked_matches([image]*3)
        self.assertEqual(p.shape,(0,2));self.assertEqual(q.shape,(0,2))
        self.assertEqual(len(fb),0);self.assertEqual(len(seeds),0)
        self.assertEqual(stats['status'],'NO_MATCHES')

    def test_all_short_rejections_prevent_long_matching(self):
        image=np.zeros((160,160),np.uint8)
        with patch.object(check_evimo_pose.cv2,'ORB_create',return_value=self.detector()), \
             patch.object(check_evimo_pose,'track_seeds',return_value=(None,np.zeros(3,bool),np.ones(3)*2)), \
             patch.object(check_evimo_pose.cv2,'BFMatcher',side_effect=AssertionError('no short support')):
            p,_,_,seeds,stats,_,_=orb_checked_matches([image]*3)
        self.assertEqual(len(p),0);self.assertEqual(len(seeds),0)
        self.assertEqual(stats['features'],3);self.assertEqual(stats['checked_tracks'],0)

    def test_missing_destination_is_an_explicit_empty_match_set(self):
        image=np.zeros((160,160),np.uint8);orb=self.detector()
        first=orb.detectAndCompute.side_effect
        source=next(iter(first))
        orb.detectAndCompute.side_effect=[source,([],None)]
        with patch.object(check_evimo_pose.cv2,'ORB_create',return_value=orb), \
             patch.object(check_evimo_pose,'track_seeds',return_value=(None,np.ones(3,bool),np.zeros(3))):
            p,_,_,seeds,stats,_,_=orb_checked_matches([image]*3)
        self.assertEqual(len(p),0);self.assertEqual(len(seeds),3)
        self.assertEqual(stats['destination_features'],0)

    def test_known_large_synthetic_translation_has_correct_correspondences(self):
        rng=np.random.default_rng(707)
        image=cv2.GaussianBlur(rng.integers(0,256,(320,480),dtype=np.uint8),(5,5),0)
        moved=cv2.warpAffine(image,np.array([[1,0,70],[0,1,-12]],np.float32),(480,320))
        opencl=cv2.ocl.useOpenCL()
        try:
            cv2.ocl.setUseOpenCL(False)
            p,q,_,_,stats,arrays,_=orb_checked_matches([image,image,moved])
        finally:
            cv2.ocl.setUseOpenCL(opencl)
        error=np.linalg.norm(q-p-[70,-12],axis=1)
        self.assertGreaterEqual(int((error<=3).sum()),15)
        self.assertLessEqual(stats['features'],400);self.assertLessEqual(stats['destination_features'],400)
        self.assertEqual(len(np.unique(arrays['matched_destination_ids'])),len(q))

    def test_invalid_images_rejected_before_extraction(self):
        image=np.zeros((160,160),np.uint8)
        for images in ([image]*2,[image,image.astype(float),image],[image,image,image[:100]],
                       [np.zeros((32,32),np.uint8)]*3):
            with self.assertRaises(ValueError): orb_checked_matches(images)

    def test_orb_cannot_be_combined_with_other_experiment_modes(self):
        for extra in ([],['--visible-control','--time-surface'],['--visible-control','--coarse-tracking'],
                      ['--visible-control','--spatial-seeds']):
            with self.subTest(extra=extra),patch.object(sys,'argv',['diag','--output','outputs/unused_orb_test',
                                                                    '--orb-correspondences',*extra]):
                with self.assertRaises(ValueError): check_evimo_pose.main()


class LastEventImageTests(unittest.TestCase):
    def test_half_open_window_ignores_old_and_future_events(self):
        xy = np.array([[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]])
        image = last_event_image(xy, [0., 1., 1.5, 2., 3.], (2, 5), end=2., window=1.)
        np.testing.assert_array_equal(image[0], [0, 1, 128, 0, 0])
        self.assertEqual(image.dtype, np.uint8)

    def test_latest_timestamp_wins_independent_of_order_and_event_multiplicity(self):
        xy = np.array([[1, 1], [1, 1], [2, 1]])
        t = np.array([1.75, 1.25, 1.5])
        expected = last_event_image(xy, t, (3, 3), end=2., window=1.)
        actual = last_event_image(np.concatenate([xy[::-1], xy]), np.concatenate([t[::-1], t]),
                                  (3, 3), end=2., window=1.)
        np.testing.assert_array_equal(actual, expected)
        self.assertGreater(actual[1, 1], actual[1, 2])

    def test_empty_and_invalid_events(self):
        self.assertFalse(last_event_image(np.empty((0, 2), int), [], (3, 3), end=2.).any())
        for xy, t in (([[3, 0]], [1.99]), ([[0, 0]], [np.nan]), ([[.5, 0]], [1.99])):
            with self.assertRaises(ValueError):
                last_event_image(xy, t, (3, 3), end=2.)


class ChainedTrackingTests(unittest.TestCase):
    def test_rejected_id_is_never_revived(self):
        images = [np.zeros((32, 32), np.uint8) for _ in range(4)]
        points = np.array([[5, 5], [10, 10]], np.float32)
        calls = []
        def track(previous, current, seeds):
            calls.append(seeds.copy())
            keep = np.ones(len(seeds), bool)
            if len(calls) == 1:
                keep[0] = False
            return seeds+1, keep, np.zeros(len(seeds))
        with patch('check_evimo_pose.track_seeds', side_effect=track):
            history, accepted, fb = chain_tracks(images, points)
        self.assertEqual([len(x) for x in calls], [2, 1, 1])
        self.assertFalse(accepted[:, 0].any())
        self.assertTrue(np.isnan(history[1:, 0]).all())
        np.testing.assert_array_equal(history[-1, 1], [13, 13])
        self.assertTrue(np.isnan(fb[1:, 0]).all())

    def test_empty_tracks_and_missing_interval(self):
        images = [np.zeros((32, 32), np.uint8) for _ in range(3)]
        history, accepted, fb = chain_tracks(images, np.empty((0, 2), np.float32))
        self.assertEqual(history.shape, (3, 0, 2))
        self.assertEqual(accepted.shape, (2, 0))
        self.assertEqual(fb.shape, (2, 0))
        with self.assertRaises(ValueError):
            chain_tracks(images[:1], np.empty((0, 2), np.float32))


class EvimoReferenceTests(unittest.TestCase):
    def test_frozen_controls_cannot_exchange_pair_target_or_thresholds(self):
        legacy = dict(frame_ids=[68, 74], target_object_id=24)
        self.assertEqual(validate_frozen_selection(legacy), ((68, 74), 24))
        visible = dict(frame_ids=[211, 217], target_object_id=6, criterion=dict(
            sequence=VISIBLE_SEQUENCE, interval_s=.1, window_s=.05,
            min_world_origin_displacement_m=.01, min_mask_pixels_each_endpoint=1000,
            mask_margin_px=10))
        self.assertEqual(validate_frozen_selection(visible, visible=True), ((211, 217), 6))
        with self.assertRaises(ValueError):
            validate_frozen_selection(visible)
        with self.assertRaises(ValueError):
            validate_frozen_selection(legacy, visible=True)
        with self.assertRaises(ValueError):
            validate_frozen_selection({**visible, 'target_object_id':24}, visible=True)
        with self.assertRaises(ValueError):
            validate_frozen_selection({**visible, 'criterion':{**visible['criterion'], 'mask_margin_px':0}}, visible=True)

    def test_explicit_second_sequence_allowlist_keeps_original_isolated(self):
        sequence = 'left_camera/imo/train/scene15_dyn_test_00_000000'
        member = tarfile.TarInfo(sequence+'/dataset_info.npz')
        self.assertEqual(selected_name(member, sequence), 'dataset_info.npz')
        self.assertIsNone(selected_name(member))
        for name in (sequence+'/../dataset_info.npz', sequence+'/unlisted.npy',
                     SEQUENCE+'/dataset_info.npz'):
            self.assertIsNone(selected_name(tarfile.TarInfo(name), sequence))
        member.type = tarfile.SYMTYPE
        with self.assertRaises(ValueError):
            selected_name(member, sequence)

    def file(self, value):
        stream = io.BytesIO()
        np.savez(stream, meta=value)
        stream.seek(0)
        return stream

    def test_reads_plain_metadata_in_numpy_envelope(self):
        value = {'frames':[{'id':2,'ts':0.1}], 'meta': {'res_x':640}}
        self.assertEqual(read_metadata(self.file(value)), value)

    def test_rejects_callable_payload_without_execution(self):
        class Payload:
            def __reduce__(self):
                return (eval, ('1+1',))
        with self.assertRaisesRegex(ValueError, 'Unsupported metadata global'):
            read_metadata(self.file({'payload':Payload()}))

    def test_rejects_non_scalar_envelope(self):
        with self.assertRaisesRegex(ValueError, 'scalar object'):
            read_metadata(self.file(np.array([{},{}],dtype=object)))

    def test_rejects_cyclic_metadata(self):
        value = {}
        value['cycle'] = value
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            read_metadata(self.file(value))

    def test_preserves_irregular_reference_intervals(self):
        result=timestamp_summary([0.01,0.02,0.22])
        self.assertAlmostEqual(result['max_step_ms'],200)
        self.assertEqual(result['count'],3)

    def test_rejects_duplicate_backward_and_nan_times(self):
        for times in ([1,1],[2,1],[0,float('nan')]):
            with self.subTest(times=times), self.assertRaises(ValueError):
                timestamp_summary(times)

    def test_network_reader_cannot_pass_budget(self):
        source=io.BytesIO(b'abcdef')
        reader=BoundedReader(source,3)
        self.assertEqual(reader.read(20),b'abc')
        with self.assertRaises(ValueError):
            reader.read(1)
        self.assertEqual(source.tell(),3)

    def test_only_exact_allowlisted_archive_files(self):
        for name in ('../dataset_info.npz',SEQUENCE+'/../dataset_info.npz',SEQUENCE+'/other.npy'):
            self.assertIsNone(selected_name(tarfile.TarInfo(name)))
        member=tarfile.TarInfo(SEQUENCE+'/dataset_info.npz')
        self.assertEqual(selected_name(member),'dataset_info.npz')
        member.type=tarfile.SYMTYPE
        with self.assertRaises(ValueError):
            selected_name(member)


class PositiveSupportTests(unittest.TestCase):
    def test_empty_reference_support_is_not_a_successful_retention(self):
        result = support_retention(np.array([np.nan]), np.array([True]), np.array([True]))
        self.assertEqual(result['retained']['evaluable'], 0)
        self.assertIsNone(result['retained']['error']['median_px'])
        empty = support_retention(np.empty(0), np.zeros(0, bool), np.zeros(0, bool))
        self.assertEqual(empty['before']['tracks'], 0)
        self.assertIsNone(empty['before']['error']['mean_px'])

    def test_loss_of_compatible_points_is_counted_with_strict_three_pixel_rule(self):
        result = support_retention(np.array([.1, 4., 3., np.nan]),
                                   np.ones(4, bool), np.array([False, False, True, True]))
        self.assertEqual(result['excluded']['reference_error_at_most_3px'], 1)
        self.assertEqual(result['excluded']['reference_error_above_3px'], 1)
        self.assertEqual(result['retained']['reference_error_at_most_3px'], 1)
        self.assertEqual(result['retained']['evaluable'], 1)

    def test_global_budget_can_exclude_weak_corners_above_quality_threshold(self):
        image = np.zeros((480, 640), np.uint8)
        for y in range(70, 460, 12):
            for x in range(10, 630, 12):
                image[y:y+5, x:x+5] = 255
        image[25:32, 300:307] = 60
        mask = np.zeros_like(image, bool); mask[20:38, 295:313] = True
        result = corner_budget_audit(image, mask)
        self.assertTrue(result['budget_exhausted'])
        self.assertEqual(result['target_initial_features'], 0)
        self.assertGreater(result['target_local_maxima_above_quality'], 0)
        self.assertTrue(result['target_max_below_all_selected'])

    def test_empty_image_or_missing_mask_does_not_invent_corner_evidence(self):
        result = corner_budget_audit(np.zeros((32, 32), np.uint8), np.zeros((32, 32), bool))
        self.assertEqual(result['initial_features'], 0)
        self.assertIsNone(result['target_score_max'])
        self.assertIsNone(result['minimum_selected_score'])
        self.assertIsNone(result['target_max_below_all_selected'])


class NativeSupportTests(unittest.TestCase):
    def test_many_events_at_isolated_pixels_do_not_create_spatial_support(self):
        counts = np.zeros((15, 15), int)
        counts[7, 7] = 100000
        counts[5, 5] = 10
        keep, inside, active = native_seed_support([[7, 7]], counts)
        self.assertFalse(keep[0])
        self.assertTrue(inside[0])
        self.assertEqual(active[0], 2)

    def test_diagonal_pair_is_enough_without_a_count_threshold(self):
        counts = np.zeros((15, 15), int)
        counts[7, 7] = counts[8, 8] = 1
        self.assertTrue(native_seed_support([[7, 7]], counts)[0][0])
        # A neighbor outside the fixed block is not part of that support.
        counts[:] = 0
        counts[7, 9] = counts[7, 10] = 1
        self.assertFalse(native_seed_support([[7, 7]], counts)[0][0])

    def test_incomplete_blocks_do_not_wrap_or_clamp_and_empty_is_supported(self):
        keep, inside, active = native_seed_support([[0, 0], [14, 14]], np.ones((15, 15)))
        self.assertFalse(keep.any())
        self.assertFalse(inside.any())
        np.testing.assert_array_equal(active, [-1, -1])
        self.assertEqual(len(native_seed_support(np.empty((0, 2)), np.zeros((15, 15)))[0]), 0)
        with self.assertRaises(ValueError):
            native_seed_support([[np.nan, 1]], np.zeros((15, 15)))
        with self.assertRaises(ValueError):
            native_seed_support([[7, 7]], -np.ones((15, 15)))

    def test_interpolation_can_falsely_connect_an_isolated_native_pixel(self):
        native = np.zeros((15, 15)); native[7, 7] = 1
        rectified = np.zeros((15, 15)); rectified[7:9, 7:9] = .25
        self.assertFalse(native_seed_support([[7, 7]], native)[0][0])
        self.assertTrue(native_seed_support([[7, 7]], rectified)[0][0])


class EvimoPoseTests(unittest.TestCase):
    @staticmethod
    def record(t=(0, 0, 0), q=(1, 0, 0, 0), ts=1.):
        return {'ts': ts, 'pos': {'t': dict(zip(('x', 'y', 'z'), t)),
                                 'q': dict(zip(('w', 'x', 'y', 'z'), q))}}

    def test_wxyz_rotation_and_translation(self):
        pose = pose_matrix(self.record((1, 2, 3), (np.sqrt(.5), 0, 0, np.sqrt(.5))), 1.)
        np.testing.assert_allclose(pose @ [1, 0, 0, 1], [1, 3, 3, 1], atol=1e-14)

    def test_rejects_invalid_or_unsynchronized_pose(self):
        for record in (self.record(q=(0, 0, 0, 0)), self.record(q=(2, 0, 0, 0)),
                       self.record(t=(np.nan, 0, 0)), self.record(ts=1.000002)):
            with self.subTest(record=record), self.assertRaises(ValueError):
                pose_matrix(record, 1.)
        self.assertEqual(pose_matrix(self.record(ts=1.000001), 1.).shape, (4, 4))

    def test_static_world_object_cancels_camera_translation_and_rotation(self):
        half = np.sqrt(.5)
        a = {'ts': 1., 'cam': self.record(), '5': self.record((3, 0, 2))}
        # Camera moves +1 m in world X and turns +90 degrees around Z.
        # The same fixed object is now (0,-2,2) with rotation -90 in camera.
        b = {'ts': 1.1, 'cam': self.record((1, 0, 0), (half, 0, 0, half), 1.1),
             '5': self.record((0, -2, 2), (half, 0, 0, -half), 1.1)}
        ref = pose_pair_reference(a, b)
        np.testing.assert_allclose(np.asarray(ref['transform_previous_to_current']) @ [3, 0, 2, 1],
                                   [0, -2, 2, 1], atol=1e-14)
        self.assertAlmostEqual(ref['objects']['5']['world_origin_displacement_m'], 0)
        self.assertAlmostEqual(ref['objects']['5']['world_rotation_deg'], 0)
        self.assertGreater(ref['objects']['5']['apparent_origin_displacement_m'], 3)

    def test_rotating_object_with_stationary_origin_is_not_lost(self):
        a = {'ts': 1., 'cam': self.record(), '5': self.record((0, 0, 2))}
        b = {'ts': 1.1, 'cam': self.record(ts=1.1),
             '5': self.record((0, 0, 2), (np.sqrt(.5), 0, 0, np.sqrt(.5)), 1.1)}
        ref = pose_pair_reference(a, b)['objects']['5']
        self.assertEqual(ref['world_origin_displacement_m'], 0)
        self.assertAlmostEqual(ref['world_rotation_deg'], 90)
        np.testing.assert_allclose(np.asarray(ref['transform_previous_to_current']) @ [1, 0, 2, 1],
                                   [0, 1, 2, 1], atol=1e-14)

    def test_missing_objects_remain_missing_and_bad_interval_rejected(self):
        a = {'ts': 1., 'cam': self.record(), '5': self.record()}
        b = {'ts': 1.1, 'cam': self.record(ts=1.1), '6': self.record(ts=1.1)}
        ref = pose_pair_reference(a, b)
        self.assertEqual(ref['missing_previous'], ['6'])
        self.assertEqual(ref['missing_current'], ['5'])
        self.assertEqual(ref['objects'], {})
        with self.assertRaises(ValueError):
            pose_pair_reference(a, a)

    def test_named_distortion_matches_producer_rational_projection(self):
        metadata = dict(dist_model='radtan', fx=500., fy=510., cx=320., cy=240.,
                        k1=-.1, k2=.2, k3=.03, k4=.01, p1=-.00065, p2=-.000555)
        k, d = radtan_calibration(metadata)
        point = np.array([[.6, -.4, 2.]])
        uv, _ = cv2.projectPoints(point, np.zeros(3), np.zeros(3), k, d)
        x, y = point[0, :2]/point[0, 2]
        r2 = x*x+y*y
        radial = (1+metadata['k1']*r2+metadata['k2']*r2**2+metadata['k3']*r2**3)/(1+metadata['k4']*r2)
        expected = [500*(x*radial+2*metadata['p1']*x*y+metadata['p2']*(r2+2*x*x))+320,
                    510*(y*radial+2*metadata['p2']*x*y+metadata['p1']*(r2+2*y*y))+240]
        np.testing.assert_allclose(uv.ravel(), expected, atol=1e-12)
        recovered = cv2.undistortPointsIter(uv, k, d, None, k,
            (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 30, 1e-12))
        np.testing.assert_allclose(recovered.ravel(), [500*x+320, 510*y+240], atol=1e-9)
        with self.assertRaises(ValueError):
            radtan_calibration(dict(metadata, dist_model='equidistant'))

    def test_reference_projection_matches_opencv_and_excludes_unprojectable(self):
        k = np.array([[500., 0, 320], [0, 510, 240], [0, 0, 1]])
        points = np.array([[320., 240], [400, 210], [100, 300], [300, 200]])
        depth = np.array([2., 3., np.nan, .05])
        transform = np.eye(4)
        rvec = np.array([.01, -.02, .03])
        transform[:3, :3] = cv2.Rodrigues(rvec)[0]
        transform[:3, 3] = [.1, -.1, -.2]
        uv, valid = project(points, depth, k, transform)
        np.testing.assert_array_equal(valid, [True, True, False, False])
        xyz = np.column_stack(((points[:2, 0]-320)/500*depth[:2],
                               (points[:2, 1]-240)/510*depth[:2], depth[:2]))
        expected = cv2.projectPoints(xyz, rvec, transform[:3, 3], k, None)[0].reshape(-1, 2)
        np.testing.assert_allclose(uv[:2], expected, atol=1e-12)
        self.assertTrue(np.isnan(uv[2:]).all())

    def test_native_identity_sampling_keeps_zero_unknown_and_border_distinct(self):
        mask = np.array([[0, 5000], [6000, 22000]], dtype=np.uint16)
        points = np.array([[.1, .1], [.6, .1], [1.4, 1.4], [1.8, .1], [-1, 0]])
        np.testing.assert_array_equal(native_labels(points, mask), [0, 5, 22, -1, -1])


if __name__ == '__main__':
    unittest.main()
