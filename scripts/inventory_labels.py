"""Count official training labels per sequence to guide subsequent sampling."""

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CLASSES = ("pedestrian", "rider", "car", "bus", "truck", "bicycle", "motorcycle", "train")


def main():
    source = ROOT / "data/raw/zurich_city_04_e/detection_labels/train_labels/train"
    paths = sorted(source.rglob("tracks.npy"))
    if not paths:
        raise FileNotFoundError("Download and extract --labels first")
    records = []
    for path in paths:
        labels = np.load(path, allow_pickle=False)
        if not {"t", "class_id", "track_id"}.issubset(labels.dtype.names or ()):
            raise ValueError(f"Unexpected label fields in {path}")
        if not np.isin(labels["class_id"], np.arange(len(CLASSES))).all():
            raise ValueError(f"Unknown class in {path}")
        records.append({"sequence": path.relative_to(source).parts[0], "label_timestamps": len(np.unique(labels["t"])), "boxes_by_class": {name: int((labels["class_id"] == index).sum()) for index, name in enumerate(CLASSES)}, "distinct_track_ids": len(np.unique(labels["track_id"]))})
    output = ROOT / "outputs/reports"
    output.mkdir(parents=True, exist_ok=True)
    (output / "label_inventory.json").write_text(json.dumps({"meaning": "Annotation instances, NOT distinct people/cars; source train archive includes sequences used as detection validation", "sequences": records}, indent=2), encoding="utf-8")
    print("sequence,pedestrian_boxes,car_boxes")
    for item in sorted(records, key=lambda r: -r["boxes_by_class"]["pedestrian"])[:12]:
        print(f"{item['sequence']},{item['boxes_by_class']['pedestrian']},{item['boxes_by_class']['car']}")


if __name__ == "__main__":
    main()
