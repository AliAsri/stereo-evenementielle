import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import download_evimo_sample as download


class Response(io.BytesIO):
    status = 206

    def __init__(self, data, *, content_range=None):
        super().__init__(data)
        self.headers = {'Content-Range': content_range or f'bytes 0-{len(data)-1}/{len(data)}'}


def archive_bytes(members):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name, payload in members:
            member = tarfile.TarInfo(name)
            if payload is None:
                member.type = tarfile.SYMTYPE
                member.linkname = '../outside'
                archive.addfile(member)
            else:
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
    return stream.getvalue()


class ValidationAcquisitionTests(unittest.TestCase):
    def invoke(self, data, *, local_limit=65536, extraction_limit=4096, response=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        out = root/'report'; out.mkdir()
        budget = dict(limit=local_limit*2, read=0)
        extraction = dict(limit=extraction_limit, written=0)
        result = download.acquire_validation_sequence(root, out, *download.VALIDATION_TARGETS[0],
            budget, extraction, local_limit,
            opener=lambda *a, **k: Response(data) if response is None else response)
        return root, result, budget, extraction

    def test_common_counter_survives_separate_streams_and_stops_exactly(self):
        budget = dict(limit=7, read=0)
        a = download.SharedBudgetReader(io.BytesIO(b'abcdefghij'), budget, 4)
        self.assertEqual(a.read(10), b'abcd')
        self.assertEqual(a.read(0), b'')
        with self.assertRaises(download.TransferLimit): a.read(1)
        b = download.SharedBudgetReader(io.BytesIO(b'0123456789'), budget, 8)
        self.assertEqual(b.read(), b'012')
        with self.assertRaises(download.TransferLimit): b.read(1)
        self.assertEqual(budget['read'], 7)
        self.assertEqual(b.digest.hexdigest(), hashlib.sha256(b'012').hexdigest())

    def test_only_fixed_target_files_are_saved_and_rehashed(self):
        prefix = 'left_camera/imo/eval/scene14_dyn_test_03_000000/'
        payloads = {name: name.encode() for name in download.FILES}
        data = archive_bytes([('left_camera/imo/train/other/dataset_info.npz', b'unrelated'),
                              (prefix+'dataset_classical.npz', b'excluded RGB'),
                              *[(prefix+name, value) for name,value in sorted(payloads.items())]])
        root, result, budget, extraction = self.invoke(data)
        self.assertEqual(result['status'], 'ACQUIRED_UNAUDITED')
        self.assertEqual(len(result['files']), 6)
        self.assertEqual(extraction['written'], sum(map(len,payloads.values())))
        self.assertEqual(result['transferred_bytes'], budget['read'])
        for record in result['files']:
            self.assertEqual((root/record['path']).read_bytes(), payloads[record['name']])
            self.assertEqual(record['sha256'], hashlib.sha256(payloads[record['name']]).hexdigest())
        self.assertEqual(len(list((root/'data').rglob('*.*'))), 6)

    def test_cap_inside_unrelated_prefix_saves_no_unapproved_data(self):
        data = archive_bytes([('left_camera/imo/train/other/large', bytes(range(256))*20)])
        response = Response(data, content_range='bytes 0-63/9999')
        root, result, budget, _ = self.invoke(data, local_limit=64, response=response)
        self.assertEqual(result['status'], 'TRANSFER_CAP_REACHED')
        self.assertEqual(budget['read'], 64)
        self.assertEqual(result['files'], [])
        self.assertFalse((root/'data').exists())

    def test_unbounded_http_range_rejected_before_body_read(self):
        response = Response(b'body', content_range='bytes 0-999/1000')
        root, result, budget, _ = self.invoke(b'', local_limit=64, response=response)
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertEqual(budget['read'], 0)
        self.assertFalse((root/'data').exists())

    def test_symlink_and_extraction_overflow_never_materialized(self):
        name = 'left_camera/imo/eval/scene14_dyn_test_03_000000/dataset_info.npz'
        for payload, limit in [(None, 100), (b'123456', 5)]:
            with self.subTest(payload=payload):
                root, result, _, extraction = self.invoke(archive_bytes([(name,payload)]),
                                                         extraction_limit=limit)
                self.assertEqual(result['status'], 'INCOMPLETE')
                self.assertEqual(extraction['written'], 0)
                self.assertFalse((root/'data').exists())

    def test_plan_is_written_before_http_and_existing_output_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); out=root/'report'
            calls=[]
            def acquire(root_arg, out_arg, category, name, budget, extraction, limit):
                plan=json.loads((out_arg/'acquisition_plan.json').read_text())
                self.assertEqual(plan['network_limit_bytes'], 512*1024**2)
                self.assertEqual(limit, 256*1024**2)
                self.assertFalse(plan['inference'])
                calls.append((category,name))
                return dict(sequence=f'left_camera/{category}/eval/{name}', status='INCOMPLETE', files=[])
            with patch.object(download,'acquire_validation_sequence',side_effect=acquire):
                result=download.acquire_validation_references(root,out)
            self.assertEqual(calls,list(download.VALIDATION_TARGETS))
            self.assertEqual(result['status'],'INCOMPLETE')
            with self.assertRaises(FileExistsError): download.acquire_validation_references(root,out)

    def test_unapproved_sequence_and_conflicting_cli_fail_before_network(self):
        with self.assertRaises(ValueError):
            download.acquire_validation_sequence(Path('.'),Path('.'),'imo','other',{}, {},1)
        with patch.object(sys,'argv',['download','--validation-reference','--next-train-sequence']), \
             patch.object(download.urllib.request,'urlopen',side_effect=AssertionError('no network')):
            with self.assertRaises(SystemExit): download.main()


if __name__ == '__main__':
    unittest.main()
