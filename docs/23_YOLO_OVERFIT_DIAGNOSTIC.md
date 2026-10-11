# Premier entraînement YOLO : arrêt du diagnostic et nouvel essai

**Mise à jour du 4 octobre 2026 :** le nouvel essai a été exécuté et réussit : AP50=0,995 pour chaque classe, 200 pas d'optimisation mesurés. Le pilote de cinq époques a ensuite terminé, avec mAP50=0,2373 sur `thun_00_a`. Les poids/CSV/figures sont récupérés et audités. [Bilan actuel](24_Y01_COLAB_RESULTS.md). Les sections suivantes conservent le diagnostic et les instructions élaborés après le premier journal, avant réception des archives ; il n'est pas nécessaire de relancer cet essai réussi.

## Preuve initiale reçue — historique du 3 octobre

L'utilisateur a transmis le journal Colab de la session `Y01_20261003T191753Z`. Il indique 50 époques terminées sur Tesla T4, Ultralytics 8.4.172, Python 3.13.15, PyTorch 2.11.0+cu130. Les poids best/last ont été sauvés et l'optimiseur retiré après la fin normale de l'entraînement. L'AssertionError intervient ensuite, lors du contrôle de qualité. Ce n'est pas une erreur CUDA ni une interruption des 50 époques.

Les fichiers distants `args.yaml`, `results.csv`, checkpoints et images de prédictions n'ont pas été récupérés localement. Les chiffres ci-dessous sont **transcrits du journal fourni**, pas issus d'une réévaluation locale des poids. Voir `outputs/reports/Y01_overfit_v1_user_log.json`.

| Classe | Images avec classe | Instances | Précision rapportée | Rappel | AP50 | AP50–95 |
|---|---:|---:|---:|---:|---:|---:|
| person | 3 | 10 | 0,00345 | 0,800 | 0,307 | 0,274 |
| car | 8 | 39 | 0,410 | 0,821 | 0,806 | 0,684 |
| ensemble | 8 images au total | 49 | 0,207 | 0,810 | 0,556 | 0,479 |

Le garde-fou impose AP50≥0,80 **pour chaque classe**. Voiture passe de peu ; personne échoue. Le programme s'arrête donc avant le pilote complet. Une AP50 de 0,307 ne signifie pas « 30,7 % des objets reconnus » : c'est une intégrale de précision/rappel à IoU 0,5. Les mêmes huit images sont utilisées pour apprendre et évaluer ce diagnostic ; aucun score de généralisation n'est disponible.

Les deux temps d'inférence affichés diffèrent entre validations (6,4 et 27,1 ms/image). Ils ne doivent pas être transformés en promesse de FPS pour le pipeline événementiel complet.

## Diagnostic établi à partir du code et du lot local

Le lot contient exactement les dix piétons et trente-neuf voitures du journal. Les piétons apparaissent dans trois images seulement ; leurs largeurs vont de 7 à 16 pixels et hauteurs de 15 à 45 pixels. Le déséquilibre et la petite taille compliquent le diagnostic, sans prouver à eux seuls la cause de l'échec.

La configuration initiale omettait `nbs`, dont la valeur par défaut dans la distribution auditée est 64. Avec huit images et batch=4, il n'y a que deux minibatches par époque. L'accumulation des gradients réduit fortement le nombre de mises à jour des poids : 50 époques ne représentent pas nécessairement 100 pas d'optimisation.

Le code **de la version 8.4.172 téléchargée** a été relu : warm-up d'une époque = deux minibatches ; interpolation de l'accumulation, puis conservation de sa valeur après warm-up. Une simulation avec la configuration fournie donne **13 appels théoriques de l'optimiseur**, aux indices 0,8,…,96. Ce nombre est une déduction du code et des réglages attendus, pas un compteur observé dans le runtime distant. Le fichier `args.yaml` doit confirmer les paramètres effectifs. Il ne faut pas reprendre une explication basée sur un ancien minimum de warm-up à 100 itérations : cette version utilise une autre règle.

