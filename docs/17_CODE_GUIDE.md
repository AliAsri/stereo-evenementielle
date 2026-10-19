# Guide du code réellement présent

## Point d’entrée actuel — 15 octobre 2026

| Rôle | Code maintenu |
|---|---|
| Commande principale, mesures, GIF/JSON | `scripts/run_integrated_demo.py` |
| Lecture et représentations | `dsec_cached.py`, `dsec_indexed.py`, `representations.py` |
| Calibration, disparité et reprojection | `geometry.py`, `stereo.py` |
| Suivi, historique exact et modèle rigide | `clip_motion.py`, `rectified_tracking.py`, `rigid_motion.py` |
| Association des boîtes aux surfaces et aux points | `object_surface.py` |
| Conversion des classes et préparation Colab | `detection.py`, `scripts/export_yolo_pilot.py`, `scripts/build_yolo_notebook.py` |

Les modules sont sous `src/pfe_events/`. L’estimation de surface n’affirme pas un centre d’objet ; le résidu n’affirme pas un mouvement propre. [État du parcours](20_NEXT_STEPS.md), [contrôles et corrections](44_PROJECT_MAINTENANCE.md). Les descriptions datées ci-dessous documentent aussi les outils historiques.

**Organisation actuelle au 8 octobre 2026 :** voir la [carte des modules et utilitaires R01](44_PROJECT_MAINTENANCE.md). Les sections ci-dessous détaillent les algorithmes ; les fonctions partagées des lanceurs ont été extraites sans modification des seuils ou des résultats scientifiques.

## Lecture indexée — `src/pfe_events/dsec_indexed.py`

`IndexedDSECReader` conserve l'interface context manager et `window(start_us,end_us,max_events)` du lecteur de référence. `__enter__` charge et contrôle `ms_to_idx` ; `_boundary` vérifie les timestamps adjacents à chaque borne utilisée, puis mémorise la vérification. `window` retire l'offset, encadre par millisecondes, lit les timestamps contigus et affine les limites par `searchsorted` à gauche. Il lit ensuite exactement les x/y/p retenus et rétablit les timestamps absolus. Le budget porte sur la fenêtre exacte ; la recherche binaire sert de repli hors couverture ou si l'encadrement excède le budget. Les incohérences d'index sont des erreurs explicites.

L'index conservé occupe environ 93–105 Kio sur les deux fichiers testés ; cela ne mesure pas la mémoire totale du processus ni les buffers HDF5. Aucun ensemble complet de timestamps n'est chargé. Les blocs HDF5 peuvent contenir des dates voisines, mais seuls les événements de la fenêtre entrent dans l'activité. `tests/test_dsec_indexed.py` couvre six groupes de cas contre un masque temporel indépendant.

## Comparaison des lecteurs — `scripts/benchmark_motion_reader.py`

`compare_case` reprend les segments M01, instancie deux détecteurs indépendants et alterne les lectures sur deux passages. Les temps excluent la comparaison d'égalité des événements/cartes/régions et les hashes. Chaque résultat est aussi confronté aux artefacts M01. `main` refuse tout dossier existant, contrôle que les sources correspondent aux séquences autorisées, archive les sources et sauvegarde les métriques et erreurs éventuelles. Le lecteur indexé est également disponible dans le rejeu par `--reader indexed` ; la référence reste le défaut. [Résultats M02 et commande](26_M02_INDEXED_READER.md).

## Activité rapide — `src/pfe_events/motion.py`

`ActivityConfig` conserve géométrie, taille de cellule, taux minimal en événements/(seconde·pixel), nombre de pixels actifs, persistance et support des régions. `ActivityDetector` valide ces paramètres et prépare l'aire réelle de chaque cellule et un compteur temporel. Dépendances : NumPy et OpenCV CPU, sans torch, modèle ni labels. Les seuils sont des valeurs d'ingénierie non calibrées.

`update(events, start_us, end_us)` accepte `x`, `y`, `t_us` entiers, ordonnés et contenus dans la fenêtre demi-ouverte ; les polarités ne servent pas à cette activité agrégée. L'appel doit suivre immédiatement la fenêtre précédente. Comptage natif par `bincount`, agrégation sur grille, comptage des pixels distincts, division par aire×durée, seuil et persistance, puis composantes connexes 8-voisins. Une cellule inactive réinitialise sa persistance. Retour : cartes de taux/candidats/activité retenue, pixels occupés, régions natives `xyxy` à borne supérieure exclusive et timestamp final, fraction active et indicateur d'activité étendue. Les régions n'ont pas de classe d'objet. `parameters()` expose la configuration sérialisable.

