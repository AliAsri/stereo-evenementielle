"""M13: blind clips and a fixed 2x2 temporal sensitivity diagnostic on train."""
import argparse
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pfe_events.dsec import load_rectify_map
from pfe_events.dsec_cached import CachedIndexedDSECReader
from pfe_events.geometry import audit_calibration
from pfe_events.pilot import unique_file, load_manifest
from pfe_events.representations import rectified_counts, normalized_event_image
from pfe_events.rectified_tracking import checked_tracks, sample_masked_depth, TrackingConfig
from pfe_events.rigid_motion import estimate_rigid_motion, RigidMotionConfig
from pfe_events.motion_review import SCHEMA, TARGET, validate_review
from pfe_events.artifacts import write_json as save, sha256_file as sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/motion/M13')
    args=parser.parse_args();out=args.output
    if out.exists():raise FileExistsError('Use a fresh output directory')
    cfg=json.loads((ROOT/'configs/m13_temporal_review.json').read_text())
    allowed={s['name'] for s in load_manifest(ROOT/'configs/pilot.json')['sequences'] if s['split']=='train'}
    if not set(cfg['sequences']).issubset(allowed):raise ValueError('Train only')
    normalizer=json.loads((ROOT/cfg['normalizer']).read_text())
    if normalizer['source_split']!='train':raise ValueError('Frozen train normalizer required')
    out.mkdir(parents=True);(out/'clips').mkdir();(out/'comparisons').mkdir();cv2.setNumThreads(1)
    files=['src/pfe_events/artifacts.py','scripts/prepare_temporal_review.py','scripts/run_real_rigid_motion.py','scripts/motion_review.html',
        'scripts/motion_review.js','src/pfe_events/motion_review.py','src/pfe_events/rigid_motion.py',
        'src/pfe_events/rectified_tracking.py','src/pfe_events/representations.py','src/pfe_events/geometry.py',
        'src/pfe_events/pilot.py','src/pfe_events/dsec.py','src/pfe_events/dsec_indexed.py','src/pfe_events/dsec_cached.py',
        'tests/test_motion_review.py','configs/m13_temporal_review.json','configs/pilot.json',cfg['normalizer']]
    report=dict(experiment='M13',status='RUNNING',utc=datetime.now(timezone.utc).isoformat(),protocol=cfg,
        tracking=asdict(TrackingConfig()),rigid=asdict(RigidMotionConfig()),
        code_sha256={p:sha(ROOT/p) for p in files},source_sha256={},comparisons=[],real_motion_quality=None)
    for name in files:
        dest=out/'source_snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/name).read_bytes())
        assert sha(dest)==report['code_sha256'][name]
    save(out/'summary.json',report)
    manifest=dict(schema=SCHEMA,target=TARGET,width=640,height=480,coordinate_frame='event_left_rectified',clips=[])
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    try:
        for name in cfg['sequences']:
            original=ROOT/cfg['anchor_source']/name
            m12=json.loads((original/'summary.json').read_text())
            report['source_sha256'][(original/'summary.json').relative_to(ROOT).as_posix()]=sha(original/'summary.json')
            for source,digest in m12['source_sha256'].items():
                if sha(ROOT/source)!=digest:raise ValueError('M12 source changed')
                report['source_sha256'][source]=digest
            source=ROOT/'data/raw'/name;cal=audit_calibration(unique_file(source/'calibration','cam_to_cam.yaml'))
            k=np.array([[cal['fx_px'],0,cal['cx_px']],[0,cal['fy_px'],cal['cy_px']],[0,0,1]])
            mapping=load_rectify_map(unique_file(source/'events_left','rectify_map*.h5'))
            with CachedIndexedDSECReader(unique_file(source/'events_left','events.h5')) as reader:
                for anchor_index in cfg['anchor_indices']:
                    anchor_id=f'pair_{anchor_index:03d}';cid=f'{name}_{anchor_index:03d}'
                    reference=json.loads((original/f'{anchor_id}.json').read_text());anchor=reference['summary']['previous_us']
                    depth_path=ROOT/reference['summary']['source']['path']
                    if sha(depth_path)!=reference['summary']['source']['sha256']:raise ValueError('S01 depth changed')
                    for path in (depth_path,original/f'{anchor_id}.json',original/f'{anchor_id}.npz'):
                        report['source_sha256'][path.relative_to(ROOT).as_posix()]=sha(path)
                    with np.load(depth_path,allow_pickle=False) as data:
                        depth,valid=data['depth_m'],data['valid']
                        if int(data['window_end_us'])!=anchor or int(data['window_us'])!=50000 or not np.allclose(data['q'],cal['q']):
                            raise ValueError('Incompatible depth timestamp or calibration')
                    start,end=anchor-cfg['clip_before_us'],anchor+cfg['clip_after_us']
                    if start<reader.first_us or end>reader.last_us:raise ValueError('Incomplete blind clip')
                    folder=out/'clips'/cid;folder.mkdir();cache={};frames=[];gif_frames=[];sheet=Image.new('RGB',(1280,1530),'#102030')
                    def event_image(window,end_us):
                        key=(window,end_us)
                        if key not in cache:
                            if end_us-window<reader.first_us or end_us>reader.last_us:raise ValueError('Incomplete comparison')
                            events=reader.window(end_us-window,end_us)
                            counts,_=rectified_counts(events,mapping)
                            cache[key]=np.ascontiguousarray(normalized_event_image(counts,normalizer)[...,2])
                        return cache[key]
                    for i,t in enumerate(range(start+cfg['review_step_us'],end+1,cfg['review_step_us'])):
                        gray=event_image(cfg['review_window_us'],t);path=folder/f'frame_{i:03d}.png'
                        Image.fromarray(gray).save(path)
                        frames.append(dict(start_us=t-cfg['review_window_us'],end_us=t,image=path.relative_to(out).as_posix(),sha256=sha(path)))
                        panel=Image.new('RGB',(640,530),'#102030');panel.paste(Image.fromarray(gray).convert('RGB'),(0,50))
                        draw=ImageDraw.Draw(panel);draw.text((8,4),f'M13 | {cid} | SANS PREDICTIONS',font=font,fill='white')
                        draw.text((8,26),f'+{(t-start)/1000:.0f} ms | fenetre 20 ms | rejeu enregistre',font=font,fill='white')
                        gif_frames.append(panel)
                        if i in (0,20,40,60,80,99):
                            j=(0,20,40,60,80,99).index(i);x=(j%2)*640;y=(j//2)*510
                            sheet.paste(Image.fromarray(gray).convert('RGB'),(x,y+30))
                            ImageDraw.Draw(sheet).text((x+8,y+4),f'{cid} | +{(t-start)/1000:.0f} ms',font=font,fill='white')
                    gif_frames[0].save(folder/'blind.gif',save_all=True,append_images=gif_frames[1:],duration=20,loop=0)
                    sheet.save(folder/'contact.png')
                    manifest['clips'].append(dict(id=cid,sequence=name,split='train',anchor_us=anchor,
                        source_pair=anchor_id,start_us=start,end_us=end,step_us=cfg['review_step_us'],window_us=cfg['review_window_us'],frames=frames))
                    for window in cfg['comparison_windows_us']:
                        for step in cfg['comparison_steps_us']:
                            a,b=event_image(window,anchor),event_image(window,anchor+step)
                            p,q,tracking=checked_tracks(a,b);z,sampling=sample_masked_depth(p,depth,valid)
                            rigid=replace(RigidMotionConfig(),residual_px=cfg['residual_speed_threshold_px_s']*step/1e6,
                                          ransac_px=cfg['ransac_noise_threshold_px'])
                            result=estimate_rigid_motion(p,q,z,k,previous_us=anchor,current_us=anchor+step,
                                                        depth_us=anchor,depth_source='predicted',config=rigid)
                            exact=None
                            if window==50000 and step==20000:
                                with np.load(original/f'{anchor_id}.npz',allow_pickle=False) as saved:
                                    for key,array in [('previous_image',a),('current_image',b),('previous',p),('current',q),('depth_m',z)]:
                                        np.testing.assert_array_equal(array,saved[key])
                                if result!=reference['rigid']:raise AssertionError('M12 anchor not reproduced exactly')
                                exact=True
                            tag=f'{cid}_w{window}_s{step}'
                            row=dict(id=tag,clip_id=cid,window_us=window,step_us=step,overlap_us=max(0,window-step),
                                tracking=tracking,depth_points=result['depth_points'],evaluated_points=result['evaluated_points'],
                                rigid_valid=result['valid'],rigid_status=result['status'],point_counts=dict(Counter(result['point_status'])),
                                residual_threshold_px=rigid.residual_px,
                                median_track_speed_px_s=float(np.median(np.linalg.norm(q-p,axis=1))*1e6/step) if len(p) else None,
                                reference_m12_exact=exact,real_motion_quality=None)
                            save(out/'comparisons'/f'{tag}.json',dict(summary=row,rigid=result,sampling=sampling))
                            np.savez_compressed(out/'comparisons'/f'{tag}.npz',previous=p,current=q,depth_m=z,intrinsic=k,previous_image=a,current_image=b)
                            report['comparisons'].append(row)
                    print(cid,'100 blind frames + 4 temporal conditions',flush=True)
        manifest['manifest_id']=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
        save(out/'review_manifest.json',manifest)
        (out/'review_data.js').write_text('window.REVIEW_DATA='+json.dumps(manifest).replace('<','\\u003c')+';\n',encoding='utf-8')
        for source,target in [('scripts/motion_review.html','review.html'),('scripts/motion_review.js','motion_review.js')]:
            (out/target).write_bytes((ROOT/source).read_bytes())
        empty=dict(schema=SCHEMA,target=TARGET,manifest_id=manifest['manifest_id'],annotations=[])
        save(out/'review_template.json',empty);save(out/'review_status.json',validate_review(manifest,empty))
        report.update(status='COMPLETE_SENSITIVITY_AND_BLIND_CLIPS_PENDING_REVIEW',clips=len(manifest['clips']),
                      blind_frames=sum(len(c['frames']) for c in manifest['clips']),manifest_sha256=sha(out/'review_manifest.json'))
    except Exception as error:
        report.update(status='FAILED',error=repr(error));raise
    finally:save(out/'summary.json',report)


if __name__=='__main__':main()
