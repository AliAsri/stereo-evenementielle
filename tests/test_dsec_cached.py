"""Cached handles must preserve indexed-reader data and validation contracts."""
import sys
from pathlib import Path
import unittest
import h5py
import numpy as np
import test_dsec_indexed as fixtures
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.dsec_cached import CachedIndexedDSECReader
from pfe_events.dsec_indexed import IndexedDSECReader


class CachedReaderTests(unittest.TestCase):
    def setUp(self): fixtures.IndexedReaderTests.setUp(self)
    def tearDown(self): self.temp.cleanup()

    def test_exact_arrays_for_sequential_backward_empty_and_edge_windows(self):
        with IndexedDSECReader(self.path) as before, CachedIndexedDSECReader(self.path) as after:
            for a,b in [(10000,11000),(11000,12000),(12000,13000),(14500,14501),
                        (9999,10001),(14000,17000),(10000,11000)]:
                old,new=before.window(a,b),after.window(a,b)
                for key in old:
                    self.assertEqual(old[key].dtype,new[key].dtype)
                    np.testing.assert_array_equal(old[key],new[key])

    def test_handles_reused_and_closed_and_reader_can_reopen(self):
        reader=CachedIndexedDSECReader(self.path)
        with reader:
            handles=dict(reader.events);reader.window(10000,11000);reader.window(11000,12000)
            self.assertTrue(all(reader.events[k] is d for k,d in handles.items()))
            self.assertTrue(all(v>0 for v in reader.cache_bytes.values()))
        self.assertIsNone(reader.file);self.assertIsNone(reader.events)
        self.assertTrue(all(not d.id.valid for d in handles.values()))
        with reader: self.assertEqual(len(reader.window(10000,11000)['x']),4)

    def test_budget_fallback_and_no_future_events(self):
        with CachedIndexedDSECReader(self.path) as reader:
            self.assertEqual(reader.window(10098,10100,max_events=1)['t_us'].tolist(),[10099])
            self.assertGreater(reader.fallback_windows,0)
            with self.assertRaises(MemoryError): reader.window(10000,11000,max_events=1)
            self.assertTrue((reader.window(10000,11000)['t_us']<11000).all())

    def test_corrupt_index_and_payload_are_rejected(self):
        for field,index,value in [('ms_to_idx',1,5),('events/x',4,640),('events/p',4,2),('events/t',4,1002)]:
            with h5py.File(self.path,'r+') as file:
                old=file[field][index];file[field][index]=value
            with CachedIndexedDSECReader(self.path) as reader:
                begin=11000 if field=='ms_to_idx' else 10000
                with self.assertRaises(ValueError): reader.window(begin,12000)
            with h5py.File(self.path,'r+') as file: file[field][index]=old


if __name__=='__main__': unittest.main()