Le rejet d'un pixel isolé protège contre un cas de bruit ; il n'est pas un filtre universel. L'indicateur d'activité étendue ne compense pas le mouvement de caméra. Changer la taille des cellules ou la persistance peut supprimer les petits objets et retarder la réponse : versionner les réglages et mesurer cet effet.

## Expérience — `scripts/run_motion_baseline.py`

`run_case` sélectionne un segment centré sans lire les labels, crée un détecteur par fenêtre testée et consomme les événements du lecteur de référence. Mesure séparément lecture et activité par `perf_counter_ns`. `distribution` calcule nombre, moyenne, médiane, p95 et maximum. Une simulation de file d'attente suit `fin=max(fin_précédente, arrivée_fin_fenêtre)+coût` ; elle ne remplace pas une mesure en direct. Rendu, hashes et écritures restent hors chronométrage.

`panel` produit une vue des pixels actifs et une grille à échelle fixe, avec rectangles d'activité. Le GIF conserve une image toutes les 50 ms de temps dataset ; son affichage 20 Hz est distinct du calcul à fenêtres 10 ms. `main` refuse un dossier existant, vérifie les partitions, fixe un thread OpenCV et conserve statut d'échec si nécessaire. Sorties : CSV par fenêtre, NPZ taux/masques, JSON de paramètres/métriques/provenance, PNG et GIF. Les champs sans GT de mouvement valent `null`, jamais une précision inventée.

`tests/test_motion.py` vérifie six cas analytiques : persistance/début synthétique, pixel isolé, causalité/continuité, taux et aire au bord, activité étendue et entrées invalides. Les tests ne valident pas la segmentation de mouvement DSEC. [Résultats et limites](25_M01_RAPID_ACTIVITY.md).

## Import des archives Colab — `scripts/import_y01_results.py`

Importeur utilisant la bibliothèque standard : session Y01 historique par défaut ; session Y01/Y02 datée sélectionnée avec `--run`, export local sélectionné avec `--dataset`. Entrées : chemins des ZIP fournis, sans modifier les archives. `sha256(path)` calcule l'empreinte en flux ; `main()` inventorie chaque archive, vérifie les chemins et doublons, extrait métadonnées/figures et poids best/last/initiaux, puis contrôle leur CRC et SHA256. Les checkpoints intermédiaires restent dans les ZIP. Un fichier local différent n'est pas écrasé ; un second import identique est accepté.

Sorties : `outputs/colab/<session>/` et `outputs/reports/Y01_colab_audit.json` ou `Y02_colab_audit.json`. Le dossier de rapports est créé si nécessaire. Le rapport inclut les métriques originales, les comparaisons de provenance (neuf pour Y01 avec reprise, huit pour Y02) et les époques portant les meilleurs scores CSV. `PASS` indique la cohérence des fichiers contrôlés, pas une évaluation du modèle. Les fichiers `.pt` ne sont pas chargés par PyTorch. Pour une autre session, adapter explicitement l'identifiant et les contrats des rapports ; ce n'est pas un importeur universel. Deux exécutions sur les ZIP réels ont vérifié l'import et sa répétabilité sans écrasement de fichiers différents. [Analyse](24_Y01_COLAB_RESULTS.md).

## Copie de la documentation — `scripts/sync_markdowns.py`

Parcourt le projet sans suivre les liens de dossiers, exclut `markdowns/`, les dépendances, environnements virtuels et caches, puis copie chaque `.md` sous le même chemin relatif dans `markdowns/`. `digest(path)` calcule le SHA256 ; `main()` réalise et vérifie les copies. La bibliothèque standard suffit. Exécuter `python scripts/sync_markdowns.py` après toute modification Markdown. Le script actualise les copies existantes sans supprimer d'originaux ni d'anciennes copies. Modifier les sources, jamais le miroir directement.

État initial : outils CPU d'inspection, pas de modèle DL intégré. Les composants proposés dans 05_PROJECT_ARCHITECTURE sont créés au fil des validations.

## `scripts/download_sample.py`

Rôle : télécharger une séquence officielle bornée et permettre la reprise. `--sequence` accepte `zurich_city_04_e` (défaut historique), `zurich_city_04_b` ou `thun_00_a`, dont les tailles et modalités ont été vérifiées. URL officielle explicite ; aucune collecte complète implicite. Sans option : calibration et timestamps. Options `--events`, `--disparity`, `--labels` ajoutent les modalités correspondantes. Les partitions sont conservées séparément dans `configs/pilot.json`.

