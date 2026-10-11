"""Audit acquired EVIMO train data; no detector, no mobility labels inferred."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pfe_events.artifacts import sha256_file as sha
from pfe_events.evimo_reference import read_metadata, timestamp_summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquisition', type=Path, default=ROOT / 'outputs/motion/M14/acquisition.json')
    parser.add_argument('--output', type=Path, required=True, help='New directory; existing results are never overwritten')
    args = parser.parse_args()
    out = args.output
    if out.exists():
        raise FileExistsError('Use a fresh audit output directory')
    acquisition = json.loads(args.acquisition.read_text(encoding='utf-8'))
    if acquisition['status'] != 'ACQUIRED_UNAUDITED':
        raise ValueError('Acquisition is incomplete')
    for file in acquisition['files']:
        if sha(ROOT / file['path']) != file['sha256']:
            raise ValueError('Acquired file hash mismatch')
    out.mkdir(parents=True)
    data = ROOT / 'data/raw/evimo2v2' / acquisition['sequence']
    meta = read_metadata(data / 'dataset_info.npz')
    frames = {int(f['id']): f for f in meta['frames']}
    if len(frames) != len(meta['frames']):
        raise ValueError('Duplicate frame IDs')
    width, height = meta['meta']['res_x'], meta['meta']['res_y']
    t = np.load(data / 'dataset_events_t.npy', mmap_mode='r', allow_pickle=False)
    p = np.load(data / 'dataset_events_p.npy', mmap_mode='r', allow_pickle=False)
    xy = np.load(data / 'dataset_events_xy.npy', mmap_mode='r', allow_pickle=False)
    if t.ndim != 1 or p.shape != t.shape or xy.shape != (len(t), 2):
        raise ValueError('Unexpected event shapes')
    previous = -np.inf
    counts = [0, 0]
    for start in range(0, len(t), 1_000_000):
        tt, pp, coords = t[start:start+1_000_000], p[start:start+1_000_000], xy[start:start+1_000_000]
        if (not np.isfinite(tt).all() or tt[0] < previous or np.any(np.diff(tt) < 0)
                or np.any(coords[:, 0] >= width) or np.any(coords[:, 1] >= height)
                or np.any(coords < 0) or np.any((pp != 0) & (pp != 1))):
            raise ValueError('Invalid events')
        previous = tt[-1]
        counts[0] += int(np.sum(pp == 0))
        counts[1] += int(np.sum(pp == 1))
    report = {
        'status': 'DATA_AUDITED_MOBILITY_NOT_EVALUATED', 'sequence': acquisition['sequence'],
        'acquisition_sha256': sha(args.acquisition),
        'event_count': len(t), 'event_range_s': [float(t[0]), float(t[-1])],
        'event_dtype': str(t.dtype), 'resolution': [width, height], 'polarity_counts': counts,
        'frames': timestamp_summary([f['ts'] for f in meta['frames']]),
        'trajectory': timestamp_summary([f['ts'] for f in meta['full_trajectory']]),
        'camera_metadata': meta['meta'], 'verified_input_hashes': len(acquisition['files']),
        'limits': ['One left-camera train sequence; not a stereo evaluation',
                   'Identity masks are not instantaneous mobility labels',
                   'Native events shown; GT spatial convention still to validate before pixelwise scoring',
                   'No precision, recall, false-alert rate or detection delay measured'],
    }
    with np.load(data / 'dataset_info.npz', allow_pickle=False) as info:
        report['K'] = info['K'].tolist()
        report['D'] = info['D'].tolist()
        report['distortion_discrepancy'] = {
            'D_p1_p2': info['D'][2:4].tolist(),
            'meta_p1_p2': [meta['meta']['p1'], meta['meta']['p2']],
            'resolution': 'Unresolved: verify producer convention before rectifying or scoring',
        }
    with np.load(data / 'dataset_mask.npz', allow_pickle=False) as masks, np.load(data / 'dataset_depth.npz', allow_pickle=False) as depths:
        mask_keys = {int(k.removeprefix('mask_')): k for k in masks.files}
        depth_keys = {int(k.removeprefix('depth_')): k for k in depths.files}
        if len(mask_keys) != len(masks.files) or len(depth_keys) != len(depths.files) or mask_keys.keys() != depth_keys.keys() or not mask_keys.keys() <= frames.keys():
            raise ValueError('Unmatched reference frames')
        ids, mask_without_pose, invalid_pose = set(), [], []
        fractions, ranges = [], []
        for index in sorted(mask_keys):
            mask, depth = masks[mask_keys[index]], depths[depth_keys[index]]
            if mask.shape != (height, width) or depth.shape != mask.shape or not np.isfinite(depth).all() or np.any(depth < 0):
                raise ValueError('Invalid reference arrays')
            unique = np.unique(mask)
            if np.any(unique % 1000):
                raise ValueError('Unexpected object encoding')
            object_ids = [str(int(v)//1000) for v in unique if v]
            ids.update(object_ids)
            for obj in object_ids:
                if obj not in frames[index]:
                    mask_without_pose.append([index, obj])
            fractions.append(float(np.mean(depth > 0)))
            if np.any(depth > 0):
                ranges.append([int(depth[depth > 0].min()), int(depth.max())])
        pose_offsets, quaternion_errors = [], []
        for collection in ('frames', 'full_trajectory'):
            for i, frame in enumerate(meta[collection]):
                for name, item in frame.items():
                    if not isinstance(item, dict) or 'pos' not in item:
                        continue
                    q = np.array([item['pos']['q'][v] for v in ('w','x','y','z')], dtype=float)
                    position = np.array([item['pos']['t'][v] for v in ('x','y','z')], dtype=float)
                    offset = abs(item['ts']-frame['ts'])
                    norm_error = abs(np.linalg.norm(q)-1)
                    pose_offsets.append(offset)
                    quaternion_errors.append(norm_error)
                    # Six-decimal timestamps may differ by 1 us; include a
                    # small floating-point margin, not nearest-frame snapping.
                    if not np.isfinite(position).all() or not np.isfinite(q).all() or norm_error > 1e-4 or not np.isfinite(offset) or offset > 1.1e-6:
                        invalid_pose.append([collection, i, name])
        available = sorted(mask_keys, key=lambda k: frames[k]['ts'])
        eligible = [k for k in available if frames[k]['ts']-0.020 >= float(t[0]) and frames[k]['ts'] <= float(t[-1])]
        report.update({
            'mask_depth_pairs': len(available),
            'paired_timestamps': timestamp_summary([frames[k]['ts'] for k in available]),
            'metadata_frame_ids_without_maps': sorted(frames.keys()-mask_keys.keys()),
            'object_ids_in_masks': sorted(ids, key=int), 'mask_objects_without_pose': mask_without_pose,
            'invalid_pose_records': invalid_pose, 'complete_causal_20ms_windows': len(eligible),
            'pose_record_count': len(pose_offsets),
            'max_pose_timestamp_offset_us': float(max(pose_offsets)*1e6),
            'max_quaternion_norm_error': float(max(quaternion_errors)),
            'pose_timestamp_tolerance_us': 1.1,
            'depth_positive_fraction_median': float(np.median(fractions)),
            'depth_stored_range': [min(r[0] for r in ranges), max(r[1] for r in ranges)],
        })
        # Fixed first/middle/last eligible references, independent of predictions.
        selected = [eligible[0], eligible[len(eligible)//2], eligible[-1]]
        canvas = Image.new('RGB', (1280, 3*520), '#102030')
        draw = ImageDraw.Draw(canvas)
        palette = np.array([[230,100,70],[80,210,160],[120,130,255],[240,205,70],[215,110,220],[60,195,235],[200,200,200],[135,185,70]], dtype=np.uint8)
        for row, index in enumerate(selected):
            end = frames[index]['ts']
            lo, hi = np.searchsorted(t, np.array([end-.020,end], dtype=np.float64), side='left')
            coords = xy[lo:hi].astype(np.int64)
            counts_image = np.bincount(coords[:,1]*width+coords[:,0], minlength=width*height).reshape(height,width)
            gray = (255*np.clip(np.log1p(counts_image)/np.log(21),0,1)).astype('uint8')
            mask = masks[mask_keys[index]]
            color = np.zeros((height,width,3),dtype=np.uint8)
            for n, obj in enumerate(sorted(ids,key=int)):
                color[mask==int(obj)*1000] = palette[n % len(palette)]
            y=row*520
            canvas.paste(Image.fromarray(gray).convert('RGB'), (0,y+40))
            canvas.paste(Image.fromarray(color), (640,y+40))
            draw.text((8,y+5), f'M14 | frame {index} | t={end:.6f}s | native events, causal 20ms',fill='white')
            draw.text((648,y+5), 'Official object IDs (not mobility) | black: ID 0',fill='white')
        canvas.save(out/'sample_preview.png')
        report['preview_frame_ids'] = selected
    sources = ['src/pfe_events/artifacts.py','scripts/download_evimo_sample.py','scripts/audit_evimo_sample.py','src/pfe_events/evimo_reference.py','tests/test_evimo_reference.py']
    report['sources'] = []
    for name in sources:
        source = ROOT / name
        snapshot = out / 'source_snapshot' / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(source.read_bytes())
        report['sources'].append({'path':name, 'sha256':sha(source)})
    (out/'audit.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','event_count','mask_depth_pairs','complete_causal_20ms_windows','invalid_pose_records','preview_frame_ids')},indent=2))


if __name__ == '__main__':
    main()
