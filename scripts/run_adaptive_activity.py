"""M05 paired adaptive-activity controls and train-only DSEC diagnostic."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from pfe_events.artifacts import sha256_file as digest
from pfe_events.artifacts import write_legacy_json as write_json
from pfe_events.reporting import adaptive_distribution as distribution
from pfe_events.adaptive_activity import AdaptiveActivityDetector, AdaptiveConfig
from pfe_events.motion import ActivityConfig, ActivityDetector
from pfe_events.motion_controls import make_control
from pfe_events.dsec_indexed import IndexedDSECReader
from pfe_events.pilot import load_manifest, unique_file


def detectors(config, width, height):
    activity = ActivityConfig(width=width, height=height, **config['activity'])
    return {name: (ActivityDetector(activity) if name == 'absolute' else
                  AdaptiveActivityDetector(activity, AdaptiveConfig(mode=name, **config['adaptive'])))
            for name in config['variants']}


def merged_events(*streams):
    result = {k: np.concatenate([e[k] for e in streams]) for k in ('x','y','t_us')}
    order = np.argsort(result['t_us'],kind='stable')
    return {k:v[order] for k,v in result.items()}


def score(rows, onset, roi, step, duration, horizon, warmup):
    def matches(row):
        return any(roi[0] <= (r['xyxy'][0]+r['xyxy'][2])/2 < roi[2]
                   and roi[1] <= (r['xyxy'][1]+r['xyxy'][3])/2 < roi[3] for r in row['regions'])
    measured = [r for r in rows if r['end_us'] > warmup]
    valid = [r for r in measured if r['valid']]
    result = {'valid_fraction': len(valid)/len(measured),
              'response': None, 'delay_ms': None, 'roi_active_fraction_after_onset': None,
              'negative_alert_fraction': None, 'negative_alert_starts': None,
              'negative_left_censored_segments': None}
    if onset is not None:
        prior = [r for r in measured if r['end_us'] <= onset]
        relevant = [r for r in measured if onset < r['end_us'] <= onset+horizon]
        active = [r for r in relevant if r['valid'] and matches(r)]
        if any(not r['valid'] for r in prior+relevant):
            result['status'] = 'UNKNOWN'
        elif any(matches(r) for r in prior):
            result['status'] = 'EARLY_ALERT'; result['response'] = False
        else:
            first = active[0]['end_us'] if active else None
            result.update(status='RESPONSE' if first is not None else 'MISS', response=first is not None,
                          delay_ms=(first-onset)/1000 if first is not None else None)
        post = [r for r in measured if r['end_us'] > onset and r['valid']]
        result['roi_active_fraction_after_onset'] = sum(matches(r) for r in post)/len(post) if post else None
    else:
        previous = None; starts = censored = 0
        for row in measured:
            state = bool(row['regions']) if row['valid'] else None
            if state is True:
                starts += previous is False; censored += previous is None
            previous = state
        result.update(status='NEGATIVE_CONTROL', negative_alert_starts=starts,
                      negative_left_censored_segments=censored,
                      negative_alert_fraction=sum(bool(r['regions']) for r in valid)/len(valid) if valid else None)
    return result


def synthetic(config, output):
    p = json.loads((ROOT/config['synthetic']['source_protocol']).read_text(encoding='utf-8'))['controls']
    records = []; groups = defaultdict(list); hashes = {}; cache = {}
    for step in config['synthetic']['steps_us']:
        cases = [(kind, strength, phase) for kind in ('local_onset','local_plus_global')
                 for strength, phase in product(config['synthetic']['strengths'],config['synthetic']['phase_tenths'])]
        cases += [(kind,24,0) for kind in ('empty','hot_pixel','global_burst','persistent_local_flicker')]
        for kind,strength,phase in cases:
            onset = p['base_onset_us']+step*phase//10
            key = f'{kind}:{strength}:{onset}'
            if key not in cache:
                kwargs = dict(width=p['width'],height=p['height'],duration_us=p['duration_us'])
                if kind == 'persistent_local_flicker':
                    events = make_control('local_onset', onset_us=0, strength=strength, noise_rate=0, **kwargs)
                elif kind == 'local_plus_global':
                    events = merged_events(make_control('local_onset',onset_us=onset,strength=strength,**kwargs),
                        make_control('global_burst',onset_us=p['base_onset_us'],**kwargs))
                else:
                    events = make_control(kind,onset_us=onset,strength=strength,**kwargs)
                cache[key] = events
                hashes[key] = {k:hashlib.sha256(v.astype('<i8').tobytes()).hexdigest() for k,v in events.items()}
            events = cache[key]
            current = detectors(config,p['width'],p['height']); timelines = {k:[] for k in current}
            for begin in range(0,p['duration_us'],step):
                end = begin+step; lo,hi = np.searchsorted(events['t_us'],[begin,end])
                part = {k:v[lo:hi] for k,v in events.items()}
                for name,detector in current.items():
                    out = detector.update(part,begin,end)
                    timelines[name].append({'end_us':end,'valid':out.get('valid',True),'regions':out['regions']})
            for name,rows in timelines.items():
                result = score(rows,onset if kind in ('local_onset','local_plus_global') else None,
                    p['roi_xyxy'],step,p['duration_us'],config['synthetic']['response_horizon_us'],
                    config['synthetic']['negative_evaluation_start_us'])
                record = {'variant':name,'control':kind,'step_us':step,'strength':strength,
                          'phase_tenths':phase,'event_key':key,**result}
                records.append(record); groups[(name,kind,step,strength)].append(record)
                if step==10000 and phase==0:
                    folder=output/'synthetic_timelines'; folder.mkdir(exist_ok=True)
                    write_json(folder/f'{kind}_{strength}_{name}.json',rows)
    summaries = []
    for (name,kind,step,strength), rows in groups.items():
        delays = [r['delay_ms'] for r in rows if r['delay_ms'] is not None]
        summaries.append({'variant':name,'control':kind,'step_us':step,'strength':strength,'trials':len(rows),
            'responses':sum(r['response'] is True for r in rows) if kind in ('local_onset','local_plus_global') else None,
            'status_counts':{s:sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})},
            'delay_ms_conditional':distribution(delays),
            'mean_roi_active_fraction_after_onset':float(np.mean([r['roi_active_fraction_after_onset'] for r in rows]))
                if rows[0]['roi_active_fraction_after_onset'] is not None else None,
            'negative_alert_fraction':rows[0]['negative_alert_fraction'],
            'negative_alert_starts':rows[0]['negative_alert_starts'],
            'negative_left_censored_segments':rows[0]['negative_left_censored_segments']})
    write_json(output/'synthetic_trials.json',records); write_json(output/'synthetic_event_hashes.json',hashes)
    return {'trials':len(records),'scope':'Artificial activity, not physical object/camera simulation', 'groups':summaries}


def panel(events, outputs, clip, end):
    raw=np.zeros((480,640),np.uint8); raw[events['y'],events['x']]=225
    im=Image.new('RGB',(960,300),'#101925'); draw=ImageDraw.Draw(im)
    for i,(name,out) in enumerate(outputs.items()):
        tile=Image.fromarray(raw).convert('RGB'); d=ImageDraw.Draw(tile)
        for region in out['regions']: d.rectangle(region['xyxy'],outline=['#ffd166','#5ce1e6','#ea83f7'][i],width=2)
        im.paste(tile.resize((320,240)),(i*320,40))
        draw.text((i*320+5,7),name,fill='white')
        draw.text((i*320+5,22),f"active cells {out['active_fraction']:.1%}",fill='white')
    draw.text((5,282),f'{clip} | {end} us | ACTIVITY ONLY; NOT CONFIRMED MOVING OBJECTS',fill='white')
    return im


def real_train(config,output):
    spec=config['real']; manifest=json.loads((ROOT/spec['manifest']).read_text(encoding='utf-8'))
    entry=next(e for e in load_manifest(ROOT/'configs/pilot.json')['sequences'] if e['name']==spec['sequence'])
    if entry['split']!='train' or spec['allowed_split']!='train': raise ValueError('Only training data authorized')
    clips=[c for c in manifest['clips'] if c['sequence']==spec['sequence'] and c['split']=='train']
    if len(clips)!=3: raise ValueError('Expected three fixed train clips')
    path=unique_file(ROOT/'data/raw'/entry['name']/'events_left','events.h5')
    summaries=[]
    with IndexedDSECReader(path) as reader:
        for clip in clips:
            current=detectors(config,640,480); rows=[]; frames=[]
            folder=output/'train'/clip['id']; folder.mkdir(parents=True)
            step=spec['step_us']
            for index,begin in enumerate(range(clip['start_us']-spec['warmup_us'],clip['end_us'],step)):
                end=begin+step; t0=time.perf_counter_ns(); events=reader.window(begin,end)
                read_ms=(time.perf_counter_ns()-t0)/1e6; results={}; elapsed={}
                order=config['variants'][index%3:]+config['variants'][:index%3]
                for name in order:
                    t0=time.perf_counter_ns(); results[name]=current[name].update(events,begin,end)
                    elapsed[name]=(time.perf_counter_ns()-t0)/1e6
                ordered={name:results[name] for name in config['variants']}
                rows.append({'end_us':end,'warmup':end<=clip['start_us'],'read_ms':read_ms,
                    'variant_order':order,'events':len(events['x']),
                    'variants':{name:{'regions':out['regions'],'valid':out.get('valid',True),
                         'active_fraction':out['active_fraction'],'compute_ms':elapsed[name],
                         'read_plus_compute_ms':read_ms+elapsed[name]} for name,out in ordered.items()}})
                if end>clip['start_us'] and (end-clip['start_us'])%50000==0:
                    frames.append(panel(events,ordered,clip['id'],end))
            write_json(folder/'predictions.json',rows)
            frames[len(frames)//2].save(folder/'comparison.png')
            frames[0].save(folder/'comparison.gif',save_all=True,append_images=frames[1:],duration=50,loop=0)
            measured=[r for r in rows if not r['warmup']]
            summary={'clip_id':clip['id'],'sequence':clip['sequence'],'split':'train','frames':len(measured),
                'quality':'NOT_EVALUATED_NO_REVIEWED_ANNOTATIONS',
                'variants':{name:{'valid_fraction':sum(r['variants'][name]['valid'] for r in measured)/len(measured),
                    'mean_active_fraction':float(np.mean([r['variants'][name]['active_fraction'] for r in measured])),
                    'fraction_frames_with_regions':sum(bool(r['variants'][name]['regions']) for r in measured)/len(measured),
                    'compute_ms':distribution([r['variants'][name]['compute_ms'] for r in measured]),
                    'read_plus_compute_ms':distribution([r['variants'][name]['read_plus_compute_ms'] for r in measured])}
                for name in current}}
            summaries.append(summary); print(clip['id'],json.dumps(summary['variants']),flush=True)
    return summaries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/motion/M05')
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh experiment directory')
    config=json.loads((ROOT/'configs/m05_adaptive_activity.json').read_text(encoding='utf-8'))
    args.output.mkdir(parents=True); cv2.setNumThreads(1)
    sources=['src/pfe_events/artifacts.py','src/pfe_events/reporting.py','configs/m05_adaptive_activity.json','configs/motion_protocol_v1.json','configs/pilot.json',
        'src/pfe_events/adaptive_activity.py','src/pfe_events/motion.py','src/pfe_events/motion_controls.py',
        'src/pfe_events/dsec.py','src/pfe_events/dsec_indexed.py','src/pfe_events/pilot.py',
        'scripts/run_adaptive_activity.py','tests/test_adaptive_activity.py',config['real']['manifest']]
    hashes={}
    for name in sources:
        target=args.output/'source_snapshot'/name; target.parent.mkdir(parents=True,exist_ok=True)
        hashes[name]=digest(ROOT/name); target.write_bytes((ROOT/name).read_bytes())
        if digest(target)!=hashes[name]: raise IOError('Source changed during snapshot')
    report={'experiment':'M05','status':'RUNNING','utc':datetime.now(timezone.utc).isoformat(),
        'config':config,'code_sha256':hashes,'versions':{'numpy':np.__version__,'opencv':cv2.__version__},
        'real_motion_quality':None,'parameter_selection':'NONE; experimental variants retain M01 reference'}
    write_json(args.output/'summary.json',report)
    try:
        report['synthetic']=synthetic(config,args.output)
        print('Synthetic trials:',report['synthetic']['trials'],flush=True)
        report['train']=real_train(config,args.output)
        report['status']='COMPLETE_CONTROLS_AND_TRAIN_DIAGNOSTIC; REAL_MOTION_ACCURACY_NOT_EVALUATED'
    except Exception as error:
        report.update(status='FAILED',error=repr(error)); raise
    finally:
        write_json(args.output/'summary.json',report)


if __name__=='__main__': main()