- `sha256(path)` : lit le fichier par flux et renvoie son empreinte locale ; dépend seulement de hashlib.
- `download(url,destination)` : fichier temporaire `.part`, en-tête Range pour reprendre, contrôle de la réponse et de taille, renommage après transfert complet ; retourne URL/octets/hash. Si le serveur ignore Range et renvoie 200, le partiel est repris depuis zéro. Aucun original final n'est écrasé. Budget 600 Mio/fichier.
- `extract_checked(archive,destination)` : contrôle les chemins contenus, le volume annoncé extrait et les fichiers déjà présents ; extraction avec validation CRC du module zipfile. Une différence avec un fichier existant arrête l'opération.
- `main()` : compose les ressources, vérifie les téléchargements déjà présents, retente au plus trois erreurs réseau identifiées, écrit `downloads.json`. L'archive des labels contient elle-même des ZIP : le train est extrait, le test reste empaqueté.

Modifier de séquence demande de vérifier URL, taille et présence des modalités ; l'outil actuel n'est pas un gestionnaire général de datasets. Une interruption pendant l'extraction peut laisser un fichier partiel qui sera refusé au prochain passage : le diagnostiquer explicitement avant retrait ciblé, ne pas supprimer tout `data/`.

## `src/pfe_events/dsec.py`

`DSECReader(path,width,height)` gère un HDF5 en lecture seule avec `with`. `__enter__` vérifie schéma, dimensions, types et temps extrêmes ; ferme puis relance l'erreur en cas d'échec. `__exit__` ferme le flux. L'import de hdf5plugin enregistre les filtres nécessaires.

`_lower_bound(local_us)` effectue une recherche binaire, O(log N) lectures scalaires, pour trouver le premier temps >= la borne. C'est un lecteur de référence simple, non une optimisation maximale des E/S.

`window(start_us,end_us,max_events=2_000_000)` reçoit des microsecondes **absolues** entières, retire l'offset uniquement pour la recherche, lit la tranche puis restitue `x,y,p,t_us`. La borne droite est exclue ; les événements simultanés restent ensemble. Une fenêtre vide est normale. Une fenêtre trop grande lève MemoryError, sans sous-échantillonnage caché. Les coordonnées et polarités sont vérifiées dans la tranche.

`audit_timestamps(chunk_size=1_000_000)` parcourt tous les timestamps par blocs et vérifie aussi la jonction entre blocs. Il ne vérifie pas tous les x/y/p de toute la séquence ; ne pas étendre sa garantie au-delà du temps.

`load_rectify_map(path,width,height)` charge une carte et contrôle sa forme. `rectify_events(events,mapping,width,height)` applique le mapping direct, arrondit pour l'affichage, rejette NaN et points hors champ, retourne un dictionnaire et le nombre rejeté. L'entrée doit déjà être validée par le lecteur. Une interpolation apprise ou bilinéaire future doit avoir un autre nom et ses tests ; ne pas changer silencieusement ce comportement.

## `src/pfe_events/representations.py`

`polarity_counts(events,width,height)` retourne `[2,H,W]` uint32 : négatif puis positif. `np.add.at` additionne correctement les événements répétés au même pixel ; une affectation vectorisée naïve n'aurait pas cette garantie. Vérifie types, dimensions et bornes. Le budget du lecteur protège le comptage contre des volumes extrêmes.

`render_counts(counts)` retourne une image uint8 RGB pour l'humain : fond blanc, négatif bleu, positif rouge, les deux violet. Les valeurs de comptage ne sont pas encodées en intensité. Ce rendu est distinct de l'encodage logarithmique maintenant implémenté.

`rectified_counts(events,mapping,width,height)` valide les entrées, applique le mapping direct et distribue chaque événement entre quatre voisins. Les centres hors image/non finis sont rejetés ; les poids nuls aux bords sont ignorés avant indexation. Retourne comptes `[2,H,W]` float32 et nombre de rejets. La conservation est contrôlée avant conversion finale depuis l'accumulateur float64. L'implémentation est une référence lisible, non optimisée.

`log_channels(counts)` vérifie des comptes finis non négatifs et renvoie HWC float32, canaux positif/négatif/total en `log1p`. `fit_log_normalizer(count_frames,source_split=...)` refuse tout split autre que train, prélève au plus 10 000 valeurs positives par canal/image, calcule un percentile et rend un dictionnaire sérialisable. Le générateur appelant et le manifeste déterminent réellement la provenance : le mot « train » seul ne garantit pas l'absence de fuite. `normalized_event_image` applique les mêmes trois échelles aux vues et produit uint8, sans réajustement par image.

