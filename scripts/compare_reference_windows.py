"""M18: paired temporal-window diagnostic; references remain post-hoc only."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pfe_events.artifacts import sha256_file, write_json


def stats(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    return {'count': int(values.size), 'median': float(np.median(values)) if values.size else None,
            'p95': float(np.percentile(values, 95)) if values.size else None,
            'max': float(values.max()) if values.size else None}


def index_frames(report):
    rows = {f['id']: f for f in report['frames']}
    if len(rows) != len(report['frames']):
        raise ValueError('Duplicate frame IDs')
    return rows


def validate_pairing(long, short, historical):
    """Reject silent date, model, input or protocol changes before comparing."""
    reports = (long, short, historical)
    for report in reports:
        if report['status'] != 'COMPLETE_TRAIN_SUPPORT_DIAGNOSTIC':
            raise ValueError('Completed inference and association required')
        if report['protocol']['step_us'] != 20000:
            raise ValueError('Frozen 20 ms step required')
    if [r['protocol']['window_us'] for r in reports] != [50000, 20000, 50000]:
        raise ValueError('Expected windows 50/20/50 ms')
    indexed = [index_frames(r) for r in reports]
    if any(set(rows) != set(indexed[0]) for rows in indexed[1:]) or len(indexed[0]) != 6:
        raise ValueError('Identical six M16 dates required')
    for field in ('stereo', 'tracking', 'rigid', 'versions', 'input_sha256'):
        if any(r[field] != historical[field] for r in reports[:2]):
            raise ValueError(f'Incomparable {field}')
    for field in ('reference', 'normalizer', 'source_manifest', 'stereo_reference_config',
                  'roi_margins_px', 'geometry', 'association', 'depth', 'annotation_policy'):
        if any(r['protocol'][field] != historical['protocol'][field] for r in reports[:2]):
            raise ValueError(f'Incomparable protocol: {field}')
    for name, digest in historical['source_sha256'].items():
        if name.startswith('src/') or name in [historical['protocol'][k] for k in
                ('reference', 'normalizer', 'source_manifest', 'stereo_reference_config')]:
            if any(r['source_sha256'].get(name) != digest for r in reports[:2]):
                raise ValueError(f'Changed frozen source: {name}')
    common, startup = [], []
    for cid, old in indexed[2].items():
        for report, rows in zip(reports, indexed):
            frame, protocol = rows[cid], report['protocol']
            if any(frame[k] != old[k] for k in ('sequence', 'mod_frame', 'timestamp_us')):
                raise ValueError('Mismatched date metadata')
            inf = frame['inference']; end = frame['timestamp_us']; window = protocol['window_us']
            if (inf['current_us'] != end or inf['previous_us'] != end-20000
                    or inf['depth_us'] != end-20000
                    or inf['windows_us'] != [[end-20000-window, end-20000], [end-window, end]]
                    or inf['overlap_us'] != window-20000):
                raise ValueError('Window or depth timestamp mismatch')
        (common if old['inference']['status'] == 'PAIR_PROCESSED' else startup).append(cid)
    if (len(common), len(startup)) != (4, 2):
        raise ValueError('Expected four preselected common dates and two startup dates')
    return sorted(common), sorted(startup)


def verify_reproduction(directory, historical_dir, fresh, historical):
    checks = []
    for cid in sorted(index_frames(historical)):
        a, b = index_frames(fresh)[cid], index_frames(historical)[cid]
        ia = {k: v for k, v in a['inference'].items() if k != 'timing_ms'}
        ib = {k: v for k, v in b['inference'].items() if k != 'timing_ms'}
        same_metadata = ia == ib and a['association'] == b['association']
        with np.load(directory / f'{cid}.npz', allow_pickle=False) as left, np.load(
                historical_dir / f'{cid}.npz', allow_pickle=False) as right:
            same_arrays = set(left.files) == set(right.files) and all(
                left[k].dtype == right[k].dtype and left[k].shape == right[k].shape
                and np.array_equal(left[k], right[k], equal_nan=True) for k in left.files)
        checks.append({'id': cid, 'arrays_exact': same_arrays, 'non_timing_metadata_exact': same_metadata})
    if not all(x['arrays_exact'] and x['non_timing_metadata_exact'] for x in checks):
        raise ValueError(f'M17 reproduction differs: {checks}')
    return checks


def describe_frame(frame, arrays):
    inf = frame['inference']; q = arrays['current']; p = arrays['previous']; z = arrays['depth_samples']
    states = np.asarray(inf['rigid']['point_status'], dtype=str)
    residual = np.asarray([np.nan if x is None else x for x in inf['rigid'].get('residual_px', [])])
    if not residual.size:
        residual = np.full(len(q), np.nan)
    union = np.zeros(len(q), bool)
    boxes = []
    for box in frame['association']['0']['boxes']:
        x1, y1, x2, y2 = box['reference_xyxy']
        inside = (q[:, 0] >= x1) & (q[:, 0] < x2) & (q[:, 1] >= y1) & (q[:, 1] < y2)
        union |= inside
        boxes.append({**box, 'displacement_px': stats(np.linalg.norm(q[inside]-p[inside], axis=1)),
                      'residual_px': stats(residual[inside]), 'previous_depth_m': stats(z[inside])})
    return {'id': frame['id'], 'status': inf['status'], 'rigid_status': inf['rigid']['status'],
            'current_events': inf['current_event_count'], 'checked_tracks': len(q),
            'depth_tracks': int((np.isfinite(z) & (z > 0)).sum()),
            'unknown_tracks': int((states == 'UNKNOWN').sum()),
            'evaluated_tracks': int((states != 'UNKNOWN').sum()),
            'residual_tracks': int((states == 'RESIDUAL_CANDIDATE').sum()),
            'inside_unique_tracks': int(union.sum()),
            'inside_unique_depth_tracks': int((union & np.isfinite(z) & (z > 0)).sum()),
            'inside_unique_residual_tracks': int((union & (states == 'RESIDUAL_CANDIDATE')).sum()),
            'outside_residual_tracks': int((~union & (states == 'RESIDUAL_CANDIDATE')).sum()),
            'depth_pixels': int(arrays['depth_valid'].sum()),
            'depth_pixels_left_search_border': int(arrays['depth_valid'][:, :96].sum()),
            'displacement_px': stats(np.linalg.norm(q-p, axis=1)), 'residual_px': stats(residual),
            'inside_residual_px': stats(residual[union]), 'boxes': boxes,
            'pipeline_cpu_ms': inf['timing_ms']['pipeline'],
            'by_margin': {m: dict(Counter(b['diagnostic'] for b in a['boxes']))
                          for m, a in frame['association'].items()}}


def aggregate(rows):
    totals = {key: sum(r[key] for r in rows) for key in (
        'current_events', 'checked_tracks', 'depth_tracks', 'unknown_tracks', 'evaluated_tracks',
        'residual_tracks', 'inside_unique_tracks', 'inside_unique_depth_tracks',
        'inside_unique_residual_tracks', 'outside_residual_tracks')}
    return {'frames': len(rows), 'reference_boxes': sum(len(r['boxes']) for r in rows),
            'totals': totals, 'pipeline_cpu_ms': stats([r['pipeline_cpu_ms'] for r in rows]),
            'by_margin': {m: dict(sum((Counter(r['by_margin'][m]) for r in rows), Counter()))
                          for m in ('-5', '0', '5')}}


def draw_pair(rows, arrays, cid, cohort):
    sheet = Image.new('RGB', (1280, 745), '#102030'); draw = ImageDraw.Draw(sheet)
    draw.text((10, 8), f'M18 | {cid} | {cohort} | RECORDED DATA / OFFLINE CPU', fill='white')
    draw.text((10, 28), 'Cyan: public reference | Orange: residual >3px | Green: model-consistent | Grey: unknown', fill='#ffc040')
    draw.text((10, 46), 'Residuals are candidates, not confirmed moving objects. Tracks differ between windows.', fill='white')
    colors = {'UNKNOWN': '#aaaaaa', 'MODEL_CONSISTENT': '#25cf9b', 'RESIDUAL_CANDIDATE': '#ffc040'}
    for shift, (label, row, data) in zip((0, 640), zip(('50 ms / step 20 ms', '20 ms / step 20 ms'), rows, arrays)):
        draw.text((shift+8, 66), label, fill='white')
        sheet.paste(Image.fromarray(data['current_image']).convert('RGB'), (shift, 90))
        for b in row['association']['0']['boxes']:
            x1, y1, x2, y2 = b['reference_xyxy']
            draw.rectangle((x1+shift, y1+90, x2+shift, y2+90), outline='#30ceff', width=2)
            draw.text((x1+shift, max(90, y1+78)), str(b['tube_index']), fill='#30ceff')
        for (x, y), status in zip(data['current'], row['inference']['rigid']['point_status']):
            draw.ellipse((x+shift-2, y+88, x+shift+2, y+92), fill=colors[status])
        d = describe_frame(row, data)
        draw.text((shift+8, 585), f"Tracks {d['checked_tracks']} | depth {d['depth_tracks']} | residual {d['residual_tracks']} | unknown {d['unknown_tracks']}", fill='white')
        for j, b in enumerate(d['boxes']):
            draw.text((shift+8, 609+j*19), f"Tube {b['tube_index']}: {b['diagnostic']} (tracks {b['checked_tracks']}, depth {b['tracks_with_previous_depth']}, res {b['residual_tracks']})", fill='white')
    return sheet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--long', type=Path, required=True)
    parser.add_argument('--short', type=Path, required=True)
    parser.add_argument('--historical', type=Path, default=ROOT / 'outputs/motion/M17')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh comparison directory')
    directories = (args.long, args.short, args.historical)
    reports = [json.loads((p / 'summary.json').read_text()) for p in directories]
    common, startup = validate_pairing(*reports)
    reproduction = verify_reproduction(args.long, args.historical, reports[0], reports[2])
    args.output.mkdir(parents=True)
    shutil.copy2(__file__, args.output / Path(__file__).name)
    result = {'experiment': 'M18', 'status': 'RUNNING',
              'common_ids_preselected_from_M17': common, 'startup_ids_separate': startup,
              'historical_reproduction': reproduction, 'input_sha256': {}, 'variants': {},
              'sources': {str(p.resolve()): sha256_file(p / 'summary.json') for p in directories},
              'script_sha256': sha256_file(Path(__file__)),
              'mobility_precision': None, 'mobility_recall': None,
              'caution': 'Window length changes overlap, event support, stereo and fitted model simultaneously; train diagnostics only; unmatched track populations; CPU times are single offline samples'}
    try:
        for label, directory, report in zip(('50ms', '20ms'), directories, reports):
            rows = []
            for frame in report['frames']:
                path = directory / (frame['id']+'.npz')
                result['input_sha256'][str(path.resolve())] = sha256_file(path)
                with np.load(path, allow_pickle=False) as data:
                    rows.append(describe_frame(frame, data))
            result['variants'][label] = {'frames': rows,
                'common': aggregate([r for r in rows if r['id'] in common]),
                'startup': aggregate([r for r in rows if r['id'] in startup])}
        indexed = [index_frames(r) for r in reports[:2]]
        result['box_transitions_common'] = []
        for cid in common + startup:
            pair = [r[cid] for r in indexed]
            arrays = []
            for directory in directories[:2]:
                with np.load(directory / (cid+'.npz'), allow_pickle=False) as data:
                    arrays.append({key: data[key] for key in data.files})
            draw_pair(pair, arrays, cid, 'COMMON DATES' if cid in common else 'STARTUP / SEPARATE').save(args.output / (cid+'.png'))
            if cid in common:
                short_boxes = {b['tube_index']: b for b in pair[1]['association']['0']['boxes']}
                for box in pair[0]['association']['0']['boxes']:
                    other = short_boxes[box['tube_index']]
                    result['box_transitions_common'].append({'id': cid, 'tube_index': box['tube_index'],
                        '50ms': box['diagnostic'], '20ms': other['diagnostic'],
                        'tracks_50ms_20ms': [box['checked_tracks'], other['checked_tracks']],
                        'depth_50ms_20ms': [box['tracks_with_previous_depth'], other['tracks_with_previous_depth']],
                        'residual_50ms_20ms': [box['residual_tracks'], other['residual_tracks']]})
        result['status'] = 'COMPLETE_PAIRED_TRAIN_DIAGNOSTIC'
        print(json.dumps({v: r['common'] for v, r in result['variants'].items()}, indent=2))
    except Exception as error:
        result.update(status='FAILED', error=repr(error)); raise
    finally:
        write_json(args.output / 'summary.json', result)


if __name__ == '__main__':
    main()
