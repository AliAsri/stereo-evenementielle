"""Artificial activity controls. No DSEC labels and no physical event simulation."""
import numpy as np
from .motion import ActivityDetector


def make_control(kind, *, onset_us=400_000, strength=8, duration_us=1_000_000,
                 width=128, height=96, seed=42, noise_rate=1000):
    """Same seeded background across positive cases; known activity onset.

    The local source stays in two adjacent cells. It does not model an object
    trajectory, contrast threshold, occlusion, stereo, or camera movement.
    """
    if kind not in ('local_onset', 'empty', 'hot_pixel', 'global_burst'):
        raise ValueError('Unknown control')
    if not 0 <= onset_us < duration_us or width < 48 or height < 48 or strength < 1:
        raise ValueError('Invalid control geometry or time')
    if width % 16 or height % 16 or duration_us % 1000:
        raise ValueError('Whole grid cells and millisecond duration required')
    rng = np.random.default_rng(seed)
    n = int(noise_rate*duration_us/1e6) if kind == 'local_onset' else 0
    x = [rng.integers(0, width, n)]; y = [rng.integers(0, height, n)]
    t = [rng.integers(0, duration_us, n)]
    if kind == 'local_onset':
        ticks = np.arange(onset_us, duration_us, 1000, dtype=np.int64)
        stamp = np.repeat(ticks, 2*strength)
        offset = np.tile(np.repeat([16, 32], strength), len(ticks))
        pixel = (np.arange(len(stamp))//(2*strength)+np.tile(np.arange(2*strength), len(ticks))) % 4
        x.append(offset+1+pixel); y.append(np.full(len(stamp), 33)); t.append(stamp)
    elif kind == 'hot_pixel':
        stamp = np.arange(0, duration_us, 10, dtype=np.int64)
        x.append(np.ones(len(stamp), dtype=np.int64)); y.append(np.ones(len(stamp), dtype=np.int64)); t.append(stamp)
    elif kind == 'global_burst':
        # 4 pixels * 6 events per cell every ms, during a 100 ms burst.
        ticks = np.arange(onset_us, min(onset_us+100_000, duration_us), 1000, dtype=np.int64)
        cx, cy = np.meshgrid(np.arange(0, width, 16), np.arange(0, height, 16))
        bx = np.repeat(cx.ravel(), 24)+np.tile(np.repeat([1, 2, 3, 4], 6), cx.size)
        by = np.repeat(cy.ravel()+1, 24)
        x.append(np.tile(bx, len(ticks))); y.append(np.tile(by, len(ticks)))
        t.append(np.repeat(ticks, len(bx)))
    t = np.concatenate(t).astype(np.int64); order = np.argsort(t, kind='stable')
    return {'x': np.concatenate(x).astype(np.int64)[order],
            'y': np.concatenate(y).astype(np.int64)[order], 't_us': t[order]}


def replay_control(events, config, step_us, duration_us, *, onset_us=None,
                   roi=(16, 32, 48, 48), horizon_us=200_000):
    """Score source activation or negative confounds, in event time only."""
    if step_us <= 0 or duration_us % step_us:
        raise ValueError('Exact positive step divisor required')
    detector = ActivityDetector(config)
    rows = []
    for begin in range(0, duration_us, step_us):
        end = begin+step_us
        lo, hi = np.searchsorted(events['t_us'], [begin, end], side='left')
        out = detector.update({k: v[lo:hi] for k, v in events.items()}, begin, end)
        match = any(roi[0] <= (r['xyxy'][0]+r['xyxy'][2])/2 < roi[2]
                    and roi[1] <= (r['xyxy'][1]+r['xyxy'][3])/2 < roi[3]
                    for r in out['regions'])
        rows.append({'end_us': end, 'roi_active': match,
                     'any_region': bool(out['regions']), 'active_fraction': out['active_fraction']})
    result = {'frames': len(rows), 'any_region_fraction': sum(r['any_region'] for r in rows)/len(rows),
              'delay_event_ms': None, 'first_response_us': None,
              'early_alert': False, 'response': None, 'status': 'NEGATIVE_CONTROL'}
    if onset_us is not None:
        early = any(r['roi_active'] for r in rows if r['end_us'] <= onset_us)
        first = next((r['end_us'] for r in rows
                      if onset_us < r['end_us'] <= onset_us+horizon_us and r['roi_active']), None)
        result.update(early_alert=early, response=(first is not None and not early),
                      status='EARLY_ALERT' if early else ('RESPONSE' if first is not None else 'MISS'),
                      first_response_us=first if not early else None,
                      delay_event_ms=(first-onset_us)/1000 if first is not None and not early else None)
    else:
        states = [r['any_region'] for r in rows]
        starts = sum(b and not a for a, b in zip(states, states[1:]))
        result.update(false_alert_frame_fraction=sum(states)/len(states),
                      false_alert_active_seconds=sum(states)*step_us/1e6,
                      false_alert_starts=starts, left_censored_initial_alert=states[0],
                      false_alert_starts_per_observable_second=(starts/((len(states)-1)*step_us/1e6)
                                                                if len(states) > 1 else None))
    return result, rows
