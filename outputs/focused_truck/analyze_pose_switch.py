"""Fixed-input sensitivity check for frames 7/8, not a replacement camera pose."""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from pfe_events.artifacts import sha256_file, write_json
from pfe_events.geometry import audit_calibration
from pfe_events.residual_regions import group_residual_regions


def project(p, q, z, intrinsic, transform):
    """Project using saved inputs, preserving unknown/missing depth abstention."""
    p, q, z = (np.asarray(v, dtype=float) for v in (p, q, z))
    xyz = np.column_stack(((p[:,0]-intrinsic[0,2])/intrinsic[0,0]*z,
                           (p[:,1]-intrinsic[1,2])/intrinsic[1,1]*z, z))
    transformed = xyz @ transform[:3,:3].T + transform[:3,3]
    valid = np.isfinite(xyz).all(1) & (z>0) & np.isfinite(transformed).all(1) & (transformed[:,2]>1e-6)
    prediction = np.full(q.shape, np.nan)
    prediction[valid] = (transformed[valid]@intrinsic.T)[:,:2]/transformed[valid,2,None]
    valid &= np.isfinite(prediction).all(1)
    residual = np.full(len(p), np.nan)
    residual[valid] = np.linalg.norm(q[valid]-prediction[valid], axis=1)
    return prediction, residual, valid


