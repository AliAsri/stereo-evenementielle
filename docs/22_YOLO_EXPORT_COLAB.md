# Exports YOLO et entraînement Colab

## Extension Y02 personne / voiture / camion — 15 octobre 2026

**Entraînement Y02 exécuté dans Colab et résultats importés le 15 octobre.** Le run `Y02_20261015T134856Z` est complet : 100 époques de surapprentissage puis cinq époques du pilote. AP50 du petit lot : 0,995 par classe ; mAP50 de validation personne/voiture : 0,385203, mAP50–95 : 0,200357. AP camion indépendante : non évaluée. Les fichiers correspondent au paquet ci-dessous. Le rejeu intégré détecte le camion sur les 17 images du train ; le modèle reste sélectionné explicitement avec `--weights`, Y01 conservant sa place de référence par défaut. [Audit des archives](../outputs/reports/Y02_colab_audit.json) · [Résultats intégrés et coût](../outputs/yolo/Y02_comparison/verification.json). Y02 conserve YOLO11n, les images natives, les fenêtres de 50 ms, le normaliseur et les partitions existants. Le mapping devient DSEC 0 → person 0, DSEC 2 → car 1, DSEC 4 → truck 2, conformément au [format officiel DSEC-Detection](https://github.com/uzh-rpg/dsec-det#data-format). Les autres classes sont toujours exclues.

Fichiers à utiliser :

- [Y02_yolo11n_truck.ipynb](../notebooks/Y02_yolo11n_truck.ipynb).
- [dsec_yolo_truck_v1.zip](../data/processed/dsec_yolo_truck_v1.zip), 158 630 744 octets, environ 159 Mo. SHA-256 : `764e1523cca22ddb10abe9548a733d8969fb070205004f430a2899247f89c1ac`.

Pour lancer l'essai :

1. Importer le notebook Y02 dans Colab et sélectionner un runtime GPU.
2. Placer le ZIP dans `Mon Drive/PFE3/data/`, ou utiliser le téléversement proposé par le notebook.
3. Exécuter les cellules dans l'ordre et autoriser le montage de votre Drive. Le ZIP et les tenseurs sont vérifiés avant entraînement.
4. Conserver le dossier `Mon Drive/PFE3/runs/Y02_<date>/` : `status.json`, environnement, provenance, contrôles, métriques, `pilot/args.yaml`, `pilot/results.csv`, `best.pt` et `last.pt`.

Le diagnostic sur huit images couvre les trois classes et utilise 100 époques, nbs=4, sans warm-up ni régularisation ; son AP50 minimale de 0,80 par classe reste un garde de chargement/apprentissage sur le train, pas un score de généralisation. Le pilote complet repart des poids COCO initiaux pour cinq époques. Aucun résultat GPU n'est prérempli. Le poste local a chargé les tenseurs avec Ultralytics 8.4.172, mais CUDA y est indisponible.

Train : **536 images, 864 boîtes person, 2 466 car, 687 truck**. Validation : **238 images, 238 person, 667 car, zéro truck**. Les 774 PNG et les labels personne/voiture reproduisent exactement Y00. Le chargeur d'entraînement réel conserve 858 person, 2 463 car et les **687 truck** ; neuf petites boîtes des classes historiques sont filtrées par le framework. Les sept identités de suivi camion source ne constituent pas sept observations indépendantes : leurs boîtes se répètent au fil du temps dans deux subdivisions d'un même groupe routier.

**La qualité camion est non évaluée sur la validation actuelle.** Le notebook rapporte `ap50: null`, `ap50_95: null`, `NOT_EVALUATED` pour truck, et indique les classes utilisées pour sélectionner `best.pt`. Ce checkpoint est choisi sur personne/voiture ; un bon score global ne valide pas le camion. L'entraînement ou la prédiction sur les images train ne remplacent pas une séquence indépendante avec camions annotés. L'extension de la reconnaissance ne prouve pas le mouvement indépendant.

**249 tests réussis**, vérification complète des deux paquets, tests des tenseurs et de l'absence de métriques inventées. [Préparation](../outputs/yolo/Y02_preparation/preparation.json) · [Tenseurs et comptes par classe](../outputs/yolo/Y02_preparation/tensor-check.json). Les poids reçus ont ensuite été testés sur l'extrait intégré : 250 tests réussis, 153 tableaux et 17 modèles de mouvement conservés, coût complet médian Y02 de 462,5 ms. Le surcoût d'association a ensuite été corrigé : 15,4 ms médians, calcul complet 345,8 ms dans un nouvel essai sous charge variable, résultats exactement conservés et 252 tests réussis. [Comparaison](../outputs/yolo/Y02_association_speed/verification.json). L'absence de validation camion indépendante motive encore le maintien de Y01 par défaut. Les autres classes attendent un corpus d'entraînement et de validation approprié.

Reproduction locale, en utilisant un dossier neuf pour l'export :

```powershell
.\.venv\Scripts\python.exe scripts/export_yolo_pilot.py --include-truck --output data/processed/dsec_yolo_truck_v1
.\.venv\Scripts\python.exe scripts/build_yolo_notebook.py --export-report outputs/reports/Y00_truck_export.json --output notebooks/Y02_yolo11n_truck.ipynb
```

## Historique Y00 / Y01 à deux classes

**Mise à jour du 4 octobre 2026 :** les archives attestent l'échec initial, puis la réussite du diagnostic corrigé (100 époques, AP50=0,995 par classe, 200 pas réels) et du pilote de cinq époques (mAP50 validation=0,2373). Le protocole initial ci-dessous reste l'historique Y00/v1. [Analyse des résultats](24_Y01_COLAB_RESULTS.md).

Préparation initiale : 3 octobre 2026. **Y00 exécuté localement ; Y01 ensuite exécuté dans Colab par l'utilisateur.** Poids et résultats sont désormais importés sur ce poste ; aucune réévaluation du modèle n'y a été exécutée. Le contrôle runtime a réussi dans la session archivée.

## Ce qui est prêt

- `data/processed/dsec_yolo_pilot_v1/` : PNG, labels YOLO, manifeste par image, hashes, normaliseur S01, exemples annotés et vérificateur portable.
- `data/processed/dsec_yolo_pilot_v1.zip` : paquet de transfert, **158 606 475 octets**, environ **151,26 Mio**.
- `notebooks/Y01_yolo11n_events_pilot.ipynb` : 16 cellules, dont 7 cellules Python compilées localement ; aucune sortie GPU préremplie.
- `outputs/reports/Y00_export.json` et `Y00_verification.json` : compteurs, provenance et contrôles réels.

SHA256 du ZIP : `ad87dfce2316ceefb401afbc62bd7f64ac316451547da3d3302cb85b8830ef73`. Le notebook exige cette empreinte avant extraction. Le ZIP contient un dossier racine `dsec_yolo_pilot_v1` ; ses chemins internes sont portables. Le normaliseur provient de S01 et n'est pas réajusté sur la validation.

## Corpus et classes

| Partition locale | Images | Boîtes person | Boîtes car | Images sans classe retenue |
|---|---:|---:|---:|---:|
| train, `04_b` + `04_e` | 536 | 864 | 2 466 | 2 |
| val, `thun_00_a` | 238 | 238 | 667 | 0 |
| Total | 774 | 1 102 | 3 133 | 2 |

Les classes DSEC **0 pedestrian → 0 person**, **2 car → 1 car** sont explicites. Rider n'est pas fusionné avec pedestrian. Les annotations d'autres classes sont retirées ; leurs objets deviennent donc du fond pour ce détecteur à deux classes. Ce choix limite le pilote aux priorités personne/voiture. Il ne répond pas encore à une détection générique à huit classes.

Chaque image est construite sur `[t−50 000,t[` µs, à une date effectivement annotée, dans la caméra gauche native 640×480. Tous les timestamps distincts avec fenêtre complète sont exportés : 268 / 268 / 238 pour `04_e` / `04_b` / `thun_00_a`. Une première date par séquence est exclue faute d'historique complet. Le manque de GT disparité à une date n'exclut pas cette date d'entraînement de détection.

Les deux images négatives possèdent des annotations officielles mais aucune boîte des classes retenues après conversion ; leur fichier texte est vide. Aucune date sans annotations n'a été inventée comme négatif. Les omissions éventuelles des annotations officielles restent une limite.

## Conversion des boîtes et traçabilité

Pour chaque boîte retenue : vérifier les valeurs finies et dimensions positives, former les coins xyxy, les borner au capteur, rejeter l'intersection vide, puis calculer centre/largeur/hauteur normalisés. Aucun seuil de taille minimale n'est appliqué à l'export. Les doublons exacts après arrondi à neuf décimales sont supprimés et comptés ; aucun n'a été rencontré ici.

Sur les dates admissibles : **5 390 boîtes source**, **1 081 exclues pour classe**, **74 hors champ/dégénérées**, **4 235 conservées**. Parmi les boîtes géométriquement admissibles, **406 ont été bornées**. Aucune géométrie non finie ou dimension non positive n'a été rencontrée. Les 22 annotations des trois dates sans historique sont exclues avant ce bilan.

`manifest.json` conserve séquence, groupe, partition, temps absolus, nombre d'événements, compteurs de conversion, lignes source, track IDs et classes DSEC des labels retenus. Il conserve aussi les hashes des labels originaux, du code, du normaliseur et les manifests de téléchargement. `checksums.json` couvre 1 560 fichiers ; le fichier de checksums n'inclut pas sa propre empreinte. L'empreinte externe du ZIP protège le paquet complet.

## Canaux : précaution nécessaire

Le PNG utilise les emplacements RGB pour **positif, négatif, total**, après `log1p`, normalisation figée et écrêtage. Une lecture OpenCV produit BGR ; une permutation supplémentaire mal placée échangerait les représentations. Les 774 fichiers ont été relus avec Pillow et OpenCV : `RGB == BGR[...,::-1]` est vérifié exactement.

La distribution officielle **Ultralytics 8.4.172** a été téléchargée pour lecture de son code, avec contrôle SHA256 contre les métadonnées PyPI. Elle n'a pas été installée dans le socle CPU. Le chargeur lit BGR et `Format(bgr=0)` retourne RGB. Le notebook désactive HSV, permutation BGR et les transformations Albumentations implicites via `augmentations=[]`. Sans cette dernière option, une installation disposant d'Albumentations peut ajouter niveaux de gris/CLAHE malgré HSV=0. [Code de référence](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/data/augment.py), audit de la version figée dans `outputs/reports/ultralytics_source_audit/`.

Même avec une géométrie identité, le filtre interne `RandomPerspective.box_candidates` peut rejeter les boîtes de largeur/hauteur ≤2 pixels ou de rapport extrême. Neuf labels train sont potentiellement concernés d'après leur géométrie exportée. Le notebook compte les boîtes réellement chargées pour publier cet écart, sans prétendre que ce contrôle runtime a déjà été exécuté.

## Contrôles effectués localement

**27 tests réussis**, dont six nouveaux sur mapping, clipping, coordonnées, invalides, doublons et sérialisation. Vérification complète des hashes, dimensions, mode PNG, paires image/label, classes, bornes, doublons et partitions. Aucun groupe ni PNG identique n'apparaît dans deux partitions.

Les **4 235 boîtes sauvegardées** ont été comparées aux lignes originales DSEC, avec recalcul indépendant des coins bornés et contrôle du timestamp. **Neuf images** (début/milieu/fin de chaque séquence) ont été reconstruites depuis les HDF5 et comparées pixel par pixel aux PNG exportés. Deux vues annotées ont été inspectées visuellement. Les sept cellules Python du notebook sont syntaxiquement compilables ; cela ne prouve pas leur exécution CUDA ni la disponibilité future du service Colab.

## Exécuter le notebook

1. Importer `Y01_yolo11n_events_pilot.ipynb` dans [Google Colab](https://colab.research.google.com/) et choisir un runtime GPU.
2. Copier le ZIP dans `Mon Drive/PFE3/data/`, ou le téléverser quand la cellule le propose. Monter Drive avec votre compte.
3. Exécuter les cellules dans l'ordre. Le notebook crée une session neuve sous `Mon Drive/PFE3/runs/`, relève GPU/VRAM/Python/PyTorch/CUDA et fige la version Ultralytics. Les dépendances effectivement résolues sont exportées par `pip freeze` ; elles ne sont pas toutes prévalidées localement.
4. Vérifier l'archive, ses chemins et le dataset. Contrôler six véritables tenseurs Ultralytics train/val, leur ordre de canaux et leur letterbox 640×640 avec bandes de 80 pixels. Afficher un lot rechargé avec ses boîtes.
5. Télécharger YOLO11n officiel, conserver son hash, puis surapprendre huit images de train pendant au plus le budget fixé de 50 époques. Le diagnostic utilise volontairement les mêmes images en train/val ; ce score n'est jamais une généralisation. Le garde-fou initial exige AP50≥0,80 pour chaque classe avant la suite.
6. Si ce diagnostic passe, repartir des poids initiaux et lancer cinq époques sur les 536 images, puis évaluer les 238 images de validation. Les augmentations sont désactivées pour ce premier contrôle. Optimiseur AdamW et réglages explicites ; AMP désactivé. Ce n'est pas encore une recherche d'hyperparamètres.

Le notebook enregistre `args.yaml`, métriques, courbes, `best.pt`, `last.pt`, état de session et provenance sur Drive. Les paramètres de calcul des AP incluent confidence minimale 0,001, IoU NMS 0,7, maximum 300 détections. Le score du pilote est séparé du score de surapprentissage. Le modèle sélectionné sur cette petite validation n'a pas encore passé un test final indépendant.

Si la session échoue ou le petit lot ne converge pas, conserver l'erreur et les courbes ; ne pas augmenter aveuglément le budget. Les indications de reprise depuis `last.pt` figurent à la fin du notebook. Une déconnexion peut nécessiter de réextraire le paquet au même chemin temporaire avant reprise.

## Résultats encore absents

Chargement Ultralytics, surapprentissage corrigé, entraînement et validation GPU : **RUN**, attestés par les archives. Le pic d'allocation PyTorch est rapporté, pas la VRAM totale. L'audit local n'utilise pas de session Colab connectée. La comparaison quantitative avec un modèle COCO non adapté reste à implémenter en respectant le mapping des classes. La fusion avec profondeur et la détection de mouvement restent à développer.
