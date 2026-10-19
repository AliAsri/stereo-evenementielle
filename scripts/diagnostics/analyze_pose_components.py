"""Saved-pose decomposition, or a fixed-data point-order sensitivity check."""
import argparse
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from pfe_events.artifacts import sha256_file, write_json


def depth_reference_metrics(predicted, reference, *, focal_baseline):
    """Conditional errors on paired depths; missing predictions stay in coverage."""
    p, r = np.asarray(predicted, dtype=float), np.asarray(reference, dtype=float)
    if p.ndim != 1 or p.shape != r.shape or not np.isfinite(focal_baseline) or focal_baseline <= 0:
        raise ValueError('Matching depth vectors and positive focal-baseline required')
    pv, rv = np.isfinite(p) & (p > 0), np.isfinite(r) & (r > 0)
    joint = pv & rv
    n = int(joint.sum()); nr = int(rv.sum())
    de = np.abs(focal_baseline / p[joint] - focal_baseline / r[joint])
    ze = np.abs(p[joint] - r[joint])
    return dict(tracks=len(p), predicted=int(pv.sum()), reference=nr, paired=n,
        reference_without_prediction=int((rv & ~pv).sum()),
        predicted_without_reference=int((pv & ~rv).sum()),
        paired_fraction_of_reference=n/nr if nr else None,
        disparity_mae_px=float(de.mean()) if n else None,
        disparity_bad3_count=int((de > 3).sum()),
        disparity_bad3_fraction=float((de > 3).mean()) if n else None,
        depth_mae_m=float(ze.mean()) if n else None,
        depth_median_abs_error_m=float(np.median(ze)) if n else None,
        depth_median_relative_error=float(np.median(ze/r[joint])) if n else None)


def check_exact_depth(output):
    """One preselected exact-date control; GT never enters tracking or pose fit."""
    from contextlib import ExitStack
    from pfe_events.dsec import load_rectify_map
    from pfe_events.dsec_cached import CachedIndexedDSECReader
    from pfe_events.geometry import audit_calibration, decode_dsec_disparity
    from pfe_events.pilot import reference_frames, unique_file
    from pfe_events.representations import rectified_counts, normalized_event_image
    from pfe_events.stereo import predict_stereo, StereoConfig
    from pfe_events.clip_motion import ClipMotionCache, infer_clip_motion
    from pfe_events.rectified_tracking import checked_tracks, sample_disparity_depth
    cv2.setNumThreads(2)
    folder=ROOT/'data/raw/zurich_city_04_b'
    times, paths=reference_frames(folder)
    # Fixed from the timestamp audit, before observing any depth errors.
    depth_us=36613900994
    hits=np.flatnonzero(times==depth_us)
    if len(hits)!=1: raise ValueError('Expected exactly one reference at the preselected date')
    gt_path=paths[int(hits[0])]; end_us=depth_us+100000
    cp=folder/'calibration/cam_to_cam.yaml'; calibration=audit_calibration(cp,require_canonical=True)
    normpath=ROOT/'outputs/stereo/S01/normalizer.json'; norm=json.loads(normpath.read_text())
    if norm['source_split']!='train': raise ValueError('Train-only frozen normalizer required')
    map_paths=[folder/f'events_{side}/rectify_map.h5' for side in ('left','right')]
    event_paths=[folder/f'events_{side}/events.h5' for side in ('left','right')]
    maps=[load_rectify_map(p) for p in map_paths]
    with ExitStack() as stack:
        readers=[stack.enter_context(CachedIndexedDSECReader(p)) for p in event_paths]
        if any(depth_us-50000<r.first_us or end_us>r.last_us for r in readers):
            raise ValueError('Incomplete causal history')
        def image(reader, mapping, end):
            return np.ascontiguousarray(normalized_event_image(
                rectified_counts(reader.window(end-50000,end),mapping)[0],norm,total_only=True))
        started=time.perf_counter()
        previous=[image(r,m,depth_us) for r,m in zip(readers,maps)]
        disparity,valid,_,_=predict_stereo(*previous,StereoConfig())
        current=image(readers[0],maps[0],end_us)
        cache=ClipMotionCache(readers,maps,calibration,norm)
        cache.remember(depth_us,previous,disparity,valid)
        arrays,model,details=infer_clip_motion(readers,maps,calibration,norm,current,
            end_us=end_us,history_cache=cache)
        inference_ms=(time.perf_counter()-started)*1000
        # Reconstruct pre-long-track seeds: duplicate suppression must precede filtering.
        seeds,_,_=checked_tracks(previous[0],image(readers[0],maps[0],depth_us+20000))
    np.testing.assert_array_equal(seeds[arrays['seed_ids']],arrays['previous'])
    zp,_=sample_disparity_depth(seeds,disparity,valid,calibration['q'])
    np.testing.assert_array_equal(zp[arrays['seed_ids']],arrays['depth_samples'])
    # References are first opened only after the prediction and pose have been computed.
    gd,gv=decode_dsec_disparity(np.asarray(Image.open(gt_path)))
    if gd.shape!=disparity.shape: raise ValueError('Reference/prediction shape mismatch')
    zr,_=sample_disparity_depth(seeds,gd,gv,calibration['q'])
    reference=zr[arrays['seed_ids']]
    metrics=depth_reference_metrics(arrays['depth_samples'],reference,
        focal_baseline=calibration['fx_px']*calibration['baseline_m'])
    inputs=[cp,normpath,gt_path,unique_file(folder,'*_disparity_timestamps.txt'),*map_paths,*event_paths]
    report=dict(status='EXACT_DATE_DEPTH_CONTROL_NOT_CAMERA_POSE_VALIDATION',
        sequence=folder.name,depth_us=depth_us,current_us=end_us,
        date_selection='Fixed from timestamp audit; final historical reference nearest the frozen replay, +58 us; not selected by error',
        reference=gt_path.relative_to(ROOT).as_posix(),metrics=metrics,
        inference_ms=inference_ms,timing_scope='One cold offline depth/tracking/pose control; no YOLO, current stereo, rendering or hashes; not a full-pipeline benchmark',
        model=model,details=details,stereo=StereoConfig().to_dict(),
        versions=dict(opencv=cv2.__version__,numpy=np.__version__),
        input_sha256={p.relative_to(ROOT).as_posix():sha256_file(p) for p in inputs},
        source_sha256={p.relative_to(ROOT).as_posix():sha256_file(p) for p in [Path(__file__),*(ROOT/'src/pfe_events').glob('*.py')]},
        limitations=['One train scene/date, partial reference coverage, conditional errors on surviving tracks.',
            'GT samples use the same rounded-pixel and duplicate rule as prediction; no interpolation.',
            'No GT depth enters pose fitting. No alternative pose, motion recall or causal attribution is established.',
            'The control is shifted by +58 us from the final frozen replay pair; it is not a re-evaluation of saved depths.'])
    output.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(output/'depth_pairs.npz',**arrays,reference_depth_m=reference,
        disparity_px=disparity,valid=valid,reference_disparity_px=gd,reference_valid=gv)
    report['artifact_sha256']={'depth_pairs.npz':sha256_file(output/'depth_pairs.npz')}
    write_json(output/'summary.json',report)
    print(json.dumps(metrics,indent=2))


