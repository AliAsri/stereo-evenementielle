"""Inventory reviewed ROI annotations; no automatic labels or accuracy claims."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from pfe_events.motion_evaluation import evaluate_annotations


def readiness(manifest, annotations, predictions):
    if annotations.get('target') != manifest['target']:
        raise ValueError('Annotation target must match the clip manifest')
    evaluation = evaluate_annotations(manifest, annotations, predictions)
    # Exact duplicate reviews would inflate an eventual sample count.
    seen = set()
    for annotation in annotations['annotations']:
        if annotation['reviewed'] and annotation['kind'] in ('onset', 'negative'):
            key = json.dumps([annotation['clip_id'], annotation['kind'], annotation['roi_xyxy'],
                              annotation.get('onset_interval_us'), annotation['annotator']], sort_keys=True)
            if key in seen: raise ValueError('Duplicate reviewed annotation; resolve before evaluation')
            seen.add(key)
    inventory = []
    for clip in manifest['clips']:
        selected = [r for r in evaluation['results'] if r['clip_id'] == clip['id']]
        excluded = [r for r in evaluation['excluded_annotations'] if r['clip_id'] == clip['id']]
        kinds = Counter(r['kind'] for r in selected)
        inventory.append({'clip_id': clip['id'], 'split': clip['split'],
                          'reviewed_onsets': kinds['onset'], 'reviewed_negative_rois': kinds['negative'],
                          'excluded': len(excluded), 'missing_annotation': not selected,
                          'onset_output_statuses': dict(Counter(r['status'] for r in selected if r['kind'] == 'onset'))})
    return {'status': 'ANNOTATIONS_PRESENT_REVIEW_COVERAGE' if evaluation['results'] else 'PENDING_REVIEWED_ANNOTATIONS',
            'scope': 'Inventory only. Counts do not establish sample adequacy, motion GT quality or object recall.',
            'reviewed_eligible_rois': len(evaluation['results']),
            'excluded_annotations': evaluation['excluded_annotations'], 'clips': inventory,
            'warning': 'Overlapping ROIs and multiple annotators must not be pooled; adjudicate first.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=ROOT/'outputs/motion/M03')
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a new inventory output')
    manifest_path = args.run/'annotation_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    annotations = (json.loads(args.annotations.read_text(encoding='utf-8-sig')) if args.annotations else
                   {'schema': manifest['schema'], 'target': manifest['target'], 'annotations': []})
    root = args.run.resolve(); predictions = {}; sources = [manifest_path, Path(__file__),
        ROOT/'src/pfe_events/motion_evaluation.py', ROOT/'configs/motion_protocol_v1.json']
    if args.annotations: sources.append(args.annotations)
    for clip in manifest['clips']:
        path = (root/'clips'/clip['id']/'predictions.json').resolve()
        if not path.is_relative_to(root/'clips'): raise ValueError('Clip path outside run')
        predictions[clip['id']] = json.loads(path.read_text(encoding='utf-8')); sources.append(path)
    report = readiness(manifest, annotations, predictions)
    report['annotation_input'] = str(args.annotations) if args.annotations else 'NONE_PROVIDED'
    report['sha256'] = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(report, file, indent=2); file.write('\n')
    print(report['status'], report['reviewed_eligible_rois'], 'eligible ROI(s)')


if __name__ == '__main__': main()
