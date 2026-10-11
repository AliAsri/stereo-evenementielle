# M07 — Retard observé pendant un rejeu cadencé

Date : 4 octobre 2026. Objectif : mesurer si la branche d'activité garde la cadence sur un segment plus long, sans modifier ses détections.

## Protocole

La chaîne est celle de M01 avec le lecteur indexé M02. Les seuils, la persistance et les régions restent inchangés. Aucun modèle YOLO, calcul stéréo ou label n'est utilisé. Le rendu et l'écriture des rapports se font hors boucle mesurée.

Deux séquences train seulement : `zurich_city_04_b` et `zurich_city_04_e`. Pour chacune, même segment central de **12 secondes**, précédé de 200 ms d'échauffement non cadencé. Les fenêtres de 10 et 20 ms sont testées deux fois, avec ordre des cas inversé au second passage. Un lecteur et un détecteur neufs sont créés pour chaque cas ; les caches du système ne sont pas vidés.

Le plan initial de 20 secondes a échoué avant toute fenêtre mesurée : les fichiers locaux ne couvrent que 13,401 secondes. Cet échec reste archivé dans `outputs/motion/M07`. La configuration révisée de 12 secondes est enregistrée avant l'exécution dans `outputs/motion/M07_12s`. Un contrôle préalable de la durée disponible a été ajouté au lanceur.

Huit cas complets représentent 96 secondes de rejeu et 7 200 fenêtres traitées. Il s'agit de répétitions de **24 secondes de scènes distinctes**, pas de 96 secondes indépendantes. Les sous-séquences du même trajet ne constituent pas une validation de généralisation.

## Ce qui est mesuré

Pour une fenêtre `[début, fin)`, les événements sont lus seulement lorsque l'horloge du rejeu atteint `fin`. Le traitement est séquentiel ; aucune fenêtre n'est sautée pour cacher un retard.

- **Service lecture + activité** : durée de lecture et calcul de cette fenêtre.
- **Retard de démarrage** : différence entre le début réel du traitement et la date prévue de disponibilité. Il inclut les effets d'ordonnancement du système et l'attente accumulée.
- **Âge de sortie après fin de fenêtre** : temps entre disponibilité prévue et fin du calcul. Il est égal au retard de démarrage plus le service.
- **Fin après la disponibilité suivante** : sortie livrée plus d'un pas après la fin de sa propre fenêtre.
- **Fenêtres supplémentaires disponibles en attente** : retard exprimé en fenêtres complètes, plafonné au nombre de fenêtres restant réellement dans ce segment.

L'horloge monotone `perf_counter_ns` pilote le rejeu. L'attente utilise `time.sleep` et ses dépassements sont mesurés. Les lignes de mesures sont conservées en mémoire ; ce petit coût de collecte contribue à l'ordonnancement de l'itération suivante. L'ouverture du fichier, l'échauffement, le rendu et l'export ne font pas partie du service mesuré.

Ces mesures sont **observées pendant un rejeu disque cadencé**, à la différence de la file d'attente simulée dans M01/M02. Elles excluent l'acquisition d'une caméra physique et l'affichage. Elles ne mesurent toujours pas le délai depuis le début réel du mouvement, qui exige des annotations.

## Exécution et preuves

[Résumé JSON](../outputs/motion/M07_12s/summary.json). Chaque cas conserve `windows.csv` (une ligne par fenêtre), `summary.json`, des statistiques par blocs de trois secondes et les paramètres du détecteur. Le dossier de l'expérience contient les versions logicielles, la plateforme, le protocole, les sources et leurs SHA256.

Les chemins, tailles, dates de modification et plages temporelles des HDF5 sont relevés. Les fichiers bruts ne sont pas intégralement rehachés pendant cette mesure ; leur provenance de téléchargement antérieure reste conservée. Les temps dépendent de la charge du poste, de la mémoire cache et de l'ordonnancement Windows.

```powershell
# Le dossier M07_12s existe déjà ; choisir une nouvelle sortie.
.\.venv\Scripts\python.exe scripts/benchmark_paced_motion.py --output outputs/motion/M07_repeat_02
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/sync_markdowns.py
```

Le budget de sécurité de 120 secondes par cas arrête une expérience trop lente au début d'une itération ; une lecture déjà commencée n'est pas interrompue. Une interruption est marquée explicitement et ne devient pas un résultat complet.

## Fonctionnement du code

