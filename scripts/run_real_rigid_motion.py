"""M12: offline real train pairs with S01 predicted depth; no motion GT loaded."""
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pfe_events.artifacts import sha256_file as sha
from pfe_events.artifacts import write_json as save
from pfe_events.reporting import rigid_distribution as distribution
from pfe_events.dsec import load_rectify_map
from pfe_events.dsec_cached import CachedIndexedDSECReader
from pfe_events.geometry import audit_calibration
from pfe_events.pilot import load_manifest, unique_file
from pfe_events.representations import rectified_counts, normalized_event_image
from pfe_events.rectified_tracking import checked_tracks, sample_masked_depth, TrackingConfig
from pfe_events.rigid_motion import estimate_rigid_motion, RigidMotionConfig
from pfe_events.global_motion import fit_apparent_motion, GlobalMotionConfig


def event_digest(events):
    h=hashlib.sha256()
    for key in sorted(events):
        array=events[key]
        h.update(f'{key}:{array.dtype}:{array.shape}:'.encode());h.update(array.tobytes())
    return h.hexdigest()


def draw_pair(image,points,old_status,result,title):
    canvas=Image.new('RGB',(1280,600),'#102030');d=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    d.text((10,6),f'M12 | {title} | DONNEES REELLES, profondeur S01 PREDITE',font=font,fill='white')
    d.text((10,29),'Gauche : similarite M03 | Droite : modele rigide + profondeur | Mouvement independant NON CONFIRME',font=font,fill='#ffc040')
    d.text((10,52),'Orange : residu >3px | Vert : compatible modele | Gris : inconnu / profondeur manquante',font=font,fill='white')
    statuses=Counter(result['point_status'])
    d.text((10,75),f"Modele : {result['status']} | profondeur {result['depth_points']}/{len(points)} | candidats {statuses['RESIDUAL_CANDIDATE']} | inconnus {statuses['UNKNOWN']}",font=font,fill='white')
    colors={'RESIDUAL_CANDIDATE':'#ffc040','MODEL_CONSISTENT':'#25cf9b','UNKNOWN':'#aaaaaa'}
    for shift,status in ((0,old_status),(640,result['point_status'])):
        canvas.paste(Image.fromarray(image).convert('RGB'),(shift,120))
        for (u,v),state in zip(points,status):
            x,y=float(u)+shift,float(v)+120
            d.ellipse((x-3,y-3,x+3,y+3),outline=colors[state],width=2)
    return canvas


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/motion/M12')
    args=parser.parse_args();output=args.output
    if output.exists():raise FileExistsError('Use a fresh output directory')
    protocol=json.loads((ROOT/'configs/m12_real_rigid_motion.json').read_text())
    manifest=load_manifest(ROOT/protocol['source_manifest'])
    allowed={e['name'] for e in manifest['sequences'] if e['split']=='train'}
    if not set(protocol['sequences']).issubset(allowed):raise ValueError('Train only')
    inventory=json.loads((ROOT/protocol['depth_inventory']).read_text())
    normalizer=json.loads((ROOT/protocol['normalizer']).read_text())
    if normalizer['source_split']!='train':raise ValueError('Expected frozen train normalizer')
    output.mkdir(parents=True);cv2.setNumThreads(1)
    files=['src/pfe_events/artifacts.py','src/pfe_events/reporting.py','scripts/run_real_rigid_motion.py','src/pfe_events/rectified_tracking.py',
           'src/pfe_events/rigid_motion.py','src/pfe_events/global_motion.py',
           'src/pfe_events/representations.py','src/pfe_events/geometry.py',
           'src/pfe_events/dsec.py','src/pfe_events/dsec_indexed.py','src/pfe_events/dsec_cached.py',
           'src/pfe_events/pilot.py','tests/test_rectified_tracking.py','configs/m12_real_rigid_motion.json',
           protocol['depth_inventory'],protocol['source_manifest'],protocol['normalizer']]
    report=dict(experiment='M12',status='RUNNING',utc=datetime.now(timezone.utc).isoformat(),protocol=protocol,
        tracking_config=asdict(TrackingConfig()),rigid_config=asdict(RigidMotionConfig()),
        similarity_config=asdict(GlobalMotionConfig()),versions=dict(opencv=cv2.__version__,numpy=np.__version__),
        source_sha256={name:sha(ROOT/name) for name in files},sequences=[],real_motion_quality=None)
    for name in files:
        target=output/'source_snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes());assert sha(target)==report['source_sha256'][name]
    save(output/'summary.json',report)
    try:
        for name in protocol['sequences']:
            source=ROOT/'data/raw'/name;target=output/name;target.mkdir()
            entries=[s for s in inventory['sequences'] if s['sequence']==name]
            if len(entries)!=1 or entries[0]['split']!='train':raise ValueError('Invalid inventory')
            calibration_path=unique_file(source/'calibration','cam_to_cam.yaml')
            map_path=unique_file(source/'events_left','rectify_map*.h5')
            events_path=unique_file(source/'events_left','events.h5')
            calibration=audit_calibration(calibration_path)
            if not calibration['canonical_equal_intrinsics'] or calibration['resolution']!=[640,480]:
                raise ValueError('This adapter requires canonical S01 event calibration')
            k=np.array([[calibration['fx_px'],0,calibration['cx_px']],
                        [0,calibration['fy_px'],calibration['cy_px']],[0,0,1]])
            mapping=load_rectify_map(map_path);rows=[];skipped=[]
            sources={p.relative_to(ROOT).as_posix():sha(p) for p in (calibration_path,map_path,events_path)}
            with CachedIndexedDSECReader(events_path) as reader:
                for index,item in enumerate(entries[0]['items']):
                    path=ROOT/item['path']
                    if sha(path)!=item['sha256']:raise ValueError('S01 depth changed')
                    t0=time.perf_counter_ns()
                    with np.load(path,allow_pickle=False) as data:
                        depth=data['depth_m'];valid=data['valid'];disparity=data['disparity_px']
                        end=int(data['window_end_us']);window=int(data['window_us'])
                        if (depth.shape!=(480,640) or valid.dtype!=bool or valid.shape!=depth.shape
                                or disparity.shape!=depth.shape or not np.allclose(data['q'],calibration['q'])
                                or end!=item['end_us'] or window!=protocol['window_us']):
                            raise ValueError('Incompatible S01 geometry or timestamp')
                        expected=calibration['fx_px']*calibration['baseline_m']/disparity[valid]
                        if not np.isfinite(expected).all() or np.any(expected<=0) or not np.allclose(depth[valid],expected,rtol=1e-5):
                            raise ValueError('Stored predicted depth disagrees with disparity/calibration')
                    t1=time.perf_counter_ns();later=end+protocol['step_us']
                    if end-window<reader.first_us or later>reader.last_us:
                        skipped.append(dict(index=index,end_us=end,reason='INCOMPLETE_EVENT_PAIR',source=item['path']))
                        continue
                    previous_events=reader.window(end-window,end)
                    current_events=reader.window(later-window,later);t2=time.perf_counter_ns()
                    prev_counts,prev_dropped=rectified_counts(previous_events,mapping)
                    curr_counts,curr_dropped=rectified_counts(current_events,mapping)
                    a=np.ascontiguousarray(normalized_event_image(prev_counts,normalizer)[...,2])
                    b=np.ascontiguousarray(normalized_event_image(curr_counts,normalizer)[...,2]);t3=time.perf_counter_ns()
                    p,q,tracking=checked_tracks(a,b);t4=time.perf_counter_ns()
                    z,sampling=sample_masked_depth(p,depth,valid);t5=time.perf_counter_ns()
                    result=estimate_rigid_motion(p,q,z,k,previous_us=end,current_us=later,
                                                depth_us=end,depth_source='predicted');t6=time.perf_counter_ns()
                    old=fit_apparent_motion(p/2,q/2)
                    old_status=np.array(['RESIDUAL_CANDIDATE' if e>3 else 'MODEL_CONSISTENT'
                        for e in old['residual_native_px']] if old['valid'] else ['UNKNOWN']*len(p))
                    new_status=np.array(result['point_status']);shared=(old_status!='UNKNOWN')&(new_status!='UNKNOWN')
                    counts=dict(Counter(result['point_status']))
                    cid=f'pair_{index:03d}'
                    row=dict(id=cid,source=item,previous_us=end,current_us=later,
                        windows_us=[[end-window,end],[later-window,later]],overlap_us=window-protocol['step_us'],
                        event_counts=[len(previous_events['x']),len(current_events['x'])],
                        event_sha256=[event_digest(previous_events),event_digest(current_events)],
                        rectification_dropped=[prev_dropped,curr_dropped],tracking=tracking,
                        depth_points=result['depth_points'],rigid_status=result['status'],rigid_valid=result['valid'],
                        rigid_point_counts=counts,similarity_valid=old['valid'],
                        similarity_point_counts=dict(Counter(old_status.tolist())),
                        shared_evaluated_points=int(shared.sum()),
                        shared_rigid_candidates=int(((new_status=='RESIDUAL_CANDIDATE')&shared).sum()),
                        shared_similarity_candidates=int(((old_status=='RESIDUAL_CANDIDATE')&shared).sum()),
                        timing_ms=dict(cached_depth_load=(t1-t0)/1e6,read_pair=(t2-t1)/1e6,
                            representation_pair=(t3-t2)/1e6,tracking=(t4-t3)/1e6,
                            sampling=(t5-t4)/1e6,rigid_fit=(t6-t5)/1e6,total_with_cached_depth=(t6-t0)/1e6),
                        real_motion_quality=None)
                    save(target/f'{cid}.json',dict(summary=row,rigid=result,similarity=old,sampling=sampling))
                    np.savez_compressed(target/f'{cid}.npz',previous=p,current=q,depth_m=z,intrinsic=k,
                        previous_image=a,current_image=b,previous_us=end,current_us=later,depth_us=end)
                    panel=draw_pair(b,q,old_status,result,f'{name} | paire {index:02d}')
                    panel.save(target/f'{cid}.png')
                    if index==10:
                        panel.save(target/'example.png')
                        save(target/'example.json',dict(selection='fixed inventoried index 10, not quality-selected',pair_id=cid))
                    rows.append(row)
                    print(name,cid,'depth',result['depth_points'],'/',len(p),result['status'],counts,flush=True)
            sequence=dict(sequence=name,split='train',source_sha256=sources,attempted=len(entries[0]['items']),
                          processed=len(rows),skipped=skipped,rigid_status_counts=dict(Counter(r['rigid_status'] for r in rows)),
                          tracks=sum(r['tracking']['checked_tracks'] for r in rows),depth_points=sum(r['depth_points'] for r in rows),
                          point_counts=dict(sum((Counter(r['rigid_point_counts']) for r in rows),Counter())),
                          shared_evaluated_points=sum(r['shared_evaluated_points'] for r in rows),
                          shared_rigid_candidates=sum(r['shared_rigid_candidates'] for r in rows),
                          shared_similarity_candidates=sum(r['shared_similarity_candidates'] for r in rows),
                          timing_ms={key:distribution([r['timing_ms'][key] for r in rows]) for key in rows[0]['timing_ms']} if rows else {},
                          rows=rows,real_motion_quality=None)
            save(target/'summary.json',sequence);report['sequences'].append(sequence)
        report['status']='COMPLETE_REAL_TRAIN_DIAGNOSTIC_NO_REVIEWED_MOTION_LABELS'
    except Exception as error:
        report.update(status='FAILED',error=repr(error));raise
    finally:save(output/'summary.json',report)


if __name__=='__main__':main()
