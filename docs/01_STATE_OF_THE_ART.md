# Étude technique orientée décisions

État au 2026-10-03. Recherche ciblée, non exhaustive, fondée sur articles et dépôts des auteurs. Les références détaillées sont dans [PAPERS.md](PAPERS.md). Les coûts « faible/moyen/élevé » expriment une analyse de complexité et d'intégration, pas des temps mesurés sur le ThinkPad.

## Ce que l'on doit résoudre

Un événement indique une variation locale de luminance, pas directement une classe ou une distance. Notre problème réunit trois estimations distinctes : correspondances gauche/droite, sémantique YOLO, activité temporelle. Les entraîner ensemble dès le départ compliquerait le diagnostic. Une chaîne modulaire permet de remplacer la stéréo sans réentraîner la détection et d'isoler les erreurs de géométrie.

## Stéréo et profondeur

| Approche | Principe / architecture / données | Atout et limite | Reproduction, coût, Colab | Décision PFE |
|---|---|---|---|---|
| Accumulation + StereoSGBM | Images d'activité rectifiées ; coût de correspondance et régularisation semi-globale ; aucun entraînement | Très explicable ; creux, contours répétés, variations de polarité et flou temporel nuisent aux correspondances | OpenCV CPU, coût ~H×W×D ; Colab CPU possible ; aucune EPE acquise | Baseline géométrique, pas profondeur dense garantie |
| Stereo sur time surfaces | Associer structures de récence le long des épipolaires | Plus d'information temporelle ; sensible au bruit, vitesse, seuils et faible activité | Faible à moyen ; adaptation maison demanderait validation supplémentaire | Comparaison facultative après baseline |
| Deep event stereo ICCV 2019 | Embedding temporel appris puis réseau stéréo dense ; MVSEC | Référence fondatrice ; anciennes dépendances | Code disponible mais préparation Python 2.7/ROS et réseau Python 3.6 ; migration coûteuse | Étudier, ne pas porter en premier |
| SE-CFF, CVPR 2022 | Concentration d'événements et réseau stéréo ; DSEC | Représentation apprise et checkpoint public ; certains éléments du papier non publiés | Dépôt testé avec 8 A100, ce qui n'est pas une exigence prouvée pour l'inférence ; extension CUDA et Docker compliquent Colab | Alternative de checkpoint si EMatch échoue |
| EMatch, ICCV 2025 | Features récurrentes et attention contextuelle pour correspondances spatiales/temporelles ; DSEC/MVSEC | Code entraînement/inférence et poids annoncés ; modèle plus complexe qu'une accumulation | Python 3.8/Torch 2.0 dans recette officielle ; port Colab à valider sur batch 1, VRAM inconnue | Premier candidat à **auditer**, branche disparité seule |
| LiDAR-Event Stereo, ECCV 2024 | Stéréo aidée par motifs dérivés du LiDAR ; DSEC/M3ED | Répond aux régions pauvres en événements ; ajoute un capteur d'entrée | Poids de baselines événementielles disponibles, entraînement non fourni | Exclure LiDAR d'entrée ; baseline sans fusion en recours |
| EventHub, CVPR 2026 | Supervision proxy depuis images et adaptation de réseaux stéréo aux événements | Généralisation intéressante ; fabrique de données complexe | Code/poids disponibles ; génération avec CUDA et architectures A100/H100 par défaut | Veille récente, pas reproduction complète pour le MVP |

