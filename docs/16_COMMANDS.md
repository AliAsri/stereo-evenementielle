# Commandes existantes et vérifiées

## Parcours actuel : mouvement prioritaire — 18 octobre 2026

```powershell
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --output outputs/demo_motion_priority_repeat
```

Indices de mouvement à chaque pas source de 20 ms, publiés dans `motion.jsonl` avant le contexte ; YOLO et association XYZ toutes les 100 ms dataset par défaut. Pour le contrôle à chaque date, ajouter `--context-step-ms 20` avec un autre dossier neuf. Ce paramètre ne change ni les fenêtres 50 ms, ni le suivi 100 ms, ni les profondeurs exactes utilisées par la compensation. Aucun saut de date de mouvement ; aucune cadence temps réel promise. Les contextes anciens ne sont pas superposés aux images actuelles ; `context.updated=false` distingue non-calcul et absence de détection. Les commandes historiques ci-dessous sans option utilisent désormais ce nouveau défaut.

## Rejeu intégré optimisé — 14 octobre 2026

```powershell
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --output outputs/demo_speed_repeat
```

Le cache des six dates courantes est actif par défaut ; seules les images et disparités aux timestamps exacts sont réutilisées dans la branche mouvement. Ajouter `--no-history-cache` pour le contrôle sans cache dans un autre dossier neuf. L'accumulation optimisée des événements reste active dans les deux cas ; cette option ne restaure donc pas toute l'ancienne implémentation. Les sorties du 14 octobre et leur comparaison sont dans `outputs/demo_speed_20261014/`. Voir [le suivi actif](20_NEXT_STEPS.md) pour les coûts mesurés et leurs limites.

Le démonstrateur utilise deux threads OpenCV et un thread PyTorch. Ajouter `--opencv-threads 1` pour mesurer le contrôle à un thread ; le cache et l'accumulation optimisée restent actifs. Le nombre de threads effectif est enregistré dans `summary.json` sous `cpu_execution`. Aucun changement de fenêtre temporelle ou de seuil scientifique n'est nécessaire.

## Validation actuelle — 11 octobre 2026

```powershell
.\.venv\Scripts\python.exe scripts/check_project.py --output outputs/checks/local_02
.\.venv\Scripts\python.exe scripts/run_integrated_demo.py --check-inputs
```

Choisir un dossier neuf pour les contrôles. La première commande vérifie le code, les aides CLI et les tests hors ligne ; la seconde liste les entrées manquantes puis vérifie tailles/SHA-256 contre le manifeste sans charger YOLO. Ce contrôle est aussi obligatoire avant le rejeu. Avec `--weights`, les sept entrées de scène restent vérifiées ; l'empreinte du checkpoint explicite est relevée sans conformité annoncée à Y01. Voir la [page active](20_NEXT_STEPS.md) pour le dernier bilan et le [README](../README.md#prérequis-du-rejeu-intégré) pour les dépendances. Les résultats et commandes datés ci-dessous restent historiques ; leur présence ne demande pas de reprendre les anciennes expériences.

Les deux diagnostics historiques auparavant exécutés à l'import demandent maintenant une sortie explicite :

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/check_camera_influence.py --output outputs/focused_truck/camera_influence_rerun.json
.\.venv\Scripts\python.exe scripts/diagnostics/explain_points.py --output outputs/focused_truck/inspection_rerun
```

Ils nécessitent les résultats locaux antérieurs indiqués par `--help` ; ce sont des contrôles après observation, pas des évaluations de mobilité.

Exécuter depuis la racine du projet. Sous PowerShell, aucun besoin d'activer un script d'environnement si l'interpréteur est appelé explicitement.

## Lecture accélérée M02 — exécutée le 4 octobre 2026

```powershell
.\.venv\Scripts\python.exe scripts/run_motion_baseline.py --reader indexed --output outputs/motion/M02_replay_rerun
.\.venv\Scripts\python.exe scripts/benchmark_motion_reader.py --output outputs/motion/M02_comparison_rerun
```

Les résultats déjà obtenus sont sous `outputs/motion/M02/` et `outputs/motion/M02_replay/`. Choisir des dossiers neufs ; M01 et ses sources archivées restent préservés. 39 tests passent ; 1 496 paires de fenêtres comparées exactement. [Protocole](26_M02_INDEXED_READER.md).

## Activité rapide M01 — exécutée le 4 octobre 2026

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/run_motion_baseline.py --output outputs/motion/M01_rerun
```

