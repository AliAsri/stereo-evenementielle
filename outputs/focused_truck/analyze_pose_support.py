"""Spatial audit of final residual support on frame 3, for saved T3 versus T2."""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from pfe_events.artifacts import sha256_file, write_json


def describe(mask, points, depth, fb):
    ids=np.flatnonzero(mask)
    return dict(count=len(ids),point_indices=ids.tolist(),left_count=int((mask&(points[:,0]<320)).sum()),
        right_count=int((mask&(points[:,0]>=320)).sum()),
        depth_median_m=float(np.median(depth[mask])) if len(ids) else None,
        depth_q25_m=float(np.quantile(depth[mask],.25)) if len(ids) else None,
        depth_q75_m=float(np.quantile(depth[mask],.75)) if len(ids) else None,
        fb_median_px=float(np.median(fb[mask])) if len(ids) else None)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Fresh output directory')
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh output directory')
    source=ROOT/'outputs/focused_truck/integrated_03'
    clip=ROOT/'outputs/focused_truck/clip_sensitivity_01'
    row_paths=[source/'100000.json',source/'120000.json']
    array_path=source/'120000.npz'
    clip_report=json.loads((clip/'summary.json').read_text())
    paths=[*row_paths,array_path,clip/'summary.json',clip/'transitions.npz']
    for path in [*row_paths,array_path]:
        assert sha256_file(path)==clip_report['input_sha256'][str(path.relative_to(ROOT))]
    assert sha256_file(clip/'transitions.npz')==clip_report['artifact_sha256']['transitions.npz']
    row2,row3=[json.loads(path.read_text()) for path in row_paths]
    assert row3['timestamp_us']-row2['timestamp_us']==20000
    assert row2['motion_model']['valid'] and row3['motion_model']['valid']
    with np.load(array_path,allow_pickle=False) as a:
        p,q,z,fb,gray=[a[name].copy() for name in ('previous','current','depth_samples','fb_px','rectified')]
    with np.load(clip/'transitions.npz',allow_pickle=False) as a:
        e2=a['image_03_residual_previous_pose'].copy();common=a['image_03_common_valid'].copy()
    e3=np.array([np.nan if v is None else v for v in row3['motion_model']['residual_px']])
    assert np.array_equal(common,np.isfinite(e2)&np.isfinite(e3))
    assert np.array_equal(common,np.isfinite(e2)) and np.array_equal(common,np.isfinite(e3))
    # These are final residual support sets, NOT the original RANSAC fit subset.
    s2=common&(e2<=1.5);s3=common&(e3<=1.5)
    groups=dict(shared=s2&s3,only_T2=s2&~s3,only_T3=s3&~s2,neither=common&~s2&~s3)
    assert np.all(np.sum(np.stack(list(groups.values())),axis=0)==common.astype(int))
    assert int(s3.sum())==row3['motion_model']['inliers']
    hull=float(cv2.contourArea(cv2.convexHull(p[s3].astype(np.float32))))/(640*480)
    assert np.isclose(hull,row3['motion_model']['hull_fraction'],rtol=0,atol=1e-12)
    report=dict(status='FINAL_SUPPORT_SPATIAL_DIAGNOSTIC',image=3,timestamp_us=row3['timestamp_us'],
        depth_us=row3['motion_model']['depth_us'],intrinsic=clip_report['intrinsic'],
        method='Same frame-3 p,q,z; final residual support <=1.5 px under saved T3 versus earlier T2. No refit.',
        input_sha256={str(path.relative_to(ROOT)):sha256_file(path) for path in paths},
        source_sha256={str(path.relative_to(ROOT)):sha256_file(path) for path in (Path(__file__),ROOT/'src/pfe_events/artifacts.py')},
        tracks=len(q),common_evaluated=int(common.sum()),unknown=int((~common).sum()),
        support_T2=describe(s2,q,z,fb),support_T3=describe(s3,q,z,fb),
        groups={name:describe(mask,q,z,fb) for name,mask in groups.items()},
        support_membership_changes=int((s2^s3).sum()),net_support_gain=int(s3.sum()-s2.sum()),
        support_set_iou=float((s2&s3).sum()/(s2|s3).sum()),
        mobility_threshold_changes=int((common&((e2>3)!=(e3>3))).sum()),
        limitations=['Support means final residual <=1.5 px, not a verified static background or original RANSAC fitting subset.',
                     'The 3 px candidate threshold is different from the 1.5 px support threshold.',
                     'T2 was estimated over a different 100 ms interval shifted by 20 ms; its reuse is hypothetical.',
                     'Left/right bins use current rectified x=320 and are not object identities or mobility labels.',
                     'Depth values are stereo estimates at the start of the frame-3 tracking interval, not ground truth.',
                     'Neither correct camera pose nor independent object motion is established; no detector change.'])
    for label in ('shared','only_T2','only_T3','neither'):
        mask=groups[label]
        report['groups'][label]['median_residual_T2_px']=float(np.median(e2[mask])) if mask.any() else None
        report['groups'][label]['median_residual_T3_px']=float(np.median(e3[mask])) if mask.any() else None
    canvas=Image.new('RGB',(1360,1100),'#0d1724');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',28)
    draw.text((24,20),'Un gain de 3 points masque un échange de 93 points de support',font=title,fill='white')
    draw.text((24,62),'Même image 3, mêmes points et profondeurs. Support = résidu final ≤ 1,5 px ; aucune nouvelle estimation.',font=font,fill='#c2d1df')
    cases=[('Pose T2 précédente : hypothèse',s2,groups['only_T2'],'#61dfff','support_T2'),
           ('Pose T3 enregistrée',s3,groups['only_T3'],'#ffb634','support_T3')]
    for i,(heading,support,exclusive,color,key) in enumerate(cases):
        x=24+672*i
        draw.text((x,110),heading,font=font,fill=color)
        picture=ImageEnhance.Brightness(Image.fromarray(gray).convert('RGB')).enhance(.55)
        ink=ImageDraw.Draw(picture)
        ink.line((320,0,320,479),fill='#8295aa',width=1)
        for mask,dot_color,radius in [(common,'#666666',2),(groups['shared'],'#ffffff',3),(exclusive,color,4)]:
            for px,py in q[mask]:ink.ellipse((px-radius,py-radius,px+radius,py+radius),fill=dot_color)
        canvas.paste(picture,(x,145))
        st=report[key]
        draw.text((x,640),f"Support : {st['count']} / {common.sum()} · gauche {st['left_count']} · droite {st['right_count']}",font=font,fill=color)
    draw.text((24,684),'Blanc : 147 points communs. Cyan : 45 propres à T2. Orange : 48 propres à T3. Gris : autres points évalués.',font=small,fill='#c2d1df')
    headers=['Support sur les mêmes points','Total','Gauche','Droite','Profondeur médiane estimée']
    xs=[30,470,620,780,945]
    for x,text in zip(xs,headers):draw.text((x,730),text,font=small,fill='#75d8f3')
    for i,(label,key) in enumerate([('Commun aux deux poses','shared'),('T2 seulement, perdu avec T3','only_T2'),('T3 seulement, gagné avec T3','only_T3'),('Aucune des deux à 1,5 px','neither')]):
        y=770+i*34;st=report['groups'][key]
        if i%2==0:draw.rectangle((24,y-3,1336,y+27),fill='#172b3e')
        for x,text in zip(xs,[label,str(st['count']),str(st['left_count']),str(st['right_count']),f"{st['depth_median_m']:.2f} m"]):
            draw.text((x,y),text,font=small,fill='white')
    draw.text((24,925),'Le support se redistribue : T3 gagne surtout à gauche et perd surtout à droite. Cela ne désigne pas la bonne pose.',font=small,fill='#ffd17a')
    draw.text((24,958),'Les 93 changements de support (1,5 px) diffèrent des 81 changements de statut candidat (3 px).',font=small,fill='#c2d1df')
    draw.text((24,991),'Les profondeurs sont estimées 100 ms avant l’image affichée. Les moitiés de l’image ne sont pas des labels objet/fond.',font=small,fill='#c2d1df')
    draw.text((24,1024),'Deux intervalles décalés de 20 ms ; comparaison hypothétique. Le support final n’est pas le sous-ensemble RANSAC initial.',font=small,fill='#c2d1df')
    draw.text((24,1057),'Aucun réglage, aucune annotation, aucun résultat du détecteur modifié. Mobilité indépendante non confirmée.',font=small,fill='#c2d1df')
    args.output.mkdir(parents=True)
    canvas.save(args.output/'comparison.png')
    report['figure_sha256']=sha256_file(args.output/'comparison.png')
    write_json(args.output/'summary.json',report)
    print(json.dumps({k:report[k] for k in ('common_evaluated','unknown','support_membership_changes','net_support_gain','support_set_iou','mobility_threshold_changes')},indent=2))


if __name__=='__main__':main()
