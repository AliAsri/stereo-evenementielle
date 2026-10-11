# S01 — Première baseline stéréo événementielle exécutable

Date : 3 octobre 2026. Cette note décrit du code exécuté et des résultats mesurés. S01 transforme deux flux événementiels en disparité et profondeur de surface. Il n'utilise aucun réseau profond et ne produit encore aucune boîte détectée ni position 3D d'objet.

## But et périmètre

Vérifier qu'une accumulation causale gauche/droite permet une première estimation cohérente avec la géométrie DSEC, mesurer ses erreurs et conserver ses échecs. Cette référence permettra de comparer les améliorations de représentation, la fusion et un éventuel modèle stéréo profond.

Le pilote utilise 20 fenêtres par séquence : `zurich_city_04_e` et `04_b` côté train/debug, `thun_00_a` en validation locale. Les deux séquences `04` appartiennent au même groupe et ne constituent pas deux trajets indépendants. `zurich_city_09_b` est réservé, non téléchargé et non évalué. Il ne s'agit pas du split officiel de compétition.

## Flux de données, dans l'ordre réel

1. Lire calibration, cartes de rectification et dates GT ; vérifier dimensions et collection PNG complète.
2. Ajouter l'offset propre à chaque flux pour travailler dans l'horloge absolue DSEC.
3. Choisir uniformément vingt dates ayant une fenêtre commune complète `[t−50 000,t[` µs. La GT à `t` correspond à la date de sortie, sans intégrer d'événement futur.
4. Répartir les événements entre voisins rectifiés avec des poids bilinéaires ; compter les rejets hors champ.
5. Construire `log1p(C+)`, `log1p(C−)`, `log1p(C++C−)`, appliquer les échelles train figées et convertir en uint8.
6. Donner le **canal total** gauche/droite à SGBM ; vérifier sens inverse et support d'activité.
7. Convertir la sortie fixe `/16`, conserver NaN aux pixels rejetés, calculer XYZ via Q et enregistrer Z en mètres.
8. Ouvrir la GT `/256` pour l'évaluation. Elle ne sert jamais de valeur de repli.

L'ajustement du normaliseur est distinct d'un apprentissage de réseau. Il utilise huit dates train au total, deux vues et variantes natives/rectifiées : 32 images de comptage. Le percentile 99,5 % des valeurs logarithmiques positives échantillonnées, seed 42, donne les échelles 2,9957323 / 2,5635023 / 3,1354942. Les paramètres et provenances sont écrits avant l'évaluation de validation. [Détail de la représentation](04_EVENT_REPRESENTATIONS.md).

## Paramètres figés pour cette exécution

| Paramètre | Valeur |
|---|---|
| Taille | 640×480, aucun redimensionnement |
| Fenêtre causale | 50 000 µs |
| Recherche | minDisparity=0, numDisparities=96 |
| Bloc | 5×5, un canal |
| Pénalités | P1=200, P2=800 |
| Unicité | 10 |
| Préfiltrage | preFilterCap=31 |
| Contrôle interne | disp12MaxDiff=1 |
| Petites composantes | speckleWindowSize=50, speckleRange=2 |
| Mode | SGBM_3WAY |
| Contrôle inverse explicite | différence <=1,5 px, échantillon droit arrondi |
| Support activité | au moins un pixel non nul dans le voisinage 5×5 de chaque vue |
| Threads OpenCV | 1 |