## `src/pfe_events/geometry.py`

`audit_calibration(path)` charge le YAML, compose `T_32 @ T_21 @ T_10`, contrôle rotations et transformations homogènes, compare baseline géométrique à celle de Q, expose intrinsics rectifiés, Q et dimensions. Ce contrôle attend la convention DSEC ; un autre dataset exige un adaptateur explicite.

`decode_dsec_disparity(encoded)` reçoit une image entière 2D compatible 16 bits, renvoie disparité float64 en pixels et masque ; zéro devient NaN. Accepte aussi un décodage PNG en int32 dans la plage valide, pour compatibilité Pillow.

`reproject_q(u,v,disparity,q)` accepte scalaires ou tableaux broadcastables ; applique la projection homogène et retourne `[...,3]`. Division singulière, valeurs non finies ou Z<=0 donnent NaN. Le code ne masque pas une exception ; il encode une invalidité géométrique attendue. Il ne suppose pas que `cx_left=cx_right`. Il ne prédit aucune disparité.

## `scripts/inspect_sample.py`

`unique_file(folder,pattern)` exige un seul fichier : absence et ambiguïté sont des erreurs. `inspect(folder,output,window_us,full_audit)` valide calibration et références, choisit une date GT au milieu de l'intersection temporelle, extrait la même fenêtre à gauche/droite, contrôle conservation des événements, génère vues natives/rectifiées et rapport JSON. La sélection des labels utilise le chemin **relatif à la racine labels**, afin de ne pas confondre le nom du dossier parent de l'échantillon avec celui d'une séquence annotée.

Les PNG de disparité GT sont triés et associés aux timestamps ordonnés après vérification du nombre. Cette convention est validée sur l'archive choisie ; pour un dataset incomplet, un manifeste explicite nom↔temps devra remplacer l'hypothèse de collection complète.

Le script montre les boîtes **officielles au timestamp exact**, sans inférence YOLO. Les statistiques de profondeur proviennent de la GT et sont nommées en conséquence. Une mesure ponctuelle de lecture est conservée, sans la convertir en FPS pipeline.

Sorties : `outputs/inspection/inspection.json`, `inspection.png`, quatre vues événementielles et `left_official_labels.png`. Options : `--window-us`, `--full-timestamp-audit`. Une nouvelle exécution remplace ces sorties d'inspection ; copier un dossier d'exécution pour un registre durable.

## `tests/test_core.py`

Treize tests déterministes sur petites données **synthétiques** : offsets et duplicats temporels, bornes, fenêtre vide, budget mémoire, schéma, ordre global, comptage, rectification hors champ, décodage GT, projection connue et Q avec point principal décalé. Les fichiers HDF5 sont réellement compressés Blosc/ZSTD. Les temporaires sont confinés dans `outputs/test-temp` puis nettoyés.

Ils ne prouvent ni précision de YOLO ni qualité d'une stéréo. Les assertions analytiques ont pour but d'éviter des erreurs silencieuses d'unité et d'index avant les futurs modèles.

## `scripts/inventory_labels.py`

Charge les `tracks.npy` officiels avec `allow_pickle=False`, vérifie les champs et identifiants de classe, compte boîtes par classe, dates annotées et IDs de pistes par séquence. Exporte `outputs/reports/label_inventory.json` et affiche les séquences les plus riches en annotations pedestrian. Les comptes sont des **instances temporelles**, pas un dénombrement de personnes distinctes. L'archive nommée train comprend aussi des séquences du split validation de détection : utiliser le manifeste de partition avant entraînement.

## `src/pfe_events/pilot.py`

`load_manifest(path)` charge le JSON, contrôle noms uniques, groupes dérivés du nom DSEC et partitions connues. Un même groupe dans deux partitions déclenche une erreur. `unique_file` exige un seul fichier correspondant au motif. `reference_frames` associe les PNG triés à la liste strictement croissante de timestamps et exige une collection complète. Les numéros des fichiers PNG ne sont pas utilisés comme indices de cette liste.

`sample_indices(timestamps,left,right,window_us,count)` conserve les dates possédant une fenêtre complète dans les deux flux, puis choisit au plus `count` indices régulièrement espacés. Elle ne consulte ni pixels GT ni qualité du matching. Le choix des fenêtres d'évaluation est donc indépendant du score.

