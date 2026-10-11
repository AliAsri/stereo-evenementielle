"""M09: exact output/state equivalence, then paced replay of lookup activity."""
import argparse
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
from pfe_events.dsec_cached import CachedIndexedDSECReader
from pfe_events.motion import ActivityDetector
from pfe_events.motion_lookup import LookupActivityDetector
from pfe_events.replay_timing import paced_windows
from pfe_events.reporting import paced_distribution as distribution
from pfe_events.artifacts import write_legacy_json as write_json, sha256_file as digest
from functools import partial
from pfe_events.benchmarking import assert_same, save_rows, event_source_path, warm

source_path = partial(event_source_path, ROOT)

DETECTORS={'reference':ActivityDetector,'lookup':LookupActivityDetector}


def paired(case,config,output):
    step=case['step_us'];start=case['start_us'];stop=case['end_us_exclusive']
    rows=[];checks=0;stream_hash=hashlib.sha256()
    detectors={name:cls() for name,cls in DETECTORS.items()}
    with CachedIndexedDSECReader(source_path(case)) as reader:
        for index,begin in enumerate(range(start-config['warmup_us'],stop,step)):
            before=time.perf_counter_ns();events=reader.window(begin,begin+step);loaded=time.perf_counter_ns()
            read_ms=(loaded-before)/1e6
            for array in events.values(): array.flags.writeable=False
            results={}
            for name in (list(DETECTORS) if index%2==0 else list(reversed(DETECTORS))):
                before=time.perf_counter_ns();results[name]=detectors[name].update(events,begin,begin+step);done=time.perf_counter_ns()
                if begin>=start:
                    rows.append({'end_us':begin+step,'variant':name,'read_ms':read_ms,
                        'activity_ms':(done-before)/1e6,'read_activity_ms':read_ms+(done-before)/1e6,
                        'events':results[name]['events']})
            assert_same(results['reference'],results['lookup'])
            if not np.array_equal(detectors['reference'].elapsed,detectors['lookup'].elapsed):
                raise AssertionError('Persistence state mismatch')
            if detectors['reference'].previous_end!=detectors['lookup'].previous_end:
                raise AssertionError('Previous timestamp mismatch')
            checks+=1
            for key in ('x','y','t_us','p'): stream_hash.update(events[key].tobytes())
        fallback=reader.fallback_windows;cache=reader.cache_bytes
    ident=f"{case['sequence']}_{step//1000}ms";target=output/'paired'/ident;target.mkdir(parents=True)
    save_rows(target/'windows.csv',rows)
    report={'case_id':ident,'sequence':case['sequence'],'split':'train','step_us':step,
        'start_us':start,'end_us_exclusive':stop,'paired_measured_windows':len(rows)//2,
        'checked_windows_including_warmup':checks,'equivalence':'EXACT_ALL_OUTPUT_FIELDS_AND_PERSISTENCE_STATE',
        'events_with_warmup_sha256':stream_hash.hexdigest(),'fallback_windows':fallback,
        'cache_limit_bytes':cache,'lookup_bytes':detectors['lookup'].pixel_to_cell.nbytes,
        'timing_ms':{name:{key:distribution([r[key] for r in rows if r['variant']==name])
            for key in ('read_ms','activity_ms','read_activity_ms')} for name in DETECTORS}}
    write_json(target/'summary.json',report);return report


