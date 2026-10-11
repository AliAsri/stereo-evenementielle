"""Verify six fixed train image correspondences; no sequence-wide extrapolation."""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pfe_events.artifacts import sha256_file, write_json
from pfe_events.dsec import DSECReader, load_rectify_map, rectify_events
from pfe_events.mod_alignment import (rgb_to_event_homography, compare_projected_rgb,
                                      select_verified_frame, verified_timestamp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Fresh output directory')
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh output directory')
    cv2.setNumThreads(2)
    manifests = ['outputs/motion/M15/rgb_acquisition.json',
                 'outputs/motion/M15/timestamp_acquisition.json',
                 'outputs/motion/M16/zurich_city_04_b_mod_acquisition.json',
                 'outputs/motion/M16/zurich_city_04_e_rgb_acquisition.json',
                 'outputs/motion/M16/zurich_city_04_b_rgb_acquisition.json',
                 'outputs/motion/M16/exposure_acquisition.json']
    hashes = {}
    for name in manifests:
        manifest = json.loads((ROOT / name).read_text(encoding='utf-8'))
        hashes[name] = sha256_file(ROOT / name)
        for entry in manifest if isinstance(manifest, list) else manifest['files']:
            path = ROOT / entry['path']
            digest = sha256_file(path)
            if digest != entry['sha256'] or path.stat().st_size != entry['bytes']:
                raise ValueError(f'Input differs: {path}')
            hashes[entry['path']] = digest
    annotations_path = ROOT / 'outputs/motion/M15/audit/train_annotations.json'
    annotations = json.loads(annotations_path.read_text())['sequences']
    hashes[str(annotations_path.relative_to(ROOT))] = sha256_file(annotations_path)
    report = {'status': 'SIX_TRAIN_FRAME_MATCHES_VERIFIED', 'frames': [], 'geometry': {},
              'matching_gate': {'max_mae_8bit': 1., 'min_runner_up_margin_8bit': 1.,
                                'chosen_after_first_04_e_probe': True},
              'scope': 'Only frames 1,134,267 of train 04_e and 04_b are mapped',
              'limits': ['Other frame timestamps remain unknown; no full-sequence offset asserted',
                         'Rotation-only RGB warp neglects camera translation and finite-depth parallax',
                         'Image photometric reproduction is not object-motion detection accuracy',
                         'Published box accuracy and completeness are not independently certified',
                         'Event panels are causal 20 ms activity, not detector predictions',
                         'No test image or test box inspected']}
    manifest = {'status': 'SAMPLE_ALIGNMENT_VERIFIED_NOT_MOBILITY_EVALUATED',
                'coordinate_frame': 'camRect0',
                'coordinate_limit': 'Boxes from rotation-only projected RGB; physical cross-camera parallax remains',
                'unverified_frame_policy': 'UNKNOWN_NO_EXTRAPOLATION', 'frames': []}
    sheets = {}
    for sequence in ('zurich_city_04_e', 'zurich_city_04_b'):
        calib_path = ROOT / f'data/raw/{sequence}/calibration/cam_to_cam.yaml'
        calibration = yaml.safe_load(calib_path.read_text())
        hashes[str(calib_path.relative_to(ROOT))] = sha256_file(calib_path)
        h = rgb_to_event_homography(calibration)
        times_path = ROOT / f'data/raw/dsec_mod/{sequence}_image_timestamps.txt'
        times = np.loadtxt(times_path, dtype=np.int64)
        exposures = np.loadtxt(ROOT / f'data/raw/dsec_mod/alignment/{sequence}/image_exposure_timestamps_left.txt',
                               delimiter=',', dtype=np.int64)
        baseline = float(np.linalg.norm(np.asarray(calibration['extrinsics']['T_10'])[:3, 3]))
        report['geometry'][sequence] = {'rgb_rect1_to_event_rect0_H': h.tolist(),
                                        'rgb_event_camera_translation_m': baseline,
                                        'box_to_rectified_detector_coordinates': 'identity_on_sample_verified_grid'}
        sheet = Image.new('RGB', (1920, 3*520), '#101c29'); draw = ImageDraw.Draw(sheet)
        mapping_path = ROOT / f'data/raw/{sequence}/events_left/rectify_map.h5'
        mapping = load_rectify_map(mapping_path)
        hashes[str(mapping_path.relative_to(ROOT))] = sha256_file(mapping_path)
        with DSECReader(ROOT / f'data/raw/{sequence}/events_left/events.h5') as reader:
            for row, frame in enumerate((1, 134, 267)):
                mod_path = ROOT / f'data/raw/dsec_mod/{sequence}/rgb_calib/{frame:06d}.png'
                mod = cv2.imread(str(mod_path)); candidates = []
                for index in range(max(0, frame-1), min(len(times), frame+3)):
                    original = cv2.imread(str(ROOT / f'data/raw/dsec_mod/alignment/{sequence}/{index:06d}.png'))
                    score, _ = compare_projected_rgb(original, mod, h)
                    candidates.append({'dsec_index': index, **score})
                chosen = select_verified_frame(candidates)
                timing = verified_timestamp(times, exposures, chosen['dsec_index'])
                entry = {'sequence': sequence, 'mod_frame': frame, **chosen, **timing, 'candidates': candidates}
                report['frames'].append(entry)
                original = cv2.imread(str(ROOT / f'data/raw/dsec_mod/alignment/{sequence}/{chosen["dsec_index"]:06d}.png'))
                _, warped = compare_projected_rgb(original, mod, h)
                t = timing['timestamp_us']
                if t-20000 < reader.first_us or t > reader.last_us:
                    raise ValueError('Incomplete event window')
                events, dropped = rectify_events(reader.window(t-20000, t), mapping)
                counts = np.zeros((480, 640), np.uint32)
                np.add.at(counts, (events['y'], events['x']), 1)
                gray = np.rint(np.clip(np.log1p(counts)/np.log(21), 0, 1)*255).astype(np.uint8)
                event_image = Image.fromarray(gray).convert('RGB')
                boxes = annotations[sequence]['frames'][frame-1]['boxes']
                panels = [Image.fromarray(cv2.cvtColor(mod, cv2.COLOR_BGR2RGB)),
                          Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)), event_image]
                for panel in panels:
                    painter = ImageDraw.Draw(panel)
                    for box in boxes: painter.rectangle(box['xyxy'], outline='#ffc400', width=2)
                y = row*520
                captions = [f'MOD {frame} | released Moving boxes',
                            f'DSEC {chosen["dsec_index"]} projected | MAE {chosen["mae_8bit"]:.3f}/255',
                            f'Rectified activity [t-20ms,t) | t={t} us | NOT predictions']
                for col, (panel, caption) in enumerate(zip(panels, captions)):
                    draw.text((col*640+8, y+8), caption, fill='white')
                    sheet.paste(panel, (col*640, y+40))
                manifest['frames'].append({'sequence': sequence, 'mod_frame': frame,
                    'dsec_image_index': chosen['dsec_index'], **timing, 'boxes': boxes,
                    'reference_source': 'DSEC-MOD published Moving annotations',
                    'temporal_onset_ground_truth': False,
                    'event_window_start_us': t-20000, 'event_window_end_us_exclusive': t,
                    'rendered_event_count': len(events['x']), 'out_of_rectified_view_events': dropped})
        sheets[sequence] = sheet
    report['input_hashes'] = hashes
    sources = ['scripts/audit_mod_alignment.py', 'src/pfe_events/mod_alignment.py',
               'src/pfe_events/dsec.py', 'src/pfe_events/artifacts.py', 'src/pfe_events/http_range.py']
    report['source_hashes'] = {name: sha256_file(ROOT / name) for name in sources}
    args.output.mkdir(parents=True)
    for sequence, sheet in sheets.items(): sheet.save(args.output / (sequence+'_alignment.png'))
    write_json(args.output / 'report.json', report)
    write_json(args.output / 'verified_sample.json', manifest)
    for entry in report['frames']:
        print(entry['sequence'], entry['mod_frame'], '->', entry['dsec_index'],
              'MAE', round(entry['mae_8bit'], 4), 'margin', round(entry['margin_8bit'], 4))


if __name__ == '__main__': main()
