"""The checker must preserve failure evidence even when a child cannot finish."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('project_checker', ROOT / 'scripts/check_project.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class CheckerFailureTests(unittest.TestCase):
    def run_case(self, effects, source=None):
        temp_root = ROOT / 'outputs/test-temp'
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            root = Path(directory)
            for folder in ('src', 'scripts', 'tests'):
                (root / folder).mkdir()
            if source is not None:
                (root / 'scripts/entry.py').write_bytes(source)
            output = root / 'report'
            with patch.object(checker, 'ROOT', root), patch.object(
                    sys, 'argv', ['check_project.py', '--output', str(output)]), patch.object(
                    checker.subprocess, 'run', side_effect=effects), patch('builtins.print'):
                with self.assertRaises(SystemExit) as error:
                    checker.main()
            self.assertEqual(error.exception.code, 1)
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(report['status'], 'FAILED')
            return report, (output / 'tests.log').read_text(encoding='utf-8')

    def test_timeout_preserves_partial_bytes_and_failure_report(self):
        report, log = self.run_case([subprocess.TimeoutExpired('tests', 180,
                                   output=b'completed case\n', stderr=b'last case')])
        self.assertIsNone(report['test_returncode'])
        self.assertIn('timed out', report['errors'][0])
        self.assertEqual(log, 'completed case\nlast case')

    def test_cannot_start_tests_preserves_error(self):
        report, log = self.run_case([OSError('cannot launch interpreter')])
        self.assertIn('could not start', report['errors'][0])
        self.assertIn('cannot launch', log)

    def test_cli_launch_failure_does_not_skip_tests(self):
        report, log = self.run_case([OSError('bad launch'),
            subprocess.CompletedProcess('tests', 0, stdout='tests completed', stderr='')],
            source=b'import argparse\n')
        self.assertEqual(report['test_returncode'], 0)
        self.assertIn('--help could not start', report['errors'][0])
        self.assertEqual(log, 'tests completed')

    def test_non_utf8_source_is_reported(self):
        report, _ = self.run_case([
            subprocess.CompletedProcess('tests', 0, stdout='', stderr='')], source=b'\xff')
        self.assertIn('entry.py', report['errors'][0])


if __name__ == '__main__':
    unittest.main()
