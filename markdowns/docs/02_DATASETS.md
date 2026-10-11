# Choix des données

Sources officielles consultées le 3 octobre 2026. « À vérifier » signifie qu'une propriété n'a pas été établie ; l'absence de vérification n'est pas une preuve d'absence. Les recommandations Colab ci-dessous sont notre appréciation d'ingénierie, pas des benchmarks.

## Comparaison fonctionnelle

| Dataset | Stéréo événementielle | Référence géométrique | Objets / YOLO | Choix |
|---|---|---|---|---|
| DSEC + DSEC-Detection | Deux capteurs événementiels 640×480 | Disparités référencées à gauche, calibration et synchronisation | Extension avec piétons, voitures et autres classes routières | Principal |
| MVSEC | Paire DAVIS 346×260 | Profondeur/poses, calibration ; formats HDF5 et ROS | Pas de boîtes d'objets documentées sur les pages de base consultées | Secondaire, géométrie seulement |
| M3ED | Deux capteurs HD 1280×720 | Profondeur et poses, capteurs multiples | Scènes urbaines, forêt et plateformes diverses ; extensions récentes distinctes | Réserve après MVP |
| EventScape / RAM-Net | Paire stéréo exploitable non établie dans la distribution consultée, orientée profondeur monoculaire | Profondeur synthétique CARLA | Une scène simulée ne garantit pas des boîtes prêtes à entraîner YOLO | Écarté du chemin stéréo |
| Prophesee Gen1 | Monoculaire, donc insuffisant pour notre stéréo | Pas de référence stéréo dans cette tâche | Voitures et piétons annotés manuellement | Préentraînement détection facultatif |