33 tests passent. La première expérience est conservée sous `outputs/motion/M01/` ; choisir un nouveau dossier pour reproduire, le script refuse tout dossier préexistant. Il lit seulement les événements gauches de deux séquences autorisées et ne lance pas YOLO. Rapports, grilles, exemples et rejeux GIF : [guide M01](25_M01_RAPID_ACTIVITY.md).

## Import des résultats Y01 — exécuté le 4 octobre 2026

```powershell
python scripts/import_y01_results.py "C:/Users/moali/Downloads/Compressed/Y01_20261003T191753Z-20261003T195558Z-1-001.zip" "C:/Users/moali/Downloads/Compressed/Y01_20261003T191753Z-20261003T195558Z-1-002.zip"
```

Import sélectif : rapports, figures, poids initiaux et best/last ; autres snapshots conservés dans les ZIP. Aucun entraînement et aucune inférence ne sont lancés. Le rapport est `outputs/reports/Y01_colab_audit.json`. [Résultats et interprétation](24_Y01_COLAB_RESULTS.md).

## Installation CPU

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

La création et l'installation ont réussi avec accès réseau et écriture temporaire autorisés. Pour reconstruire les versions exactes du poste audité avec Python 3.14.6 / Windows x64 :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-inspection-lock.txt
```

Le verrouillage Windows ne garantit pas la disponibilité des mêmes wheels dans un ancien environnement de recherche ou dans Colab.

## Échantillon officiel

```powershell
python scripts/download_sample.py
python scripts/download_sample.py --events --disparity --labels
```

La première commande ne récupère que métadonnées/calibration. La deuxième ajoute les flux, GT et labels : environ 512 Mio d'archives mesurés pour ce premier échantillon, plus extraction. Les téléchargements déjà connus sont vérifiés par SHA256 et réutilisés. Une coupure conserve `.part` pour reprise.

## Tests puis inspection réelle

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/inspect_sample.py --full-timestamp-audit
.\.venv\Scripts\python.exe scripts/inventory_labels.py
```

Le contrôle complet des temps est activé par cette option. Pour explorer une autre durée avec les mêmes données :

```powershell
.\.venv\Scripts\python.exe scripts/inspect_sample.py --window-us 20000
```

Cette dernière forme est supportée, mais n'a pas été exécutée lors de la validation initiale ; elle remplacera les fichiers de `outputs/inspection`. Sans audit complet, le JSON indique que l'ordre global n'a pas été revérifié.

## Lire les résultats

```powershell
Get-Content -Raw outputs/inspection/inspection.json
Get-Content -Raw docs/19_PROGRESS.md
```

Aucune commande `train.py`, `evaluate.py` ou `demo.py` n'est annoncée : ces scripts n'existent pas encore. Les commandes GPU seront ajoutées après leur exécution effective.

## Pilote avec piétons et expérience S01

```powershell
python scripts/download_sample.py --sequence zurich_city_04_b --events --disparity
python scripts/download_sample.py --sequence thun_00_a --events --disparity
.\.venv\Scripts\python.exe scripts/run_stereo_baseline.py --full-timestamp-audit
```

Ces commandes ont été exécutées. Les labels communs sont ceux acquis avec `--labels` pour le premier échantillon. L'expérience a été conservée sous `outputs/stereo/S01` ; le script refusera désormais de l'écraser. Pour une répétition, choisir un nom neuf :

```powershell
.\.venv\Scripts\python.exe scripts/run_stereo_baseline.py --full-timestamp-audit --output outputs/stereo/S01_rerun
Get-Content -Raw outputs/reports/S01_summary.json
Get-Content outputs/reports/S01_metrics.csv
```

Par défaut, 20 dates par séquence, 50 000 µs par fenêtre, partitions dans `configs/pilot.json`. `--frames`, `--window-us`, `--manifest` et `--output` sont explicites. Le script ne lit jamais les entrées `test_reserved`. Modifier la fenêtre recalcule le normaliseur sur train et crée une expérience différente ; ne pas confondre ses scores avec S01. Sans `--full-timestamp-audit`, le rapport signale que seul l'ordre des tranches a été contrôlé.

## Export YOLO et notebook préparé

```powershell
.\.venv\Scripts\python.exe scripts/export_yolo_pilot.py
.\.venv\Scripts\python.exe scripts/verify_yolo_export.py data/processed/dsec_yolo_pilot_v1
.\.venv\Scripts\python.exe scripts/build_yolo_notebook.py
```

