# M09 — Calcul d'activité avec table pixel → cellule

Préparation : 4 octobre 2026. Reprise et vérification : 7 octobre 2026. Optimisation du calcul d'activité, à paramètres et sorties identiques à M01.

## Problème traité

Après M08, le lecteur HDF5 réutilise ses datasets, mais le calcul d'activité reste coûteux. À chaque fenêtre, M01 convertit les indices des pixels occupés en indices de cellules avec plusieurs divisions et modulos entiers. La géométrie ne change pourtant pas pendant le rejeu.

M09 construit une table pixel → cellule à l'initialisation du détecteur. Pendant le traitement, l'accès `pixel_to_cell[occupied]` remplace ce calcul géométrique répété. Deux adaptations locales complètent la modification : extraction des pixels occupés depuis un masque booléen, et conversions de coordonnées sans copie supplémentaire lorsque leur type est déjà celui requis.

L'absence de copie ne supprime pas les conversions nécessaires : les coordonnées DSEC sont notamment en `uint16` et doivent encore être converties en entier natif pour le comptage. Les tableaux d'entrée ne sont jamais modifiés.

La table de 640 × 480 entiers natifs occupe **2 457 600 octets, soit 2,344 Mio** sur l'environnement 64 bits utilisé. C'est le stockage additionnel permanent de la table, pas la mémoire totale du processus. Un masque booléen temporaire de 307 200 éléments est aussi créé lors du repérage des pixels occupés. La table est marquée en lecture seule.

## Contrats préservés

Le comptage événementiel, le support en pixels distincts, les taux, le seuil, la persistance temporelle, les composantes connexes et leurs boîtes sont inchangés. Les contrôles de coordonnées, timestamps, ordre et continuité sont exécutés avant la mise à jour de l'état.

La classe `LookupActivityDetector` reprend l'API d'`ActivityDetector`. Le corps du calcul est conservé dans une classe distincte pour permettre une comparaison directe avec la référence, sans modifier `motion.py`. Ce choix impose de maintenir la cohérence des validations entre les deux classes ; les tests d'équivalence sont indispensables lors de changements futurs.

## Expérience fixée avant l'exécution

Le protocole `configs/m09_lookup_activity.json` réutilise les quatre cas train de M07 : deux séquences, même segment de 12 secondes par séquence, pas 10 et 20 ms. **Les deux variantes utilisent le lecteur avec cache M08**. M09 mesure donc l'effet du changement de détecteur, sans comparer simultanément deux lecteurs différents.

Pour la comparaison appariée, chaque fenêtre est lue une seule fois et transmise aux deux détecteurs dans un ordre alterné. Les tableaux d'événements sont rendus non modifiables. Toutes les sorties sont comparées exactement, ainsi que l'état de persistance et le timestamp précédent. Comparaison et hachage sont hors chronométrage.

Le coût total apparié est la somme de la lecture partagée et du calcul propre à chaque variante. Il ne constitue pas une mesure de débit de deux pipelines autonomes. Des passages séparés cadencés à 10 ms sont donc aussi exécutés : deux variantes × deux séquences × deux répétitions, ordre inversé à la seconde répétition, sans sauter de fenêtres.

Les caches du système ne sont pas vidés et la charge du poste varie. Comparer les résultats internes à M09 ; ne pas additionner mécaniquement les pourcentages de gain M08 et M09, ni comparer des chronométrages issus de protocoles différents.

## Commandes et preuves

```powershell
# La campagne complète est conservée dans M09_20261007 ; utiliser une nouvelle sortie.
.\.venv\Scripts\python.exe scripts/benchmark_lookup_activity.py --output outputs/motion/M09_repeat
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/sync_markdowns.py
```

[Résumé de la campagne complète](../outputs/motion/M09_20261007/summary.json). Les sous-dossiers `paired/` et `paced/` conservent les lignes de mesure CSV et les résumés ; `source_snapshot/` conserve le code réellement exécuté. La configuration et les empreintes sont dans le résumé.

## Guide du code

- `src/pfe_events/motion_lookup.py` : table immuable construite après validation de la configuration, remplacement du calcul des indices de cellule, mêmes résultats que la référence. Entrées : dictionnaire événementiel et bornes entières contiguës ; sortie : cartes, pixels occupés, régions, taux et timestamps au format M01.
- `scripts/benchmark_lookup_activity.py` : lecture partagée, chronométrage alterné des deux détecteurs, vérification exacte des sorties et de l'état, puis rejeux cadencés indépendants. Toute divergence arrête l'expérience.
- `tests/test_motion_lookup.py` : séquences artificielles avec seed fixe, différentes géométries et tailles de cellule, types entiers, bords partiels, entrée vide, pixel chaud, persistance, entrées invalides et tableaux non modifiables. Les tableaux rendus ne sont pas altérés par une mise à jour ultérieure.