Sources par ligne : [DSEC](https://dsec.ifi.uzh.ch/), [DSEC-Detection](https://dsec.ifi.uzh.ch/dsec-detection/), [MVSEC](https://daniilidis-group.github.io/mvsec/), [M3ED](https://m3ed.io/), [RAM-Net/EventScape](https://github.com/uzh-rpg/rpg_ramnet), [Gen1](https://www.prophesee.ai/2020/01/24/prophesee-gen1-automotive-detection-dataset/).

## Coût d'accès, documentation et licences

| Dataset | Formats / accès | Volume vérifié ou limite de connaissance | Usage local / Colab | Licence annoncée |
|---|---|---|---|---|
| DSEC | HDF5, PNG, YAML, TXT ; téléchargement par séquence et modalité | Échantillon `zurich_city_04_e` : 261 + 227 Mo événements, 18 Mo disparité selon catalogue ; calibration très petite | Lecture par fenêtres ; une séquence d'abord, pas de copie totale en RAM | Données CC BY-SA 4.0 ; outils DSEC MIT ; dsec-det GPL-3.0 |
| MVSEC | HDF5 direct ou ROS bags ; miroir Google Drive | Certaines archives ROS atteignent 27 Go ; taille HDF5 choisie à vérifier | HDF5 pour éviter ROS sur Windows ; petit extrait sur Colab | Données CC BY-SA 4.0 |
| M3ED | HDF5 avec calibration et index temporels ; fichiers de GT séparés | Total non audité ; le sous-ensemble EventHub décrit déjà ~150 Go bruts | Recadrage/sous-ensemble impératif ; plus de mémoire et d'E/S | Données CC BY-SA 4.0 |
| EventScape | Archives du dépôt RAM-Net, données synthétiques | Archives annoncées 71/12/14 Gb pour train/val/test ; vérifier octets avant récupération | Trop volumineux pour une simple exploration locale | Licence des données non clarifiée par la page consultée ; ne pas déduire celle des données de celle du code |
| Gen1 | `.dat` et annotations `.npy`, découpages documentés | 39 h annoncées ; octets à vérifier avant usage | Étape de conversion en plus, seulement si DSEC détection insuffisant | Conditions de distribution à consulter avant acquisition |

Références opérationnelles : [catalogue DSEC](https://dsec.ifi.uzh.ch/dsec-datasets/download/), [MVSEC téléchargement](https://daniilidis-group.github.io/mvsec/download/), [M3ED fichiers](https://m3ed.io/data_overview/datafiles/), [EventHub](https://github.com/bartn8/eventhub). Licences de données, de code et de poids seront enregistrées séparément ; cette note ne remplace pas leurs textes.

## Pourquoi DSEC, concrètement

Le facteur déterminant est la possibilité de travailler sur une même famille de scènes pour la stéréo et la détection. Les boîtes DSEC-Detection proviennent d'un suivi sur images, transféré vers les événements puis corrigé pour retirer de fausses pistes : ce ne sont pas des annotations parfaites de tout objet visible. L'extension comporte huit classes routières ; « objets génériques » signifie ici classes annotées, pas tout objet arbitraire. Le mapping de classe devra être testé.

Le dataset complet comporte des séquences supplémentaires de détection. Leur présence ne prouve pas la disponibilité conjointe de droite + GT disparité. Construire un manifeste d'intersection par séquence et timestamp. Les partitions de détection et de disparité répondent à des tâches différentes : ne pas les fusionner sans vérifier leur compatibilité. Les régions sans annotation ne deviennent pas automatiquement des exemples négatifs fiables.

## Repères : risque prioritaire

Les boîtes de `tracks.npy` sont dans la vue événementielle gauche déformée, d'après le [dépôt officiel dsec-det](https://github.com/uzh-rpg/dsec-det). Choix projet : YOLO travaille d'abord dans ce repère natif. Pour chaque pixel de sa ROI, appliquer la carte de rectification et échantillonner la disparité dans la vue rectifiée. Éviter de transformer seulement deux coins d'une boîte : une rectification non linéaire ne préserve pas les rectangles. Ce choix préserve les labels natifs et évite de créer prématurément de nouvelles annotations approximatives.

## Premier échantillon et partitions

`zurich_city_04_e` appartient au train officiel de détection : adapté au débogage, pas à une mesure finale de généralisation. Le script borné `scripts/download_sample.py` récupère seulement les modalités choisies. Il conserve les archives, extrait dans des sous-dossiers et enregistre les octets et SHA256 calculés localement. Le CRC ZIP contrôle l'intégrité d'extraction ; un hash local n'est pas une signature de l'auteur.

Après ce pilote, inventorier personnes/voitures, jour/nuit, plages communes et profondeur disponible. Puis séparer des **trajets complets** : les suffixes `04_a`…`04_f` appartiennent à un même groupe potentiel et ne doivent pas être répartis aléatoirement. Pour le protocole de profondeur local, réserver des groupes du train officiel qui possèdent la GT ; ne pas inventer une GT de test officiel absente. Vérifier aussi les séquences utilisées pour entraîner un checkpoint externe avant de qualifier un test d'indépendant.

## Pilote figé pour S01 — 2026-10-03

Le manifeste exécutable est `configs/pilot.json`. Les candidates `00_a/00_b/01_b` restent pertinentes pour agrandir ultérieurement le corpus. Pour ce pilote CPU, le catalogue et l'inventaire ont permis de retenir des séquences plus légères avec piétons, afin de limiter téléchargement et stockage.

| Séquence | Groupe | Partition locale | Instances pedestrian / car | Octets téléchargés |
|---|---|---|---|---|
| `zurich_city_04_e` | `zurich_city_04` | train/debug | 0 / 1 614 | 536 897 112, labels globaux inclus |
| `zurich_city_04_b` | `zurich_city_04` | train | 921 / 877 | 565 657 460 |
| `thun_00_a` | `thun_00` | validation pilote | 239 / 673 | 590 818 770 |
| `zurich_city_09_b` | `zurich_city_09` | test réservé | inventaire consulté seulement | non téléchargée |

Ces nombres d'annotations comptent des boîtes sur plusieurs dates, pas des objets distincts. Les flux gauche/droite, cartes de rectification, calibration et disparités sont effectivement disponibles pour les trois séquences acquises. Les labels sont réutilisés depuis l'archive commune déjà extraite sous `04_e`, sans duplication. Le volume total sur disque de `data/raw`, archives comprises, est **3 421 637 725 octets**, soit environ 3,19 Gio au relevé S01.

Les partitions sont **locales**, à l'intérieur des séquences train DSEC ; ce n'est pas le protocole officiel de compétition. Toutes les subdivisions du groupe `04` restent côté train. Le chargeur rejette tout groupe présent dans deux partitions. Une seule petite séquence de validation ne représente pas la diversité des trajets, saisons ou éclairages. Le test réservé n'a été ni affiché ni évalué ; seul son inventaire de labels a servi à la sélection du corpus. Tout checkpoint externe devra encore être audité avant de qualifier ce test d'indépendant.

Provenance : [catalogue officiel](https://dsec.ifi.uzh.ch/dsec-datasets/download/) et manifests locaux `downloads.json`, reproduits dans le rapport S01. Les empreintes sont locales ; elles ne constituent pas des signatures publiées par DSEC.

## Validation secondaire envisagée

MVSEC peut tester la portabilité de la géométrie et la chute de performance inter-dataset, sans prétendre mesurer YOLO sans annotations. M3ED devient pertinent si le temps le permet pour les mouvements plus agressifs. EventScape n'est pas retenu comme preuve de stéréo réelle.