## `src/pfe_events/stereo.py`

`StereoConfig` fige les paramètres de la baseline. `decode_sgbm` exige une image int16, divise par 16 et rend invalides les valeurs <=0. Ce comportement est propre à la plage positive choisie ici : une paire avec autre convention de disparité exigerait un adaptateur différent.

`predict_stereo(left,right,config)` reçoit deux images rectifiées uint8 H×W. Crée SGBM, calcule sens direct et inverse par retournement horizontal, puis contrôle activité locale, position de correspondance et accord à 1,5 px. La correspondance de vérification droite est échantillonnée au pixel le plus proche. Retour : disparité float32 avec NaN, masque booléen, sortie brute Q4 et compteurs de support. La fonction n'accepte aucune GT.

`disparity_metrics(prediction,gt)` renvoie compteurs additifs, EPE, RMSE, Bad3, couverture et taux Bad3-ou-absent. Les absents ne participent pas à l'EPE mais restent au dénominateur de couverture. Si aucune correspondance n'est évaluable, les erreurs sont `None`, pas zéro. `aggregate_metrics(rows)` additionne les sommes d'erreurs et effectifs avant division ; elle ne moyenne pas les moyennes de fenêtres.

## `scripts/run_stereo_baseline.py`

`training_frames` parcourt exclusivement les entrées train : quatre dates par séquence, gauche/droite, natif/rectifié. Le normaliseur commun et ses provenances sont sauvegardés avant toute validation. `open_pair` centralise lecteurs/calibration/maps avec fermeture garantie par `ExitStack`.

`evaluate_sequence` sélectionne les dates, audite les temps si demandé, lit les événements, construit les images, prédit la disparité et reprojecte en profondeur. La GT n'est décodée qu'après cette branche ; elle ne corrige aucune prédiction. Les sorties NPZ sont écrites par index GT, avec unité explicite dans chaque clé. Les rapports conservent compteurs d'événements, rejets, labels au temps exact, plage GT et temps par étape.

`make_sheet` distingue événements, GT, prédiction et erreurs. Les deux cartes de disparité partagent une échelle fixe 0–96 px ; le magenta signale une GT sans prédiction. L'exemple central est déterminé par l'ordre temporel ; le cas d'échec selon Bad3-ou-absent ; l'exemple natif annoté selon le nombre maximal de piétons parmi les vingt dates. Ces choix de figures ne modifient pas l'échantillonnage des métriques.

`main` refuse tout dossier de sortie préexistant, vérifie le manifeste, n'ouvre jamais `test_reserved`, fixe un thread OpenCV, ajuste le normaliseur puis exécute les séquences. `summary.json` contient versions et hashes du code. Les JSON n'autorisent pas NaN ; les cartes NPZ, elles, conservent NaN comme invalidité attendue. Si l'exécution échoue, son dossier partiel reste présent et n'est pas transformé en expérience complète.

## `tests/test_stereo.py`

Huit contrôles synthétiques ajoutés aux treize initiaux : masse bilinéaire aux frontières et hors champ, entrée vide, normalisation train-only et canaux, échelle SGBM, plan texturé décalé de huit pixels avec contrôle inverse, images vides, métriques avec prédictions absentes, rejet de fuite entre groupes. Total exécuté : 21 tests, zéro échec. Les assertions sur un plan synthétique ne constituent pas une précision expérimentale sur DSEC.

Une vérification supplémentaire des 60 fichiers S01 a recalculé les métriques depuis les PNG GT et NPZ sauvegardés et contrôlé `Z=fx*B/d` pour ces calibrations canoniques. Son résultat est conservé dans `outputs/reports/S01_verification.json`.

## `src/pfe_events/detection.py`

`CLASS_MAP` fixe les identifiants DSEC 0→YOLO 0 et 2→YOLO 1 ; `CLASS_NAMES` donne person/car. `convert_boxes` vérifie le schéma, distingue classes exclues et géométrie invalide, borne les coins au capteur puis normalise le rectangle restant. Les doublons après arrondi à neuf décimales sont comptés séparément. Retour : tableau N×5, indices des lignes d'entrée conservées et compteurs dont la somme explique chaque exclusion. `labels_to_text` produit le format YOLO, y compris une chaîne vide pour N=0. Aucun accès modèle ni changement de repère n'est réalisé.

## `scripts/export_yolo_pilot.py`

