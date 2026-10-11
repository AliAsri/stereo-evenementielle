"""Describe spatial persistence of saved proposals; never assign object identities."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlap(a, b):
    """Set intersection / union, undefined for two empty masks."""
    union = int(np.count_nonzero(a | b))
    return float(np.count_nonzero(a & b) / union) if union else None


def masks(regions, points):
    boxes = np.zeros((480, 640), bool)
    cells = np.zeros((15, 20), bool)
    for region in regions:
        x1, y1, x2, y2 = region['xyxy']
        assert 0 <= x1 < x2 <= 640 and 0 <= y1 < y2 <= 480
        boxes[y1:y2, x1:x2] = True
        ids = region['point_indices']
        assert len(ids) == region['support_points'] >= 3
        p = points[ids]
        assert np.isfinite(p).all() and np.all(p >= 0) and np.all(p < [640, 480])
        xy = (p // 32).astype(int)
        cells[xy[:, 1], xy[:, 0]] = True
    return boxes, cells


def summarize(values):
    finite = [v for v in values if v is not None]
    return dict(min=float(min(finite)), median=float(np.median(finite)), max=float(max(finite))) if finite else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Fresh output directory')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh output directory')
    source = ROOT / 'outputs/focused_truck/integrated_03'
    regions_path = ROOT / 'outputs/focused_truck/viewer_02/regions.json'
    region_data = json.loads(regions_path.read_text())
    summary_path = source / 'summary.json'
    summary = json.loads(summary_path.read_text())
    records = {row['timestamp_us']: row for row in summary['frames']}
    files = {json.loads(p.read_text())['timestamp_us']: p for p in source.glob('[0-9]*.json')}
    manifest_path = ROOT / 'outputs/focused_truck/viewer_02/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    # Refuse silently changed source predictions used to build the zones.
    for name, expected in manifest['input_sha256'].items():
        if name.startswith('outputs'):
            assert digest(ROOT / name) == expected, name
    assert len(region_data['frames']) == len(summary['frames']) == 17
    report = dict(status='DESCRIPTIVE_SPATIAL_STABILITY',
        source='viewer_02/regions.json + integrated_03',
        method=dict(box_overlap='IoU of union of all proposal rectangles, half-open pixel bounds',
                    cell_overlap='IoU of occupied 32 px cells of grouped residual points, WITHOUT dilation',
                    temporal_comparison='Consecutive outputs, no coordinate warping or point/zone identity association'),
        limitations=['Image-space persistence is not physical motion or object tracking.',
                     'Large merged rectangles can inflate overlap; their filled interior is not an object mask.',
                     'Grid overlap depends on fixed cell boundaries and excludes ungrouped residual points.',
                     'Overlapping 100 ms pairs and 50 ms images are not independent observations.',
                     'No mobility ground truth, precision, recall or false-alarm rate is measured.'],
        input_sha256={str(p.relative_to(ROOT)): digest(p) for p in (regions_path, summary_path, manifest_path)},
        script_sha256=digest(Path(__file__)), frames=[], transitions=[])
    previous = None
    images = []
    for i, frame in enumerate(region_data['frames']):
        timestamp = frame['timestamp_us']
        assert timestamp == summary['frames'][i]['timestamp_us']
        row = records[timestamp]
        path = files[timestamp].with_suffix('.npz')
        report['input_sha256'][str(path.relative_to(ROOT))] = digest(path)
        with np.load(path, allow_pickle=False) as arrays:
            boxes, cells = masks(frame['regions'], arrays['current'])
            images.append(arrays['rectified'].copy())
            for region in frame['regions']:
                assert row['motion_model']['valid']
                assert all(row['motion_model']['residual_px'][j] > 3 for j in region['point_indices'])
        assert len({j for r in frame['regions'] for j in r['point_indices']}) == sum(r['support_points'] for r in frame['regions'])
        report['frames'].append(dict(image=i+1, timestamp_us=timestamp, offset_ms=row['offset_ms'],
            region_count=len(frame['regions']), grouped_points=sum(r['support_points'] for r in frame['regions']),
            occupied_cells=int(cells.sum()), union_box_area_px=int(boxes.sum()),
            union_box_area_percent=float(100*boxes.mean())))
        if previous is not None:
            old_time, old_boxes, old_cells = previous
            assert timestamp-old_time == summary['step_us'] == 20000
            report['transitions'].append(dict(from_image=i, to_image=i+1,
                box_union_iou=overlap(old_boxes, boxes), occupied_cell_iou=overlap(old_cells, cells)))
        previous = timestamp, boxes, cells
    report['statistics'] = dict(
        frames=len(report['frames']), transitions=len(report['transitions']),
        box_union_iou=summarize([r['box_union_iou'] for r in report['transitions']]),
        occupied_cell_iou=summarize([r['occupied_cell_iou'] for r in report['transitions']]),
        union_box_area_percent=summarize([r['union_box_area_percent'] for r in report['frames']]))
    # Illustrations selected reproducibly: largest drop (lowest overlap), and final frame.
    worst = min(report['transitions'], key=lambda t: t['box_union_iou'])
    slots = [worst['from_image']-1, worst['to_image']-1, 16]
    report['illustrated_frames'] = [i+1 for i in slots]
    canvas = Image.new('RGB', (1440, 1140), '#0d1724')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
    title = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 28)
    draw.text((24, 18), 'Les zones réapparaissent, mais leur localisation varie', font=title, fill='white')
    draw.text((24, 60), '17 images · pas de 20 ms · mêmes paramètres · cadres candidats, sans identité ni mobilité confirmée', font=font, fill='#c2d1df')
    for slot, idx in enumerate(slots):
        x = 24+slot*472
        frame = report['frames'][idx]
        draw.text((x, 106), f"Image {idx+1} · {frame['offset_ms']:.0f} ms · {frame['region_count']} zone(s)", font=font, fill='white')
        picture = Image.fromarray(images[idx]).convert('RGB')
        ink = ImageDraw.Draw(picture)
        for r in region_data['frames'][idx]['regions']:
            x1,y1,x2,y2 = r['xyxy']
            ink.rectangle((x1,y1,x2-1,y2-1), outline='#ffb634', width=3)
        canvas.paste(picture.resize((448,336)), (x,140))
        draw.text((x,487), f"Cadres : {frame['union_box_area_percent']:.1f} % de l'image", font=small, fill='#ffd17a')
    draw.text((24,535), 'Toutes les dates : surface des cadres et recouvrement avec la date précédente', font=font, fill='white')
    headings = ['Image', 'Décalage', 'Zones', 'Points regroupés', 'Surface cadres', 'IoU cadres', 'IoU cellules']
    columns = [30,140,300,425,665,925,1160]
    for x,label in zip(columns,headings):
        draw.text((x,578),label,font=small,fill='#75d8f3')
    for i,frame in enumerate(report['frames']):
        y = 612+i*24
        trans = report['transitions'][i-1] if i else None
        values = [str(i+1), f"{frame['offset_ms']:.0f} ms",str(frame['region_count']),str(frame['grouped_points']),
                  f"{frame['union_box_area_percent']:.1f} %",
                  f"{trans['box_union_iou']:.2f}" if trans else '—',
                  f"{trans['occupied_cell_iou']:.2f}" if trans else '—']
        if i%2==0:
            draw.rectangle((24,y-1,1414,y+22),fill='#172b3e')
        for x,value in zip(columns,values):
            draw.text((x,y),value,font=small,fill='white')
    draw.text((24,1036), 'IoU = intersection / union : 1 = même emprise, 0 = aucune intersection. Ce n’est pas une précision de détection.', font=small, fill='#c2d1df')
    draw.text((24,1064), 'Cellules : grille 32 px des points regroupés, sans dilatation. Des cadres larges peuvent masquer un changement des points.', font=small, fill='#c2d1df')
    draw.text((24,1092), 'Pas de compensation entre images ni suivi d’identité. Les intervalles se recouvrent ; aucune qualité de mobilité mesurée.', font=small, fill='#ffd17a')
    args.output.mkdir(parents=True)
    canvas.save(args.output/'comparison.png')
    report['figure_sha256'] = digest(args.output/'comparison.png')
    (args.output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(statistics=report['statistics'],worst_transition=worst,illustrated_frames=report['illustrated_frames']),indent=2))


if __name__ == '__main__':
    main()