def project_fixed_pose(points, depths, intrinsic, transform):
    """Project with an already fitted pose, preserving missing/behind-camera points."""
    p,z,k,t=(np.asarray(v,dtype=float) for v in (points,depths,intrinsic,transform))
    if (p.ndim!=2 or p.shape[1:]!=(2,) or z.shape!=(len(p),)
            or k.shape!=(3,3) or t.shape!=(4,4) or not np.isfinite(p).all()
            or not np.isfinite(k).all() or not np.isfinite(t).all()
            or k[0,0]<=0 or k[1,1]<=0
            or not np.allclose(k,[[k[0,0],0,k[0,2]],[0,k[1,1],k[1,2]],[0,0,1]])
            or not np.allclose(t[3],[0,0,0,1])
            or not np.allclose(t[:3,:3].T@t[:3,:3],np.eye(3),atol=1e-6)
            or not np.isclose(np.linalg.det(t[:3,:3]),1)):
        raise ValueError('Finite pixels, matching depths, pinhole K and rigid transform required')
    uv=np.full((len(p),2),np.nan)
    ids=np.flatnonzero(np.isfinite(z)&(z>0))
    xyz=np.column_stack(((p[ids,0]-k[0,2])/k[0,0]*z[ids],
                         (p[ids,1]-k[1,2])/k[1,1]*z[ids],z[ids]))
    moved=xyz@t[:3,:3].T+t[:3,3]
    front=np.isfinite(moved).all(axis=1)&(moved[:,2]>1e-6)
    uv[ids[front]]=(moved[front]@k.T)[:,:2]/moved[front,2,None]
    return uv,np.isfinite(uv).all(axis=1)


