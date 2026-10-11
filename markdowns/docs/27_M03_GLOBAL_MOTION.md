# M03 — Mouvement apparent global et préparation de l'évaluation

Date : 4 octobre 2026. **Prototype exécuté ; qualité de détection indépendante non évaluée.**

## Résultat et décision

M03 ajoute une estimation du déplacement apparent global de l'image et des propositions de zones résiduelles. Six clips réels sont traités : 12 secondes mesurées, 600 fenêtres de 20 ms et 60 fenêtres de préchauffage. Le modèle passe ses contrôles de support dans les 600 fenêtres mesurées, mais produit des régions résiduelles dans **599/600 fenêtres**. Ce nombre est une fréquence de sortie, **pas un taux de fausses alertes** : aucune annotation réelle relue n'est encore importée.

L'inspection des figures montre notamment des résidus sur la route et le décor proche. Une similarité globale ne suffit donc pas, à ce stade, à identifier les objets qui bougent indépendamment. La parallaxe et les erreurs de suivi sont des explications possibles, sans attribution quantitative démontrée. Nous conservons ce prototype comme référence diagnostique ; nous ne le présentons pas comme une compensation complète du mouvement de caméra.

La branche légère M01/M02 reste disponible. Ajouter M03 à chaque fenêtre augmente le coût ; son passage au premier plan n'est pas justifié avant une mesure de qualité.

## Données et causalité

- Trois clips de deux secondes par séquence, sélectionnés au début, au milieu et à la fin de la plage disponible, sans sélection par score ou label.
- `zurich_city_04_b` : train/debug ; `thun_00_a` : validation locale. Aucun accès au test réservé `09_b`.
- Préparation de 200 ms avant chaque clip ; pas fixe de 20 ms. Les fenêtres d'événements sont causales et le suivi compare l'image précédente à l'image courante.
- Lecteur indexé M02 ; aucune dépendance à YOLO, aux classes reconnues ou à un entraînement GPU.
- Horloges en microsecondes, ROI natives 640×480. Le manifeste conserve les dates absolues et les chemins des 600 images.

## Méthode implémentée

`src/pfe_events/global_motion.py` construit une image de comptes à 320×240, transformée par `log1p` avec échelle fixe, puis lissée par un noyau 3×3. Jusqu'à 400 points sont suivis par Lucas–Kanade pyramidal. Le contrôle aller-retour rejette les correspondances dont l'écart dépasse un pixel de l'image réduite.

Une similarité à quatre paramètres (translation, rotation et échelle isotrope) est estimée par RANSAC. Les critères retenus sont : au moins 20 pistes, 12 inliers, 50 % d'inliers et une enveloppe convexe couvrant 10 % de l'image. L'échelle doit rester entre 0,8 et 1,2. Un échec conduit à une abstention explicite. Le statut `VALID_IMAGE_MODEL` signifie uniquement que ces critères sont satisfaits ; il ne valide ni la pose de caméra ni une séparation physique des mouvements.

Les déplacements résiduels supérieurs à trois pixels natifs sont regroupés sur une grille de 32 pixels avec proximité spatiale. Une région requiert au moins trois points. Ces régions restent des **candidats de déplacement apparent résiduel**. Un objet sans points suivis peut être manqué ; une grande région peut mélanger plusieurs surfaces.

