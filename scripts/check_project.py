"""Offline project checks: syntax, import boundaries, CLI help and unit tests.

Does not download data, train models or rerun experiments. Uses this interpreter
and writes the report only into a new directory supplied with --output.
"""
import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'RUNNING', 'syntax_files': 0, 'cli_help': [], 'errors': []}
    scripts = {p.stem for p in (ROOT / 'scripts').glob('*.py')}
    help_scripts = []
    for folder in ('src', 'scripts', 'tests'):
        for path in sorted((ROOT / folder).rglob('*.py')):
            try:
                source = path.read_text(encoding='utf-8-sig')
                tree = ast.parse(source, filename=str(path))
                compile(tree, str(path), 'exec')
                report['syntax_files'] += 1
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.level == 0:
                        module = (node.module or '').split('.')[0]
                        # The portable Colab verifier deliberately has no package dependency.
                        allowed = folder == 'scripts' and path.name == 'export_yolo_pilot.py' and module == 'verify_yolo_export'
                        if folder != 'tests' and module in scripts and not allowed:
                            report['errors'].append(f'{path.relative_to(ROOT)} imports entry point {module}')
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if folder != 'tests' and alias.name.split('.')[0] in scripts:
                                report['errors'].append(f'{path.relative_to(ROOT)} imports entry point {alias.name}')
                if folder == 'scripts' and path != Path(__file__).resolve() and any(
                    isinstance(node, ast.Import) and any(a.name == 'argparse' for a in node.names)
                    for node in tree.body
                ):
                    help_scripts.append(path)
            except (SyntaxError, ValueError, OSError) as error:
                report['errors'].append(f'{path.relative_to(ROOT)}: {error}')
    for path in help_scripts:
        try:
            run = subprocess.run([sys.executable, str(path), '--help'], cwd=ROOT,
                                 capture_output=True, text=True, timeout=30)
            report['cli_help'].append({'script': path.name, 'returncode': run.returncode})
            if run.returncode:
                report['errors'].append(f'{path.name} --help: {run.stderr}')
        except subprocess.TimeoutExpired:
            report['errors'].append(f'{path.name} --help timed out')
        except OSError as error:
            report['errors'].append(f'{path.name} --help could not start: {error}')
    report['test_returncode'] = None
    try:
        run = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                             cwd=ROOT, capture_output=True, text=True, timeout=180)
        log = run.stdout + run.stderr
        report['test_returncode'] = run.returncode
        if run.returncode:
            report['errors'].append(f'Unit tests failed (exit {run.returncode}); see tests.log')
    except subprocess.TimeoutExpired as error:
        # TimeoutExpired may hold bytes even when subprocess.run uses text=True.
        def decoded(value):
            return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
        log = decoded(error.stdout) + decoded(error.stderr)
        report['errors'].append('Unit tests timed out after 180 seconds; partial output in tests.log')
    except OSError as error:
        log = str(error)
        report['errors'].append(f'Unit tests could not start: {error}')
    (args.output / 'tests.log').write_text(log, encoding='utf-8')
    report['status'] = 'PASSED' if not report['errors'] and report['test_returncode'] == 0 else 'FAILED'
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"{report['status']}: {report['syntax_files']} Python files, {len(help_scripts)} CLI help checks; tests.log saved")
    if report['status'] != 'PASSED':
        print('\n'.join(report['errors']))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
