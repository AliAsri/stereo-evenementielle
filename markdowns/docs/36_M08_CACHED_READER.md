# M08 — Réutiliser les accès HDF5 sans changer les détections

Date : 4 octobre 2026. Optimisation de lecture de la branche d'activité rapide, avec comparaison exacte à la référence.

## Diagnostic effectué avant l'optimisation

Le profilage porte sur les trois dernières secondes du segment train `zurich_city_04_b` de M07, au pas de 10 ms, précédées de 200 ms d'échauffement. Il utilise le lecteur M02 et le détecteur M01 inchangés.

Sur 300 fenêtres, `cProfile` attribue environ 1,90 s à la fonction de lecture et 1,58 s à la fonction d'activité. La lecture appelle 1 800 fois l'accès à un dataset du groupe HDF5, soit six accès par fenêtre. Ce poste représente environ 0,24 s dans le profil. Les lectures effectives de tableaux représentent aussi une part importante. Dans le détecteur, l'extraction des pixels occupés représente environ 0,30 s ; le calcul d'activité reste donc une autre piste.

Ces durées incluent l'instrumentation du profileur et ne doivent pas être comparées directement aux chronométrages ordinaires. [Profil texte](../outputs/motion/M08_profile/profile.txt) et [paramètres](../outputs/motion/M08_profile/summary.json).

## Modification réalisée

`CachedIndexedDSECReader` conserve ouverts les quatre datasets `x`, `y`, `t`, `p` pendant la durée du contexte. Le lecteur précédent récupérait leurs handles à répétition. Leur réutilisation évite ces ouvertures et permet aux caches de blocs HDF5 de rester attachés aux mêmes datasets entre fenêtres.

L'algorithme de recherche des bornes, le découpage exact `[début, fin)`, les limites mémoire par fenêtre, la validation des coordonnées, polarités et timestamps sont hérités sans modification. Le détecteur d'activité et ses seuils restent identiques. L'application ne précharge pas les prochaines fenêtres ; la décompression interne d'un bloc HDF5 peut porter sur des événements hors fenêtre, comme dans la référence, mais ils ne sont jamais transmis au détecteur.

Les limites de cache observées sont enregistrées par champ. Sur cette machine, elles sont de 8 Mio par dataset, soit un plafond configuré total de 32 Mio pour les quatre caches persistants. Ce chiffre n'est pas une mesure de la RAM totale du processus. À la sortie du contexte, le fichier et les handles sont fermés.

Le nouveau lecteur est une classe distincte dans `src/pfe_events/dsec_cached.py`. Les sources M01/M02 et leurs rapports historiques sont préservés ; les anciens lanceurs continuent d'utiliser leur lecteur d'origine.

## Comparaison fixée avant l'exécution

Le protocole `configs/m08_cached_reader.json` réutilise exactement les segments centraux de 12 secondes de M07 sur les deux séquences train `04_b` et `04_e`.

**Comparaison appariée :** pas 10 et 20 ms, lecteurs ouverts simultanément, ordre de passage inversé à chaque fenêtre. Les appels de lecture et d'activité sont chronométrés séparément ; les comparaisons et le hachage des événements sont hors chronométrage. Tous les champs événementiels et tous les champs de sortie du détecteur sont comparés : types, valeurs des tableaux, cartes, propositions, timestamps et indicateurs. L'échauffement est également contrôlé.

**Rejeu cadencé autonome :** pas de 10 ms, chaque lecteur dans un passage séparé, deux répétitions sur les deux séquences. Ordre des cas inversé lors de la seconde répétition. Aucun saut de fenêtre. Les coûts et âges de sortie sont enregistrés dans les mêmes unités que M07.

Les caches du système ne sont pas vidés, la charge du poste n'est pas contrôlée expérimentalement et les passages autonomes ne sont pas simultanés. La comparaison appariée peut elle-même modifier l'état du cache. Les résultats doivent donc être lus par cas et avec les répétitions, sans transformer un gain local en garantie générale.

## Exécution et fichiers

```powershell
# Expériences déjà exécutées : choisir de nouvelles sorties pour les reproduire.
.\.venv\Scripts\python.exe scripts/profile_motion_cost.py --output outputs/motion/M08_profile_repeat
.\.venv\Scripts\python.exe scripts/benchmark_cached_motion.py --output outputs/motion/M08_repeat
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/sync_markdowns.py
```

[Rapport M08](../outputs/motion/M08/summary.json). Les sous-dossiers `paired/` et `paced/` conservent les CSV par fenêtre et les résumés. Les sources, configurations et empreintes sont archivées. Le profilage a son propre dossier `M08_profile`, ce qui sépare ses coûts instrumentés du benchmark ordinaire.

## Guide du code

