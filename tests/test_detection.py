"""Synthetic label geometry; no accuracy claims about a trained detector."""

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from pfe_events.detection import convert_boxes, labels_to_text

DTYPE = [("x", "f8"), ("y", "f8"), ("w", "f8"), ("h", "f8"), ("class_id", "i4")]


class DetectionTests(unittest.TestCase):
    def test_mapping_and_analytical_coordinates(self):
        labels, indices, stats = convert_boxes(np.array([(64, 48, 128, 96, 0), (0, 0, 640, 480, 2), (2, 2, 20, 20, 1)], dtype=DTYPE))
        np.testing.assert_allclose(labels, [[0, .2, .2, .2, .2], [1, .5, .5, 1, 1]])
        self.assertEqual(indices, [0, 1])
        self.assertEqual(stats["excluded_class"], 1)  # rider is not person

    def test_clipping_uses_clipped_center_and_width(self):
        labels, _, stats = convert_boxes(np.array([(-20, 470, 40, 30, 0)], dtype=DTYPE))
        np.testing.assert_allclose(labels, [[0, 10/640, 475/480, 20/640, 10/480]])
        self.assertEqual(stats["clipped"], 1)

    def test_invalid_and_outside_are_counted(self):
        boxes = np.array([(1, 1, -1, 2, 0), (np.nan, 0, 2, 2, 2), (700, 0, 2, 2, 0)], dtype=DTYPE)
        labels, _, stats = convert_boxes(boxes)
        self.assertEqual(labels.shape, (0, 5))
        self.assertEqual(stats["invalid_geometry"], 2)
        self.assertEqual(stats["outside_or_degenerate"], 1)

    def test_empty_labels_and_unknown_class(self):
        labels, _, _ = convert_boxes(np.empty(0, dtype=DTYPE))
        self.assertEqual(labels_to_text(labels), "")
        with self.assertRaises(ValueError):
            convert_boxes(np.array([(0, 0, 1, 1, 8)], dtype=DTYPE))

    def test_duplicate_labels_have_traceable_source(self):
        box = (10, 20, 30, 40, 2)
        labels, indices, stats = convert_boxes(np.array([box, box], dtype=DTYPE))
        self.assertEqual(len(labels), 1)
        self.assertEqual(indices, [0])
        self.assertEqual(stats["duplicate"], 1)

    def test_text_roundtrip_preserves_native_geometry(self):
        labels, _, _ = convert_boxes(np.array([(13.3, 21.7, 122.1, 57.8, 0)], dtype=DTYPE))
        recovered = np.array([float(x) for x in labels_to_text(labels).split()])
        np.testing.assert_allclose(recovered, labels[0], atol=5e-10)
        _, cx, cy, w, h = recovered
        np.testing.assert_allclose([(cx-w/2)*640, (cy-h/2)*480, w*640, h*480], [13.3, 21.7, 122.1, 57.8], atol=1e-5)


if __name__ == "__main__":
    unittest.main()
