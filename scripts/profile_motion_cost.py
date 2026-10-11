"""Profile unchanged M02 reader + M01 activity on the final three seconds of M07 train."""
import argparse
import cProfile
import hashlib
import io
import json
from pathlib import Path
import pstats
import sys
import time
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pfe_events.dsec_indexed import IndexedDSECReader
from pfe_events.motion import ActivityDetector
from pfe_events.pilot import unique_file


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/motion/M08_profile')
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh profile directory')
    previous=json.loads((ROOT/'outputs/motion/M07_12s/summary.json').read_text())
    case=next(c for c in previous['cases'] if c['case_id']=='zurich_city_04_b_10ms_r1')
    if case['split']!='train': raise ValueError('Train profiling only')
    start=case['end_us_exclusive']-3000000;stop=case['end_us_exclusive'];step=10000
    source=unique_file(ROOT/'data/raw'/case['sequence']/'events_left','events.h5')
    cv2.setNumThreads(1);detector=ActivityDetector();profiler=cProfile.Profile();rows=[]
    with IndexedDSECReader(source) as reader:
        for begin in range(start-200000,start,step): detector.update(reader.window(begin,begin+step),begin,begin+step)
        profiler.enable()
        for begin in range(start,stop,step):
            before=time.perf_counter_ns();events=reader.window(begin,begin+step);loaded=time.perf_counter_ns()
            result=detector.update(events,begin,begin+step);done=time.perf_counter_ns()
            rows.append({'end_us':begin+step,'events':result['events'],
                         'read_ms':(loaded-before)/1e6,'activity_ms':(done-loaded)/1e6})
        profiler.disable()
    args.output.mkdir(parents=True)
    profiler.dump_stats(str(args.output/'reference.prof'))
    stream=io.StringIO();pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(40)
    (args.output/'profile.txt').write_text(stream.getvalue(),encoding='utf-8')
    report={'status':'COMPLETE_PROFILE_ONLY','sequence':case['sequence'],'split':'train','start_us':start,'end_us_exclusive':stop,
        'step_us':step,'windows':len(rows),'warning':'cProfile overhead included; do not compare these times with unprofiled benchmarks',
        'timing_ms':{k:{'median':float(np.median([r[k] for r in rows])),'total':sum(r[k] for r in rows)} for k in ['read_ms','activity_ms']},
        'sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ['scripts/profile_motion_cost.py','src/pfe_events/dsec_indexed.py','src/pfe_events/dsec.py','src/pfe_events/motion.py','outputs/motion/M07_12s/summary.json']}}
    (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for p in report['sha256']:
        if p.startswith('outputs/'): continue
        target=args.output/'source_snapshot'/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/p).read_bytes())
    print(stream.getvalue());print(json.dumps(report['timing_ms']))


if __name__=='__main__': main()
