"""One DSEC clip: recompute Y01, stereo/XYZ and 100 ms motion from raw events.

Offline CPU replay; measure computation separately from rendering and export.
Run in .venv-demo. No training, reference boxes or ground-truth depth are used.
"""
import argparse
from collections import Counter
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))


def render(native, rectified, points, statuses, objects, row):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB',(1280,880),'#102030')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    def text(x,y,value,color='white',small_font=False):
        draw.text((x,y),value,fill=color,font=small if small_font else font)
    text(12,10,'DSEC | Objets, profondeur et indices de mouvement')
    text(12,36,f"zurich_city_04_b | t={row['timestamp_us']} us | fenetres 50 ms | rejeu ralenti x5",small_font=True)
    text(12,64,'YOLO : image native | cyan = detection')
    text(650,64,'Image rectifiee | orange = residu > 3 px sur 100 ms')
    image.paste(Image.fromarray(native),(0,94))
    image.paste(Image.fromarray(rectified).convert('RGB'),(640,94))
    colors = {'UNKNOWN':'#aaaaaa','MODEL_CONSISTENT':'#25cf9b','RESIDUAL_CANDIDATE':'#ffae30'}
    for (x,y),status in zip(points,statuses):
        draw.ellipse((x+638,y+92,x+642,y+96),fill=colors[status])
    for index,obj in enumerate(objects):
        x1,y1,x2,y2 = obj['native_xyxy']
        draw.rectangle((x1,y1+94,x2,y2+94),outline='#35ddff',width=2)
        label = f"#{index+1}"
        w = draw.textlength(label,font=small)
        tx = max(0,min(x1,640-w-8)); ty = max(94,y1+72)
        draw.rectangle((tx,ty,tx+w+8,ty+21),fill='#102030')
        text(tx+3,ty,label,'#35ddff',True)
        surface = obj['surface']
        if surface['xyz_m'] is not None:
            u,v = surface['rectified_pixel']
            draw.ellipse((u+635,v+89,u+645,v+99),outline='#35ddff',width=2)
            text(u+648,v+94,f'#{index+1}','#35ddff',True)
    text(12,586,'Mouvement propre NON CONFIRME | vert = compatible avec le modele | gris = inconnu','#ffcf70',True)
    text(12,614,'Surface estimee : X droite, Y bas, Z avant (metres) ; ce point peut appartenir au fond.',small_font=True)
    if not objects:
        text(12,646,'Aucune detection YOLO au seuil 0,25 : aucune position d objet inventee.','#35ddff')
    for index,obj in enumerate(objects[:6]):
        s=obj['surface']; xyz=s['xyz_m']; m=obj['motion_support']
        loc = (f'X={xyz[0]:.2f}  Y={xyz[1]:.2f}  Z={xyz[2]:.2f} m'
               if xyz is not None else f"XYZ indisponible ({s['status']})")
        text(12,642+index*25,f"#{index+1} {obj['class_name']} ({obj['confidence']:.2f}) | {loc} | points residuels {m['RESIDUAL_CANDIDATE']}/{m['tracked_points']}",small_font=True)
    if len(objects)>6: text(12,786,f'{len(objects)-6} autres detections : details dans le JSON.',small_font=True)
    text(12,812,'Numeros propres a cette image ; aucune identite d objet suivie.','#b7c8d8',True)
    text(12,842,f"Tout recalcule sur CPU | calcul : {row['timing_ms']['full_pipeline']:.0f} ms | pas source : 20 ms | hors rendu/export",'#b7c8d8',True)
    return image


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Fresh output directory')
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh output directory')
    run_started=time.perf_counter()
    os.environ['YOLO_OFFLINE']='true'
    (ROOT/'outputs/runtime/yolo/Ultralytics').mkdir(parents=True,exist_ok=True)
    os.environ['YOLO_CONFIG_DIR']=str(ROOT/'outputs/runtime/yolo')
    import cv2
    import numpy as np
    import torch
    import ultralytics
    from ultralytics import YOLO, settings
    from PIL import Image
    from pfe_events.artifacts import sha256_file, write_json
    from pfe_events.dsec import load_rectify_map
    from pfe_events.dsec_cached import CachedIndexedDSECReader
    from pfe_events.geometry import audit_calibration
    from pfe_events.representations import polarity_counts, rectified_counts, normalized_event_image
    from pfe_events.stereo import predict_stereo, StereoConfig
    from pfe_events.object_surface import associate_surface, region_motion_support
    from pfe_events.clip_motion import infer_clip_motion
    settings.update({'sync':False})
    cv2.setNumThreads(1); torch.set_num_threads(1)
    weights=ROOT/'outputs/colab/Y01_20261003T191753Z/pilot/weights/best.pt'
    # Same bounded clip as the previous replay, with no previous result as input.
    anchor_us=36614000936
    end_times=range(anchor_us-320000,anchor_us+1,20000)
    folder=ROOT/'data/raw/zurich_city_04_b'
    normalizer_path=ROOT/'outputs/stereo/S01/normalizer.json'
    normalizer=json.loads(normalizer_path.read_text())
    if normalizer['source_split']!='train': raise ValueError('Train-only normalizer required')
    calibration_path=folder/'calibration/cam_to_cam.yaml'
    calibration=audit_calibration(calibration_path)
    map_paths=[folder/f'events_{side}/rectify_map.h5' for side in ('left','right')]
    maps=[load_rectify_map(p) for p in map_paths]
    event_paths=[folder/f'events_{side}/events.h5' for side in ('left','right')]
    model=YOLO(str(weights))
    if model.names!={0:'person',1:'car'}: raise ValueError(f'Unexpected model classes: {model.names}')
    args.output.mkdir(parents=True)
    inputs=[weights,normalizer_path,calibration_path,*map_paths,*event_paths]
    sources=[Path(__file__),*(ROOT/'src/pfe_events').glob('*.py')]
    report=dict(status='RUNNING',sequence='zurich_city_04_b',split='train_debug_not_quality_evaluation',
                window_us=50000,motion_interval_us=100000,step_us=20000,
                yolo=dict(checkpoint=str(weights.relative_to(ROOT)),conf=0.25,iou=0.7,imgsz=640,
                          classes=model.names,representation='native RGB positive,negative,total; frozen S01 scales'),
                versions=dict(torch=torch.__version__,ultralytics=ultralytics.__version__,opencv=cv2.__version__,numpy=np.__version__),
                input_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in inputs},
                source_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in sources},
                timing_scope='Full sequential CPU computation: event reads/representations, YOLO, current stereo, historical stereo, tracking, rigid fit, association. Excludes initialization, hashes, rendering and export; first YOLO call included. One offline run; HDF5/OS caches active.',
                motion_source='Recomputed from raw events; no prior prediction file is read',
                history_policy='50 ms images at t-100, t-80, t; depth at t-100 for motion and at t for object XYZ; no future events',
                playback='100 ms per 20 ms source step, 5x slow motion',frames=[])
    write_json(args.output/'summary.json',report)
    views=[]
    try:
        with ExitStack() as stack:
            readers=[stack.enter_context(CachedIndexedDSECReader(p)) for p in event_paths]
            for end in end_times:
                index=end-(anchor_us-400000)
                stem=f'{index:06d}'
                begin=time.perf_counter()
                if any(end-50000<r.first_us or end>r.last_us for r in readers):
                    raise ValueError('Incomplete stereo window')
                events=[r.window(end-50000,end) for r in readers]
                native=normalized_event_image(polarity_counts(events[0]),normalizer)
                rectified=[normalized_event_image(rectified_counts(e,m)[0],normalizer)[...,2]
                           for e,m in zip(events,maps)]
                represented=time.perf_counter()
                # PIL passes RGB without the BGR-array conversion ambiguity.
                prediction=model.predict(Image.fromarray(native),imgsz=640,conf=.25,iou=.7,
                                         device='cpu',verbose=False,save=False)[0]
                inferred=time.perf_counter()
                disparity,valid,_,_=predict_stereo(*rectified,StereoConfig())
                stereo_done=time.perf_counter()
                motion_arrays,motion,motion_details=infer_clip_motion(readers,maps,calibration,
                    normalizer,rectified[0],end_us=end)
                points=motion_arrays['current']; statuses=motion['point_status']
                motion_done=time.perf_counter()
                objects=[]
                for box,confidence,cls in zip(prediction.boxes.xyxy.cpu().numpy(),
                        prediction.boxes.conf.cpu().numpy(),prediction.boxes.cls.cpu().numpy()):
                    surface=associate_surface(box,maps[0],disparity,valid,calibration['q'],detection_us=end,depth_us=end)
                    support=region_motion_support(box,maps[0],disparity.shape,points,statuses)
                    objects.append(dict(native_xyxy=box.tolist(),class_id=int(cls),class_name=model.names[int(cls)],
                                        confidence=float(confidence),surface=surface,motion_support=support))
                finished=time.perf_counter()
                row=dict(timestamp_us=end,depth_us=end,motion_us=end,offset_ms=(end-anchor_us)/1000,
                         objects=objects,stereo_valid_pixels=int(valid.sum()),
                         motion_model=motion,motion_details=motion_details,
                         timing_ms=dict(read_representations=(represented-begin)*1000,yolo=(inferred-represented)*1000,
                                        stereo=(stereo_done-inferred)*1000,motion=(motion_done-stereo_done)*1000,
                                        association=(finished-motion_done)*1000,full_pipeline=(finished-begin)*1000))
                export_started=time.perf_counter()
                np.savez_compressed(args.output/f'{stem}.npz',native=native,rectified=rectified[0],disparity_px=disparity,valid=valid,
                                    **motion_arrays)
                # Same-date anchor export is an independent channel/preprocessing check.
                if end==anchor_us:
                    export=ROOT/f'data/processed/dsec_yolo_pilot_v1/images/train/zurich_city_04_b_{end}.png'
                    row['native_matches_y00_export']=bool(np.array_equal(native,np.asarray(Image.open(export))))
                    if not row['native_matches_y00_export']: raise ValueError('Y00 representation mismatch')
                view=render(native,rectified[0],points,statuses,objects,row); views.append(view)
                if end==anchor_us: view.save(args.output/'preview.png')
                row['array_export_render_ms']=(time.perf_counter()-export_started)*1000
                write_json(args.output/f'{stem}.json',row)
                report['frames'].append(row)
                print(stem,'detections',len(objects),'XYZ',sum(o['surface']['xyz_m'] is not None for o in objects),
                      'compute_ms',round(row['timing_ms']['full_pipeline'],1),flush=True)
        views[0].save(args.output/'clip.gif',save_all=True,append_images=views[1:],duration=100,loop=0,optimize=False)
        report['surface_status_counts']=dict(Counter(o['surface']['status'] for f in report['frames'] for o in f['objects']))
        report['detection_count']=sum(len(f['objects']) for f in report['frames'])
        stages=report['frames'][0]['timing_ms']
        report['timing_summary_ms']={key:dict(mean=float(np.mean([f['timing_ms'][key] for f in report['frames']])),
            median=float(np.median([f['timing_ms'][key] for f in report['frames']])),
            p95=float(np.percentile([f['timing_ms'][key] for f in report['frames']],95))) for key in stages}
        costs=[f['timing_ms']['full_pipeline'] for f in report['frames']]
        report['compute_budget']=dict(first_frame_ms=costs[0],median_after_first_ms=float(np.median(costs[1:])),
            frames_over_20ms=sum(v>20 for v in costs),frames=len(costs),total_compute_ms=sum(costs),
            serial_compute_outputs_per_second=1000/float(np.mean(costs)),
            meaning='Offline compute throughput; not display FPS, sensor latency or motion-onset delay')
        report['status']='COMPLETE_FRESH_OFFLINE_PIPELINE'
    except Exception as error:
        report.update(status='FAILED',error=repr(error)); raise
    finally:
        report['wall_seconds_before_final_summary'] = time.perf_counter()-run_started
        write_json(args.output/'summary.json',report)


if __name__=='__main__': main()
