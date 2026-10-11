"""Deterministic clock controls for recorded-time availability and overload."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pfe_events.replay_timing import paced_windows


class FakeClock:
    def __init__(self, oversleep_ns=0): self.now=0; self.oversleep_ns=oversleep_ns
    def clock(self): return self.now
    def sleep(self, seconds): self.now += round(seconds*1e9)+self.oversleep_ns


class Reader:
    def __init__(self, clock, cost_ns): self.clock=clock; self.cost_ns=cost_ns; self.calls=[]
    def window(self, begin, end):
        self.calls.append((begin,end,self.clock.now)); self.clock.now+=self.cost_ns
        return {}


class Detector:
    def __init__(self, clock, cost_ns): self.clock=clock; self.cost_ns=cost_ns
    def update(self, events, begin, end):
        self.clock.now+=self.cost_ns
        return {'events':0,'regions':[],'active_fraction':0.0}


class ReplayTimingTests(unittest.TestCase):
    def run_case(self, read_ms=2, compute_ms=3, oversleep_ms=0, **extra):
        c=FakeClock(int(oversleep_ms*1e6)); reader=Reader(c,int(read_ms*1e6))
        rows, status=paced_windows(reader,Detector(c,int(compute_ms*1e6)),1000000,50000,10000,
            clock_ns=c.clock,sleep=c.sleep,**extra)
        return rows,status,reader

    def test_no_future_read_and_complete_contiguous_windows(self):
        rows,status,reader=self.run_case()
        self.assertEqual(status['status'],'COMPLETE'); self.assertEqual(len(rows),5)
        for i,(begin,end,wall) in enumerate(reader.calls):
            self.assertEqual((begin,end),(1000000+i*10000,1010000+i*10000))
            self.assertGreaterEqual(wall,(i+1)*10000000)
        self.assertEqual([r['output_age_after_window_end_ms'] for r in rows],[5]*5)

    def test_overload_accumulates_without_skipping(self):
        rows,status,_=self.run_case(read_ms=8,compute_ms=7)
        self.assertEqual([r['start_lateness_ms'] for r in rows],[0,5,10,15,20])
        self.assertEqual([r['output_age_after_window_end_ms'] for r in rows],[15,20,25,30,35])
        self.assertTrue(all(r['completion_past_next_release'] for r in rows))
        self.assertEqual(status['processed_windows'],5)
        self.assertEqual(rows[2]['additional_released_windows_waiting_at_start'],1)
        self.assertEqual(rows[-1]['additional_released_windows_waiting_at_start'],0)

    def test_scheduler_oversleep_is_separate_from_compute(self):
        rows,_,_=self.run_case(oversleep_ms=2)
        self.assertEqual(rows[0]['read_activity_ms'],5)
        self.assertEqual(rows[0]['start_lateness_ms'],2)
        self.assertEqual(rows[0]['output_age_after_window_end_ms'],7)

    def test_deadline_equality_is_not_exceedance(self):
        rows,_,_=self.run_case(read_ms=4,compute_ms=6)
        self.assertFalse(any(r['completion_past_next_release'] for r in rows))

    def test_budget_exhaustion_is_explicit(self):
        rows,status,_=self.run_case(read_ms=100,compute_ms=100,max_wall_seconds=.1)
        self.assertEqual(len(rows),1); self.assertEqual(status['status'],'WALL_BUDGET_EXCEEDED')
        self.assertEqual(status['planned_windows'],5)

    def test_invalid_cadence_rejected(self):
        with self.assertRaises(ValueError): paced_windows(None,None,0,50000,20000)


if __name__=='__main__': unittest.main()
