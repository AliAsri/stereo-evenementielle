import io
import sys
import tarfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from pfe_events.evimo_reference import read_metadata, timestamp_summary
from download_evimo_sample import BoundedReader, selected_name, SEQUENCE


class EvimoReferenceTests(unittest.TestCase):
    def file(self, value):
        stream = io.BytesIO()
        np.savez(stream, meta=value)
        stream.seek(0)
        return stream

    def test_reads_plain_metadata_in_numpy_envelope(self):
        value = {'frames':[{'id':2,'ts':0.1}], 'meta': {'res_x':640}}
        self.assertEqual(read_metadata(self.file(value)), value)

    def test_rejects_callable_payload_without_execution(self):
        class Payload:
            def __reduce__(self):
                return (eval, ('1+1',))
        with self.assertRaisesRegex(ValueError, 'Unsupported metadata global'):
            read_metadata(self.file({'payload':Payload()}))

    def test_rejects_non_scalar_envelope(self):
        with self.assertRaisesRegex(ValueError, 'scalar object'):
            read_metadata(self.file(np.array([{},{}],dtype=object)))

    def test_rejects_cyclic_metadata(self):
        value = {}
        value['cycle'] = value
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            read_metadata(self.file(value))

    def test_preserves_irregular_reference_intervals(self):
        result=timestamp_summary([0.01,0.02,0.22])
        self.assertAlmostEqual(result['max_step_ms'],200)
        self.assertEqual(result['count'],3)

    def test_rejects_duplicate_backward_and_nan_times(self):
        for times in ([1,1],[2,1],[0,float('nan')]):
            with self.subTest(times=times), self.assertRaises(ValueError):
                timestamp_summary(times)

    def test_network_reader_cannot_pass_budget(self):
        source=io.BytesIO(b'abcdef')
        reader=BoundedReader(source,3)
        self.assertEqual(reader.read(20),b'abc')
        with self.assertRaises(ValueError):
            reader.read(1)
        self.assertEqual(source.tell(),3)

    def test_only_exact_allowlisted_archive_files(self):
        for name in ('../dataset_info.npz',SEQUENCE+'/../dataset_info.npz',SEQUENCE+'/other.npy'):
            self.assertIsNone(selected_name(tarfile.TarInfo(name)))
        member=tarfile.TarInfo(SEQUENCE+'/dataset_info.npz')
        self.assertEqual(selected_name(member),'dataset_info.npz')
        member.type=tarfile.SYMTYPE
        with self.assertRaises(ValueError):
            selected_name(member)


if __name__ == '__main__':
    unittest.main()
