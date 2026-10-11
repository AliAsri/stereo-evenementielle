# M02 — Lecture accélérée, résultats d'activité identiques

Étape du 4 octobre 2026, dans la priorité « détection rapide du mouvement ». Le lecteur utilise maintenant l'index temporel DSEC pour réduire le coût d'accès aux fenêtres. Le calcul d'activité et ses seuils restent ceux de M01. La cadence cible de 10 ms se rapproche, mais n'est pas garantie au p95 dans le rejeu autonome.

## Changement réalisé

`IndexedDSECReader`, dans `src/pfe_events/dsec_indexed.py`, complète le lecteur binaire de référence sans le modifier. L'index `ms_to_idx` associe chaque milliseconde à une position dans le flux ; l'offset du fichier est retiré avant recherche et rétabli dans les timestamps retournés. Le contrat de l'index est décrit dans le [format officiel DSEC](https://dsec.ifi.uzh.ch/data-format/) et son [lecteur officiel](https://github.com/uzh-rpg/DSEC/blob/master/scripts/utils/eventslicer.py).

L'implémentation encadre la fenêtre par les millisecondes inférieure et supérieure, lit les timestamps de cet intervalle borné puis détermine les bornes exactes par `searchsorted(..., side="left")`. Elle ne retourne que les événements de `[début, fin[`, même si la lecture HDF5 ou l'encadrement temporel accèdent aussi à des données voisines. Aucun événement futur n'entre dans la carte d'activité. Il s'agit toujours d'un lecteur de données enregistrées, pas d'un pilote d'acquisition.

À l'ouverture, dimensions, type, ordre et plage de l'index sont contrôlés. Chaque borne utilisée est confrontée aux timestamps adjacents une première fois : cela évite qu'un index incorrect supprime silencieusement un événement ou une partie d'un groupe de timestamps égaux. L'ordre local des timestamps, les coordonnées et les polarités restent contrôlés. Le lecteur conserve l'hypothèse d'un fichier temporellement ordonné, comme la référence ; les fichiers ont été audités dans S01.

Si la fenêtre dépasse la couverture de l'index ou si son encadrement est plus gros que le budget d'événements, la recherche binaire de référence est utilisée. Le budget reste appliqué à la fenêtre exacte. Un index incohérent provoque une erreur, pas une sortie vide. Les six essais M02 n'ont pas eu besoin de ce repli ; il est vérifié sur fixtures synthétiques.

## Comparaison contrôlée

Même sélection que M01 : segments centrés de deux secondes sur `zurich_city_04_b` et `thun_00_a`, précédés de 200 ms de préchauffage, fenêtres/pas 10/20/50 ms, même activité et mêmes seuils. Deux passages ; ordre des lecteurs alterné à chaque fenêtre et inversé au second passage. Les comparaisons d'égalité et les hashes sont hors chronométrage.

Au total : **1 496 paires de fenêtres comparées**, 2 992 lignes de chronométrage avec préchauffage. Les champs x/y/t/p, les cartes de taux, les masques candidats/actifs et les rectangles proposés sont identiques entre les deux lecteurs. Les hashes du flux et les cartes NPZ correspondent également à M01. Le test réservé n'est pas ouvert.

Temps combiné lecture + activité, en millisecondes :

| Séquence | Fenêtre | Référence médiane | Indexé médiane | Référence p95 | Indexé p95 |
|---|---:|---:|---:|---:|---:|
| `04_b` | 10 ms | 9,03 | 5,86 | 11,02 | 7,78 |
| `04_b` | 20 ms | 12,41 | 9,33 | 15,59 | 12,83 |
| `04_b` | 50 ms | 18,20 | 16,24 | 27,40 | 26,20 |
| `thun_00_a` | 10 ms | 10,54 | 7,70 | 12,27 | 9,47 |
| `thun_00_a` | 20 ms | 14,82 | 12,52 | 17,02 | 14,67 |
| `thun_00_a` | 50 ms | 27,00 | 25,52 | 32,96 | 31,78 |

