"""Compare 20/100 ms on identical seed points, depth and 50 ms images.

Offline analysis of run_01 only; no change to the application or thresholds.
The final public box selects an endpoint cohort after both pose estimates.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from pfe_events.artifacts import write_json, sha256_file
from pfe_events.geometry import audit_calibration
from pfe_events.rigid_motion import estimate_rigid_motion, RigidMotionConfig


def track_seeds(previous, current, points):
    """Same LK and FB <=1 px rule as existing tracker, preserving seed IDs."""
    lk = dict(winSize=(21,21), maxLevel=2,
              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,20,.01))
    features = np.ascontiguousarray(points.reshape(-1,1,2),dtype=np.float32)
    forward, good, _ = cv2.calcOpticalFlowPyrLK(previous,current,features,None,**lk)
    if forward is None:
        return np.full_like(points,np.nan),np.zeros(len(points),bool),np.full(len(points),np.nan)
    backward, reverse_good, _ = cv2.calcOpticalFlowPyrLK(current,previous,forward,None,**lk)
    if backward is None:
        return forward.reshape(-1,2),np.zeros(len(points),bool),np.full(len(points),np.nan)
    q, back = forward.reshape(-1,2),backward.reshape(-1,2)
    fb = np.linalg.norm(back-points,axis=1)
    h,w=previous.shape
    keep=((good.ravel()==1)&(reverse_good.ravel()==1)&np.isfinite(q).all(axis=1)
          &np.isfinite(back).all(axis=1)&(fb<=1)&(q>=0).all(axis=1)
          &(q[:,0]<w)&(q[:,1]<h))
    return q,keep,fb


def stats(a):
    a=np.asarray(a,dtype=float);a=a[np.isfinite(a)]
    return {'count':int(a.size),'median':float(np.median(a)) if a.size else None,
            'max':float(a.max()) if a.size else None}


def as_vectors(model):
    return np.array([p if p is not None else [np.nan,np.nan] for p in model['predicted_pixels']])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Use a fresh output directory')
    source=ROOT/'outputs/focused_truck/run_01'
    saved=json.loads((source/'summary.json').read_text())
    assert saved['status']=='COMPLETE' and saved['window_us']==50000
    for name,digest in saved['source_sha256'].items():
        if name.startswith('src/'):assert sha256_file(ROOT/name)==digest,name
    cal_path=ROOT/'data/raw/zurich_city_04_b/calibration/cam_to_cam.yaml'
    assert sha256_file(cal_path)==saved['input_sha256'][cal_path.relative_to(ROOT).as_posix()]
    cal=audit_calibration(cal_path)
    k=np.array([[cal['fx_px'],0,cal['cx_px']],[0,cal['fy_px'],cal['cy_px']],[0,0,1.]])
    with np.load(source/'320000.npz',allow_pickle=False) as a:
        p,z,previous,short,saved_q=[a[n].copy() for n in ('previous','depth_samples','previous_image','current_image','current')]
    with np.load(source/'400000.npz',allow_pickle=False) as a:long=a['current_image'].copy()
    meta=json.loads((source/'320000_inference.json').read_text())
    end=saved['anchor_timestamp_us'];start=end-100000
    assert meta['previous_us']==meta['depth_us']==start and meta['current_us']==start+20000
    cv2.setNumThreads(1)
    q20,ok20,fb20=track_seeds(previous,short,p)
    q100,ok100,fb100=track_seeds(previous,long,p)
    # Existing 20 ms correspondences must be reproduced before comparing.
    assert ok20.all() and np.allclose(q20,saved_q,atol=1e-4,rtol=0)
    common=ok20&ok100
    ids=np.flatnonzero(common);points=p[common];depth=z[common]
    args.output.mkdir(parents=True)
    shutil.copy2(__file__,args.output/Path(__file__).name)
    inputs=[source/n for n in ('summary.json','320000.npz','400000.npz','320000_inference.json')]+[cal_path]
    report={'status':'RUNNING','start_us':start,'anchor_us':end,'window_us':50000,
            'intervals_us':[20000,100000], 'seed_policy':'All existing checked 20 ms points, no box seeding; common surviving IDs used in both pose fits',
            'reference_policy':'Final verified box selects endpoints at 100 ms only, after inference; same IDs inspected at 20 ms; not per-frame ground truth',
            'seeds':len(p),'common_survivors':len(ids),'lost_at_100ms':int((~ok100).sum()),
            'input_sha256':{str(f.relative_to(ROOT)):sha256_file(f) for f in inputs},
            'source_sha256':{n:sha256_file(ROOT/n) for n in saved['source_sha256'] if n.startswith('src/')},
            'script_sha256':sha256_file(Path(__file__)), 'horizons':{},
            'limitations':['Shared 20/100 ms survivors only; long-horizon survivor bias',
                          'Point inside box can be background; LK agreement does not prove correspondence accuracy',
                          'No annotated onset, object precision/recall or camera pose reference',
                          'Same pixel threshold is a different residual-rate cutoff at different intervals']}
    try:
        # Fit both poses before any use of reference coordinates.
        models={dt:estimate_rigid_motion(points,q[common],depth,k,previous_us=start,
                   current_us=start+dt,depth_us=start,depth_source='predicted')
                for dt,q in ((20000,q20),(100000,q100))}
        x1,y1,x2,y2=saved['reference_box_valid_only_at_anchor']['xyxy']
        endpoint=q100[common]
        region=(endpoint[:,0]>=x1)&(endpoint[:,0]<x2)&(endpoint[:,1]>=y1)&(endpoint[:,1]<y2)
        report['endpoint_cohort_points']=int(region.sum())
        report['endpoint_cohort_with_depth']=int(np.isfinite(depth[region]).sum())
        arrays={'seed_ids':ids,'previous':points,'depth_samples':depth,'endpoint_cohort':region,
                'previous_us':np.array(start),'depth_us':np.array(start)}
        for dt,q,fb in ((20000,q20,fb20),(100000,q100,fb100)):
            model=models[dt];res=np.array([np.nan if v is None else v for v in model['residual_px']])
            predicted=as_vectors(model);seconds=dt/1e6
            report['horizons'][str(dt)]={'model':model,'cohort':{
                'residual_px':stats(res[region]),'residual_px_per_s':stats(res[region]/seconds),
                'observed_displacement_px':stats(np.linalg.norm(q[common][region]-points[region],axis=1)),
                'predicted_displacement_px':stats(np.linalg.norm(predicted[region]-points[region],axis=1)),
                'forward_backward_px':stats(fb[common][region]),
                'over_3px':int(np.count_nonzero(res[region]>3)),
                'over_150px_per_s':int(np.count_nonzero(res[region]/seconds>150)),
                'unevaluated':int(np.count_nonzero(~np.isfinite(res[region])))}}
            arrays[f'current_{dt}']=q[common];arrays[f'predicted_{dt}']=predicted
            arrays[f'residual_{dt}']=res;arrays[f'fb_{dt}']=fb[common]
        np.savez_compressed(args.output/'paired_points.npz',**arrays)
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
        small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
        view=Image.new('RGB',(1280,740),'#102030');draw=ImageDraw.Draw(view)
        draw.text((12,10),'MEME CAMION | memes points de depart et meme profondeur | images de 50 ms',font=font,fill='white')
        draw.text((12,38),'Bleu : deplacement observe | Orange : ecart au modele camera | Fleches amplifiees x5',font=small,fill='#ffcf60')
        for shift,dt,img in ((0,20000,short),(640,100000,long)):
            view.paste(Image.fromarray(img).convert('RGB'),(shift,95))
            draw.text((shift+12,68),f'Intervalle {dt//1000} ms',font=font,fill='white')
            if dt==100000:draw.rectangle((shift+x1,95+y1,shift+x2,95+y2),outline='#37c9ff',width=2)
            for p0,q0,pred in zip(points[region],arrays[f'current_{dt}'][region],arrays[f'predicted_{dt}'][region]):
                if not np.isfinite(pred).all():continue
                origin=p0+np.array([shift,95]);observed=origin+5*(q0-p0)
                residual_end=observed+5*(q0-pred)
                draw.line([tuple(origin),tuple(observed)],fill='#37c9ff',width=2)
                draw.line([tuple(observed),tuple(residual_end)],fill='#ffbb30',width=2)
            c=report['horizons'][str(dt)]['cohort']
            med=c['residual_px']['median'];rate=c['residual_px_per_s']['median']
            draw.text((shift+12,595),f"Residus > 3 px : {c['over_3px']} | inconnus : {c['unevaluated']}",font=font,fill='white')
            label=f'Residu median : {med:.3f} px ({rate:.1f} px/s)' if med is not None else 'Pose ou projection indisponible'
            draw.text((shift+12,624),label,font=font,fill='white')
        draw.text((12,671),'La boite est une reference uniquement a droite. Les memes identifiants de points sont examines a gauche.',font=small,fill='white')
        draw.text((12,703),'Un residu plus grand sur 100 ms ne suffit pas a prouver un objet mobile ni un meilleur detecteur.',font=small,fill='#ffcf60')
        view.save(args.output/'comparison.png')
        report['status']='COMPLETE'
        print(json.dumps({dt:v['cohort'] for dt,v in report['horizons'].items()},indent=2))
    except Exception as e:
        report.update(status='FAILED',error=repr(e));raise
    finally:write_json(args.output/'summary.json',report)


if __name__=='__main__':main()
