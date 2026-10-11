"""Frozen geometric pipeline, followed by train-reference support audit (M17/M18)."""
import argparse
from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pfe_events.artifacts import sha256_file, write_json
from pfe_events.dsec import load_rectify_map
from pfe_events.dsec_cached import CachedIndexedDSECReader
from pfe_events.geometry import audit_calibration, reproject_q
from pfe_events.representations import rectified_counts, normalized_event_image
from pfe_events.rectified_tracking import checked_tracks, sample_masked_depth, TrackingConfig
from pfe_events.rigid_motion import estimate_rigid_motion, RigidMotionConfig
from pfe_events.stereo import predict_stereo, StereoConfig
from pfe_events.reference_diagnostic import box_support


def infer_pair(left, right, maps, calibration, normalizer, end, window, step, stereo):
    """Model inputs contain events, calibration and dates only, never boxes/RGB."""
    if (any(type(v) is not int for v in (end, window, step))
            or not 0 < step <= window or step > RigidMotionConfig().max_interval_us):
        raise ValueError('Integer causal dates and 0 < step <= window required')
    begin = time.perf_counter()
    previous_end = end-step
    if end-window < left.first_us or end > left.last_us:
        raise ValueError('Incomplete current activity window')
    current_events = left.window(end-window, end)
    counts, dropped = rectified_counts(current_events, maps[0])
    current = np.ascontiguousarray(normalized_event_image(counts, normalizer)[..., 2])
    activity_time = time.perf_counter()
    output = {'previous': np.empty((0, 2), np.float32), 'current': np.empty((0, 2), np.float32),
              'depth_samples': np.empty(0), 'current_image': current, 'current_counts': counts.sum(axis=0),
              'previous_image': np.zeros_like(current), 'depth_m': np.full(current.shape, np.nan, np.float32),
              'disparity_px': np.full(current.shape, np.nan, np.float32),
              'depth_valid': np.zeros(current.shape, bool)}
    common = {'previous_us': previous_end, 'current_us': end, 'depth_us': previous_end,
              'current_event_count': len(current_events['x']), 'current_rectification_dropped': dropped,
              'windows_us': [[previous_end-window, previous_end], [end-window, end]],
              'overlap_us': window-step, 'tracking': {'checked_tracks': 0},
              'rigid': {'valid': False, 'status': 'INSUFFICIENT_HISTORY', 'point_status': []},
              'timing_ms': {'current_read_representation': (activity_time-begin)*1000}}
    if any(previous_end-window < r.first_us or previous_end > r.last_us for r in (left, right)):
        common['status'] = 'INSUFFICIENT_HISTORY'
        common['available_history_us_left_right'] = [end-r.first_us for r in (left, right)]
        common['required_history_us'] = window+step
        common['timing_ms']['pipeline'] = (time.perf_counter()-begin)*1000
        return output, common
    images, event_counts = [], []
    for reader, mapping in zip((left, right), maps):
        events = reader.window(previous_end-window, previous_end)
        event_counts.append(len(events['x']))
        previous_counts, _ = rectified_counts(events, mapping)
        images.append(np.ascontiguousarray(normalized_event_image(previous_counts, normalizer)[..., 2]))
    represented = time.perf_counter()
    disparity, valid, _, mask = predict_stereo(*images, stereo)
    yy, xx = np.indices(disparity.shape)
    depth = reproject_q(xx, yy, disparity, calibration['q'])[..., 2].astype(np.float32)
    stereo_end = time.perf_counter()
    p, q, tracking = checked_tracks(images[0], current)
    z, sampling = sample_masked_depth(p, depth, valid)
    tracked = time.perf_counter()
    intrinsic = np.array([[calibration['fx_px'], 0, calibration['cx_px']],
                          [0, calibration['fy_px'], calibration['cy_px']], [0, 0, 1.]])
    rigid = estimate_rigid_motion(p, q, z, intrinsic, previous_us=previous_end,
                                 current_us=end, depth_us=previous_end, depth_source='predicted')
    finished = time.perf_counter()
    output.update(previous=p, current=q, depth_samples=z, previous_image=images[0],
                  depth_m=depth, disparity_px=disparity, depth_valid=valid)
    common.update(status='PAIR_PROCESSED', tracking=tracking, sampling=sampling, rigid=rigid,
                  previous_event_counts_left_right=event_counts, stereo_mask=mask,
                  predicted_depth_pixels=int(valid.sum()))
    common['timing_ms'].update(previous_stereo_read_representation=(represented-activity_time)*1000,
                              stereo_and_depth=(stereo_end-represented)*1000,
                              tracking_sampling=(tracked-stereo_end)*1000,
                              rigid_fit=(finished-tracked)*1000, pipeline=(finished-begin)*1000)
    return output, common