def check_depth_projection(output):
    """Use saved exact-date depths and ONE saved transform; no refitting or inference."""
    from pfe_events.geometry import audit_calibration
    source=ROOT/'outputs/focused_truck/depth_exact_20261016'
    sp=source/'summary.json'; ap=source/'depth_pairs.npz'
    saved=json.loads(sp.read_text()); model=saved['model']
    cp=ROOT/'data/raw'/saved['sequence']/'calibration/cam_to_cam.yaml'
    if (sha256_file(ap)!=saved['artifact_sha256']['depth_pairs.npz']
            or sha256_file(cp)!=saved['input_sha256'][cp.relative_to(ROOT).as_posix()]):
        raise ValueError('Saved depth arrays or calibration have changed')
    if (not model['valid'] or model['depth_source']!='predicted'
            or model['depth_us']!=saved['depth_us'] or model['previous_us']!=saved['depth_us']
            or model['current_us']!=saved['current_us']):
        raise ValueError('Valid predicted-depth pose and matching exact dates required')
    c=audit_calibration(cp,require_canonical=True)
    k=np.array([[c['fx_px'],0,c['cx_px']],[0,c['fy_px'],c['cy_px']],[0,0,1.]])
    with np.load(ap,allow_pickle=False) as a:
        p,q,z,r=(a[n].copy() for n in ('previous','current','depth_samples','reference_depth_m'))
    if q.shape!=p.shape or not np.isfinite(q).all(): raise ValueError('Matching observed pixels required')
    t=np.array(model['transform_previous_to_current'])
    begin=time.perf_counter()
    up,mp=project_fixed_pose(p,z,k,t); ur,mr=project_fixed_pose(p,r,k,t)
    paired=np.isfinite(z)&(z>0)&np.isfinite(r)&(r>0)
    common=paired&mp&mr
    if int(paired.sum())!=saved['metrics']['paired']: raise ValueError('Pair support mismatch')
    residual_saved=np.array([np.nan if e is None else e for e in model['residual_px']])
    ep=np.linalg.norm(up-q,axis=1); er=np.linalg.norm(ur-q,axis=1)
    np.testing.assert_allclose(ep,residual_saved,atol=1e-8,rtol=0,equal_nan=True)
    saved_pixels=np.array([[np.nan,np.nan] if v is None else v for v in model['predicted_pixels']],dtype=float)
    np.testing.assert_allclose(up,saved_pixels,atol=1e-8,rtol=0,equal_nan=True)
    # Independent projection API for both depth sources, without invoking any pose solver.
    for zz,uv,mask in [(z,up,mp),(r,ur,mr)]:
        ids=np.flatnonzero(mask)
        if len(ids):
            xyz=np.column_stack(((p[ids,0]-k[0,2])/k[0,0]*zz[ids],(p[ids,1]-k[1,2])/k[1,1]*zz[ids],zz[ids]))
            independent=cv2.projectPoints(xyz,cv2.Rodrigues(t[:3,:3])[0],t[:3,3],k,None)[0].reshape(-1,2)
            np.testing.assert_allclose(uv[ids],independent,atol=1e-7,rtol=0)
    def stats(values):
        return dict(count=len(values),median=float(np.median(values)) if len(values) else None,
            mean=float(np.mean(values)) if len(values) else None,
            p95=float(np.percentile(values,95)) if len(values) else None,
            maximum=float(np.max(values)) if len(values) else None)
    ids=np.flatnonzero(common); shift=np.linalg.norm(ur[common]-up[common],axis=1)
    transitions={}
    for label,threshold in [('rigid_support',1.5),('residual_candidate',3.0)]:
        before=ep[common]<=threshold if label=='rigid_support' else ep[common]>threshold
        after=er[common]<=threshold if label=='rigid_support' else er[common]>threshold
        transitions[label]=dict(threshold_px=threshold,before=int(before.sum()),after=int(after.sum()),
            entered_indices=ids[~before&after].tolist(),left_indices=ids[before&~after].tolist())
    elapsed_ms=(time.perf_counter()-begin)*1000
    report=dict(status='FIXED_POSE_DEPTH_PROJECTION_NOT_MOTION_VALIDATION',
        depth_us=saved['depth_us'],current_us=saved['current_us'],tracks=len(p),paired_depths=int(paired.sum()),
        common_projectable=int(common.sum()),paired_unprojectable=int((paired&~common).sum()),
        predicted_only_projectable=int((paired&mp&~mr).sum()),reference_only_projectable=int((paired&mr&~mp).sum()),
        projection_shift_px=stats(shift),residual_predicted_px=stats(ep[common]),
        residual_reference_depth_px=stats(er[common]),absolute_residual_change_px=stats(abs(er[common]-ep[common])),
        transitions=transitions,transform_previous_to_current=t.tolist(),
        computation_and_verification_ms=elapsed_ms,
        timing_scope='One offline array projection/verification; excludes input loading and hashing, no runtime gain claimed',
        checks=['Original saved residuals and projections reproduced','Both depth projections checked against cv2.projectPoints'],
        limitations=['Pose fitted previously with predicted depth and retained; its bias is not removed.',
            'Reference depth changes projections only; observed tracking remains unvalidated.',
            '83-pair subset is partial, one train date; status changes are not errors or recovered mobile objects.',
            'Conditional residuals are not a pose quality score; GT depths never enter the detector.'],
        input_sha256={x.relative_to(ROOT).as_posix():sha256_file(x) for x in [sp,ap,cp]},
        source_sha256={Path(__file__).relative_to(ROOT).as_posix():sha256_file(Path(__file__))})
    output.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(output/'projection_pairs.npz',point_indices=ids,previous=p,current=q,
        predicted_projection=up,reference_depth_projection=ur,paired_depths=paired,common_projectable=common,
        predicted_residual_px=ep,reference_depth_residual_px=er)
    report['artifact_sha256']={'projection_pairs.npz':sha256_file(output/'projection_pairs.npz')}
    write_json(output/'summary.json',report)
    print(json.dumps({key:report[key] for key in ['common_projectable','paired_unprojectable','projection_shift_px','residual_predicted_px','residual_reference_depth_px','transitions']},indent=2))