Le code repose sur les méthodes documentées par OpenCV : [Lucas–Kanade pyramidal](https://docs.opencv.org/4.x/dc/d6b/group__video__track.html) et [estimateAffinePartial2D](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html). La version effectivement exécutée est `opencv-python-headless 4.14.0.94`, enregistrée dans le rapport. Les modalités officielles DSEC ne constituent pas automatiquement des annotations de début de mouvement d'objet : [format des données](https://dsec.ifi.uzh.ch/data-format/).

## Temps mesurés

Rejeu disque non cadencé, CPU local, OpenCV limité à un thread. Le total comprend lecture, activité M01, représentation et suivi/ajustement global. Export des images, JSON et rendu exclus. Ces coûts ne sont pas des délais de réponse à un vrai début de mouvement.

| Clip | Total médian (ms) | Total p95 (ms) | Suivi/ajustement médian (ms) |
|---|---:|---:|---:|
| `zurich_city_04_b_0` | 20,02 | 25,52 | 8,62 |
| `zurich_city_04_b_1` | 24,17 | 36,03 | 8,39 |
| `zurich_city_04_b_2` | 37,94 | 50,56 | 8,31 |
| `thun_00_a_0` | 31,32 | 44,77 | 8,23 |
| `thun_00_a_1` | 30,48 | 44,50 | 8,14 |
| `thun_00_a_2` | 32,04 | 44,41 | 8,15 |

La chaîne combinée ne soutient pas un pas de 20 ms sur ces clips. Ces segments ne constituent pas une comparaison appariée avec M02 : ne pas attribuer toute différence de temps à une seule modification du code. L'étape globale pourrait ensuite fonctionner à cadence distincte, mais cela reste à implémenter et à mesurer avec l'âge des estimations.

## Annotation sans prédictions

Ouvrir [l'annotateur local](../outputs/motion/M03/annotate.html) dans un navigateur. Le dossier doit conserver `annotation_data.js` et `clips/` à côté du HTML. Le serveur local peut aussi servir ce dossier (commande ci-dessous). Aucun service externe n'est nécessaire.

1. Choisir un clip, le lire puis avancer image par image. Le pas est de 20 ms ; la lecture animée dépend des performances du navigateur et ne constitue pas un instrument de mesure de latence.
2. Tracer une ROI native autour du phénomène. Elle reste fixe : choisir une zone pertinente pour le début étudié, et ne pas interpréter une sortie de ROI comme un arrêt physique.
3. Choisir « début observable », « déjà en mouvement », « négatif » ou « incertain ». L'entrée d'un objet dans l'image ne prouve pas son démarrage. Les boîtes de détection officielles ne fournissent pas cette preuve non plus.
4. Pour un début, borner le temps possible/certain avec les deux boutons. Renseigner l'annotateur, les indices et ambiguïtés. Cocher « relue » seulement après examen du clip entier.
5. Ajouter chaque annotation, puis exporter le JSON avant de fermer. Les ajouts restent uniquement en mémoire jusqu'à l'export. Un clip non annoté n'est jamais considéré comme négatif.

L'interface a été chargée dans le navigateur local : six clips, contrôles et rendu événementiel vérifiés. Le dessin et le téléchargement JSON n'ont pas fait l'objet d'une validation interactive complète à cette étape. Les annotations en cours dans l'interface ne sont pas incorporées automatiquement aux résultats.

## Évaluation prête, résultats réels encore absents

`scripts/evaluate_motion_annotations.py` accepte le JSON exporté. Il exclut les brouillons, les zones incertaines et les objets déjà en mouvement. Les dates, ROI, identités de clips et alignements des prédictions sont contrôlés. Les résultats restent **par annotation et par partition** ; aucune moyenne qui compterait plusieurs fois des ROI superposées n'est produite.

Le critère de correspondance est fixé : le centre d'une région prédite doit être dans la ROI annotée. Il mesure la réponse dans cette zone, pas une AP de détection ni la segmentation d'un objet. Des propositions très grandes ou une ROI mal choisie peuvent biaiser cette mesure ; conserver les figures pour l'inspection.

Pour un début annoté dans `[t_possible, t_certain]`, une première réponse à `t` donne l'intervalle de délai `[(t−t_certain), (t−t_possible)]`. Une borne inférieure négative signifie une réponse pendant l'intervalle d'incertitude. L'horizon d'observation est fixé à 200 ms après la borne certaine ; une fin de clip anticipée est signalée. Une zone déjà active avant l'intervalle n'est pas créditée d'une bonne détection. Une abstention avant la première réponse rend l'interprétation du délai insuffisamment couverte. Le délai est celui de l'horloge des événements, sans coût CPU, file d'attente ou affichage.

Pour une ROI négative sur tout le clip, le rapport contient la fraction de fenêtres valides avec alerte, le temps actif, les départs d'alertes confirmés et les segments actifs dont le début est inconnu. Un départ confirmé exige deux sorties valides successives : inactive puis active. Une activité au bord du clip ou après abstention est comptée séparément comme début censuré. Le taux de départs utilise uniquement la durée des transitions observables ; toujours le lire avec la couverture, le temps actif et le nombre de débuts censurés. Une longue alerte continue peut avoir zéro nouveau départ tout en étant fausse pendant tout le clip.

Le fichier `annotations_empty_template.json` ne contient aucune annotation. Son passage dans le CLI produit `evaluation_pending.json` avec `NOT_EVALUATED_NO_ELIGIBLE_ANNOTATIONS`, sans score artificiel. **Aucun délai réel, rappel de mouvement ou taux de fausses alertes réel n'est actuellement revendiqué.**

## Commandes PowerShell

```powershell
# Nouvelle expérience ; refus d'écraser M03 existant.
.\.venv\Scripts\python.exe scripts/run_global_motion.py --output outputs/motion/M03_rerun

# Option de consultation locale ; laisser le terminal ouvert.
.\.venv\Scripts\python.exe -m http.server 8768 --bind 127.0.0.1 --directory outputs/motion/M03
# Puis http://127.0.0.1:8768/annotate.html

# Après export et relecture des véritables annotations.
.\.venv\Scripts\python.exe scripts/evaluate_motion_annotations.py --run outputs/motion/M03 --annotations outputs/motion/M03/M03_manual_annotations.json --output outputs/motion/M03/evaluation_v1.json

.\.venv\Scripts\python.exe -m unittest discover -s tests -v
python scripts/sync_markdowns.py
```

Copier le JSON téléchargé à l'emplacement indiqué ou adapter `--annotations`. Le CLI refuse d'écraser un rapport existant et conserve les SHA-256 des entrées et du code d'évaluation.

## Preuves et prochaine étape

- `outputs/motion/M03/summary.json` : paramètres, versions, temps et statut sans précision réelle.
- `clips/*/predictions.json` : 660 sorties avec préchauffage, timestamps et timings.
- `clips/*/diagnostic.png` : activité M01 à gauche, résidus M03 à droite ; `contact_sheet.png` : six dates par clip.
- `annotation_manifest.json`, `annotation_data.js`, `annotate.html` et 600 JPEG : matériel d'annotation séparé des prédictions.
- `source_snapshot/` : code de l'expérience ; `evaluation_tooling_snapshot/` : évaluateur et tests ajoutés ensuite.
- `verification.json` : intégrité des 600 images, dates, hashes des sources et contrôle du cas sans annotation.
- **53 tests réussis**, dont six sur le modèle global et huit sur les métriques. Les tests synthétiques ne prouvent pas une précision sur DSEC.

La prochaine porte est la relecture d'annotations de mouvement et de zones négatives, puis leur évaluation sans modification des seuils sur validation. Les cas ambigus restent exclus. Selon les erreurs constatées sur train, comparer une compensation tenant compte de la géométrie/profondeur ou une autre hypothèse de mouvement, et mesurer le bénéfice ainsi que le coût. Ne pas augmenter simplement le seuil pour faire disparaître visuellement le décor.
