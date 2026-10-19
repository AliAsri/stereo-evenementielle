# Organisation, revue et maintenance

## Nettoyage du dépôt — 19 octobre 2026

Après publication `480332d`, inventaire Git : **205 fichiers, 1 990 819 octets de contenu**, aucun fichier de plus de 1 Mo et aucun doublon exact par SHA-256. Ce volume exclut l'historique Git, les environnements, données, poids et résultats ignorés. Les anciens lecteurs, outils d'annotation et diagnostics encore référencés sont conservés pour la reproductibilité ; aucune expérience locale supprimée.

README recentré sur le parcours principal et quatre objectifs ; les chiffres historiques restent dans les documents existants. Exclusions complétées pour les caches, rapports de couverture, environnements de test et dossiers racine de construction/distribution. Les dossiers `output/` et `tmp/` étaient déjà exclus lors du push précédent. Aucun code scientifique, test, configuration ou fichier de données supprimé ou déplacé. Vérification des exclusions et synchronisation Markdown ; pas de nouvelle inférence ni répétition de la suite de tests pour ce changement documentaire.

## Revue globale du 15 octobre 2026

**Verdict : les composants choisis restent cohérents avec le sujet, mais le livrable scientifique n’est pas encore validé.** Le projet possède une chaîne réelle événements → YOLO → stéréo → surface 3D → indices de mouvement. Il ne démontre pas encore la détection rapide et fiable d’un mouvement indépendant de la caméra. La suite doit produire cette preuve ou exposer précisément sa limite, plutôt qu’accumuler des variantes.

La revue a confronté le cahier des charges, les décisions datées, le parcours intégré, les données/exportations et les preuves enregistrées. Les contrôles globaux couvrent le chargement des commandes et la suite de tests ; le rejeu réel couvre le parcours principal Y02 sur l’extrait existant. Les anciens entraînements Colab, tous les diagnostics historiques, un test GPU et un test matériel de caméra n’ont pas été réexécutés. Ce bilan ne promet pas l’absence de tout défaut.

### Ce qui est solide

- Les lecteurs conservent des fenêtres causales demi-ouvertes et contrôlent les horloges. Le cache réutilise uniquement des dates exactes dans un contexte de rejeu borné.
- Les événements natifs alimentent YOLO ; les vues rectifiées alimentent la stéréo et le suivi. La profondeur du mouvement appartient à l’instant précédent ; celle associée à une boîte appartient au même instant que la boîte.
- Le train et la validation sont séparés par groupe de trajet ; le normaliseur est ajusté sur le train. Les exports conservent labels, timestamps et empreintes. L’absence de camion en validation est explicite.
- Le démonstrateur calcule réellement ses sorties depuis les événements et les poids ; les boîtes de référence et la profondeur GT ne guident pas cette inférence.
- Les abstentions et limites sont explicites. Le point XYZ est une surface visible, et le résidu n’est pas présenté comme une preuve de mobilité.

### Défauts corrigés et refactoring ciblé

| Constat | Correction | Effet attendu |
|---|---|---|
| Le démonstrateur ne faisait pas respecter le contrat de calibration déjà exigé par le diagnostic de référence. L’audit ne rejetait pas explicitement les intrinsèques non finis, une résolution incohérente ou une base nulle. | Validation commune dans `audit_calibration`, option `require_canonical` réutilisée par les deux commandes ; le démonstrateur exige sa résolution figée 640×480. | Échec explicite sur des entrées incompatibles, avant le chargement du modèle. Les calibrations actuelles restent acceptées. |
| L’ordre des canaux déclaré dans un normaliseur pouvait être incompatible avec les échelles utilisées sans être signalé. | `normalized_event_image` vérifie les métadonnées de canaux lorsqu’elles sont présentes, y compris dans le chemin canal total. | Empêche une mauvaise interprétation silencieuse des échelles ; les appels synthétiques à échelles seules restent compatibles. |
| L’import Colab supposait que `outputs/reports` existait ; un `--dataset` externe échouait lors du calcul du chemin relatif du ZIP. | Création du dossier de rapport et conservation d’un chemin absolu pour les fichiers hors projet. Test de premier import dans un dossier neuf, sur preuves synthétiques. | Import reproductible sans dépendre de l’ordre d’exécution d’autres scripts. Le statut PASS reste un contrôle de fichiers, pas une validation scientifique. |
| La feuille de route contenait 947 lignes et plusieurs « résultats actuels » ou « prochaines étapes » incompatibles selon leur date. | Page active ramenée à 56 lignes ; contenu précédent conservé intégralement dans `19_PROGRESS.md`. README, guide du code, architecture et pages historiques réorientés. | Une seule reprise lisible, sans effacer les décisions ou résultats passés. |

