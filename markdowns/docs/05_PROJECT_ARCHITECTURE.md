# Architecture proposée et contrats

## Priorité de mobilité — 7 octobre 2026

La branche rapide doit évoluer de l’activité vers des propositions d’objets mobiles : suivi temporel des structures, modèle du déplacement apparent du décor, résidus et cohérence temporelle, avec abstention en cas d’ambiguïté. M03 fournit la référence globale ; M10 ajoute des candidats cohérents et persistants, exécutés sur train mais sans validation du mouvement indépendant. YOLO pourra ajouter une classe et la stéréo une profondeur, sans décider seuls qu’un objet bouge. [Contrats et évaluation](38_OBJECTIF_OBJETS_MOBILES.md).

## Principe

Une application Python locale et des expériences GPU Colab. Priorité au 4 octobre 2026 : une branche d'activité native à fenêtres courtes, indépendante de YOLO et de la stéréo. Ces deux branches complètent ensuite le résultat par une classe et une profondeur. Leurs fenêtres et cadences peuvent différer ; leurs sorties gardent un timestamp et un âge explicites. Le diagramme décrit la cible ; M01 réalise déjà la branche d'activité, sans association sémantique ni compensation de caméra.

```mermaid
flowchart TD
    A[DSEC gauche et droite] --> B[Lecture par fenetre causale commune]
    B --> C[Evenements natifs gauche]
    B --> D[Rectification gauche et droite]
    C --> E[Pseudo-image native]
    E --> F[YOLO adapte aux evenements]
    D --> G[Representation stereo]
    G --> H[SGBM puis candidat stereo profond]
    H --> I[Disparite rectifiee et validite]
    F --> J[ROI native et mapping de ses pixels]
    I --> K[Association robuste et reprojection Q]
    J --> K
    A --> L[Activite native causale 10 ou 20 ms]
    K --> M[Visualisation, JSON, metriques]
    L --> O[Zones actives disponibles sans attendre YOLO]
    O --> M
    C --> P[Correspondances temporelles et modele du decor]
    P --> R[Residus locaux et coherence temporelle - M10 candidats]
    R --> S[Candidats mobiles avec statut et incertitude]
    S --> M
    N[GT et annotations] -. evaluation uniquement .-> M
```

Les adaptations à la chaîne initiale du cahier des charges sont motivées : branches sémantique/géométrie indépendantes ; préservation des annotations natives ; chemin d'activité léger mis à jour plus souvent que les réseaux. La GT ne traverse jamais la branche d'inférence.

## Structure progressive

`src/pfe_events/` accueille les fonctions réutilisables, d'abord lecteur et représentations. Au fur et à mesure : `stereo.py`, `geometry.py`, `detection.py`, `fusion.py`, `motion.py`. Scinder un module uniquement lorsqu'il devient difficile à lire. `scripts/` fournit les commandes, `tests/` les cas à risque, `docs/` les notes. `data/raw` garde les originaux ; `data/processed` les exports reproductibles. `outputs/` contient rapports et visualisations. `models/` et `notebooks/` seront créés lors de leur première utilisation.

Cette organisation a moins de sous-dossiers que la suggestion initiale ; les fonctions restent localisables sans couches d'abstraction.

## Interfaces cibles

| Objet | Champs essentiels | Invariant |
|---|---|---|
| Fenêtre | `x,y,t_us,p,start_us,end_us,view` | Même unité temporelle, borne droite exclusive |
| Représentation | tenseur, ordre des canaux, normalisation, résolution, vue | Toute transformation est traçable |
| Disparité | `d_px`, masque valide, `timestamp_us`, calibration_id | Repère gauche rectifié, bonne unité |
| Détection | classe, score, `xyxy`, vue, temps | Coordonnées remises à l'échelle après letterbox |
| Objet 3D | point XYZ, repère, support, dispersion, statut | Pas de coordonnées si support insuffisant |
| Mesure | durée de chaque étape, mémoire, matériel, cadence | Distinguer temps dataset et temps horloge |

La stéréo peut retourner une carte partiellement invalide. Une absence de détection est un résultat valide. Un fichier absent ou une calibration incohérente est une erreur qui doit arrêter la commande ; elle ne doit pas devenir une carte de zéros silencieuse.

## Dépendances et environnements

Socle CPU installé : NumPy, h5py, hdf5plugin, PyYAML, Pillow et OpenCV headless pour S01. `stereo.py`, `geometry.py`, `representations.py`, `dsec.py` et `pilot.py` sont présents. DL : PyTorch + Ultralytics, à installer dans un environnement GPU séparé. L'environnement de lecture Python 3.14 ne prouve pas la compatibilité des anciens dépôts scientifiques ; ne pas y installer arbitrairement leur pile CUDA. Choisir le runtime Colab et verrouiller les versions après un premier test d'inférence.

## Démonstrateur final

Panneaux : événements gauche/droite, boîtes dans la vue native, disparité prédite avec masque, tableau XYZ/statut et performances. Marquer clairement `GT — diagnostic` si une carte de référence est affichée. En lecture d'une prédiction précalculée, afficher `REJEU DE PRÉDICTIONS`. Pas d'interface web complexe requise : fenêtre OpenCV ou vidéo annotée plus panneau de mesures conviennent.


## État de la branche objets mobiles après M10

Le filtre de cohérence et de persistance est maintenant exécuté sur train, en aval des correspondances et du modèle global M03. Il utilise le lecteur M08 et retourne des candidats explicitement incertains. La profondeur, la pose et YOLO n'entrent pas encore dans cette décision. La compensation géométrique et la référence de mobilité restent à construire : la parallaxe et la rotation locale exposent des limites observées. [Bilan M10](39_M10_MOBILE_CANDIDATES.md).


## M11 : géométrie implémentée, intégration réelle en préparation

La branche géométrique dispose d'un estimateur robuste du modèle rigide dominant à partir de points rectifiés suivis et de leur profondeur au premier instant. Il fournit résidus et abstention, sans dépendre d'une boîte YOLO. Les tests M11 utilisent une profondeur synthétique de référence explicitement oracle ; aucun résultat réel de mouvement indépendant n'est encore validé. Le raccord aux profondeurs S01 prédites et aux correspondances rectifiées reste la prochaine étape. [Bilan M11](40_M11_RIGID_MOTION.md).


## M12 : raccord aux données réelles exécuté

Événements gauches → splat rectifié/normalisation S01 → correspondances LK → profondeur prédite S01 aux points précédents → modèle rigide M11 → résidus/abstention. Ce chemin est exécuté sur 38 paires train, sans pose ou profondeur GT. Il ne comporte pas encore de persistance continue, de regroupement en objets ni de validation réelle de mobilité. Les cadences asynchrones restent une cible : ce diagnostic avec profondeur en cache coûte 321–385 ms médians par paire. [Preuves M12](41_M12_REAL_RIGID_MOTION.md).
