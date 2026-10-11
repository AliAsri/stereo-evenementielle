"""Exact slicing against an independent in-memory timestamp mask."""

import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import hdf5plugin
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from pfe_events.dsec_indexed import IndexedDSECReader


class IndexedReaderTests(unittest.TestCase):
    def setUp(self):
        temp_root = ROOT/"outputs/test-temp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.path = Path(self.temp.name)/"events.h5"
        self.times = np.array([0, 0, 99, 999, 1000, 1000, 1001, 3999, 4000, 4500], dtype=np.int64)
        with h5py.File(self.path, "w") as out:
            for key, data in {"t": self.times, "x": np.arange(len(self.times)),
                              "y": np.zeros(len(self.times), dtype=int), "p": np.arange(len(self.times)) % 2}.items():
                out.create_dataset("events/"+key, data=data, **hdf5plugin.Blosc(cname="zstd"))
            out["t_offset"] = 10_000
            out["ms_to_idx"] = np.searchsorted(self.times, np.arange(6)*1000)

    def tearDown(self):
        self.temp.cleanup()

    def test_boundaries_duplicates_gaps_and_file_edges(self):
        points = [-1, 0, 1, 99, 999, 1000, 1001, 2000, 3000, 3999, 4000, 4500, 4501, 6000]
        with IndexedDSECReader(self.path) as reader:
            for start in points:
                for end in points:
                    if end <= start:
                        continue
                    result = reader.window(start+10_000, end+10_000)
                    expected = (self.times >= start) & (self.times < end)
                    np.testing.assert_array_equal(result["t_us"], self.times[expected]+10_000)
                    np.testing.assert_array_equal(result["x"], np.flatnonzero(expected))

    def test_budget_checks_exact_slice_not_conservative_envelope(self):
        with IndexedDSECReader(self.path) as reader:
            self.assertEqual(len(reader.window(10_098, 10_100, max_events=1)["x"]), 1)
            self.assertGreater(reader.fallback_windows, 0)
            with self.assertRaises(MemoryError):
                reader.window(10_000, 11_000, max_events=1)

    def test_corrupt_boundary_cannot_silently_drop_duplicate(self):
        with h5py.File(self.path, "r+") as out:
            out["ms_to_idx"][1] = 5  # valid range/order, wrong lower bound at repeated t=1000
        with IndexedDSECReader(self.path) as reader:
            with self.assertRaises(ValueError):
                reader.window(11_000, 12_000)

    def test_invalid_index_schema_and_range(self):
        for values in [[0, 100], [0, -1], [0, 2, 1], [0.0, 2.0], [[0, 1]], []]:
            with h5py.File(self.path, "r+") as out:
                del out["ms_to_idx"]
                out["ms_to_idx"] = values
            with self.assertRaises(ValueError):
                with IndexedDSECReader(self.path):
                    self.fail("Bad index accepted")

    def test_input_validation_and_missing_tail_sentinel(self):
        with h5py.File(self.path, "r+") as out:
            del out["ms_to_idx"]
            out["ms_to_idx"] = np.searchsorted(self.times, np.arange(4)*1000)
        with IndexedDSECReader(self.path) as reader:
            self.assertEqual(len(reader.window(14_500, 14_501)["x"]), 1)
            self.assertEqual(reader.fallback_windows, 1)
            with self.assertRaises(TypeError):
                reader.window(1.5, 2)
            with self.assertRaises(ValueError):
                reader.window(2, 2)

    def test_coordinates_polarities_and_unsorted_envelope_still_checked(self):
        for field, value in [("x", 640), ("p", 2), ("t", 1002)]:
            with h5py.File(self.path, "r+") as out:
                old = out['events/'+field][4]
                out['events/'+field][4] = value
            with IndexedDSECReader(self.path) as reader:
                with self.assertRaises(ValueError):
                    reader.window(10_000, 12_000)
            with h5py.File(self.path, "r+") as out:
                out['events/'+field][4] = old


if __name__ == "__main__":
    unittest.main()
