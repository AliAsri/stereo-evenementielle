# M12 — Modèle géométrique sur événements réels et profondeur prédite

7 octobre 2026. **Exécuté sur deux séquences DSEC train, avec profondeur S01 prédite. Qualité de mobilité non évaluée.**

## Avancée

M11 utilisait des points et profondeurs synthétiques. M12 raccorde maintenant le modèle rigide aux événements réels : lecture causale, rectification, suivi temporel, échantillonnage de profondeur prédite et décision par résidu. Ni pose GT, ni profondeur GT, ni labels de mobilité ne sont chargés dans cette expérience.

Le raccord fonctionne sur 38 paires. Sur les 8 630 correspondances évaluables par les deux modèles, la similarité 2D produit 176 points candidats et le modèle géométrique 49. **Cette diminution ne mesure pas une réduction des fausses alertes.** Une suppression des vrais mouvements, notamment avec des images temporellement chevauchantes, reste possible.

## Données et temps

Les 40 cartes de profondeur prédites S01 inventoriées dans M11 sont toutes examinées, 20 par séquence train `zurich_city_04_b` et `zurich_city_04_e`. Elles sont espacées d'environ 700 ms. Les trajets de validation et le test réservé ne sont pas utilisés.

Pour une profondeur datée `t`, les événements gauches forment deux images :

- précédente : `[t − 50 ms, t)` ;
- courante : `[t − 30 ms, t + 20 ms)`.

La date de profondeur correspond à la fin de la première accumulation S01. Les images sont des accumulations causales, **pas des photographies instantanées**. Elles partagent 30 ms d'événements ; cela peut favoriser des correspondances de structures communes et réduire le mouvement estimé. Le modèle de projection à deux instants reste donc une approximation à examiner.

La dernière carte de chaque séquence ne dispose pas d'événements jusqu'à `t + 20 ms` : deux paires sont exclues explicitement pour `INCOMPLETE_EVENT_PAIR`. Aucune fenêtre incomplète n'est complétée silencieusement. Il reste 19 paires par séquence.

Les fenêtres espacées de 700 ms ne constituent pas un rejeu continu à 50 Hz. Aucun délai de début de mouvement, maintien d'alerte ou identification temporelle d'objet n'est mesuré.

## Chaîne exécutée

1. Vérifier les empreintes des cartes S01 et leurs dates, dimensions et matrice Q. Vérifier que la profondeur stockée correspond à la disparité prédite et à la calibration canonique du couple événementiel.
2. Lire les événements avec `CachedIndexedDSECReader`, puis appliquer le splat bilinéaire S01 à la résolution rectifiée 640×480.
3. Utiliser le canal total logarithmique du normaliseur S01 figé sur train. Aucune normalisation n'est réapprise.
4. Extraire au plus 400 points et les suivre avec Lucas–Kanade : fenêtre 21×21, pyramide de niveau 2, contrôle aller-retour ≤1 pixel rectifié. Rejeter suivis invalides, non finis ou hors champ.
5. Échantillonner la profondeur au point précédent, au plus proche pixel avec `floor(x+0,5)`, masque valide exigé. Ni remplissage des trous ni interpolation de profondeur. Un pixel répété n'apporte pas plusieurs supports indépendants ; un arrondi hors carte reste inconnu.
6. Appeler le modèle rigide M11 avec `depth_source='predicted'` et `oracle=false`. Ses seuils sont conservés, sans réglage après inspection de ces résultats.
7. Comparer à la similarité M03 sur **les mêmes correspondances rectifiées**. Les coordonnées sont adaptées à l'échelle de travail M03. Il s'agit de réutiliser son modèle mathématique ; ce ne sont pas ses sorties historiques natives ni les boîtes persistantes M10.

La profondeur des points sans support valide demeure inconnue. Un modèle accepté signifie que ses critères de support sont satisfaits ; cela ne prouve pas que le mouvement dominant est celui du décor. Le contre-exemple M11 d'un objet mobile dominant reste applicable.

## Résultats

Les nombres ci-dessous cumulent les points à chaque paire, sans compter des objets distincts.

| Mesure | `04_b` | `04_e` | Total |
|---|---:|---:|---:|
| Paires traitées / examinées | 19 / 20 | 19 / 20 | 38 / 40 |
| Correspondances suivies | 7 521 | 7 297 | 14 818 |
| Points avec profondeur exploitable | 4 459 | 4 171 | 8 630 |
| Points inconnus | 3 062 | 3 126 | 6 188 |
| Points compatibles avec le modèle rigide | 4 430 | 4 151 | 8 581 |
| Points candidats du modèle rigide | 29 | 20 | 49 |
| Points candidats M03 sur le même support évaluable | 85 | 91 | 176 |
| Paires avec modèle rigide accepté | 19 | 19 | 38 |