Aucun seuil scientifique, checkpoint par défaut, partition ou résultat expérimental n’a été changé par cette revue. Le refactoring mutualise un contrôle existant et clarifie les responsabilités ; aucune nouvelle couche d’architecture n’est ajoutée.

### Vérifications exécutées

| Contrôle | Résultat |
|---|---|
| Avant modifications | 252 tests, 115 fichiers Python, 42 aides CLI réussis |
| Après modifications | **255 tests, 115 fichiers Python, 42 aides CLI réussis** |
| Dépendances installées | `pip check` réussi dans les deux environnements ; contrôle de `.venv-demo` piloté par le pip de `.venv` |
| Entrées du démonstrateur Y01 | **8 tailles et SHA256 conformes** à `configs/demo_assets.json` |
| Exports à deux et trois classes | **Deux PASS**, chacun 774 images et 1 560 fichiers hachés ; groupes séparés ; camion absent de validation déclaré |
| Rejeu Y02 depuis les événements | **17 images, 83 occurrences, 74 surfaces, 9 abstentions** |
| Régression contre le dernier rejeu Y02 | **153 tableaux et tous les résultats scientifiques des 17 images identiques**, hors chronométrages ; versions et empreintes d’entrées identiques |
| Documentation | Ancienne feuille de route intégralement conservée ; liens locaux contrôlés et miroir Markdown synchronisé |

Le rejeu de revue mesure 356,1 ms médians de calcul complet, hors initialisation/rendu/export. Il sert à vérifier la conservation des résultats ; il ne prouve pas un gain ou une régression de vitesse par rapport au benchmark précédent de 345,8 ms. Le démarrage et la charge varient ; toutes les sorties dépassent encore le budget source de 20 ms.

Preuves locales : [contrôles finaux](../outputs/reviews/global_20261015/final_checks/report.json), [tests](../outputs/reviews/global_20261015/final_checks/tests.log), [régression](../outputs/reviews/global_20261015/regression.json), [export trois classes](../outputs/reviews/global_20261015/truck_export.json), [export deux classes](../outputs/reviews/global_20261015/pilot_export.json), [rejeu](../outputs/reviews/global_20261015/replay_y02/clip.gif). Les fichiers modifiés ont une copie préalable sous `outputs/reviews/global_20261015/before/`, suffixée `.bak`.

### Nettoyage du dossier

Inventaire au début de la revue : **38 456 fichiers, 3 883 dossiers, environ 6,69 Gio**. Environ **75 % des fichiers sont dans `.venv` et `.venv-demo`**. Git suit **192 fichiers**, aucun de plus de 1 Mo ; ce nombre ne comprend pas les nouveaux fichiers de travail non encore suivis. Le code Python contrôlé compte 36 fichiers de bibliothèque, 46 scripts et 33 fichiers de tests.

| Ensemble local | Taille approximative | Décision |
|---|---:|---|
| Données | 4,39 Gio | Conserver les originaux, exports et références |
| Deux environnements Python | 1,24 Gio | Conserver : inspection légère et exécution YOLO ont des rôles distincts |
| Résultats | 1,04 Gio | Conserver les preuves et expériences historiques |
| Miroir Markdown | Moins de 1 Mio à l’inventaire | Synchroniser, garder hors Git |

**91 fichiers de cache Python générés, environ 0,92 Mio, supprimés** dans quatre dossiers `__pycache__` sous `src`, `scripts` et `tests`, après les contrôles. Ces fichiers se recréent automatiquement. Aucun dataset, checkpoint, environnement, expérience, document source ou résultat antérieur n’a été supprimé. Pas de suppression massive ni de nouvelle dépendance.

[Inventaire](../outputs/reviews/global_20261015/inventory.json) · [Nettoyage des caches](../outputs/reviews/global_20261015/cache_cleanup.json).

### Sommes-nous dans la bonne voie ?

