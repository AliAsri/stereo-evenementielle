"""M06: retain coarse annotation uncertainty when scoring finer predictions."""
from copy import deepcopy
from .motion_evaluation import SCHEMA, _box, _integer, _matches, evaluate_annotations


def evaluate_multirate(manifest, annotations, predictions, prediction_steps, horizon_us=200_000):
    """Adapt v1 ROI metrics without snapping onset bounds or interpolating outputs.

    Only complete, aligned prediction grids dividing the annotation period are
    supported. Optional active_interval_us is an explicitly reviewed continuous
    movement-in-ROI interval, not inferred from an onset annotation.
    """
    if manifest.get('schema') != SCHEMA or annotations.get('schema') != SCHEMA:
        raise ValueError('Unsupported annotation schema')
    if annotations.get('target') != manifest.get('target') or not manifest.get('target'):
        raise ValueError('Annotation target must match the manifest')
    clips = {c['id']: c for c in manifest['clips']}
    if len(clips) != len(manifest['clips']): raise ValueError('Duplicate clip IDs')
    if set(predictions) != set(clips) or set(prediction_steps) != set(clips):
        raise ValueError('Explicit predictions and cadence required for every selected clip')
    refined = deepcopy(manifest); measured = {}
    for clip in refined['clips']:
        cid = clip['id']; original = clips[cid]; step = prediction_steps[cid]
        coarse = original['step_us']; start, end = original['start_us'], original['end_us']
        if (not all(_integer(v) for v in (coarse,step,start,end)) or coarse <= 0 or step <= 0
                or end <= start or (end-start) % coarse or coarse % step):
            raise ValueError('Prediction step must divide the annotation step on the same time grid')
        if [f['end_us'] for f in original['frames']] != list(range(start+coarse,end+1,coarse)):
            raise ValueError('Invalid annotation frame grid')
        rows = predictions[cid]
        previous = None
        for row in rows:
            timestamp = row['end_us']
            if (not _integer(timestamp) or type(row['warmup']) is not bool or timestamp > end
                    or row['warmup'] != (timestamp <= start)
                    or (timestamp-start) % step
                    or (previous is not None and timestamp-previous != step)):
                raise ValueError('Prediction timestamps/warm-up are inconsistent; interpolation is forbidden')
            model = row['motion']
            if type(model['valid']) is not bool or not isinstance(model['regions'],list):
                raise ValueError('Explicit validity and regions required')
            if not all(_box(r['xyxy'],manifest['width'],manifest['height']) for r in model['regions']):
                raise ValueError('Malformed native predicted box')
            previous = timestamp
        measured[cid] = [r for r in rows if not r['warmup']]
        if [r['end_us'] for r in measured[cid]] != list(range(start+step,end+1,step)):
            raise ValueError('Incomplete prediction grid; use explicit invalid rows for abstention')
        clip['step_us'] = step
        clip['frames'] = [{'end_us':t} for t in range(start+step,end+1,step)]
    seen = set()
    for annotation in annotations['annotations']:
        cid = annotation['clip_id']
        if cid not in clips: raise ValueError('Annotation clip is outside the selected comparison')
        clip = clips[cid]; start, end, coarse = clip['start_us'],clip['end_us'],clip['step_us']
        if not annotation.get('reviewed') or annotation.get('kind') in ('uncertain','already_moving'):
            continue
        if annotation.get('kind') == 'onset':
            onset = annotation.get('onset_interval_us')
            if (not isinstance(onset,list) or len(onset)!=2 or not all(_integer(v) for v in onset)
                    or not start <= onset[0] < onset[1] <= end or any((t-start)%coarse for t in onset)):
                raise ValueError('Onset bounds must retain the original annotation grid')
        active = annotation.get('active_interval_us')
        if active is not None:
            if (annotation.get('kind')!='onset' or not isinstance(active,list) or len(active)!=2
                    or not all(_integer(v) for v in active)
                    or not annotation['onset_interval_us'][1] <= active[0] < active[1] <= end
                    or any((t-start)%coarse for t in active)
                    or annotation.get('continuous_motion_reviewed') is not True):
                raise ValueError('Continuous motion interval needs explicit review on original frame boundaries')
        key = (cid,annotation.get('kind'),tuple(annotation.get('roi_xyxy') or []),
               tuple(annotation.get('onset_interval_us') or []),annotation.get('annotator'))
        if key in seen: raise ValueError('Duplicate reviewed annotation; adjudicate first')
        seen.add(key)
    report = evaluate_annotations(refined,annotations,predictions,horizon_us=horizon_us)
    report.update(schema='pfe-motion-evaluation-v2',
        temporal_policy='Original onset bounds unchanged; score native prediction timestamps; no interpolation',
        continuous_activity_policy='Only on explicitly reviewed active_interval_us; not object tracking recall',
        streams_checked=len(clips))
    for result in report['results']:
        annotation = annotations['annotations'][result['annotation_index']]
        cid=result['clip_id']; step=prediction_steps[cid]
        result['annotation_step_us']=clips[cid]['step_us']; result['prediction_step_us']=step
        result['continuous_motion']={'status':'NOT_ANNOTATED','window_alert_fraction':None,
                                     'valid_fraction':None,'interval_us':None}
        active=annotation.get('active_interval_us')
        if active is None: continue
        selected=[r for r in measured[cid] if active[0] < r['end_us'] <= active[1]]
        valid=[r for r in selected if r['motion']['valid']]
        count=sum(_matches(r['motion']['regions'],annotation['roi_xyxy']) for r in valid)
        result['continuous_motion']={
            'status':'EVALUATED_REVIEWED_INTERVAL' if valid else 'NO_VALID_OUTPUT',
            'interval_us':active,'valid_fraction':len(valid)/len(selected),
            'window_alert_fraction':count/len(valid) if valid else None,
            'evaluated_windows':len(selected),'valid_windows':len(valid),'alert_windows':count,
            'inactive_valid_windows':len(valid)-count,'unknown_windows':len(selected)-len(valid),
            'valid_window_seconds':len(valid)*step/1e6,'alert_window_seconds':count*step/1e6}
    return report
