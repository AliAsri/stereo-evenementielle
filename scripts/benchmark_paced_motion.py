"""M07: sustained paced CPU replay of unchanged event activity on train only."""
import argparse
import csv
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys
import time
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pfe_events.artifacts import sha256_file as digest
from pfe_events.artifacts import write_legacy_json as write_json
from pfe_events.reporting import paced_distribution as distribution
from pfe_events.dsec_indexed import IndexedDSECReader
from pfe_events.motion import ActivityDetector
from pfe_events.pilot import load_manifest, unique_file
from pfe_events.replay_timing import paced_windows


def run_case(entry, step, repeat, config, output):
    source=unique_file(ROOT/'data/raw'/entry['name']/'events_left','events.h5')
    detector=ActivityDetector()
    with IndexedDSECReader(source) as reader:
        start=(reader.first_us+reader.last_us-config['duration_us'])//2
        stop=start+config['duration_us']; warm_start=start-config['warmup_us']
        if warm_start<reader.first_us or stop>reader.last_us or config['warmup_us']%step:
            raise ValueError('Sequence too short or warm-up not divisible by step')
        for begin in range(warm_start,start,step):
            detector.update(reader.window(begin,begin+step),begin,begin+step)
        fallback_before=reader.fallback_windows
        rows,status=paced_windows(reader,detector,start,config['duration_us'],step,
                                 max_wall_seconds=config['max_wall_seconds_per_case'])
        metadata={'path':source.relative_to(ROOT).as_posix(),'bytes':source.stat().st_size,
            'mtime_ns':source.stat().st_mtime_ns,'t_offset_us':reader.offset_us,
            'file_time_range_us':[reader.first_us,reader.last_us],
            'fallback_windows_measured':reader.fallback_windows-fallback_before,
            'raw_file_sha256':'NOT_RECOMPUTED: source path/size/mtime and prior download provenance retained'}
    case_id=f"{entry['name']}_{step//1000}ms_r{repeat}"
    target=output/case_id;target.mkdir()
    if rows:
        with (target/'windows.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    metrics=('read_ms','activity_ms','read_activity_ms','start_lateness_ms','output_age_after_window_end_ms')
    summary={'case_id':case_id,'sequence':entry['name'],'split':entry['split'],'repeat':repeat,
        'step_us':step,'start_us':start,'end_us_exclusive':stop,'source':metadata,
        'parameters':detector.parameters(),'run':status,'timing_ms':{
            k:distribution([r[k] for r in rows]) for k in metrics},
        'events':sum(r['events'] for r in rows),
        'events_per_window':distribution([r['events'] for r in rows]),
        'fraction_service_over_step':float(np.mean([r['read_activity_ms']>step/1000 for r in rows])) if rows else None,
        'fraction_completion_past_next_release':float(np.mean([r['completion_past_next_release'] for r in rows])) if rows else None,
        'max_additional_released_windows_waiting_at_start':max((r['additional_released_windows_waiting_at_start'] for r in rows),default=None),
        'tail_output_age_ms':rows[-1]['output_age_after_window_end_ms'] if rows else None,
        'quality_status':'NOT_EVALUATED_NO_REVIEWED_ANNOTATIONS',
        'real_motion_onset_delay_ms':None,'false_alerts_per_second':None,
        'temporal_blocks':[]}
    # Short temporal blocks expose bursts hidden by one pooled percentile.
    block_us=config['block_us']
    for block in range((config['duration_us']+block_us-1)//block_us):
        selected=[r for r in rows if start+block*block_us<r['end_us_exclusive']<=min(stop,start+(block+1)*block_us)]
        summary['temporal_blocks'].append({'start_relative_s':block*block_us/1e6,'windows':len(selected),
            'events':sum(r['events'] for r in selected),
            'service_ms':distribution([r['read_activity_ms'] for r in selected]),
            'output_age_ms':distribution([r['output_age_after_window_end_ms'] for r in selected])})
    write_json(target/'summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/motion/M07_12s')
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a new output directory')
    config=json.loads((ROOT/'configs/m07_paced_replay.json').read_text())
    manifest=load_manifest(ROOT/'configs/pilot.json')
    entries={e['name']:e for e in manifest['sequences']}
    if any(entries[n]['split']!=config['allowed_split'] or entries[n]['split']!='train' for n in config['sequences']):
        raise ValueError('Only train sequences authorized by this protocol')
    for name in config['sequences']:
        source=unique_file(ROOT/'data/raw'/name/'events_left','events.h5')
        with IndexedDSECReader(source) as reader:
            start=(reader.first_us+reader.last_us-config['duration_us'])//2
            if start-config['warmup_us']<reader.first_us:
                raise ValueError(f'{name}: source too short for centered segment plus warm-up')
    paths=['src/pfe_events/artifacts.py','src/pfe_events/reporting.py','scripts/benchmark_paced_motion.py','src/pfe_events/replay_timing.py',
           'src/pfe_events/motion.py','src/pfe_events/dsec.py','src/pfe_events/dsec_indexed.py',
           'src/pfe_events/pilot.py','configs/pilot.json','configs/m07_paced_replay.json',
           'tests/test_replay_timing.py']
    report={'experiment':'M07','status':'RUNNING','utc':datetime.now(timezone.utc).isoformat(),
        'protocol':config,'python':platform.python_version(),'platform':platform.platform(),
        'versions':{p:importlib.metadata.version(p) for p in ('numpy','opencv-python-headless','h5py')},
        'code_sha256':{p:digest(ROOT/p) for p in paths},'cases':[],
        'timing_limitations':'Observed disk replay under current desktop load; OS scheduling/cache vary. No hardware real-time guarantee. No display, stereo, YOLO or onset quality measured.',
        'clock':str(time.get_clock_info('perf_counter'))}
    args.output.mkdir(parents=True)
    for path in paths:
        target=args.output/'source_snapshot'/path;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/path,target)
        if digest(target)!=report['code_sha256'][path]: raise RuntimeError('Source changed during snapshot')
    cv2.setNumThreads(1)
    target=args.output/'summary.json';write_json(target,report)
    order=[(n,step) for n in config['sequences'] for step in config['steps_us']]
    try:
        for repeat in range(1,config['repeats']+1):
            for name,step in (order if repeat%2 else list(reversed(order))):
                case=run_case(entries[name],step,repeat,config,args.output)
                report['cases'].append(case);write_json(target,report)
                print(case['case_id'],case['run']['status'],
                    'service_p95_ms=',round(case['timing_ms']['read_activity_ms']['p95'],3),
                    'output_age_p95_ms=',round(case['timing_ms']['output_age_after_window_end_ms']['p95'],3),flush=True)
        report['status']='COMPLETE' if all(c['run']['status']=='COMPLETE' for c in report['cases']) else 'INCOMPLETE_CASES'
    except Exception as error:
        report.update(status='FAILED',error=repr(error));raise
    finally:
        write_json(target,report)


if __name__=='__main__': main()
