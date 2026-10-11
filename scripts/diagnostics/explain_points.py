"""Three post-hoc examples from saved results, not motion annotations or an evaluation."""
import json
from pathlib import Path
import sys
import math
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from pfe_events.artifacts import sha256_file,write_json

out=ROOT/'outputs/focused_truck/inspection_01'
if out.exists() and any(out.iterdir()): raise FileExistsError('Output directory must be empty')
out.mkdir(exist_ok=True)
source=ROOT/'outputs/focused_truck/integrated_03'
cases=[('120000',10,'Camion : compatible','Un grand déplacement peut être expliqué.'),
       ('120000',157,'Zone de façade : résidu','Un résidu peut aussi apparaître sur le décor.'),
       ('260000',13,'Zone du camion : résidu','Le déplacement prédit explique moins ce point.')]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27)
canvas=Image.new('RGB',(1320,925),'#0d1724');draw=ImageDraw.Draw(canvas)
draw.text((18,15),'Déplacement observé et résidu : trois exemples concrets',font=title,fill='white')
draw.text((18,52),'Même extrait, mêmes paramètres. Points choisis après observation ; aucun label de mobilité créé.',font=font,fill='#becfe0')
report={'status':'VERIFIED_POSTHOC_EXAMPLES','source':str(source.relative_to(ROOT)),
        'input_sha256':{},'script_sha256':sha256_file(Path(__file__)),'examples':[],
        'limitations':['Different points, not tracked identities across the two dates',
        'Appearance-based inspection zones, not mobility labels or object masks',
        'No ground-truth camera pose or object speed; explanations remain hypotheses']}
def arrow(a,b,color):
    draw.line((*a,*b),fill=color,width=3)
    theta=math.atan2(b[1]-a[1],b[0]-a[0])
    draw.polygon([tuple(b),(b[0]-9*math.cos(theta-.4),b[1]-9*math.sin(theta-.4)),
                     (b[0]-9*math.cos(theta+.4),b[1]-9*math.sin(theta+.4))],fill=color)
for slot,(stem,i,label,explanation) in enumerate(cases):
    paths=[source/(stem+'.json'),source/(stem+'.npz')]
    for path in paths:report['input_sha256'][str(path.relative_to(ROOT))]=sha256_file(path)
    row=json.loads(paths[0].read_text());model=row['motion_model']
    with np.load(paths[1],allow_pickle=False) as arrays:
        p=arrays['previous'][i].astype(float);q=arrays['current'][i].astype(float)
        z=float(arrays['depth_samples'][i]);image=arrays['rectified'].copy()
    predicted=np.array(model['predicted_pixels'][i],float)
    observed_vector=q-p;predicted_vector=predicted-p;residual_vector=q-predicted
    residual=float(np.linalg.norm(residual_vector))
    assert np.isclose(residual,model['residual_px'][i],rtol=1e-10,atol=1e-10)
    status='RESIDUAL_CANDIDATE' if residual>3 else 'MODEL_CONSISTENT'
    assert model['point_status'][i]==status
    datum=dict(timestamp_us=row['timestamp_us'],offset_ms=row['offset_ms'],
        viewer_frame=int((row['offset_ms']+320)/20)+1,viewer_point=i+1,inspection_label=label,
        previous_pixel=p.tolist(),current_pixel=q.tolist(),predicted_pixel=predicted.tolist(),
        observed_vector_px=observed_vector.tolist(),predicted_vector_px=predicted_vector.tolist(),
        residual_vector_px=residual_vector.tolist(),observed_norm_px=float(np.linalg.norm(observed_vector)),
        predicted_norm_px=float(np.linalg.norm(predicted_vector)),residual_px=residual,
        previous_depth_m=z,status=status)
    report['examples'].append(datum)
    x=14+slot*436
    draw.rounded_rectangle((x,92,x+420,872),radius=9,fill='#142537',outline='#3b5369')
    draw.text((x+12,108),f'{slot+1}. {label}',font=font,fill='white')
    draw.text((x+12,137),f"Image {datum['viewer_frame']} · point {i+1} · {row['offset_ms']:.0f} ms",font=small,fill='#bdcee0')
    left=int(np.clip(q[0]-80,0,480));top=int(np.clip(q[1]-60,0,360))
    crop=Image.fromarray(image).convert('RGB').crop((left,top,left+160,top+120)).resize((384,288))
    cd=ImageDraw.Draw(crop);u=(q[0]-left)*2.4;v=(q[1]-top)*2.4
    cd.ellipse((u-10,v-10,u+10,v+10),outline='#ffbf49' if residual>3 else '#39dbad',width=3)
    canvas.paste(crop,(x+18,172))
    draw.text((x+18,470),f'Point rectifié : ({q[0]:.1f}, {q[1]:.1f}) px',font=small,fill='#bdcee0')
    origin=np.array([x+238,645]); scale=18
    draw.line((x+38,645,x+390,645),fill='#456078');draw.line((x+238,510,x+238,689),fill='#456078')
    arrow(origin,origin+observed_vector*scale,'#ffffff')
    arrow(origin,origin+predicted_vector*scale,'#59d9ff')
    arrow(origin+predicted_vector*scale,origin+observed_vector*scale,'#ffb634')
    draw.text((x+242,650),'origine',font=small,fill='#bdcee0')
    draw.text((x+18,694),'Vecteurs agrandis ×18 ; X droite, Y bas',font=small,fill='#bdcee0')
    draw.text((x+18,726),f"Observé : {datum['observed_norm_px']:.2f} px",font=font,fill='white')
    draw.text((x+18,753),f"Prédit : {datum['predicted_norm_px']:.2f} px",font=font,fill='#59d9ff')
    draw.text((x+18,780),f'Résidu : {residual:.2f} px  |  seuil : 3 px',font=font,fill='#ffbf49' if residual>3 else '#39dbad')
    draw.text((x+18,823),explanation,font=small,fill='white')
draw.text((18,892),'Le résidu est une distance entre deux positions, pas la différence des longueurs. Mobilité non confirmée.',font=font,fill='#ffd17a')
canvas.save(out/'comparison.png')
write_json(out/'examples.json',report)
print(json.dumps(report['examples'],indent=2))
