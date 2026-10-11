"""Compare archived M05 10 ms and M03 20 ms streams on the same reviewed ROIs."""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from pfe_events.artifacts import sha256_file as digest
from pfe_events.multirate_evaluation import evaluate_multirate

VARIANTS = ('absolute', 'relative', 'relative_history', 'global_residual_20ms')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def compare(manifest, annotations, streams, steps, horizon_us=200_000):
    """Keep original annotation indices even when the input includes other clips."""
    if set(streams) != set(VARIANTS) or set(steps) != set(VARIANTS):
        raise ValueError('All four comparison variants are required')
    known = {c['id'] for c in manifest['clips']}
    selected = set(streams[VARIANTS[0]])
    if not selected or not selected <= known:
        raise ValueError('Comparison clips must exist in the manifest')
    if any(set(s) != selected for s in streams.values()):
        raise ValueError('Variants must cover identical clips')
    subset = deepcopy(manifest)
    subset['clips'] = [c for c in manifest['clips'] if c['id'] in selected]
    if any(c['split'] != 'train' for c in subset['clips']):
        raise ValueError('This comparison is restricted to train clips')
    kept, indices, outside = [], [], []
    for index, annotation in enumerate(annotations['annotations']):
        if annotation['clip_id'] not in known:
            raise ValueError('Unknown annotation clip')
        if annotation['clip_id'] in selected:
            kept.append(annotation); indices.append(index)
        else:
            outside.append({'annotation_index': index, 'clip_id': annotation['clip_id'],
                            'reason': 'OUTSIDE_COMMON_TRAIN_COMPARISON'})
    bundle = dict(annotations, annotations=kept)
    reports = {}
    for variant in VARIANTS:
        report = evaluate_multirate(subset, bundle, streams[variant], steps[variant], horizon_us)
        for row in report['results'] + report['excluded_annotations']:
            row['annotation_index'] = indices[row['annotation_index']]
        report['status_counts'] = dict(Counter(r['status'] for r in report['results']))
        report['measured_prediction_rows'] = sum(not r['warmup'] for rows in streams[variant].values() for r in rows)
        reports[variant] = report
    eligible = len(reports[VARIANTS[0]]['results'])
    summary = {'experiment': 'M06', 'status': 'EVALUATED_REVIEWED_ROIS' if eligible else 'PENDING_ANNOTATIONS',
               'clips': sorted(selected), 'eligible_reviewed_rois': eligible,
               'excluded_outside_comparison': outside, 'aggregate_quality_score': None,
               'scope': 'Per-ROI train diagnostics only; no pooling, parameter selection or generalization claim',
               'timing': 'Recorded event time; CPU, queuing and display excluded',
               'variants': {v: {'status': r['status'], 'status_counts': r['status_counts'],
                    'measured_prediction_rows': r['measured_prediction_rows'],
                    'prediction_steps_us': steps[v]} for v, r in reports.items()}}
    return summary, reports, subset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--m03', type=Path, default=ROOT/'outputs/motion/M03')
    parser.add_argument('--m05', type=Path, default=ROOT/'outputs/motion/M05')
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a new output directory to preserve earlier runs')
    manifest_path = args.m03/'annotation_manifest.json'
    summary_path = args.m05/'summary.json'
    manifest, previous = read(manifest_path), read(summary_path)
    if previous['code_sha256']['outputs/motion/M03/annotation_manifest.json'] != digest(manifest_path):
        raise ValueError('M05 was generated with a different M03 manifest')
    config = read(ROOT/'configs/m06_evaluation.json')
    annotations = read(args.annotations) if args.annotations else {
        'schema': manifest['schema'], 'target': manifest['target'], 'annotations': []}
    streams = {v: {} for v in VARIANTS}; steps = {v: {} for v in VARIANTS}
    sources = [manifest_path, summary_path]
    if args.annotations: sources.append(args.annotations)
    clips = {c['id']: c for c in manifest['clips']}
    for entry in previous['train']:
        cid = entry['clip_id']; clip = clips[cid]
        if (cid in streams['absolute'] or entry['split'] != clip['split'] or
                entry['sequence'] != clip['sequence'] or clip['split'] != 'train'):
            raise ValueError('M03/M05 clip identity mismatch')
        paths = [args.m05/'train'/cid/'predictions.json', args.m03/'clips'/cid/'predictions.json']
        for path, root in zip(paths, [args.m05/'train', args.m03/'clips']):
            if not path.resolve().is_relative_to(root.resolve()): raise ValueError('Unsafe clip path')
        adaptive, global_rows = map(read, paths); sources.extend(paths)
        if sum(not r['warmup'] for r in adaptive) != entry['frames']:
            raise ValueError('M05 summary frame count mismatch')
        for variant in VARIANTS[:-1]:
            streams[variant][cid] = [{'end_us': r['end_us'], 'warmup': r['warmup'],
                                     'motion': r['variants'][variant]} for r in adaptive]
            steps[variant][cid] = previous['config']['real']['step_us']
        streams[VARIANTS[-1]][cid] = global_rows
        steps[VARIANTS[-1]][cid] = clip['step_us']
    summary, reports, subset = compare(manifest, annotations, streams, steps, config['response_horizon_us'])
    code = [Path(__file__), ROOT/'src/pfe_events/artifacts.py', ROOT/'src/pfe_events/multirate_evaluation.py',
            ROOT/'src/pfe_events/motion_evaluation.py', ROOT/'configs/m06_evaluation.json',
            ROOT/'scripts/motion_annotation_v2.html', ROOT/'tests/test_multirate_evaluation.py',
            ROOT/'tests/test_motion_comparison.py']
    sources.extend(code)
    summary.update(utc=datetime.now(timezone.utc).isoformat(), protocol=config,
                   annotation_input=str(args.annotations.resolve()) if args.annotations else 'NONE_PROVIDED',
                   sha256={str(p.resolve()): digest(p) for p in sources})
    # Separate UI data has paths relative to this new package; evaluation source stays untouched.
    ui = deepcopy(subset)
    import os
    for clip in ui['clips']:
        for frame in clip['frames']:
            source = (args.m03/frame['image']).resolve()
            if not source.is_file(): raise FileNotFoundError(source)
            frame['image'] = Path(os.path.relpath(source, args.output.resolve())).as_posix()
    args.output.mkdir(parents=True)
    def save(name, value):
        (args.output/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    save('summary.json', summary)
    for variant, report in reports.items(): save(variant+'.json', report)
    save('annotation_manifest.json', subset)
    save('annotations_input.json', annotations)
    (args.output/'annotation_data.js').write_text('window.ANNOTATION_DATA = '+json.dumps(ui)+';\n', encoding='utf-8')
    shutil.copyfile(ROOT/'scripts/motion_annotation_v2.html', args.output/'annotate.html')
    for path in code:
        target = args.output/'source_snapshot'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    print(summary['status'], len(subset['clips']), 'clips;',
          sum(r['measured_prediction_rows'] for r in reports.values()), 'prediction rows checked')


if __name__ == '__main__': main()