La couverture est d'environ **58,2 % des correspondances suivies**. Les autres 41,8 % restent inconnues : ce ne sont pas des points déclarés statiques. Ce dénominateur diffère de la couverture S01 calculée sur les pixels de disparité GT ; les pourcentages ne doivent pas être comparés directement.

Les rapports conservent `real_motion_quality: null`. Ni précision, ni rappel, ni taux de fausses alertes, ni erreur de pose caméra ne sont disponibles sans une référence adaptée.

## Images

À gauche, similarité M03 ; à droite, modèle géométrique avec profondeur prédite. Orange : résidu supérieur à 3 pixels ; vert : compatible avec le modèle ; gris : inconnu. Les points sont dessinés à leur position courante sur l'image rectifiée.

![Première paire train 04_b](../outputs/motion/M12/zurich_city_04_b/pair_000.png)

Sur cette première paire `04_b`, plusieurs résidus proches de la chaussée disparaissent dans le modèle géométrique. Il reste quatre candidats et 219 points inconnus sur 387 suivis. Cette observation visuelle ne constitue pas une annotation du mouvement indépendant.

![Exemple à indice fixe 04_e](../outputs/motion/M12/zurich_city_04_e/example.png)

L'exemple `04_e` est la paire d'indice 10, fixé avant le calcul : 197 points compatibles et 191 inconnus, aucun candidat. Cette absence ne prouve pas l'absence d'objet mobile. Les deux `example.png` sont sélectionnés par indice, sans choisir le résultat le plus favorable. Toutes les 38 comparaisons restent disponibles dans les dossiers de séquences.

## Coût mesuré

| Séquence | Coût total médian avec profondeur en cache | p95 |
|---|---:|---:|
| `04_b` | 321,06 ms | 780,46 ms |
| `04_e` | 385,26 ms | 647,31 ms |

Ce coût inclut chargement de la profondeur déjà calculée, lecture des deux fenêtres, leurs représentations, suivi, échantillonnage et modèle rigide. Il exclut le calcul stéréo S01 d'origine, les vérifications SHA, le rendu, l'export et la comparaison M03. Il ne s'agit donc **ni d'une latence bout en bout, ni d'une cadence temps réel**. L'expérience ne soutient pas un traitement à 20 ms. Les images chevauchantes sont reconstruites indépendamment, sans réutilisation de calcul entre elles. La représentation des deux images domine le coût médian (281,46 / 341,54 ms) ; le modèle rigide seul prend environ 1,34 ms. Ces durées isolées ne doivent pas être additionnées comme des médianes d’une même paire.

## Vérifications et reproduction

- `src/pfe_events/rectified_tracking.py` : suivi vérifié et échantillonnage masqué.
- `scripts/run_real_rigid_motion.py` : contrôle des sources, exécution et figures.
- `configs/m12_real_rigid_motion.json` : protocole, dates, partitions et limites.
- `tests/test_rectified_tracking.py` : six tests supplémentaires ; **123 tests réussis** dans le projet.

Vérification terminée : 15 empreintes de sources/protocole et leurs snapshots, six empreintes des données réelles, 38 paires et 14 818 correspondances contrôlées. Les profondeurs échantillonnées sont confrontées aux cartes S01 originales ; les résidus sont recalculés à partir des matrices exportées.

Les artefacts permettent de relire les deux images, les points suivis, les profondeurs échantillonnées, K, les dates, les matrices de transformation et les états de chaque point. Sources, paramètres et données sont identifiés par empreintes SHA256 ; le contrôle des résidus est séparé des métriques de qualité réelle.

[Rapport complet](../outputs/motion/M12/summary.json), [vérification des artefacts](../outputs/motion/M12/verification.json), [journal des tests](../outputs/motion/M12/tests.log).

```powershell
# Le dossier M12 existant est conservé.
.\.venv\Scripts\python.exe scripts/run_real_rigid_motion.py --output outputs/motion/M12_repeat
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/sync_markdowns.py
```

## Prochaine étape

La priorité devient **vérifier le maintien du signal sur de vrais objets mobiles**, plutôt que chercher encore à diminuer le nombre de candidats. Préparer de courts extraits continus autour de dates train, avec vues sans prédictions pour relire les zones mobiles, le décor et les cas ambigus. Une comparaison de fenêtres chevauchantes et non chevauchantes devra contrôler l'effet du partage des événements, en tenant compte de leur durée et du déplacement attendu.

Les labels de classe DSEC/YOLO ne sont pas des labels de mobilité. Les métriques de mouvement restent suspendues tant que cette référence n'est pas exploitable. Un suivi interrompu, une profondeur manquante ou un modèle dominé par un objet mobile doivent rester visibles. YOLO, XYZ et les optimisations restent nécessaires au projet, mais ne remplacent pas cette vérification de la séparation objet/caméra.
