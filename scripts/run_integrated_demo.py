"""One DSEC clip: prioritize motion indicators, with dated YOLO/XYZ context.

Offline CPU replay; measure computation separately from rendering and export.
Run in .venv-demo. No training, reference boxes or ground-truth depth are used.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from pfe_events.artifacts import sha256_file


def required_inputs(weights=None):
    """Include the independent anchor check, which is read at the last frame."""
    folder = ROOT/'data/raw/zurich_city_04_b'
    return [Path(weights).resolve() if weights is not None else ROOT/'outputs/colab/Y01_20261003T191753Z/pilot/weights/best.pt',
            ROOT/'outputs/stereo/S01/normalizer.json',
            folder/'calibration/cam_to_cam.yaml',
            *(folder/f'events_{side}/rectify_map.h5' for side in ('left', 'right')),
            *(folder/f'events_{side}/events.h5' for side in ('left', 'right')),
            ROOT/'data/processed/dsec_yolo_pilot_v1/images/train/zurich_city_04_b_36614000936.png']


def check_inputs(weights=None):
    paths = required_inputs(weights)
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError('Missing demo inputs (see README preparation notes):\n- '
                                + '\n- '.join(missing))
    return paths


def verify_inputs(paths):
    """Verify the frozen scene before imports/inference; custom weights stay explicit."""
    manifest = ROOT/'configs/demo_assets.json'
    spec = json.loads(manifest.read_text(encoding='utf-8'))
    defaults = required_inputs()
    entries = spec['files']
    expected = {entry['path']: entry for entry in entries}
    if (spec['schema'] != 1 or len(expected) != len(entries)
            or set(expected) != {p.relative_to(ROOT).as_posix() for p in defaults}):
        raise ValueError('Demo manifest must describe exactly the eight frozen inputs')
    custom_weights = paths[0].resolve() != defaults[0].resolve()
    hashes, failures = {}, []
    for index, path in enumerate(paths):
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        digest = sha256_file(path)
        hashes[key] = digest
        if index == 0 and custom_weights:
            continue  # --weights explicitly selects an experiment, not frozen Y01.
        entry = expected[defaults[index].relative_to(ROOT).as_posix()]
        if path.stat().st_size != entry['bytes'] or digest != entry['sha256']:
            failures.append(str(path))
    if failures:
        raise ValueError('Changed demo inputs; restore the frozen files, not their hashes:\n- '
                         + '\n- '.join(failures))
    return dict(mode='EXPLICIT_CHECKPOINT' if custom_weights else 'FROZEN_Y01',
                verified_frozen_inputs=7 if custom_weights else 8,
                checkpoint_identity='RECORDED_NOT_VERIFIED' if custom_weights else 'VERIFIED',
                manifest_sha256=sha256_file(manifest), sha256=hashes)


def context_due(timestamp_us, first_us, period_us):
    """Fixed dataset-time schedule; never infer a wall-clock rate from it."""
    if (any(type(v) is not int for v in (timestamp_us, first_us, period_us))
            or period_us < 20000 or period_us % 20000
            or timestamp_us < first_us or (timestamp_us-first_us) % 20000):
        raise ValueError('Context period must be a positive multiple of the 20 ms source step')
    return (timestamp_us-first_us) % period_us == 0


def context_metadata(timestamp_us, source_us):
    if (type(timestamp_us) is not int or type(source_us) is not int
            or source_us > timestamp_us):
        raise ValueError('Context must come from an already computed date')
    return dict(updated=source_us == timestamp_us, timestamp_us=source_us,
                age_us=timestamp_us-source_us, age_kind='DATASET_TIME_NOT_SYSTEM_LATENCY',
                geometry='camRect0 at context timestamp; not propagated to current camera',
                objects_policy='Current objects only; older context is referenced, never overlaid')


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
    context = row.get('context', {'updated': True})
    if not context['updated']:
        text(12,646,'YOLO / XYZ non recalcules a cette date ; aucune ancienne boite superposee.','#35ddff')
        text(12,675,f"Dernier contexte : t={context['timestamp_us']} us | age dataset {context['age_us']/1000:.0f} ms",small_font=True)
        text(12,704,'Les positions precedentes ne sont pas transportees dans la camera actuelle.',small_font=True)
    elif not objects:
        text(12,646,'Aucune detection YOLO au seuil 0,25 : aucune position d objet inventee.','#35ddff')
    for index,obj in enumerate(objects[:6]):
        s=obj['surface']; xyz=s['xyz_m']; m=obj['motion_support']
        loc = (f'X={xyz[0]:.2f}  Y={xyz[1]:.2f}  Z={xyz[2]:.2f} m'
               if xyz is not None else f"XYZ indisponible ({s['status']})")
        text(12,642+index*25,f"#{index+1} {obj['class_name']} ({obj['confidence']:.2f}) | {loc} | points residuels {m['RESIDUAL_CANDIDATE']}/{m['tracked_points']}",small_font=True)
    if len(objects)>6: text(12,786,f'{len(objects)-6} autres detections : details dans le JSON.',small_font=True)
    text(12,812,'Numeros propres a cette image ; aucune identite d objet suivie.','#b7c8d8',True)
    cost = row['timing_ms']['full_pipeline']
    budget_status = 'HORS BUDGET' if cost > 20 else 'budget calcul respecte'
    text(12,842,f"CPU | calcul : {cost:.0f} ms / budget 20 ms | {budget_status} | hors rendu/export",'#b7c8d8',True)
    return image


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Fresh output directory (required for replay)')
    parser.add_argument('--check-inputs',action='store_true',help='Verify frozen input sizes and SHA256 without importing inference dependencies or running the replay')
    parser.add_argument('--no-history-cache',action='store_true',help='Recompute history for comparison with the original sequential pipeline')
    parser.add_argument('--opencv-threads',type=int,default=2,help='OpenCV CPU threads (default: 2; use 1 for the sequential control)')
    parser.add_argument('--weights',type=Path,help='Explicit event-trained person/car or person/car/truck checkpoint; default remains Y01')
    parser.add_argument('--context-step-ms',type=int,default=100,
                        help='YOLO/object XYZ period in dataset time (default 100 ms; 20 for every-frame control); motion and internal stereo keep 20 ms steps')
    args=parser.parse_args()
    if args.opencv_threads < 1:
        parser.error('--opencv-threads must be positive')
    if args.context_step_ms < 20 or args.context_step_ms % 20:
        parser.error('--context-step-ms must be a positive multiple of 20')
    if not args.check_inputs and args.output is None:
        parser.error('--output is required for replay')
    inputs=check_inputs(args.weights)
    input_verification=verify_inputs(inputs)
    if args.check_inputs:
        print(f"Verified {input_verification['verified_frozen_inputs']} frozen inputs (sizes/SHA256); "
              f"mode={input_verification['mode']}; runtime dependencies not checked.")
        if input_verification['mode'] == 'EXPLICIT_CHECKPOINT':
            print('Explicit checkpoint SHA256 recorded, not verified against frozen Y01: '
                  + next(iter(input_verification['sha256'].values())))
        return
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
    from pfe_events.artifacts import write_json
    from pfe_events.dsec import load_rectify_map
    from pfe_events.dsec_cached import CachedIndexedDSECReader
    from pfe_events.geometry import audit_calibration
    from pfe_events.representations import (BilinearRectifier, stereo_event_images,
                                            polarity_counts, normalized_event_image)
    from pfe_events.stereo import predict_stereo, StereoConfig
    from pfe_events.object_surface import associate_surface, region_motion_support
    from pfe_events.clip_motion import infer_clip_motion, ClipMotionCache
    from pfe_events.replay_timing import offline_cadence_budget
    settings.update({'sync':False})
    cv2.setNumThreads(args.opencv_threads); torch.set_num_threads(1)
    weights=inputs[0]
    # Same bounded clip as the previous replay, with no previous result as input.
    anchor_us=36614000936
    end_times=range(anchor_us-320000,anchor_us+1,20000)
    folder=ROOT/'data/raw/zurich_city_04_b'
    normalizer_path=ROOT/'outputs/stereo/S01/normalizer.json'
    normalizer=json.loads(normalizer_path.read_text())
    if normalizer['source_split']!='train': raise ValueError('Train-only normalizer required')
    calibration_path=folder/'calibration/cam_to_cam.yaml'
    calibration=audit_calibration(calibration_path, require_canonical=True)
    if calibration['resolution'] != [640, 480]:
        raise ValueError('This frozen demo requires 640x480 event calibration')
    map_paths=[folder/f'events_{side}/rectify_map.h5' for side in ('left','right')]
    maps=[load_rectify_map(p) for p in map_paths]
    rectifier_started=time.perf_counter()
    rectifiers=[BilinearRectifier(m) for m in maps]
    rectifier_setup_ms=(time.perf_counter()-rectifier_started)*1000
    event_paths=[folder/f'events_{side}/events.h5' for side in ('left','right')]
    model=YOLO(str(weights))
    if model.names not in ({0:'person',1:'car'}, {0:'person',1:'car',2:'truck'}):
        raise ValueError(f'Unexpected model classes: {model.names}')
    args.output.mkdir(parents=True)
    sources=[Path(__file__),*(ROOT/'src/pfe_events').glob('*.py')]
    report=dict(status='RUNNING',sequence='zurich_city_04_b',split='train_debug_not_quality_evaluation',
                window_us=50000,motion_interval_us=100000,step_us=20000,
                yolo=dict(checkpoint=str(weights.relative_to(ROOT)) if weights.is_relative_to(ROOT) else str(weights),conf=0.25,iou=0.7,imgsz=640,
                          classes=model.names,representation='native RGB positive,negative,total; frozen S01 scales'),
                versions=dict(torch=torch.__version__,ultralytics=ultralytics.__version__,opencv=cv2.__version__,numpy=np.__version__),
                cpu_execution=dict(opencv_threads=cv2.getNumThreads(),torch_threads=torch.get_num_threads(),
                                   stereo_matching_jobs=2, stereo_executor_workers=1,
                                   representation_jobs=2, representation_worker='same persistent stereo executor'),
                stereo=StereoConfig().to_dict(),
                rectification=dict(method='precomputed bilinear geometry; original event order',
                                   setup_ms=rectifier_setup_ms,
                                   lookup_bytes=sum(a.nbytes for r in rectifiers
                                       for a in (r.keep,r.base,*r.weights))),
                input_sha256=input_verification['sha256'],
                input_verification={k:v for k,v in input_verification.items() if k != 'sha256'},
                context_policy=dict(period_us=args.context_step_ms*1000,first_us=end_times.start,
                    scheduling='Fixed dataset dates; no deadline-driven dropping or adaptive selection',
                    internal_depth='Stereo still computed every 20 ms for exact-date motion history',
                    publication='motion.jsonl flushed before native RGB, current stereo and optional YOLO/XYZ; offline sequential replay, not independent real-time workers'),
                source_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in sources},
                timing_scope='End-to-end CPU computation, frames processed sequentially: event reads/rectified representations, historical stereo/tracking/rigid fit, native RGB, current stereo, then scheduled YOLO/association. Excludes initialization, hashes, motion publication, rendering and export; first YOLO call included. One offline run; HDF5/OS caches active. motion_ready is a cumulative subcost, not an additive stage; native_representation is now a separate additive stage.',
                motion_source='Recomputed from raw events; no prior prediction file is read',
                history_cache=dict(enabled=not args.no_history_cache, max_frames=6,
                    policy='Exact timestamps in this replay only; missing dates recomputed from raw events'),
                history_policy='50 ms images at t-100, t-80, t; depth at t-100 for motion and at t for object XYZ; no future events',
                playback='100 ms per 20 ms source step, 5x slow motion',frames=[])
    report['demo_contract'] = dict(
        requested_step_us=20000, requested_outputs_per_second=50,
        criterion='20 ms comparison budget from source step, not an independently validated motion-onset requirement; no skipped motion frames',
        quality='Independent object motion NOT VALIDATED; residuals are candidates only',
        required_history_us=150000,
        motion_onset_delay_ms=None,
        motion_onset_delay_status='NOT_MEASURED_NO_VALIDATED_ONSET_REFERENCE')
    write_json(args.output/'summary.json',report)
    views=[]
    serial_costs=[]
    last_context_us=None
    try:
        with ExitStack() as stack:
            motion_stream=stack.enter_context((args.output/'motion.jsonl').open('x',encoding='utf-8'))
            stereo_executor=stack.enter_context(ThreadPoolExecutor(max_workers=1,
                                                                  thread_name_prefix='stereo-reverse'))
            readers=[stack.enter_context(CachedIndexedDSECReader(p)) for p in event_paths]
            history_cache=(None if args.no_history_cache else
                           ClipMotionCache(readers,maps,calibration,normalizer))
            for end in end_times:
                index=end-(anchor_us-400000)
                stem=f'{index:06d}'
                begin=time.perf_counter()
                if any(end-50000<r.first_us or end>r.last_us for r in readers):
                    raise ValueError('Incomplete stereo window')
                events=[r.window(end-50000,end) for r in readers]
                _,rectified=stereo_event_images(events,rectifiers,normalizer,
                                                executor=stereo_executor,include_native=False)
                represented=time.perf_counter()
                motion_arrays,motion,motion_details=infer_clip_motion(readers,maps,calibration,
                    normalizer,rectified[0],end_us=end,history_cache=history_cache,
                    stereo_executor=stereo_executor)
                points=motion_arrays['current']; statuses=motion['point_status']
                motion_done=time.perf_counter()
                # Publish current motion evidence before waiting for context.
                # These are residual indicators, never confirmed object mobility.
                motion_stream.write(json.dumps(dict(timestamp_us=end,
                    evidence='INDEPENDENT_MOTION_UNCONFIRMED',motion_model=motion,
                    current_points=points.tolist(),compute_to_motion_ms=(motion_done-begin)*1000),
                    allow_nan=False)+'\n')
                motion_stream.flush()
                published=time.perf_counter()
                # Native RGB serves YOLO/export only; motion uses rectified totals.
                native=normalized_event_image(polarity_counts(events[0]),normalizer)
                native_done=time.perf_counter()
                # Motion needs depth at t-100 ms, not this current depth. Keep
                # current stereo for exact-date future history and current XYZ,
                # but do not delay publication of the already computed motion.
                disparity,valid,_,_=predict_stereo(*rectified,StereoConfig(),executor=stereo_executor)
                if history_cache is not None:
                    history_cache.remember(end,rectified,disparity,valid)
                context_started=time.perf_counter()
                update_context=context_due(end,end_times.start,args.context_step_ms*1000)
                prediction=None
                if update_context:
                    # PIL preserves the frozen RGB event-channel convention.
                    prediction=model.predict(Image.fromarray(native),imgsz=640,conf=.25,iou=.7,
                                             device='cpu',verbose=False,save=False)[0]
                inferred=time.perf_counter()
                objects=[]
                detections=(zip(prediction.boxes.xyxy.cpu().numpy(),prediction.boxes.conf.cpu().numpy(),
                                prediction.boxes.cls.cpu().numpy()) if prediction is not None else ())
                for box,confidence,cls in detections:
                    surface=associate_surface(box,maps[0],disparity,valid,calibration['q'],detection_us=end,depth_us=end)
                    support=region_motion_support(box,maps[0],disparity.shape,points,statuses)
                    objects.append(dict(native_xyxy=box.tolist(),class_id=int(cls),class_name=model.names[int(cls)],
                                        confidence=float(confidence),surface=surface,motion_support=support))
                if update_context:
                    last_context_us=end
                context=context_metadata(end,last_context_us)
                context['result_file']=f'{last_context_us-(anchor_us-400000):06d}.json'
                finished=time.perf_counter()
                row=dict(timestamp_us=end,depth_us=end,motion_us=end,offset_ms=(end-anchor_us)/1000,
                         objects=objects,context=context,stereo_valid_pixels=int(valid.sum()),
                         motion_model=motion,motion_details=motion_details,
                         motion_publication_ms=(published-motion_done)*1000,
                         timing_ms=dict(read_representations=(represented-begin)*1000,yolo=(inferred-context_started)*1000,
                                        native_representation=(native_done-published)*1000,
                                        stereo=(context_started-native_done)*1000,motion=(motion_done-represented)*1000,
                                        association=(finished-inferred)*1000,motion_ready=(motion_done-begin)*1000,
                                        full_pipeline=((motion_done-begin)+(finished-published))*1000))
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
                serial_costs.append((time.perf_counter()-begin)*1000)
                print(stem,'detections',len(objects),'XYZ',sum(o['surface']['xyz_m'] is not None for o in objects),
                      'compute_ms',round(row['timing_ms']['full_pipeline'],1),flush=True)
        views[0].save(args.output/'clip.gif',save_all=True,append_images=views[1:],duration=100,loop=0,optimize=False)
        report['surface_status_counts']=dict(Counter(o['surface']['status'] for f in report['frames'] for o in f['objects']))
        report['detection_count']=sum(len(f['objects']) for f in report['frames'])
        report['context_updates']=sum(f['context']['updated'] for f in report['frames'])
        report['detection_count_scope']='Occurrences on scheduled context dates only; not all motion frames or unique objects'
        stages=report['frames'][0]['timing_ms']
        report['timing_summary_ms']={key:dict(mean=float(np.mean([f['timing_ms'][key] for f in report['frames']])),
            median=float(np.median([f['timing_ms'][key] for f in report['frames']])),
            p95=float(np.percentile([f['timing_ms'][key] for f in report['frames']],95))) for key in stages}
        costs=[f['timing_ms']['full_pipeline'] for f in report['frames']]
        report['compute_budget']=dict(first_frame_ms=costs[0],median_after_first_ms=float(np.median(costs[1:])),
            frames_over_20ms=sum(v>20 for v in costs),frames=len(costs),total_compute_ms=sum(costs),
            serial_compute_outputs_per_second=1000/float(np.mean(costs)),
            meaning='Offline compute throughput; not display FPS, sensor latency or motion-onset delay')
        dates = [f['timestamp_us'] for f in report['frames']]
        report['cadence_budget'] = dict(
            compute_only=offline_cadence_budget(dates, costs, step_us=report['step_us']),
            serial_processing=offline_cadence_budget(dates, serial_costs, step_us=report['step_us']),
            serial_scope='Measured from event read through NPZ export, image rendering, optional preview PNG and frame JSON write; includes first inference. Excludes initialization, input hashes, reader setup, console output, final GIF/summary publication and viewer display.',
            serial_service_ms=dict(mean=float(np.mean(serial_costs)),
                median=float(np.median(serial_costs)),p95=float(np.percentile(serial_costs,95))))
        report['status']='COMPLETE_FRESH_OFFLINE_PIPELINE'
    except Exception as error:
        report.update(status='FAILED',error=repr(error)); raise
    finally:
        report['wall_seconds_before_final_summary'] = time.perf_counter()-run_started
        write_json(args.output/'summary.json',report)


if __name__=='__main__': main()
