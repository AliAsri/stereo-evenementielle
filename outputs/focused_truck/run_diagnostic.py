"""One short train clip, existing M17 inference, fixed inspection region.

No new detector, no propagated reference labels, no parameter search.
Run from any directory; --output must name a fresh directory.
"""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import runpy
import shutil
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from pfe_events.artifacts import sha256_file, write_json
from pfe_events.dsec import load_rectify_map
from pfe_events.dsec_cached import CachedIndexedDSECReader
from pfe_events.geometry import audit_calibration
from pfe_events.stereo import StereoConfig


def finite_stats(values):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    return {'count': len(a), 'median': float(np.median(a)) if len(a) else None,
            'max': float(a.max()) if len(a) else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh output directory')
    reference = json.loads((ROOT / 'outputs/motion/M16/audit/verified_sample.json').read_text())
    frame, = [f for f in reference['frames'] if f['sequence'] == 'zurich_city_04_b' and f['mod_frame'] == 134]
    box, = [b for b in frame['boxes'] if b['tube_index'] == 11]
    historical = json.loads((ROOT / 'outputs/motion/M17/summary.json').read_text())
    normalizer = json.loads((ROOT / 'outputs/stereo/S01/normalizer.json').read_text())
    for name, digest in historical['source_sha256'].items():
        if name.startswith('src/'):
            assert sha256_file(ROOT / name) == digest, name
    assert normalizer['source_split'] == 'train'
    # Reuse the existing function without running its CLI or changing its algorithms.
    infer_pair = runpy.run_path(str(ROOT / 'scripts/run_reference_diagnostic.py'))['infer_pair']
    folder = ROOT / 'data/raw' / frame['sequence']
    calib_path = folder / 'calibration/cam_to_cam.yaml'
    calibration = audit_calibration(calib_path)
    assert calibration['canonical_equal_intrinsics']
    paths = [folder / f'events_{s}/events.h5' for s in ('left', 'right')]
    map_paths = [folder / f'events_{s}/rectify_map.h5' for s in ('left', 'right')]
    maps = [load_rectify_map(p) for p in map_paths]
    args.output.mkdir(parents=True)
    source_paths = [Path(__file__), ROOT / 'scripts/run_reference_diagnostic.py',
                    ROOT / 'outputs/motion/M16/audit/verified_sample.json',
                    ROOT / 'outputs/stereo/S01/normalizer.json']
    source_paths += [ROOT / n for n in historical['source_sha256'] if n.startswith('src/')]
    report = {'status': 'RUNNING', 'sequence': frame['sequence'], 'anchor_timestamp_us': frame['timestamp_us'],
              'reference_box_valid_only_at_anchor': box, 'window_us': 50000, 'step_us': 20000,
              'clip_duration_us': 400000, 'source_sha256': {}, 'input_sha256': {}, 'frames': [],
              'region_policy': 'Fixed inspection rectangle, reference only at anchor; no interpolated labels or object tracking',
              'claim': 'Train diagnostic; no measured object precision, recall, onset delay or live throughput'}
    for path in source_paths:
        name = path.relative_to(ROOT).as_posix()
        report['source_sha256'][name] = sha256_file(path)
        dest = args.output / 'sources' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    for path in [calib_path, *paths, *map_paths]:
        name = path.relative_to(ROOT).as_posix()
        report['input_sha256'][name] = sha256_file(path)
        assert report['input_sha256'][name] == historical['input_sha256'][name]
    cv2.setNumThreads(1)
    font_path = Path('C:/Windows/Fonts/arial.ttf')
    font = ImageFont.truetype(str(font_path), 17) if font_path.exists() else ImageFont.load_default()
    small = ImageFont.truetype(str(font_path), 14) if font_path.exists() else font
    views = []
    x1, y1, x2, y2 = map(int, box['xyxy'])
    try:
        with ExitStack() as stack:
            readers = [stack.enter_context(CachedIndexedDSECReader(p)) for p in paths]
            for offset in range(-400000, 1, 20000):
                end = frame['timestamp_us'] + offset
                arrays, inf = infer_pair(*readers, maps, calibration, normalizer, end, 50000, 20000, StereoConfig())
                p, q = arrays['previous'], arrays['current']
                inside = (q[:, 0] >= x1) & (q[:, 0] < x2) & (q[:, 1] >= y1) & (q[:, 1] < y2)
                residual = np.asarray([np.nan if x is None else x for x in inf['rigid']['residual_px']])
                predicted = np.asarray([v if v is not None else [np.nan, np.nan] for v in inf['rigid']['predicted_pixels']]).reshape(-1, 2)
                row = {'offset_ms': offset/1000, 'timestamp_us': end, 'reference_valid': offset == 0,
                       'tracks_in_fixed_region': int(inside.sum()),
                       'depth_in_fixed_region': int(np.isfinite(arrays['depth_samples'][inside]).sum()),
                       'candidates_in_fixed_region': int(np.count_nonzero(residual[inside] > 3)),
                       'residual_px': finite_stats(residual[inside]),
                       'observed_displacement_px': finite_stats(np.linalg.norm(q[inside]-p[inside], axis=1)),
                       'model_displacement_px': finite_stats(np.linalg.norm(predicted[inside]-p[inside], axis=1)),
                       'depth_m': finite_stats(arrays['depth_samples'][inside]),
                       'rigid_status': inf['rigid']['status'], 'pipeline_cpu_ms': inf['timing_ms']['pipeline']}
                report['frames'].append(row)
                stem = f'{offset+400000:06d}'
                np.savez_compressed(args.output / (stem+'.npz'), **arrays)
                write_json(args.output / (stem+'_inference.json'), inf)
                if offset == 0:
                    old = ROOT / 'outputs/motion/M17/zurich_city_04_b_000134.npz'
                    with np.load(old, allow_pickle=False) as saved:
                        assert set(arrays) == set(saved.files)
                        assert all(np.array_equal(v, saved[k], equal_nan=True) for k, v in arrays.items())
                    old_inf = json.loads((old.parent / (old.stem+'_inference.json')).read_text())
                    assert {k:v for k,v in inf.items() if k != 'timing_ms'} == {k:v for k,v in old_inf.items() if k != 'timing_ms'}
                    report['anchor_reproduces_M17_exactly_except_timing'] = True
                scene = Image.fromarray(arrays['current_image']).convert('RGB')
                painter = ImageDraw.Draw(scene)
                for (x, y), status in zip(q, inf['rigid']['point_status']):
                    color = {'UNKNOWN':'#aaaaaa','MODEL_CONSISTENT':'#42dfae','RESIDUAL_CANDIDATE':'#ffbd30'}[status]
                    painter.ellipse((x-1, y-1, x+1, y+1), fill=color)
                painter.rectangle((x1,y1,x2,y2), outline='#37c9ff', width=2)
                panel = Image.new('RGB', (1000, 680), '#102030'); draw = ImageDraw.Draw(panel)
                draw.text((12,10), 'CAMION | un extrait, une configuration | rejeu de donnees enregistrees', font=font, fill='white')
                label = 'REFERENCE PUBLIEE' if offset == 0 else 'ZONE FIXE D\'INSPECTION, PAS UNE ANNOTATION A CETTE DATE'
                draw.text((12,38), f'{offset/1000:+.0f} ms | {label}', font=small, fill='#37c9ff')
                panel.paste(scene, (0,70))
                crop = scene.crop((x1,y1,x2,y2)).resize((350,350), Image.Resampling.NEAREST)
                panel.paste(crop,(645,70))
                draw.text((654,435), f"1. Suivi : {row['tracks_in_fixed_region']} points",font=font,fill='white')
                draw.text((654,463), f"2. Profondeur : {row['depth_in_fixed_region']} points",font=font,fill='white')
                draw.text((654,491), f"3. Residus > 3 px : {row['candidates_in_fixed_region']}",font=font,fill='white')
                med = row['residual_px']['median']; maximum = row['residual_px']['max']
                detail = f'Residu median {med:.3f} px | max {maximum:.3f} px' if med is not None else 'Residus inconnus : support insuffisant'
                draw.text((12,566), detail, font=font, fill='white')
                draw.text((12,599), 'Vert : compatible avec le modele | Gris : inconnu | Orange : candidat, mobilite non prouvee',font=small,fill='white')
                draw.text((12,629), 'La zone contient aussi du fond. Une absence de residu ne prouve pas un objet immobile.',font=small,fill='#ffce63')
                views.append(panel)
                print(offset, row['tracks_in_fixed_region'], row['depth_in_fixed_region'], row['residual_px'],flush=True)
        views[-1].save(args.output / 'diagnostic.png')
        views[0].save(args.output / 'clip.gif', save_all=True, append_images=views[1:], duration=100, loop=0)
        report['playback'] = '5x slow motion: 20 ms of recorded time per displayed 100 ms; not live processing'
        report['status'] = 'COMPLETE'
    except Exception as error:
        report.update(status='FAILED', error=repr(error))
        raise
    finally:
        write_json(args.output / 'summary.json', report)


if __name__ == '__main__':
    main()
