"""Build the unexecuted Colab notebook from verified export/source metadata."""

import ast
import argparse
import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-report', type=Path, default=ROOT/'outputs/reports/Y00_export.json')
    parser.add_argument('--output', type=Path, default=ROOT/'notebooks/Y01_yolo11n_events_pilot.ipynb')
    args = parser.parse_args()
    export = json.loads(args.export_report.read_text())
    class_names = {int(k): v for k, v in export.get('names', {'0': 'person', '1': 'car'}).items()}
    nc = len(class_names)
    if class_names not in ({0: 'person', 1: 'car'}, {0: 'person', 1: 'car', 2: 'truck'}):
        raise ValueError('Unsupported class profile')
    if nc == 3 and args.output.resolve() == (ROOT/'notebooks/Y01_yolo11n_events_pilot.ipynb').resolve():
        raise ValueError('Choose a new notebook destination for the truck extension')
    experiment = 'Y02' if nc == 3 else 'Y01'
    counts = export['verification']['counts']
    missing = export['verification'].get('validation_missing_classes', [])
    source = json.loads((ROOT/"outputs/reports/ultralytics_source_audit/provenance.json").read_text())
    archive_name = export["archive"].replace("\\", "/").rsplit("/", 1)[-1]
    dataset_name = Path(archive_name).stem
    cells = []

    def add(kind, text):
        value = {"cell_type": kind, "id": f"pfe-{len(cells):03d}", "metadata": {},
                 "source": textwrap.dedent(text).strip()+"\n"}
        if kind == "code":
            ast.parse(value["source"])
            value.update(execution_count=None, outputs=[])
        cells.append(value)

    add("markdown", f"""
    # YOLO11n sur événements DSEC : pilote {experiment}

    **Statut livré : NOT RUN sur Colab.** L'export Y00 est réel et vérifié localement ; aucune métrique de réseau n'est fournie.

    Classes : {class_names}. Person correspond à pedestrian DSEC. Les classes exclues deviennent du fond. Images natives 640×480,
    fenêtre causale 50 ms, canaux PNG R/G/B = positif/négatif/total. Ce ne sont pas des couleurs de scène.

    Train : {counts['train']['images']} images du groupe zurich_city_04. Validation locale : {counts['val']['images']} images thun_00_a.
    Aucune image du test réservé. Les nombreuses dates voisines ne sont pas des observations indépendantes.
    **Classes absentes de la validation : {missing or 'aucune'}.** Leur AP sera `null`, jamais inventée.
    Le meilleur checkpoint est choisi uniquement sur les classes évaluables. Il ne valide pas une classe absente.
    Ce notebook prépare un essai ; il ne remplace pas automatiquement le modèle du démonstrateur.

    **Utilisation :** importer ce notebook dans Colab, choisir un runtime GPU, exécuter les cellules dans l'ordre.
    Placer `{archive_name}` dans `Mon Drive/PFE3/data/`, ou utiliser le téléversement proposé si absent.
    Les poids et journaux seront sauvegardés sous `Mon Drive/PFE3/runs/`. Monter Drive nécessite votre connexion Google.
    Aucun abonnement, service d'entraînement payant ou publication n'est configuré.

    Sources : [format YOLO](https://docs.ultralytics.com/datasets/detect/),
    [YOLO11](https://docs.ultralytics.com/models/yolo11/), [DSEC](https://dsec.ifi.uzh.ch/).
    Les images dérivées conservent l'attribution DSEC et les conditions CC BY-SA 4.0 ; consulter `NOTICE.txt`.
    """)
    add("markdown", "## 1. Vérifier le GPU puis installer la version Ultralytics auditée\nLa pile PyTorch/CUDA fournie par Colab est conservée. Les versions réellement résolues seront enregistrées.")
    add("code", f"""
    import sys, subprocess, platform, json, os
    from pathlib import Path
    CLASS_NAMES = {class_names!r}
    EXPERIMENT = {experiment!r}
    VALIDATION_SUPPORT = {counts['val']['boxes']!r}
    import torch
    assert sys.version_info >= (3, 11), "Ce notebook requiert Python >=3.11."
    assert torch.cuda.is_available(), "Sélectionner Exécution > Modifier le type d'exécution > GPU, puis relancer."
    print(platform.python_version(), torch.__version__, torch.cuda.get_device_name(0))
    ULTRALYTICS_VERSION = {source['version']!r}
    subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                    "ultralytics=="+ULTRALYTICS_VERSION], check=True)
    """)
    add("markdown", "## 2. Créer une session persistante et journaliser l'environnement")
    add("code", """
    from datetime import datetime, timezone
    from google.colab import drive
    drive.mount('/content/drive')
    DRIVE_ROOT = Path('/content/drive/MyDrive/PFE3')
    SESSION = EXPERIMENT + '_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    RUN_DIR = DRIVE_ROOT / 'runs' / SESSION
    RUN_DIR.mkdir(parents=True, exist_ok=False)
    def write_json(path, value):
        Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    import importlib.metadata, hashlib, numpy as np, cv2, yaml, ultralytics
    from PIL import Image, ImageDraw
    from ultralytics import YOLO, settings
    assert ultralytics.__version__ == ULTRALYTICS_VERSION
    # Désactiver les intégrations externes ; conserver les résultats dans Drive.
    settings.update({k: False for k in ('sync', 'wandb', 'comet', 'clearml', 'mlflow', 'neptune', 'raytune') if k in settings})
    def sha256(path):
        with Path(path).open('rb') as f:
            return hashlib.file_digest(f, 'sha256').hexdigest()
    environment = {'utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
                   'torch': torch.__version__, 'cuda': torch.version.cuda,
                   'gpu': torch.cuda.get_device_name(0),
                   'vram_bytes': torch.cuda.get_device_properties(0).total_memory,
                   'versions': {k: importlib.metadata.version(k) for k in ('ultralytics', 'numpy', 'Pillow', 'PyYAML')}}
    write_json(RUN_DIR/'environment.json', environment)
    (RUN_DIR/'pip-freeze.txt').write_text(subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True))
    write_json(RUN_DIR/'status.json', {'status': 'SETUP', 'training': 'NOT RUN'})
    print('Résultats persistants :', RUN_DIR)
    """)
    add("markdown", "## 3. Copier, vérifier et extraire le paquet Y00\nL'empreinte attendue est intégrée au notebook. Un autre export exige un nouveau notebook ou une modification explicite et documentée de cette empreinte.")
    add("code", f"""
    import shutil, zipfile
    EXPECTED_ARCHIVE_SHA256 = {export['archive_sha256']!r}
    ARCHIVE_NAME = {archive_name!r}
    source_archive = DRIVE_ROOT/'data'/ARCHIVE_NAME
    if not source_archive.is_file():
        from google.colab import files
        os.chdir('/content')
        print('Téléverser', ARCHIVE_NAME)
        uploaded = files.upload()
        assert ARCHIVE_NAME in uploaded, 'Archive attendue absente.'
        source_archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path('/content')/ARCHIVE_NAME, source_archive)
        del uploaded
    local_archive = Path('/content')/ARCHIVE_NAME
    if source_archive.resolve() != local_archive.resolve():
        shutil.copy2(source_archive, local_archive)
    assert sha256(local_archive) == EXPECTED_ARCHIVE_SHA256, 'Archive différente ou transfert incomplet.'
    extract_root = Path('/content')/SESSION
    extract_root.mkdir(exist_ok=False)
    with zipfile.ZipFile(local_archive) as archive:
        assert sum(x.file_size for x in archive.infolist()) < 1024**3, 'Budget extraction dépassé.'
        for entry in archive.infolist():
            target = (extract_root/entry.filename).resolve()
            assert target.is_relative_to(extract_root.resolve()), 'Chemin ZIP invalide.'
            assert (entry.external_attr >> 16) & 0o170000 != 0o120000, 'Lien ZIP non accepté.'
        archive.extractall(extract_root)
    DATA_ROOT = extract_root/{dataset_name!r}
    subprocess.run([sys.executable, str(DATA_ROOT/'verify_yolo_export.py'), str(DATA_ROOT),
                    '--report', str(RUN_DIR/'dataset-verification.json')], check=True)
    manifest = json.loads((DATA_ROOT/'manifest.json').read_text())
    write_json(RUN_DIR/'dataset-provenance.json', {{'archive_sha256': EXPECTED_ARCHIVE_SHA256,
               'manifest_sha256': sha256(DATA_ROOT/'manifest.json'), 'normalizer_sha256': sha256(DATA_ROOT/'normalizer.json'),
               'groups': {{s['name']:s['split'] for s in manifest['sequences']}}}})
    for name in ('manifest.json', 'normalizer.json', 'NOTICE.txt'):
        shutil.copy2(DATA_ROOT/name, RUN_DIR/name)
    data = yaml.safe_load((DATA_ROOT/'data.yaml').read_text())
    assert data['names'] == CLASS_NAMES
    data['path'] = str(DATA_ROOT)
    DATA_YAML = DATA_ROOT/'data_runtime.yaml'
    DATA_YAML.write_text(yaml.safe_dump(data))
    overfit_data = {{**data, 'train': 'overfit.txt', 'val': 'overfit.txt'}}
    OVERFIT_YAML = DATA_ROOT/'overfit_runtime.yaml'
    OVERFIT_YAML.write_text(yaml.safe_dump(overfit_data))
    print('Dataset validé ; les chemins runtime sont absolus et spécifiques à cette session.')
    """)
    add("markdown", """
    ## 4. Vérifier les vrais tenseurs Ultralytics et afficher un lot
    Le chargeur lit BGR, puis `Format(bgr=0)` restitue RGB : l'ordre doit rester positif/négatif/total.
    HSV, permutation BGR et augmentations Albumentations sont désactivés. La liste vide `augmentations=[]`
    empêche notamment l'ajout implicite de niveaux de gris/CLAHE si Albumentations est installé dans Colab.
    Le test contrôle les chemins train **et** validation, avec letterbox de 80 pixels en haut et en bas.
    """)
    add("code", """
    from ultralytics.cfg import get_cfg
    from ultralytics.data.dataset import YOLODataset
    NO_AUG = dict(hsv_h=0.0, hsv_s=0.0, hsv_v=0.0, bgr=0.0, augmentations=[],
                  mosaic=0.0, mixup=0.0, cutmix=0.0, copy_paste=0.0,
                  degrees=0.0, translate=0.0, scale=0.0, shear=0.0, perspective=0.0,
                  flipud=0.0, fliplr=0.0)
    runtime_data = {**data, 'nc': len(CLASS_NAMES), 'channels': 3}
    def make_dataset(split, augment):
        hyp = get_cfg(overrides=dict(imgsz=640, task='detect', **NO_AUG))
        return YOLODataset(img_path=str(DATA_ROOT/'images'/split), imgsz=640, batch_size=4,
                           augment=augment, hyp=hyp, rect=False, cache=False, stride=32,
                           data=runtime_data, task='detect')
    train_dataset = make_dataset('train', True)
    validation_dataset = make_dataset('val', False)
    for dataset in (train_dataset, validation_dataset):
        # Vérifier plusieurs images, avec labels lus indépendamment du chargeur.
        for index in (0, len(dataset)//2, len(dataset)-1):
            sample = dataset[index]
            image_path = Path(sample['im_file'])
            native = np.asarray(Image.open(image_path))
            expected = np.pad(native, ((80,80),(0,0),(0,0)), constant_values=114)
            actual = sample['img'].cpu().numpy().transpose(1,2,0)
            np.testing.assert_array_equal(actual, expected)
            label_path = DATA_ROOT/'labels'/image_path.parent.name/(image_path.stem+'.txt')
            text = label_path.read_text().strip()
            labels = np.array([[float(v) for v in line.split()] for line in text.splitlines()]).reshape(-1,5)
            expected_boxes = labels[:,1:].copy()
            expected_boxes[:,1] = (expected_boxes[:,1]*480+80)/640
            expected_boxes[:,3] *= 480/640
            np.testing.assert_allclose(sample['bboxes'].numpy(), expected_boxes, atol=2e-6)
            np.testing.assert_array_equal(sample['cls'].numpy().ravel(), labels[:,0])
    batch = train_dataset.collate_fn([train_dataset[i] for i in range(4)])
    assert batch['img'].shape == (4,3,640,640)
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2,2,figsize=(12,12))
    for i, ax in enumerate(axes.flat):
        preview = Image.fromarray(batch['img'][i].numpy().transpose(1,2,0))
        draw = ImageDraw.Draw(preview)
        ids = batch['batch_idx'].numpy().ravel() == i
        for cls, box in zip(batch['cls'].numpy()[ids].ravel(), batch['bboxes'].numpy()[ids]):
            cx,cy,w,h = box*640
            draw.rectangle((cx-w/2,cy-h/2,cx+w/2,cy+h/2), outline='lime', width=2)
            draw.text((cx-w/2,max(0,cy-h/2-12)), data['names'][int(cls)], fill='white')
        ax.imshow(preview); ax.axis('off'); ax.set_title('Labels rechargés — pas des prédictions')
    plt.tight_layout(); plt.savefig(RUN_DIR/'reloaded_batch.png'); plt.show()
    CHECKS_PASSED = True
    # Même avec des transformations identités, RandomPerspective filtre de très
    # petites boîtes. Publier ce décompte, distinct du nombre de labels exportés.
    train_class_boxes_loaded = np.zeros(len(CLASS_NAMES), dtype=np.int64)
    for i in range(len(train_dataset)):
        ids = train_dataset[i]['cls'].numpy().ravel().astype(np.int64)
        train_class_boxes_loaded += np.bincount(ids, minlength=len(CLASS_NAMES))
    train_boxes_loaded = int(train_class_boxes_loaded.sum())
    train_boxes_exported = sum(f['conversion']['kept'] for f in manifest['frames'] if f['split']=='train')
    mapping = {int(k): v for k,v in manifest['class_mapping'].items()}
    train_class_boxes_exported = np.bincount([mapping[c] for f in manifest['frames'] if f['split']=='train'
                                               for c in f['source_class_ids_kept']], minlength=len(CLASS_NAMES))
    assert 0 < train_boxes_loaded <= train_boxes_exported
    assert np.all(train_class_boxes_loaded > 0) and np.all(train_class_boxes_loaded <= train_class_boxes_exported)
    write_json(RUN_DIR/'tensor-check.json', {'status':'PASS', 'images_checked':6,
               'channels':['positive','negative','total'], 'letterbox':[80,80], 'training':'NOT RUN',
               'train_boxes_exported':train_boxes_exported, 'train_boxes_loaded':train_boxes_loaded,
               'train_boxes_exported_by_class':train_class_boxes_exported.tolist(),
               'train_boxes_loaded_by_class':train_class_boxes_loaded.tolist(),
               'train_boxes_filtered_by_framework':train_boxes_exported-train_boxes_loaded})
    """)
    add("markdown", """
    ## 5. Fixer la configuration et télécharger les poids officiels
    Initialisation COCO uniquement : sa précision événementielle n'est pas supposée. Aucune mesure de référence COCO
    non adaptée n'est calculée ici. L'essai complet repartira des mêmes poids initiaux, pas des poids surappris.
    AMP est désactivé pour ce premier contrôle ; la VRAM sera mesurée. Budget pilote : cinq époques.
    """)
    add("code", """
    assert CHECKS_PASSED
    weights_dir = RUN_DIR/'initial_weights'
    weights_dir.mkdir()
    INITIAL = weights_dir/'yolo11n.pt'
    initial_model = YOLO(str(INITIAL))
    assert INITIAL.is_file(), 'Poids non disponibles.'
    write_json(RUN_DIR/'checkpoint-provenance.json', {'file':str(INITIAL), 'sha256':sha256(INITIAL),
               'source':'Ultralytics official asset downloader; yolo11n COCO', 'event_finetuning':'NOT RUN'})
    del initial_model
    COMMON = dict(imgsz=640, batch=4, workers=2, device=0, seed=42, deterministic=True,
                  optimizer='AdamW', lr0=0.001, lrf=0.01, momentum=0.9, weight_decay=0.0005,
                  warmup_epochs=1.0, cache=False, amp=False, compile=False,
                  rect=False, save=True, save_period=1, plots=True, patience=0,
                  project=str(RUN_DIR), exist_ok=False, close_mosaic=0, **NO_AUG)
    OVERFIT_EPOCHS = 100
    # Le diagnostic sur huit images doit mettre à jour les poids à chaque batch.
    # Ne pas modifier COMMON : les réglages du pilote complet restent séparés.
    OVERFIT_COMMON = {**COMMON, 'nbs': 4, 'warmup_epochs': 0.0,
                      'lrf': 1.0, 'weight_decay': 0.0}
    PILOT_EPOCHS = 5
    OVERFIT_MIN_AP50 = 0.80  # garde diagnostic par classe, pas seuil de validation scientifique
    write_json(RUN_DIR/'requested-config.json', {'common':COMMON, 'overfit_common':OVERFIT_COMMON, 'overfit_epochs':OVERFIT_EPOCHS,
               'pilot_epochs':PILOT_EPOCHS, 'overfit_min_ap50':OVERFIT_MIN_AP50})
    def metrics_dict(metrics, purpose, support):
        per_class = []
        indexes = {int(cls): i for i, cls in enumerate(metrics.box.ap_class_index)}
        for cls, name in CLASS_NAMES.items():
            i = indexes.get(cls)
            available = support[cls] > 0 and i is not None
            per_class.append({'class_id':cls, 'name':name, 'label_support':int(support[cls]),
                              'status':'EVALUATED' if available else 'NOT_EVALUATED',
                              'ap50':float(metrics.box.ap50[i]) if available else None,
                              'ap50_95':float(metrics.box.ap[i]) if available else None})
        return {'purpose':purpose, 'map50':float(metrics.box.map50), 'map50_95':float(metrics.box.map),
                'map_scope':'Framework aggregate over supported classes only; not all-class validation',
                'per_class':per_class, 'validation_conf_floor':0.001, 'nms_iou':0.7,
                'max_det':300, 'metrics':{k:float(v) for k,v in metrics.results_dict.items()}}
    """)
    add("markdown", """
    ## 6. Surapprendre huit images de train
    Train et validation pointent volontairement vers **les mêmes huit images** pour ce diagnostic uniquement.
    L'arrêt en cas d'AP50 insuffisante sert à corriger le chargement ou la configuration avant un essai plus long.
    Il ne faut pas contourner cet arrêt en présentant les scores du petit lot comme une généralisation.
    Révision après le premier essai : 100 époques, nbs=4, sans warm-up ni décroissance du LR,
    sans régularisation des poids pour ce diagnostic. Le lot de huit images est inchangé.
    """)
    add("code", """
    assert CHECKS_PASSED
    overfit_classes = []
    for relative in (DATA_ROOT/'overfit.txt').read_text().splitlines():
        label = DATA_ROOT/relative.removeprefix('./').replace('images/','labels/')
        overfit_classes.extend(int(line.split()[0]) for line in label.with_suffix('.txt').read_text().splitlines())
    assert set(overfit_classes) == set(CLASS_NAMES), 'Le petit lot doit contenir toutes les classes.'
    overfit_support = np.bincount(overfit_classes, minlength=len(CLASS_NAMES)).tolist()
    write_json(RUN_DIR/'status.json', {'status':'OVERFIT_RUNNING', 'generalization':'NOT EVALUATED'})
    try:
        model = YOLO(str(INITIAL))
        optimizer_counter = {'steps': 0}
        def install_counter(trainer):
            def count_step(optimizer, args, kwargs):
                optimizer_counter['steps'] += 1
            trainer.optimizer.register_step_post_hook(count_step)
        model.add_callback('on_train_start', install_counter)
        model.train(data=str(OVERFIT_YAML), epochs=OVERFIT_EPOCHS, name='overfit', **OVERFIT_COMMON)
        OVERFIT_BEST = Path(model.trainer.save_dir)/'weights/best.pt'
        overfit_metrics = YOLO(str(OVERFIT_BEST)).val(data=str(OVERFIT_YAML), imgsz=640, batch=4, device=0,
                             conf=0.001, iou=0.7, max_det=300, workers=2,
                             project=str(RUN_DIR), name='overfit_check', plots=True)
        overfit_report = metrics_dict(overfit_metrics, 'TRAIN-SET FIT DIAGNOSTIC; NOT GENERALIZATION', overfit_support)
        overfit_report['optimizer_steps'] = optimizer_counter['steps']
        write_json(RUN_DIR/'overfit-metrics.json', overfit_report)
        OVERFIT_PASSED = all(r['ap50'] is not None and r['ap50'] >= OVERFIT_MIN_AP50 for r in overfit_report['per_class'])
        assert OVERFIT_PASSED, 'Surapprentissage insuffisant : inspecter lot, labels et courbes avant de poursuivre.'
        write_json(RUN_DIR/'status.json', {'status':'OVERFIT_PASSED', 'pilot':'NOT RUN'})
    except Exception as error:
        write_json(RUN_DIR/'status.json', {'status':'OVERFIT_FAILED', 'error':repr(error), 'pilot':'NOT RUN'})
        raise
    """)
    add("markdown", "## 7. Pilote de cinq époques puis validation locale\nLe groupe thun_00 reste séparé. Aucun test réservé n'est ouvert. Ce corpus est trop petit pour conclure à une généralisation routière.")
    add("code", """
    assert CHECKS_PASSED and OVERFIT_PASSED
    write_json(RUN_DIR/'status.json', {'status':'PILOT_RUNNING'})
    try:
        torch.cuda.reset_peak_memory_stats()
        model = YOLO(str(INITIAL))  # nouvelle initialisation, pas reprise du petit lot
        model.train(data=str(DATA_YAML), epochs=PILOT_EPOCHS, name='pilot', **COMMON)
        PILOT_DIR = Path(model.trainer.save_dir)
        BEST = PILOT_DIR/'weights/best.pt'
        LAST = PILOT_DIR/'weights/last.pt'
        assert BEST.is_file() and LAST.is_file()
        validation = YOLO(str(BEST)).val(data=str(DATA_YAML), split='val', imgsz=640, batch=4, device=0,
                     conf=0.001, iou=0.7, max_det=300, workers=2,
                     project=str(RUN_DIR), name='pilot_validation', plots=True)
        report = metrics_dict(validation, 'LOCAL VALIDATION thun_00_a; NOT OFFICIAL BENCHMARK', VALIDATION_SUPPORT)
        report.update({'best_sha256':sha256(BEST), 'last_sha256':sha256(LAST),
                       'checkpoint_selection_classes':[CLASS_NAMES[i] for i, n in enumerate(VALIDATION_SUPPORT) if n],
                       'truck_independent_quality':'NOT EVALUATED' if 'truck' in CLASS_NAMES.values() and not VALIDATION_SUPPORT[2] else 'SEE PER CLASS',
                       'peak_gpu_allocated_bytes':torch.cuda.max_memory_allocated(),
                       'dataset_sha256':EXPECTED_ARCHIVE_SHA256})
        write_json(RUN_DIR/'pilot-metrics.json', report)
        for required in (PILOT_DIR/'args.yaml', PILOT_DIR/'results.csv', BEST, LAST):
            assert required.is_file() and required.stat().st_size > 0, str(required)
        write_json(RUN_DIR/'status.json', {'status':'PILOT_COMPLETE', 'test_reserved':'NOT RUN',
                                          'object_depth_fusion':'NOT RUN'})
        print(json.dumps(report, indent=2))
        print('Poids, configuration effective et journaux sauvegardés :', RUN_DIR)
    except Exception as error:
        write_json(RUN_DIR/'status.json', {'status':'PILOT_FAILED', 'error':repr(error)})
        raise
    """)
    add("markdown", """
    ## Après exécution / reprise

    Conserver `status.json`, `environment.json`, `pip-freeze.txt`, `dataset-provenance.json`,
    `tensor-check.json`, `overfit-metrics.json`, `pilot-metrics.json`, `pilot/args.yaml`,
    `pilot/results.csv`, et les poids `best.pt`/`last.pt`. Les métriques ne seront considérées exécutées
    dans le projet local qu'après récupération de ces preuves. Les images de lots restent des annotations,
    pas des détections prédites. Les scores du surapprentissage restent séparés de la validation.

    En cas de déconnexion pendant un entraînement, remonter Drive, recopier la même archive vérifiée,
    reconstruire ses chemins runtime puis reprendre **le checkpoint de la session précédente** :
    `YOLO('/content/drive/MyDrive/PFE3/runs/SESSION/pilot/weights/last.pt').train(resume=True, data=str(DATA_YAML), device=0)`.
    Consigner la reprise et son environnement. Ne pas écraser une session complète pour faire un nouvel essai.
    Si le framework ne retrouve pas les anciens chemins après une reconnexion, utiliser le même dossier `/content/SESSION`
    pour réextraire les données avant la reprise. Une reprise depuis un entraînement déjà terminé n'est pas la continuation d'un essai interrompu.

    Le protocole est prêt mais **aucune cellule GPU n'a été exécutée lors de la création locale du notebook**.
    """)
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python"}, "accelerator": "GPU",
                "colab": {"name": args.output.name, "provenance": []}}, "nbformat": 4, "nbformat_minor": 5}
    path = args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Created {path}: {len(cells)} cells; code parsed; GPU cells NOT RUN")


if __name__ == "__main__":
    main()
