"""Strict format checks for M13 blind review; does not certify label truth."""
import math

SCHEMA = 'pfe-motion-review-v1'
TARGET = 'observable independent object motion in fixed rectified ROI; uncertainty explicit'


def validate_review(manifest, document):
    if (manifest.get('schema') != SCHEMA or document.get('schema') != SCHEMA
            or manifest.get('target') != TARGET or document.get('target') != TARGET
            or document.get('manifest_id') != manifest.get('manifest_id')
            or not manifest.get('manifest_id')):
        raise ValueError('Review must match exact manifest and target')
    clips = {c['id']: c for c in manifest['clips']}
    if len(clips) != len(manifest['clips']):
        raise ValueError('Duplicate clip IDs')
    for c in clips.values():
        frames=c['frames']
        if (not frames or c['step_us'] != c['window_us'] or c['step_us'] != 20000
                or [f['end_us'] for f in frames] != list(range(c['start_us']+c['step_us'], c['end_us']+1, c['step_us']))
                or any(f['start_us'] != f['end_us']-c['window_us'] for f in frames)):
            raise ValueError('Complete nonoverlapping review grid required')
    annotations = document.get('annotations')
    if not isinstance(annotations, list):
        raise ValueError('Annotation list required')
    counts = {'moving':0, 'static':0, 'unknown':0}
    for a in annotations:
        if a.get('clip_id') not in clips or a.get('state') not in counts:
            raise ValueError('Unknown clip or interpretation')
        if (a.get('reviewed') is not True or a.get('source') != 'manual_blind_event_clip'
                or not isinstance(a.get('annotator'),str) or not a['annotator'].strip()
                or not isinstance(a.get('notes'),str) or not a['notes'].strip()
                or a.get('camera_state') not in ('fixed','moving','unknown')):
            raise ValueError('Explicit review, observer, evidence and camera state required')
        box=a.get('roi_xyxy');interval=a.get('frame_interval')
        if (not isinstance(box,list) or len(box)!=4
                or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in box)
                or not 0 <= box[0] < box[2] <= manifest['width']
                or not 0 <= box[1] < box[3] <= manifest['height']):
            raise ValueError('Nonempty in-bounds rectified ROI required')
        clip=clips[a['clip_id']]
        if (not isinstance(interval,list) or len(interval)!=2 or any(type(v) is not int for v in interval)
                or not 0 <= interval[0] <= interval[1] < len(clip['frames'])):
            raise ValueError('Inclusive frame interval required')
        if a.get('roi_valid_for_whole_interval') is not True:
            raise ValueError('ROI must remain relevant for the entire reviewed interval')
        counts[a['state']]+=1
    return dict(status='PENDING_REVIEW' if not annotations else 'FORMAT_VALID_MANUAL_LABELS_NOT_CERTIFIED',
                annotations=len(annotations),counts=counts,real_motion_quality=None)
