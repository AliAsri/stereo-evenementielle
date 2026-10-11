"""Behavioral contracts shared by existing experiment entry points."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pfe_events.artifacts import sha256_file, write_json, write_legacy_json, write_unicode_json
from pfe_events.benchmarking import assert_same, warm
from pfe_events.reporting import activity_distribution, paced_distribution, adaptive_distribution, rigid_distribution
from pfe_events.visualization import native_event_image


class ArtifactTests(unittest.TestCase):
    def test_json_bytes_and_unicode_profiles(self):
        value = {'texte': 'événement', 'missing': None, 'values': [1, 0.5]}
        for writer, options, ending in (
            (write_json, {'allow_nan': False}, '\n'),
            (write_legacy_json, {}, '\n'),
            (write_unicode_json, {'allow_nan': False, 'ensure_ascii': False}, ''),
        ):
            with self.subTest(writer=writer.__name__), patch.object(Path, 'write_text') as write:
                writer(Path('result.json'), value)
                write.assert_called_once_with(json.dumps(value, indent=2, **options) + ending, encoding='utf-8')

    def test_strict_nan_failure_does_not_touch_destination(self):
        for writer in (write_json, write_unicode_json):
            with patch.object(Path, 'write_text') as write, self.assertRaises(ValueError):
                writer(Path('existing.json'), {'invalid': float('nan')})
            write.assert_not_called()

    def test_streamed_hash_matches_bytes(self):
        path = Path(__file__)
        self.assertEqual(sha256_file(path), hashlib.sha256(path.read_bytes()).hexdigest())


class ReportingTests(unittest.TestCase):
    def test_historical_report_schemas_and_values(self):
        values = [1.0, 2.0, 3.0, 20.0]
        expected = {'count':4, 'mean':6.5, 'median':2.5, 'p95':float(np.percentile(values,95)),
                    'p99':float(np.percentile(values,99)), 'max':20.0}
        for function, keys in (
            (activity_distribution, ('count','mean','median','p95','max')),
            (paced_distribution, ('count','mean','median','p95','p99','max')),
            (adaptive_distribution, ('count','median','p95','max')),
            (rigid_distribution, ('count','median','p95')),
        ):
            with self.subTest(function=function.__name__):
                self.assertEqual(function(values), {k:expected[k] for k in keys})
        for function in (paced_distribution, adaptive_distribution, rigid_distribution):
            self.assertIsNone(function([]))


class BenchmarkUtilityTests(unittest.TestCase):
    def test_equivalence_detects_dtype_and_value_changes(self):
        before = {'mask':np.array([1,0],dtype=np.uint8), 'status':'OK'}
        assert_same(before, {'mask':before['mask'].copy(), 'status':'OK'})
        for after in ({'mask':np.array([1,0],dtype=np.int64), 'status':'OK'},
                      {'mask':np.array([0,0],dtype=np.uint8), 'status':'OK'},
                      {'mask':before['mask'], 'status':'BAD'}, {}):
            with self.assertRaises(AssertionError):
                assert_same(before, after)

    def test_warmup_reads_only_preceding_half_open_windows(self):
        reads, updates = [], []
        class Reader:
            def window(self, start, end):
                reads.append((start,end))
                return (start,end)
        class Detector:
            def update(self, events, start, end):
                updates.append((events,start,end))
        warm(Reader(), Detector(), 100, 20, {'warmup_us':60})
        self.assertEqual(reads, [(40,60),(60,80),(80,100)])
        self.assertEqual(updates, [(r,*r) for r in reads])

    def test_native_renderer_fixed_scale_and_no_polarity_gate(self):
        events = {'x':np.array([2]*20+[3]), 'y':np.array([1]*21)}
        image = np.asarray(native_event_image(events))
        self.assertEqual(image.shape, (480,640,3))
        self.assertTrue((image[1,2] == 255).all())
        self.assertTrue((image[0,0] == 0).all())
        self.assertTrue((image[1,3] == round(np.log(2)/np.log(21)*255)).all())


if __name__ == '__main__':
    unittest.main()
