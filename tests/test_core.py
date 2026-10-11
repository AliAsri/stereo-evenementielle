"""Analytical synthetic fixtures only; they are not experimental model results."""

import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import hdf5plugin
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pfe_events.dsec import DSECReader, rectify_events
from pfe_events.geometry import decode_dsec_disparity, reproject_q
from pfe_events.representations import polarity_counts


class ReaderTests(unittest.TestCase):
    def setUp(self):
        temp_root = ROOT / "outputs/test-temp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.path = Path(self.temp.name) / "synthetic_events.h5"
        with h5py.File(self.path, "w") as output:
            for key, values in {"t": [0, 100, 100, 200, 1000], "x": [0, 1, 1, 2, 3], "y": [0, 1, 1, 2, 2], "p": [0, 1, 1, 0, 1]}.items():
                output.create_dataset(f"events/{key}", data=np.array(values, dtype=np.int64), **hdf5plugin.Blosc(cname="zstd"))
            output["t_offset"] = 1_000_000
            output["ms_to_idx"] = [0, 4]

    def tearDown(self):
        self.temp.cleanup()

    def test_half_open_window_with_offset_and_duplicate_times(self):
        with DSECReader(self.path, 4, 3) as reader:
            window = reader.window(1_000_100, 1_000_200)
            np.testing.assert_array_equal(window["t_us"], [1_000_100, 1_000_100])
            self.assertEqual(reader.audit_timestamps(chunk_size=2)["checked_timestamps"], 5)

    def test_empty_window(self):
        with DSECReader(self.path, 4, 3) as reader:
            self.assertEqual(len(reader.window(0, 10)["x"]), 0)

    def test_all_events_including_last(self):
        with DSECReader(self.path, 4, 3) as reader:
            self.assertEqual(len(reader.window(reader.first_us, reader.last_us+1)["x"]), 5)

    def test_budget_and_time_errors(self):
        with DSECReader(self.path, 4, 3) as reader:
            with self.assertRaises(MemoryError):
                reader.window(reader.first_us, reader.last_us+1, max_events=2)
            with self.assertRaises(ValueError):
                reader.window(10, 10)
            with self.assertRaises(TypeError):
                reader.window(1.5, 10)

    def test_unsorted_file_detected_across_chunks(self):
        with h5py.File(self.path, "r+") as output:
            output["events/t"][2] = 99
        with DSECReader(self.path, 4, 3) as reader:
            with self.assertRaises(ValueError):
                reader.audit_timestamps(chunk_size=2)

    def test_missing_schema_rejected(self):
        with h5py.File(self.path, "r+") as output:
            del output["t_offset"]
        with self.assertRaises(ValueError):
            with DSECReader(self.path):
                self.fail("Malformed file accepted")


class RepresentationTests(unittest.TestCase):
    def test_repeated_pixels_counted_and_polarities_separated(self):
        events = {"x": np.array([1, 1, 1]), "y": np.array([0, 0, 0]), "p": np.array([0, 1, 1])}
        counts = polarity_counts(events, 3, 2)
        self.assertEqual(counts[0, 0, 1], 1)
        self.assertEqual(counts[1, 0, 1], 2)
        self.assertEqual(counts.sum(), 3)

    def test_invalid_coordinates_not_wrapped(self):
        with self.assertRaises(ValueError):
            polarity_counts({"x": np.array([-1]), "y": np.array([0]), "p": np.array([1])}, 3, 2)

    def test_rectification_excludes_outside_and_nonfinite(self):
        mapping = np.array([[[0., 0.], [-2., 0.], [np.nan, 0.]]])
        events = {"x": np.array([0, 1, 2]), "y": np.array([0, 0, 0]), "p": np.array([0, 1, 1]), "t_us": np.array([1, 2, 3])}
        rectified, dropped = rectify_events(events, mapping, 3, 1)
        self.assertEqual(dropped, 2)
        np.testing.assert_array_equal(rectified["t_us"], [1])


class GeometryTests(unittest.TestCase):
    def test_fixed_point_gt_and_invalid_mask(self):
        disp, valid = decode_dsec_disparity(np.array([[0, 256, 2560]], dtype=np.uint16))
        self.assertTrue(np.isnan(disp[0, 0]))
        np.testing.assert_array_equal(disp[valid], [1, 10])

    def test_known_projection_and_back_projection(self):
        # SYNTHETIC: f=500px, B=0.2m, cx=320, cy=240; d=10 -> Z=10m.
        q = [[1, 0, 0, -320], [0, 1, 0, -240], [0, 0, 0, 500], [0, 0, 5, 0]]
        xyz = reproject_q(370, 265, 10, q)
        np.testing.assert_allclose(xyz, [1, .5, 10])
        np.testing.assert_allclose([500*xyz[0]/xyz[2]+320, 500*xyz[1]/xyz[2]+240], [370, 265])

    def test_q_handles_principal_point_offset(self):
        q = [[1, 0, 0, -320], [0, 1, 0, -240], [0, 0, 0, 500], [0, 0, 5, -10]]
        np.testing.assert_allclose(reproject_q(320, 240, 12, q), [0, 0, 10])

    def test_invalid_depth_not_fabricated(self):
        q = [[1, 0, 0, -320], [0, 1, 0, -240], [0, 0, 0, 500], [0, 0, 5, 0]]
        xyz = reproject_q([320]*3, [240]*3, [0, -1, np.nan], q)
        self.assertTrue(np.isnan(xyz).all())


if __name__ == "__main__":
    unittest.main(verbosity=2)
