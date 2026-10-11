"""M03: fixed global image-motion baseline and blind annotation clips."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from pfe_events.visualization import native_event_image as native_image
from pfe_events.dsec_indexed import IndexedDSECReader
from pfe_events.global_motion import GlobalMotionDetector, event_gray
from pfe_events.motion import ActivityDetector
from pfe_events.pilot import load_manifest, unique_file
from pfe_events.artifacts import sha256_file as digest
from pfe_events.reporting import activity_distribution as distribution


def diagnostic(raw, activity, motion, clip_id, end):
    out = Image.new('RGB', (1280, 552), '#102030')
    out.paste(raw, (0, 64)); out.paste(raw, (640, 64))
    draw = ImageDraw.Draw(out)
    draw.text((12, 8), f'M03 | {clip_id} | t={end} us | 20 ms | RECORDED REPLAY', fill='white')
    draw.text((12, 28), 'LEFT: event activity / RIGHT: residual candidates, NOT confirmed moving objects', fill='#ffd166')
    draw.text((12, 46), f"Global image model: {motion['status']} | tracked points: {motion.get('tracks', 0)}", fill='white')
    for region in activity['regions']:
        x1, y1, x2, y2 = region['xyxy']; draw.rectangle((x1, y1+64, x2-1, y2+63), outline='#dd77ff', width=2)
    for x, y in motion.get('residual_points_native', []):
        draw.ellipse((640+x-2, y+62, 640+x+2, y+66), fill='#ffbb33')
    for region in motion['regions']:
        x1, y1, x2, y2 = region['xyxy']; draw.rectangle((640+x1, y1+64, 639+x2, y2+63), outline='#ffbb33', width=2)
    return out


def run_clip(reader, sequence, split, index, start, output):
    clip_id = f'{sequence}_{index}'
    folder = output/'clips'/clip_id; (folder/'raw').mkdir(parents=True)
    activity = ActivityDetector(); detector = GlobalMotionDetector()
    frames, results, snapshots = [], [], []
    for i, begin in enumerate(range(start-200_000, start+2_000_000, 20_000)):
        end = begin+20_000
        t0 = time.perf_counter_ns(); events = reader.window(begin, end); t1 = time.perf_counter_ns()
        active = activity.update(events, begin, end); t2 = time.perf_counter_ns()
        gray = event_gray(events); t3 = time.perf_counter_ns()
        motion = detector.update(gray, end); t4 = time.perf_counter_ns()
        record = {'end_us': end, 'warmup': end <= start, 'motion': motion,
                  'activity_regions': active['regions'], 'events': len(events['x']),
                  'timing_ms': {'read': (t1-t0)/1e6, 'activity': (t2-t1)/1e6,
                                'representation': (t3-t2)/1e6, 'global_motion': (t4-t3)/1e6,
                                'total': (t4-t0)/1e6}}
        results.append(record)
        if end > start:
            raw = native_image(events)  # annotation/export outside measured sections
            name = f'raw/{len(frames):04d}.jpg'
            raw.save(folder/name, quality=90)
            frames.append({'end_us': end, 'start_us': begin, 'image': f'clips/{clip_id}/{name}'})
            if len(frames) in (1, 21, 41, 61, 81, 100):
                snapshots.append((raw, end))
            if len(frames) == 51:
                diagnostic(raw, active, motion, clip_id, end).save(folder/'diagnostic.png')
    (folder/'predictions.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
    sheet = Image.new('RGB', (960, 540), '#102030'); draw = ImageDraw.Draw(sheet)
    for i, (picture, end) in enumerate(snapshots):
        x, y = i % 3 * 320, i // 3 * 270
        sheet.paste(picture.resize((320, 240)), (x, y+30))
        draw.text((x+5, y+5), f'{clip_id} | +{(end-start)/1000:.0f} ms', fill='white')
    sheet.save(folder/'contact_sheet.png')
    measured = [r for r in results if not r['warmup']]
    valid = [r for r in measured if r['motion']['valid']]
    return {'id': clip_id, 'sequence': sequence, 'split': split, 'start_us': start, 'end_us': start+2_000_000,
            'step_us': 20_000, 'frames': frames, 'motion_parameters': detector.parameters(),
            'statuses': dict(Counter(r['motion']['status'] for r in measured)),
            'valid_fraction': len(valid)/len(measured),
            'fraction_frames_with_residual_regions': sum(bool(r['motion']['regions']) for r in measured)/len(measured),
            'fraction_frames_with_activity_regions': sum(bool(r['activity_regions']) for r in measured)/len(measured),
            'timing_ms': {k: distribution([r['timing_ms'][k] for r in measured]) for k in measured[0]['timing_ms']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/motion/M03')
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh experiment directory')
    entries = [e for e in load_manifest(ROOT/'configs/pilot.json')['sequences']
               if e['name'] in ('zurich_city_04_b', 'thun_00_a') and e['split'] != 'test_reserved']
    if len(entries) != 2: raise ValueError('Expected two authorized sequences')
    args.output.mkdir(parents=True); cv2.setNumThreads(1)
    sources = ['src/pfe_events/artifacts.py','src/pfe_events/reporting.py','src/pfe_events/visualization.py','scripts/run_global_motion.py', 'src/pfe_events/global_motion.py', 'src/pfe_events/motion.py',
               'src/pfe_events/dsec.py', 'src/pfe_events/dsec_indexed.py', 'configs/pilot.json']
    report = {'experiment': 'M03', 'status': 'RUNNING', 'utc': datetime.now(timezone.utc).isoformat(),
              'purpose': 'APPARENT GLOBAL IMAGE MOTION AND RESIDUAL CANDIDATES; NOT CONFIRMED INDEPENDENT OBJECT MOTION',
              'selection': 'Beginning/middle/end two-second clips, 200ms prior warmup; no label or score selection',
              'timing_scope': 'Read + activity + fixed representation + sparse flow/global fit. Export/render excluded; unpaced disk replay.',
              'versions': {k: importlib.metadata.version(k) for k in ('numpy', 'opencv-python-headless', 'h5py', 'Pillow')},
              'code_sha256': {p: digest(ROOT/p) for p in sources}, 'clips': [],
              'real_onset_delay_ms': None, 'false_alerts_per_second': None, 'annotation_status': 'PENDING_MANUAL_REVIEW'}
    try:
        for name in sources:
            dest = args.output/'source_snapshot'/name; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT/name).read_bytes())
            if digest(dest) != report['code_sha256'][name]: raise IOError('Source changed')
        for entry in entries:
            path = unique_file(ROOT/'data/raw'/entry['name']/'events_left', 'events.h5')
            with IndexedDSECReader(path) as reader:
                span = reader.last_us-reader.first_us-2_200_000
                if span < 0: raise ValueError('Sequence too short')
                for index, fraction in enumerate((0.0, 0.5, 1.0)):
                    start = reader.first_us+200_000+int(span*fraction)//20_000*20_000
                    clip = run_clip(reader, entry['name'], entry['split'], index, start, args.output)
                    report['clips'].append(clip)
                    print(clip['id'], clip['statuses'], clip['timing_ms']['total'], flush=True)
        report['status'] = 'COMPLETE_DIAGNOSTIC_AND_ANNOTATION_PACK; ACCURACY_NOT_EVALUATED'
        manifest = {'schema': 'pfe-motion-annotation-v1', 'width': 640, 'height': 480,
                    'step_us': 20_000, 'target': 'observable local motion relative to scene; uncertainty required',
                    'clips': [{k: c[k] for k in ('id', 'sequence', 'split', 'start_us', 'end_us', 'step_us', 'frames')} for c in report['clips']]}
        (args.output/'annotation_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
        (args.output/'annotation_data.js').write_text('window.ANNOTATION_DATA='+json.dumps(manifest)+';\n', encoding='utf-8')
        template = ROOT/'scripts/motion_annotation.html'
        (args.output/'annotate.html').write_bytes(template.read_bytes())
        report['annotation_ui_sha256'] = digest(template)
    except Exception as error:
        report.update(status='FAILED', error=repr(error)); raise
    finally:
        (args.output/'summary.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__': main()