Ces tests synthétiques ne sont pas des mesures de détection réelle. L'expérience DSEC vérifie l'équivalence et le coût ; la qualité du mouvement et les fausses alertes restent à évaluer avec les annotations M06.


## Reprise de la campagne le 7 octobre

La première campagne du 4 octobre, conservée dans `outputs/motion/M09`, s’est arrêtée après quatre comparaisons appariées et quatre rejeux de la première répétition. Son fichier indiquait encore RUNNING lors de la reprise ; aucune seconde répétition complète n’y est enregistrée. Ce dossier reste une archive partielle et ne doit pas être présenté comme un protocole terminé.

Les treize empreintes des sources/entrées ont été revérifiées avant la reprise. La campagne complète a été relancée dans `outputs/motion/M09_20261007`, sans mélanger des répétitions séparées de plusieurs jours. Le journal des 96 tests réussis est conservé avec les nouveaux résultats.


## Résultats appariés du 7 octobre

**3 600 fenêtres mesurées et 60 fenêtres d’échauffement** : 3 660 comparaisons exactes de toutes les sorties et de l’état de persistance. Les empreintes des événements sont aussi identiques à celles de M08 sur les quatre segments.

| Séquence | Pas | Calcul médian référence → table (ms) | Réduction du calcul médian | Lecture partagée + calcul, médiane référence → table (ms) |
|---|---:|---:|---:|---:|
| `04_b` | 10 ms | 4,09 → 3,40 | 16,91 % | 7,19 → 6,50 |
| `04_b` | 20 ms | 4,95 → 4,21 | 15,01 % | 8,85 → 7,84 |
| `04_e` | 10 ms | 3,59 → 2,94 | 18,14 % | 7,03 → 6,38 |
| `04_e` | 20 ms | 5,34 → 4,64 | 13,07 % | 10,47 → 9,71 |

Le coût médian du calcul baisse de **13,07 à 18,14 %** ; la somme lecture partagée + calcul baisse de **7,28 à 11,40 %** sur ces cas. Le tableau mesure l’ensemble des trois modifications, sans attribuer expérimentalement le gain à chacune séparément.

## Rejeux cadencés indépendants à 10 ms

Huit passages complets de 12 secondes : **9 600 fenêtres**. La référence utilise déjà le lecteur avec cache M08.

| Séquence | Répétition | Âge de sortie p95 référence → table (ms) | Retard final référence → table (ms) |
|---|---:|---:|---:|
| `04_b` | 1 | 17,56 → 109,44 | 10,11 → 75,81 |
| `04_b` | 2 | 260,16 → 141,18 | 264,49 → 55,19 |
| `04_e` | 1 | 14,07 → 8,58 | 3,94 → 4,92 |
| `04_e` | 2 | 12,16 → 9,04 | 5,38 → 6,73 |

**Résultat mitigé pour l'âge des sorties.** Sur `04_b`, le premier passage avec table est moins bon (109,44 ms contre 17,56 ms au p95), alors que le second est meilleur (141,18 ms contre 260,16 ms). Sur `04_e`, les deux passages avec table améliorent le p95 (8,58 et 9,04 ms contre 14,07 et 12,16 ms). Il n'est donc pas démontré que cette optimisation améliore systématiquement le retard en conditions cadencées.

Le coût apparié mesure une différence de calcul sur les mêmes événements ; les passages autonomes incluent aussi la lecture, les caches et l'ordonnancement du système. La cause exacte de la variabilité entre passages n'a pas été isolée. Ne pas en attribuer arbitrairement la cause à Windows, à OneDrive ou à une chauffe du processeur.

Même un p95 inférieur à 10 ms ne garantit pas toutes les fenêtres sous 10 ms. L'âge mesuré commence à la fin de la fenêtre et exclut acquisition et affichage ; ce n'est pas le délai depuis le début physique du mouvement.

## Vérification et décision

**96 tests réussis**, dont cinq nouveaux contrôles du détecteur. Treize sources/entrées et leurs snapshots vérifiés ; 9 600 fenêtres cadencées contiguës sans lecture anticipée. Les comptes d'événements sont identiques entre variantes et répétitions, avec 115 668 807 événements par passage sur `04_b` et 113 533 698 sur `04_e`. La référence M01, les lecteurs et l'ordonnanceur restent inchangés depuis M08. [Vérification](../outputs/motion/M09_20261007/verification.json).

Conserver la variante avec table comme option d'implémentation équivalente sur les cas vérifiés et moins coûteuse en médiane. Ne pas annoncer une cadence 10 ms garantie ni remplacer silencieusement les références historiques.

**Prochaine étape : intégrer les optimisations M08/M09 dans un démonstrateur de la branche rapide**, avec choix explicite référence/optimisée et affichage du coût, de l'âge de sortie et du retard. Garder le terme « activité événementielle » tant que les annotations de mouvement ne permettent pas de confirmer le mouvement indépendant d'un objet. La comparaison qualité/délai réel via M06 reste en attente des annotations relues.