- `src/pfe_events/dsec_cached.py` : sous-classe du lecteur indexé ; `__enter__` conserve les quatre datasets et expose leurs limites de cache ; `__exit__` ferme le contexte et libère les références. L'API `window(start_us, end_us, max_events)` est inchangée.
- `scripts/profile_motion_cost.py` : sélectionne le dernier bloc train de M07, exécute le profilage et archive la provenance. Aucun label consulté.
- `scripts/benchmark_cached_motion.py` : compare exactement les entrées et sorties avec deux détecteurs indépendants, puis exécute les rejeux cadencés via `paced_windows`. Toute divergence arrête l'expérience avec un statut d'échec.
- `tests/test_dsec_cached.py` : vérifie les limites et doublons de temps, fenêtres vides et parcours arrière, repli sur le lecteur de référence, refus de dépassement du budget, données corrompues, réutilisation et fermeture des handles.

L'équivalence des sorties prouve ici que l'optimisation ne modifie pas les résultats sur les cas vérifiés. Elle ne prouve pas que les zones détectées correspondent à des objets mobiles indépendamment de la caméra. Les annotations M06 restent nécessaires pour cette évaluation.


## Résultats appariés réellement obtenus

**3 600 fenêtres mesurées**, plus 60 fenêtres d’échauffement : **3 660 comparaisons exactes** réussies sur tous les champs événementiels et toutes les sorties d’activité. Aucun repli du lecteur indexé pendant ces cas.

| Séquence | Pas | Lecture médiane avant → après (ms) | Lecture + activité médiane avant → après (ms) | Réduction du coût médian total |
|---|---:|---:|---:|---:|
| `04_b` | 10 ms | 3,78 → 2,31 | 10,25 → 8,77 | 14,44 % |
| `04_b` | 20 ms | 7,67 → 5,97 | 16,47 → 14,73 | 10,54 % |
| `04_e` | 10 ms | 3,32 → 2,34 | 7,60 → 6,54 | 14,03 % |
| `04_e` | 20 ms | 4,93 → 3,92 | 10,94 → 9,97 | 8,87 % |

La réduction observée du coût médian lecture + activité varie de **8,87 à 14,44 %** sur ces cas. Il s’agit des comparaisons internes à M08 ; comparer directement ces chiffres avec ceux de M07 confondrait protocole, charge et caches.

## Rejeux autonomes à 10 ms

Huit passages complets de 12 secondes, **9 600 fenêtres**. Les deux lecteurs sont comparés dans chaque répétition ; leurs passages restent séparés dans le temps.

| Séquence | Répétition | Âge de sortie p95 référence → cache (ms) | Retard final référence → cache (ms) |
|---|---:|---:|---:|
| `04_b` | 1 | 997,22 → 261,11 | 1127,52 → 288,98 |
| `04_b` | 2 | 358,15 → 351,18 | 428,72 → 379,59 |
| `04_e` | 1 | 77,70 → 16,71 | 6,22 → 4,58 |
| `04_e` | 2 | 66,11 → 13,81 | 10,64 → 4,31 |

Le gain sur l'attente est très variable. Sur `04_b`, il est marqué au premier passage, mais le p95 passe seulement de 358,15 à 351,19 ms au second. Le p95 de service du lecteur optimisé est même un peu plus élevé lors de ce second passage autonome (12,69 contre 12,10 ms), malgré sa médiane inférieure. Il faut conserver cette variabilité, sans annoncer une réduction garantie du retard.

Sur `04_e`, le p95 d'âge de sortie atteint 16,71 puis 13,81 ms avec cache. Ce sont des mesures d'âge après fin de fenêtre, pas des temps depuis le début d'un mouvement. L'acquisition et l'affichage restent exclus.

## Vérification et décision

**91 tests automatisés réussis**, dont quatre nouveaux tests du lecteur avec cache. Les onze empreintes d'entrée/source et les snapshots sont vérifiés. Les 9 600 fenêtres cadencées sont contiguës et ne sont pas lues avant leur disponibilité ; leurs comptes d'événements concordent entre lecteurs et répétitions. Le lecteur original, son parent, le détecteur et l'ordonnanceur sont inchangés depuis M07. [Rapport de vérification](../outputs/motion/M08/verification.json).

Le lecteur avec cache est disponible pour les prochaines intégrations de la branche rapide ; les lanceurs historiques restent reproductibles avec leur lecteur d'origine. La modification améliore le coût médian sans modifier les sorties vérifiées. Elle ne suffit pas à garantir la cadence 10 ms, en particulier sur la fin de `04_b`.

Prochaine optimisation à examiner : le calcul d'activité, notamment l'extraction des pixels occupés et leur conversion en cellules de grille. Comparer toute modification à la référence sur tous les tableaux et propositions avant d'en mesurer le gain. Les annotations M06 restent la prochaine entrée nécessaire pour quantifier délai réel et fausses alertes ; aucun réglage de seuil ni qualité de mouvement n'a été sélectionné dans M08.
