"""All 16 fixed-input previous-pose controls; descriptive, no new detector rule."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Reuse the preserved projection of the single-pair diagnostic, without its main.
from analyze_pose_switch import ROOT, project
from pfe_events.artifacts import sha256_file, write_json
from pfe_events.geometry import audit_calibration


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Fresh output directory')
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh output directory')
    source=ROOT/'outputs/focused_truck/integrated_03'
    summary_path=source/'summary.json'; summary=json.loads(summary_path.read_text())
    calibration=ROOT/'data/raw/zurich_city_04_b/calibration/cam_to_cam.yaml'
    cal=audit_calibration(calibration)
    k=np.array([[cal['fx_px'],0,cal['cx_px']],[0,cal['fy_px'],cal['cy_px']],[0,0,1.]])
    manifest_path=ROOT/'outputs/focused_truck/viewer_03/manifest.json'
    manifest=json.loads(manifest_path.read_text())
    records={json.loads(p.read_text())['timestamp_us']:p for p in source.glob('[0-9]*.json')}
    helper=Path(__file__).with_name('analyze_pose_switch.py')
    report=dict(status='CLIP_POSE_SENSITIVITY_DIAGNOSTIC',intrinsic=k.tolist(),
        method='For each current image, preserve p,q,z and compare its saved pose with the previous saved pose; no refitting.',
        input_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in (summary_path,calibration,manifest_path)},
        source_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in (Path(__file__),helper,ROOT/'src/pfe_events/geometry.py',ROOT/'src/pfe_events/artifacts.py')},
        limitations=['The two poses describe shifted overlapping intervals, not identical physical camera motion.',
                     'Sensitivity is not pose accuracy, mobility precision, recall or false-alert rate.',
                     'Point indices belong to each current image; totals are point occurrences, not unique tracks.',
                     'Small sensitivity does not establish a correct pose or a static/moving object.',
                     'The two observed value ranges are described after inspecting this clip, not used as an alarm threshold.',
                     'Original predictions, viewer, parameters and annotations remain unchanged.'],transitions=[])
    arrays_out={};previous=None
    assert len(summary['frames'])==17
    for index,row in enumerate(summary['frames']):
        path=records[row['timestamp_us']]; assert json.loads(path.read_text())==row
        for p in (path,path.with_suffix('.npz')):
            name=str(p.relative_to(ROOT)); digest=sha256_file(p)
            assert digest==manifest['input_sha256'][name],name
            report['input_sha256'][name]=digest
        model=row['motion_model']
        assert model['valid'] and model['depth_us']==model['previous_us']
        assert model['current_us']-model['previous_us']==100000
        transform=np.array(model['transform_previous_to_current'])
        with np.load(path.with_suffix('.npz'),allow_pickle=False) as a:
            p,q,z=(a[name].copy() for name in ('previous','current','depth_samples'))
        prediction,residual,valid=project(p,q,z,k,transform)
        saved=np.array([np.nan if v is None else v for v in model['residual_px']])
        saved_prediction=np.array([[np.nan,np.nan] if v is None else v for v in model['predicted_pixels']])
        np.testing.assert_allclose(residual,saved,atol=1e-10,rtol=0,equal_nan=True)
        np.testing.assert_allclose(prediction,saved_prediction,atol=1e-10,rtol=0,equal_nan=True)
        if previous is not None:
            old_row,old_transform=previous
            assert row['timestamp_us']-old_row['timestamp_us']==summary['step_us']==20000
            alternative,alt_residual,alt_valid=project(p,q,z,k,old_transform)
            common=valid&alt_valid
            current_candidate=residual>3; alternative_candidate=alt_residual>3
            changed=common&(current_candidate!=alternative_candidate)
            matrix=[[int((common&(current_candidate==i)&(alternative_candidate==j)).sum())
                     for j in (False,True)] for i in (False,True)]
            transition=dict(from_image=index,to_image=index+1,timestamp_us=row['timestamp_us'],offset_ms=row['offset_ms'],
                current_pose_previous_us=model['previous_us'],previous_pose_current_us=old_row['timestamp_us'],
                tracks=len(p),original_evaluated=int(valid.sum()),hypothesis_evaluated=int(alt_valid.sum()),
                common_evaluated=int(common.sum()),validity_changed=int((valid!=alt_valid).sum()),
                changed_points=int(changed.sum()),changed_percent=float(100*changed.sum()/common.sum()) if common.any() else None,
                original_candidates_common=int((common&current_candidate).sum()),
                hypothesis_candidates_common=int((common&alternative_candidate).sum()),
                candidate_to_consistent=matrix[1][0],consistent_to_candidate=matrix[0][1],
                status_matrix_rows_original_columns_hypothesis=matrix,
                changed_point_indices=np.flatnonzero(changed).tolist(),
                median_prediction_difference_px=float(np.median(np.linalg.norm(prediction[common]-alternative[common],axis=1))) if common.any() else None)
            report['transitions'].append(transition)
            prefix=f'image_{index+1:02d}_'
            for name,arr in [('prediction_previous_pose',alternative),('residual_previous_pose',alt_residual),('common_valid',common),('changed',changed)]:
                arrays_out[prefix+name]=arr
        previous=row,transform
    rows=report['transitions']; percentages=np.array([r['changed_percent'] for r in rows])
    assert len(rows)==16 and np.isfinite(percentages).all()
    # Describe the largest observed gap; do not define or activate a detector threshold.
    ordered=np.sort(percentages); cut=int(np.argmax(np.diff(ordered)))+1
    def span(values): return dict(count=len(values),min_percent=float(values.min()),max_percent=float(values.max()))
    report['statistics']=dict(transitions=16,min_percent=float(percentages.min()),median_percent=float(np.median(percentages)),
        max_percent=float(percentages.max()),changed_point_occurrences=sum(r['changed_points'] for r in rows),
        evaluated_point_occurrences=sum(r['common_evaluated'] for r in rows),
        validity_change_occurrences=sum(r['validity_changed'] for r in rows),
        descriptive_ranges_split_at_largest_observed_gap=dict(lower=span(ordered[:cut]),upper=span(ordered[cut:]),
            meaning='Post-hoc description only; no operational threshold chosen'),
        transition_7_to_8_rank_descending=int(1+np.sum(percentages>rows[6]['changed_percent'])))
    # Ensure the former one-pair diagnostic is reproduced on the exact same arrays.
    former=ROOT/'outputs/focused_truck/pose_switch_01/frame8_sensitivity.npz'
    report['input_sha256'][str(former.relative_to(ROOT))]=sha256_file(former)
    with np.load(former,allow_pickle=False) as old:
        for key,name in [('prediction_previous_pose','predicted_T7'),('residual_previous_pose','residual_T7'),('common_valid','valid'),('changed','changed')]:
            np.testing.assert_array_equal(arrays_out['image_08_'+key],old[name])
    canvas=Image.new('RGB',(1400,1035),'#0d1724');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',28)
    draw.text((24,20),'Sensibilité à la pose : le cas 7 → 8 n’est pas isolé',font=title,fill='white')
    draw.text((24,66),'Pour chaque image : mêmes points et profondeurs, seule la pose est remplacée par la précédente.',font=font,fill='#c2d1df')
    lower,upper=ordered[:cut],ordered[cut:]
    draw.text((24,110),f'{len(upper)} transitions : {upper.min():.1f} à {upper.max():.1f} % de statuts modifiés.',font=font,fill='#ffd17a')
    draw.text((24,142),f'Les {len(lower)} autres : {lower.min():.1f} à {lower.max():.1f} %. Plages observées après analyse, sans seuil d’alarme.',font=font,fill='#c2d1df')
    columns=[28,194,360,570,800,1010,1200]
    headings=['Transition','Évalués','Modifiés','Part modifiée','Candidats T','Hypothèse','Δ préd. méd.']
    for x,label in zip(columns,headings):draw.text((x,210),label,font=small,fill='#75d8f3')
    for i,row in enumerate(rows):
        y=250+i*34
        draw.rectangle((24,y-3,1375,y+27),fill='#244356' if row['to_image']==8 else '#172b3e' if i%2==0 else '#0d1724')
        values=[f"{row['from_image']} → {row['to_image']}",str(row['common_evaluated']),str(row['changed_points']),
                f"{row['changed_percent']:.2f} %",str(row['original_candidates_common']),str(row['hypothesis_candidates_common']),
                f"{row['median_prediction_difference_px']:.2f} px"]
        for x,value in zip(columns,values):draw.text((x,y),value,font=small,fill='white')
    draw.text((24,823),'Candidats T : pose enregistrée de l’image courante. Hypothèse : pose précédente appliquée aux mêmes données.',font=small,fill='#c2d1df')
    draw.text((24,852),'Δ préd. méd. : distance médiane entre les deux positions prédites. Seuil résiduel conservé : strictement > 3 px.',font=small,fill='#c2d1df')
    draw.text((24,888),'Chaque comparaison porte sur deux intervalles de 100 ms décalés de 20 ms. Les observations se recouvrent.',font=small,fill='#c2d1df')
    draw.text((24,922),'Ces pourcentages mesurent une sensibilité, pas une erreur de pose ni une précision de détection.',font=font,fill='#ffd17a')
    draw.text((24,957),'Une faible sensibilité ne prouve pas non plus une pose correcte. Aucune prédiction ni règle de mobilité remplacée.',font=small,fill='#c2d1df')
    draw.text((24,992),'Points redétectés entre les images : les effectifs cumulés ne comptent pas des points ou objets distincts.',font=small,fill='#c2d1df')
    args.output.mkdir(parents=True)
    canvas.save(args.output/'comparison.png')
    np.savez_compressed(args.output/'transitions.npz',**arrays_out)
    report['artifact_sha256']={name:sha256_file(args.output/name) for name in ('comparison.png','transitions.npz')}
    write_json(args.output/'summary.json',report)
    print(json.dumps(report['statistics'],indent=2))


if __name__=='__main__':main()