Valide le manifeste et la provenance train-only du normaliseur S01 ; refuse de remplacer un dossier ou ZIP existant. Parcourt les dates officielles de labels avec historique gauche complet, en laissant `test_reserved` fermé. Limite à 1 000 images par séquence pour éviter un export massif implicite. Les images sont calculées directement depuis les événements natifs et écrites avec Pillow en RGB logique positif/négatif/total.

Les labels conservés restent liés aux indices du `tracks.npy`, aux track IDs et aux classes source. Le script crée une liste de huit images train espacées pour surapprentissage, un YAML portable, les previews, la notice et un vérificateur autonome. Il calcule les hashes, vérifie intégralement le dossier, puis seulement produit le ZIP et le rapport `Y00_export.json`. Une erreur laisse un export partiel diagnostiquable, sans écraser la version précédente.

## `scripts/verify_yolo_export.py`

Ce fichier est copié dans le ZIP et fonctionne sans importer le projet. `verify(root)` vérifie chemins contenus, hashes, schéma des images, lecture Pillow/OpenCV, coordonnées et classes, doublons, effectifs, fenêtres, huit images de surapprentissage issues de train, fichiers manquants/surnuméraires et séparation des groupes. Il recherche aussi une image PNG identique entre partitions. Il exige les deux classes dans train et validation. Cette exigence appartient au pilote, pas à une règle universelle pour tous les jeux de détection.

Il ne vérifie pas la qualité sémantique des labels et ne charge pas Ultralytics. Le contrôle source supplémentaire de Y00 a comparé toutes les 4 235 boîtes aux données originales et régénéré neuf images ; le rapport précise la différence entre ces contrôles.

## `scripts/build_yolo_notebook.py` et notebook Y01

Le générateur lit le hash réel du ZIP Y00 et la version Ultralytics auditée, construit 16 cellules et compile leurs sept blocs Python avant écriture. Il laisse `execution_count=null` et les sorties vides : il ne simule aucune exécution distante. Modifier ce générateur puis régénérer pour conserver les changements reproductibles.

Le notebook vérifie GPU/runtime, prépare une session Drive neuve, installe la version Ultralytics figée, vérifie et extrait le ZIP puis lance le vérificateur portable. Il reconstruit les chemins absolus de son YAML, compare six tenseurs du vrai chargeur aux images avec letterbox et à leurs labels, affiche un lot et compte les boîtes filtrées. Les augmentations colorimétriques, Albumentations implicites et géométriques sont neutralisées pour ce premier pilote.

Le petit lot de huit images sert uniquement au diagnostic de surapprentissage. Un garde-fou AP50 par classe empêche de poursuivre si ce diagnostic échoue. Le pilote complet repart du checkpoint initial ; ses métriques sur `thun_00_a` sont séparées des métriques de train. Les erreurs mettent à jour `status.json` puis sont relancées, sans résultat fictif. `args.yaml`, checkpoint hashes et environnement complètent les paramètres demandés. La reprise après déconnexion est documentée dans la dernière cellule Markdown.

## `tests/test_detection.py`

Six tests synthétiques : mapping/rider exclu, rectangle analytique, clipping et centre recalculé, géométrie invalide/hors champ, labels vides et classe inconnue, doublons et précision du round-trip texte (certains cas sont réunis dans un même test). Total du socle : 27 tests réussis. Aucun score de détecteur ne découle de ces tests.

## Branche rapide M01–M03

- `src/pfe_events/motion.py` : activité causale sur grille, support et persistance ; indépendante des classes YOLO.
- `src/pfe_events/dsec_indexed.py` : lecture par index milliseconde avec contrôles des bornes et repli borné ; le lecteur de référence est conservé.
- `scripts/run_motion_baseline.py` et `scripts/benchmark_motion_reader.py` : rejeu, comparaison appariée, mesures et vérification d'équivalence.
- `src/pfe_events/global_motion.py` : image fixe de comptes, suivi aller-retour LK, similarité RANSAC, abstention et régions résiduelles natives. Ce module ne produit pas une pose de caméra ni une segmentation indépendante validée.
- `scripts/run_global_motion.py` : sélection fixe de six clips, mesure séparée des étapes, export de prédictions et préparation des images sans prédictions pour annotation.
- `scripts/motion_annotation.html` : source de l'interface locale ; l'expérience en conserve une copie et un hash. Aucune annotation sauvegardée sur disque avant l'export JSON.
- `src/pfe_events/motion_evaluation.py` : délai intervalle, activité sur ROI négative, couverture et départs censurés ; uniquement annotations éligibles relues. Aucune agrégation de ROI superposées.
- `scripts/evaluate_motion_annotations.py` : CLI de validation des entrées, sortie neuve et SHA-256 de provenance.

