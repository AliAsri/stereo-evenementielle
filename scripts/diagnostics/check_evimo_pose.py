"""One frozen EVIMO2 pair: independent poses, checked LK, oracle depth.

Separate development control, not a DSEC evaluation or mobility benchmark.
No downloads, parameter search, second pose fit or new mobility thresholds.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from pfe_events.artifacts import sha256_file, write_json
from pfe_events.clip_motion import track_seeds
from pfe_events.evimo_reference import read_metadata, pose_pair_reference, radtan_calibration, rotation_angle_deg
from pfe_events.rectified_tracking import checked_tracks, sample_masked_depth, TrackingConfig, select_features
from pfe_events.rigid_motion import estimate_rigid_motion

SEQUENCE = 'left_camera/imo/train/scene13_dyn_test_02_000000'
FRAME_IDS = (60, 66)  # Fixed before evaluating results; exactly 100 ms.
VISIBLE_SEQUENCE = 'left_camera/imo/train/scene15_dyn_test_00_000000'
ORB_CONFIG = dict(nfeatures=400, scaleFactor=1.2, nlevels=8, edgeThreshold=31,
                  firstLevel=0, WTA_K=2, scoreType=cv2.ORB_HARRIS_SCORE,
                  patchSize=31, fastThreshold=20)


def orb_checked_matches(images):
    """Frozen diagnostic frontend; images only, no GT or target selection.

    Source ORB points pass the unchanged 20 ms LK/FB rule. Their descriptors
    are matched globally to destination ORB descriptors with mutual Hamming.
    Returned FB errors belong ONLY to the short check, not the long match.
    """
    if (len(images)!=3 or any(im.ndim!=2 or im.dtype!=np.uint8 for im in images)
            or any(im.shape!=images[0].shape for im in images) or min(images[0].shape)<64):
        raise ValueError('Three matching native uint8 images at t0,t0+20ms,t1 required')
    started=time.perf_counter()
    orb=cv2.ORB_create(**ORB_CONFIG)
    source,descriptors0=orb.detectAndCompute(images[0],None)
    destination,descriptors1=orb.detectAndCompute(images[2],None)
    p=np.asarray([key.pt for key in source],np.float32).reshape(-1,2)
    q=np.asarray([key.pt for key in destination],np.float32).reshape(-1,2)
    if max(len(p),len(q))>400:
        raise ValueError('ORB exceeded the frozen feature budget')
    described=time.perf_counter()
    _,keep,fb=track_seeds(images[0],images[1],p,max_level=2)
    short_ids=np.flatnonzero(keep)
    checked=time.perf_counter()
    matches=[]
    if len(short_ids) and len(q):
        if descriptors0 is None or descriptors1 is None:
            raise ValueError('Detected ORB points missing descriptors')
        matches=sorted(cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True).match(
            np.ascontiguousarray(descriptors0[short_ids]),descriptors1),
            key=lambda m:(m.queryIdx,m.trainIdx))
    source_ids=short_ids[[m.queryIdx for m in matches]] if matches else np.empty(0,int)
    destination_ids=np.array([m.trainIdx for m in matches],int)
    finished=time.perf_counter()
    arrays=dict(source_initial=p,destination_initial=q,source_short_keep=keep,
        source_short_fb_px=fb,matched_source_ids=source_ids,matched_destination_ids=destination_ids,
        hamming_distance=np.array([m.distance for m in matches],np.float32))
    stats=dict(features=len(p),checked_tracks=len(short_ids),destination_features=len(q),
        long_matches=len(matches),status='MATCHED' if matches else 'NO_MATCHES')
    timing=dict(detection_descriptors=(described-started)*1000,short_lk=(checked-described)*1000,
                global_matching=(finished-checked)*1000,total=(finished-started)*1000)
    return p[source_ids],q[destination_ids],fb[source_ids],p[short_ids],stats,arrays,timing


def last_event_image(xy, timestamps, shape, *, end, window=.050):
    """Diagnostic linear recency image; half-open causal window, no fitted decay."""
    xy, timestamps = np.asarray(xy), np.asarray(timestamps, dtype=float)
    if (xy.shape != (len(timestamps), 2) or timestamps.ndim != 1
            or not np.issubdtype(xy.dtype, np.integer)
            or not np.isfinite(timestamps).all() or not np.isfinite(end)
            or not np.isfinite(window) or window <= 0
            or len(shape) != 2 or min(shape) <= 0):
        raise ValueError('Finite timestamps, integer Nx2 coordinates and positive geometry/window required')
    height, width = shape
    if np.any(xy < 0) or np.any(xy >= [width, height]):
        raise ValueError('Event outside native image')
    use = (timestamps >= end-window) & (timestamps < end)
    last = np.full(height*width, -np.inf)
    np.maximum.at(last, xy[use, 1]*width+xy[use, 0], timestamps[use])
    image = np.zeros(height*width, np.uint8)
    active = np.isfinite(last)
    image[active] = 1 + np.floor(254*(last[active]-(end-window))/window).astype(np.uint8)
    return image.reshape(shape)


def validate_frozen_selection(selection, *, visible=False):
    pair, target = ([211, 217], 6) if visible else ([68, 74], 24)
    if selection['frame_ids'] != pair or selection['target_object_id'] != target:
        raise ValueError('Only the preselected pair and object are supported')
    if visible:
        criteria = selection['criterion']
        expected = dict(sequence=VISIBLE_SEQUENCE, interval_s=.1, window_s=.05,
                        min_world_origin_displacement_m=.01,
                        min_mask_pixels_each_endpoint=1000, mask_margin_px=10)
        if any(criteria.get(key) != value for key, value in expected.items()):
            raise ValueError('Frozen visible-control selection criteria changed')
    return tuple(pair), target


def project(points, depth, k, transform):
    xyz = np.column_stack(((points[:, 0]-k[0, 2])/k[0, 0]*depth,
                           (points[:, 1]-k[1, 2])/k[1, 1]*depth, depth))
    moved = xyz @ transform[:3, :3].T + transform[:3, 3]
    valid = np.isfinite(moved).all(axis=1) & (moved[:, 2] > 1e-6)
    uv = np.full_like(points, np.nan, dtype=float)
    uv[valid] = (moved[valid] @ k.T)[:, :2] / moved[valid, 2, None]
    return uv, valid


def error_summary(errors):
    finite = np.asarray(errors)[np.isfinite(errors)]
    return dict(count=len(finite), median_px=float(np.median(finite)) if len(finite) else None,
                mean_px=float(finite.mean()) if len(finite) else None,
                p95_px=float(np.percentile(finite, 95)) if len(finite) else None)


def native_labels(points, mask):
    pixels = np.floor(points + .5).astype(int)
    ok = (pixels >= 0).all(axis=1) & (pixels[:, 0] < mask.shape[1]) & (pixels[:, 1] < mask.shape[0])
    labels = np.full(len(points), -1, int)
    labels[ok] = mask[pixels[ok, 1], pixels[ok, 0]].astype(int) // 1000
    return labels


def native_seed_support(points, counts):
    """Diagnostic gate: an 8-connected active pair inside the seed's 5x5 block.

    The block size is the existing corner detector's blockSize=5. Native
    counts only: bilinear rectification can turn an isolated pixel into a
    connected cluster. No count/rate threshold or iterative morphology.
    This is evidence of spatial support, not a mobility or tracking label.
    """
    points, counts = np.asarray(points, float), np.asarray(counts)
    if (points.ndim != 2 or points.shape[1:] != (2,) or not np.isfinite(points).all()
            or counts.ndim != 2 or min(counts.shape) < 5
            or not np.isfinite(counts).all() or np.any(counts < 0)):
        raise ValueError('Finite Nx2 points and nonnegative native count image required')
    height, width = counts.shape
    inside = ((points >= 1.5).all(axis=1) & (points[:, 0] < width-2.5)
              & (points[:, 1] < height-2.5))
    ids = np.flatnonzero(inside)
    pixels = np.floor(points[ids]+.5).astype(int)
    offsets = np.arange(-2, 3)
    patches = counts[pixels[:, 1, None, None]+offsets[None, :, None],
                     pixels[:, 0, None, None]+offsets[None, None, :]] > 0
    paired = (np.any(patches[:, 1:, :] & patches[:, :-1, :], axis=(1, 2))
              | np.any(patches[:, :, 1:] & patches[:, :, :-1], axis=(1, 2))
              | np.any(patches[:, 1:, 1:] & patches[:, :-1, :-1], axis=(1, 2))
              | np.any(patches[:, 1:, :-1] & patches[:, :-1, 1:], axis=(1, 2)))
    supported = np.zeros(len(points), bool)
    active_pixels = np.full(len(points), -1, int)
    supported[ids], active_pixels[ids] = paired, patches.sum(axis=(1, 2))
    return supported, inside, active_pixels


def support_retention(errors, eligible, supported):
    """Account for losses as well as retained errors; empty support stays null."""
    errors, eligible, supported = np.asarray(errors, float), np.asarray(eligible), np.asarray(supported)
    if (errors.ndim != 1 or eligible.shape != errors.shape or supported.shape != errors.shape
            or eligible.dtype != bool or supported.dtype != bool):
        raise ValueError('Matching error vector and boolean support masks required')
    eligible = eligible & np.isfinite(errors)
    groups = {}
    for name, selection in (('before', np.ones(len(errors), bool)), ('retained', supported), ('excluded', ~supported)):
        valid = selection & eligible
        groups[name] = dict(tracks=int(selection.sum()), evaluable=int(valid.sum()),
            error=error_summary(errors[valid]), reference_error_above_3px=int((valid & (errors > 3)).sum()),
            reference_error_at_most_3px=int((valid & (errors <= 3)).sum()))
    return groups


def corner_budget_audit(image, target_mask, config=TrackingConfig()):
    """Audit the unchanged global corner selector, without tracking/refitting.

    Masks describe coverage after selection; they are never supplied to GFTT.
    A target score below every selected score identifies global-budget pressure,
    not a guarantee that all target corners would survive spacing or tracking.
    """
    c = config
    features = select_features(image, c)
    points = np.empty((0, 2), np.float32) if features is None else features.reshape(-1, 2)
    score = cv2.cornerMinEigenVal(image, blockSize=5, ksize=3)
    pixels = np.floor(points+.5).astype(int)
    selected_scores = score[pixels[:, 1], pixels[:, 0]]
    threshold = float(score.max())*c.quality
    local = (score == cv2.dilate(score, None)) & (score > threshold)
    local[[0, -1], :] = False
    local[:, [0, -1]] = False
    y, x = np.nonzero(target_mask)
    maximum = float(score[target_mask].max()) if len(x) else None
    minimum = float(selected_scores.min()) if len(points) else None
    return dict(selection=c.selection, initial_features=len(points), target_initial_features=int(target_mask[pixels[:, 1], pixels[:, 0]].sum()),
        target_pixels=len(x), target_bbox_xyxy=[int(x.min()), int(y.min()), int(x.max()), int(y.max())] if len(x) else None,
        global_score_max=float(score.max()), quality_threshold=threshold,
        target_score_max=maximum, minimum_selected_score=minimum,
        target_pixels_above_quality=int((target_mask & (score > threshold)).sum()),
        target_local_maxima_above_quality=int((target_mask & local).sum()),
        budget_exhausted=len(points) == c.max_features,
        target_max_below_all_selected=maximum < minimum if maximum is not None and minimum is not None else None,
        scope='Identical unmasked corner selection only; no extra LK or pose fit; local maxima do not include minDistance selection')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='Fresh output directory')
    parser.add_argument('--inspect-tracks', type=Path,
                        help='Inspect a saved fixed pair; no tracking or pose fitting rerun')
    parser.add_argument('--reference-selection', type=Path,
                        help='Pre-recorded pose-only positive pair selection; frozen gate evaluation')
    parser.add_argument('--spatial-seeds', action='store_true',
                        help='Single experimental 8x6 redistribution; default remains global')
    parser.add_argument('--inspect-target-corners', action='store_true',
                        help='Diagnostic only: follow the three previously identified target corners; no pose fit')
    parser.add_argument('--chain-target-corners', action='store_true',
                        help='Same diagnostic seeds, five causal 20 ms steps; never revive a rejected track')
    parser.add_argument('--visible-control', action='store_true',
                        help='Frozen new-sequence 211->217/object 6 control; global selection only')
    parser.add_argument('--coarse-tracking', action='store_true',
                        help='Single explicit maxLevel=3 trial for long LK on the visible control')
    parser.add_argument('--time-surface', action='store_true',
                        help='Single diagnostic linear last-event image on the frozen visible control')
    parser.add_argument('--orb-correspondences', action='store_true',
                        help='Authorized single ORB400/Hamming control on frozen 211->217; no DSEC change')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh output directory')
    if args.coarse_tracking and not args.visible_control:
        raise ValueError('Coarse tracking is restricted to the frozen visible control')
    if args.time_surface and (not args.visible_control or args.coarse_tracking):
        raise ValueError('Time surface requires the frozen visible control and default LK')
    if args.orb_correspondences and (not args.visible_control or args.time_surface or args.coarse_tracking):
        raise ValueError('ORB requires only the frozen visible control and count images')
    orb_protocol=None
    orb_protocol_path=ROOT/'outputs/motion/M14_next_sample_20261017/orb_protocol_20261019.json'
    if args.visible_control:
        if args.reference_selection or args.inspect_tracks or args.spatial_seeds or args.inspect_target_corners or args.chain_target_corners:
            raise ValueError('Visible control uses its frozen manifest and global selection only')
        args.reference_selection = ROOT/'outputs/motion/M14_next_sample_20261017/selection.json'
    if args.inspect_target_corners and args.chain_target_corners:
        raise ValueError('Choose direct or chained target inspection')
    if (args.inspect_target_corners or args.chain_target_corners) and (args.reference_selection is None or args.spatial_seeds or args.inspect_tracks):
        raise ValueError('Target-corner inspection requires only the frozen positive reference selection')
    if args.inspect_tracks is not None and args.reference_selection is not None:
        raise ValueError('Choose saved-track inspection or a preselected positive control')
    if args.inspect_tracks is not None and args.spatial_seeds:
        raise ValueError('Saved-track inspection does not reselect seeds')
    if args.inspect_tracks is not None:
        inspect_tracks(args.inspect_tracks, args.output)
        return
    if args.orb_correspondences:
        orb_protocol=json.loads(orb_protocol_path.read_text())
        if (orb_protocol['orb_config']!=ORB_CONFIG or orb_protocol['frame_ids']!=[211,217]
                or orb_protocol['target_object_id']!=6):
            raise ValueError('Frozen ORB protocol changed')
        for name,expected in orb_protocol['baseline_sha256'].items():
            if sha256_file(ROOT/name)!=expected:
                raise ValueError('Frozen baseline changed: '+name)
        cv2.ocl.setUseOpenCL(False)  # This authorized control is explicitly CPU.
    sequence = VISIBLE_SEQUENCE if args.visible_control else SEQUENCE
    acquisition_path = ROOT / ('outputs/motion/M14_next_sample_20261017/acquired/acquisition.json'
                               if args.visible_control else 'outputs/motion/M14/acquisition.json')
    acquisition = json.loads(acquisition_path.read_text(encoding='utf-8'))
    if acquisition['sequence'] != sequence or acquisition['official_split'] != 'train':
        raise ValueError('Frozen sequence or partition mismatch')
    if len(acquisition['files']) != 6:
        raise ValueError('Expected six acquired inputs')
    for item in acquisition['files']:
        if ((ROOT/item['path']).stat().st_size!=item['bytes']
                or sha256_file(ROOT / item['path']) != item['sha256']):
            raise ValueError('Input changed since acquisition: ' + item['name'])
    data = ROOT / 'data/raw/evimo2v2' / sequence
    meta = read_metadata(data / 'dataset_info.npz')
    frames = {int(f['id']): f for f in meta['frames']}
    if len(frames) != len(meta['frames']):
        raise ValueError('Duplicate frame IDs')
    selection = None
    target_id = None
    frame_ids = FRAME_IDS
    if args.reference_selection is not None:
        selection = json.loads(args.reference_selection.read_text(encoding='utf-8'))
        if selection['metadata_sha256'] != sha256_file(data/'dataset_info.npz'):
            raise ValueError('Selection metadata hash mismatch')
        frame_ids, target_id = validate_frozen_selection(selection, visible=args.visible_control)
        if args.visible_control:
            protocol_path = args.reference_selection.parent/'protocol.json'
            if sha256_file(protocol_path) != selection['protocol_sha256']:
                raise ValueError('Frozen selection protocol hash mismatch')
    a, b = [frames[i] for i in frame_ids]
    if abs((b['ts'] - a['ts']) - .100) > 1e-10:
        raise ValueError('Frozen pair must span exactly 100 ms')
    ref = pose_pair_reference(a, b)
    if selection is not None:
        if ([a['ts'], b['ts']] != selection['times_s']
                or ref['objects'][str(target_id)]['world_origin_displacement_m'] < .010):
            raise ValueError('Selection times or reference motion criterion mismatch')
    k, d = radtan_calibration(meta['meta'])
    with np.load(data / 'dataset_info.npz', allow_pickle=False) as info:
        if not np.allclose(k, info['K'], atol=1e-6, rtol=0):
            raise ValueError('K differs between metadata and numeric array')
        legacy_d = info['D'].tolist()
    height, width = int(meta['meta']['res_y']), int(meta['meta']['res_x'])
    event_t = np.load(data / 'dataset_events_t.npy', mmap_mode='r', allow_pickle=False)
    event_xy = np.load(data / 'dataset_events_xy.npy', mmap_mode='r', allow_pickle=False)
    event_counts = []
    source_counts = None

    def event_image(end):
        nonlocal source_counts
        if end-.050 < event_t[0] or end > event_t[-1]:
            raise ValueError('Incomplete causal event window')
        lo, hi = np.searchsorted(event_t, [end-.050, end], side='left')
        xy = event_xy[lo:hi].astype(np.int64)
        counts = np.bincount(xy[:, 1]*width+xy[:, 0], minlength=height*width).reshape(height, width)
        event_counts.append(int(hi-lo))
        if source_counts is None:
            source_counts = counts
        if args.time_surface:
            return last_event_image(xy, event_t[lo:hi], (height, width), end=end)
        # Fixed M14 display scale, not fitted on this pair or transferred from DSEC.
        return (255*np.clip(np.log1p(counts)/np.log(21), 0, 1)).astype(np.uint8)

    start = time.perf_counter()
    times = ([a['ts']+i*.020 for i in range(5)]+[b['ts']] if args.chain_target_corners
             else [a['ts'], a['ts']+.020, b['ts']])
    images = [event_image(end) for end in times]
    represented = time.perf_counter()
    if args.inspect_target_corners or args.chain_target_corners:
        inspect_target_corners(args.output, images, source_counts, data, k, d, ref,
                               selection, acquisition, chained=args.chain_target_corners,
                               representation_ms=(represented-start)*1000)
        return
    tracking_config = TrackingConfig(selection='spatial_8x6' if args.spatial_seeds else 'global')
    orb_arrays,orb_timing=None,None
    if args.orb_correspondences:
        p,q,fb,seed_points,seed_stats,orb_arrays,orb_timing=orb_checked_matches(images)
        long_tracking_ms=orb_timing['global_matching']
    else:
        p, _, seed_stats = checked_tracks(images[0], images[1], tracking_config)
        seed_points = p.copy()
        long_tracking_started = time.perf_counter()
        q, keep, fb = track_seeds(images[0], images[2], p, max_level=3 if args.coarse_tracking else 2)
        long_tracking_ms = (time.perf_counter()-long_tracking_started)*1000
        p, q, fb = p[keep], q[keep], fb[keep]
    long_count=len(p)
    tracked = time.perf_counter()
    # Maps are native/distorted. Sample depth BEFORE undistorting feature coordinates.
    with np.load(data / 'dataset_depth.npz', allow_pickle=False) as archive:
        depth = archive[f'depth_{frame_ids[0]:010d}'].astype(float) / 1000
    with np.load(data / 'dataset_mask.npz', allow_pickle=False) as archive:
        masks = [archive[f'mask_{i:010d}'] for i in frame_ids]
    if depth.shape != (height, width) or any(m.shape != depth.shape for m in masks):
        raise ValueError('Unexpected map shape')
    if selection is not None and any(not np.any(m == target_id*1000) for m in masks):
        raise ValueError('Selected target is not visible at both endpoints')
    z, depth_stats = sample_masked_depth(p, depth, np.isfinite(depth) & (depth > 0))

    def undistort(points):
        if not len(points):
            return np.empty((0, 2), float)
        return cv2.undistortPointsIter(points.astype(float).reshape(-1, 1, 2), k, d,
            None, k, (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 30, 1e-12)).reshape(-1, 2)

    up, uq = undistort(p), undistort(q)
    inside = (np.isfinite(up).all(axis=1) & np.isfinite(uq).all(axis=1)
              & (up >= 0).all(axis=1) & (uq >= 0).all(axis=1)
              & (up < [width, height]).all(axis=1) & (uq < [width, height]).all(axis=1))
    excluded = int((~inside).sum())
    if orb_arrays is not None:
        orb_arrays['matched_pinhole_inside']=inside.copy()
    p, q, up, uq, z, fb = [v[inside] for v in (p, q, up, uq, z, fb)]
    ready = time.perf_counter()
    model = estimate_rigid_motion(up, uq, z, k, previous_us=round(a['ts']*1e6),
        current_us=round(b['ts']*1e6), depth_us=round(a['ts']*1e6),
        depth_source='dataset_reference', frame_size=(width, height))
    fitted = time.perf_counter()
    # Camera/object reference poses and identity masks are NEVER passed to the fitter.
    camera_uv, camera_valid = project(up, z, k, np.asarray(ref['transform_previous_to_current']))
    camera_error = np.linalg.norm(camera_uv-uq, axis=1)
    labels0, labels1 = [native_labels(v, m) for v, m in zip((p, q), masks)]
    object_uv = np.full_like(up, np.nan)
    object_valid = np.zeros(len(up), bool)
    for key, item in ref['objects'].items():
        use = labels0 == int(key)
        pred, valid = project(up[use], z[use], k, np.asarray(item['transform_previous_to_current']))
        object_uv[use], object_valid[use] = pred, valid
    full_error = np.linalg.norm(object_uv-uq, axis=1)
    same_id = (labels0 > 0) & (labels0 == labels1)
    per_object = []
    for key, item in ref['objects'].items():
        use = (labels0 == int(key)) & same_id
        per_object.append(dict(object_id=int(key), **item, previous_tracks=int((labels0 == int(key)).sum()),
            same_identity_tracks=int(use.sum()), usable_reference_tracks=int((use & object_valid).sum()),
            camera_only=error_summary(camera_error[use]), camera_and_object=error_summary(full_error[use])))
    pose_error = None
    if model['valid']:
        estimated = np.asarray(model['transform_previous_to_current'])
        truth = np.asarray(ref['transform_previous_to_current'])
        pose_error = dict(rotation_deg=rotation_angle_deg(estimated[:3, :3] @ truth[:3, :3].T),
                          translation_vector_difference_m=float(np.linalg.norm(estimated[:3, 3]-truth[:3, 3])))
    report = dict(status='BOUNDED_ORACLE_REFERENCE_CONTROL', sequence=sequence, split='train',
        frame_ids=list(frame_ids), times_s=[a['ts'], b['ts']],
        selection=selection if selection is not None else 'Fixed IDs 60 and 66 before outcomes',
        acquisition_sha256=sha256_file(acquisition_path), verified_inputs=acquisition['files'],
        protocol=dict(window_ms=50, short_seed_interval_ms=20, track_interval_ms=100,
            seed_selection='ORB_GLOBAL' if args.orb_correspondences else tracking_config.selection,
            max_features=tracking_config.max_features,
            long_lk_max_level=None if args.orb_correspondences else (3 if args.coarse_tracking else 2),
            image_scale=('inactive=0; active=1+floor(254*(latest_timestamp-start)/.050); native [start,end)'
                         if args.time_surface else
                         'uint8(255*clip(log1p(total counts)/log(21),0,1)); native coordinates'),
            geometry='Native axial GT depth in metres; undistorted native endpoints; pinhole PnP',
            K=k.tolist(), D_legacy=legacy_d, D_opencv_from_named_metadata=d.tolist(),
            pose_timestamp_tolerance_us=1.1, depth_source='dataset_reference', fits=1,
            mask_usage='Evaluation strata only; zero/unknown IDs never assumed static'),
        reference=ref, model=model, estimated_pose_error=pose_error,
        tracks=dict(seed=seed_stats, passed_100ms=long_count, outside_undistorted=excluded,
            retained=len(p), usable_depth=int(np.isfinite(z).sum()), depth_sampling=depth_stats,
            unknown_or_zero_identity=int((labels0 <= 0).sum()),
            changed_or_unknown_endpoint_identity=int(((labels0 > 0) & ~same_id).sum()),
            same_identity=int(same_id.sum()), same_identity_and_depth=int((same_id & object_valid).sum())),
        reference_errors_same_identity=dict(camera_only=error_summary(camera_error[same_id]),
            camera_and_object=error_summary(full_error[same_id])), per_object=per_object,
        event_counts=event_counts,
        timing_ms=dict(read_representation_tracking=(tracked-start)*1000,
            read_representation=(represented-start)*1000,
            long_tracking=long_tracking_ms,
            map_load_sampling_undistortion=(ready-tracked)*1000, rigid_fit=(fitted-ready)*1000,
            note='One cold diagnostic call; excludes initial hashes/metadata and reference evaluation, not a DSEC speed benchmark'),
        limits=['One train pair, one camera, close-range objects; not a DSEC validation',
            'GT depth is oracle; no predicted stereo, YOLO or end-to-end cadence evaluation',
            'Causal 50 ms event images are not instantaneous GT samples',
            'Same endpoint identity does not prove same physical surface point or no occlusion',
            'Map rasterization, calibration and tracking uncertainty remain; no mobility binary labels',
            'No precision/recall, false-alert rate or motion-onset delay measured'],
        upstream=dict(evimo_revision='8897c6d9aa18384f9746b89b565d09cc7d8a059f',
            pydvs_revision='fa12a1434a02133321a1b03929a5383f4ec23009',
            format_url='https://better-flow.github.io/evimo/docs/ground-truth-format.html',
            note='Inspected source revisions; original archive build revision is unknown'),
        attribution='EVIMO / EVIMO2, Better Flow; data and derived preview CC BY-SA 4.0')
    args.output.mkdir(parents=True)
    if args.orb_correspondences:
        report['protocol'].update(frontend='ORB400, short LK2, mutual Hamming; no long LK',
            orb_config=ORB_CONFIG,fb_px_meaning='Short 20ms LK check only, not long-match validation',
            matching_order='Source detector order after short rejection; no sorting by GT, score or fit')
        report['protocol']['orb_protocol_sha256']=sha256_file(orb_protocol_path)
        report['timing_ms']['orb_frontend']=orb_timing
        report['cpu_execution']=dict(opencv_threads=cv2.getNumThreads(),opencv_version=cv2.__version__,
                                    opencl_enabled=cv2.ocl.useOpenCL())
        (args.output/'protocol.json').write_bytes(orb_protocol_path.read_bytes())
        np.savez_compressed(args.output/'orb_frontend.npz',**orb_arrays)
        np.savez_compressed(args.output/'images.npz',images=np.asarray(images),times_s=times)
    if args.time_surface:
        protocol = ROOT/'outputs/motion/M14_next_sample_20261017/time_surface_protocol.json'
        report['representation_protocol_sha256'] = sha256_file(protocol)
        (args.output/'protocol.json').write_bytes(protocol.read_bytes())
        np.savez_compressed(args.output/'images.npz', images=np.asarray(images), times_s=times)
    if selection is not None:
        started = time.perf_counter()
        supported, complete, active = native_seed_support(p, source_counts)
        gate_ms = (time.perf_counter()-started)*1000
        seed_supported, _, _ = native_seed_support(seed_points, source_counts)
        seed_labels = native_labels(seed_points, masks[0])
        eligible = same_id & object_valid
        target = (labels0 == selection['target_object_id'])
        shift = np.linalg.norm(camera_uv-object_uv, axis=1)
        report['positive_support_control'] = dict(
            status='NO_TARGET_TRACKS_NOT_EVALUABLE' if not np.any(target & eligible) else 'TARGET_SUPPORT_MEASURED',
            target_object_id=selection['target_object_id'],
            target_short_checked_seeds=int((seed_labels == target_id).sum()),
            target_short_seeds_with_spatial_support=int(((seed_labels == target_id) & seed_supported).sum()),
            target_long_tracks=int(target.sum()),
            target=support_retention(full_error[target], eligible[target], supported[target]),
            all_objects=support_retention(full_error, eligible, supported),
            target_reference_motion_shift=error_summary(shift[target & eligible]),
            target_comparable_reference_shift_above_3px=int((target & eligible & (shift > 3)).sum()),
            outside_complete_blocks=int((~complete).sum()), gate_ms=gate_ms,
            application='Post-hoc support gate on saved correspondences and unchanged fitted pose; no refit',
            timing_scope='One cold gate call, excluding count accumulation, IO and seed-stage audit',
            limits='One GT-selected train pair, not recall/precision or independent test-set validation')
        if args.orb_correspondences:
            report['positive_support_control']['orb_feature_coverage']=dict(
                source_features=len(orb_arrays['source_initial']),
                target_initial_features=int((native_labels(orb_arrays['source_initial'],masks[0])==target_id).sum()),
                destination_features=len(orb_arrays['destination_initial']),
                target_destination_features=int((native_labels(orb_arrays['destination_initial'],masks[1])==target_id).sum()),
                mask_usage='Coverage evaluated after matching; never passed to ORB or matcher')
        else:
            report['positive_support_control']['corner_budget_audit'] = corner_budget_audit(images[0], masks[0] == target_id*1000, tracking_config)
        report['positive_support_control']['target_events_source'] = int(source_counts[masks[0] == target_id*1000].sum())
        np.savez_compressed(args.output/'support.npz', supported=supported, complete_block=complete,
            active_pixels_5x5=active, evaluable=eligible, target=target, reference_error_px=full_error,
            reference_motion_shift_px=shift, seed_points=seed_points,
            seed_labels=seed_labels, seed_supported=seed_supported)
        (args.output/'selection.json').write_bytes(args.reference_selection.read_bytes())
        report['selection_sha256'] = sha256_file(args.reference_selection)
    np.savez_compressed(args.output/'pair.npz', previous_native=p, current_native=q,
        previous_pinhole=up, current_pinhole=uq, depth_m=z, fb_px=fb,
        reference_camera_uv=camera_uv, reference_object_uv=object_uv,
        camera_valid=camera_valid, object_valid=object_valid, labels_previous=labels0, labels_current=labels1)
    report['sources'] = []
    for name in ('scripts/diagnostics/check_evimo_pose.py', 'src/pfe_events/evimo_reference.py',
                 'src/pfe_events/rectified_tracking.py', 'src/pfe_events/clip_motion.py',
                 'src/pfe_events/rigid_motion.py', 'tests/test_evimo_reference.py'):
        target = args.output/'source_snapshot'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
        report['sources'].append(dict(path=name, sha256=sha256_file(ROOT/name)))
    report['pair_sha256'] = sha256_file(args.output/'pair.npz')
    write_json(args.output/'summary.json', report)
    preview(images, p, q, report, args.output/'preview.png')
    print(json.dumps({key: report[key] for key in ('status', 'estimated_pose_error', 'reference_errors_same_identity')}, indent=2))


def chain_tracks(images, points):
    """Diagnostic composition of unchanged LK gates; rejected IDs stay rejected."""
    points = np.asarray(points, np.float32)
    if len(images) < 2:
        raise ValueError('At least two chronological images required')
    history = np.full((len(images), len(points), 2), np.nan, np.float32)
    history[0] = points
    alive = np.ones(len(points), bool)
    accepted = np.zeros((len(images)-1, len(points)), bool)
    fb = np.full(accepted.shape, np.nan)
    for step, (previous, current) in enumerate(zip(images[:-1], images[1:])):
        ids = np.flatnonzero(alive)
        q, keep, error = track_seeds(previous, current, history[step, ids])
        fb[step, ids] = error
        alive[ids] = keep
        accepted[step] = alive
        history[step+1, ids[keep]] = q[keep]
    return history, accepted, fb


def inspect_target_corners(output, images, counts, data, k, d, ref, selection, acquisition,
                           *, chained=False, representation_ms=None):
    """Frozen coordinates from the prior audit, not a detector or selection rule.

    Track all three once at 20 and 100 ms with the existing LK settings. Depth,
    masks and poses are used afterward solely to assess these diagnostic seeds.
    No pose is fitted and no parameter is tuned after inspecting outcomes.
    """
    p = np.array([[346, 7], [342, 1], [361, 4]], np.float32)
    tracking_started = time.perf_counter()
    chain_report = None
    if chained:
        if len(images) != 6:
            raise ValueError('Frozen chain requires six images at 20 ms steps')
        history, step_keep, step_fb = chain_tracks(images, p)
        short, short_keep, short_fb = history[1], step_keep[0], step_fb[0]
        q, long_keep, long_fb = history[-1], step_keep[-1], step_fb[-1]
        chain_report = dict(step_end_ms=[20, 40, 60, 80, 100],
                            surviving_tracks=step_keep.sum(axis=1).tolist(),
                            last_fb_is_only_last_step=True,
                            final_reference_error_checks_accumulated_drift=True)
    else:
        short, short_keep, short_fb = track_seeds(images[0], images[1], p)
        q, long_keep, long_fb = track_seeds(images[0], images[2], p)
    tracking_ms = (time.perf_counter()-tracking_started)*1000
    with np.load(data/'dataset_depth.npz', allow_pickle=False) as archive:
        depth = archive['depth_0000000068'].astype(float)/1000
    with np.load(data/'dataset_mask.npz', allow_pickle=False) as archive:
        masks = [archive[f'mask_{i:010d}'] for i in (68, 74)]
    labels0 = native_labels(p, masks[0])
    if not np.all(labels0 == 24):
        raise ValueError('Frozen corners no longer lie on target 24')
    labels1 = np.full(3, -1, int)
    finite_q = np.isfinite(q).all(axis=1)
    labels1[finite_q] = native_labels(q[finite_q], masks[1])
    z, _ = sample_masked_depth(p, depth, np.isfinite(depth) & (depth > 0))
    def undistort(points):
        return cv2.undistortPointsIter(points.astype(float).reshape(-1, 1, 2), k, d,
            None, k, (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 30, 1e-12)).reshape(-1, 2)
    up = undistort(p)
    uq = np.full((3, 2), np.nan)
    uq[finite_q] = undistort(q[finite_q])
    transform = np.asarray(ref['objects']['24']['transform_previous_to_current'])
    expected, valid = project(up, z, k, transform)
    xyz = np.column_stack(((up[:, 0]-k[0, 2])/k[0, 0]*z,
                           (up[:, 1]-k[1, 2])/k[1, 1]*z, z))
    expected_native = np.full((3, 2), np.nan)
    ids = np.flatnonzero(valid)
    if len(ids):
        rotation = cv2.Rodrigues(transform[:3, :3])[0]
        check = cv2.projectPoints(xyz[ids], rotation, transform[:3, 3], k, None)[0].reshape(-1, 2)
        np.testing.assert_allclose(check, expected[ids], rtol=0, atol=1e-8)
        expected_native[ids] = cv2.projectPoints(xyz[ids], rotation, transform[:3, 3], k, d)[0].reshape(-1, 2)
    errors = np.linalg.norm(expected-uq, axis=1)
    support, complete, active = native_seed_support(p, counts)
    height, width = images[0].shape
    pinhole_inside = (np.isfinite(up).all(axis=1) & np.isfinite(uq).all(axis=1)
        & (up >= 0).all(axis=1) & (uq >= 0).all(axis=1)
        & (up < [width, height]).all(axis=1) & (uq < [width, height]).all(axis=1))
    accepted = short_keep & long_keep & pinhole_inside
    scalar = lambda v: float(v) if np.isfinite(v) else None
    coords = lambda v: [scalar(x) for x in v]
    rows = [dict(source_native=p[i].tolist(), short_native=coords(short[i]), current_native=coords(q[i]),
        short_pass=bool(short_keep[i]), long_pass=bool(long_keep[i]),
        short_fb_px=scalar(short_fb[i]), long_fb_px=scalar(long_fb[i]),
        undistorted_inside=bool(pinhole_inside[i]), accepted_by_existing_tracking=bool(accepted[i]),
        source_label=int(labels0[i]), current_label=int(labels1[i]),
        oracle_depth_m=scalar(z[i]), reference_native=coords(expected_native[i]),
        reference_error_px=scalar(errors[i]), reference_projectable=bool(valid[i]),
        complete_native_5x5=bool(complete[i]), native_active_pixels_5x5=int(active[i]),
        native_gate_supported=bool(support[i])) for i in range(3)]
    evaluation_ms = (time.perf_counter()-tracking_started)*1000-tracking_ms
    output.mkdir(parents=True)
    write_json(output/'summary.json', dict(
        status='DIAGNOSTIC_TARGET_CORNERS_ONLY', frame_ids=[68, 74], target_object_id=24,
        selection=selection, verified_inputs=acquisition['files'],
        tracking_mode='five_20ms_steps' if chained else 'direct_100ms', chain=chain_report,
        timing_ms=dict(read_representations=representation_ms, tracking=tracking_ms,
                       oracle_evaluation=evaluation_ms),
        timing_scope='One cold diagnostic call on three imposed seeds; excludes acquisition hashes, setup, rendering/export; no DSEC cadence claim',
        protocol=dict(seeds='Three coordinates fixed in the 16 October audit; target-informed diagnostic only',
            short_ms=20, long_ms=100, window_ms=50, pose_fit=False,
            gate='Existing track_seeds forward/backward <=1px per step and native bounds; existing final undistorted bounds',
            reference_error='Euclidean undistorted pixel error vs object+camera pose using source oracle depth',
            rejected_tracks='Reference errors shown for diagnosis; rejected tracks never counted as accepted'),
        corners=rows, accepted_tracks=int(accepted.sum()),
        accepted_same_target=int((accepted & (labels1 == 24)).sum()),
        accepted_same_target_reference_at_most_3px=int((accepted & (labels1 == 24) & valid & (errors <= 3)).sum()),
        projection_verified_with_opencv=True,
        limitations=['Only three target-informed diagnostic seeds; no detector improvement or recall claim',
            'Boundary visibility, depth rasterization and calibration uncertainty remain',
            'No new selection, fit, threshold, dataset, or change to DSEC'],
        source_sha256={f: sha256_file(ROOT/f) for f in ('scripts/diagnostics/check_evimo_pose.py',
            'src/pfe_events/clip_motion.py', 'src/pfe_events/evimo_reference.py',
            'src/pfe_events/rectified_tracking.py')}))
    np.savez_compressed(output/'corners.npz', source=p, short=short, current=q,
        expected_native=expected_native, expected_undistorted=expected, depth_m=z,
        source_image=images[0], short_image=images[1], current_image=images[-1])
    if chained:
        np.savez_compressed(output/'chain.npz', history=history, accepted=step_keep, fb_px=step_fb)
    images = [images[0], images[1], images[-1]]
    canvas = Image.new('RGB', (1200, 450), '#102030')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    colors = ('#ff9933', '#44ddff', '#ff66cc')
    for panel, (im, points, title) in enumerate(zip(images, (p, short, q), ('Source', '+20 ms', '+100 ms'))):
        crop = Image.fromarray(im).convert('RGB').crop((300, 0, 400, 60)).resize((400, 240), Image.Resampling.NEAREST)
        canvas.paste(crop, (panel*400, 35))
        draw.text((panel*400+8, 8), title, fill='white', font=font)
        for i, point in enumerate(points):
            if np.isfinite(point).all() and 300 <= point[0] < 400 and 0 <= point[1] < 60:
                x, y = panel*400+(point[0]-300)*4, 35+point[1]*4
                draw.ellipse((x-5, y-5, x+5, y+5), outline=colors[i], width=2)
                draw.text((x+7, y), str(i+1), fill=colors[i], font=font)
        if panel == 2:
            for point in expected_native:
                if np.isfinite(point).all() and 300 <= point[0] < 400 and 0 <= point[1] < 60:
                    x, y = panel*400+(point[0]-300)*4, 35+point[1]*4
                    draw.line((x-5, y, x+5, y), fill='white', width=2)
                    draw.line((x, y-5, x, y+5), fill='white', width=2)
    draw.text((10, 290), 'Diagnostic cible uniquement | cercles : LK, croix blanches : projection de reference', fill='white', font=font)
    for i, row in enumerate(rows):
        error = row['reference_error_px']
        text = f"#{i+1} court={row['short_pass']} long={row['long_pass']} accepte={row['accepted_by_existing_tracking']} | erreur GT={error:.2f} px" if error is not None else f'#{i+1} erreur finale non evaluable (suivi ou reference indisponible)'
        draw.text((10, 322+i*30), text, fill=colors[i], font=font)
    canvas.save(output/'preview.png')


def inspect_tracks(source, output):
    """Inspect saved failures and one untuned support gate at the frozen pose."""
    summary = json.loads((source/'summary.json').read_text(encoding='utf-8'))
    if summary['sequence'] != SEQUENCE or summary['frame_ids'] != list(FRAME_IDS):
        raise ValueError('Only the frozen EVIMO pair is supported')
    if sha256_file(source/'pair.npz') != summary['pair_sha256']:
        raise ValueError('Saved correspondences changed')
    for item in summary['verified_inputs']:
        if sha256_file(ROOT/item['path']) != item['sha256']:
            raise ValueError('Acquired input changed')
    with np.load(source/'pair.npz', allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    data = ROOT/'data/raw/evimo2v2'/SEQUENCE
    times = np.load(data/'dataset_events_t.npy', mmap_mode='r', allow_pickle=False)
    xy = np.load(data/'dataset_events_xy.npy', mmap_mode='r', allow_pickle=False)
    polarities = np.load(data/'dataset_events_p.npy', mmap_mode='r', allow_pickle=False)
    counts, event_slices = [], []
    for end in summary['times_s']:
        lo, hi = np.searchsorted(times, [end-.05, end], side='left')
        coords = xy[lo:hi].astype(int)
        counts.append(np.bincount(coords[:, 1]*640+coords[:, 0], minlength=640*480).reshape(480, 640))
        event_slices.append((times[lo:hi], coords, polarities[lo:hi]))
    p, q = arrays['previous_native'], arrays['current_native']
    # First source image only: support is causal at seed time, before t1 or GT.
    started = time.perf_counter()
    supported, inside, active = native_seed_support(p, counts[0])
    gate_ms = (time.perf_counter()-started)*1000
    errors = np.linalg.norm(arrays['reference_object_uv']-arrays['current_pinhole'], axis=1)
    eligible = ((arrays['labels_previous'] > 0)
                & (arrays['labels_previous'] == arrays['labels_current']) & np.isfinite(errors))
    candidate_ids = np.flatnonzero(np.array(summary['model']['point_status']) == 'RESIDUAL_CANDIDATE')
    details = []
    for index in candidate_ids:
        x, y = np.floor(p[index]+.5).astype(int)
        left, top, right, bottom = max(0, x-10), max(0, y-10), min(640, x+11), min(480, y+11)
        patch = counts[0][top:bottom, left:right]
        yy, xx = np.unravel_index(patch.argmax(), patch.shape)
        peak = [int(xx+left), int(yy+top)]
        windows = []
        for end, (ts, coords, pol) in zip(summary['times_s'], event_slices):
            exact = (coords[:, 0] == peak[0]) & (coords[:, 1] == peak[1])
            neighbors = ((abs(coords[:, 0]-peak[0]) <= 1)
                         & (abs(coords[:, 1]-peak[1]) <= 1) & ~exact)
            windows.append(dict(events=int(exact.sum()), eight_neighbor_events=int(neighbors.sum()),
                positive_events=int(pol[exact].sum()),
                counts_per_10ms=np.histogram(ts[exact], np.linspace(end-.05, end, 6))[0].tolist()))
        details.append(dict(track_index=int(index), peak_native_xy=peak,
            peak_selection='Maximum count in original 21x21 LK footprint, previous window only',
            seed_active_pixels_5x5=int(active[index]), gate_supported=bool(supported[index]),
            native_border_distance_px=float(min(x, y, 639-x, 479-y)),
            windows=windows, original_fb_px=float(arrays['fb_px'][index]),
            original_model_residual_px=summary['model']['residual_px'][index],
            full_reference_residual_px=float(errors[index])))
    groups = {}
    for name, selection in (('before', np.ones(len(p), bool)), ('retained', supported), ('excluded', ~supported)):
        subset = selection & eligible
        groups[name] = dict(tracks=int(selection.sum()), evaluable=int(subset.sum()),
            error=error_summary(errors[subset]), reference_error_above_3px=int((subset & (errors > 3)).sum()),
            reference_error_at_most_3px=int((subset & (errors <= 3)).sum()))
    report = dict(status='NATIVE_SUPPORT_CAUSE_IDENTIFIED_NOT_PROMOTED',
        source_summary_sha256=sha256_file(source/'summary.json'), source_pair_sha256=sha256_file(source/'pair.npz'),
        protocol=dict(frame_ids=list(FRAME_IDS), fit_rerun=False, tracking_rerun=False,
            gate='At least one 8-connected active pixel pair inside source seed 5x5 block',
            block_size_reason='Existing goodFeaturesToTrack blockSize=5; no tuning',
            uses_only='Native event counts in the causal 50ms source window',
            estimated_pose='Frozen original estimate; filtering does not evaluate a new pose'),
        groups=groups, candidates=details, outside_complete_5x5=int((~inside).sum()),
        gate_timing_ms=gate_ms, timing_scope='One cold call: validation and support at 274 points; excludes IO/count accumulation',
        decision='Do not activate on DSEC: no positive independent-motion control and native support must precede rectification',
        limits=['Spatially isolated recurring activity is observed; a hardware hot-pixel diagnosis is not established',
                'Removing candidates also removes correspondences compatible with reference; not a precision/recall score',
                'A native isolated pixel may spread to up to four connected rectified pixels',
                'Single previously inspected train pair; exploratory rule needs independent positive-motion validation'],
        attribution='EVIMO / EVIMO2, Better Flow; derived preview CC BY-SA 4.0')
    output.mkdir(parents=True)
    np.savez_compressed(output/'support.npz', supported=supported, complete_block=inside,
                        active_pixels_5x5=active, reference_error_px=errors, evaluable=eligible)
    for name in ('scripts/diagnostics/check_evimo_pose.py', 'tests/test_evimo_reference.py'):
        target = output/'source_snapshot'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    report['source_sha256'] = sha256_file(Path(__file__))
    write_json(output/'summary.json', report)
    support_preview(counts, arrays, summary, report, output/'patches.png')
    print(json.dumps(dict(groups=groups, candidates=details, gate_ms=gate_ms), indent=2))


def support_preview(counts, arrays, summary, report, path):
    details = report['candidates']
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
    small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
    k, d = np.asarray(summary['protocol']['K']), np.asarray(summary['protocol']['D_opencv_from_named_metadata'])
    ids = [row['track_index'] for row in details]
    uv = arrays['reference_object_uv'][ids]
    rays = np.column_stack(((uv[:, 0]-k[0, 2])/k[0, 0], (uv[:, 1]-k[1, 2])/k[1, 1], np.ones(len(ids))))
    gt = cv2.projectPoints(rays, np.zeros(3), np.zeros(3), k, d)[0].reshape(-1, 2)
    canvas = Image.new('RGB', (1280, 880), '#102030')
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 10), 'EVIMO2 | Trois correspondances suspectes | Paire et pose conservees', font=font, fill='white')
    draw.text((16, 39), 'Cyan : source | Jaune : suivi LK | Rouge : projection de reference camera + objet', font=small, fill='white')
    for row, item in enumerate(details):
        index = item['track_index']; p = arrays['previous_native'][index]; q = arrays['current_native'][index]
        x, y = np.floor(p+.5).astype(int); ybase = 76+row*250
        for col, count in enumerate(counts):
            gray = (255*np.clip(np.log1p(count)/np.log(21), 0, 1)).astype(np.uint8)
            tile = Image.fromarray(gray).convert('RGB').crop((x-28, y-28, x+29, y+29)).resize((228, 228), Image.Resampling.NEAREST)
            pen = ImageDraw.Draw(tile)
            for point, color in ((p, '#00ffff'), (q, '#ffff00'), (gt[row], '#ff5050')):
                px, py = (point-[x-28, y-28])*4+1.5
                pen.ellipse((px-5, py-5, px+5, py+5), outline=color, width=2)
            # Outline the existing 5x5 corner block and show the real image edge.
            pen.rectangle((26*4, 26*4, 31*4-1, 31*4-1), outline='#8d9aaa')
            if x+28 >= 640:
                edge=(640-(x-28))*4
                pen.line((edge, 0, edge, 227), fill='#8d9aaa', width=2)
            canvas.paste(tile, (16+col*245, ybase))
        draw.text((520, ybase+5), f"Point {index} | pixel dominant natif {item['peak_native_xy']}", font=font, fill='#ffc65c')
        draw.text((520, ybase+40), 'Source / arrivee : memes coordonnees du capteur', font=small, fill='white')
        for j, window in enumerate(item['windows']):
            draw.text((520, ybase+70+j*30), f"{['Avant','Apres'][j]} : {window['events']} evenements ; voisins : {window['eight_neighbor_events']}", font=small, fill='white')
        draw.text((520, ybase+140), f"Aller-retour : {item['original_fb_px']:.4f} px | ecart GT : {item['full_reference_residual_px']:.2f} px", font=small, fill='white')
        draw.text((520, ybase+175), 'Support isole : aucune paire de pixels actifs voisins dans le bloc 5x5.', font=small, fill='white')
    excluded = report['groups']['excluded']
    draw.text((16, 834), f"Garde-fou exploratoire : {excluded['tracks']} suivis exclus, dont {excluded['reference_error_at_most_3px']} a ecart GT <=3 px. Non active sur DSEC.", font=small, fill='#ffc65c')
    draw.text((16, 858), 'EVIMO / EVIMO2 - Better Flow | CC BY-SA 4.0 | Une paire train ; aucune precision de mobilite mesuree.', font=small, fill='white')
    canvas.save(path)


def preview(images, p, q, report, path):
    font_path = Path('C:/Windows/Fonts/arial.ttf')
    font = ImageFont.truetype(str(font_path), 20) if font_path.exists() else ImageFont.load_default(size=20)
    small = ImageFont.truetype(str(font_path), 17) if font_path.exists() else ImageFont.load_default(size=17)
    canvas = Image.new('RGB', (1280, 970), '#102030')
    draw = ImageDraw.Draw(canvas)
    ids = report['frame_ids']
    method='ORB | ' if report['protocol'].get('frontend','').startswith('ORB') else ''
    draw.text((18, 12), f'EVIMO2 | {method}Controle separe, profondeur de reference | Images {ids[0]} -> {ids[1]} : 100 ms', font=font, fill='white')
    for i, (im, points) in enumerate(((images[0], p), (images[2], q))):
        canvas.paste(Image.fromarray(im).convert('RGB'), (640*i, 78))
        draw.text((18+640*i, 47), f"t = {report['times_s'][i]:.6f} s | evenements des 50 ms precedentes", font=small, fill='white')
        for x, y in points:
            draw.ellipse((x+640*i-2, y+76, x+640*i+2, y+80), fill='#40dfb0')
    y = 573
    draw.text((18, y), f"{len(p)} suivis retenus | Pose estimee : {report['model']['status']}", font=font, fill='#ffc65c')
    draw.text((18, y+32), 'References : deplacement de l origine objet sur 100 ms (pas une vitesse instantanee ni une classe mobile)', font=small, fill='white')
    columns = (18, 115, 470, 825)
    for x, label in zip(columns, ('ID', 'Apparent / camera (mm)', 'Corrige / monde (mm)', 'Rotation monde (deg)')):
        draw.text((x, y+66), label, font=font, fill='#9ac8ef')
    for row, item in enumerate(report['per_object']):
        values = (str(item['object_id']), f"{1000*item['apparent_origin_displacement_m']:.2f}",
                  f"{1000*item['world_origin_displacement_m']:.2f}", f"{item['world_rotation_deg']:.3f}")
        for x, text in zip(columns, values):
            draw.text((x, y+98+row*27), text, font=small, fill='white')
    draw.text((18, 904), 'Points verts : correspondances LK controlees, sans etiquette de mobilite. Test oracle sur une seule paire train.', font=small, fill='#ffc65c')
    draw.text((18, 936), 'EVIMO / EVIMO2 - Better Flow | CC BY-SA 4.0 | Ne valide pas la mobilite ni le temps reel sur DSEC.', font=small, fill='white')
    canvas.save(path)


if __name__ == '__main__':
    main()
