"""Shared paired-benchmark checks and causal warmup; no experiment runs on import."""
import csv
import numpy as np
from .pilot import unique_file

def save_rows(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def assert_same(before,after):
    if set(before)!=set(after): raise AssertionError('Different output keys')
    for key,value in before.items():
        other=after[key]
        if isinstance(value,np.ndarray):
            if value.dtype!=other.dtype or not np.array_equal(value,other):
                raise AssertionError('Array mismatch: '+key)
        elif value!=other: raise AssertionError('Output mismatch: '+key)


def warm(reader,detector,start,step,config):
    for begin in range(start-config['warmup_us'],start,step):
        detector.update(reader.window(begin,begin+step),begin,begin+step)


def event_source_path(root, case): return unique_file(root/'data/raw'/case['sequence']/'events_left','events.h5')
