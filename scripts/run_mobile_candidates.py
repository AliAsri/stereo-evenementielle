"""M10: controlled residual cases and three existing train clips, no motion GT inferred."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pfe_events.mobile_candidates import CandidateConfig,ResidualCandidateTracker,ImageCandidateDetector
from pfe_events.mobile_controls import KINDS,control_points
from pfe_events.global_motion import event_gray
from pfe_events.dsec_cached import CachedIndexedDSECReader
from pfe_events.pilot import unique_file
from pfe_events.reporting import paced_distribution as distribution
from pfe_events.artifacts import sha256_file as digest, write_legacy_json as write_json
from pfe_events.visualization import native_event_image as native_image


def controls(config):
    records=[]
    for kind in KINDS:
        detector=ResidualCandidateTracker(config=CandidateConfig(**config['candidate']));rows=[]
        for i in range(1,11):
            result=detector.update(*control_points(kind,3<=i<=6),i*20000)
            rows.append({'end_us':i*20000,'valid':result['valid'],
                'raw_regions':len(result['raw_motion']['regions']),
                'tentative_regions':len(result['tentative_regions']),'persistent_regions':len(result['regions']),
                'rejections':result['rejections']})
        first=next((r['end_us'] for r in rows if r['persistent_regions']),None)
        records.append({'control':kind,'scope':'IDEAL_CORRESPONDENCES_NOT_EVENT_CAMERA_SIMULATION',
            'known_limit':{'parallax_counterexample':'Static nearer layer is indistinguishable from moving patch in these correspondences',
                          'local_rotation':'Direction coherence can reject a genuinely rotating patch'}.get(kind),
            'first_persistent_end_us':first,
            'extra_confirmation_ms_after_first_local_observation':(first-60000)/1000 if first else None,
            'persistent_windows':sum(r['persistent_regions']>0 for r in rows),'rows':rows})
    return records


def panel(raw,result,cid,relative_ms):
    out=Image.new('RGB',(1280,568),'#102030');out.paste(raw,(0,80));out.paste(raw,(640,80))
    draw=ImageDraw.Draw(out)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    draw.text((10,7),f'M10 | {cid} | +{relative_ms:.0f} ms | REJEU ENREGISTRE',font=font,fill='white')
    draw.text((10,29),'GAUCHE : residus M03 | DROITE : candidats coherents ; vert = persistant, gris = provisoire',font=font,fill='#ffd166')
    draw.text((10,51),"Mouvement independant NON CONFIRME : camera et parallaxe peuvent encore tromper le modele",font=font,fill='#ffd166')
    for regions,shift,color in [(result['raw_motion']['regions'],0,'#ffbf40'),
        (result['tentative_regions'],640,'#aabbcc'),(result['regions'],640,'#44e699')]:
        for region in regions:
            x1,y1,x2,y2=region['xyxy'];draw.rectangle((x1+shift,y1+80,x2-1+shift,y2+79),outline=color,width=2)
            if 'candidate_id' in region:
                draw.text((x1+shift+3,y1+81),f"C{region['candidate_id']} ({region['consecutive_observations']})",font=font,fill=color)
    return out


def run_clip(clip,config,output):
    cid=clip['id'];source=unique_file(ROOT/'data/raw'/clip['sequence']/'events_left','events.h5')
    detector=ImageCandidateDetector(config=CandidateConfig(**config['candidate']))
    reference_path=ROOT/'outputs/motion/M03/clips'/cid/'predictions.json'
    reference={r['end_us']:r['motion'] for r in json.loads(reference_path.read_text())}
    rows=[];pictures=[];matches=0;target=output/'clips'/cid;target.mkdir(parents=True)
    with CachedIndexedDSECReader(source) as reader:
        for begin in range(clip['start_us']-config['warmup_us'],clip['end_us'],clip['step_us']):
            end=begin+clip['step_us'];t0=time.perf_counter_ns();events=reader.window(begin,end);t1=time.perf_counter_ns()
            gray=event_gray(events);t2=time.perf_counter_ns();result=detector.update(gray,end);t3=time.perf_counter_ns()
            old=reference[end]
            if result['raw_motion']['valid']!=old['valid']: raise AssertionError('M03 validity changed')
            if old['valid']:
                if old!=result['raw_motion']: raise AssertionError('M03 residual reference changed')
                matches+=1
            warmup=end<=clip['start_us']
            rows.append({'end_us':end,'warmup':warmup,'motion':{k:v for k,v in result.items() if k!='raw_motion'},
                'raw_motion':result['raw_motion'],'timing_ms':{'read':(t1-t0)/1e6,'representation':(t2-t1)/1e6,
                    'motion_and_candidates':(t3-t2)/1e6,'total':(t3-t0)/1e6}})
            if not warmup and (end-clip['start_us'])%100000==0:
                frame=panel(native_image(events),result,cid,(end-clip['start_us'])/1000);pictures.append(frame)
                if end-clip['start_us']==1000000: frame.save(target/'comparison.png')
    pictures[0].save(target/'comparison.gif',save_all=True,append_images=pictures[1:],duration=100,loop=0)
    write_json(target/'predictions.json',rows)
    measured=[r for r in rows if not r['warmup']]
    report={'clip_id':cid,'split':'train','step_us':clip['step_us'],'frames':len(measured),
        'source_events_path':source.relative_to(ROOT).as_posix(),'reference_sha256':digest(reference_path),
        'valid_raw_reference_frames_exactly_matched_including_warmup':matches,
        'raw_regions':sum(len(r['raw_motion']['regions']) for r in measured),
        'tentative_regions':sum(len(r['motion']['tentative_regions']) for r in measured),
        'persistent_regions':sum(len(r['motion']['regions']) for r in measured),
        'frames_with_raw_regions':sum(bool(r['raw_motion']['regions']) for r in measured),
        'frames_with_persistent_candidates':sum(bool(r['motion']['regions']) for r in measured),
        'valid_frames':sum(r['motion']['valid'] for r in measured),
        'rejection_reasons':dict(Counter(reason for r in measured for rejected in r['motion']['rejections'] for reason in rejected['reasons'])),
        'timing_ms':{k:distribution([r['timing_ms'][k] for r in measured]) for k in measured[0]['timing_ms']},
        'real_motion_quality':None,'status':'DIAGNOSTIC_ONLY_NO_REVIEWED_MOTION_LABELS'}
    write_json(target/'summary.json',report);return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'outputs/motion/M10')
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a new output directory')
    config=json.loads((ROOT/'configs/m10_mobile_candidates.json').read_text());manifest=json.loads((ROOT/config['manifest']).read_text())
    clips=[c for c in manifest['clips'] if c['sequence']==config['sequence']]
    if len(clips)!=3 or any(c['split']!='train' or c['step_us']!=config['step_us'] for c in clips):
        raise ValueError('Expected three existing train clips at fixed cadence')
    files=['src/pfe_events/artifacts.py','src/pfe_events/reporting.py','src/pfe_events/visualization.py','scripts/run_mobile_candidates.py','src/pfe_events/mobile_candidates.py','src/pfe_events/mobile_controls.py',
        'src/pfe_events/global_motion.py','src/pfe_events/dsec_cached.py','src/pfe_events/dsec_indexed.py','src/pfe_events/dsec.py',
        'src/pfe_events/pilot.py','scripts/run_global_motion.py','scripts/run_motion_baseline.py','scripts/benchmark_paced_motion.py',
        'configs/m10_mobile_candidates.json','tests/test_mobile_candidates.py',config['manifest']]
    report={'experiment':'M10','status':'RUNNING','utc':datetime.now(timezone.utc).isoformat(),'protocol':config,
        'opencv_version':cv2.__version__,'numpy_version':np.__version__,
        'timing_scope':'Unpaced CPU disk replay: read, representation, LK/global fit/candidates; render/export excluded',
        'code_sha256':{p:digest(ROOT/p) for p in files},'clips':[]}
    args.output.mkdir(parents=True)
    for p in files:
        target=args.output/'source_snapshot'/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/p).read_bytes())
        if digest(target)!=report['code_sha256'][p]: raise RuntimeError('Source changed during snapshot')
    cv2.setNumThreads(1)
    try:
        report['controls']=controls(config);write_json(args.output/'controls.json',report['controls'])
        for clip in clips:
            result=run_clip(clip,config,args.output);report['clips'].append(result)
            print(result['clip_id'],'raw boxes',result['raw_regions'],'persistent candidate boxes',result['persistent_regions'],flush=True)
        report['status']='COMPLETE_CONTROLS_AND_TRAIN_DIAGNOSTIC; INDEPENDENT_MOTION_NOT_VALIDATED'
    except Exception as error:
        report.update(status='FAILED',error=repr(error));raise
    finally: write_json(args.output/'summary.json',report)


if __name__=='__main__': main()
