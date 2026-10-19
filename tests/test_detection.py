"""Synthetic label geometry; no accuracy claims about a trained detector."""

import sys
import json
import ast
import runpy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from pfe_events.detection import convert_boxes, labels_to_text, TRUCK_CLASS_MAP

DTYPE = [("x", "f8"), ("y", "f8"), ("w", "f8"), ("h", "f8"), ("class_id", "i4")]


class DetectionTests(unittest.TestCase):
    def test_truck_extension_preserves_old_classes_and_source_rows(self):
        boxes = np.array([(10, 20, 30, 40, cls) for cls in range(8)], dtype=DTYPE)
        old, old_rows, _ = convert_boxes(boxes)
        new, rows, stats = convert_boxes(boxes, class_map=TRUCK_CLASS_MAP)
        np.testing.assert_array_equal(new[:2], old)
        self.assertEqual(rows, old_rows+[4])
        self.assertEqual(new[2, 0], 2)
        np.testing.assert_array_equal(new[2, 1:], old[0, 1:])
        self.assertEqual(stats['excluded_class'], 5)
        # The extension must not change the historical default mapping.
        np.testing.assert_array_equal(convert_boxes(boxes)[0], old)

    def test_invalid_class_maps_cannot_merge_or_invent_classes(self):
        empty = np.empty(0, dtype=DTYPE)
        for mapping in ({}, {0: 0, 4: 0}, {0: 0, 4: 2}, {8: 0}, {0: False}, {0.0: 0}):
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                convert_boxes(empty, class_map=mapping)

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


class ExportCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tools = runpy.run_path(str(ROOT/'scripts/verify_yolo_export.py'))
        parent = ROOT/'outputs/test-temp'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        frames = []
        for split, count in [('train', 8), ('val', 1)]:
            for kind in ['images', 'labels']:
                (self.root/kind/split).mkdir(parents=True)
            for i in range(count):
                seq = 'zurich_city_04_b' if split == 'train' else 'thun_00_a'
                image, label = f'images/{split}/{i}.png', f'labels/{split}/{i}.txt'
                Image.new('RGB', (640, 480), color=(i+1 if split == 'train' else 20, 2, 3)).save(self.root/image)
                classes = range(3 if split == 'train' else 2)
                (self.root/label).write_text(''.join(f'{cls} .5 .5 .1 .1\n' for cls in classes))
                frames.append(dict(sequence=seq, group=seq.rsplit('_', 1)[0], split=split, image=image,
                                   label=label, window_start_us=0, window_end_us=50000, conversion={'kept':len(classes)}))
        self.manifest = dict(status='COMPLETE', names={0:'person', 1:'car', 2:'truck'},
                             class_mapping=TRUCK_CLASS_MAP, window_us=50000, frames=frames)
        (self.root/'data.yaml').write_text(yaml.safe_dump(dict(train='images/train', val='images/val', names=self.manifest['names'])))
        (self.root/'overfit.txt').write_text(''.join(f'./images/train/{i}.png\n' for i in range(8)))

    def check(self):
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))
        hashes = {p.relative_to(self.root).as_posix(): self.tools['sha256'](p)
                  for p in self.root.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        (self.root/'checksums.json').write_text(json.dumps(hashes))
        return self.tools['verify'](self.root)

    def test_missing_truck_validation_requires_explicit_disclosure(self):
        with self.assertRaisesRegex(ValueError, 'Missing pilot class/split: val'):
            self.check()
        self.manifest['allowed_missing_validation_classes'] = [2]
        report = self.check()
        self.assertEqual(report['validation_missing_classes'], ['truck'])
        self.assertEqual(report['counts']['train']['boxes'], [8, 8, 8])
        self.assertEqual(report['counts']['val']['boxes'], [1, 1, 0])

    def test_truck_exception_does_not_allow_missing_person_validation(self):
        self.manifest['allowed_missing_validation_classes'] = [2]
        (self.root/'labels/val/0.txt').write_text('1 .5 .5 .1 .1\n')
        self.manifest['frames'][-1]['conversion']['kept'] = 1
        with self.assertRaisesRegex(ValueError, 'Missing pilot class/split: val'):
            self.check()

    def test_names_must_agree_with_training_yaml(self):
        self.manifest['names'][2] = 'bus'
        with self.assertRaisesRegex(ValueError, 'class mapping'):
            self.check()


class NotebookMetricTests(unittest.TestCase):
    def test_absent_validation_class_cannot_receive_framework_fallback_ap(self):
        notebook = json.loads((ROOT/'notebooks/Y02_yolo11n_truck.ipynb').read_text(encoding='utf-8'))
        source = next(c['source'] for c in notebook['cells']
                      if c['cell_type'] == 'code' and 'def metrics_dict(' in c['source'])
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
                    and n.name == 'metrics_dict')
        namespace = {'CLASS_NAMES': {0:'person', 1:'car', 2:'truck'}}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'notebook metrics', 'exec'), namespace)
        metrics = SimpleNamespace(box=SimpleNamespace(ap_class_index=np.array([0, 1, 2]),
            ap50=np.array([.2, .4, .99]), ap=np.array([.1, .3, .8]), map50=.3, map=.2), results_dict={})
        row = namespace['metrics_dict'](metrics, 'synthetic validation', [238, 667, 0])['per_class'][2]
        self.assertEqual(row['status'], 'NOT_EVALUATED')
        self.assertIsNone(row['ap50'])
        self.assertIsNone(row['ap50_95'])
        row = namespace['metrics_dict'](metrics, 'synthetic overfit', [3, 4, 5])['per_class'][2]
        self.assertEqual(row['ap50'], .99)


if __name__ == "__main__":
    unittest.main()