def stats(q, z, fb, residual, valid):
    result = {}
    for name, side in [('all',np.ones(len(q),bool)), ('left_x_lt_320',q[:,0]<320), ('right_x_ge_320',q[:,0]>=320)]:
        keep = valid & side
        result[name] = dict(evaluated=int(keep.sum()), candidates=int((keep&(residual>3)).sum()),
            support_le_1_5px=int((keep&(residual<=1.5)).sum()),
            median_residual_px=float(np.median(residual[keep])),
            median_depth_m=float(np.median(z[keep])), median_fb_px=float(np.median(fb[keep])))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Fresh diagnostic output directory')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh output directory')
    source = ROOT/'outputs/focused_truck/integrated_03'
    calibration_path = ROOT/'data/raw/zurich_city_04_b/calibration/cam_to_cam.yaml'
    cal = audit_calibration(calibration_path)
    k = np.array([[cal['fx_px'],0,cal['cx_px']],[0,cal['fy_px'],cal['cy_px']],[0,0,1.]])
    paths = [source/(s+extension) for s in ('200000','220000') for extension in ('.json','.npz')]
    summary_path = source/'summary.json'
    summary = json.loads(summary_path.read_text())
    regions_path = ROOT/'outputs/focused_truck/viewer_02/regions.json'
    saved_regions = json.loads(regions_path.read_text())['frames']
    report = dict(status='FIXED_INPUT_POSE_SENSITIVITY_DIAGNOSTIC',
        input_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in [*paths,calibration_path,summary_path,regions_path]},
        script_sha256=sha256_file(Path(__file__)), intrinsic=k.tolist(), observed=[],
        method='Use frame-8 p,q,z unchanged; replace only T8 by saved T7. No new pose fit or temporal matching.',
        limitations=['T7 and T8 describe different overlapping 100 ms intervals, shifted by 20 ms.',
                     'Reusing T7 on frame 8 is a numerical sensitivity hypothesis, not a verified camera transform.',
                     'This does not identify the correct pose or isolate the cause of the original pose difference.',
                     'No depth or tracking ground truth; forward/backward consistency is not tracking accuracy.',
                     'Image halves are fixed spatial bins, not static/dynamic labels.',
                     'No production output, threshold, training or annotation is modified.'])
    loaded = []
    for idx, stem in [(6,'200000'),(7,'220000')]:
        row = json.loads((source/(stem+'.json')).read_text())
        assert row == summary['frames'][idx]
        model = row['motion_model']
        assert model['valid'] and model['depth_us']==model['previous_us']
        assert model['current_us']-model['previous_us']==100000
        with np.load(source/(stem+'.npz'),allow_pickle=False) as arrays:
            a = {key:arrays[key].copy() for key in arrays.files}
        transform = np.array(model['transform_previous_to_current'])
        prediction, residual, valid = project(a['previous'],a['current'],a['depth_samples'],k,transform)
        saved_prediction = np.array([[np.nan,np.nan] if v is None else v for v in model['predicted_pixels']])
        saved_residual = np.array([np.nan if v is None else v for v in model['residual_px']])
        np.testing.assert_allclose(prediction,saved_prediction,atol=1e-10,rtol=0,equal_nan=True)
        np.testing.assert_allclose(residual,saved_residual,atol=1e-10,rtol=0,equal_nan=True)
        regions = group_residual_regions(a['current'],residual,model_valid=True)
        assert [(r['xyxy'],r['point_indices']) for r in regions] == [(r['xyxy'],r['point_indices']) for r in saved_regions[idx]['regions']]
        result = dict(image=idx+1,timestamp_us=row['timestamp_us'],previous_us=model['previous_us'],
            tracks=len(a['current']),unknown=int((~valid).sum()),transform=transform.tolist(),
            spatial_stats=stats(a['current'],a['depth_samples'],a['fb_px'],residual,valid), regions=regions)
        report['observed'].append(result)
        loaded.append((a,transform,prediction,residual,valid))
    a7,t7,pred7,res7,valid7 = loaded[0]
    a8,t8,pred8,res8,valid8 = loaded[1]
    assert report['observed'][1]['timestamp_us']-report['observed'][0]['timestamp_us']==20000
    pred_cf,res_cf,valid_cf = project(a8['previous'],a8['current'],a8['depth_samples'],k,t7)
    # Denominator of status comparisons must not change with the transform.
    assert np.array_equal(valid8,valid_cf)
    common = valid8 & valid_cf
    matrix = [[int((common&((res8>3)==old)&((res_cf>3)==new)).sum()) for new in (False,True)] for old in (False,True)]
    changed = common & ((res8>3)!=(res_cf>3))
    regions_cf = group_residual_regions(a8['current'],res_cf,model_valid=True)
    report['frame8_with_T7_hypothesis'] = dict(spatial_stats=stats(a8['current'],a8['depth_samples'],a8['fb_px'],res_cf,valid_cf),
        regions=regions_cf, evaluated=int(common.sum()), changed_status=int(changed.sum()),
        status_matrix_rows_T8_columns_T7_consistent_then_candidate=matrix,
        changed_frame8_point_indices=np.flatnonzero(changed).tolist(),
        median_prediction_difference_px=float(np.median(np.linalg.norm(pred8[common]-pred_cf[common],axis=1))))
    report['pose_parameter_difference'] = dict(translation_vector_difference_m=(t8[:3,3]-t7[:3,3]).tolist(),
        translation_difference_norm_m=float(np.linalg.norm(t8[:3,3]-t7[:3,3])),
        rotation_matrix_difference_deg=float(np.linalg.norm(cv2.Rodrigues(t8[:3,:3]@t7[:3,:3].T)[0])*180/np.pi),
        meaning='Difference of fitted transform parameters for shifted intervals, not camera error, acceleration or object speed')
    # Three panels: actual frame 7, actual frame 8, hypothesis with SAME frame-8 inputs.
    canvas=Image.new('RGB',(1440,845),'#0d1724');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',28)
    draw.text((24,18),'Changer uniquement la pose suffit à redistribuer les candidats',font=title,fill='white')
    draw.text((24,60),'À droite : mêmes points, déplacements et profondeurs que l’image 8 ; seule la transformation est remplacée.',font=font,fill='#c2d1df')
    panels=[('Image 7 · pose T7 enregistrée',a7,res7,report['observed'][0]['regions'],report['observed'][0]['spatial_stats']),
            ('Image 8 · pose T8 enregistrée',a8,res8,report['observed'][1]['regions'],report['observed'][1]['spatial_stats']),
            ('Image 8 · pose T7 : hypothèse',a8,res_cf,regions_cf,report['frame8_with_T7_hypothesis']['spatial_stats'])]
    for slot,(label,a,residual,regions,st) in enumerate(panels):
        x=24+472*slot
        draw.text((x,110),label,font=font,fill='white' if slot<2 else '#ffd17a')
        picture=Image.fromarray(a['rectified']).convert('RGB');ink=ImageDraw.Draw(picture)
        for point in a['current'][np.isfinite(residual)&(residual>3)]:
            px,py=point;ink.ellipse((px-3,py-3,px+3,py+3),fill='#ffb634')
        for region in regions:
            x1,y1,x2,y2=region['xyxy'];ink.rectangle((x1,y1,x2-1,y2-1),outline='#ffb634',width=2)
        canvas.paste(picture.resize((448,336)),(x,146))
        draw.text((x,499),f"{st['all']['candidates']} candidats / {st['all']['evaluated']} points évalués",font=font,fill='#ffd17a')
        draw.text((x,533),f"Moitié gauche : {st['left_x_lt_320']['candidates']} · moitié droite : {st['right_x_ge_320']['candidates']}",font=small,fill='#c2d1df')
        draw.text((x,564),f"Support à 1,5 px : {st['all']['support_le_1_5px']} points",font=small,fill='#c2d1df')
    draw.text((24,619),f"Sur les mêmes {common.sum()} points de l’image 8 : {changed.sum()} changent de statut au seuil conservé de 3 px.",font=font,fill='white')
    draw.text((24,652),f"T8 → T7 : {matrix[1][0]} candidats deviennent compatibles ; {matrix[0][1]} compatibles deviennent candidats.",font=font,fill='white')
    draw.text((24,697),'Les deux poses décrivent des intervalles de 100 ms décalés de 20 ms. Réutiliser T7 est un contrôle de sensibilité.',font=small,fill='#c2d1df')
    draw.text((24,727),'Le déplacement des alertes dépend fortement de la pose. Cela ne prouve pas que T7 est correcte ou que T8 est fausse.',font=small,fill='#ffd17a')
    draw.text((24,757),'Un meilleur consensus global peut expliquer une autre partie de la scène. Aucune pose caméra vraie n’est disponible ici.',font=small,fill='#c2d1df')
    draw.text((24,797),'Diagnostic uniquement : aucun résultat du détecteur remplacé, aucune identité ni mobilité confirmée.',font=small,fill='#c2d1df')
    args.output.mkdir(parents=True)
    canvas.save(args.output/'comparison.png')
    np.savez_compressed(args.output/'frame8_sensitivity.npz',predicted_T8=pred8,predicted_T7=pred_cf,
                        residual_T8=res8,residual_T7=res_cf,valid=common,changed=changed)
    report['artifact_sha256']={name:sha256_file(args.output/name) for name in ('comparison.png','frame8_sensitivity.npz')}
    write_json(args.output/'summary.json',report)
    print(json.dumps({key:report[key] for key in ('pose_parameter_difference','frame8_with_T7_hypothesis')},indent=2))


if __name__=='__main__':
    main()