Les contraintes de l'API, les pénalités et l'échelle fixe sont documentées dans la [référence officielle StereoSGBM](https://docs.opencv.org/4.x/d2/d85/classcv_1_1StereoSGBM.html). Aucun balayage de paramètres n'a été réalisé sur validation. Ces valeurs constituent un départ reproductible, pas un optimum revendiqué.

Dans le sens inverse, les images droite et gauche sont retournées horizontalement avant le matching positif, puis la carte est remise dans le sens original. Les deux cartes représentent ainsi `u_L−u_R`. Une disparité gauche `d` au pixel `u` est comparée à la carte inverse au pixel droit `round(u−d)`. Les pixels hors image, sans activité, sans résultat positif ou incohérents sont rejetés. Cette vérification n'est pas une probabilité calibrée de confiance.

## Lecture des mesures

L'EPE est la moyenne de l'erreur absolue sur les pixels où GT et prédiction sont valides. Une petite EPE peut cacher de nombreuses abstentions : on publie donc la couverture `pixels évalués / pixels GT valides`. Bad3 compte les erreurs strictement supérieures à trois pixels sur l'intersection. Le diagnostic Bad3-ou-absent compte aussi chaque GT sans prédiction comme échec ; c'est un indicateur local.

Les agrégats sont pondérés par le nombre de pixels, pas par le nombre d'images. La MAE Z compare des surfaces au même pixel rectifié, sur l'intersection valide. Les petites disparités amplifient les erreurs de distance : une EPE proche d'un pixel ne garantit pas la distance précise de tout objet.

Sur validation : **EPE 1,045 px, couverture 36,00 %, Bad3 4,26 % des évalués, Bad3-ou-absent 65,54 % de toute la GT**. La MAE Z conditionnelle vaut 1,421 m. Aucun pixel GT échantillonné n'est hors de la plage de recherche. [Résultats par séquence et limites](13_RESULTS.md).

## Sorties et traçabilité

`outputs/stereo/S01/` conserve `config.json`, `normalizer.json`, `summary.json`, puis un dossier par séquence avec rapport par date, vingt cartes NPZ, exemple temporel central, cas d'échec et pseudo-image native avec annotations officielles.

Chaque NPZ contient `disparity_px`, `valid`, `raw_sgbm_q4`, `depth_m`, `q`, `window_end_us` et `window_us`. Les absences restent NaN. `frame_000069.npz` désigne l'index dans la liste de timestamps, pas nécessairement le numéro porté par le PNG GT ; le chemin exact GT figure dans le rapport.

Résumé, tableau CSV et bilan de vérifications sont aussi dans `outputs/reports/`, réservé aux preuves légères. D00 reste intact. Les archives ont des hashes calculés localement ; aucune signature de l'auteur n'est prétendue. Les sorties S01 occupent environ 21,3 Mio ; le corpus brut avec archives environ 3,19 Gio.

## Vérifications exécutées

Les 21 tests réussis couvrent slicing, géométrie, comptage, conservation bilinéaire, normalisation train-only, échelle de disparité, sens inverse sur plan synthétique et cas sans estimation. Les six flux ont été audités sur **723 007 877 timestamps** non décroissants.

Après l'expérience, les 60 NPZ ont été relus séparément : concordance masque/valeurs finies, disparité conservée égale à sortie brute/16, Z conforme à `fx*B/d` pour les calibrations canoniques vérifiées. EPE, Bad3 et couverture ont été recalculées depuis les fichiers, avec concordance aux rapports. Les hashes du code ont été comparés. Cela contrôle les unités et la chaîne de calcul, sans garantir que chaque correspondance conservée soit correcte.

La vue native `04_b` sélectionnée contient huit piétons annotés et douze boîtes au total. La superposition est visuellement plausible dans le repère natif. Le cas difficile de validation montre de grandes régions GT sans estimation et des erreurs localisées ; il reste visible dans `worst_coverage_or_error.png`. Aucun réglage n'a été modifié après son inspection.

## Reproduction et suite

Socle mesuré : Windows, Python 3.14.6, NumPy 2.5.3, OpenCV headless 4.14.0.94 ; versions exactes dans `requirements-inspection-lock.txt` et le rapport. Le cahier des charges annonce un Ryzen 5 PRO 7535U avec 16 Go ; l'exécution identifie la plateforme logicielle, sans inventaire matériel indépendant complet. Aucun GPU n'est utilisé.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/run_stereo_baseline.py --full-timestamp-audit --output outputs/stereo/S01_rerun
```

Le dossier de destination doit être neuf. Le programme refuse l'écrasement et conserve les sorties partielles en cas d'erreur. Seul un `summary.json` final marque une exécution terminée.

La priorité suivante est l'export vérifié des labels/pseudo-images puis le pilote YOLO. La fusion devra s'abstenir en l'absence de support. Avant toute promesse de rapidité, profiler la représentation : la médiane lecture→profondeur de validation est environ 505 ms, hors évaluation/écriture, premier passage inclus. Ce code de référence ne valide pas le temps réel.
