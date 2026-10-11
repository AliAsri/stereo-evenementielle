# Veille technique corrigée — Stéréovision événementielle et objets mobiles

Version 2.0 — 10 octobre 2026 — revue D01 du document externe `veille_bibliographique_pfe.md`.

[Conception corrigée](conception_pfe_stereo_evenementielle.md) · [Journal de revue](48_REVIEW_CONCEPTION_BIBLIOGRAPHIE.md) · [Prochaine expérience prévue](20_NEXT_STEPS.md).

## 1. Portée de la vérification

Cette veille sert au développement et à l'expérimentation du PFE. Toutes les sections des deux documents fournis ont été relues ; les références centrales ont été confrontées aux pages des auteurs, articles, dépôts ou documentations officielles. Les pistes périphériques non contrôlées sont conservées dans une réserve explicite. Cette revue ne constitue ni une reproduction expérimentale des publications, ni une recherche bibliographique exhaustive.

La présence d'un article, d'un dépôt ou d'un résumé ne démontre pas que ses poids sont utilisables sur notre machine. Les statuts portent sur une affirmation précise :

- **Documenté** : la source primaire consultée soutient la description donnée.
- **Rapporté par les auteurs** : résultat chiffré de leur expérience, non reproduit dans le PFE.
- **À auditer** : conditions d'exécution, protocole détaillé, checkpoint ou référence restant à vérifier.
- **Proposition PFE** : choix de travail, distinct d'un résultat publié.

Les anciens « ✅ » généralisés sont retirés. Les résultats de recherche multilingue rapportés par la version 1 ne sont pas un protocole exhaustif reproductible ; l'absence d'un mémoire trouvé ne démontre pas une nouveauté scientifique.

## 2. Données : distinguer objets, mobilité et profondeur