Sur validation à 10 ms, la lecture seule passe de 6,91 à 4,18 ms en médiane (facteur 1,65). Le temps combiné baisse d'environ **27 %**, avec 2 % de dépassements du pas de 10 ms contre 66,25 % pour la référence dans cette comparaison. Les deux passages répètent le même segment : ils ne représentent pas deux séquences indépendantes.

Ces valeurs de référence diffèrent des anciennes mesures M01 : charge du poste, cache et protocole alterné varient. Le gain attribué au lecteur est donc calculé dans la comparaison appariée ci-dessus, pas en soustrayant des mesures historiques prises dans d'autres conditions. Les effets de cache ne sont pas éliminés ; l'ouverture des lecteurs est enregistrée séparément et exclue des temps par fenêtre.

## Rejeu autonome supplémentaire

Le script de rejeu accepte désormais `--reader indexed`. Une exécution séparée dans `outputs/motion/M02_replay/` vérifie le nouveau lecteur seul, avec génération des figures et GIF hors chronométrage.

| Séquence, fenêtre 10 ms | Médiane lecture + activité | p95 | Fenêtres dépassant 10 ms |
|---|---:|---:|---:|
| `04_b` | 7,44 ms | 10,28 ms | 6,5 % |
| `thun_00_a` | 8,45 ms | 11,32 ms | 14 % |

Les six ensembles de cartes/timestamps et les hashes d'événements sont exactement identiques à M01. Les deux GIF de 40 images sont présents. Le [rejeu de validation accéléré](../outputs/motion/M02_replay/thun_00_a/10ms/replay.gif) conserve le rendu de l'algorithme M01 ; ses temps proviennent du lecteur indexé.

Le p95 autonome dépasse encore 10 ms. Il faut garder une marge et tester des segments plus longs avant toute promesse de cadence soutenue. La simulation de file d'attente donne jusqu'à 25,17 ms de retard de complétion après fin de fenêtre sur la validation autonome ; ce n'est pas une latence mesurée sur un capteur.

## Vérifications, code et preuves

**39 tests réussis**, dont six nouveaux groupes de tests du lecteur indexé : timestamps dupliqués et bornes exactes, trous temporels, bords du fichier, budget sur la fenêtre exacte, corruption d'index, contrôles des événements. Les fenêtres synthétiques sont vérifiées contre un masque temporel indépendant en mémoire, pas seulement contre un second lecteur.

[Comparaison M02](../outputs/motion/M02/summary.json) · [vérification](../outputs/motion/M02/verification.json) · [rejeu autonome](../outputs/motion/M02_replay/summary.json). Les CSV permettent de recalculer les médianes, p95 et dépassements.

Les rapports M01 restent intacts. Des copies des sources correspondant aux hashes d'exécution sont sous `source_snapshot/` dans les dossiers d'expérience, notamment avant de modifier le script de rejeu. Le script actuel de benchmark relève directement les versions installées et archive ses sources ; pour l'exécution initiale M02, les versions reprises de M01 ont aussi été vérifiées contre l'environnement installé. Ces ajustements de provenance ne modifient pas l'algorithme chronométré.

## Utilisation

```powershell
.\.venv\Scripts\python.exe scripts/run_motion_baseline.py --reader indexed --output outputs/motion/M02_replay_rerun
.\.venv\Scripts\python.exe scripts/benchmark_motion_reader.py --output outputs/motion/M02_comparison_rerun
```

Choisir un dossier neuf. Sans `--reader`, le rejeu conserve la référence binaire. Le benchmark requiert les artefacts M01 ; une absence ou une différence arrête la comparaison. Les anciens scripts d'inspection, de stéréo et d'export restent sur le lecteur de référence.

## Prochaine porte de validation

Le coût baisse, mais les mêmes zones de décor restent actives : l'optimisation n'améliore pas la distinction objet/caméra. Le délai réel entre début de mouvement et alerte, ainsi que les fausses alertes, restent non mesurés faute de GT temporelle.

Passer maintenant à M03 : constituer des segments annotés (début observable, incertitude, négatifs et mouvement de caméra), puis tester une estimation du mouvement apparent global et des résidus locaux. Garder M01/M02 comme références et séparer coût CPU, attente de fenêtre, persistance et retard accumulé. YOLO/stéréo/XYZ enrichiront ensuite les zones sans bloquer ce chemin rapide.