def paced(case,name,repeat,config,output):
    start=case['start_us'];stop=case['end_us_exclusive'];step=case['step_us'];detector=DETECTORS[name]()
    with CachedIndexedDSECReader(source_path(case)) as reader:
        warm(reader,detector,start,step,config);before=reader.fallback_windows
        rows,status=paced_windows(reader,detector,start,stop-start,step,max_wall_seconds=config['max_wall_seconds_per_case'])
        fallback=reader.fallback_windows-before
    ident=f"{case['sequence']}_{name}_r{repeat}";target=output/'paced'/ident;target.mkdir(parents=True)
    if rows: save_rows(target/'windows.csv',rows)
    report={'case_id':ident,'sequence':case['sequence'],'split':'train','variant':name,'repeat':repeat,
        'step_us':step,'start_us':start,'end_us_exclusive':stop,'run':status,'fallback_windows':fallback,
        'events':sum(r['events'] for r in rows),'timing_ms':{key:distribution([r[key] for r in rows])
            for key in ('read_ms','activity_ms','read_activity_ms','start_lateness_ms','output_age_after_window_end_ms')},
        'tail_output_age_ms':rows[-1]['output_age_after_window_end_ms'] if rows else None,
        'fraction_completion_past_next_release':float(np.mean([r['completion_past_next_release'] for r in rows])) if rows else None}
    write_json(target/'summary.json',report);return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/motion/M09')
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a new output directory')
    config=json.loads((ROOT/'configs/m09_lookup_activity.json').read_text())
    previous=json.loads((ROOT/config['source_segments']).read_text())
    cases=[c for c in previous['cases'] if c['repeat']==1 and c['sequence'] in config['sequences']
           and c['step_us'] in config['paired_steps_us']]
    if len(cases)!=4 or any(c['split']!='train' for c in cases): raise ValueError('Expected fixed train cases')
    files=['src/pfe_events/artifacts.py','src/pfe_events/reporting.py','src/pfe_events/benchmarking.py','scripts/benchmark_lookup_activity.py','scripts/benchmark_cached_motion.py','scripts/benchmark_paced_motion.py',
        'src/pfe_events/motion_lookup.py','src/pfe_events/motion.py','src/pfe_events/dsec_cached.py',
        'src/pfe_events/dsec_indexed.py','src/pfe_events/dsec.py','src/pfe_events/replay_timing.py','src/pfe_events/pilot.py',
        'configs/m09_lookup_activity.json','tests/test_motion_lookup.py',config['source_segments']]
    report={'experiment':'M09','status':'RUNNING','utc':datetime.now(timezone.utc).isoformat(),'protocol':config,
        'python':platform.python_version(),'platform':platform.platform(),
        'versions':{p:importlib.metadata.version(p) for p in ('numpy','h5py','opencv-python-headless')},
        'code_sha256':{p:digest(ROOT/p) for p in files},'paired':[],'paced':[],
        'quality_status':'NOT_EVALUATED_NO_REVIEWED_ANNOTATIONS',
        'limits':'Same train segments and no OS cache flush. Timing varies with desktop load. Output age excludes acquisition/display and is not physical motion onset delay.'}
    args.output.mkdir(parents=True);target=args.output/'summary.json';write_json(target,report)
    for path in files:
        dest=args.output/'source_snapshot'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/path).read_bytes())
        if digest(dest)!=report['code_sha256'][path]: raise RuntimeError('Source changed during snapshot')
    cv2.setNumThreads(1)
    try:
        for case in cases:
            result=paired(case,config,args.output);report['paired'].append(result);write_json(target,report)
            print('PAIRED',result['case_id'],result['equivalence'],
                {v:round(result['timing_ms'][v]['activity_ms']['median'],3) for v in DETECTORS},flush=True)
        order=[(c,name) for c in cases if c['step_us']==config['paced_step_us'] for name in DETECTORS]
        for repeat in range(1,config['paced_repeats']+1):
            for case,name in (order if repeat%2 else list(reversed(order))):
                result=paced(case,name,repeat,config,args.output);report['paced'].append(result);write_json(target,report)
                print('PACED',result['case_id'],result['run']['status'],'age_p95_ms',
                    round(result['timing_ms']['output_age_after_window_end_ms']['p95'],3),flush=True)
        report['status']='COMPLETE' if all(c['run']['status']=='COMPLETE' for c in report['paced']) else 'INCOMPLETE_CASES'
    except Exception as error:
        report.update(status='FAILED',error=repr(error));raise
    finally: write_json(target,report)


if __name__=='__main__': main()