**Oui pour les briques et la traçabilité ; pas encore pour la démonstration de l’objectif principal.** Les événements, la stéréo, YOLO et XYZ restent bien dans le périmètre demandé. L’excès se situe dans l’accumulation des diagnostics et de leur documentation. Les gains sur les classes ou sur un tri de pixels ne suffisent pas à valider le mouvement indépendant.

Les blocages restent le coût complet supérieur au budget, la sensibilité du modèle de caméra, le support de profondeur et de suivi incomplet, puis l’absence de validation camion indépendante. Le test réservé reste à préserver ; les références partielles du train ne permettent pas d’inventer une précision/rappel. La promotion de Y02 et les autres classes passent après leur qualification ; elles ne doivent pas détourner le projet du mouvement.

La [feuille de route active](20_NEXT_STEPS.md#la-suite-utile) fixe la suite, avec un seul parcours, des critères mesurables et aucune nouvelle architecture par défaut.

---

## Archive R01 — organisation du 8 octobre 2026


**8 octobre 2026.** Nettoyage demandé avant l'audit DSEC-MOD. Cette étape réorganise le code partagé et les accès à la documentation ; elle n'introduit pas de nouvelle méthode de détection et ne change aucun seuil scientifique.

**Archive de R01.** Les prochaines actions décrites en fin de page sont celles du 8 octobre, déjà dépassées. La simplification du 10 octobre et l'audit R02 du 11 octobre sont suivis exclusivement dans [la page active](20_NEXT_STEPS.md).

## Carte du code

| Responsabilité | Modules dans `src/pfe_events/` |
|---|---|
| Lecture DSEC, variantes de référence et accélérées | `dsec.py`, `dsec_indexed.py`, `dsec_cached.py` |
| Partitions, localisation des fichiers, dates admissibles | `pilot.py` |
| Représentations, calibration, stéréo | `representations.py`, `geometry.py`, `stereo.py` |
| Conversion des labels YOLO | `detection.py` |
| Activité causale et variantes | `motion.py`, `adaptive_activity.py`, `motion_lookup.py` |
| Mouvement apparent et candidats persistants | `global_motion.py`, `mobile_candidates.py` |
| Géométrie assistée par profondeur | `rectified_tracking.py`, `rigid_motion.py` |
| Contrôles synthétiques | `motion_controls.py`, `mobile_controls.py`, `rigid_controls.py` |
| Évaluation temporelle et formats de relecture | `motion_evaluation.py`, `multirate_evaluation.py`, `motion_review.py` |
| Rejeu cadencé | `replay_timing.py` |
| Métadonnées publiques EVIMO | `evimo_reference.py` |
| **Nouveau : fichiers et rapports JSON** | `artifacts.py` |
| **Nouveau : statistiques historiques** | `reporting.py` |
| **Nouveau : support de benchmarks** | `benchmarking.py` |
| **Nouveau : rendu événementiel partagé** | `visualization.py` |

Les modules ne lancent pas d'expérience à l'import. Les commandes restent sous `scripts/` et conservent leurs noms. Les résultats ne sont pas déplacés : les chemins présents dans les anciens rapports et documents restent utilisables.

## Ce qui a été refactorisé

Seize scripts utilisent désormais les fonctions du package à la place de fonctions dupliquées ou importées depuis un autre lanceur d'expérience. Les noms locaux historiques (`digest`, `sha`, `save`, `distribution`, etc.) sont conservés par alias lorsque nécessaire.

- `artifacts.sha256_file` calcule les empreintes en flux, y compris pour les grands fichiers.
- `artifacts.write_json` écrit un JSON strict avec retour final ; `write_unicode_json` conserve le format S01/export YOLO. `write_legacy_json` préserve explicitement le format ancien, y compris sa permissivité NaN. Les nouvelles expériences doivent préférer le format strict.
- Les quatre statistiques `activity_distribution`, `paced_distribution`, `adaptive_distribution`, `rigid_distribution` gardent leurs champs et comportements historiques. Unifier leurs noms en changeant silencieusement les rapports aurait cassé leur comparaison.
- `benchmarking` contient la comparaison exacte des sorties, l'écriture CSV, l'échauffement causal et la localisation des événements. Le chemin racine est fourni explicitement.
- `visualization.native_event_image` garde l'échelle fixe du rendu M03/M10.
- Les listes de provenance des lanceurs modifiés incluent les nouveaux modules dont ils dépendent.

Le vérificateur `scripts/verify_yolo_export.py` reste autonome, car il est copié dans le paquet Colab. L'exporteur peut toujours l'importer : c'est une exception explicite à la règle de séparation des lanceurs. Les petits téléchargeurs autonomes et le synchroniseur Markdown ne sont pas forcés à charger NumPy ou le package.

## Commande de contrôle commune

```powershell
.\.venv\Scripts\python.exe scripts/check_project.py --output outputs/checks/local_01
```

Choisir un dossier neuf à chaque exécution. La commande utilise l'interpréteur qui la lance, vérifie la syntaxe, les imports entre lanceurs, les aides des CLI utilisant argparse, puis exécute la suite unittest. Elle ne télécharge rien, n'entraîne rien et ne relance pas les expériences.

L'état et les erreurs sont dans `report.json`, les tests dans `tests.log`. Une vérification d'aide CLI contrôle le chargement et les arguments ; elle ne valide pas toutes les exécutions complètes sur données réelles.

## Audit EVIMO : sortie protégée

Le précédent audit écrivait directement dans M14. Il exige maintenant une sortie neuve pour protéger l'expérience historique :

```powershell
.\.venv\Scripts\python.exe scripts/audit_evimo_sample.py --output outputs/motion/M14_audit_02
```

L'acquisition reste lue par défaut depuis `outputs/motion/M14/acquisition.json`. L'option `--acquisition` permet de préciser un autre manifeste. Le dossier existant est refusé avant de lancer l'audit. Cette protection est le seul changement volontaire d'interface ; les autres commandes gardent leurs arguments.

## Vérifications réellement exécutées

| Vérification | Résultat |
|---|---|
| Suite avant refactoring | 137 tests réussis |
| Suite après refactoring | 144 tests réussis |
| Syntaxe | 78 fichiers Python contrôlés |
| Aides de commandes | 24 CLI réussies |
| Contrôles M11 relancés dans un dossier neuf | 135 cas JSON exactement identiques hors durées ; 1 620 tableaux identiques |
| Audit M14 relancé dans un dossier neuf | Rapport identique hors provenance du code ; PNG identique octet par octet |
| Fichiers antérieurs sous `data/` et `outputs/` | 4 381 entrées présentes, tailles et dates de modification inchangées |
| Modules algorithmiques existants | Empreintes SHA256 inchangées |

Les coûts d'exécution changent naturellement entre deux exécutions et ne servent pas de critère d'égalité. Cette vérification ne constitue pas une nouvelle mesure de performance. Aucun réentraînement YOLO, aucune nouvelle campagne cadencée M08/M09 ni aucune nouvelle évaluation de mobilité n'a été réalisé.

Les sept nouveaux tests portent sur les formats JSON, le refus des NaN avant écriture stricte, le hash, les schémas de statistiques, la comparaison des sorties, les dates d'échauffement et l'échelle du rendu.

Preuves : [contrôles](../outputs/refactor/R01/checks/report.json), [journal des tests](../outputs/refactor/R01/checks/tests.log), [comparaison de résultats](../outputs/refactor/R01/regression.json). Les 147 fichiers de travail sauvegardés avant intervention sont dans `outputs/refactor/R01/before/`, avec empreintes dans `before_hashes.json`. Les copies historiques de Markdown y portent le suffixe `.md.bak` pour ne pas encombrer la copie documentaire courante. Aucune suppression de données ou nettoyage de cache n'a été effectué.

## Pour la prochaine étape

L'audit DSEC-MOD doit ajouter un adaptateur de données et une commande dédiée. Il doit réutiliser le hash et le JSON strict, conserver les dates/repères/provenance et refuser de confondre boîtes d'objets, activité et mobilité. Les partitions déjà utilisées pour réglage doivent être recensées avant de définir une évaluation indépendante.

Conserver EVIMO comme complément pour l'analyse géométrique. Les références publiques ne deviennent pas des entrées du détecteur sans marquage oracle explicite. Les annotations manuelles utilisateur restent sautées.

Après chaque modification documentaire, modifier les sources puis lancer `python scripts/sync_markdowns.py`. Les copies sous `markdowns/` ne sont pas éditées directement.
