"""M04 synthetic activity sweep; never reports DSEC motion accuracy."""
import argparse
from collections import defaultdict
import csv
import hashlib
from itertools import product
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from pfe_events.artifacts import sha256_file as digest
from pfe_events.motion import ActivityConfig
from pfe_events.motion_controls import make_control, replay_control


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/motion/M04_controls')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh output directory')
    protocol_path = ROOT/'configs/motion_protocol_v1.json'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    c = protocol['controls']; cv2.setNumThreads(1)
    args.output.mkdir(parents=True)
    sources = ['src/pfe_events/artifacts.py','configs/motion_protocol_v1.json', 'src/pfe_events/motion.py',
               'src/pfe_events/motion_controls.py', 'scripts/run_motion_controls.py']
    hashes = {}
    for name in sources:
        source = ROOT/name; hashes[name] = digest(source)
        target = args.output/'source_snapshot'/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(source.read_bytes())
        if digest(target) != hashes[name]: raise IOError('Source changed during snapshot')
    report = {'experiment': 'M04_controls', 'status': 'RUNNING',
              'utc': datetime.now(timezone.utc).isoformat(), 'code_sha256': hashes,
              'data_kind': c['kind'], 'geometry': [c['width'], c['height']],
              'scope': 'Artificial source onset; not object motion, not real DSEC accuracy, not a CPU latency benchmark',
              'protocol_id': protocol['protocol_id'], 'numpy': np.__version__, 'opencv': cv2.__version__}
    (args.output/'summary.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    records = []; cache = {}; event_hashes = {}; groups = defaultdict(list)
    try:
        for step, persistence, threshold in product(c['steps_us'], c['persistence_us'], c['min_rates']):
            config = ActivityConfig(width=c['width'], height=c['height'], persistence_us=persistence, min_rate=threshold)
            cases = [('local_onset', strength, c['base_onset_us']+step*phase//10, phase)
                     for strength in c['events_per_ms_per_cell'] for phase in c['phase_tenths_of_window']]
            cases += [(kind, 8, c['base_onset_us'], None) for kind in c['negative_cases']]
            for kind, strength, onset, phase in cases:
                key = f'{kind}:{strength}:{onset}'
                if key not in cache:
                    cache[key] = make_control(kind, onset_us=onset, strength=strength,
                        duration_us=c['duration_us'], width=c['width'], height=c['height'],
                        seed=c['noise_seed'], noise_rate=c['noise_events_per_second'])
                    event_hashes[key] = {k: hashlib.sha256(v.astype('<i8').tobytes()).hexdigest()
                                         for k, v in cache[key].items()}
                result, timeline = replay_control(cache[key], config, step, c['duration_us'],
                    onset_us=onset if kind == 'local_onset' else None,
                    roi=c['roi_xyxy'], horizon_us=c['response_horizon_us'])
                record = {'control': kind, 'step_us': step, 'persistence_us': persistence,
                          'min_rate': threshold, 'strength_events_per_ms_per_cell': strength if kind == 'local_onset' else None,
                          'phase_tenths': phase, 'source_start_us': onset if kind != 'empty' else None,
                          'event_key': key, **result}
                records.append(record)
                groups[(kind, step, persistence, threshold, record['strength_events_per_ms_per_cell'])].append(record)
                # Save timelines for the original M01 10 ms/20 ms/20 rate setting.
                if step == 10000 and persistence == 20000 and threshold == 20:
                    folder = args.output/'reference_timelines'; folder.mkdir(exist_ok=True)
                    (folder/f'{kind}_{strength}_{phase}.json').write_text(json.dumps(timeline)+'\n', encoding='utf-8')
        summaries = []
        for (kind, step, persistence, threshold, strength), rows in groups.items():
            delays = [r['delay_event_ms'] for r in rows if r['delay_event_ms'] is not None]
            summaries.append({'control': kind, 'step_us': step, 'persistence_us': persistence,
                'min_rate': threshold, 'strength': strength, 'trials': len(rows),
                'responses': sum(r['response'] is True for r in rows) if kind == 'local_onset' else None,
                'early_alerts': sum(r['early_alert'] for r in rows),
                'conditional_delay_median_ms': float(np.median(delays)) if delays else None,
                'conditional_delay_p95_ms': float(np.percentile(delays, 95)) if delays else None,
                'negative_frame_fraction': rows[0].get('false_alert_frame_fraction')})
        fieldnames = list(dict.fromkeys(k for r in records for k in r))
        with (args.output/'trials.csv').open('w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames); writer.writeheader(); writer.writerows(records)
        (args.output/'trials.json').write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8')
        (args.output/'event_hashes.json').write_text(json.dumps(event_hashes, indent=2)+'\n', encoding='utf-8')
        report.update(status='COMPLETE_SYNTHETIC_CONTROLS_ONLY', trials=len(records),
                      frames=sum(r['frames'] for r in records), groups=summaries,
                      real_motion_delay_ms=None, real_false_alerts_per_second=None,
                      parameter_selection='NONE; sweep diagnostics only')
    except Exception as error:
        report.update(status='FAILED', error=repr(error)); raise
    finally:
        (args.output/'summary.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(report['status'], report['trials'], 'trials', report['frames'], 'frames')
    for row in summaries:
        if row['step_us'] == 10000 and row['persistence_us'] == 20000 and row['min_rate'] == 20:
            print(json.dumps(row))


if __name__ == '__main__': main()