| Ressource et source primaire | Information documentée | Usage et réserve pour le projet |
|---|---|---|
| [DSEC, Gehrig et al., 2021](https://arxiv.org/abs/2103.06011), [site officiel](https://dsec.ifi.uzh.ch/) | Corpus original de 53 séquences routières, stéréo événementielle et images, référence de disparité | Principal. Une référence LiDAR n'est pas dense ni disponible pour chaque pixel/date |
| [DSEC-Detection](https://dsec.ifi.uzh.ch/dsec-detection/) | Boîtes, catégories et identités de suivi ; la distribution inclut des séquences supplémentaires au corpus original | YOLO obligatoire. Les huit catégories annoncées ne sont pas huit classes de mobilité ; ne pas réduire cette extension aux « 53 séquences » sans son inventaire |
| [DSEC-MOD / RENet](https://github.com/ZZY-Zhou/RENet), [article](https://arxiv.org/abs/2209.08323) | Référence d'objets mobiles associée à un travail de fusion RGB–événements | Audit local M15/M16 disponible. Le cache utilisé porte une classe `Moving`, sans distinction sémantique voiture/personne |
| [DSEC-MOS / EmoFormer](https://github.com/ZZY-Zhou/DSEC-MOS), [article v3, §IV-A](https://arxiv.org/html/2305.00126v3) | 16 séquences : 10 495 frames train et 2 819 test ; masques candidats issus d'un modèle dérivé de SAM, puis corrections et vérifications humaines | Future référence pixel. Les huit catégories évoquées dans l'article décrivent les objets du corpus ; auditer l'encodage des fichiers avant de supposer huit labels sémantiques par pixel |
| [EVIMO2, Burner et al., 2022](https://arxiv.org/abs/2205.03467) | Trois caméras événementielles 640×480 ; 173 séquences ; profondeur/segmentation à 60 Hz et poses caméra/objets | Complément. L'échantillon M14 est mono-caméra. Un masque d'identité ne suffit pas à définir la mobilité instantanée |
| [EV-IMO, Mitrokhin et al., 2019](https://arxiv.org/abs/1903.07520) | Dataset et pipeline d'apprentissage pour la segmentation de mouvement | Référence historique distincte d'EVIMO2 |
| [M3ED, site des auteurs](https://m3ed.io/) | Données multi-capteurs embarquées sur plusieurs types de plateformes, dont stéréo événementielle | Généralisation éventuelle selon les GT effectivement fournies ; aucune évaluation de masque mobile garantie par la seule présence d'objets dans les scènes |
| [MVSEC, site des auteurs](https://daniilidis-group.github.io/mvsec/) | Stéréo événementielle DAVIS346, données de profondeur et poses | Comparaison selon le protocole propre à MVSEC. La résolution et la géométrie diffèrent de DSEC |
| [MTevent, Awasthi et al., 2025](https://arxiv.org/abs/2505.11282) | **CVPR Workshops 2025**, stéréo événementielle et RGB, 75 scènes, 16 objets, poses 6D et détection d'objets mobiles | Piste secondaire. Le baseline de pose présenté utilise FoundationPose sur RGB ; ce n'est pas une preuve de performance d'un modèle événementiel |

L'alignement « dans le repère événementiel » ne garantit pas l'absence de parallaxe entre capteurs RGB et événementiels. M16 l'a vérifié sur six dates seulement ; les autres dates ne sont pas déclarées automatiquement alignées. Une annotation humaine assistée par modèle et une annotation dérivée de poses/CAD ont des sources d'erreur différentes : aucun classement général de fiabilité n'est établi ici.

Même famille de données ne signifie pas même support de labels. Pour un apprentissage conjoint disparité/mouvement, construire le manifeste des dates et vues disponibles ; masquer les pertes absentes au lieu d'inventer des cibles. Respecter les partitions par trajet et la provenance des préentraînements. Ne pas fusionner MOD/MOS/Detection sans cet audit.

Les calibrations par séquence font autorité pour les focales et baselines. Les valeurs nominales de 60 cm pour DSEC et 10 cm pour MVSEC ne sont pas des constantes à injecter dans tous les calculs. Comparer les méthodes dans chaque benchmark avant de discuter le transfert entre corpus.

## 3. Références centrales de stéréo

| Référence | Ce que la consultation permet de retenir | Conséquence pratique |
|---|---|---|
| [Ghosh et Gallego, Event-based Stereo Depth Estimation: A Survey](https://arxiv.org/abs/2409.17680) | Cartographie de la stéréo événementielle | Point d'entrée pour distinguer appariement instantané, intégration temporelle et besoin de poses |
| [DDES, Tulyakov et al., ICCV 2019](https://github.com/tlkvstepan/event_stereo_ICCV2019) | Dépôt lié à l'apprentissage d'un plongement de séquences pour la stéréo dense | Référence historique ; exécution et compatibilité des anciennes dépendances non testées ici |
| [SE-CFF, Nam et al., CVPR 2022](https://openaccess.thecvf.com/content/CVPR2022/papers/Nam_Stereo_Depth_From_Events_Cameras_Concentrate_and_Focus_on_the_CVPR_2022_paper.pdf) | Représentation concentrée et apprentissage utilisant du futur, avec inférence sur le passé ; variante événements seuls et extension avec images | Le futur d'entraînement ne doit pas être introduit en inférence ; choisir explicitement la modalité. Le chiffre de 500 000 événements n'est pas un optimum universel |
| [Discrete Time Convolution, Zhang et al., CVPR 2022](https://github.com/Huawei-BIC/Discrete_Time_Convolution_for_Fast_Event_Based_Stereo) | Le dépôt fournit des variantes DTC-PDS et DTC-SPADE et des parcours DSEC/MVSEC | Candidat rapide à auditer ; le nom de la méthode ne valide pas son coût sur Colab |
| [Temporal Event Stereo, Cho, Kang et Yoon, ECCV 2024](https://arxiv.org/abs/2407.10831) | Apprentissage de flux stéréoscopique et agrégation d'information passée ; résultats annoncés sur **MVSEC et DSEC** | Retrait de l'affirmation non étayée « SOTA sur M3ED et EVIMO2 ». Un mécanisme temporel peut aider la stéréo sans produire directement des labels mobiles |
| [EMatch, Zhang et al., ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Zhang_EMatch_A_Unified_Framework_for_Event-based_Optical_Flow_and_Stereo_ICCV_2025_paper.html), [code](https://github.com/BIT-Vision/EMatch) | Cadre commun d'appariement pour flux et disparité | Candidat déjà envisagé dans le projet. Vérifier configuration et provenance des poids ; ne pas confondre flux optique total et mouvement propre d'objet |
| [EV-MGDispNet, Jiang et al., 2024](https://arxiv.org/abs/2408.05452) | Agrégation et attention guidées par des cartes de confiance de mouvement, avec perte de cohérence gauche-droite | Les cartes de confiance servent à la disparité ; elles ne sont pas des masques certifiés de mobilité indépendante |
| [MADNet-ε, Mannocci et al., IET Image Processing 2026](https://cris.unibo.it/handle/11585/1081390) | Histogrammes de 10 ms, extracteur récurrent avec cellules spiking ConvLSTM, préentraînement ε-CARLA puis données réelles ; **>140 FPS rapportés** | L'architecture initiale proposée n'est pas cette méthode. Hardware, périmètre de mesure, code et poids à auditer avant adoption |
| [DERD-Net, Hitzges, Ghosh et Gallego, NeurIPS 2025](https://arxiv.org/abs/2504.15863) | Densités de rayons reconstruites avec des **poses caméra connues**, puis réseau local récurrent | La réduction de MAE d'au moins 42 % est une annonce sous ce protocole. L'entrée pose est une différence majeure avec notre stéréo instantanée |
| [URNet, 2025](https://arxiv.org/abs/2509.18184) | Réseau de raffinement tenant compte de l'incertitude pour la stéréo événementielle | Existence et thème confirmés ; poids, détails de pertes, calibration de confiance et performances à auditer |
| [EventHub, Bartolomei et al., CVPR 2026](https://arxiv.org/abs/2604.02331) | Données et annotations proxy dérivées d'images pour entraîner la stéréo événementielle sans GT provenant de capteurs actifs | Utile pour étudier le transfert. « Sans capteur actif » ne signifie pas sans supervision ; pas une preuve de segmentation mobile |
| [Wu et al., Depth Estimation from Moving Stereo Event Cameras without Motion Cues](https://openreview.net/pdf/df48eb5bb11fafa2042396b6e46baa6eecc40608.pdf) | Représentation SCARF et SGBM ; profondeur semi-dense sans pose externe, plus de 100 Hz sur MVSEC rapportés dans le résumé | Piste proche de notre référence SGBM. Ne pas transférer ce débit à DSEC ni au détecteur complet ; audit de reproduction nécessaire |

Une architecture légère n'est pas définie uniquement par son nombre de poids. Mesurer les volumes intermédiaires, opérateurs, états temporels et transferts. AANet est un exemple de remplacement des convolutions 3D par une agrégation adaptative ; sa classification comme équivalent coûteux de PSMNet était incorrecte. [Source AANet, CVPR 2020](https://openaccess.thecvf.com/content_CVPR_2020/html/Xu_AANet_Adaptive_Aggregation_Network_for_Efficient_Stereo_Matching_CVPR_2020_paper.html).

Le document initial excluait les SNN tout en prenant MADNet-ε comme inspiration principale : il fallait signaler ses cellules récurrentes impulsionnelles. La version corrigée propose un audit de faisabilité, sans exclusion fondée sur la seule famille d'architecture.

## 4. Détection, segmentation de mouvement et 3D

| Référence | Entrées / tâche | Limite pour notre comparaison |
|---|---|---|
| [Mitrokhin et al., Event-based Moving Object Detection and Tracking, IROS 2018](https://arxiv.org/abs/1803.04523) | Compensation du mouvement apparent et détection/suivi à partir d'événements | Inspiration géométrique ; une compensation globale simple ne traite pas automatiquement toute parallaxe |
| [Zhou, Gallego, Lu, Liu et Shen, Event-based Motion Segmentation with Spatio-Temporal Graph Cuts, TNNLS 2021](https://arxiv.org/html/2012.08730v3) | Ajustement de plusieurs modèles et segmentation spatio-temporelle | Attribution à Parameshwara corrigée. Le §VI-B rapporte bien **64,38 % d'IoU sur son expérience EVIMO2** ; ne pas le supprimer ni le convertir en objectif universel |
| [FAST-Dynamic-Vision, He et al., 2021](https://arxiv.org/abs/2103.05903) | Compensation et fusion événements/profondeur pour trajectoires | Dépendances capteurs et estimateurs à reproduire ; pas une baseline purement stéréo événementielle interchangeable |
| [EV-IMO, Mitrokhin et al., IROS 2019](https://arxiv.org/abs/1903.07520) | Dataset et apprentissage de segmentation de mouvement | Protocole distinct des masques d'identité bruts présents dans notre acquisition EVIMO2 |
| [EV-LayerSegNet, Farah et al., CVPRW 2025](https://openaccess.thecvf.com/content/CVPR2025W/EventVision/html/Farah_EV-LayerSegNet_Self-supervised_Motion_Segmentation_using_Event_Cameras_CVPRW_2025_paper.html) | Auto-supervision par compensation ; couches et flux affines | L'évaluation présentée porte sur des données **simulées à mouvement affine**. Elle ne démontre pas une séparation routière 6DoF sur DSEC |
| [AED, Liu et al., TIM 2023 ; prépublication 2022](https://arxiv.org/abs/2208.11602) | Détection d'objets, représentation TAF et robustesse à la vitesse relative caméra/objet | À classer dans la détection sémantique événementielle ; ce n'est pas un équivalent direct d'un masque de mobilité monde |
| [RENet, RGB-Event Fusion for Moving Object Detection in Autonomous Driving](https://arxiv.org/abs/2209.08323) | Détection mobile par fusion RGB–événements | Source de MOD et comparaison multimodale, différente d'une inférence événements seuls |
| [EvPlug](https://arxiv.org/abs/2312.16933) | Module de fusion images/événements | Existence et thème documentés ; conditions exactes et gains sur MOD à extraire avant comparaison chiffrée |
| [EmoFormer / DSEC-MOS](https://arxiv.org/html/2305.00126v3) | Événements utilisés comme supervision à l'entraînement ; **images RGB en inférence** | Ne pas le présenter comme un détecteur événementiel seul ni confondre « sans événements en inférence » et « sans images » |
| [Ev-Stereo3D, Kang, Cho et Yoon, ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Kang_Unleashing_the_Temporal_Potential_of_Stereo_Event_Cameras_for_Continuous-Time_ICCV_2025_paper.html) | Détection 3D en temps continu avec stéréo événementielle | Référence proche du volet 3D ; ni preuve de mobilité indépendante ni garantie de délai physique. Sa lourdeur doit être mesurée, pas présumée |

Le §VI-D de l'article graph cuts rapporte des temps de l'ordre de secondes pour certaines étapes sur son CPU. Il fournit donc surtout une référence de modélisation pour notre besoin de faible délai. Son protocole de conversion événements→masques et ses exclusions d'évaluation doivent accompagner ses chiffres.

Un résidu après compensation peut indiquer un mouvement propre **ou** une erreur du modèle, du suivi, de la profondeur ou de l'alignement. Une méthode n'est comparable à une autre que si la tâche, les entrées et les labels correspondent.

## 5. Chiffres vérifiés et chiffres à ne pas transférer

Le tableau ci-dessous est **historique : compétition DSEC CVPR 2021**, test officiel. Les quatre lignes ont été contrôlées sur la [page officielle des résultats](https://dsec.ifi.uzh.ch/cvpr-2021-competition-results/). `E` désigne les événements, `I` les images. MAE/RMSE sont en pixels de disparité ; 1PE/2PE sont des pourcentages de pixels GT dépassant respectivement 1/2 px d'erreur.

| Rang historique | Méthode | Entrées | MAE (px) | 1PE (%) | 2PE (%) | RMSE (px) |
|---|---|---|---:|---:|---:|---:|
| 1 | EI-Stereo | E + I | 0,396 | 5,814 | 1,055 | 0,906 |
| 2 | CESNet | E | 0,510 | 9,366 | 2,408 | 1,170 |
| 3 | LSMonRGBE | E + I | 0,517 | 9,235 | 1,867 | 1,324 |
| 6 | DSEC Baseline | E | 0,576 | 10,915 | 2,905 | 1,381 |

Ce tableau ne représente pas le classement de 2026. Le [protocole actuel consulté](https://dsec.ifi.uzh.ch/uzh/disparity-benchmark/) prévoit une évaluation sur les pixels GT de la vue événementielle gauche ; ses résultats dynamiques n'ont pas été extraits ici. Les mesures locales S01 sur une petite validation avec abstentions ne doivent pas être ajoutées au classement comme si le protocole était identique.

Les affirmations « SE-CFF 0,533 », « DTC-PDS ≈0,53 », « MAE cible 0,55–0,65 », « MVSEC→DSEC MAE 13 donc il faut toujours réentraîner », ainsi que les gains de 92 % ou 4,8 cm sans protocole associé, ne sont plus des conclusions opérationnelles. Les chiffres non recontrôlés restent dans l'original archivé. Pour les réutiliser, extraire la table exacte, variante, partition, unité, domaine valide, données d'entraînement et modalités.

La promesse de 60–100 FPS pour notre pipeline et l'objectif IoU >65 % ne sont pas déduits de ces publications. Les références rapides chronomètrent des périmètres et matériels différents ; les valeurs GPU ne prédisent pas le coût CPU local.

## 6. Outils et reproductibilité

| Outil / dépôt | Vérification et décision documentaire |
|---|---|
| [Tonic, catalogue officiel](https://tonic.readthedocs.io/en/latest/autoapi/tonic/datasets/index.html) | Les interfaces DSEC, MVSEC et TUMVIE sont bien documentées. Cela ne remplace pas l'audit de leurs conventions ou des loaders déjà présents dans le projet |
| [OpenEB](https://github.com/prophesee-ai/openeb) | Le dépôt public consulté ne confirme pas l'affirmation « OpenEB a été archivé ». Retrait de cette affirmation ; ne pas confondre statut du SDK, composants et anciennes versions |
| [EMatch](https://github.com/BIT-Vision/EMatch), [Temporal Event Stereo](https://github.com/mickeykang16/TemporalEventStereo), [DTC](https://github.com/Huawei-BIC/Discrete_Time_Convolution_for_Fast_Event_Based_Stereo), [DDES](https://github.com/tlkvstepan/event_stereo_ICCV2019) | Dépôts consultés. Aucun n'a été installé ou exécuté pendant D01 ; checkpoint et reproductibilité restent à auditer |
| [EventCV](https://arxiv.org/abs/2609.21330) | Notice d'article confirmée en 2026 ; bibliothèque non testée localement |
| dv-processing, Metavision, jAER, evlib, EV-Utils | Pistes externes ; compatibilité, maintenance, périmètre ouvert et versions non audités ici |
| ESIM, v2e, DAVIS Simulator, ICNS, DVS-Voltmeter, CARLA DVS | Pistes de simulation conservées ; un simulateur n'est pas nécessaire à la prochaine expérience |

Le projet dispose déjà de lecteurs, géométrie, configuration, provenance, tests et scripts. Conserver ces composants. Tout modèle retenu aura son environnement compatible sur Colab, sa révision de code, ses poids hachés, ses paramètres et son manifeste de données. Ne pas supposer qu'une liste de dépendances non exécutée garantit une reproduction.

## 7. Registre des autres pistes : statut explicite

Les références suivantes sont conservées pour éviter de perdre la recherche initiale. **Elles ne justifient pas une décision technique avant la vérification indiquée.** Les superlatifs « premier », « SOTA », les taux d'acceptation et chiffres détaillés non recontrôlés ont été retirés.

### 7.1 Articles dont la notice a été consultée, mais pas le protocole complet

| Piste | Source | Ce qui reste à vérifier |
|---|---|---|
| Continual Adaptation for Deep Stereo | [arXiv 2007.05233](https://arxiv.org/abs/2007.05233) | Distinguer MADNet conventionnel de MADNet-ε événementiel ; variantes et budget d'adaptation |
| Stereo-DEVO | [arXiv 2509.08235](https://arxiv.org/abs/2509.08235) | Entrées, entraînement, causalité, débit et dérive des poses ; intérêt après diagnostic de notre modèle caméra |
| eKalibr-Stereo | [arXiv 2504.04451](https://arxiv.org/abs/2504.04451) | Reproduction et conventions ; acquisition matérielle hors priorité actuelle |
| Egocentric Event-Based Vision for Ping Pong Ball Trajectory Prediction | [arXiv 2506.07860](https://arxiv.org/abs/2506.07860) | Tâche, protocole et métriques ; ne pas réutiliser le gain chiffré de la version 1 sans son contexte |

### 7.2 Références secondaires non revalidées dans cette revue

| Groupe | Pistes conservées et liens fournis dans l'original | Vérification nécessaire |
|---|---|---|
| Revues générales | [Deep Learning for Event-based Vision](https://arxiv.org/abs/2302.08890), [Hardware, Algorithms, and Applications](https://arxiv.org/abs/2504.08588), [Deep Stereo in the Twenties](https://arxiv.org/abs/2407.07816), [Recent Event Camera Innovations](https://arxiv.org/abs/2408.13627), [Mobile Embodied Perception](https://arxiv.org/abs/2503.22943) | Titre, auteurs, version et passages pertinents avant attribution détaillée |
| Revues chinoises | [Qiu et al., DOI 10.3788/LOP241073](https://researching.cn/ArticlePdf/m00002/2025/62/4/0400004.pdf), [Robot, DOI 10.13976/j.cnki.xk.2021.0069](https://xk.sia.cn/cn/article/doi/10.13976/j.cnki.xk.2021.0069) | Notice, texte et traduction ; pas de conclusion sur toute la littérature chinoise |
| Géométrie / impulsions | Osswald 2017, Xie–Chen–Orchard 2017, [MC-EMVS](https://arxiv.org/abs/2210.08927), [ESVO](https://arxiv.org/abs/2007.15548), [StereoSpike](https://arxiv.org/abs/2109.13751) | Besoin de poses, hypothèses de scène, entrées exactes et taux de décharge éventuels |
| Stéréo apprise et fusion | SCSNet 2022 ; [LiDAR-Event Stereo Fusion](https://github.com/bartn8/eventvppstereo) ; [distillation inter-capteurs ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/papers/Zhang_Enhanced_Event-based_Dense_Stereo_via_Cross-Sensor_Knowledge_Distillation_ICCV_2025_paper.pdf) | Distinguer capteurs nécessaires à l'entraînement et à l'inférence ; poids et coûts |
| Autres stéréos | EI-Stereo, CMPStereo, Active Event-based Stereo Vision | Les chiffres historiques EI-Stereo sont contrôlés au §5 ; les détails des autres approches et la mention de projecteur IR restent à vérifier |
| Mouvement classique | Stoffregen et al. 2019 ; Yamaki et al. 2025 ; Mondal et al. 2021 ; méthode IMU 2023 ; [disparité antérieure, arXiv 1809.07986](https://arxiv.org/abs/1809.07986) | Notices et hypothèses exactes ; ne pas assimiler tous les modèles de compensation |
| Comparaison RGB–événements | SSTNet, titre fourni : Multi-level Aggregation Attention RGB–Event Fusion Network for Moving Object Detection | Recherche effectuée, mais source primaire exploitable non obtenue ; statut, ConvLSTM, code et classement non validés ici |
| Détection sémantique | Perot et al., NeurIPS 2020 | Tâche de détection à distinguer des labels de mobilité indépendante ; contrôler la référence avant citation |
| Suivi / robotique | [3D Feature Tracking via Event Camera, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Li_3D_Feature_Tracking_via_Event_Camera_CVPR_2024_paper.pdf), SFERA ICRA 2025, Event Guided Depth Sensing 3DV 2021 | Une cadence de dataset n'est pas une cadence de traitement ; capteurs et géométrie à inspecter |
| Autres datasets | RGBE-UAV, TUMTraf Event | Périmètre, modalités, licences et annotations à établir avant inclusion |
| Géométrie conventionnelle | [Toda et al., Chuo, document 2017](https://www.mech.chuo-u.ac.jp/umedalab/publications/pdf/2017/201709_toda_RSJ.pdf), étude IEEE IV 2013 évoquée sans notice complète | Le nom de conférence SICE/RSJ et la référence exacte doivent être résolus ; taux de 92 % retiré |

### 7.3 Thèses, ateliers et ressources exploratoires

Conserver comme pistes, **sans certifier le diplôme, le titre, l'année ou le contenu sans lecture** : [document TUM](https://mediatum.ub.tum.de/doc/1445947/1445947.pdf), [Université du Chili](https://repositorio.uchile.cl/handle/2250/206384), [thèse Lille](https://pepite-depot.univ-lille.fr/LIBRE/EDMADIS/2023/2023ULILB035.pdf), [Marcireau, notice Sorbonne](https://theses.fr/2019SORUS248), [rapport ENSTA Bretagne](https://www.ensta-bretagne.fr/jaulin/rapport_pfe_sergio_pertierre.pdf).

Les sujets TU Dortmund, EURECOM–IMRA et Edinburgh étaient cités sans lien primaire précis : références à compléter. Un sujet proposé ou une offre de thèse n'est pas une étude expérimentale achevée.

Les ateliers Event-based Vision, SIS Challenge/DIMOS, séminaire GRASP 2022 et exposé SNUFA 2021 restent des pistes. Éditions, dates, intervenants et taux d'acceptation ne sont pas certifiés par cette revue. L'appartenance d'EventHub à CVPR 2026 est documentée par les auteurs ; le détail « oral, 4,2 % » n'est pas nécessaire à notre sélection et n'a pas été revalidé.

Les listes [Awesome Deep Stereo](https://github.com/fabiotosi92/Awesome-Deep-Stereo-Matching) et [Event-based Vision Resources](https://github.com/chakravarthi589/Event-based-Vision_Resources) servent à découvrir des sources. Les conclusions techniques doivent revenir à l'article et au code des auteurs.

## 8. Exploitation concrète pour notre PFE

La contribution proposée reste une **étude expérimentale reproductible** de la séparation objet/caméra et du compromis qualité/délai. Les affirmations de lacune générale ou de nouveauté sont des hypothèses bibliographiques, pas des résultats de cette revue.

Ordre de lecture utile :

1. DSEC-MOD/MOS et nos audits M15–M17 : définir exactement ce que les références permettent de mesurer.
2. Survey stéréo et article graph cuts : expliciter profondeur, modèles de mouvement, hypothèses et limites.
3. EMatch, Temporal Event Stereo et MADNet-ε : sélectionner un candidat reproductible, puis auditer ses poids et ressources.
4. SE-CFF et l'approche SCARF–SGBM : examiner les représentations si le manque de support persiste.
5. Ev-Stereo3D : préparer l'articulation avec la partie 3D, sans remplacer l'exigence YOLO.

La prochaine expérience demeure M18, telle que définie dans [le plan courant](20_NEXT_STEPS.md). Le nombre de méthodes dans cette veille n'est pas un engagement à toutes les implémenter. Aucun nouveau score de mobilité, entraînement ou benchmark n'a été produit pendant D01.

Pour toute référence retenue ensuite, relever : version et URL, entrée réelle, future/past context, données et splits d'entraînement, capteurs auxiliaires, checkpoint/révision, format/calibration, unité des métriques, domaine valide, hardware, batch, périmètre chronométré, code de reproduction et limites.

Mots-clés conservés pour une recherche ciblée : `event stereo independent motion`, `ego-motion compensation event camera`, `DSEC-MOD`, `DSEC-MOS`, `causal event stereo latency`, `事件相机 运动目标检测`, `cámaras de eventos estéreo`, `vision neuromorphique stéréo`. La recherche multilingue élargit les pistes ; elle ne prouve pas l'exhaustivité.