def check_point_order(output):
    """One fixed permutation, all points retained; never select a winning pose."""
    from pfe_events.geometry import audit_calibration
    from pfe_events.rigid_motion import estimate_rigid_motion
    from pfe_events.reference_diagnostic import box_support
    cv2.setNumThreads(2)
    report = dict(status='RUNNING', opencv=cv2.__version__, numpy=np.__version__,
        permutation='NumPy default_rng(42).permutation(N), reset per frame; all correspondences retained',
        decision='Do not promote an alternative pose or add a two-fit runtime gate without quality evidence',
        limitations=['One order perturbation is not a confidence interval or pose accuracy.',
                    'The two estimates use the same data and can share a bias.',
                    'Public references are partial train boxes with unresolved RGB/event parallax; no precision/recall.'],
        sources=['https://github.com/opencv/opencv/blob/4.14.0/modules/calib3d/src/ptsetreg.cpp#L158',
                 'https://github.com/opencv/opencv/blob/4.14.0/modules/calib3d/src/solvepnp.cpp#L283'],
        input_sha256={}, source_sha256={}, groups={})
    def record(path):
        report['input_sha256'][path.relative_to(ROOT).as_posix()] = sha256_file(path)
    def compare(arrays, saved, k):
        p, q, z = (arrays[n] for n in ('previous', 'current', 'depth_samples'))
        order = np.random.default_rng(42).permutation(len(p))
        inverse = np.argsort(order)
        np.testing.assert_array_equal(order[inverse], np.arange(len(p)))
        models, costs = [], []
        for selection in (np.arange(len(p)), order):
            started = time.perf_counter()
            model = estimate_rigid_motion(p[selection], q[selection], z[selection], k,
                previous_us=saved['previous_us'], current_us=saved['current_us'],
                depth_us=saved['depth_us'], depth_source=saved['depth_source'])
            costs.append((time.perf_counter()-started)*1000)
            models.append(model)
        if models[0] != saved:
            raise ValueError('Current default estimator does not reproduce saved model')
        aligned = dict(models[1])
        for field in ('point_status', 'residual_px', 'predicted_pixels'):
            aligned[field] = [models[1][field][j] for j in inverse]
        # Check index restoration independently by projecting original-order rays.
        if aligned['valid']:
            ids = np.array([i for i, e in enumerate(aligned['residual_px']) if e is not None], dtype=int)
            xyz = np.column_stack(((p[ids,0]-k[0,2])/k[0,0]*z[ids],
                                   (p[ids,1]-k[1,2])/k[1,1]*z[ids],z[ids]))
            t = np.asarray(aligned['transform_previous_to_current'])
            projected = cv2.projectPoints(xyz, cv2.Rodrigues(t[:3,:3])[0], t[:3,3], k, None)[0].reshape(-1,2)
            np.testing.assert_allclose(projected, np.asarray([aligned['predicted_pixels'][i] for i in ids], dtype=float), atol=1e-7, rtol=0)
        changed = [i for i, (a,b) in enumerate(zip(saved['point_status'], aligned['point_status'])) if a != b]
        return dict(original_model=saved, permuted_model_original_order=aligned,
                    permutation=order.tolist(), changed_point_indices=changed,
                    changed_points=len(changed), fit_ms_original_permuted=costs)
    for group, relative in [('demo','outputs/demo_contract_20261015'),
                            ('public_reference','outputs/demo_border_20261015/reference')]:
        source = ROOT/relative; summary_path = source/'summary.json'; record(summary_path)
        summary = json.loads(summary_path.read_text())
        rows = []
        for index, frame in enumerate(summary['frames']):
            if group == 'demo':
                saved = frame['motion_model']; sequence = summary['sequence']
                stem = f"{frame['timestamp_us']-summary['frames'][0]['timestamp_us']+80000:06d}"
            else:
                saved = frame['inference']['rigid']; sequence = frame['sequence']; stem = frame['id']
                if frame['inference']['status'] == 'INSUFFICIENT_HISTORY':
                    rows.append(dict(id=stem,status='INSUFFICIENT_HISTORY',boxes=len(frame['association']['0']['boxes'])))
                    continue
            calibration_path = ROOT/f'data/raw/{sequence}/calibration/cam_to_cam.yaml'; record(calibration_path)
            c = audit_calibration(calibration_path, require_canonical=True)
            k = np.array([[c['fx_px'],0,c['cx_px']],[0,c['fy_px'],c['cy_px']],[0,0,1.]])
            path = source/f'{stem}.npz'; record(path)
            with np.load(path, allow_pickle=False) as arrays:
                row = compare(arrays, saved, k)
                row.update(id=stem,timestamp_us=frame['timestamp_us'],status='COMPARED')
                if group == 'public_reference':
                    original = frame['association']['0']
                    boxes = [dict(tube_index=b['tube_index'],xyxy=b['reference_xyxy']) for b in original['boxes']]
                    kwargs = dict(points=arrays['current'],depths=arrays['depth_samples'],counts=arrays['current_counts'])
                    repeated = box_support(boxes, statuses=saved['point_status'], **kwargs)
                    if repeated != original: raise ValueError('Saved reference association mismatch')
                    row['association_original'] = original
                    row['association_permuted'] = box_support(boxes, statuses=row['permuted_model_original_order']['point_status'], **kwargs)
            rows.append(row)
        compared = [row for row in rows if row['status']=='COMPARED']
        report['groups'][group] = dict(frames=rows, compared=len(compared),
            frames_with_changes=sum(row['changed_points']>0 for row in compared),
            changed_point_occurrences=sum(row['changed_points'] for row in compared),
            extra_fit_median_ms=float(np.median([row['fit_ms_original_permuted'][1] for row in compared])))
    for path in [Path(__file__), ROOT/'src/pfe_events/rigid_motion.py', ROOT/'src/pfe_events/geometry.py',
                 ROOT/'src/pfe_events/reference_diagnostic.py', ROOT/'src/pfe_events/artifacts.py']:
        report['source_sha256'][path.relative_to(ROOT).as_posix()] = sha256_file(path)
    report['status']='COMPLETE_POINT_ORDER_CHECK_NOT_QUALITY_EVALUATION'
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'summary.json',report)
    print(json.dumps({g:{k:v for k,v in value.items() if k!='frames'} for g,value in report['groups'].items()},indent=2))


