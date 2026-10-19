"""Read frozen M17/100 ms outputs against six qualified MOS masks; no inference.

Positive-mask association is provisional under RGB/event parallax. Zero and
out-of-crop pixels are unknown, never certified static negatives.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from pfe_events.artifacts import write_json

ARCHIVES = {
    'historical_20ms': ('outputs/motion/M17', 20000),
    'saved_100ms_border': ('outputs/demo_border_20261015/reference', 100000),
}


def mask_strata(points, mask):
    """Nearest pixel floor(x+.5); the unlabelled 40 rows remain unknown.

    A positive boundary pixel has an opposite/unknown pixel in its 3x3
    neighbourhood. This flag is descriptive, not a bound on parallax.
    """
    points = np.asarray(points)
    if (points.ndim != 2 or points.shape[1:] != (2,)
            or not np.isfinite(points).all() or np.any(points < 0)
            or np.any(points >= [640,480])
            or mask.shape != (440,640) or mask.dtype != bool):
        raise ValueError('Finite in-frame Nx2 points and native boolean 440x640 mask required')
    xy = np.floor(points+.5).astype(int)
    covered = (xy[:,0] < 640) & (xy[:,1] < 440)
    positive = np.zeros(len(points),bool)
    positive[covered] = mask[xy[covered,1],xy[covered,0]]
    interior = mask.copy()
    padded = np.pad(mask,1,constant_values=False)
    for y in range(3):
        for x in range(3): interior &= padded[y:y+440,x:x+640]
    boundary = np.zeros(len(points),bool)
    ids = np.flatnonzero(positive)
    boundary[ids] = ~interior[xy[ids,1],xy[ids,0]]
    return dict(positive_mask_provisional=positive,
                zero_mask_unknown=covered & ~positive,
                outside_mask_unknown=~covered,
                positive_boundary_3x3=boundary)


def numbers(values):
    values = np.asarray(values,dtype=float)
    values = values[np.isfinite(values)]
    return dict(count=len(values),median_px=float(np.median(values)) if len(values) else None,
                p95_px=float(np.percentile(values,95)) if len(values) else None,
                max_px=float(values.max()) if len(values) else None)


def support(previous, current, depth, model, mask):
    previous,current,depth = map(np.asarray,(previous,current,depth))
    strata = mask_strata(current,mask)
    n = len(current)
    if (previous.shape != current.shape or depth.shape != (n,)
            or not np.isfinite(previous).all() or len(model['point_status']) != n):
        raise ValueError('Matching saved correspondences, depths and model statuses required')
    residual = np.array([np.nan if x is None else x for x in model.get('residual_px',[None]*n)],float)
    status = np.asarray(model['point_status'])
    if residual.shape != (n,): raise ValueError('One residual entry per track required')
    usable_depth = np.isfinite(depth) & (depth > 0)
    evaluated = (np.isfinite(residual) & usable_depth & bool(model['valid'])
                 & np.isin(status,('MODEL_CONSISTENT','RESIDUAL_CANDIDATE')))
    if np.any(np.isfinite(residual) != evaluated):
        raise ValueError('Finite residuals must agree with evaluated depth/model statuses')
    if np.any(np.isin(status,('MODEL_CONSISTENT','RESIDUAL_CANDIDATE')) != evaluated):
        raise ValueError('Classified points must have a finite evaluated residual')
    if int(evaluated.sum()) != model.get('evaluated_points',0):
        raise ValueError('Saved evaluated-point count differs from arrays')
    raw = np.linalg.norm(current-previous,axis=1)
    result = {}
    for key, select in strata.items():
        common = select & evaluated
        result[key] = dict(tracks=int(select.sum()),usable_depth=int((select & usable_depth).sum()),
            evaluated=int(common.sum()),abstentions=int((select & ~evaluated).sum()),
            residual_candidates=int((select & (status=='RESIDUAL_CANDIDATE')).sum()),
            c0_displacement_all_tracks=numbers(raw[select]),
            c0_displacement_common_points=numbers(raw[common]),
            c1_residual_common_points=numbers(residual[common]))
    return result,strata,residual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Fresh output directory')
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh output directory')
    hashes = {}
    def checked(path,expected=None):
        path = ROOT/path
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected is not None and actual != expected: raise ValueError(f'Input hash differs: {path}')
        hashes[path.relative_to(ROOT).as_posix()] = actual
        return path
    qualification = json.loads(checked('outputs/dsec_mos_reference_20261018/qualification.json').read_text())
    acquisition = json.loads(checked('outputs/dsec_mos_reference_20261018/acquisition_selected.json',
                         qualification['acquisition_manifest_sha256']).read_text())
    for entry in acquisition['files']:
        path = checked(entry['path'],entry['sha256'])
        if path.stat().st_size != entry['bytes']: raise ValueError('Acquired input size differs')
    ref_path = 'outputs/motion/M16/audit/verified_sample.json'
    reference = json.loads(checked(ref_path,qualification['inputs_sha256'][ref_path]).read_text())
    qualified = {(r['sequence'],r['frame']):r for r in qualification['frames']}
    assert len(qualified) == len(reference['frames']) == 6
    reports,panels = {},[]
    for label,(folder,interval) in ARCHIVES.items():
        summary = json.loads(checked(f'{folder}/summary.json').read_text())
        # These archives freeze different stereo versions as well as intervals.
        # Preserve both provenance maps; do not attribute differences to interval alone.
        archived_sources = {}
        for name,expected in summary['source_sha256'].items():
            if name.replace('\\','/') == ref_path:
                checked(ref_path,expected)
            source = ROOT/folder/'sources'/name
            if source.is_file():
                checked(source,expected)
                archived_sources[name] = expected
        if len(archived_sources) != len(summary['source_sha256']):
            raise ValueError('Missing frozen source snapshot')
        original_rows = {r['id']:r for r in summary['frames']}
        frames = []
        for ref in reference['frames']:
            seq,num = ref['sequence'],ref['mod_frame']
            q = qualified[(seq,num)]
            assert q['exact_vertical_offsets'] == [0] and q['timestamp_us'] == ref['timestamp_us']
            stem = f'{seq}_{num:06d}'
            inference = json.loads(checked(f'{folder}/{stem}_inference.json').read_text())
            assert inference == original_rows[stem]['inference']
            assert inference['current_us'] == ref['timestamp_us']
            assert inference['current_us']-inference['previous_us'] == interval
            assert inference['depth_us'] == inference['previous_us']
            array_path = checked(f'{folder}/{stem}.npz')
            with np.load(array_path,allow_pickle=False) as a:
                previous,current,depth = (a[k].copy() for k in ('previous','current','depth_samples'))
                counts = a['current_counts'].copy()
                assert counts.shape == (480,640) and np.isfinite(counts).all() and np.all(counts>=0)
            mask_path = ROOT/'data/raw/dsec_mos_sample_20261018'/seq/'gt_mask'/f'{num:06d}.png'
            rgb_path = mask_path.parent.parent/'image_calib'/mask_path.name
            with Image.open(mask_path) as im:
                if im.mode != '1': raise ValueError('Expected native 1-bit mask')
                mask = np.array(im)
            result,strata,residual = support(previous,current,depth,inference['rigid'],mask)
            partition_counts = [result[key]['tracks'] for key in
                ('positive_mask_provisional','zero_mask_unknown','outside_mask_unknown')]
            assert sum(partition_counts) == len(current)
            frames.append(dict(sequence=seq,frame=num,timestamp_us=ref['timestamp_us'],interval_us=interval,
                saved_inference_status=inference['status'],saved_model_status=inference['rigid']['status'],
                all_tracks=len(current),mask_nonzero_pixels=int(mask.sum()),
                active_pixels_in_mask=int((counts[:440][mask]>0).sum()),strata=result))
            with Image.open(rgb_path) as im: rgb=np.array(im.convert('RGB'))
            overlay=rgb.copy();overlay[mask]=np.rint(.65*rgb[mask]+.35*np.array([0,255,70])).astype(np.uint8)
            panel=Image.new('RGB',(640,480),(17,27,39));panel.paste(Image.fromarray(overlay),(0,40))
            draw=ImageDraw.Draw(panel)
            positive=result['positive_mask_provisional']
            draw.text((8,4),f'{label} {seq} / {num} | saved results, not new inference',fill='white')
            draw.text((8,20),f"mask: tracks {positive['tracks']} depth {positive['usable_depth']} eval {positive['evaluated']} residual candidates {positive['residual_candidates']}",fill='#ffdb56')
            for index,(x,y) in enumerate(current):
                if y >= 440: continue
                fill=('#ff4040' if np.isfinite(residual[index]) and residual[index]>3 else
                      '#00ddff' if strata['positive_mask_provisional'][index] else '#b0b0b0')
                draw.ellipse((x-2,y+38,x+2,y+42),fill=fill)
            panels.append((label,seq,num,panel))
        totals = {key:{metric:sum(f['strata'][key][metric] for f in frames)
                      for metric in ('tracks','usable_depth','evaluated','abstentions','residual_candidates')}
                  for key in frames[0]['strata']}
        reports[label]=dict(archive=folder,interval_us=interval,frames=frames,totals=totals,
            insufficient_history_frames=sum(f['saved_inference_status']=='INSUFFICIENT_HISTORY' for f in frames),
            saved_source_sha256=summary['source_sha256'],verified_available_source_snapshots=archived_sources)
    # One exact common date links the 100 ms archive to the current integrated output.
    archive=ROOT/ARCHIVES['saved_100ms_border'][0]
    current_path='outputs/motion_publication_20261018/after/400000.npz'
    with np.load(checked(current_path),allow_pickle=False) as a, np.load(
            archive/'zurich_city_04_b_000134.npz',allow_pickle=False) as b:
        for key in ('previous','current','depth_samples'): np.testing.assert_array_equal(a[key],b[key])
    current_row=json.loads(checked('outputs/motion_publication_20261018/after/400000.json').read_text())
    old=json.loads((archive/'zurich_city_04_b_000134_inference.json').read_text())
    assert current_row['motion_model'] == old['rigid']
    assert current_row['timestamp_us'] == old['current_us']
    args.output.mkdir(parents=True)
    preview=Image.new('RGB',(1280,6*480+45),(17,27,39))
    ImageDraw.Draw(preview).text((8,8),'Green: MOS reference; cyan: mask-associated saved track; red: residual >3 px, UNCONFIRMED. Zero-mask area is not certified static.',fill='white')
    for i,ref in enumerate(reference['frames']):
        for col,label in enumerate(ARCHIVES):
            panel=next(p for l,s,n,p in panels if (l,s,n)==(label,ref['sequence'],ref['mod_frame']))
            preview.paste(panel,(col*640,45+i*480))
    preview.save(args.output/'mask_support.png')
    write_json(args.output/'summary.json',dict(status='SAVED_RESULTS_MASK_SUPPORT_ONLY',
        groups=reports,input_sha256=hashes,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        current_demo_common_date_exact=True,comparison='Two historical configurations, not an isolated interval ablation',
        inference_runs=0,mobility_precision=None,mobility_recall=None,roc_auc=None,
        sampling='Nearest pixel floor(x+.5); rows 440:480 unknown; no mask resizing/padding',
        limits=['Positive association provisional under RGB/event parallax and mask uncertainty',
            'Zero-mask regions are not certified physical static negatives',
            'Native 3x3 boundary flag is descriptive, not a parallax margin',
            'Mask components and track occurrences are not distinct object identities',
            'All six dates are development, no independent test or onset labels']))
    for label,item in reports.items(): print(label,item['totals']['positive_mask_provisional'])


if __name__=='__main__': main()
