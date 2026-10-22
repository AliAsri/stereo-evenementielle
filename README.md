# Prototype de détection de mouvement par stéréo événementielle

**Prototype revu pour publication — 22 octobre 2026.** Démonstrateur CPU sur un extrait DSEC enregistré : suivi et compensation géométrique, contexte YOLO personne/voiture, surface XYZ et décision conditionnelle par détection. **La fiabilité physique du mouvement et le temps réel ne sont pas démontrés.** L'utilisateur choisit de finaliser ce prototype avec ses limites ; aucun nouveau dataset ou entraînement n'est requis pour consulter le résultat.

## Voir le résultat

[Ouvrir le GIF de référence](outputs/object_surface/integrated_f2_20261022/clip.gif) · [Première image avec décisions](outputs/object_surface/integrated_f2_20261022/first_frame.png) · [Vérification du rejeu](outputs/object_surface/integrated_f2_20261022/verification.json).

Le GIF contient 17 dates et est ralenti cinq fois ; sa fluidité ne mesure pas le temps de calcul. Les résultats et les poids restent hors Git. Le paquet local `outputs/delivery/reviewed_20261022/prototype-local.zip` contient une copie du code courant, les trois petits artefacts figés et les résultats de présentation. Il exclut les environnements et les cinq gros fichiers DSEC. `DELIVERY_MANIFEST.json` dans le paquet décrit le contenu et ses SHA-256. Le paquet capture le dossier de travail courant ; il ne signifie pas que ces changements ont été publiés sur GitHub.

## Relancer sur le PC préparé

Depuis la racine, avec `.venv-demo` et les huit entrées décrites dans [configs/demo_assets.json](configs/demo_assets.json) :

```powershell
.\.venv-demo\Scripts\python.exe -B scripts/run_integrated_demo.py --check-inputs
.\.venv-demo\Scripts\python.exe -B scripts/run_integrated_demo.py --output outputs/demo_local_01
```

Choisir un dossier de sortie neuf ; les anciens résultats sont conservés. Le contrôle des tailles et empreintes est également imposé au démarrage du rejeu. La commande ne réentraîne aucun modèle. L'environnement local est Windows/Python 3.14, avec [requirements-demo-lock.txt](requirements-demo-lock.txt) ; une installation neuve et un autre poste n'ont pas été validés.

Pour réutiliser le paquet sur un autre dossier local, copier les cinq fichiers DSEC vers les chemins du manifeste, préparer l'environnement décrit ci-dessous, puis exécuter les mêmes commandes. Une extraction seule permet de consulter le GIF ; elle ne permet pas de rejouer sans les données et dépendances.

## Ce qui est livré et vérifié

| Élément | Résultat de référence du 22 octobre |
|---|---|
| Entrées et calculs | Huit tailles/SHA-256 conformes ; 153 tableaux et 17 messages de mouvement conservés |
| Contexte | Quatre dates de contexte YOLO/XYZ, 18 occurrences de détection ; aucune identité persistante |
| Décision conditionnelle | 2 mobiles estimées, 2 immobiles estimées, 14 indéterminées |
| Surfaces XYZ | 13 estimations, 2 abstentions pour couches ambiguës, 3 profondeurs insuffisantes |
| Contrôles logiciels de finalisation | 391 tests passent ; 129 fichiers Python et 47 aides CLI contrôlés |
| Dépendances locales | `pip check` réussi dans les deux environnements existants |

[Contrôles finaux](outputs/reviews/prepush_20261022/checks/report.json) · [Règles et limites détaillées](docs/38_OBJECTIF_OBJETS_MOBILES.md) · [État et finalisation](docs/20_NEXT_STEPS.md).

Le calcul médian de ce rejeu est d'environ **109,1 ms jusqu'au mouvement** et **230,6 ms pour le parcours complet**, hors rendu/export ; la première image inclut le démarrage de l'inférence. Les 17 sorties dépassent le budget de comparaison de 20 ms. Une session hors ligne ne constitue pas un benchmark stable, une latence caméra ou un délai de détection du début du mouvement.