L'export et la génération ont été exécutés. L'exporteur refuse désormais le dossier existant pour préserver les preuves ; pour une nouvelle version, fournir `--output data/processed/NOUVELLE_VERSION`. Le générateur régénère le notebook à partir du rapport Y00 courant ; modifier sa source dans `scripts/build_yolo_notebook.py` pour conserver une correction. Le vérificateur peut être relancé sans régénérer les images.

Pour reproduire Y01, transférer `data/processed/dsec_yolo_pilot_v1.zip` (151,26 Mio) et importer `notebooks/Y01_yolo11n_events_pilot.ipynb` dans Colab. Choisir un GPU et suivre le [guide](22_YOLO_EXPORT_COLAB.md). L'utilisateur a déjà exécuté le protocole avec correction du diagnostic ; les archives attestent les contrôles des tenseurs et l'entraînement. Une reproduction doit écrire dans une nouvelle session. Y02 a été entraîné le 15 octobre ; son utilisation explicite et ses limites sont décrites dans [la page active](20_NEXT_STEPS.md#y02--personne-voiture-camion).

## Mettre à jour les copies Markdown

```powershell
python scripts/sync_markdowns.py
```

À exécuter après chaque modification de la documentation. Tous les `.md` du projet sont copiés dans `markdowns/` en conservant leurs chemins relatifs ; les environnements virtuels, dépendances et caches sont exclus. Chaque copie est vérifiée par SHA256. Aucun original n'est déplacé ni supprimé. Les liens vers des fichiers non Markdown restent destinés à être utilisés depuis les documents sources.

## M03 : diagnostic global et évaluation des annotations

```powershell
.\.venv\Scripts\python.exe scripts/run_global_motion.py --output outputs/motion/M03_rerun
.\.venv\Scripts\python.exe -m http.server 8768 --bind 127.0.0.1 --directory outputs/motion/M03
```

Le dossier M03 contient déjà les six clips exécutés. Pour annoter, ouvrir `http://127.0.0.1:8768/annotate.html` pendant que le serveur tourne, ou ouvrir le fichier HTML local avec ses fichiers voisins. Exporter puis relire les annotations ; adapter le chemin du JSON téléchargé :

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_motion_annotations.py --run outputs/motion/M03 --annotations outputs/motion/M03/M03_manual_annotations.json --output outputs/motion/M03/evaluation_v1.json
```

Les sorties existantes ne sont pas écrasées. Une annotation incertaine, déjà en mouvement ou non relue est exclue des métriques. [Protocole, limites et interprétation](27_M03_GLOBAL_MOTION.md).

## M04 : contrôles artificiels et inventaire d'annotations

```powershell
.\.venv\Scripts\python.exe scripts/run_motion_controls.py --output outputs/motion/M04_controls_rerun
.\.venv\Scripts\python.exe scripts/check_motion_annotations.py --annotations outputs/motion/M03/M03_manual_annotations.json --output outputs/motion/M03/annotation_inventory_v1.json
```

Le second script attend le JSON exporté de l'annotateur ; adapter son chemin. Sans `--annotations`, il produit explicitement un inventaire vide en attente, jamais des négatifs implicites. Chaque sortie doit être neuve. [Protocole](29_M04_MOTION_PROTOCOL.md).

## M05 : comparaison des variantes d'activité

```powershell
.\.venv\Scripts\python.exe scripts/run_adaptive_activity.py --output outputs/motion/M05_rerun
```

Paramètres fixés dans `configs/m05_adaptive_activity.json`. Le script refuse un dossier existant, traite 306 contrôles puis les trois clips train autorisés de `04_b`. Aucun accès aux flux de validation/test. Les comparaisons PNG/GIF sont sous `outputs/motion/M05/train/`. [Méthodes et limites](31_M05_ADAPTIVE_ACTIVITY.md).


## M06 — Comparaison des alertes à 10/20 ms

```powershell
# Le premier contrôle sans annotations existe déjà dans outputs/motion/M06.
# Utiliser un nouveau dossier : toute sortie existante est refusée.
.\.venv\Scripts\python.exe scripts/compare_motion_annotations.py --output outputs/motion/M06_check_02
# Après export manuel réel (adapter le chemin) :
.\.venv\Scripts\python.exe scripts/compare_motion_annotations.py --annotations "C:\Users\moali\Downloads\M06_manual_annotations.json" --output outputs/motion/M06_reviewed_01
```

[Annotateur et protocole M06](34_M06_TEMPORAL_EVALUATION.md). Sans annotations relues, le statut reste PENDING_ANNOTATIONS et aucun score de qualité n’est calculé.


## M07 — Rejeu cadencé sur segments de 12 secondes

```powershell
# Huit cas, environ 96 secondes de données rejouées plus les retards.
# Choisir une nouvelle sortie ; M07_12s contient déjà l’expérience terminée.
.\.venv\Scripts\python.exe scripts/benchmark_paced_motion.py --output outputs/motion/M07_repeat_02
```

Protocole dans `configs/m07_paced_replay.json`, train seulement, pas de fenêtre sautée. [Mesures et explications](35_M07_PACED_REPLAY.md).


## M08 — Profilage et lecteur avec cache

```powershell
# Les sorties M08_profile et M08 existent ; utiliser des noms neufs.
.\.venv\Scripts\python.exe scripts/profile_motion_cost.py --output outputs/motion/M08_profile_repeat
.\.venv\Scripts\python.exe scripts/benchmark_cached_motion.py --output outputs/motion/M08_repeat
```

La seconde commande exige une équivalence exacte avant les rejeux cadencés. Elle utilise les deux segments train de M07 ; aucun téléchargement ni entraînement. [Protocole M08](36_M08_CACHED_READER.md).


## M09 — Comparer le calcul d’activité

```powershell
# Campagne complète existante : outputs/motion/M09_20261007.
# M09 contient une ancienne campagne partielle ; choisir une sortie neuve.
.\.venv\Scripts\python.exe scripts/benchmark_lookup_activity.py --output outputs/motion/M09_repeat
```

Les deux variantes utilisent le lecteur M08. L’équivalence exacte de chaque sortie et de l’état précède les huit rejeux cadencés. [Guide M09](37_M09_LOOKUP_ACTIVITY.md).


## M10 — Candidats cohérents et persistants

```powershell
# Sortie M10 existante à conserver ; le script refuse de l'écraser.
.\.venv\Scripts\python.exe scripts/run_mobile_candidates.py --output outputs/motion/M10_repeat
```

Sept contrôles idéaux puis trois extraits train du manifeste M03 ; sorties JSON et comparaison PNG/GIF. Aucun entraînement ni téléchargement. La comparaison exacte des sorties brutes M03 est obligatoire. [Résultats et limites](39_M10_MOBILE_CANDIDATES.md).


## M11 — Compensation rigide sur contrôles 3D

```powershell
.\.venv\Scripts\python.exe scripts/run_rigid_controls.py --output outputs/motion/M11_repeat
```

Le dossier de sortie doit être neuf. Ne télécharge rien et ne lit aucun événement réel : 135 paires contrôlées, profondeurs synthétiques explicitement oracle, comparaison par point avec M03. [Contrats et résultats](40_M11_RIGID_MOTION.md).


## M12 — Modèle rigide sur événements train et profondeur S01

```powershell
# Préserver M12 ; choisir un nouveau dossier.
.\.venv\Scripts\python.exe scripts/run_real_rigid_motion.py --output outputs/motion/M12_repeat
```

Lit les événements gauches des deux séquences train et les cartes S01 inventoriées par M11. Recalcule les images rectifiées et le suivi ; ne recalcule pas la stéréo, ne charge aucune GT ni poids YOLO. Les paires incomplètes sont rapportées. [Protocole, fichiers et limites](41_M12_REAL_RIGID_MOTION.md).


## M13 — Clips sans prédictions et relecture

```powershell
.\.venv\Scripts\python.exe scripts/prepare_temporal_review.py --output outputs/motion/M13_repeat
node --check scripts/motion_review.js
# Après relecture et export depuis outputs/motion/M13/review.html :
.\.venv\Scripts\python.exe scripts/check_motion_review.py "C:\chemin\M13_manual_review.json"
```

Pour une autre campagne, passer `--manifest outputs/motion/M13_repeat/review_manifest.json` au validateur. Le paquet initial M13 existe déjà. Le JSON vide retourne PENDING_REVIEW ; le validateur ne calcule aucune métrique et ne certifie pas la vérité des annotations. [Mode d'emploi](42_M13_TEMPORAL_REVIEW.md).