`src/pfe_events/replay_timing.py` fournit `paced_windows(reader, detector, start_us, duration_us, step_us, ...)`. Il calcule la date de disponibilité de chaque fenêtre, attend cette date, appelle le lecteur puis le détecteur, et sauvegarde les dates et coûts. Les dépendances de l'horloge et de l'attente sont injectables pour les tests, sans fausser l'horloge des expériences réelles. La fonction retourne les lignes et un statut avec le nombre prévu et traité.

`scripts/benchmark_paced_motion.py` impose les séquences train, vérifie leur durée, initialise les sources, exécute les huit cas et sauvegarde les statistiques sans modifier `motion.py` ni `dsec_indexed.py`. `configs/m07_paced_replay.json` fixe durées, fenêtres, répétitions et périmètre.

Six contrôles déterministes avec horloge artificielle vérifient : aucune lecture avant disponibilité, fenêtres contiguës, accumulation du retard sans saut, séparation attente/calcul, égalité exacte à l'échéance et arrêt explicite au budget. Les résultats de ces horloges artificielles sont des tests logiciels, distincts des mesures DSEC.


## Résultats réellement obtenus

| Séquence | Pas | Répétition | Service médian / p95 (ms) | Âge de sortie p95 (ms) | Âge maximal (ms) | Fins au-delà du pas |
|---|---:|---:|---:|---:|---:|---:|
| `04_b` | 10 ms | 1 | 8,45 / 13,07 | 667,65 | 801,32 | 47,83 % |
| `04_b` | 10 ms | 2 | 8,13 / 12,44 | 445,73 | 533,62 | 42,08 % |
| `04_b` | 20 ms | 1 | 10,96 / 19,43 | 19,96 | 23,82 | 4,83 % |
| `04_b` | 20 ms | 2 | 10,81 / 23,04 | 123,97 | 132,20 | 30,50 % |
| `04_e` | 10 ms | 1 | 8,45 / 11,72 | 41,52 | 65,14 | 35,17 % |
| `04_e` | 10 ms | 2 | 7,87 / 10,53 | 16,44 | 36,73 | 18,17 % |
| `04_e` | 20 ms | 1 | 12,54 / 16,12 | 16,62 | 27,40 | 2,00 % |
| `04_e` | 20 ms | 2 | 12,67 / 15,70 | 16,26 | 35,43 | 1,67 % |

Sur `04_b`, les deux passages à 10 ms terminent avec respectivement **801,32 ms et 533,62 ms** de retard. Le maximum de fenêtres supplémentaires déjà disponibles en attente atteint 64 et 45 pendant ces passages. Le traitement ne tient donc pas la cadence de 10 ms sur toute la durée observée.

La moyenne du service peut pourtant rester sous 10 ms : elle vaut 8,84 et 8,35 ms pour ces deux cas. Le débit n'est pas uniforme. Sur les trois dernières secondes, le service moyen monte à **12,21 et 11,48 ms par fenêtre de 10 ms** ; l'attente s'accumule. Une moyenne globale ou un court extrait peut ainsi masquer le problème.

Le pas de 20 ms réduit fortement l'âge des sorties sur `04_b`, mais le second passage atteint encore 123,97 ms au p95. Sur `04_e`, le p95 de l'âge reste entre 16,26 et 16,62 ms à 20 ms, avec quelques dépassements. Ces observations ne garantissent ni une cadence stricte ni une performance similaire sous une autre charge. Le coût de lecture et celui d'activité contribuent tous les deux ; ne pas attribuer le problème à un seul composant sans profilage.

**Vérification : 87 tests réussis**, neuf sources et snapshots hachés vérifiés, 7 200 fenêtres contiguës sans lecture anticipée. Les nombres d'événements traités sont identiques entre pas et répétitions pour chaque séquence : 115 668 807 pour `04_b`, 113 533 698 pour `04_e`. Cette égalité de comptage n'est pas une preuve d'égalité des propositions entre fenêtres de durées différentes. Les fichiers du détecteur et du lecteur sont identiques à ceux archivés dans M05. [Contrôles](../outputs/motion/M07_12s/verification.json).

## Décision et prochaine étape

La cadence 10 ms reste une cible, pas une garantie acquise. Le pas 20 ms est un point de comparaison utile, sans remplacement automatique du réglage : changer la fenêtre change aussi le comportement temporel du détecteur.

Prochaine tâche indépendante des annotations : profiler lecture et activité sur la fin du segment `04_b`, puis optimiser en conservant exactement les sorties de référence à même fenêtre. Comparer avant/après sur les mêmes événements. Les annotations M06 restent nécessaires pour mesurer la qualité réelle et arbitrer le compromis de cadence. Ne pas supprimer des fenêtres ni abaisser les seuils pour donner artificiellement une impression de rapidité.
