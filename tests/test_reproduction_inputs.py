"""Failures during preparation must be recoverable before expensive inference."""
import importlib.util
import ast
import hashlib
import inspect
import json
from pathlib import Path
import sys
import tempfile
import textwrap
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load_script(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


download = load_script('sample_download', 'scripts/download_sample.py')
demo = load_script('integrated_demo', 'scripts/run_integrated_demo.py')
colab_import = load_script('colab_import', 'scripts/import_y01_results.py')


class ReproductionTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'outputs/test-temp'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, payload=b'valid data'):
        path = self.root / 'sample.zip'
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as archive:
            archive.writestr('nested/events.h5', payload)
        return path

    def frozen_manifest(self, paths):
        target = self.root/'configs/demo_assets.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        entries = [dict(path=p.relative_to(self.root).as_posix(), bytes=p.stat().st_size,
                        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]
        target.write_text(json.dumps(dict(schema=1, files=entries)))
        return target

    def frozen_inputs(self):
        paths = demo.required_inputs()
        for index, path in enumerate(paths):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f'input {index}'.encode())
        self.frozen_manifest(paths)
        return paths

    def test_changed_inputs_fail_before_runtime_or_output_creation(self):
        with patch.object(demo, 'ROOT', self.root):
            paths = self.frozen_inputs()
            for path in paths:
                original = path.read_bytes()
                for changed in (b'x'*len(original), original+b'!'):
                    with self.subTest(input=path.name, size=len(changed)):
                        path.write_bytes(changed)
                        with patch.object(sys, 'argv', ['demo', '--output', str(self.root/'result')]):
                            with self.assertRaisesRegex(ValueError, 'Changed demo inputs'):
                                demo.main()
                        self.assertFalse((self.root/'result').exists())
                        self.assertFalse((self.root/'outputs/runtime').exists())
                path.write_bytes(original)
            verified = demo.verify_inputs(paths)
            self.assertEqual(verified['mode'], 'FROZEN_Y01')
            self.assertEqual(verified['verified_frozen_inputs'], 8)

    def test_explicit_checkpoint_does_not_disable_scene_integrity_checks(self):
        with patch.object(demo, 'ROOT', self.root):
            defaults = self.frozen_inputs()
            defaults[0].unlink()  # No implicit requirement or fallback to Y01.
            selected = self.root/'candidate.pt'
            selected.write_bytes(b'explicit candidate')
            paths = demo.check_inputs(selected)
            report = demo.verify_inputs(paths)
            self.assertEqual(report['mode'], 'EXPLICIT_CHECKPOINT')
            self.assertEqual(report['verified_frozen_inputs'], 7)
            self.assertEqual(report['checkpoint_identity'], 'RECORDED_NOT_VERIFIED')
            self.assertEqual(report['sha256']['candidate.pt'], hashlib.sha256(selected.read_bytes()).hexdigest())
            paths[1].write_bytes(b'changed normalizer')
            with self.assertRaisesRegex(ValueError, 'Changed demo inputs'):
                demo.verify_inputs(paths)

    def test_incomplete_or_duplicate_manifest_is_rejected(self):
        with patch.object(demo, 'ROOT', self.root):
            paths = self.frozen_inputs()
            manifest = self.root/'configs/demo_assets.json'
            original = json.loads(manifest.read_text())
            for entries in (original['files'][:-1], original['files']+[original['files'][0]]):
                manifest.write_text(json.dumps(dict(schema=1, files=entries)))
                with self.assertRaisesRegex(ValueError, 'exactly the eight'):
                    demo.verify_inputs(paths)

    def test_context_schedule_keeps_all_motion_dates_and_explicit_age(self):
        first = 36613680936
        dates = list(range(first, first+320001, 20000))
        last = None
        rows = []
        for date in dates:
            if demo.context_due(date, first, 100000):
                last = date
            rows.append(demo.context_metadata(date, last))
        self.assertEqual(len(rows), 17)
        self.assertEqual([i for i, row in enumerate(rows) if row['updated']], [0, 5, 10, 15])
        self.assertEqual([row['age_us'] for row in rows[:6]], [0, 20000, 40000, 60000, 80000, 0])
        self.assertTrue(all(row['timestamp_us'] <= date for row, date in zip(rows, dates)))
        self.assertTrue(all(demo.context_due(date, first, 20000) for date in dates))

    def test_context_rejects_invalid_schedule_and_future_or_missing_results(self):
        for period in (0, -20000, 10000, 30000, 20000.0):
            with self.assertRaises(ValueError):
                demo.context_due(100000, 100000, period)
        for date in (99999, 100001, 100000.0):
            with self.assertRaises(ValueError):
                demo.context_due(date, 100000, 100000)
        for source in (None, 120000, 100000.0):
            with self.assertRaises(ValueError):
                demo.context_metadata(100000, source)

    def test_colab_import_on_fresh_checkout_with_external_dataset(self):
        # Synthetic evidence only: exercises first import/report publication,
        # without deserializing weights or claiming successful real training.
        checkout = self.root/'checkout'; checkout.mkdir()
        dataset = self.root/'dataset'; dataset.mkdir()
        payload = b'synthetic'; digest = hashlib.sha256(payload).hexdigest()
        for name in ('manifest.json', 'normalizer.json'):
            (dataset/name).write_bytes(payload)
        dataset.with_suffix('.zip').write_bytes(payload)
        run = 'Y02_20261015T000000Z'
        metadata = {
            'dataset-provenance.json': {'manifest_sha256':digest, 'normalizer_sha256':digest, 'archive_sha256':digest},
            'checkpoint-provenance.json': {'sha256':digest},
            'pilot-metrics.json': {'best_sha256':digest, 'last_sha256':digest},
            **{name:{} for name in ('environment.json', 'status.json', 'overfit-metrics.json', 'tensor-check.json', 'dataset-verification.json')}}
        archive = self.root/'colab.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            for name, value in metadata.items(): zipped.writestr(f'{run}/{name}', json.dumps(value))
            for name in ('manifest.json', 'normalizer.json', 'initial_weights/yolo11n.pt', 'pilot/weights/best.pt', 'pilot/weights/last.pt'):
                zipped.writestr(f'{run}/{name}', payload)
        with patch.object(colab_import, 'ROOT', checkout), patch.object(sys, 'argv',
                ['import_y01_results.py', str(archive), '--run', run, '--dataset', str(dataset)]):
            colab_import.main()
        report = json.loads((checkout/'outputs/reports/Y02_colab_audit.json').read_text())
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(len(report['checks']), 8)
        self.assertTrue(all(c['passed'] for c in report['checks']))

    def test_bad_crc_leaves_no_final_file_and_repaired_archive_can_retry(self):
        payload = b'x' * (2 * 1024**2) + b'end marker'
        archive = self.archive(payload)
        archive.write_bytes(archive.read_bytes().replace(b'end marker', b'bad marker', 1))
        destination = self.root / 'unpacked'
        with self.assertRaises(zipfile.BadZipFile):
            download.extract_checked(archive, destination)
        self.assertEqual([p for p in destination.rglob('*') if p.is_file()], [])
        self.archive(payload)
        download.extract_checked(archive, destination)
        self.assertEqual((destination / 'nested/events.h5').read_bytes(), payload)

    def test_identical_extraction_can_repeat_but_different_data_is_preserved(self):
        archive = self.archive()
        destination = self.root / 'unpacked'
        download.extract_checked(archive, destination)
        download.extract_checked(archive, destination)
        target = destination / 'nested/events.h5'
        target.write_bytes(b'existing different data')
        with self.assertRaises(FileExistsError):
            download.extract_checked(archive, destination)
        self.assertEqual(target.read_bytes(), b'existing different data')

    def test_archive_traversal_is_rejected(self):
        archive = self.root / 'unsafe.zip'
        with zipfile.ZipFile(archive, 'w') as stream:
            stream.writestr('../outside.txt', b'bad')
        with self.assertRaises(ValueError):
            download.extract_checked(archive, self.root / 'unpacked')
        self.assertFalse((self.root / 'outside.txt').exists())

    def test_missing_inputs_are_listed_together_without_output_side_effects(self):
        with patch.object(demo, 'ROOT', self.root), patch.object(sys, 'argv',
                ['run_integrated_demo.py', '--output', str(self.root / 'result')]):
            with self.assertRaises(FileNotFoundError) as error:
                demo.main()
            for path in demo.required_inputs():
                self.assertIn(str(path.relative_to(self.root)), str(error.exception))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_anchor_export_is_required_and_preflight_needs_no_inference_runtime(self):
        with patch.object(demo, 'ROOT', self.root):
            paths = demo.required_inputs()
            for path in paths[:-1]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            with self.assertRaisesRegex(FileNotFoundError, '36614000936.png'):
                demo.check_inputs()
            paths[-1].parent.mkdir(parents=True)
            paths[-1].touch()
            self.frozen_manifest(paths)
            with patch.object(sys, 'argv', ['demo', '--check-inputs']), patch('builtins.print'):
                demo.main()
            self.assertFalse((self.root / 'outputs/runtime').exists())

    def test_selected_checkpoint_is_required_without_fallback_to_old_model(self):
        selected = self.root/'candidate.pt'
        with patch.object(demo, 'ROOT', self.root):
            original = demo.required_inputs()
            for path in original:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            with self.assertRaisesRegex(FileNotFoundError, 'candidate.pt'):
                demo.check_inputs(selected)
            selected.touch()
            paths = demo.check_inputs(selected)
            self.assertEqual(paths[0], selected.resolve())
            self.assertEqual(paths[1:], original[1:])
            self.assertNotIn(original[0], paths)

    def test_historical_diagnostics_import_without_reading_or_writing_results(self):
        # Importing either formerly executed the complete experiment immediately.
        with patch.object(Path, 'read_text', side_effect=AssertionError('unexpected input read')), \
                patch.object(Path, 'mkdir', side_effect=AssertionError('unexpected output creation')):
            for name in ('check_camera_influence', 'explain_points'):
                module = load_script(name, f'scripts/diagnostics/{name}.py')
                self.assertTrue(callable(module.main))

    def retry_reporting(self):
        source = (ROOT/'notebooks/Y01_retry_overfit_cell.py').read_text(encoding='utf-8')
        node = next(n for n in ast.parse(source).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'prepare_retry_reporting')
        namespace = {'inspect': inspect}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'retry preflight', 'exec'), namespace)
        return namespace['prepare_retry_reporting']

    def test_retry_reporting_handles_both_apis_and_missing_class(self):
        prepare = self.retry_reporting()
        label = self.root/'labels/train/a.txt'
        label.parent.mkdir(parents=True)
        label.write_text('0 .5 .5 .1 .1\n1 .5 .5 .2 .2\n1 .5 .5 .1 .1\n')
        subset = ['./images/train/a.png']
        def legacy(metrics, purpose):
            return metrics, purpose
        def current(metrics, purpose, support):
            return support
        self.assertEqual(prepare(legacy, self.root, subset), {})
        kwargs = prepare(current, self.root, subset)
        self.assertEqual(current(None, 'synthetic', **kwargs), [1, 2])
        label.write_text('0 .5 .5 .1 .1\n')
        with self.assertRaisesRegex(ValueError, 'both person and car'):
            prepare(current, self.root, subset)
        label.write_text('2 .5 .5 .1 .1\n')
        with self.assertRaisesRegex(ValueError, 'Y01 person/car only'):
            prepare(current, self.root, subset)

    def test_retry_reporting_rejects_unsupported_api_before_training(self):
        label = self.root/'labels/train/a.txt'
        label.parent.mkdir(parents=True)
        label.write_text('0 .5 .5 .1 .1\n1 .5 .5 .1 .1\n')
        def incompatible(metrics, purpose, additional_required_argument):
            pass
        with self.assertRaises(TypeError):
            self.retry_reporting()(incompatible, self.root, ['./images/train/a.png'])

    def test_retry_calls_real_legacy_and_generated_reporting_functions(self):
        label = self.root/'labels/train/a.txt'
        label.parent.mkdir(parents=True)
        label.write_text('0 .5 .5 .1 .1\n1 .5 .5 .1 .1\n')
        notebook = json.loads((ROOT/'notebooks/Y01_yolo11n_events_pilot.ipynb').read_text(encoding='utf-8'))
        legacy = next(''.join(c['source']) for c in notebook['cells']
                      if c['cell_type'] == 'code' and 'def metrics_dict(' in ''.join(c['source']))
        generator = ast.parse((ROOT/'scripts/build_yolo_notebook.py').read_text(encoding='utf-8'))
        generated = next(textwrap.dedent(n.value) for n in ast.walk(generator)
                         if isinstance(n, ast.Constant) and isinstance(n.value, str)
                         and 'def metrics_dict(' in n.value)
        metrics = SimpleNamespace(box=SimpleNamespace(ap_class_index=[0, 1], ap50=[.9, .95],
            ap=[.8, .85], map50=.925, map=.825), results_dict={})
        for source in (legacy, generated):
            node = next(n for n in ast.parse(source).body
                        if isinstance(n, ast.FunctionDef) and n.name == 'metrics_dict')
            names = {0: 'person', 1: 'car'}
            namespace = {'CLASS_NAMES': names, 'data': {'names': names}}
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'actual notebook report', 'exec'), namespace)
            report_fn = namespace['metrics_dict']
            kwargs = self.retry_reporting()(report_fn, self.root, ['./images/train/a.png'])
            report = report_fn(metrics, 'synthetic overfit', **kwargs)
            self.assertEqual([r['ap50'] for r in report['per_class']], [.9, .95])


if __name__ == '__main__':
    unittest.main()