Le total actuel est de 53 tests réussis. Les contrôles synthétiques vérifient les contrats ; ils ne mesurent pas la qualité du mouvement sur DSEC. [Description complète M03](27_M03_GLOBAL_MOTION.md).

## Contrôles M04 et contrat d'évaluation

`configs/motion_protocol_v1.json` fixe le périmètre des mesures réelles par ROI et les conditions artificielles avant leur exécution. `src/pfe_events/motion_controls.py` génère des sources d'activité, bruit uniforme, pixel chaud et bouffée globale ; ce n'est pas un simulateur physique d'objets. `scripts/run_motion_controls.py` balaie fenêtres/persistances/seuils, archive les sources et conserve les délais manqués à `null`.

`scripts/check_motion_annotations.py` vérifie la cible, réutilise la validation de l'évaluateur M03, rejette les doublons exacts relus et inventorie les annotations par clip. Les brouillons/incertains restent exclus ; les ROI superposées ne doivent pas être agrégées. Cinq tests supplémentaires vérifient les contrôles, trois vérifient l'inventaire. Total actuel : 61 tests. [Protocole et limites](29_M04_MOTION_PROTOCOL.md).

## Activité adaptative M05

`src/pfe_events/adaptive_activity.py` ajoute un calcul d'excès par rapport à la médiane/MAD de la fenêtre, puis un historique exponentiel optionnel. Le seuil utilise l'état passé ; l'actualisation suit la décision. Préchauffage explicite de 200 ms et persistance propre. Le wrapper réutilise les taux/supports du détecteur M01 sans modifier sa source ; son coût inclut ce calcul interne.

`scripts/run_adaptive_activity.py` compare les trois variantes sur des signaux identiques, puis sur trois clips train avec ordre d'appel tournant, lecture partagée et export des régions/temps. Il rapporte aussi la durée de signalement de la source : l'historique peut supprimer une activité persistante. `tests/test_adaptive_activity.py` ajoute six tests ; total actuel 67. [Rapport M05](31_M05_ADAPTIVE_ACTIVITY.md).


## M06 — Cadences et maintien du signalement

`src/pfe_events/multirate_evaluation.py` valide les grilles originales et natives, puis appelle l’évaluateur v1 avec les dates de prédiction sans changer l’intervalle annoté. Il ajoute un diagnostic de maintien uniquement sur une durée explicitement relue. `scripts/compare_motion_annotations.py` adapte les archives M05/M03, restreint la comparaison aux clips train communs, conserve les indices du fichier d’annotations et archive sources/hashes. `scripts/motion_annotation_v2.html` ajoute l’intervalle continu facultatif en conservant les exports v1.

[Entrées, sorties, algorithme, commandes, tests et pièges](34_M06_TEMPORAL_EVALUATION.md). Ne pas réduire les sorties 10 ms à 20 ms ni inventer une durée continue ; ne pas assimiler une abstention à une absence d’alerte.


## M07 — Ordonnancement et âge des sorties

`src/pfe_events/replay_timing.py` : `paced_windows` attend la disponibilité de chaque fenêtre, lit les événements, calcule l’activité et mesure service, attente et âge de sortie. Horloge injectable pour six tests déterministes, horloge monotone réelle pour DSEC. Les fenêtres en retard restent traitées dans l’ordre.

`scripts/benchmark_paced_motion.py` : initialise les clips train et l’échauffement, inverse l’ordre à la seconde répétition, sauvegarde les traces hors boucle et résume les coûts par blocs. Le détecteur et le lecteur de référence restent inchangés. [Contrats, métriques et commandes](35_M07_PACED_REPLAY.md).


## M08 — Lecture indexée avec handles persistants

`src/pfe_events/dsec_cached.py` fournit `CachedIndexedDSECReader`, avec la même API que `IndexedDSECReader`. Il conserve les quatre datasets du contexte ouvert ; la recherche de bornes, les contrôles et le découpage sont hérités. La fermeture invalide tous les handles. Exemple d’intégration future :

```python
from pfe_events.dsec_cached import CachedIndexedDSECReader

with CachedIndexedDSECReader(events_path) as reader:
    events = reader.window(start_us, end_us)
```

Les bornes et le chemin doivent venir du manifeste réel. Ne pas utiliser le lecteur après fermeture du contexte. `scripts/profile_motion_cost.py` archive le profil original ; `scripts/benchmark_cached_motion.py` compare chaque champ et mesure ensuite les passages cadencés. [Explications détaillées et limites](36_M08_CACHED_READER.md).