def analyze_groups(predictions, errors, common, ids, q, z, gray, support, output):
    """Exact vector decomposition on each of two swap orders; descriptive groups."""
    baseline=predictions['R2_t2'];final=predictions['R3_t3']
    joint=final-baseline
    orders={
        'rotation_then_translation':(predictions['R3_t2']-baseline,final-predictions['R3_t2']),
        'translation_then_rotation':(final-predictions['R2_t3'],predictions['R2_t3']-baseline)}
    s2=errors['R2_t2']<=1.5;s3=errors['R3_t3']<=1.5
    groups={'shared':common&s2&s3,'only_T2':common&s2&~s3,'only_T3':common&~s2&s3,'neither':common&~s2&~s3}
    assert np.array_equal(np.sum(list(groups.values()),axis=0),common.astype(int))
    stats={};closure={}
    for order,(dr,dt) in orders.items():
        np.testing.assert_allclose((dr+dt)[common],joint[common],rtol=0,atol=1e-10)
        closure[order]=float(np.max(np.abs((dr+dt-joint)[common])))
    for name,mask in groups.items():
        selected=ids[mask]
        assert selected.tolist()==support['groups'][name]['point_indices']
        st={'count':len(selected),'point_indices':selected.tolist(),'left':int((q[selected,0]<320).sum()),'right':int((q[selected,0]>=320).sum()),'depth_median_m':float(np.median(z[selected])),'joint_shift_median_px':float(np.median(np.linalg.norm(joint[mask],axis=1))),'orders':{}}
        for order,(dr,dt) in orders.items():
            r,t=dr[mask],dt[mask];nr=np.linalg.norm(r,axis=1);nt=np.linalg.norm(t,axis=1)
            nz=(nr>1e-12)&(nt>1e-12)
            angles=np.degrees(np.arccos(np.clip(np.sum(r[nz]*t[nz],axis=1)/(nr[nz]*nt[nz]),-1,1)))
            st['orders'][order]={'rotation_shift_median_px':float(np.median(nr)),'translation_shift_median_px':float(np.median(nt)),'opposing_count':int((np.sum(r*t,axis=1)<0).sum()),'angle_evaluable':int(nz.sum()),'angle_median_deg':float(np.median(angles)) if nz.any() else None}
        stats[name]=st
    figure=Image.new('RGB',(1480,920),'#102030');d=ImageDraw.Draw(figure)
    title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    d.text((24,18),'Ou rotation et translation se compensent-elles ?',font=title,fill='white')
    d.text((24,58),'Image 3 | memes 264 points | profondeur estimee fixe | groupes definis par le support final <=1,5 px',font=font,fill='#bbcddd')
    colors={'shared':'#ffffff','only_T2':'#60dfff','only_T3':'#ffb634','neither':'#bb8aff'}
    labels={'shared':'Commun aux deux poses','only_T2':'Perdu avec T3','only_T3':'Gagne avec T3','neither':'Aucune des deux poses'}
    im=ImageEnhance.Brightness(Image.fromarray(gray).convert('RGB')).enhance(.5);ink=ImageDraw.Draw(im)
    for name,mask in groups.items():
        for x,y in q[ids[mask]]:ink.ellipse((x-3,y-3,x+3,y+3),fill=colors[name])
    figure.paste(im,(24,105))
    d.text((690,105),'Decomposition : rotation puis translation',font=font,fill='#ffd17a')
    for i,(name,st) in enumerate(stats.items()):
        y=145+i*107;a=st['orders']['rotation_then_translation']
        lines=[f"{labels[name]} : {st['count']} points",f"Profondeur mediane : {st['depth_median_m']:.2f} m | G/D : {st['left']}/{st['right']}",f"R : {a['rotation_shift_median_px']:.2f} px | t : {a['translation_shift_median_px']:.2f} px | ensemble : {st['joint_shift_median_px']:.2f} px",f"Directions opposees : {a['opposing_count']}/{st['count']} | angle median : {a['angle_median_deg']:.1f} deg"]
        for j,line in enumerate(lines):d.text((690,y+j*24),line,font=small,fill=colors[name] if j==0 else '#d3dfea')
    notes=['R et t mesurent ici des changements de projection entre hypotheses, pas les mouvements physiques des objets.',
           'Le groupe commun est plus lointain en profondeur estimee ; les groupes perdus/gagnes sont surtout proches.',
           'Ce sont des groupes choisis apres observation : profondeur, position et appartenance au support varient ensemble.',
           'La decomposition vectorielle se referme exactement point par point. Les medianes des normes ne s additionnent pas.',
           'Les deux ordres de remplacement sont verifies et conserves dans le JSON ; leurs composantes peuvent differer.',
           'Aucune pose de reference, aucune annotation de mobilite, aucune correction automatique du detecteur.']
    for i,line in enumerate(notes):d.text((24,625+i*42),line,font=font if i==0 else small,fill='#ffd17a' if i==0 else '#bbcddd')
    figure.save(output/'groups.png')
    return {'groups':stats,'vector_closure_max_error_px':closure,'definition':'Projection changes between saved/mixed poses, not physical velocity. Groups defined post hoc by final residual <=1.5 px. Both swap orders checked; depth is predicted and confounded with location/support.'}


