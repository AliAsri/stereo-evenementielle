# Détection d’objets mobiles par stéréo événementielle

PFE de Master : distinguer le mouvement des objets de celui de la caméra, puis associer une classe YOLO et des coordonnées 3D lorsque les données le permettent.

## Contenu du dépôt et démarrage

[Dépôt public GitHub](https://github.com/AliAsri/pfe-stereo-evenementielle).

Le dépôt contient le code, les tests, les configurations, les notebooks, les documents techniques et leur copie dans `markdowns/`. Les neuf programmes de diagnostic placés directement dans `outputs/focused_truck/` sont également versionnés. Les environnements Python, données DSEC, poids YOLO, archives et résultats générés restent locaux. Les liens vers `data/` et les résultats sous `outputs/` nécessitent donc les artefacts locaux ; cloner ce dépôt ne télécharge pas la démonstration ni les données.

Configuration vérifiée sous Windows avec Python 3.14.6. Depuis la racine, dans PowerShell :

```powershell
git clone https://github.com/AliAsri/pfe-stereo-evenementielle.git
cd pfe-stereo-evenementielle
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-inspection-lock.txt
.\.venv\Scripts\python.exe scripts/check_project.py --output outputs/checks/initial
```

Le dossier passé à `--output` doit être neuf. Ces contrôles n'exigent ni téléchargement DSEC ni entraînement YOLO. L'inférence complète utilise un environnement distinct, créé avec `.venv-demo` et `requirements-demo-lock.txt`, ainsi que les données et poids déjà préparés : son exécution n'est pas autonome après un simple clonage. Les étapes historiques de préparation sont documentées dans `docs/` ; ne pas relancer tous les scripts indistinctement.

Les illustrations événementielles dans `docs/assets/reunion_simple/` sont issues de DSEC et de nos traitements. Source : [DSEC, Université de Zurich / ETH Zurich](https://dsec.ifi.uzh.ch/), données sous [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Cette attribution concerne ces données et illustrations dérivées.

**Décision du 10 octobre 2026 : simplifier.** Un extrait DSEC, une configuration existante, un affichage compréhensible. EMatch, les nouveaux datasets et les optimisations supplémentaires sont en pause. Les résultats antérieurs sont conservés.

**11 octobre : audit global terminé, nouvelles étapes en pause.** 215 tests passent ; le rejeu complet reproduit exactement les 153 tableaux précédents et les résultats scientifiques des 17 images. Quatre défauts de robustesse ou d'affichage ont été corrigés. [Bilan, périmètre et limites](docs/20_NEXT_STEPS.md#audit-global-r02--11-octobre-2026).

## Où nous en sommes

Un affichage commun réunit YOLO, la profondeur stéréo, les coordonnées XYZ disponibles et les indices de mouvement, tous recalculés depuis les événements. Sur 17 images : 77 détections cumulées, 45 estimations de surface 3D et 32 abstentions, identiques aux résultats précédents. Le calcul CPU médian prend 1,05 s par sortie, hors rendu/export, pour un pas source de 20 ms : cette démonstration reste hors ligne. Le mouvement indépendant reste non confirmé. Un lecteur interactif permet maintenant d'examiner ces résultats image par image, de sélectionner les détections et d'inspecter les résidus.

**[Page active : résultat, décision et prochaine action](docs/20_NEXT_STEPS.md)**

[Voir la démonstration recalculée au ralenti](outputs/focused_truck/integrated_03/clip.gif) · [Image finale](outputs/focused_truck/integrated_03/preview.png)

**[Lecteur interactif autonome](outputs/focused_truck/viewer_04/index.html)** : ouvrir le fichier dans un navigateur ; pause, navigation et inspection disponibles sans serveur ni installation. La sensibilité à une hypothèse de pose est affichée pour chaque date, avec le pourcentage et les effectifs ; la première image indique une comparaison indisponible. Le bouton **« Comparer les poses · image 8 »** conserve les deux vues détaillées et le filtre des 67 statuts modifiés. Données et logique des interactions vérifiées ; le rendu dans un navigateur reste à vérifier, l'accès automatisé aux fichiers locaux ayant été bloqué.

Les cadres orange regroupent les points résiduels, indépendamment de YOLO : 22 occurrences de zones sur 17 images, dont 12 sans point partagé avec les boîtes YOLO. Ce ne sont pas des objets mobiles confirmés. La comparaison de poses est un diagnostic distinct ; elle ne remplace aucun résultat enregistré.

[Trois points expliqués en image](outputs/focused_truck/inspection_01/comparison.png) : comprendre pourquoi un déplacement important peut rester compatible avec le modèle et pourquoi un résidu peut apparaître sur le décor.

[Stabilité des zones sur les 17 images](outputs/focused_truck/stability_01/comparison.png) : les zones sont récurrentes, mais leur localisation varie. Le recouvrement des cadres entre images descend à 3,4 % ; leur répétition ne suffit pas à confirmer un objet mobile.

[Pourquoi les alertes changent de côté](outputs/focused_truck/pose_switch_01/comparison.png) : sur les mêmes données de l'image 8, remplacer uniquement sa pose par la précédente change le statut de 67 points sur 255. Ce contrôle montre la sensibilité à la pose, sans déterminer laquelle est correcte ni remplacer les résultats du détecteur.

[Sensibilité sur les 16 transitions](outputs/focused_truck/clip_sensitivity_01/comparison.png) : le cas 7 → 8 n'est pas isolé. Huit transitions changent le statut de 26,3 à 30,7 % des points évalués ; les huit autres, de 0,4 à 5,4 %. Ces plages décrivent cet extrait et ne constituent pas des seuils validés de qualité ou de mobilité.

[Où le support de pose se redistribue](outputs/focused_truck/pose_support_01/comparison.png) : sur les mêmes points de l'image 3, T3 gagne 48 points de support surtout à gauche et en perd 45 surtout à droite. Le gain net de trois points masque 93 changements d'appartenance au support ; il ne désigne pas la bonne pose caméra.

## Repères utiles

- [Cahier des charges](docs/PROJECT_BRIEF.md) et [consignes persistantes](AGENTS.md).
- [Guide du code et de maintenance](docs/44_PROJECT_MAINTENANCE.md).
- [Historique des expériences](docs/19_PROGRESS.md) et [décisions antérieures](docs/DECISIONS.md) : archives de travail, à lire au besoin.
- Code dans `src/pfe_events/`, commandes dans `scripts/`, résultats dans `outputs/`.
- Environnement local existant : `.venv`; apprentissage YOLO sur Colab. Aucune annotation manuelle demandée.

Après modification des documents : `.\.venv\Scripts\python.exe scripts/sync_markdowns.py`. Les copies sont conservées dans `markdowns/` avec les mêmes chemins relatifs.