La revue avant publication refuse désormais les configurations de surface non finies ou les supports de pixels non entiers. Le rendu dispose d'un repli de police et le contrôle des couches de profondeur est isolé dans une fonction dédiée. Les 18 décisions et les 17 images restent exactement conformes aux résultats sauvegardés, sans nouvelle inférence ni réglage. [Compte rendu de revue](docs/44_PROJECT_MAINTENANCE.md#revue-avant-publication--22-octobre-2026). Le paquet précédent est conservé comme instantané historique.

## Lire les sorties

- `clip.gif` : résultat visible, avec les libellés « mobile estimé », « immobile estimé » ou « indéterminé ».
- `motion.jsonl` : indices de mouvement publiés à chaque date source, avant la stéréo courante et le contexte optionnel.
- Un JSON par date : modèle final, diagnostics bruts, contexte daté, surfaces et décisions par détection. `physical_mobility` reste `UNCONFIRMED`.
- Un NPZ par date : tableaux numériques du rejeu ; ces gros fichiers restent locaux et sont exclus du paquet de présentation.
- `summary.json` : versions, empreintes, configuration et coûts observés. `verification.json` : comparaison d'intégration.

Les fenêtres causales durent 50 ms, le pas source est de 20 ms et le suivi porte sur 100 ms. La compensation exige la profondeur exacte à t−100 ms. La stéréo interne reste calculée à chaque date ; YOLO et XYZ sont actualisés toutes les 100 ms dataset. Sur une date sans contexte, `objects=[]` et `context.updated=false` signifient « non calculé », et non « aucun objet ». Les anciens contextes ne sont pas superposés à l'image courante.

## Limites à présenter avec la démonstration

La décision mobile/immobile est **conditionnelle au modèle rigide dominant et à l'association de surface**. Elle n'est pas une étiquette de mobilité physique validée. Le garde-fou de modèles concurrents produit cinq abstentions sur ce rejeu ; un modèle accepté peut encore appartenir à une couche mobile. Le cas synthétique 108 points mobiles/16 points de fond et le biais de profondeur restent des contre-exemples connus.

XYZ représente un point de surface échantillonné, pouvant appartenir au fond, et non le centre ou la trajectoire 3D de l'objet. Le contrôle F5 s'abstient devant plusieurs couches suffisamment distinctes et soutenues ; une cible sans profondeur valide peut rester invisible. La limite proche nominale est de 3,590 m pour la calibration et la recherche actuelles (0..95 px), sans garantie de couverture. Une profondeur absente ne révèle pas sûrement sa cause.

L'extrait intégré appartient au train. Les comptes ci-dessus sont des occurrences sur un petit extrait, pas des objets uniques ou des mesures de précision/rappel indépendantes. Y01 personne/voiture reste le défaut. Y02 personne/voiture/camion est conservé comme essai historique et sa classe camion n'est pas qualifiée indépendamment. La validation indépendante reste ouverte ; aucun nouveau téléchargement ou message aux auteurs n'est engagé dans cette finalisation.

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

## Pour développer ou retrouver l'historique

- [Commandes](docs/16_COMMANDS.md), [architecture](docs/05_PROJECT_ARCHITECTURE.md), [cahier des charges](docs/PROJECT_BRIEF.md).
- [Historique des essais](docs/19_PROGRESS.md), [objectif et preuves détaillées](docs/38_OBJECTIF_OBJETS_MOBILES.md), [audit daté conservé](docs/AUDIT_TECHNIQUE_SCIENTIFIQUE_18_OCTOBRE_2026.md).
- `src/pfe_events/` contient les composants ; `scripts/run_integrated_demo.py` est le parcours principal. Les diagnostics sont conservés comme historique et ne doivent pas être relancés indistinctement.

Contrôle commun, sans entraînement ni téléchargement :

```powershell
.\.venv\Scripts\python.exe -B scripts/check_project.py --output outputs/checks/local_01
```

Choisir une sortie neuve. Modifier les sources Markdown puis lancer `.\.venv\Scripts\python.exe -B scripts/sync_markdowns.py`. Le miroir `markdowns/` est local et hors Git.