def draw_diagnostic(frame, arrays, inference, diagnostic, experiment='M17'):
    sheet = Image.new('RGB', (1280, 710), '#102030'); draw = ImageDraw.Draw(sheet)
    draw.text((10, 8), f"{experiment} | {frame['sequence']} | frame {frame['mod_frame']} | {inference['status']}", fill='white')
    draw.text((10, 28), 'LEFT: published Moving references | RIGHT: event tracks and rigid residuals (not object detections)', fill='white')
    draw.text((10, 48), 'Cyan boxes: reference | Orange points: residual >3px | Green: model-consistent | Grey: unknown', fill='#ffc040')
    rgb_path = ROOT / f"data/raw/dsec_mod/{frame['sequence']}/rgb_calib/{frame['mod_frame']:06d}.png"
    with Image.open(rgb_path) as rgb: sheet.paste(rgb.convert('RGB'), (0, 80))
    sheet.paste(Image.fromarray(arrays['current_image']).convert('RGB'), (640, 80))
    for box in frame['boxes']:
        x1, y1, x2, y2 = box['xyxy']
        for shift in (0, 640):
            draw.rectangle([x1+shift, y1+80, x2+shift, y2+80], outline='#30ceff', width=2)
            draw.text((x1+shift, max(80, y1+68)), str(box['tube_index']), fill='#30ceff')
    colors = {'UNKNOWN': '#aaaaaa', 'MODEL_CONSISTENT': '#25cf9b', 'RESIDUAL_CANDIDATE': '#ffc040'}
    for (x, y), status in zip(arrays['current'], inference['rigid']['point_status']):
        draw.ellipse([x+638, y+78, x+642, y+82], fill=colors[status])
    for i, box in enumerate(diagnostic['boxes']):
        draw.text((10, 575+i*19), f"Tube {box['tube_index']}: {box['diagnostic']} | tracks {box['checked_tracks']} | depth {box['tracks_with_previous_depth']} | residual {box['residual_tracks']}", fill='white')
    return sheet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Fresh experiment directory')
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/m17_reference_diagnostic.json',
                        help='Frozen protocol; defaults to the historical M17 configuration')
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh output directory')
    protocol_path = args.config.resolve()
    protocol = json.loads(protocol_path.read_text())
    reference = json.loads((ROOT / protocol['reference']).read_text())
    pilot = json.loads((ROOT / protocol['source_manifest']).read_text())
    allowed = {s['name'] for s in pilot['sequences'] if s['split'] == 'train'}
    frames = reference['frames']
    if (reference['status'] != 'SAMPLE_ALIGNMENT_VERIFIED_NOT_MOBILITY_EVALUATED'
            or reference['coordinate_frame'] != 'camRect0' or len(frames) != 6
            or len({(f['sequence'], f['mod_frame']) for f in frames}) != 6
            or not {f['sequence'] for f in frames} <= allowed):
        raise ValueError('Expected six verified train frames')
    normalizer = json.loads((ROOT / protocol['normalizer']).read_text())
    if normalizer['source_split'] != 'train': raise ValueError('Frozen train normalizer required')
    stereo = StereoConfig(); saved = json.loads((ROOT / protocol['stereo_reference_config']).read_text())
    if any(saved['stereo'][key] != value for key, value in asdict(stereo).items()):
        raise ValueError('Stereo defaults changed since S01')
    if protocol.get('frozen_model_reference'):
        frozen = json.loads((ROOT / protocol['frozen_model_reference']).read_text())
        for key, actual in [('stereo', asdict(stereo)), ('tracking', asdict(TrackingConfig())),
                            ('rigid', asdict(RigidMotionConfig()))]:
            if frozen[key] != actual:
                raise ValueError(f'Frozen M17 {key} parameters changed')
        for name, digest in frozen['source_sha256'].items():
            if name.startswith('src/') and sha256_file(ROOT / name) != digest:
                raise ValueError(f'Frozen M17 algorithm changed: {name}')
    cv2.setNumThreads(1)
    args.output.mkdir(parents=True)
    source_files = ['scripts/run_reference_diagnostic.py', 'src/pfe_events/reference_diagnostic.py',
                    'src/pfe_events/artifacts.py', 'src/pfe_events/representations.py', 'src/pfe_events/stereo.py',
                    'src/pfe_events/geometry.py', 'src/pfe_events/rectified_tracking.py', 'src/pfe_events/rigid_motion.py',
                    'src/pfe_events/dsec.py', 'src/pfe_events/dsec_cached.py', 'src/pfe_events/dsec_indexed.py',
                    'tests/test_reference_diagnostic.py', protocol_path.relative_to(ROOT).as_posix(),
                    protocol['reference'], protocol['source_manifest'], protocol['normalizer'], protocol['stereo_reference_config']]
    if protocol.get('frozen_model_reference'):
        source_files.append(protocol['frozen_model_reference'])
    report = {'experiment': protocol['experiment'], 'status': 'RUNNING', 'utc': datetime.now(timezone.utc).isoformat(),
              'protocol': protocol, 'stereo': asdict(stereo), 'tracking': asdict(TrackingConfig()),
              'rigid': asdict(RigidMotionConfig()), 'versions': {'opencv': cv2.__version__, 'numpy': np.__version__},
              'source_sha256': {p: sha256_file(ROOT / p) for p in source_files}, 'input_sha256': {}, 'frames': [],
              'mobility_precision': None, 'mobility_recall': None, 'false_alert_rate': None,
              'timing_limit': 'Sequential offline CPU costs including fresh stereo; excludes init, evaluation, visualization; not detection delay'}
    for name in source_files:
        dst = args.output / 'sources' / name; dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dst)
    write_json(args.output / 'summary.json', report)
    try:
        # Inference phase: pass sequence/date metadata only, no reference boxes.
        for sequence in sorted({f['sequence'] for f in frames}):
            folder = ROOT / 'data/raw' / sequence
            calib_path = folder / 'calibration/cam_to_cam.yaml'
            calibration = audit_calibration(calib_path)
            if not calibration['canonical_equal_intrinsics']: raise ValueError('Unsupported event geometry')
            paths = [folder / f'events_{side}/events.h5' for side in ('left', 'right')]
            map_paths = [folder / f'events_{side}/rectify_map.h5' for side in ('left', 'right')]
            for path in [calib_path, *paths, *map_paths]:
                report['input_sha256'][path.relative_to(ROOT).as_posix()] = sha256_file(path)
            maps = [load_rectify_map(path) for path in map_paths]
            with ExitStack() as stack:
                readers = [stack.enter_context(CachedIndexedDSECReader(p)) for p in paths]
                jobs = [(f['mod_frame'], f['timestamp_us']) for f in frames if f['sequence'] == sequence]
                for index, end in jobs:
                    arrays, inference = infer_pair(*readers, maps, calibration, normalizer, end,
                        protocol['window_us'], protocol['step_us'], stereo)
                    cid = f'{sequence}_{index:06d}'
                    np.savez_compressed(args.output / f'{cid}.npz', **arrays)
                    write_json(args.output / f'{cid}_inference.json', inference)
                    report['frames'].append({'id': cid, 'sequence': sequence, 'mod_frame': index,
                                              'timestamp_us': end, 'inference': inference})
                    print(cid, inference['status'], inference['rigid']['status'], flush=True)
        # Only after all inference results are saved are the boxes consulted.
        for row in report['frames']:
            frame, = [f for f in frames if (f['sequence'], f['mod_frame']) == (row['sequence'], row['mod_frame'])]
            with np.load(args.output / (row['id']+'.npz'), allow_pickle=False) as data:
                arrays = {key: data[key] for key in data.files}
            inference = row['inference']
            unavailable = inference['status'] if inference['status'] == 'INSUFFICIENT_HISTORY' else None
            row['association'] = {}
            for margin in protocol['roi_margins_px']:
                row['association'][str(margin)] = box_support(frame['boxes'], arrays['current'],
                    arrays['depth_samples'], inference['rigid']['point_status'], arrays['current_counts'],
                    margin=margin, unavailable=unavailable)
            draw_diagnostic(frame, arrays, inference, row['association']['0'], protocol['experiment']).save(args.output / (row['id']+'.png'))
            write_json(args.output / (row['id']+'_diagnostic.json'), row)
        report['by_margin'] = {str(m): dict(Counter(b['diagnostic'] for row in report['frames']
                              for b in row['association'][str(m)]['boxes'])) for m in protocol['roi_margins_px']}
        report['status'] = 'COMPLETE_TRAIN_SUPPORT_DIAGNOSTIC'
        print(json.dumps(report['by_margin'], indent=2))
    except Exception as error:
        report.update(status='FAILED', error=repr(error)); raise
    finally:
        write_json(args.output / 'summary.json', report)


if __name__ == '__main__': main()
