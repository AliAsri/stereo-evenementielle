# Plan d'apprentissage et exécution Colab

**Résultats reçus le 4 octobre 2026 :** après l'échec initial, le diagnostic révisé atteint AP50=0,995 par classe avec 200 pas d'optimisation. Il utilise 100 époques, nbs=4 pour batch=4, warmup=0, lr0=0,001 constant, weight_decay=0. Le pilote conserve ses propres réglages et termine cinq époques : mAP50=0,2373 sur validation. [Analyse et limites](24_Y01_COLAB_RESULTS.md).

## Environnements

Le lecteur CPU initial est testé avec Python 3.14.6 sous Windows ; le fichier verrouillé décrit uniquement cet environnement. La pile GPU sera isolée et choisie à partir du runtime Colab réel. Ne pas remplacer le pilote CUDA de Colab pour copier aveuglément une recette de 2022. Relever Python, torch, torchvision, version CUDA visible, GPU et VRAM avant de choisir un checkpoint.

## Premier entraînement YOLO

Préconditions : manifeste par séquence, labels superposés correctement, mapping de classes testé, représentation et normalisation figées, contrôle de fuite train/validation/test. Initialiser un YOLO11n depuis les poids officiels, modifier les classes et affiner sur event frames. Le préentraînement RGB n'est qu'une initialisation. On compare aussi une inférence sans adaptation pour objectiver le besoin d'entraînement.

Configuration pilote Y01 exécutée : seed 42, letterbox 640×640 à partir de 640×480, batch 4, nbs=64, workers 2, AdamW, lr0=0,001, lrf=0,01, momentum=0,9, weight_decay=0,0005, warmup 1 époque. Le premier diagnostic de 50 époques a échoué ; le diagnostic corrigé décrit ci-dessus passe avant les cinq époques sur le pilote complet, qui repart des poids initiaux. Le garde-fou AP50≥0,80 par classe est un contrôle de mémorisation, pas de généralisation. Augmentations et AMP désactivés. Une nouvelle expérience de 30 époques est proposée ; elle n'est pas lancée.

Désactiver les augmentations colorimétriques et valider les transformations spatiales. Les augmentations de temporalité doivent reconstruire événements et labels de manière cohérente. Ne jamais régler le modèle sur le test final. Sauvegarder `best`, `last`, configuration, mapping de classes, partitions et logs après chaque session.

## Stéréo profonde

Audit d'EMatch en inférence, pas entraînement de toute l'architecture immédiatement. Le préprint v2 utilise 15 bins/100 ms et décrit 400k puis 150k itérations ; cette recette constitue un coût très différent d'un petit fine-tuning YOLO. Respecter la configuration associée aux poids choisis. [Article EMatch v2](https://arxiv.org/html/2407.21735v2).

Limiter l'apprentissage stéréo à une adaptation documentée si le checkpoint est fonctionnel, la mémoire suffisante et la baseline déjà acquise. Modifier la fenêtre de 100 à 20 ms au test ne constitue pas une comparaison contrôlée. Fixer au plus deux candidats, pas une recherche d'architecture ouverte.

## Procédure Colab pour les prochaines exécutions

1. Vérifier runtime et matériel, refuser de lancer un entraînement lourd sans GPU.
2. Installer versions validées et vérifier imports.
3. Copier le sous-ensemble nécessaire depuis le stockage vers `/content` pour limiter les petites lectures distantes.
4. Charger manifeste, vérifier hashes, montrer un lot et ses annotations.
5. Charger poids, exécuter une inférence, puis un pas d'entraînement et une validation courte.
6. Lancer l'expérience avec reprise, checkpoints fréquents et métriques exportées.
7. Sauvegarder vers le stockage persistant et vérifier que les fichiers s'y trouvent avant de fermer.

Le notebook est `notebooks/Y01_yolo11n_events_pilot.ipynb`, généré par `scripts/build_yolo_notebook.py` à partir du hash de l'export vérifié. Ses 16 cellules sont présentes ; les sept cellules de code compilent localement. Ultralytics 8.4.172 est figé, PyTorch/CUDA sont ceux du runtime et leurs versions seront enregistrées. Le notebook écrit directement les journaux et checkpoints dans une nouvelle session Drive. [Mode d'emploi complet](22_YOLO_EXPORT_COLAB.md).

L'exécution GPU par l'utilisateur et les contrôles des vrais tenseurs sont attestés par les archives Y01 ; l'assistant les a importées et auditées sans relancer le modèle localement. Le témoin quantitatif COCO non adapté n'est pas inclus dans ce premier notebook ; il demandera une évaluation avec remapping explicite des classes.
