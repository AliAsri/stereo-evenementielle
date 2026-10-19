"""A frozen demo bundle restores exactly and never replaces conflicting inputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('demo_assets', ROOT/'scripts/manage_demo_assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class DemoAssetsTests(unittest.TestCase):
    def setUp(self):
        base = ROOT/'outputs/test-temp'
        base.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root/'source'
        self.target = self.root/'target'
        self.archive = self.root/'assets.zip'
        self.entries = []
        for name, data in [('outputs/model.pt', b'opaque weights'), ('data/control.png', b'image')]:
            path = self.source/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self.entries.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))

    def test_round_trip_and_repeat_restore(self):
        assets.pack(self.source, self.archive, self.entries)
        for _ in range(2):
            assets.restore(self.target, self.archive, self.entries)
        for entry in self.entries:
            self.assertEqual((self.source/entry['path']).read_bytes(), (self.target/entry['path']).read_bytes())
        with self.assertRaises(FileExistsError):
            assets.pack(self.source, self.archive, self.entries)

    def test_conflict_checked_before_any_installation(self):
        assets.pack(self.source, self.archive, self.entries)
        conflict = self.target/self.entries[-1]['path']
        conflict.parent.mkdir(parents=True)
        conflict.write_bytes(b'keep this')
        with self.assertRaises(FileExistsError):
            assets.restore(self.target, self.archive, self.entries)
        self.assertFalse((self.target/self.entries[0]['path']).exists())
        self.assertEqual(conflict.read_bytes(), b'keep this')

    def test_same_size_tampering_rejected_before_installation(self):
        with zipfile.ZipFile(self.archive, 'w') as zipped:
            for entry in self.entries:
                zipped.writestr(entry['path'], b'x'*entry['bytes'])
        with self.assertRaisesRegex(ValueError, 'checksum'):
            assets.restore(self.target, self.archive, self.entries)
        self.assertFalse(self.target.exists())

    def test_extra_member_rejected(self):
        assets.pack(self.source, self.archive, self.entries)
        with zipfile.ZipFile(self.archive, 'a') as zipped:
            zipped.writestr('../outside.txt', b'bad')
        with self.assertRaises(ValueError):
            assets.restore(self.target, self.archive, self.entries)
        self.assertFalse(self.target.exists())

    def test_changed_source_not_packaged(self):
        (self.source/self.entries[-1]['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            assets.pack(self.source, self.archive, self.entries)
        self.assertFalse(self.archive.exists())

    def test_frozen_spec_matches_the_demo_required_paths(self):
        demo_spec = importlib.util.spec_from_file_location('demo', ROOT/'scripts/run_integrated_demo.py')
        demo = importlib.util.module_from_spec(demo_spec)
        demo_spec.loader.exec_module(demo)
        config = json.loads((ROOT/'configs/demo_assets.json').read_text())
        self.assertEqual({e['path'] for e in config['files']},
                         {p.relative_to(ROOT).as_posix() for p in demo.required_inputs()})
        self.assertEqual(sum(e['bundled'] for e in config['files']), 3)


if __name__ == '__main__':
    unittest.main()
