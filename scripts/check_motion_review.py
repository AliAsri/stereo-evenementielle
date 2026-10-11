"""Validate a manual M13 review without deriving any quality metric."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pfe_events.motion_review import validate_review

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('annotations',type=Path)
    parser.add_argument('--manifest',type=Path,default=ROOT/'outputs/motion/M13/review_manifest.json')
    args=parser.parse_args()
    print(json.dumps(validate_review(json.loads(args.manifest.read_text(encoding='utf-8')),
                                    json.loads(args.annotations.read_text(encoding='utf-8'))),indent=2))