L'omission de l'accumulation est un défaut du protocole de petit lot fourni. Le taux d'apprentissage décroît aussi rapidement au cours de ce faible nombre de mises à jour. Ces éléments motivent un essai corrigé, sans garantir qu'ils expliquent toute l'erreur piéton. Les courbes et faux positifs restent à examiner.

## Essai corrigé préparé après l'échec — désormais exécuté

Conserver le **même lot**, les mêmes images 640×480, la même représentation, le même checkpoint COCO initial et le même seuil AP50 de 0,80. Ne pas changer simultanément le dataset pour masquer l'effet de l'optimisation.

Réglages du diagnostic : 100 époques, batch=4, **nbs=4**, warmup_epochs=0, lr0=0,001, lrf=1, weight_decay=0. Les augmentations restent désactivées. Cela prévoit 200 mises à jour sur deux minibatches par époque, hors incident/reprise. Le nouveau code compte les **vrais pas de l'optimiseur** par hook. Ces paramètres servent à mémoriser un petit lot ; ils ne sont pas automatiquement transférés au pilote complet.

La décroissance du LR et la régularisation sont retirées pour ce test de mémorisation. La correction ne consiste pas à abaisser le seuil, forcer `OVERFIT_PASSED=True` ou sélectionner un sous-ensemble plus facile après observation du score.

## Dans la session Colab encore ouverte

Téléverser `notebooks/Y01_retry_overfit_cell.py` puis l'exécuter **dans une nouvelle cellule après celle qui a échoué**, en conservant le runtime et ses variables :

```python
from google.colab import files
uploaded = files.upload()  # choisir Y01_retry_overfit_cell.py
exec(compile(uploaded["Y01_retry_overfit_cell.py"], "retry_overfit", "exec"))
```

Le fichier peut aussi être copié intégralement dans une nouvelle cellule. Il affiche la configuration précédente et les cinq dernières lignes de pertes/métriques si présentes, puis crée `overfit_retry_<date UTC>/` sous la session. L'essai raté et son rapport ne sont pas écrasés. Les nouveaux poids, métriques, compteur et prédictions visuelles (confidence 0,25, distincte du seuil d'évaluation) sont conservés dans ce nouveau dossier.

Le fichier repart des poids initiaux ; il n'utilise pas `resume=True` sur le checkpoint d'un entraînement terminé dont l'optimiseur a été retiré. Si le diagnostic passe, `OVERFIT_PASSED` est mis à True après le contrôle et la cellule 7 du notebook original peut être exécutée. Sinon il reste False et le pilote doit rester arrêté. Examiner les sorties avant de changer encore les paramètres.

Si le runtime est perdu, utiliser le notebook principal actualisé depuis la préparation. La version initiale est conservée localement dans `notebooks/archive/Y01_yolo11n_events_pilot_v1.ipynb`, hors Git depuis le nettoyage du 11 octobre. Il n'est pas nécessaire de régénérer ou transférer une nouvelle archive de données : le ZIP Y00 est inchangé.

## Vérifications et statut

Cellule de reprise et sept cellules du notebook révisé compilées localement. Les affectations réelles de configuration ont été exécutées sans GPU pour vérifier que `nbs=4` et les réglages du diagnostic n'altèrent pas `COMMON` utilisé par le pilote. Le seuil reste 0,80, le budget pilote cinq époques. Rapport : `outputs/reports/Y01_retry_preparation.json`.

À la préparation de cette correction, le premier surapprentissage était exécuté avec seuil non atteint, tandis que le nouvel essai et le pilote n'étaient pas encore attestés. Les archives reçues depuis confirment leur exécution : diagnostic corrigé réussi, pilote terminé avec validation faible. Fusion profondeur/objets et mouvement : toujours à réaliser.