def analyze_depth_sensitivity(p, ids, common, k, transforms, support, output):
    """Counterfactual depths with fixed rays, poses and original group membership."""
    depths=np.array([10.,15.,30.,50.,100.])  # Fixed diagnostic grid, not fitted.
    selected=ids[common]
    rays=np.column_stack((p[selected],np.ones(len(selected))))@np.linalg.inv(k).T
    groups={'all':np.ones(len(selected),dtype=bool)}
    groups.update({name:np.isin(selected,st['point_indices']) for name,st in support['groups'].items()})
    arrays={'depths_m':depths,'point_indices':selected};rows=[];max_error=0.
    pure_rotation=[]
    for depth in depths:
        xyz=rays*depth;pred={}
        for i,j in [(0,0),(1,0),(0,1),(1,1)]:
            name=f'R{i+2}_t{j+2}';r=transforms[i][:3,:3];t=transforms[j][:3,3]
            moved=xyz@r.T+t
            assert np.isfinite(moved).all() and (moved[:,2]>0).all()
            uv=(moved@k.T)[:,:2]/moved[:,2,None]
            expected=cv2.projectPoints(xyz,cv2.Rodrigues(r)[0],t,k,np.zeros(5))[0].reshape(-1,2)
            np.testing.assert_allclose(uv,expected,rtol=0,atol=1e-8)
            max_error=max(max_error,float(np.max(np.abs(uv-expected))))
            pred[name]=uv;arrays[f'z{int(depth)}_'+name]=uv
        dr=pred['R3_t2']-pred['R2_t2'];dt=pred['R3_t3']-pred['R3_t2']
        joint=pred['R3_t3']-pred['R2_t2']
        np.testing.assert_allclose(dr+dt,joint,rtol=0,atol=1e-10)
        stats={name:{'count':int(mask.sum()),'rotation_median_px':float(np.median(np.linalg.norm(dr[mask],axis=1))),
                     'translation_median_px':float(np.median(np.linalg.norm(dt[mask],axis=1))),
                     'joint_median_px':float(np.median(np.linalg.norm(joint[mask],axis=1)))} for name,mask in groups.items()}
        rows.append({'hypothetical_depth_m':float(depth),'groups':stats})
        rotated=xyz@transforms[0][:3,:3].T
        pure_rotation.append((rotated@k.T)[:,:2]/rotated[:,2,None])
    for uv in pure_rotation[1:]:np.testing.assert_allclose(uv,pure_rotation[0],rtol=0,atol=1e-10)
    pure_error=max(float(np.max(np.abs(uv-pure_rotation[0]))) for uv in pure_rotation)
    np.savez_compressed(output/'depth_sensitivity.npz',**arrays)
    figure=Image.new('RGB',(1360,760),'#102030');d=ImageDraw.Draw(figure)
    title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    d.text((24,20),'Sensibilite a la profondeur : un controle geometrique',font=title,fill='white')
    notes=['264 rayons fixes | poses T2/T3 fixes | meme profondeur hypothetique pour tous les points',
           'Effet translation : R3,t2 -> R3,t3. Valeurs = medianes des deplacements de projection, en pixels.']
    for i,line in enumerate(notes):d.text((24,65+i*32),line,font=font,fill='#bbcddd')
    headers=['Profondeur','Tous (264)','Communs (147)','Perdus (45)','Gagnes (48)','Autres (24)']
    columns=[24,230,445,680,900,1120]
    for x,label in zip(columns,headers):d.text((x,160),label,font=font,fill='#ffd17a')
    for index,row in enumerate(rows):
        values=[f"{row['hypothetical_depth_m']:.0f} m"]+[f"{row['groups'][g]['translation_median_px']:.3f}" for g in ['all','shared','only_T2','only_T3','neither']]
        for x,value in zip(columns,values):d.text((x,215+index*53),value,font=font,fill='white')
    notes=['Les groupes restent ceux du diagnostic initial ; ils ne sont pas recalcules avec les profondeurs artificielles.',
           'A profondeur egale, les differences restantes viennent des rayons / positions dans l image pour ces poses.',
           'Ce test ne choisit pas une profondeur correcte, ne corrige pas la pose et ne prouve aucun objet mobile.',
           'Le JSON conserve aussi les effets rotation et total. La rotation pure sans translation est invariante en profondeur.',
           'Projections controlees independamment avec OpenCV. Aucun nouveau seuil ni ajustement du detecteur.']
    for i,line in enumerate(notes):d.text((24,490+i*45),line,font=font,fill='#bbcddd' if i!=2 else '#ffd17a')
    figure.save(output/'depth_sensitivity.png')
    return {'depth_grid_m':depths.tolist(),'evaluated':len(selected),'rows':rows,
            'independent_projection_max_error_px':max_error,'pure_rotation_depth_invariance_max_error_px':pure_error,
            'definition':'Synthetic uniform depths on fixed previous-image rays. Original groups frozen. Rotation-then-translation decomposition; no residual classification or accuracy measurement.',
            'limitations':['Depth values are hypotheses, not corrected measurements or ground truth.','Saved poses concern shifted time intervals; no reference camera trajectory.','Single pair, selected projectable points; no conclusion about generalization or object mobility.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--check-point-order',action='store_true',help='Compare the same saved data with one fixed permutation; existing demo and public references only')
    mode.add_argument('--check-exact-depth',action='store_true',help='One exact DSEC depth date; references used after inference only')
    mode.add_argument('--check-depth-projection',action='store_true',help='Project saved paired depths with the same saved pose; no refitting')
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh output directory')
    if args.check_depth_projection:
        check_depth_projection(args.output)
        return
    if args.check_exact_depth:
        check_exact_depth(args.output)
        return
    if args.check_point_order:
        check_point_order(args.output)
        return
    source=ROOT/'outputs/focused_truck/integrated_03'
    support_path=ROOT/'outputs/focused_truck/pose_support_01/summary.json'
    support=json.loads(support_path.read_text())
    paths=[source/'100000.json',source/'120000.json',source/'120000.npz']
    for path in paths:
        assert sha256_file(path)==support['input_sha256'][str(path.relative_to(ROOT))]
    rows=[json.loads(p.read_text()) for p in paths[:2]]
    assert rows[1]['timestamp_us']-rows[0]['timestamp_us']==20000
    assert all(r['motion_model']['valid'] for r in rows)
    transforms=[np.array(r['motion_model']['transform_previous_to_current'],dtype=float) for r in rows]
    k=np.array(support['intrinsic'],dtype=float)
    with np.load(paths[2],allow_pickle=False) as a:
        p,q,z,gray=[a[n].copy() for n in ('previous','current','depth_samples','rectified')]
    valid=np.isfinite(z)&(z>0)&np.isfinite(p).all(axis=1)&np.isfinite(q).all(axis=1)
    ids=np.flatnonzero(valid)
    xyz=(np.column_stack((p[valid],np.ones(valid.sum())))@np.linalg.inv(k).T)*z[valid,None]
    predictions={};errors={};masks={};verification={};arrays={'point_indices':ids}
    for i,j in [(0,0),(1,0),(0,1),(1,1)]:
        name=f'R{i+2}_t{j+2}';r=transforms[i][:3,:3];t=transforms[j][:3,3]
        assert np.allclose(r.T@r,np.eye(3),atol=1e-8) and np.isclose(np.linalg.det(r),1)
        moved=xyz@r.T+t
        mask=np.isfinite(moved).all(axis=1)&(moved[:,2]>0)
        uv=np.full((len(ids),2),np.nan);uv[mask]=(moved[mask]@k.T)[:,:2]/moved[mask,2,None]
        expected=cv2.projectPoints(xyz[mask],cv2.Rodrigues(r)[0],t,k,np.zeros(5))[0].reshape(-1,2)
        np.testing.assert_allclose(uv[mask],expected,rtol=0,atol=1e-8)
        verification[name]=float(np.max(np.abs(uv[mask]-expected)))
        predictions[name]=uv;masks[name]=mask;errors[name]=np.linalg.norm(uv-q[valid],axis=1)
        arrays[name+'_projection']=uv;arrays[name+'_residual']=errors[name]
    common=np.logical_and.reduce(list(masks.values()))
    assert common.sum()==support['common_evaluated']
    saved=np.array([np.nan if v is None else v for v in rows[1]['motion_model']['residual_px']])
    np.testing.assert_allclose(errors['R3_t3'][common],saved[ids[common]],rtol=0,atol=1e-8)
    cases={}
    for name,e in errors.items():
        cases[name]={'support_le_1_5':int((e[common]<=1.5).sum()),'candidates_gt_3':int((e[common]>3).sum()),'median_residual_px':float(np.median(e[common])),'unprojectable':int((~masks[name]).sum())}
    assert cases['R2_t2']['support_le_1_5']==support['support_T2']['count']
    assert cases['R3_t3']['support_le_1_5']==support['support_T3']['count']
    effects={}
    for label,a,b in [('rotation_at_t2','R2_t2','R3_t2'),('rotation_at_t3','R2_t3','R3_t3'),('translation_at_R2','R2_t2','R2_t3'),('translation_at_R3','R3_t2','R3_t3'),('joint_change','R2_t2','R3_t3')]:
        delta=predictions[b][common]-predictions[a][common]
        effects[label]={'median_projection_shift_px':float(np.median(np.linalg.norm(delta,axis=1))), 'support_changes':int(((errors[a][common]<=1.5)!=(errors[b][common]<=1.5)).sum()),'candidate_changes':int(((errors[a][common]>3)!=(errors[b][common]>3)).sum())}
    assert effects['joint_change']['support_changes']==93 and effects['joint_change']['candidate_changes']==81
    interaction=predictions['R3_t3']-predictions['R3_t2']-predictions['R2_t3']+predictions['R2_t2']
    arrays['common']=common;arrays['interaction_projection_px']=interaction
    report={'status':'VERIFIED_FACTORIAL_PROJECTION_DIAGNOSTIC','frame':3,'timestamp_us':rows[1]['timestamp_us'],'depth_us':rows[1]['motion_model']['depth_us'],'tracks':len(p),'evaluated_common':int(common.sum()),'unknown':len(p)-int(common.sum()),'cases':cases,'effects':effects,'interaction_median_px':float(np.median(np.linalg.norm(interaction[common],axis=1))),'independent_projection_max_error_px':verification,'transforms':{'T2':transforms[0].tolist(),'T3':transforms[1].tolist()},'input_sha256':{str(path.relative_to(ROOT)):sha256_file(path) for path in paths+[support_path]},'source_sha256':sha256_file(Path(__file__)),'limitations':['Same frame-3 correspondences and estimated starting depths; no refit and no reference camera pose.','T2 and T3 describe different 100 ms intervals shifted by 20 ms. Mixed transforms are numerical hypotheses, not measured physical camera trajectories.','Rotation/translation swaps are expressed in the existing camera-coordinate convention; t is not the camera centre.','Threshold counts are nonlinear. Projection interactions and cancellation prevent assigning percentages of physical causality.','Support <=1.5 px is final residual support, not RANSAC membership; candidates >3 px are not confirmed moving objects.']}
    canvas=Image.new('RGB',(1360,1320),'#102030');d=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27)
    d.text((24,16),'Rotation et translation : quatre hypotheses sur les memes points',font=title,fill='white')
    d.text((24,54),f'Image 3 | {common.sum()} points communs | profondeur et suivi fixes | aucun nouvel ajustement de pose',font=font,fill='#b7c8d8')
    for index,name in enumerate(['R2_t2','R3_t2','R2_t3','R3_t3']):
        x=24+(index%2)*672;y=95+(index//2)*550
        st=cases[name];d.text((x,y),f"{name} : support {st['support_le_1_5']} | candidats {st['candidates_gt_3']}",font=font,fill='#ffd17a')
        im=ImageEnhance.Brightness(Image.fromarray(gray).convert('RGB')).enhance(.5);ink=ImageDraw.Draw(im)
        for point,e in zip(q[ids[common]],errors[name][common]):
            a,b=point;color='#ffb634' if e>3 else ('#25cf9b' if e<=1.5 else '#d9e0e8')
            ink.ellipse((a-2,b-2,a+2,b+2),fill=color)
        canvas.paste(im,(x,y+32))
    d.text((24,1190),'Vert : residu <=1,5 px | blanc : entre 1,5 et 3 px | orange : >3 px. Points inconnus non affiches.',font=small,fill='white')
    d.text((24,1220),'R2_t2 et R3_t3 : poses sauvegardees. R3_t2 et R2_t3 : combinaisons artificielles pour le diagnostic.',font=small,fill='#b7c8d8')
    d.text((24,1250),'La comparaison ne designe pas la bonne pose et ne confirme pas la mobilite des objets.',font=font,fill='#ffd17a')
    d.text((24,1284),'t est la translation de la transformation des points ; ce n est pas directement la position de la camera.',font=small,fill='#b7c8d8')
    args.output.mkdir(parents=True)
    report['group_analysis']=analyze_groups(predictions,errors,common,ids,q,z,gray,support,args.output)
    report['depth_sensitivity']=analyze_depth_sensitivity(p,ids,common,k,transforms,support,args.output)
    canvas.save(args.output/'comparison.png');np.savez_compressed(args.output/'projections.npz',**arrays)
    report['artifact_sha256']={name:sha256_file(args.output/name) for name in ('comparison.png','groups.png','projections.npz','depth_sensitivity.png','depth_sensitivity.npz')}
    write_json(args.output/'summary.json',report)
    print(json.dumps({'cases':cases,'effects':effects,'interaction_median_px':report['interaction_median_px']},indent=2))


if __name__=='__main__':main()
