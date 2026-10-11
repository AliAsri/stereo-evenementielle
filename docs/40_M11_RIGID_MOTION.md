# M11 — Compensation géométrique du mouvement apparent

7 octobre 2026. **Implémenté et exécuté sur référence 3D synthétique. Pas encore exécuté sur les événements réels.**

Cette étape suit l'accord utilisateur sur la revue de l'architecture proposée. Elle traite la limite de parallaxe de M10, avant une nouvelle optimisation de coût ou un entraînement YOLO. La fusion XYZ par objet reste distincte de cette estimation géométrique.

## Ce qui change

M03 ajuste une transformation 2D globale. Des points immobiles situés à des profondeurs différentes peuvent avoir des déplacements différents lorsque la caméra se déplace : M03 laisse alors des résidus sans mouvement propre d'objet.

M11 associe les points suivis à leur profondeur au premier instant, les reconstruit en 3D et estime la rotation/translation qui explique un ensemble dominant de correspondances. Il reprojette ces points au second instant pour comparer le déplacement attendu au déplacement observé.

**Résultat :** dans notre contrôle de caméra en translation devant une scène fixe à plusieurs profondeurs, les 52 points sur 124 que M03 signalait deviennent compatibles avec le modèle rigide. Ce résultat utilise une profondeur synthétique exacte ; il ne démontre pas encore un gain sur DSEC.

## Modèle, entrées et conventions

`src/pfe_events/rigid_motion.py` fournit `estimate_rigid_motion` :

- points correspondants `previous` et `current`, N×2, dans le même repère image rectifié 640×480 ;
- profondeurs axiales Z en mètres, une par point au premier instant ;
- matrice intrinsèque rectifiée K, sans distorsion résiduelle supposée ;
- dates entières `previous_us`, `current_us`, `depth_us` ;
- provenance explicite : `predicted`, `synthetic_reference` ou `dataset_reference`.

La profondeur doit avoir exactement la date du premier instant. Une profondeur ancienne ou future est refusée, comme un intervalle nul, négatif ou supérieur à 100 ms. Les coordonnées hors champ et une calibration invalide sont des erreurs ; une profondeur absente/invalidée produit une abstention pour le point. L'adaptateur aux événements réels devra aussi conserver les fenêtres d'accumulation associées à ces dates.

La transformation retournée applique `X_current = R × X_previous + t`. Ce n'est pas la trajectoire monde de la caméra. La reconstruction utilise `X=(u-cx)Z/fx`, `Y=(v-cy)Z/fy`, puis la projection dans la caméra suivante.

Estimation : PnP EPNP avec RANSAC, 500 itérations maximum, seuil 1,5 pixel et confiance demandée 0,999 ; raffinement LM sur les correspondances retenues. Les supports et résidus sont recalculés après raffinement. Le modèle requiert au moins 20 profondeurs utilisables, 16 points cohérents, 60 % d'inliers et une enveloppe couvrant au moins 10 % de l'image. Une géométrie 3D colinéaire est rejetée. Ces seuils sont des choix initiaux, non validés sur scène réelle.

La [documentation OpenCV PnP](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html) décrit l'estimation à partir de correspondances 3D–2D, les conventions de transformation et le contrôle robuste RANSAC.

## Sortie et abstention

| État d'un point | Signification |
|---|---|
| `RESIDUAL_CANDIDATE` | Résidu supérieur à 3 pixels après modèle rigide accepté |
| `MODEL_CONSISTENT` | Déplacement compatible avec le modèle au seuil choisi |
| `UNKNOWN` | Profondeur absente, projection invalide ou modèle global non accepté |

Un point compatible ne prouve pas qu'il est immobile. Un résidu ne prouve pas qu'un objet bouge : profondeur, correspondance ou calibration peuvent être fausses. `valid` valide les critères numériques du modèle dominant, pas l'identification certaine du décor.

Les références synthétiques ou dataset portent `oracle=true`. La pose vraie et les labels mobiles des contrôles sont réservés à l'évaluation ; l'estimateur ne les reçoit jamais. Seule la profondeur de référence est fournie à l'estimateur dans cette expérience, explicitement comme diagnostic oracle.

Il n'y a pas encore de regroupement en objets, de classe YOLO ni de persistance M10 appliquée aux résidus M11. Aucune vitesse d'objet ou reconnaissance d'arrêt n'est annoncée.

## Référence contrôlée et protocole

`rigid_controls.py` crée des scènes à deux instants, séparés de 20 ms : 108 points répartis dans l'image aux profondeurs 6/12/24 mètres, et 16 points d'une zone locale à 5 mètres. Les images sont calculées par projection perspective d'une géométrie 3D explicite.

Neuf scénarios × trois niveaux de bruit de localisation au second instant (écart-type 0, 0,2 et 0,5 pixel par coordonnée) × cinq seeds = **135 paires, 16 740 correspondances archivées**. Ces répétitions ne sont pas 135 scènes indépendantes. Sans bruit, les cinq seeds donnent les mêmes données. Les points sont parfaitement associés ; ni événements, ni LK, ni occultations ne sont simulés.

La profondeur est exacte sauf dans les scénarios d'absence et de biais. Les résultats ne modélisent donc pas la distribution d'erreurs réelle de SGBM. Les paramètres sont fixés avant la campagne dans `configs/m11_rigid_motion.json` et dans la configuration du module.

## Résultats par paire sans bruit

