# Problèmes rencontrés et diagnostics

## DNS du terminal restreint

- Symptôme : `getaddrinfo failed` pour l'hôte officiel de téléchargement.
- Cause identifiée : accès réseau du terminal restreint ; le même accès fonctionne avec l'exécution réseau autorisée.
- Solution : transfert explicite depuis la source publique officielle avec permissions adaptées. Aucune désactivation TLS ni miroir inconnu.
- Fichier : `scripts/download_sample.py`.

## Création de venv interrompue

- Symptôme : ensurepip échoue avec PermissionError dans le répertoire temporaire du sandbox.
- Diagnostic : le traceback désigne la copie de la wheel pip dans ce dossier, pas une incompatibilité Python.
- Solution appliquée : relancer création/installation avec droits d'exécution adaptés ; imports h5py/hdf5plugin/NumPy/Pillow/PyYAML ensuite vérifiés.
- Important : aucune conclusion négative sur Python 3.14 n'a été tirée de cette erreur de permission.

## Coupure pendant le premier flux gauche

- Symptôme : TimeoutError après téléchargement partiel.
- Solution : conservation du `.part`, reprise HTTP Range validée, nombre de tentatives borné, erreur explicite si épuisées. Le transfert et l'extraction suivants ont réussi.
- Limite : si le serveur renvoie 200 au lieu de 206, le partiel est recommencé ; aucune concaténation incorrecte.

## Labels téléchargés mais introuvables

- Diagnostic : l'archive officielle des annotations contient deux autres ZIP train/test.
- Solution : extraire également l'archive train et conserver la structure originale.
- Deuxième diagnostic : rechercher le nom de séquence dans le chemin absolu sélectionnait toutes les annotations, car le dossier parent de données portait déjà ce nom.
- Correction : recherche dans le chemin relatif à la racine des annotations ; huit boîtes au timestamp inspecté ont ensuite été trouvées.
- Fichiers : `scripts/download_sample.py`, `scripts/inspect_sample.py`.

## Aucun piéton dans l'échantillon

Ce n'est pas une erreur du modèle : aucun modèle n'a tourné. Le comptage des annotations de `zurich_city_04_e` donne zéro `pedestrian`. Garder cette séquence pour géométrie/débogage ; sélectionner d'autres séquences annotées avant la phase de détection. Ne pas changer le mapping des classes pour produire artificiellement des personnes.

## Grille de trous après rectification

Le rendu direct arrondit les coordonnées fractionnaires et peut créer des trous structurés lorsque l'image est dilatée. Il ne s'agit pas de lignes épipolaires dessinées. Ce choix est acceptable pour la première inspection, mais le prétraitement réseau devra employer la stratégie d'interpolation compatible avec son entraînement. Ne pas lisser sans quantifier l'effet sur correspondances et comptages.

## À diagnostiquer seulement si rencontré

Erreur filtre HDF5 : vérifier `import hdf5plugin` avant ouverture. Profondeurs 16× ou 256× trop grandes : contrôler la convention de disparité de chaque adaptateur. Boîtes décalées : vérifier vue native/rectifiée, letterbox et timestamp avant de conclure que YOLO est mauvais. Ces trois cas sont des aides futures, pas des incidents observés aujourd'hui.


## M07 : segment demandé plus long que le fichier local

- Problème observé : le lancement initial sur 20 secondes lève `Sequence too short or warm-up not divisible by step`.
- Cause vérifiée : les deux HDF5 train couvrent chacun environ 13,401 secondes. L’échauffement était divisible ; la durée disponible était insuffisante.
- Solution : protocole révisé avant mesure sur 12 secondes centrales avec 200 ms d’échauffement précédent ; contrôle préalable de durée dans le lanceur.
- Traçabilité : échec initial conservé dans `outputs/motion/M07`, expérience complète dans `outputs/motion/M07_12s`. Aucun événement mesuré lors de l’essai initial.
- Fichier : `scripts/benchmark_paced_motion.py`.
