"""Paced recorded-data replay: release each window only at its recorded end.

This measures output age after window availability, not physical motion onset.
All windows are processed in order; overload is reported, never silently skipped.
"""
import time


def paced_windows(reader, detector, start_us, duration_us, step_us, *,
                  max_wall_seconds=120, clock_ns=time.perf_counter_ns, sleep=time.sleep):
    if (any(type(v) is not int or v <= 0 for v in (duration_us, step_us))
            or type(start_us) is not int or duration_us % step_us
            or max_wall_seconds <= duration_us/1e6):
        raise ValueError('Positive divisible duration/step and sufficient wall budget required')
    count = duration_us//step_us
    origin = clock_ns(); step_ns = step_us*1000
    rows = []
    for index in range(count):
        release = origin+(index+1)*step_ns
        now = clock_ns()
        if now-origin > max_wall_seconds*1e9:
            return rows, {'status': 'WALL_BUDGET_EXCEEDED', 'planned_windows': count,
                          'processed_windows': len(rows), 'wall_seconds': (now-origin)/1e9}
        while now < release:
            sleep((release-now)/1e9)
            now = clock_ns()
        begin = start_us+index*step_us; end = begin+step_us
        before = clock_ns()
        events = reader.window(begin, end)
        loaded = clock_ns()
        result = detector.update(events, begin, end)
        done = clock_ns()
        rows.append({'start_us': begin, 'end_us_exclusive': end,
            'release_ms': (release-origin)/1e6, 'start_ms': (before-origin)/1e6,
            'finish_ms': (done-origin)/1e6, 'read_ms': (loaded-before)/1e6,
            'activity_ms': (done-loaded)/1e6, 'read_activity_ms': (done-before)/1e6,
            'start_lateness_ms': (before-release)/1e6,
            'output_age_after_window_end_ms': (done-release)/1e6,
            'completion_past_next_release': done > release+step_ns,
            'additional_released_windows_waiting_at_start': min(count-index-1, max(0,(before-release)//step_ns)),
            'events': result['events'], 'regions': len(result['regions']),
            'active_fraction': result['active_fraction']})
    return rows, {'status': 'COMPLETE', 'planned_windows': count,
                  'processed_windows': len(rows), 'wall_seconds': (clock_ns()-origin)/1e9}