| Scénario | M03 : vrais / faux points candidats | M11 : vrais / faux points candidats | Limite ou observation |
|---|---:|---:|---|
| Scène et caméra fixes | 0 / 0 | 0 / 0 | 124 points compatibles |
| Caméra en translation, scène fixe | 0 / 52 | 0 / 0 | Parallaxe expliquée par la profondeur |
| Caméra en rotation, scène fixe | 0 / 0 | 0 / 0 | Cas simple accepté |
| Zone locale en translation, caméra fixe | 16 / 0 | 16 / 0 | Mouvement local retenu |
| Caméra et zone locale en mouvement | 0 / 36 | 16 / 0 | M03 manque ici les 16 points mobiles |
| Zone locale en rotation | 16 / 0 | 16 / 0 | M11 n'impose pas une direction commune aux résidus |
| Seulement 10 profondeurs disponibles | 0 / 52 | Inconnu pour les 124 points | Abstention globale, pas un succès de rejet |
| Profondeur locale multipliée par 3, scène fixe | 0 / 52 | 0 / 16 | **Échec : profondeur erronée → faux candidats** |
| Couche mobile majoritaire, 108 points mobiles | 36 / 16 | 0 / 16 | **Échec : modèle dominé par l'objet mobile** |

Les mêmes comptes M11 sont observés aux deux niveaux de bruit et sur les cinq seeds. Ce résultat très favorable sur les six cas simples reste limité à la construction choisie. Les deux contre-exemples échouent également avec bruit.

Dans les métriques exportées, le rappel utilise tous les points mobiles de référence ; un point mobile inconnu n'est pas retiré du dénominateur. L'abstention est comptée séparément. La précision est `null` quand aucune proposition n'existe ; le rappel est `null` quand aucun point mobile n'existe.

La comparaison porte sur les **résidus par point de M03**, pas sur les boîtes persistantes de M10. Les coordonnées sont adaptées à la résolution de travail de M03 et ses seuils historiques sont conservés. Ne pas présenter ces chiffres comme une comparaison de détecteurs d'objets complets.

## Visualisations

À gauche : modèle de similarité M03. À droite : modèle rigide avec profondeur de référence. Orange : candidat résiduel ; vert : compatible avec le modèle ; gris : inconnu. Le cercle violet indique un point réellement mobile dans la construction de la scène, uniquement pour l'évaluation.

![Parallaxe avec scène fixe](../outputs/motion/M11/camera_translation.png)

![Caméra et objet en mouvement](../outputs/motion/M11/combined.png)

Les contre-exemples sont aussi exportés : [profondeur biaisée](../outputs/motion/M11/biased_near_depth.png), [mouvement majoritaire](../outputs/motion/M11/dominant_moving_layer.png). Le vert ne doit jamais être légendé « immobile confirmé ».

## Preuves et reproduction

**117 tests réussis**, dont 12 nouveaux : géométrie, parallaxe, rotation locale, bruit, profondeur manquante, absence de mutation des entrées, dates, calibration, dégénérescence et contre-exemples.

Les six sources/protocole archivés correspondent à leurs empreintes. Les 135 paires NPZ sont relues sans pickle ; les résidus sont recalculés à partir des matrices exportées ; les 16 740 statuts et les neuf figures sont contrôlés. [Rapport](../outputs/motion/M11/summary.json), [vérification](../outputs/motion/M11/verification.json), [tests](../outputs/motion/M11/tests.log).

```powershell
# Conserver la campagne existante ; choisir un nouveau dossier.
.\.venv\Scripts\python.exe scripts/run_rigid_controls.py --output outputs/motion/M11_repeat
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/sync_markdowns.py
```

Le coût de la fonction est enregistré pour diagnostic, mais exclut lecture, représentation, suivi et profondeur : aucune cadence de système ni délai de détection n'en est déduit. Cette expérience à deux instants ne mesure pas le maintien temporel ou le début de mouvement.

## Passage aux événements réels : préparation vérifiée

Un [inventaire des entrées réelles](../outputs/motion/M11/real_input_inventory.json) recense 40 cartes S01 **prédites**, 20 sur chaque séquence train `04_b`/`04_e`, avec dates et empreintes. Elles proviennent de fenêtres de 50 ms et sont espacées d'environ 700 ms : ce ne sont pas des profondeurs disponibles toutes les 20 ms.

Prochaine expérience : pour chaque date S01 retenue sur train, construire les correspondances dans le repère rectifié à cette date et à +20 ms, puis échantillonner la profondeur prédite au premier instant. Vérifier support, couverture, résidus et abstention. Ne pas transférer directement des coordonnées natives M03 dans une carte rectifiée, ni prolonger arbitrairement une profondeur ancienne.

Ce premier diagnostic réel devra rester sans métrique de mobilité jusqu'à une référence relue. Un résultat avec GT profondeur/pose sera isolé comme oracle. Un grand nombre d'inliers ne suffira pas à écarter le contre-exemple d'un objet mobile dominant.

## Architecture retenue après la revue utilisateur

Conserver les branches à cadences distinctes avec dates/âges propres et les candidats sans classe YOLO obligatoire. La branche rapide signale un changement visuel ; la géométrie cherche à expliquer le déplacement du décor. Les cadences proposées restent des objectifs mesurables. La fraction de ROI XYZ doit être réglée sur train/debug et figée avant validation ; la formulation antérieure du document 09 a été corrigée. Aucun changement de `nbs` ni nouvel entraînement YOLO n'est effectué dans cette étape.
