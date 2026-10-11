"""ROI response diagnostics from reviewed human annotations, not object AP."""

SCHEMA = 'pfe-motion-annotation-v1'


def _integer(value):
    return type(value) is int


def _box(box, width, height):
    return (isinstance(box, list) and len(box) == 4
            and all(_integer(v) for v in box)
            and 0 <= box[0] < box[2] <= width
            and 0 <= box[1] < box[3] <= height)


def _matches(regions, roi):
    # Fixed criterion: the proposal centre lies in the manually specified ROI.
    return any(roi[0] <= (r['xyxy'][0]+r['xyxy'][2])/2 < roi[2]
               and roi[1] <= (r['xyxy'][1]+r['xyxy'][3])/2 < roi[3]
               for r in regions)


def evaluate_annotations(manifest, annotations, predictions, horizon_us=200_000):
    """Return per-ROI metrics; overlapping annotations are never pooled.

    Delay is in recorded event time, excluding CPU/queue/display latency.
    An alert episode requires a valid inactive predecessor. Active output at
    the clip boundary or after abstention is left-censored, reported separately.
    """
    if manifest.get('schema') != SCHEMA or annotations.get('schema') != SCHEMA:
        raise ValueError('Unsupported annotation schema')
    if not _integer(horizon_us) or horizon_us <= 0:
        raise ValueError('Positive integer horizon required')
    clips = {c['id']: c for c in manifest['clips']}
    if len(clips) != len(manifest['clips']):
        raise ValueError('Duplicate clip IDs')
    results, excluded = [], []
    for number, annotation in enumerate(annotations['annotations']):
        clip_id, kind = annotation.get('clip_id'), annotation.get('kind')
        if clip_id not in clips or kind not in ('onset', 'negative', 'already_moving', 'uncertain'):
            raise ValueError('Unknown clip or annotation kind')
        if type(annotation.get('reviewed')) is not bool:
            raise ValueError('Explicit reviewed flag required')
        if not isinstance(annotation.get('annotator'), str) or not annotation['annotator'].strip():
            raise ValueError('Named annotator required')
        if annotation.get('source') != 'manual_blind_event_clip':
            raise ValueError('Expected blind manual annotations')
        if not annotation['reviewed'] or kind in ('uncertain', 'already_moving'):
            excluded.append({'annotation_index': number, 'clip_id': clip_id,
                             'reason': 'UNREVIEWED' if not annotation['reviewed'] else kind.upper()})
            continue
        clip = clips[clip_id]
        roi = annotation.get('roi_xyxy')
        if not _box(roi, manifest['width'], manifest['height']):
            raise ValueError('Integer nonempty native ROI required')
        rows = [r for r in predictions[clip_id] if not r['warmup']]
        expected = [f['end_us'] for f in clip['frames']]
        if [r['end_us'] for r in rows] != expected or not rows:
            raise ValueError('Predictions must cover exactly the ordered manifest frames')
        step = clip['step_us']
        if (not _integer(step) or step <= 0 or expected[-1] != clip['end_us']
                or expected != list(range(clip['start_us']+step, clip['end_us']+1, step))):
            raise ValueError('Expected contiguous fixed-duration frames')
        states = []
        for row in rows:
            model = row['motion']
            if type(model['valid']) is not bool:
                raise ValueError('Explicit model validity required')
            if not all(_box(r['xyxy'], manifest['width'], manifest['height']) for r in model['regions']):
                raise ValueError('Malformed predicted region')
            states.append(_matches(model['regions'], roi) if model['valid'] else None)
        count_valid = sum(s is not None for s in states)
        result = {'annotation_index': number, 'clip_id': clip_id, 'split': clip['split'],
                  'kind': kind, 'roi_xyxy': roi, 'valid_fraction': count_valid/len(rows),
                  'valid_roi_seconds': count_valid*step/1e6}
        if kind == 'negative':
            episodes, censored = 0, 0
            previous = None
            for state in states:
                if state is True:
                    episodes += previous is False
                    censored += previous is None
                previous = state
            # Denominator only includes valid pairs, where a new episode is observable.
            transition_seconds = sum(a is not None and b is not None
                                     for a, b in zip(states, states[1:]))*step/1e6
            result.update(status='EVALUATED' if count_valid else 'NO_VALID_OUTPUT',
                          false_alert_frame_fraction=(sum(s is True for s in states)/count_valid
                                                      if count_valid else None),
                          false_alert_seconds=sum(s is True for s in states)*step/1e6,
                          confirmed_false_alert_starts=episodes,
                          left_censored_active_segments=censored,
                          observable_transition_seconds=transition_seconds,
                          false_alert_starts_per_observable_second=(episodes/transition_seconds
                                                                    if transition_seconds else None))
        else:
            interval = annotation.get('onset_interval_us')
            if (not isinstance(interval, list) or len(interval) != 2
                    or not all(_integer(v) for v in interval)
                    or not clip['start_us'] <= interval[0] < interval[1] <= clip['end_us']
                    or any((v-clip['start_us']) % step for v in interval)):
                raise ValueError('Onset interval must use clip window boundaries')
            lo, hi = interval
            stop = min(hi+horizon_us, clip['end_us'])
            selected = [i for i, t in enumerate(expected) if lo < t <= stop]
            previous = next((states[i] for i, t in enumerate(expected) if t == lo), None)
            result.update(onset_interval_us=interval, response_horizon_us=horizon_us,
                          observation_truncated=stop < hi+horizon_us,
                          delay_interval_ms=None, first_response_us=None)
            if previous is True:
                result['status'] = 'ALREADY_ACTIVE_BEFORE_ONSET_INTERVAL'
            elif previous is None:
                result['status'] = 'UNKNOWN_PRE_ONSET_STATE'
            else:
                first = next((i for i in selected if states[i] is True), None)
                checked = selected if first is None else [i for i in selected if i <= first]
                if any(states[i] is None for i in checked):
                    result['status'] = 'INSUFFICIENT_COVERAGE'
                elif first is not None:
                    timestamp = expected[first]
                    result.update(status='RESPONSE_OBSERVED', first_response_us=timestamp,
                                  delay_interval_ms=[(timestamp-hi)/1000, (timestamp-lo)/1000])
                else:
                    result['status'] = ('TRUNCATED_WITHOUT_RESPONSE' if result['observation_truncated']
                                        else 'NO_RESPONSE_WITHIN_HORIZON')
        results.append(result)
    return {'schema': 'pfe-motion-evaluation-v1',
            'status': 'EVALUATED_REVIEWED_ROIS' if results else 'NOT_EVALUATED_NO_ELIGIBLE_ANNOTATIONS',
            'matching': 'Proposal centre inside fixed native annotation ROI; not object AP',
            'timing': 'Recorded event time only; CPU, queue and display excluded',
            'aggregation': 'Per annotation only; overlapping ROIs/annotators must not be pooled',
            'results': results, 'excluded_annotations': excluded}
