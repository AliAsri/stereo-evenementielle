"""Copy this ENTIRE file into ONE NEW Colab cell after the failed overfit cell.

Requires the original notebook's setup variables in the still-active runtime.
Preserves the failed run. Executes one new diagnostic, NOT the full pilot.
Y01 person/car only; supports both historical and regenerated reporting APIs.
"""

from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import inspect
import json
import math

import torch
import ultralytics
import yaml
from ultralytics import YOLO


def prepare_retry_reporting(metrics_fn, data_root, subset):
    """Check Y01 label support and reporting compatibility BEFORE any training."""
    support = [0, 0]
    for relative in subset:
        label = data_root/relative.removeprefix('./').replace('images/', 'labels/', 1)
        for line in label.with_suffix('.txt').read_text().splitlines():
            cls = int(line.split()[0])
            if cls not in (0, 1):
                raise ValueError('This retry cell is for Y01 person/car only')
            support[cls] += 1
    if not all(support):
        raise ValueError('Y01 retry requires both person and car labels')
    signature = inspect.signature(metrics_fn)
    kwargs = {'support': support} if 'support' in signature.parameters else {}
    signature.bind(None, 'same train subset diagnostic', **kwargs)
    return kwargs


required = ("RUN_DIR", "INITIAL", "OVERFIT_YAML", "DATA_ROOT", "COMMON", "CHECKS_PASSED", "metrics_dict")
missing = [name for name in required if name not in globals()]
assert not missing, f"Runtime incomplet ({missing}). Utiliser le notebook mis à jour depuis la préparation."
assert CHECKS_PASSED and torch.cuda.is_available()
assert ultralytics.__version__ == "8.4.172", "Version différente : réauditer la configuration."
assert Path(INITIAL).is_file() and Path(OVERFIT_YAML).is_file()
OVERFIT_PASSED = False
OVERFIT_MIN_AP50 = 0.80

# Afficher la configuration et les dernières pertes de l'essai précédent.
previous_args = Path(RUN_DIR)/"overfit/args.yaml"
if previous_args.exists():
    previous = yaml.safe_load(previous_args.read_text())
    print("Configuration précédente :", {k: previous.get(k) for k in
          ("epochs", "batch", "nbs", "warmup_epochs", "optimizer", "lr0", "lrf", "weight_decay")})
previous_csv = Path(RUN_DIR)/"overfit/results.csv"
if previous_csv.exists():
    with previous_csv.open() as stream:
        rows = list(csv.DictReader(stream))
    print("Cinq dernières lignes de pertes/métriques :")
    for row in rows[-5:]:
        print({k.strip(): v.strip() for k, v in row.items()})

# Même lot et même initialisation : on corrige d'abord le budget d'optimisation.
subset = (Path(DATA_ROOT)/"overfit.txt").read_text().splitlines()
assert len(subset) == len(set(subset)) == 8
assert all(line.startswith("./images/train/") for line in subset)
retry_names = yaml.safe_load(Path(OVERFIT_YAML).read_text())['names']
assert retry_names in ({0: 'person', 1: 'car'}, ['person', 'car']), 'Cellule réservée à Y01 personne/voiture.'
retry_metrics_kwargs = prepare_retry_reporting(metrics_dict, Path(DATA_ROOT), subset)
attempt = Path(RUN_DIR)/("overfit_retry_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
attempt.mkdir(exist_ok=False)

def retry_json(name, value):
    (attempt/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")

retry_args = {**COMMON, "project": str(attempt), "name": "fit", "epochs": 100,
              "nbs": 4, "batch": 4, "warmup_epochs": 0.0, "lr0": 0.001,
              "lrf": 1.0, "weight_decay": 0.0, "patience": 0,
              "resume": False, "exist_ok": False}
retry_json("requested-config.json", {"args": retry_args, "subset": subset,
           "initial_sha256": hashlib.sha256(Path(INITIAL).read_bytes()).hexdigest(),
           "subset_sha256": hashlib.sha256((Path(DATA_ROOT)/"overfit.txt").read_bytes()).hexdigest(),
           "purpose": "same-train-set fit diagnostic; not generalization"})
retry_json("status.json", {"status": "RUNNING", "full_pilot": "NOT RUN"})

# Compter les vrais appels de l'optimiseur, pas seulement les époques.
counter = {"optimizer_steps": 0}
def attach_step_counter(trainer):
    def count_step(optimizer, args, kwargs):
        counter["optimizer_steps"] += 1
    trainer.optimizer.register_step_post_hook(count_step)

try:
    retry_model = YOLO(str(INITIAL))  # pas resume=True : le premier essai est terminé
    retry_model.add_callback("on_train_start", attach_step_counter)
    retry_model.train(data=str(OVERFIT_YAML), **retry_args)
    retry_best = Path(retry_model.trainer.save_dir)/"weights/best.pt"
    retry_metrics = YOLO(str(retry_best)).val(
        data=str(OVERFIT_YAML), imgsz=640, batch=4, device=0, conf=0.001,
        iou=0.7, max_det=300, workers=2, project=str(attempt), name="check", plots=True)
    retry_report = metrics_dict(retry_metrics, "SAME TRAIN SUBSET DIAGNOSTIC; NOT GENERALIZATION",
                                **retry_metrics_kwargs)
    retry_report.update(counter)
    retry_report["best_sha256"] = hashlib.sha256(retry_best.read_bytes()).hexdigest()
    retry_json("metrics.json", retry_report)
    # Sauver quelques prédictions à seuil visuel déclaré pour examiner les faux positifs.
    source_images = [str(Path(DATA_ROOT)/p.removeprefix("./")) for p in subset]
    YOLO(str(retry_best)).predict(source=source_images, imgsz=640, device=0, conf=0.25,
                                 iou=0.7, max_det=300, save=True, project=str(attempt), name="predictions")
    OVERFIT_PASSED = ({r["class_id"] for r in retry_report["per_class"]} == {0, 1}
                      and all(math.isfinite(r["ap50"]) and r["ap50"] >= OVERFIT_MIN_AP50
                              for r in retry_report["per_class"]))
    retry_json("status.json", {"status": "PASSED" if OVERFIT_PASSED else "GATE_FAILED",
                               **counter, "full_pilot": "NOT RUN"})
    print(json.dumps(retry_report, indent=2))
    print("Essai conservé dans :", attempt)
    if OVERFIT_PASSED:
        OVERFIT_BEST = retry_best
        print("Diagnostic réussi. La cellule 7 du notebook peut maintenant être exécutée.")
    else:
        print("Arrêt conservé. Examiner metrics.json, fit/results.csv et predictions avant un nouvel essai.")
except Exception as error:
    OVERFIT_PASSED = False
    retry_json("status.json", {"status": "ERROR", "error": repr(error), **counter})
    raise
