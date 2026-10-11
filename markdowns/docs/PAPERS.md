# Base de travail bibliographique

Consultation : 2026-10-03. Fiches techniques, non destinées à être un chapitre de mémoire. Les résultats publiés ci-dessous sont attribués à leurs auteurs et ne sont pas des résultats du PFE. Reproduction locale des modèles : **NOT RUN**. Les références qui n'ont pas fait l'objet d'une lecture exhaustive sont signalées.

## P01 — Event-based Vision: A Survey

- Auteurs : Guillermo Gallego, Tobi Delbrück, Garrick Orchard, Chiara Bartolozzi, Brian Taba, Andrea Censi, Stefan Leutenegger, Andrew J. Davison, Jörg Conradt, Kostas Daniilidis, Davide Scaramuzza.
- Année/lieu : TPAMI, volume 44, 2022 ; prépublication antérieure.
- [Article](https://arxiv.org/abs/1904.08405).
- Problème/méthode : synthèse des capteurs, représentations et tâches événementielles ; pas un modèle unique à entraîner.
- Données/résultats : panorama multi-datasets ; aucune métrique unique pertinente à transposer ici.
- Intérêt : vocabulaire, modèle de génération, limites du capteur ; lecture ciblée des principes et des familles de représentations.

## P02 — Event-based Stereo Depth Estimation: A Survey

- Auteurs : Suman Ghosh, Guillermo Gallego.
- Version lue : arXiv v2, 27 mai 2025 ; préprint initial 2024. Ne pas confondre date de dépôt et date de publication.
- [Article et tableaux associés](https://arxiv.org/html/2409.17680v2).
- Problème : comparer des familles de stéréo parfois fondées sur des hypothèses différentes.
- Méthode : classement selon modalités, apprentissage et durée temporelle ; distinction entre stéréo instantanée et fusion à longue trajectoire.
- Données/résultats : comparaison de jeux et approches, pas une performance du PFE.
- Intérêt : privilégier la stéréo instantanée compatible avec scènes dynamiques et éviter de transformer le PFE en SLAM. Lecture ciblée de la taxonomie ; revue complète à approfondir si nécessaire.

## P03 — DSEC: A Stereo Event Camera Dataset for Driving Scenarios

- Auteurs : Mathias Gehrig, Willem Aarents, Daniel Gehrig, Davide Scaramuzza.
- Année/lieu : RA-L 2021 ; DOI 10.1109/LRA.2021.3068942.
- [Article](https://arxiv.org/abs/2103.06011), [données et outils](https://dsec.ifi.uzh.ch/).
- Problème/méthode : fournir des scènes routières stéréo calibrées et des références de disparité.
- Résultat principal : une ressource publique de 53 séquences ; la disponibilité des annotations objets vient d'une extension ultérieure, pas du papier initial.
- Intérêt : support principal de notre chaîne et de son évaluation ; la sélection détaillée figure dans 02_DATASETS.

## P04 — The Multi Vehicle Stereo Event Camera Dataset: An Event Camera Dataset for 3D Perception

- Auteurs : Alex Zihao Zhu, Dinesh Thakur, Tolga Ozaslan, Bernd Pfrommer, Vijay Kumar, Kostas Daniilidis.
- Année/lieu : RA-L 2018 ; DOI 10.1109/LRA.2018.2800793.
- [Article](https://arxiv.org/abs/1801.10202), [dataset](https://daniilidis-group.github.io/mvsec/).
- Problème : données événementielles de perception 3D avec références géométriques.
- Méthode : paire synchronisée, images, IMU et références profondeur/pose sur plusieurs plateformes.
- Résultat/intérêt : données réelles réutilisables pour un test de transfert géométrique. Pas de mAP objets à attribuer à ce dataset sans labels supplémentaires. Lecture résumé, format et accès aux données.

## P05 — M3ED: Multi-Robot, Multi-Sensor, Multi-Environment Event Dataset

- Auteurs : Kenneth Chaney, Fernando Cladera, Ziyun Wang, Anthony Bisulco, M. Ani Hsieh, Christopher Korpela, Vijay Kumar, Camillo J. Taylor, Kostas Daniilidis.
- Année/lieu : CVPR Workshops 2023, pp. 4015–4022.
- [Article](https://openaccess.thecvf.com/content/CVPR2023W/EventVision/papers/Chaney_M3ED_Multi-Robot_Multi-Sensor_Multi-Environment_Event_Dataset_CVPRW_2023_paper.pdf), [dataset](https://m3ed.io/).
- Méthode/données : acquisition multi-capteurs sur voiture, robot à pattes et plateforme aérienne ; stéréo événementielle HD.
- Résultat principal : diversification des conditions de mouvement et d'environnement, avec références géométriques.
- Intérêt : validation ultérieure des cas rapides ; volume et adaptation des formats plus coûteux. Les extensions sémantiques/3D récentes doivent être auditées séparément avant usage.

## P06 — Combining Events and Frames using Recurrent Asynchronous Multimodal Networks for Monocular Depth Prediction

- Auteurs : Daniel Gehrig, Michelle Rüegg, Mathias Gehrig, Javier Hidalgo-Carrió, Davide Scaramuzza.
- Année/lieu : RA-L 2021.
- [Projet](https://rpg.ifi.uzh.ch/RAMNet.html), [code / EventScape](https://github.com/uzh-rpg/rpg_ramnet).
- Méthode : fusion récurrente asynchrone événements/images pour profondeur **monoculaire** ; entraînement synthétique EventScape et adaptation MVSEC.
- Résultats : poids distribués ; métriques numériques non extraites dans cet audit.
- Intérêt : comprendre le rôle du contexte d'intensité. Ce travail ne justifie pas de remplacer la paire stéréo imposée par une profondeur monoculaire. Coût d'adaptation inutile pour notre MVP.

## P07 — Learning an Event Sequence Embedding for Dense Event-Based Deep Stereo

- Auteurs : Stepan Tulyakov, François Fleuret, Martin Kiefel, Peter Gehler, Michael Hirsch.
- Année/lieu : ICCV 2019.
- [Dépôt des auteurs et article lié](https://github.com/tlkvstepan/event_stereo_ICCV2019).
- Méthode : agrégation temporelle continue apprise puis traitement spatial pour stéréo dense ; MVSEC.
- Résultat publié : amélioration par rapport aux approches comparées dans cet article ; chiffres non repris sans audit complet du protocole.
- Intérêt : référence fondatrice de représentation apprise. Limite pratique : pile historique, coûts de migration et ROS dans la préparation. Reproduction non prioritaire.

## P08 — Stereo Depth from Events Cameras: Concentrate and Focus on the Future

- Auteurs : Yeongwoo Nam, Mohammad Mostafavi, Kuk-Jin Yoon, Jonghyun Choi.
- Année/lieu : CVPR 2022.
- [Article](https://ppolon.github.io/paper/cvpr2022-eventstereo.pdf), [code officiel](https://github.com/yonseivnl/se-cff).
- Méthode : concentrer une pile d'événements et apprendre la correspondance stéréo ; DSEC.
- Résultat principal : gain rapporté sur la qualité de disparité ; aucun FPS PFE déduit.
- Reproduction : poids accessibles ; code de distillation par événements futurs annoncé absent du dépôt. Distinguer la supervision utilisant le futur d'une inférence qui serait elle-même non causale.
- Intérêt : alternative événementielle documentée ; installation à tester avant engagement.

## P09 — EMatch: A Unified Framework for Event-based Optical Flow and Stereo Matching

- Auteurs préprint v2 : Pengjie Zhang, Lin Zhu, Xiao Wang, Lizhi Wang, Wanxuan Lu, Hua Huang. Le README ICCV 2025 affiche une liste différente sans Wanxuan Lu ; citer la version effectivement utilisée.
- [Préprint v2, 2024](https://arxiv.org/html/2407.21735v2), [code ICCV 2025](https://github.com/BIT-Vision/EMatch).
- Méthode : récurrence temporelle, attention spatiale et correspondances partagées.
- Résultats publiés, **tableau 7 du préprint v2, DSEC disparité** : EMatch-single MAE 0,49 px / RMSE 1,10 px ; EMatch-cross 0,47 / 1,09. Ce ne sont ni des erreurs métriques en mètres ni des résultats locaux.
- Intérêt : candidat d'inférence, entraînement complet trop ambitieux pour le premier cycle. Vérifier correspondance entre poids publiés et version du papier avant comparaison.

## P10 — LiDAR-Event Stereo Fusion with Hallucinations

- Auteurs : Luca Bartolomei, Matteo Poggi, Andrea Conti, Stefano Mattoccia.
- Année/lieu : ECCV 2024.
- [Code et article](https://github.com/bartn8/eventvppstereo).
- Méthode : injecter des structures synthétiques guidées par LiDAR pour aider la stéréo ; DSEC/M3ED.
- Résultat : amélioration rapportée pour la fusion ; ne pas transférer cette conclusion à un système sans LiDAR.
- Reproduction : poids de baselines, code d'évaluation ; entraînement non publié selon README.
- Intérêt : référence des limites dans les zones sans événements et source de baseline **sans** fusion. L'inférence LiDAR-guidée reste hors périmètre principal.

## P11 — Recurrent Vision Transformers for Object Detection with Event Cameras

- Auteurs : Mathias Gehrig, Davide Scaramuzza.
- Année/lieu : CVPR 2023.
- [Article](https://arxiv.org/abs/2212.05598), [code et poids](https://github.com/uzh-rpg/RVT).
- Méthode : backbone récurrent convolution/attention ; tête issue de YOLOX ; benchmarks Gen1/1Mpx.
- Résultats chiffrés vérifiés : voir 01_STATE_OF_THE_ART, attribués au résumé de l'article. Aucun transfert direct de ces chiffres vers DSEC.
- Intérêt : temporalité et faisabilité d'inférence GPU compacte ; reproduction plus complexe qu'un YOLO standard affiné. Ne pas présenter le fait d'utiliser une tête YOLOX comme équivalent à l'intégration déjà faite de notre YOLO11.

## P12 — Low-latency automotive vision with event cameras

- Auteurs : Daniel Gehrig, Davide Scaramuzza.
- Année/lieu : Nature 629, 1034–1040, 2024.
- [Article](https://www.nature.com/articles/s41586-024-07409-w).
- Méthode : branche images et graphe événementiel pour mises à jour asynchrones ; évaluations incluant Gen1 et DSEC-Detection.
- Résultat principal : réduction du compromis latence/bande passante dans ce système hybride. Les annonces d'équivalence à une caméra très haute cadence ne sont pas le FPS de notre pipeline fenêtré.
- Intérêt : justifie de mesurer délai perceptuel et calcul séparément, et documente la provenance des annotations. Pas de port du graphe proposé dans le MVP.

## P13 — EventHub: Data Factory for Generalizable Event-Based Stereo Networks without Active Sensors

- Auteurs : Luca Bartolomei, Fabio Tosi, Matteo Poggi, Stefano Mattoccia, Guillermo Gallego.
- Année/lieu : CVPR 2026.
- [Article](https://arxiv.org/abs/2604.02331), [code](https://github.com/bartn8/eventhub).
- Méthode : production de données/proxy-labels depuis images et adaptation de réseaux stéréo aux événements.
- Résultat principal : meilleure généralisation rapportée sur les benchmarks événementiels ; chiffres non transférés à notre sous-ensemble.
- Intérêt : piste récente d'adaptation et limites des labels LiDAR. Le coût de la fabrique complète dépasse l'objectif étudiant ; seuls des poids ou prétraitements isolés pourraient être réutilisés après audit.

## Travaux associés à approfondir uniquement si besoin

[Learning Visual Motion Segmentation Using Event Surfaces](https://openaccess.thecvf.com/content_CVPR_2020/html/Mitrokhin_Learning_Visual_Motion_Segmentation_Using_Event_Surfaces_CVPR_2020_paper.html), Anton Mitrokhin, Zhiyuan Hua, Cornelia Fermüller, Yiannis Aloimonos, CVPR 2020 : graphe spatio-temporel, EV-IMO, segmentation de mouvement spécifique. Résultats numériques non relevés ; étude utile pour délimiter ce que notre carte d'activité ne démontre pas.

Prochaine lecture ciblée : code et configuration du checkpoint EMatch réellement choisi, avec taille des tenseurs et conditions causales. Aucun palmarès global n'est établi entre tableaux d'articles aux protocoles différents.
