"""Sliding 100 ms diagnostic on existing 50 ms images; no new model.

Counts recurrence in a fixed inspection region, not persistent object identities.
"""
import argparse
import json
from pathlib import Path
import runpy
import shutil
import sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from pfe_events.artifacts import sha256_file,write_json
from pfe_events.geometry import audit_calibration
from pfe_events.rigid_motion import estimate_rigid_motion


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Use a fresh output directory')
    source=ROOT/'outputs/focused_truck/run_01'
    previous_comparison=ROOT/'outputs/focused_truck/interval_01'
    old=json.loads((previous_comparison/'summary.json').read_text())
    saved=json.loads((source/'summary.json').read_text())
    assert old['status']==saved['status']=='COMPLETE'
    for name,digest in old['source_sha256'].items():assert sha256_file(ROOT/name)==digest,name
    helper=Path(__file__).with_name('compare_intervals.py')
    assert sha256_file(helper)==old['script_sha256']
    track_seeds=runpy.run_path(str(helper))['track_seeds']
    cal_path=ROOT/'data/raw/zurich_city_04_b/calibration/cam_to_cam.yaml'
    assert sha256_file(cal_path)==saved['input_sha256'][cal_path.relative_to(ROOT).as_posix()]
    cal=audit_calibration(cal_path)
    k=np.array([[cal['fx_px'],0,cal['cx_px']],[0,cal['fy_px'],cal['cy_px']],[0,0,1.]])
    args.output.mkdir(parents=True)
    shutil.copy2(__file__,args.output/Path(__file__).name)
    shutil.copy2(helper,args.output/helper.name)
    report={'status':'RUNNING','interval_us':100000,'image_window_us':50000,'output_step_us':20000,
            'anchor_us':saved['anchor_timestamp_us'],'frames':[],
            'reference_box_valid_only_at_anchor':saved['reference_box_valid_only_at_anchor'],
            'input_sha256':{},'source_sha256':old['source_sha256'],
            'script_sha256':sha256_file(Path(__file__)),'helper_sha256':sha256_file(helper),
            'region_policy':'Fixed inspection region; published box valid only at last date; no box in inference',
            'identity_policy':'Features reseeded for each pair; recurrence is not same-point or same-object persistence',
            'timing_policy':'Reuse of images/depth already computed; no end-to-end speed or detection-delay measurement',
            'playback':'5x slow motion: 100 ms display per 20 ms source step',
            'threshold_policy':'Unchanged 3 px threshold; 30 px/s at 100 ms; not equivalent to 3 px at 20 ms'}
    for p in (cal_path,source/'summary.json',previous_comparison/'summary.json'):
        report['input_sha256'][p.relative_to(ROOT).as_posix()]=sha256_file(p)
    x1,y1,x2,y2=map(int,saved['reference_box_valid_only_at_anchor']['xyxy'])
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    views=[];cv2.setNumThreads(1)
    try:
        for index in range(80000,400001,20000):
            base=source/f'{index-80000:06d}.npz';current_path=source/f'{index:06d}.npz'
            meta_path=source/f'{index-80000:06d}_inference.json'
            for pth in (base,current_path,meta_path):
                report['input_sha256'][pth.relative_to(ROOT).as_posix()]=sha256_file(pth)
            with np.load(base,allow_pickle=False) as a:
                p,z,previous=[a[n].copy() for n in ('previous','depth_samples','previous_image')]
            with np.load(current_path,allow_pickle=False) as a:current=a['current_image'].copy()
            meta=json.loads(meta_path.read_text())
            end=saved['anchor_timestamp_us']-400000+index;start=end-100000
            assert meta['previous_us']==meta['depth_us']==start
            assert meta['current_us']==start+20000
            q,keep,fb=track_seeds(previous,current,p)
            ids=np.flatnonzero(keep);p,q,z,fb=p[keep],q[keep],z[keep],fb[keep]
            model=estimate_rigid_motion(p,q,z,k,previous_us=start,current_us=end,depth_us=start,depth_source='predicted')
            residual=np.asarray([np.nan if v is None else v for v in model['residual_px']])
            inside=(q[:,0]>=x1)&(q[:,0]<x2)&(q[:,1]>=y1)&(q[:,1]<y2)
            candidates=residual>3;observed=np.isfinite(residual)
            vals=residual[inside&observed]
            row={'offset_ms':(index-400000)/1000,'start_us':start,'end_us':end,'depth_us':start,
                 'seed_count':len(keep),'lost_tracks':int((~keep).sum()),'checked_tracks':len(p),
                 'region_tracks':int(inside.sum()),'region_depth':int(np.isfinite(z[inside]).sum()),
                 'region_unknown':int((inside&~observed).sum()),'region_evaluated':int((inside&observed).sum()),
                 'region_candidates':int((inside&candidates).sum()),'outside_candidates':int((~inside&candidates).sum()),
                 'region_over_150px_per_s':int((inside&(residual>15)).sum()),
                 'region_median_residual_px':float(np.median(vals)) if len(vals) else None,
                 'region_max_residual_px':float(vals.max()) if len(vals) else None,
                 'model_valid':model['valid'],'model_status':model['status'],
                 'reference_valid':index==400000,'candidate_pixels':q[candidates].tolist()}
            report['frames'].append(row)
            stem=f'{index:06d}'
            np.savez_compressed(args.output/(stem+'.npz'),seed_ids=ids,previous=p,current=q,
                                depth_samples=z,fb_px=fb,region=inside,residual_px=residual)
            write_json(args.output/(stem+'_model.json'),model)
            if index==400000:
                assert model==old['horizons']['100000']['model']
                with np.load(previous_comparison/'paired_points.npz',allow_pickle=False) as a:
                    for actual,name in ((p,'previous'),(q,'current_100000'),(z,'depth_samples'),
                                        (ids,'seed_ids'),(residual,'residual_100000')):
                        assert np.array_equal(actual,a[name],equal_nan=True),name
                report['last_pair_exact_interval_01']=True
            scene=Image.fromarray(current).convert('RGB');painter=ImageDraw.Draw(scene)
            for (x,y),res in zip(q,residual):
                color='#aaaaaa' if not np.isfinite(res) else '#ffbd30' if res>3 else '#42dfae'
                radius=3 if res>3 else 1
                painter.ellipse((x-radius,y-radius,x+radius,y+radius),fill=color)
            painter.rectangle((x1,y1,x2,y2),outline='#37c9ff',width=2)
            panel=Image.new('RGB',(1000,730),'#102030');draw=ImageDraw.Draw(panel)
            draw.text((12,10),'CAMION | intervalle glissant 100 ms | images 50 ms | rejeu ralenti x5',font=font,fill='white')
            label='REFERENCE PUBLIEE' if row['reference_valid'] else 'ZONE FIXE D\'INSPECTION, PAS UNE ANNOTATION A CETTE DATE'
            draw.text((12,39),f"{row['offset_ms']:+.0f} ms | {label}",font=small,fill='#37c9ff')
            panel.paste(scene,(0,70));panel.paste(scene.crop((x1,y1,x2,y2)).resize((350,350)),(645,70))
            draw.text((654,438),f"Zone : {row['region_candidates']} candidats / {row['region_evaluated']} evalues",font=font,fill='#ffbd30')
            draw.text((654,467),f"Zone : {row['region_unknown']} points inconnus",font=font,fill='white')
            draw.text((654,496),f"Hors zone : {row['outside_candidates']} candidats",font=font,fill='white')
            draw.text((12,569),f"Suivi global : {len(p)} gardes, {row['lost_tracks']} perdus | modele : {'disponible' if model['valid'] else 'INCONNU'}",font=font,fill='white')
            draw.text((12,601),'Presence de candidats dans la zone (une case = 20 ms, jusqu\'a maintenant) :',font=small,fill='white')
            for j,past in enumerate(report['frames']):
                color='#aaaaaa' if not past['model_valid'] else '#ffbd30' if past['region_candidates'] else '#263e50'
                draw.rectangle((12+29*j,629,35+29*j,647),fill=color)
            draw.text((12,666),'Orange : residu > 3 px | Vert : compatible avec le modele | Gris : inconnu',font=small,fill='white')
            draw.text((12,696),'Presence repetee dans une zone != identite suivie ni mobilite confirmee. Fond non certifie statique.',font=small,fill='#ffcf60')
            views.append(panel)
            print(index,row['region_candidates'],row['outside_candidates'],row['model_status'],flush=True)
        rows=report['frames'];run=longest=0
        for row in rows:
            run=run+1 if row['model_valid'] and row['region_candidates']>0 else 0;longest=max(longest,run)
        report['recurrence']={'frames':len(rows),'valid_models':sum(r['model_valid'] for r in rows),
            'frames_with_region_candidates':sum(r['region_candidates']>0 for r in rows),
            'longest_consecutive_frames':longest,'longest_first_to_last_span_ms':max(0,longest-1)*20,
            'region_candidates_min_max':[min(r['region_candidates'] for r in rows),max(r['region_candidates'] for r in rows)],
            'outside_candidates_min_max':[min(r['outside_candidates'] for r in rows),max(r['outside_candidates'] for r in rows)]}
        views[-1].save(args.output/'diagnostic.png')
        views[0].save(args.output/'clip.gif',save_all=True,append_images=views[1:],duration=100,loop=0)
        report['status']='COMPLETE';print(json.dumps(report['recurrence']))
    except Exception as e:
        report.update(status='FAILED',error=repr(e));raise
    finally:write_json(args.output/'summary.json',report)


if __name__=='__main__':main()