Sources : [OpenCV StereoSGBM](https://docs.opencv.org/4.x/d2/d85/classcv_1_1StereoSGBM.html), [ICCV 2019](https://github.com/tlkvstepan/event_stereo_ICCV2019), [SE-CFF](https://github.com/yonseivnl/se-cff), [EMatch](https://github.com/BIT-Vision/EMatch), [fusion LiDAR](https://github.com/bartn8/eventvppstereo), [EventHub](https://github.com/bartn8/eventhub).

Le LiDAR fourni avec un dataset peut servir de vérité terrain. L'utiliser comme entrée d'inférence serait une autre expérience, à ne pas présenter comme stéréo uniquement événementielle. De même, une profondeur monoculaire apprise ne remplace pas la triangulation imposée.

## Détection

| Stratégie | Architecture et supervision | Avantage | Limite / coût / décision |
|---|---|---|---|
| YOLO COCO directement sur pseudo-images | Réseau RGB appliqué sans adaptation | Diagnostic rapide de transfert de domaine | Poids inadaptés au contraste événementiel ; ne vaut pas solution validée |
| YOLO11n affiné sur event frames | Trois canaux d'activité ; labels natifs DSEC-Detection ; backbone préentraîné, tête adaptée | Simple, vraie composante DL et YOLO explicite | Nécessite apprentissage et métriques par classe ; principal choix proposé, GPU Colab à tester |
| Voxel grid + backbone modifié | B bins en entrée, première convolution adaptée | Préserve davantage d'ordre temporel | Modification des poids et du pipeline ; ablation tardive, pas achat de complexité initial |
| E2VID puis YOLO | Reconstruction d'intensité puis détection | Représentation plus proche du domaine RGB | Deux réseaux, artefacts de reconstruction et latence ; secours expérimental seulement |
| Images classiques + YOLO | Détection sur caméra d'intensité avec reprojection géométrique | Témoin de modalité utile | Ne démontre pas une détection fondée sur les événements ; ne sera pas présenté comme le pipeline final |
| RVT | Backbone récurrent avec attention, tête YOLOX ; Gen1/1Mpx | Référence sérieuse pour temporalité et latence | Plus difficile à expliquer et adapter ; notre YOLO compact conserve le périmètre simple |
| DAGr / détecteurs graphiques asynchrones | CNN image + graphe événementiel | Faible latence de mise à jour dans le cadre de l'article | Ingénierie spécifique, dépendance images et graphes ; référence, pas port du modèle |

[YOLO11 officiel](https://docs.ultralytics.com/models/yolo11/), [RVT](https://github.com/uzh-rpg/RVT), [DAGr, Nature 2024](https://www.nature.com/articles/s41586-024-07409-w). Le choix YOLO11n est un point de départ compact et documenté, pas une revendication de modèle le plus récent.

## Performances : ne pas mélanger les cadres

RVT rapporte dans son résumé **47,2 % mAP sur Gen1** et une inférence **< 12 ms sur T4**. Cela ne prédit ni la mAP DSEC de notre YOLO ni la latence de notre chaîne incluant la stéréo. [Article RVT](https://arxiv.org/abs/2212.05598).

Deux résultats de disparité EMatch ont été vérifiés dans le tableau 7 du préprint v2 et consignés dans [PAPERS.md](PAPERS.md). Pour les autres candidats stéréo, aucun tableau numérique complet n'a encore été audité. Un classement « état de l'art » dans un résumé ne sert pas de critère numérique. Notre statut reste **NOT RUN**. Avant intégration : relever version d'article, split, résolution, modalité, normalisation, métrique et matériel ; exécuter le checkpoint et enregistrer son hash.

## Choix de développement et règle de repli

PyTorch est retenu pour la détection et l'audit de stéréo profonde : correspondance avec les dépôts étudiés, accès aux poids et même écosystème pour l'apprentissage. NumPy/HDF5 pour les événements, OpenCV pour la baseline et la géométrie, fichiers PNG/JSON pour la première visualisation. Aucun besoin de microservice.

Budget d'audit d'un checkpoint stéréo : deux journées actives d'installation et premier passage, puis une courte évaluation. Si incompatibilité CUDA ou mémoire non résolue, journaliser l'échec et tester le candidat de secours. Aucun entraînement profond stéréo depuis zéro ne précède le MVP. La contribution réaliste est une fusion robuste et un compromis fenêtre/erreur/latence, mesurés avec une seule variable modifiée à la fois.
