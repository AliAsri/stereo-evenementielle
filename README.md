# Détection d’objets mobiles par stéréo événementielle

Objectif : distinguer le mouvement d’un objet de celui de la caméra, lui associer une classe et estimer une surface 3D lorsque les données le permettent. **Priorités : rapidité, détection fiable, puis 3D.** Cible confirmée : démonstration sur le PC actuel, avec le parcours CPU existant ; Colab reste disponible pour l’entraînement.

**État au 19 octobre 2026 : prototype intégré sur données DSEC enregistrées.** Le temps réel et la détection fiable du mouvement indépendant restent à démontrer. [État actuel et prochaines étapes](docs/20_NEXT_STEPS.md) · [Audit technique et scientifique](docs/AUDIT_TECHNIQUE_SCIENTIFIQUE_18_OCTOBRE_2026.md) · [Historique depuis le début](docs/19_PROGRESS.md).

La [préparation de validation du 19 octobre](docs/38_OBJECTIF_OBJETS_MOBILES.md#validation-indépendante-proposée--19-octobre-2026) propose deux nouveaux enregistrements publics, mobile et rigide, pour contrôler la compensation avec profondeur oracle. Leur acquisition bornée a atteint le plafond de 512 Mio sans obtenir les fichiers cibles ; ces nouvelles références restent non qualifiées, sans résultat de qualité. ORB a été testé puis écarté, sans intégration DSEC.

## Un parcours principal

Depuis la racine, sur le poste où les données et l’environnement sont préparés :

```powershell
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --output outputs/demo_repeat
```

Choisir un dossier neuf, puis ouvrir `outputs/demo_repeat/clip.gif`. **Le mouvement est prioritaire :** ses indices sont calculés à chaque date source (pas 20 ms) et publiés dans `motion.jsonl` avant l’image native couleur, la stéréo courante et le YOLO éventuel ; ils utilisent la profondeur exacte à t−100 ms. Le contexte YOLO/XYZ est actualisé toutes les **100 ms de temps dataset** par défaut ; `--context-step-ms 20` permet le contrôle à chaque date. La stéréo interne reste calculée à chaque date pour l'historique de compensation et les XYZ courants. Les contextes anciens sont datés et ne sont pas superposés à l'image courante. Ce traitement reste séquentiel et hors temps réel. **Y01 personne/voiture reste le modèle par défaut.** Le GIF est ralenti cinq fois ; sa fluidité ne mesure pas la vitesse du calcul.

Y02 personne/voiture/camion est disponible avec `--weights outputs/colab/Y02_20261015T134856Z/pilot/weights/best.pt`. [Voir le rejeu historique Y02 du 17 octobre](outputs/stereo_speed_20261017/after/clip.gif) · [Voir le parcours par défaut Y01 du 19 octobre](outputs/rectifier_buffers_20261019/after/clip.gif).

**Contrôle de cadence intégré :** le dernier contrôle du 19 octobre dépasse encore le budget de 20 ms sur 17/17 sorties. Le résumé distingue calcul, traitement avec rendu/écritures et retard FIFO simulé ; ce dernier n’est pas une latence caméra. [Mesures et décision](docs/20_NEXT_STEPS.md).

## Résultats et limites

| Mesure | Résultat | Portée |
|---|---|---|
| YOLO, validation personne/voiture | Y02 mAP50 **38,52 %** ; Y01 **23,73 %** | Même validation de 238 images ; aucune référence camion. |
| Rejeu Y02 de 17 images | **83 occurrences**, **74 surfaces**, **9 abstentions** ; camion présent dans les 17 sorties | Extrait du train, pas une validation indépendante ni un nombre d’objets uniques. |
| Dernier rejeu CPU Y02 (17 octobre) | **257,8 ms** de calcul médian pour un pas source de **20 ms** | Hors initialisation, rendu et export ; pas de temps réel. |
| Dernier contrôle CPU Y01, buffers de rectification (19 octobre) | Calcul jusqu’au mouvement **135,3→103,8 ms** médians ; calcul complet **266,5→224,2 ms** | Comparaison unique, autres coûts variables ; 34 fenêtres résidentes isolent une rectification de 39,77→32,25 ms, toujours 17/17 hors budget intégré. |
| Contrôle antérieur, contexte 20→100 ms (18 octobre) | Calcul médian **277,6→225,1 ms** | Comparaison distincte ; 100 ms désigne la période dataset, pas une cadence réelle tenue. |
| Contexte moins fréquent | **17→4 appels YOLO/XYZ**, 18 occurrences fraîches, 15 surfaces et 3 abstentions | Seulement les quatre dates de contexte ; aucun rappel garanti entre ces dates. |
| Non-régression du mouvement | **153 tableaux, 17 modèles de mouvement et quatre contextes communs identiques** | Conservation des sorties comparables, pas validation de leur exactitude physique. |

Une boîte YOLO indique une classe. Un point orange indique un résidu supérieur à 3 px après compensation ; un point vert est compatible avec le modèle, un point gris reste inconnu. **Aucun de ces éléments ne prouve seul le mouvement propre.** XYZ désigne une surface échantillonnée pouvant appartenir au fond, pas le centre d’un objet.

La correction du bord stéréo et les optimisations restent actives. Le cache conserve au plus six dates exactes, sans utiliser de profondeur future. `--no-history-cache` et `--opencv-threads 1` servent aux contrôles ciblés ; ces options ne rétablissent pas toutes les anciennes implémentations. Les mesures détaillées, références publiques partielles et limites de la pose sont dans [la page active](docs/20_NEXT_STEPS.md#conclusion-sur-les-preuves-disponibles).

Dans les JSON, `context.updated=false` et `objects=[]` signifient que YOLO/XYZ n'a pas été exécuté à cette date. Le dernier contexte est référencé par `context.result_file`, avec timestamp et âge en temps dataset. Ce n'est pas une absence d'objet ni une position transportée dans la caméra actuelle. Les objets brefs entre deux actualisations peuvent ne pas être classés.

<details>
<summary>Installation sur un autre poste, acquisition et restauration des données</summary>

## Contenu du dépôt et démarrage

[Dépôt public GitHub](https://github.com/AliAsri/stereo-evenementielle).

Le dépôt contient le code, les tests, les configurations, le notebook actuel, la cellule de diagnostic YOLO et les documents techniques. Les programmes de diagnostic spécialisés sont dans `scripts/diagnostics/`. Les copies régénérables `markdowns/`, anciens notebooks, avis externes bruts, supports de réunion, environnements Python, données DSEC, poids YOLO et résultats générés restent locaux. Les liens vers `data/` et les résultats sous `outputs/` nécessitent donc les artefacts locaux ; cloner ce dépôt ne télécharge pas la démonstration ni les données.

Configuration vérifiée sous Windows avec Python 3.14.6. Depuis la racine, dans PowerShell :

```powershell
git clone https://github.com/AliAsri/stereo-evenementielle.git
cd stereo-evenementielle
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-inspection-lock.txt
.\.venv\Scripts\python.exe scripts/check_project.py --output outputs/checks/initial
```

Le dossier passé à `--output` doit être neuf. Ces contrôles n'exigent ni téléchargement DSEC ni entraînement YOLO. L'inférence complète utilise un environnement distinct, créé avec `.venv-demo` et `requirements-demo-lock.txt`, ainsi que les données et poids déjà préparés : son exécution n'est pas autonome après un simple clonage. Les étapes historiques de préparation sont documentées dans `docs/` ; ne pas relancer tous les scripts indistinctement.

### Prérequis du rejeu intégré

Vérifier les huit fichiers requis avant de charger YOLO ou de lancer les calculs :

```powershell
.\.venv\Scripts\python.exe scripts/run_integrated_demo.py --check-inputs
```

Cette commande liste les fichiers absents, puis vérifie tailles et SHA-256 contre `configs/demo_assets.json`, sans charger YOLO ni créer de résultats. Le même contrôle est obligatoire avant chaque rejeu ; un fichier altéré est refusé avant l'inférence. Les dépendances de calcul ne sont pas contrôlées par cette commande. Le coût de cette vérification préalable est hors calcul par image.

Avec un autre checkpoint choisi par `--weights`, les sept entrées de scène restent vérifiées ; l'empreinte du poids explicite est enregistrée, mais n'est pas qualifiée de conforme à Y01. Le résumé distingue `FROZEN_Y01` de `EXPLICIT_CHECKPOINT`. Y01 demeure le défaut.

| Entrée locale | Préparation / disponibilité |
|---|---|
| `data/raw/zurich_city_04_b/calibration/cam_to_cam.yaml` et, pour chaque côté, `events.h5` et `rectify_map.h5` dans `events_left/` et `events_right/` | Acquisition officielle : `python scripts/download_sample.py --sequence zurich_city_04_b --events` ; cinq fichiers utilisés par le rejeu |
| `outputs/stereo/S01/normalizer.json` | Normalisation figée issue de S01, ajustée sur le train ; préparation décrite dans [S01](docs/21_STEREO_BASELINE.md). Ne pas remplacer par une normalisation ajustée sur l'extrait de test. |
| `outputs/colab/Y01_20261003T191753Z/pilot/weights/best.pt` | Poids du pilote Y01, acquis par entraînement Colab puis import local ; ce checkpoint n'est pas distribué par Git ni par le téléchargeur DSEC |
| `data/processed/dsec_yolo_pilot_v1/images/train/zurich_city_04_b_36614000936.png` | Image de contrôle indépendante produite par l'export Y00 avec la même normalisation ; sa présence et son empreinte sont désormais déclarées |

Avec ces artefacts préparés et l'environnement `.venv-demo` installé :

```powershell
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --output outputs/focused_truck/integrated_rerun
```

Le dossier de sortie doit être neuf. **Un clonage seul ne contient toujours pas ces artefacts.** Le paquet local ci-dessous permet de les transférer sans réentraînement ; sa distribution publique reste à organiser. Les références de mobilité DSEC-MOD servent aux diagnostics historiques ; elles ne sont pas nécessaires à ce rejeu intégré.

### Restaurer les artefacts préparés

Un [paquet local des trois artefacts](outputs/reproduction/demo-assets-v1.zip) est disponible sur le poste de travail, hors Git. Les noms, tailles et empreintes attendus des **huit entrées** sont décrits dans [la configuration de reproduction](configs/demo_assets.json). Le manifeste et le script de restauration font partie de cette version ; une reproduction depuis un clone GitHub neuf avec installation des dépendances n'a pas été vérifiée. Les empreintes identifient nos fichiers figés ; elles ne sont pas des signatures de l'éditeur DSEC.

Après installation de l'environnement d'inspection, copier ce ZIP depuis le poste de travail puis, dans le nouveau clonage :

```powershell
# Remplacer ce chemin par celui du paquet reçu.
.\.venv\Scripts\python.exe scripts/manage_demo_assets.py --restore "C:/chemin/demo-assets-v1.zip"
.\.venv\Scripts\python.exe scripts/download_sample.py --sequence zurich_city_04_b --events
.\.venv\Scripts\python.exe scripts/manage_demo_assets.py --verify
py -3.14 -m venv .venv-demo
.\.venv-demo\Scripts\python.exe -m pip install -r requirements-demo-lock.txt
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --output outputs/focused_truck/integrated_rerun
```

**Contrôle local du 19 octobre, version avant optimisation des buffers de rectification : réussi dans un dossier neuf.** Quarante fichiers de sources/configuration ont été copiés ; le paquet a été restauré deux fois pour vérifier son idempotence, puis les cinq entrées DSEC ont été copiées localement en conservant les chemins du manifeste. Les huit tailles/SHA-256 sont conformes et le rejeu reproduit exactement **153 tableaux, 17 résultats scientifiques et 17 messages de mouvement**. [Preuves](outputs/reproduction/isolated_20261019/verification.json).

Ce contrôle utilise le Python Windows déjà installé avec `-I -B` et le code du dossier isolé ; aucun ancien résultat n'est fourni au démonstrateur. Il **ne vérifie pas** une réinstallation des dépendances, un autre poste ou le dépôt public. Cette version inclut `scripts/manage_demo_assets.py` et `configs/demo_assets.json`, nécessaires à la restauration et au précontrôle. Les huit entrées binaires restent hors Git.

Pour une restauration hors ligne, copier uniquement les cinq fichiers DSEC listés dans `configs/demo_assets.json` depuis le poste source vers les mêmes chemins relatifs du dossier cible, puis exécuter `--verify`. Cette copie remplace la commande de téléchargement dans la procédure ci-dessus ; ne pas relancer l'acquisition lorsque les fichiers vérifiés sont disponibles. Les trois autres fichiers viennent du paquet ZIP. L'environnement Python reste un prérequis distinct.

La restauration vérifie le contenu avant installation, refuse les conflits et accepte une restauration répétée si les fichiers sont identiques. Elle ne charge pas le modèle. `--verify` contrôle aussi les cinq fichiers DSEC. Un téléchargement officiel qui ne correspondrait plus à cette version figée est signalé ; ne pas modifier les empreintes pour masquer un écart.

Pour recréer le paquet depuis le poste disposant des artefacts exacts :

```powershell
.\.venv\Scripts\python.exe scripts/manage_demo_assets.py --pack outputs/reproduction/demo-assets-new.zip
```

Le paquet exclut les événements bruts, résultats d'inférence, environnements et références de mobilité. Il conserve les poids et la normalisation déjà utilisés, sans nouveau réglage. Les attributions DSEC ci-dessous s'appliquent à l'image de contrôle dérivée ; le paquet n'est pas une nouvelle attribution de licence aux poids YOLO.

Les données et illustrations événementielles conservées localement sont issues de DSEC et de nos traitements. Source : [DSEC, Université de Zurich / ETH Zurich](https://dsec.ifi.uzh.ch/), données sous [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Cette attribution concerne ces données et illustrations dérivées.


</details>

## Repères pour travailler sur le code

- `src/pfe_events/` : algorithmes ; `scripts/run_integrated_demo.py` : commande principale.
- `scripts/diagnostics/` et les autres commandes : outils spécialisés conservés, sans obligation de les exécuter.
- `outputs/` : résultats locaux ; `docs/` : documentation ; `markdowns/` : miroir local hors Git.
- [Cahier des charges](docs/PROJECT_BRIEF.md), [maintenance](docs/44_PROJECT_MAINTENANCE.md) et [commandes de contrôle](docs/16_COMMANDS.md).

Après une modification Markdown : `.\.venv\Scripts\python.exe scripts/sync_markdowns.py`.
