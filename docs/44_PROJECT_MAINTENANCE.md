# Organisation et maintenance — refactoring R01

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
