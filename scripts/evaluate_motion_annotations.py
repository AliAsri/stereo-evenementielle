"""Evaluate reviewed M03 annotations; use a fresh JSON output path."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from pfe_events.motion_evaluation import evaluate_annotations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=ROOT/'outputs/motion/M03')
    parser.add_argument('--annotations', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a new evaluation output')
    manifest_path = args.run/'annotation_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    annotations = json.loads(args.annotations.read_text(encoding='utf-8-sig'))
    paths = [manifest_path, args.annotations, Path(__file__), ROOT/'src/pfe_events/motion_evaluation.py']
    predictions = {}
    run_root = args.run.resolve()
    for clip in manifest['clips']:
        path = (run_root/'clips'/clip['id']/'predictions.json').resolve()
        if not path.is_relative_to(run_root/'clips'):
            raise ValueError('Clip path outside run')
        predictions[clip['id']] = json.loads(path.read_text(encoding='utf-8'))
        paths.append(path)
    report = evaluate_annotations(manifest, annotations, predictions)
    report['sha256'] = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
        file.write('\n')
    print(report['status'], len(report['results']), 'evaluated ROI(s)')


if __name__ == '__main__':
    main()
