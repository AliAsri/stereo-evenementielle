import copy
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_reference_diagnostic import infer_pair, StereoConfig
from compare_reference_windows import validate_pairing, aggregate


class EmptyReader:
    def __init__(self, first=0, last=100000):
        self.first_us, self.last_us = first, last
        self.calls = []

    def window(self, begin, end):
        self.calls.append((begin, end))
        assert self.first_us <= begin < end <= self.last_us
        return {k: np.empty(0, dtype=np.uint16) for k in ('x', 'y', 'p')}


class WindowInferenceTests(unittest.TestCase):
    def infer(self, left, right, window, end=50000, step=20000):
        calibration = {'q': [[1, 0, 0, -320], [0, 1, 0, -240],
                              [0, 0, 0, 100], [0, 0, 10, 0]],
                       'fx_px': 100, 'fy_px': 100, 'cx_px': 320, 'cy_px': 240}
        return infer_pair(left, right, [np.zeros((2, 2, 2), np.float32)]*2,
                          calibration, {'scales': [1, 1, 1]}, end, window, step, StereoConfig())

    def test_long_window_startup_reads_no_truncated_stereo(self):
        left, right = EmptyReader(), EmptyReader()
        arrays, result = self.infer(left, right, 50000)
        self.assertEqual(result['status'], 'INSUFFICIENT_HISTORY')
        self.assertEqual(left.calls, [(0, 50000)])
        self.assertEqual(right.calls, [])
        self.assertEqual(result['required_history_us'], 70000)
        self.assertFalse(arrays['depth_valid'].any())

    def test_short_startup_uses_complete_nonoverlapping_past_windows(self):
        left, right = EmptyReader(), EmptyReader()
        arrays, result = self.infer(left, right, 20000)
        self.assertEqual(left.calls, [(30000, 50000), (10000, 30000)])
        self.assertEqual(right.calls, [(10000, 30000)])
        self.assertEqual(result['overlap_us'], 0)
        self.assertEqual(result['depth_us'], result['previous_us'])
        self.assertEqual(result['rigid']['depth_source'], 'predicted')
        self.assertFalse(result['rigid']['oracle'])
        self.assertFalse(result['rigid']['valid'])
        self.assertEqual(len(arrays['current']), 0)

    def test_missing_right_history_also_abstains(self):
        left, right = EmptyReader(), EmptyReader(first=15000)
        _, result = self.infer(left, right, 20000)
        self.assertEqual(result['status'], 'INSUFFICIENT_HISTORY')
        self.assertEqual(right.calls, [])

    def test_incomplete_current_window_is_rejected(self):
        with self.assertRaises(ValueError):
            self.infer(EmptyReader(first=40000), EmptyReader(), 20000)

    def test_invalid_causal_parameters_are_rejected(self):
        for window, step in ((0, 20000), (20000, 0), (20000, 30000), (20000., 20000)):
            with self.subTest(window=window, step=step), self.assertRaises(ValueError):
                self.infer(EmptyReader(), EmptyReader(), window, step=step)


def report_fixture(window):
    protocol = dict(window_us=window, step_us=20000, reference='ref', normalizer='norm',
                    source_manifest='manifest', stereo_reference_config='stereo',
                    roi_margins_px=[-5, 0, 5], geometry='camRect0', association='posthoc',
                    depth='predicted', annotation_policy='not_model_input')
    frames = []
    for seq in ('a', 'b'):
        for index in (1, 134, 267):
            end = index*100000
            frames.append(dict(id=f'{seq}_{index}', sequence=seq, mod_frame=index, timestamp_us=end,
                inference=dict(status='INSUFFICIENT_HISTORY' if index == 1 and window == 50000 else 'PAIR_PROCESSED',
                    current_us=end, previous_us=end-20000, depth_us=end-20000,
                    windows_us=[[end-20000-window, end-20000], [end-window, end]], overlap_us=window-20000)))
    return dict(status='COMPLETE_TRAIN_SUPPORT_DIAGNOSTIC', protocol=protocol, frames=frames,
                stereo={}, tracking={}, rigid={'residual_px': 3}, versions={}, input_sha256={'events': 'abc'},
                source_sha256={k: k for k in ('ref', 'norm', 'manifest', 'stereo', 'src/kernel.py')})


class PairedProtocolTests(unittest.TestCase):
    def test_startup_not_silently_added_to_common_cohort(self):
        long, short = report_fixture(50000), report_fixture(20000)
        common, startup = validate_pairing(long, short, copy.deepcopy(long))
        self.assertEqual(common, ['a_134', 'a_267', 'b_134', 'b_267'])
        self.assertEqual(startup, ['a_1', 'b_1'])

    def test_changed_data_model_and_normalizer_are_rejected(self):
        for key in ('input_sha256', 'rigid', 'source_sha256'):
            long, short = report_fixture(50000), report_fixture(20000)
            short[key] = {'altered': 1}
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_pairing(long, short, copy.deepcopy(long))

    def test_future_depth_and_duplicate_dates_are_rejected(self):
        long, short = report_fixture(50000), report_fixture(20000)
        short['frames'][1]['inference']['depth_us'] += 20000
        with self.assertRaises(ValueError):
            validate_pairing(long, short, copy.deepcopy(long))
        short = report_fixture(20000)
        short['frames'][1] = copy.deepcopy(short['frames'][0])
        with self.assertRaises(ValueError):
            validate_pairing(long, short, copy.deepcopy(long))


if __name__ == '__main__':
    unittest.main()
