"""M11: compare 2D similarity and depth-assisted rigid motion on two-view 3D controls."""
import argparse
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
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
from pfe_events.artifacts import write_json as write
from pfe_events.rigid_motion import estimate_rigid_motion, RigidMotionConfig
from pfe_events.rigid_controls import make_scene, KINDS
from pfe_events.global_motion import fit_apparent_motion, GlobalMotionConfig


def metrics(status,moving):
    status=np.asarray(status);known=status!='UNKNOWN';candidate=status=='RESIDUAL_CANDIDATE'
    tp=int((candidate&moving).sum());fp=int((candidate&~moving).sum())
    positives=int(moving.sum());negatives=int((~moving).sum())
    return dict(tp=tp,fp=fp,fn=positives-tp,positive_points=positives,negative_points=negatives,
                unknown_points=int((~known).sum()),evaluated_points=int(known.sum()),
                precision=tp/(tp+fp) if tp+fp else None,
                recall_all_positive_points=tp/positives if positives else None,
                false_candidate_fraction_all_static_points=fp/negatives if negatives else None)


def comparison_panel(scene,old_status,new_status):
    canvas=Image.new('RGB',(1280,550),'#102030');d=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    d.text((10,5),f"M11 | {scene['kind']} | SCENE 3D SYNTHETIQUE, profondeur de reference",font=font,fill='white')
    d.text((10,28),'Gauche : similarite M03 | Droite : modele rigide + profondeur (oracle)',font=font,fill='white')
    d.text((10,51),'Orange : residu >3px | Vert : compatible modele | Gris : inconnu | Cercle violet : point mobile GT',font=font,fill='white')
    colors={'RESIDUAL_CANDIDATE':'#ffc040','MODEL_CONSISTENT':'#25cf9b','UNKNOWN':'#999999'}
    for shift,status in ((0,old_status),(640,new_status)):
        for i,(u,v) in enumerate(scene['current']):
            x,y=float(u)+shift,float(v)+70
            if scene['moving'][i]:d.ellipse((x-7,y-7,x+7,y+7),outline='#ed7eff',width=2)
            d.ellipse((x-3,y-3,x+3,y+3),fill=colors[status[i]])
    return canvas


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/motion/M11')
    args=parser.parse_args();output=args.output
    if output.exists():raise FileExistsError('Use a new output directory')
    protocol=json.loads((ROOT/'configs/m11_rigid_motion.json').read_text())
    config=RigidMotionConfig();cv2.setNumThreads(1)
    files=['src/pfe_events/artifacts.py','src/pfe_events/rigid_motion.py','src/pfe_events/rigid_controls.py',
           'src/pfe_events/global_motion.py','scripts/run_rigid_controls.py',
           'tests/test_rigid_motion.py','configs/m11_rigid_motion.json']
    output.mkdir(parents=True);(output/'cases').mkdir()
    report=dict(experiment='M11',status='RUNNING',utc=datetime.now(timezone.utc).isoformat(),
                protocol=protocol,rigid_config=asdict(config),similarity_config=asdict(GlobalMotionConfig()),
                versions=dict(opencv=cv2.__version__,numpy=np.__version__),
                source_sha256={p:sha(ROOT/p) for p in files},cases=[],real_motion_quality=None)
    for name in files:
        dest=output/'source_snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((ROOT/name).read_bytes())
        assert sha(dest)==report['source_sha256'][name]
    write(output/'summary.json',report)
    try:
        for kind in KINDS:
            for noise in protocol['noise_px']:
                for seed in protocol['seeds']:
                    s=make_scene(kind,seed,noise);case_id=f'{kind}_noise{noise}_seed{seed}'
                    np.savez_compressed(output/'cases'/f'{case_id}.npz',**s)
                    start=time.perf_counter_ns()
                    result=estimate_rigid_motion(s['previous'],s['current'],s['depth_m'],s['intrinsic'],
                        previous_us=s['previous_us'],current_us=s['current_us'],depth_us=s['previous_us'],
                        depth_source=protocol['depth_source'],config=config)
                    cost_ms=(time.perf_counter_ns()-start)/1e6
                    old=fit_apparent_motion(s['previous']/2,s['current']/2)
                    old_status=['RESIDUAL_CANDIDATE' if e>3 else 'MODEL_CONSISTENT'
                                for e in old['residual_native_px']] if old['valid'] else ['UNKNOWN']*len(s['previous'])
                    pose_error=None
                    if result['valid']:
                        estimated=np.asarray(result['transform_previous_to_current']);truth=s['transform']
                        rotation_delta=estimated[:3,:3]@truth[:3,:3].T
                        pose_error=dict(translation_l2_m=float(np.linalg.norm(estimated[:3,3]-truth[:3,3])),
                            rotation_deg=float(np.rad2deg(np.arccos(np.clip((np.trace(rotation_delta)-1)/2,-1,1)))))
                    record=dict(case_id=case_id,kind=kind,noise_px=noise,seed=seed,
                                rigid_valid=result['valid'],rigid_status=result['status'],
                                rigid=metrics(result['point_status'],s['moving']),
                                similarity=metrics(old_status,s['moving']),pose_error=pose_error,
                                rigid_fit_cost_ms=cost_ms)
                    write(output/'cases'/f'{case_id}.json',dict(summary=record,rigid=result,similarity=old))
                    report['cases'].append(record)
                    if noise==0 and seed==0:
                        comparison_panel(s,old_status,result['point_status']).save(output/f'{kind}.png')
        groups=defaultdict(list)
        for row in report['cases']:groups[(row['kind'],row['noise_px'])].append(row)
        report['groups']=[]
        for (kind,noise),rows in groups.items():
            group=dict(kind=kind,noise_px=noise,cases=len(rows),valid_fits=sum(r['rigid_valid'] for r in rows))
            for method in ('rigid','similarity'):
                keys=('tp','fp','fn','positive_points','negative_points','unknown_points','evaluated_points')
                group[method]={key:sum(r[method][key] for r in rows) for key in keys}
            group['median_fit_ms']=float(np.median([r['rigid_fit_cost_ms'] for r in rows]))
            report['groups'].append(group)
        report['status']='COMPLETE_SYNTHETIC_ORACLE_CONTROLS_REAL_MOTION_NOT_EVALUATED'
    except Exception as error:
        report.update(status='FAILED',error=repr(error));raise
    finally:write(output/'summary.json',report)
    print('Completed',len(report['cases']),'controlled pairs; real motion quality NOT EVALUATED')
    for row in report['groups']:
        if row['noise_px']==0:print(row['kind'],'rigid',row['rigid'],'similarity',row['similarity'])


if __name__=='__main__':main()
