"""Exact activity equivalence on analytical and seeded synthetic event streams."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.motion import ActivityConfig, ActivityDetector
from pfe_events.motion_lookup import LookupActivityDetector


def same(test, before, after):
    test.assertEqual(before.keys(),after.keys())
    for key,value in before.items():
        if isinstance(value,np.ndarray):
            test.assertEqual(value.dtype,after[key].dtype)
            np.testing.assert_array_equal(value,after[key])
        else: test.assertEqual(value,after[key])


class LookupActivityTests(unittest.TestCase):
    def test_seeded_stream_all_fields_and_state_at_multiple_geometries(self):
        rng=np.random.default_rng(20261004)
        for width,height,cell in [(640,480,16),(35,19,16),(8,7,3)]:
            for dtype in [np.uint16,np.int32,np.int64]:
                config=ActivityConfig(width=width,height=height,cell_px=cell)
                a,b=ActivityDetector(config),LookupActivityDetector(config)
                for i,count in enumerate([0,1,100,2000,10000,0,20000]):
                    events={'x':rng.integers(0,width,count).astype(dtype),
                            'y':rng.integers(0,height,count).astype(dtype),
                            't_us':np.sort(rng.integers(i*10000,(i+1)*10000,count))}
                    same(self,a.update(events,i*10000,(i+1)*10000),b.update(events,i*10000,(i+1)*10000))
                    np.testing.assert_array_equal(a.elapsed,b.elapsed)
                    self.assertEqual(a.previous_end,b.previous_end)

    def test_lookup_partial_border_and_storage(self):
        b=LookupActivityDetector(ActivityConfig(width=18,height=18))
        self.assertEqual(b.pixel_to_cell[17*18+17],3)
        self.assertEqual(b.pixel_to_cell[0],0)
        self.assertFalse(b.pixel_to_cell.flags.writeable)
        self.assertEqual(LookupActivityDetector().pixel_to_cell.nbytes,640*480*np.dtype(np.intp).itemsize)

    def test_future_corrupt_and_noncontiguous_rejected_without_state_change(self):
        for events in [dict(x=np.array([1]),y=np.array([1]),t_us=np.array([10000])),
                       dict(x=np.array([640]),y=np.array([1]),t_us=np.array([1])),
                       dict(x=np.array([1,2]),y=np.array([1,1]),t_us=np.array([3,2])),
                       dict(x=np.array([1.5]),y=np.array([1]),t_us=np.array([1]))]:
            for cls in [ActivityDetector,LookupActivityDetector]:
                detector=cls()
                with self.assertRaises(ValueError): detector.update(events,0,10000)
                self.assertIsNone(detector.previous_end);self.assertFalse(detector.elapsed.any())
        e={k:np.array([],dtype=np.int64) for k in ('x','y','t_us')}
        b=LookupActivityDetector();b.update(e,0,10000)
        with self.assertRaises(ValueError): b.update(e,20000,30000)
        self.assertEqual(b.previous_end,10000)

    def test_readonly_inputs_not_modified_or_output_aliased(self):
        events={'x':np.array([1,2,17,18]*100),'y':np.ones(400,dtype=np.int64),
                't_us':np.full(400,1000,dtype=np.int64)}
        copies={k:v.copy() for k,v in events.items()}
        for a in events.values(): a.flags.writeable=False
        detector=LookupActivityDetector();out=detector.update(events,0,10000)
        previous={k:v.copy() for k,v in out.items() if isinstance(v,np.ndarray)}
        events2=dict(events,t_us=np.full(400,11000,dtype=np.int64))
        detector.update(events2,10000,20000)
        for k,v in copies.items(): np.testing.assert_array_equal(events[k],v)
        for k,v in previous.items(): np.testing.assert_array_equal(out[k],v)

    def test_persistence_hot_pixel_and_reset_equivalence(self):
        a,b=ActivityDetector(),LookupActivityDetector()
        patterns=[([1]*10000,[1]*10000),([1,2,3,4,17,18,19,20]*20,[1]*160),
                  ([1,2,3,4,17,18,19,20]*20,[1]*160),([],[])]
        for i,(x,y) in enumerate(patterns):
            e={'x':np.array(x,dtype=np.int64),'y':np.array(y,dtype=np.int64),
               't_us':np.full(len(x),i*10000+1,dtype=np.int64)}
            same(self,a.update(e,i*10000,(i+1)*10000),b.update(e,i*10000,(i+1)*10000))


if __name__=='__main__': unittest.main()
