"""M08: exact paired equivalence and separate paced runs of cached HDF5 handles."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from functools import partial
from pfe_events.benchmarking import assert_same, save_rows, event_source_path, warm
from pfe_events.dsec_indexed import IndexedDSECReader
from pfe_events.dsec_cached import CachedIndexedDSECReader
from pfe_events.motion import ActivityDetector
from pfe_events.pilot import unique_file
from pfe_events.replay_timing import paced_windows
from pfe_events.reporting import paced_distribution as distribution
from pfe_events.artifacts import write_legacy_json as write_json, sha256_file as digest

source_path = partial(event_source_path, ROOT)

READERS={'indexed':IndexedDSECReader,'cached':CachedIndexedDSECReader}


def paired(case,config,output):
    step=case['step_us'];start=case['start_us'];stop=case['end_us_exclusive']
    rows=[]; stream_hash=hashlib.sha256();checks=0
    detectors={name:ActivityDetector() for name in READERS}
    with ExitStack() as stack:
        readers={name:stack.enter_context(cls(source_path(case))) for name,cls in READERS.items()}
        cache_bytes=readers['cached'].cache_bytes
        # Warm-up outputs are also compared, not just the measured segment.
        for index,begin in enumerate(range(start-config['warmup_us'],stop,step)):
            results={};events={}
            for name in (list(READERS) if index%2==0 else list(reversed(READERS))):
                before=time.perf_counter_ns();events[name]=readers[name].window(begin,begin+step);loaded=time.perf_counter_ns()
                results[name]=detectors[name].update(events[name],begin,begin+step);done=time.perf_counter_ns()
                if begin>=start:
                    rows.append({'end_us':begin+step,'variant':name,'read_ms':(loaded-before)/1e6,
                        'activity_ms':(done-loaded)/1e6,'read_activity_ms':(done-before)/1e6,
                        'events':results[name]['events']})
            assert_same(events['indexed'],events['cached']);assert_same(results['indexed'],results['cached'])
            checks+=1
            for key in ('x','y','t_us','p'): stream_hash.update(events['indexed'][key].tobytes())
        fallbacks={name:r.fallback_windows for name,r in readers.items()}
    ident=f"{case['sequence']}_{step//1000}ms";target=output/'paired'/ident;target.mkdir(parents=True)
    save_rows(target/'windows.csv',rows)
    report={'case_id':ident,'sequence':case['sequence'],'split':'train','step_us':step,
        'start_us':start,'end_us_exclusive':stop,'paired_measured_windows':len(rows)//2,
        'checked_windows_including_warmup':checks,'equivalence':'EXACT_ALL_EVENT_AND_DETECTOR_FIELDS',
        'events_with_warmup_sha256':stream_hash.hexdigest(),'cache_limit_bytes':cache_bytes,
        'fallback_windows':fallbacks,'timing_ms':{name:{key:distribution([r[key] for r in rows if r['variant']==name])
            for key in ('read_ms','activity_ms','read_activity_ms')} for name in READERS}}
    write_json(target/'summary.json',report)
    return report


def paced(case,name,repeat,config,output):
    start=case['start_us'];stop=case['end_us_exclusive'];step=case['step_us'];detector=ActivityDetector()
    with READERS[name](source_path(case)) as reader:
        warm(reader,detector,start,step,config);before=reader.fallback_windows
        rows,status=paced_windows(reader,detector,start,stop-start,step,max_wall_seconds=config['max_wall_seconds_per_case'])
        fallbacks=reader.fallback_windows-before
        cache=getattr(reader,'cache_bytes',None)
    ident=f"{case['sequence']}_{name}_r{repeat}";target=output/'paced'/ident;target.mkdir(parents=True)
    if rows: save_rows(target/'windows.csv',rows)
    report={'case_id':ident,'sequence':case['sequence'],'split':'train','variant':name,'repeat':repeat,
        'step_us':step,'start_us':start,'end_us_exclusive':stop,'run':status,
        'cache_limit_bytes':cache,'fallback_windows':fallbacks,'events':sum(r['events'] for r in rows),
        'timing_ms':{key:distribution([r[key] for r in rows]) for key in
            ('read_ms','activity_ms','read_activity_ms','start_lateness_ms','output_age_after_window_end_ms')},
        'tail_output_age_ms':rows[-1]['output_age_after_window_end_ms'] if rows else None,
        'fraction_completion_past_next_release':float(np.mean([r['completion_past_next_release'] for r in rows])) if rows else None}
    write_json(target/'summary.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/motion/M08')
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a new output directory')
    config=json.loads((ROOT/'configs/m08_cached_reader.json').read_text())
    previous=json.loads((ROOT/config['source_segments']).read_text())
    cases=[c for c in previous['cases'] if c['repeat']==1 and c['sequence'] in config['sequences']
           and c['step_us'] in config['paired_steps_us']]
    if len(cases)!=4 or any(c['split']!='train' for c in cases): raise ValueError('Expected four fixed train cases')
    files=['src/pfe_events/artifacts.py','src/pfe_events/reporting.py','src/pfe_events/benchmarking.py','scripts/benchmark_cached_motion.py','scripts/benchmark_paced_motion.py',
        'src/pfe_events/dsec_cached.py','src/pfe_events/dsec_indexed.py','src/pfe_events/dsec.py',
        'src/pfe_events/motion.py','src/pfe_events/replay_timing.py','src/pfe_events/pilot.py',
        'configs/m08_cached_reader.json','tests/test_dsec_cached.py',config['source_segments']]
    report={'experiment':'M08','status':'RUNNING','utc':datetime.now(timezone.utc).isoformat(),'protocol':config,
        'python':platform.python_version(),'platform':platform.platform(),
        'versions':{p:importlib.metadata.version(p) for p in ('numpy','h5py','opencv-python-headless')},
        'code_sha256':{p:digest(ROOT/p) for p in files},'paired':[],'paced':[],
        'quality_status':'NOT_EVALUATED_NO_REVIEWED_ANNOTATIONS',
        'limits':'Same train clips; cache and system load effects remain; measured replay output age excludes acquisition, display, YOLO, stereo and motion onset.'}
    args.output.mkdir(parents=True);target=args.output/'summary.json';write_json(target,report)
    for p in files:
        dest=args.output/'source_snapshot'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/p).read_bytes())
        if digest(dest)!=report['code_sha256'][p]: raise RuntimeError('Source changed during snapshot')
    cv2.setNumThreads(1)
    try:
        for case in cases:
            result=paired(case,config,args.output);report['paired'].append(result);write_json(target,report)
            print('PAIRED',result['case_id'],result['equivalence'],
                {v:round(result['timing_ms'][v]['read_activity_ms']['median'],3) for v in READERS},flush=True)
        order=[(c,name) for c in cases if c['step_us']==config['paced_step_us'] for name in READERS]
        for repeat in range(1,config['paced_repeats']+1):
            for case,name in (order if repeat%2 else list(reversed(order))):
                result=paced(case,name,repeat,config,args.output);report['paced'].append(result);write_json(target,report)
                print('PACED',result['case_id'],result['run']['status'],
                    'age_p95_ms',round(result['timing_ms']['output_age_after_window_end_ms']['p95'],3),flush=True)
        report['status']='COMPLETE' if all(c['run']['status']=='COMPLETE' for c in report['paced']) else 'INCOMPLETE_CASES'
    except Exception as error:
        report.update(status='FAILED',error=repr(error));raise
    finally: write_json(target,report)


if __name__=='__main__': main()
