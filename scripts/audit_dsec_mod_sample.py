"""Audit DSEC-MOD train annotations without inventing timestamp alignment."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pfe_events.artifacts import sha256_file, write_json
from pfe_events.dsec_mod_reference import read_train_cache, audit_tubes


def verified_files(entries):
    for entry in entries:
        path = ROOT / entry['path']
        if path.stat().st_size != entry['bytes'] or sha256_file(path) != entry['sha256']:
            raise ValueError(f'Acquisition hash/size mismatch: {entry["path"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquisition', type=Path, default=ROOT / 'outputs/motion/M15/acquisition.json')
    parser.add_argument('--timestamps', type=Path, default=ROOT / 'outputs/motion/M15/timestamp_acquisition.json')
    parser.add_argument('--rgb', type=Path, default=ROOT / 'outputs/motion/M15/rgb_acquisition.json')
    parser.add_argument('--output', type=Path, required=True, help='New audit directory')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh output directory')
    acquisition = json.loads(args.acquisition.read_text(encoding='utf-8'))
    timestamps = json.loads(args.timestamps.read_text(encoding='utf-8'))
    rgb = json.loads(args.rgb.read_text(encoding='utf-8'))
    for entries in (acquisition['files'], timestamps, rgb['files']):
        verified_files(entries)
    cache, = [ROOT / f['path'] for f in acquisition['files'] if f['upstream_path'] == 'data/DSEC/DSEC-GT.pkl']
    pilot = json.loads((ROOT / 'configs/pilot.json').read_text(encoding='utf-8'))
    sequences = [s['name'] for s in pilot['sequences'] if s['split'] == 'train']
    with cache.open('rb') as stream:
        reference = read_train_cache(stream, sequences)
    report = {'status': 'TRAIN_ANNOTATIONS_AUDITED_ALIGNMENT_PENDING',
              'upstream_commit': acquisition['commit'], 'cache_sha256': sha256_file(cache),
              'labels': reference['labels'], 'official_train': reference['train'],
              'official_test': reference['test'],
              'official_train_frames': sum(reference['metadata'][s]['frames'] for s in reference['train']),
              'official_test_frames': sum(reference['metadata'][s]['frames'] for s in reference['test']),
              'selected_train': sequences, 'sequences': {},
              'test_policy': {'bundled_test_bytes_downloaded': True, 'test_numeric_arrays_materialized': False,
                              'test_boxes_exported_or_inspected': False, 'test_images_downloaded': False},
              'limits': ['No precision, recall, false-alert rate or detection delay evaluated',
                         'Frame ordinals are not timestamps; no offset inferred from matching counts',
                         '640x480 projected RGB is not yet a verified native/rectified event coordinate convention',
                         'Upstream Moving annotations are not independently audited for exhaustiveness or onset timing',
                         'Annotation redistribution licence not established by the consulted sources']}
    by_name = {s['name']: s for s in pilot['sequences']}
    report['local_partition_membership'] = {
        name: {'local_split': s['split'], 'mod_split': 'train' if name in reference['train'] else
               'test' if name in reference['test'] else 'absent'} for name, s in by_name.items()}
    report['official_groups_in_both_splits'] = sorted(
        {s.rsplit('_', 1)[0] for s in reference['train']} & {s.rsplit('_', 1)[0] for s in reference['test']})
    export = {'status': 'NOT_READY_FOR_EVENT_SCORING', 'class': 'Moving',
              'box_format': 'xyxy_as_released', 'timestamp_mapping': None,
              'coordinate_mapping': None, 'sequences': {}}
    for sequence in sequences:
        meta = reference['metadata'][sequence]
        tubes = reference['tubes'][sequence]
        summary = audit_tubes(tubes, meta)
        tentry, = [e for e in timestamps if Path(e['path']).name == sequence + '_image_timestamps.txt']
        times = np.loadtxt(ROOT / tentry['path'], dtype=np.int64)
        if times.ndim != 1 or len(times) < 2 or np.any(np.diff(times) <= 0):
            raise ValueError('Invalid DSEC image timestamps')
        summary.update(meta)
        summary['dsec_image_timestamps'] = {'count': len(times), 'first_us': int(times[0]),
                                            'last_us': int(times[-1]),
                                            'median_step_us': float(np.median(np.diff(times))),
                                            'count_difference': len(times) - meta['frames']}
        report['sequences'][sequence] = summary
        export['sequences'][sequence] = {
            'metadata': meta, 'frames': [{'frame': frame, 'timestamp_us': None,
                'boxes': [{'tube_index': index, 'xyxy': row[1:].tolist()}
                          for index, tube in enumerate(tubes) for row in tube if row[0] == frame]}
                for frame in range(1, meta['frames'] + 1)]}
    report['source_hashes'] = {p: sha256_file(ROOT / p) for p in (
        'scripts/audit_dsec_mod_sample.py', 'src/pfe_events/dsec_mod_reference.py',
        'src/pfe_events/artifacts.py', 'configs/pilot.json')}
    report['acquisition_manifest_hashes'] = {p.name: sha256_file(p) for p in
                                            (args.acquisition, args.timestamps, args.rgb)}
    args.output.mkdir(parents=True)
    write_json(args.output / 'report.json', report)
    write_json(args.output / 'train_annotations.json', export)
    sheet = Image.new('RGB', (1280, 3 * 520), '#101c29')
    draw = ImageDraw.Draw(sheet)
    if rgb['sequence'] not in sequences or len(rgb['files']) != 3:
        raise ValueError('Expected three selected train images')
    for index, entry in enumerate(rgb['files']):
        with Image.open(ROOT / entry['path']) as source:
            image = source.convert('RGB')
        if image.size != (640, 480):
            raise ValueError('Unexpected projected RGB size')
        annotated = image.copy(); painter = ImageDraw.Draw(annotated)
        frame = export['sequences'][rgb['sequence']]['frames'][entry['frame']-1]
        for box in frame['boxes']:
            xy = box['xyxy']; painter.rectangle(xy, outline='#ffc400', width=2)
            painter.text((xy[0], max(0, xy[1]-12)), f"Moving / tube {box['tube_index']}", fill='#ffc400')
        y = index * 520
        draw.text((8, y+8), f"M15 | train {rgb['sequence']} | frame {entry['frame']} | timestamp UNKNOWN", fill='white')
        draw.text((648, y+8), 'Released boxes on projected RGB | event alignment NOT VALIDATED', fill='#ffc400')
        sheet.paste(image, (0, y+40)); sheet.paste(annotated, (640, y+40))
    sheet.save(args.output / 'train_preview.png')
    print(report['status'])
    for sequence, summary in report['sequences'].items():
        print(sequence, summary['box_count'], 'boxes;', summary['frames'], 'frames')


if __name__ == '__main__':
    main()
