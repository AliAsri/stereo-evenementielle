"""Explicit DSEC -> two-class native YOLO label conversion."""

import numpy as np

CLASS_MAP = {0: 0, 2: 1}  # DSEC pedestrian/car -> YOLO person/car. Rider stays excluded.
CLASS_NAMES = {0: "person", 1: "car"}


def convert_boxes(boxes, width=640, height=480):
    """Clip native xywh, reject invalid geometry, preserve source row identities.

    No minimum-size filtering. Other DSEC classes become background in this
    two-class pilot. Exact duplicate output labels are explicitly counted.
    """
    required = {"x", "y", "w", "h", "class_id"}
    if not required.issubset(boxes.dtype.names or ()) or width <= 0 or height <= 0:
        raise ValueError("Invalid box schema or image dimensions")
    if not np.isin(boxes["class_id"], range(8)).all():
        raise ValueError("Unknown DSEC class")
    stats = {"source": len(boxes), "excluded_class": 0, "invalid_geometry": 0,
             "outside_or_degenerate": 0, "clipped": 0, "duplicate": 0, "kept": 0}
    labels, source_rows, seen = [], [], set()
    for index, box in enumerate(boxes):
        original_class = int(box["class_id"])
        if original_class not in CLASS_MAP:
            stats["excluded_class"] += 1
            continue
        x, y, w, h = (float(box[k]) for k in ("x", "y", "w", "h"))
        if not np.isfinite([x, y, w, h]).all() or w <= 0 or h <= 0:
            stats["invalid_geometry"] += 1
            continue
        native = np.array([x, y, x+w, y+h])
        clipped = np.clip(native, [0, 0, 0, 0], [width, height, width, height])
        x1, y1, x2, y2 = clipped
        if x2 <= x1 or y2 <= y1:
            stats["outside_or_degenerate"] += 1
            continue
        stats["clipped"] += int(not np.array_equal(native, clipped))
        row = (CLASS_MAP[original_class], (x1+x2)/(2*width), (y1+y2)/(2*height),
               (x2-x1)/width, (y2-y1)/height)
        # Match serialization precision: duplicates after rounding are also removed.
        key = tuple(np.round(row, 9))
        if key in seen:
            stats["duplicate"] += 1
            continue
        seen.add(key)
        labels.append(row)
        source_rows.append(index)
    stats["kept"] = len(labels)
    assert stats["source"] == sum(stats[k] for k in ("excluded_class", "invalid_geometry", "outside_or_degenerate", "duplicate", "kept"))
    return np.array(labels, dtype=np.float64).reshape(-1, 5), source_rows, stats


def labels_to_text(labels):
    return "".join(f"{int(row[0])} " + " ".join(f"{v:.9f}" for v in row[1:]) + "\n" for row in labels)