## M09 — Détecteur avec table pixel→cellule

`src/pfe_events/motion_lookup.py` fournit `LookupActivityDetector`, sous-classe d’`ActivityDetector` avec table géométrique préconstruite. L’API `update(events, start_us, end_us)` et le format de sortie restent identiques. Le tableau est immuable et les entrées ne sont pas modifiées. Le corps de calcul est conservé séparément pour comparer directement à M01 ; maintenir les validations cohérentes entre les deux classes.

`scripts/benchmark_lookup_activity.py` compare cartes, propositions et état de persistance, avec entrées partagées en lecture seule et ordre alterné, puis mesure le rejeu autonome. Cinq nouveaux tests couvrent géométries/types variés, bords, persistance, erreurs et absence de modification des tableaux. [Détails et mesures M09](37_M09_LOOKUP_ACTIVITY.md).


## M10 — Candidats de mouvement apparent

`mobile_candidates.py` sépare le filtre `ResidualCandidateTracker` (paires de points en coordonnées de travail et date entière) de l'adaptateur `ImageCandidateDetector` (image uint8 320×240 et date). Les dates doivent être contiguës au pas configuré de 20 ms. Les sorties `regions` sont persistantes, `tentative_regions` provisoires ; `rejections` conserve les raisons. `valid` concerne le modèle apparent, pas une confirmation de mobilité. En cas de modèle invalide, la persistance est réinitialisée.

`mobile_controls.py` génère les sept contrôles idéaux, dont deux échecs connus. `run_mobile_candidates.py` préserve M03, vérifie l'équivalence de son résultat brut, archive les paramètres/sources et rend les trois clips train. Les identifiants de candidats ne garantissent pas une identité d'objet. [Détails et limites M10](39_M10_MOBILE_CANDIDATES.md).


## M11 — Géométrie et provenance de profondeur

`rigid_motion.py` expose `estimate_rigid_motion(previous, current, depth_m, intrinsic, ...)`, sans état temporel caché. Points en pixels rectifiés, profondeurs axiales en mètres au premier instant, K rectifiée. Les dates, la provenance de profondeur et les dimensions sont vérifiées avant estimation ; les profondeurs manquantes restent inconnues. Le modèle dominant produit une transformation caméra précédente→caméra courante, et non une pose monde certifiée.

`rigid_controls.py` génère les paires 3D et conserve la pose/les labels de référence uniquement pour l'évaluation. `run_rigid_controls.py` archive chaque scène NPZ et résultat JSON, les paramètres et les sources ; il compare les résidus par point à M03. Il n'exécute pas le suivi événementiel ni le filtre de persistance M10. [API et limitations](40_M11_RIGID_MOTION.md).


## M12 — Adaptation aux images rectifiées réelles

`rectified_tracking.py` fournit `checked_tracks` (images uint8, LK avec contrôle aller-retour) et `sample_masked_depth` (échantillonnage au plus proche pixel rectifié, masque booléen, pas de remplissage ni de support dupliqué). Les points sans profondeur restent NaN en entrée du modèle et UNKNOWN en sortie.

`run_real_rigid_motion.py` reconstruit les deux fenêtres causales avec le splat S01 et le normaliseur train figé ; il vérifie les cartes prédites, Q et leurs dates avant le modèle M11. Les archives NPZ conservent les images/points/profondeurs pour le contrôle ; les JSON séparent les sorties rigides et de similarité sur les mêmes points. La profondeur précalculée exclut toute revendication de latence bout en bout. [Guide M12](41_M12_REAL_RIGID_MOTION.md).


## M13 — Relecture et comparaison temporelle

`prepare_temporal_review.py` génère les clips rectifiés sans prédictions et les quatre conditions temporelles aux dates fixées ; chaque cas 50/20 doit reproduire exactement l'archive M12. La profondeur reste celle de S01 à la date initiale. Les clips et les sorties comparatives sont séparés : les résultats ne sont jamais injectés dans `review_data.js`.

`motion_review.html` / `.js` dessinent la ROI, sélectionnent un intervalle d'images et exportent un état moving/static/unknown avec auteur, indices et relecture explicite. `motion_review.py` vérifie le schéma, le manifeste, le repère et les intervalles ; `check_motion_review.py` fournit la commande de contrôle. Ce format n'est pas directement celui des métriques M06 et aucune conversion implicite n'est faite. [Guide M13](42_M13_TEMPORAL_REVIEW.md).
