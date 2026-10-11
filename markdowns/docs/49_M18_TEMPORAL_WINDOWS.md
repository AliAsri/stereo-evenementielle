# M18 — Comparaison des fenêtres temporelles

**10 octobre 2026 — expérience exécutée sur les données train.** La fenêtre de 20 ms n'améliore pas le diagnostic de mobilité sur les dates examinées. Elle réduit le support stéréo dans les boîtes de référence. La configuration 50 ms reste notre référence ; aucune variante n'est déclarée détecteur validé d'objets mobiles.

## Protocole contrôlé

Les six dates et 22 boîtes vérifiées de M16 sont conservées. La comparaison principale porte uniquement sur les quatre dates déjà traitables dans M17 : frames MOD 134 et 267 de `zurich_city_04_b` et `zurich_city_04_e`, soit 15 boîtes. Les deux dates de démarrage et leurs sept boîtes sont analysées séparément.

- Fenêtre longue : gauche précédente et droite précédente `[t−70, t−20)` ms, gauche courante `[t−50, t)` ; chevauchement temporel gauche de 30 ms.
- Fenêtre courte : gauche précédente et droite précédente `[t−40, t−20)` ms, gauche courante `[t−20, t)` ; aucun chevauchement.
- Pas de 20 ms, normaliseur S01, paramètres SGBM, suivi, compensation rigide, seuil de résidu de 3 px et marges d'association −5/0/+5 px conservés.
- Profondeur S01 prédite recalculée pour chaque représentation à la date précédente ; pas de GT dans l'inférence et pas de boîtes pour estimer le modèle caméra.
- Contrôle des empreintes des sources, données et configurations contre M17. Les six sorties 50 ms reproduisent exactement les tableaux et métadonnées M17 hors durées.

Changer la fenêtre modifie simultanément densité événementielle, chevauchement, suivi, stéréo et estimation de pose. L'expérience ne mesure donc pas un effet isolé du chevauchement. Les sommes de points comparent des populations différentes.

## Résultat principal : quatre dates communes

| Mesure cumulée, sauf durées | 50 ms | 20 ms |
|---|---:|---:|
| Événements des images courantes | 1 758 994 | 697 782 |
| Correspondances suivies et contrôlées | 1 558 | 1 558 |
| Correspondances avec profondeur exploitable | 928 | 761 |
| Correspondances inconnues | 630 | 797 |
| Points suivis dans l'union des boîtes | 201 | 130 |
| Points avec profondeur dans l'union des boîtes | 141 | 72 |
| Candidats résiduels dans l'union des boîtes | 0 | 0 |
| Candidats résiduels hors des boîtes | 0 | 1 |
| Temps CPU médian par paire, calcul stéréo inclus | 544,96 ms | 324,08 ms |
| Temps CPU maximal observé | 948,86 ms | 508,22 ms |

Un point inclus dans deux boîtes compte une seule fois dans leur union. L'égalité de 1 558 correspondances ne signifie pas que les deux méthodes suivent les mêmes points.

| Diagnostic par boîte, marge 0 px | 50 ms | 20 ms |
|---|---:|---:|
| Sans correspondance suivie | 4 | 6 |
| Avec suivi mais sans profondeur exploitable | 3 | 3 |
| Avec points évalués sans résidu >3 px | 8 | 6 |
| Avec candidat résiduel | 0 | 0 |

Les marges −5/+5 px ne font apparaître aucun candidat dans les boîtes. Les petites boîtes devenues vides à −5 px restent explicitement identifiées dans le rapport JSON.

## Exemple qui explique la limite

À la frame 134 de `04_e`, les tubes 5 et 7 possèdent respectivement 2 et 4 points suivis avec 50 ms, puis aucun avec 20 ms. Leurs points avec profondeur passent de 1 et 4 à zéro. Une stéréo plus dense, seule, ne réparera pas une absence de correspondances temporelles.

![Comparaison sur 04_e, frame 134](../outputs/motion/M18/comparison/zurich_city_04_e_000134.png)

Les rectangles cyan sont des références publiques. Les points verts sont compatibles avec le modèle rigide, les gris inconnus, les orange candidats résiduels. Le candidat de la fenêtre courte est hors des boîtes, avec un résidu de 21,70 px. Sa présence ne prouve ni objet mobile ni fausse alerte : les régions non annotées ne sont pas des négatifs certifiés. Les limites de projection RGB/événements de M16 restent applicables.

## Démarrage, séparé de la comparaison principale

Les deux premières dates nécessitent 70 ms d'historique pour la fenêtre longue contre 40 ms pour la courte. Elles sont donc non traitables en 50 ms et traitables en 20 ms.

La variante courte y produit 771 correspondances, dont 318 avec profondeur, et deux candidats hors des boîtes. Sur sept boîtes : six contiennent des points évalués sans résidu et une manque de profondeur. Aucun candidat dans les boîtes. Ces dates supplémentaires ne sont pas ajoutées au bilan principal et ne prouvent pas un gain de délai de détection d'objet.

## Performances et portée

Les temps proviennent d'une seule exécution hors ligne par configuration, sans benchmark entrelacé ni mesure d'âge de sortie. Initialisation et rendu sont exclus. Ils suggèrent un coût moindre avec moins d'événements, mais ne démontrent pas un gain reproductible de cadence. Les deux médianes restent très supérieures au pas de 20 ms.

L'absence de résidus dans les boîtes est un résultat défavorable conservé, pas une preuve d'immobilité. Quatre dates train ne permettent ni précision/rappel objet global, ni généralisation, ni délai réel de début de mouvement. Le modèle rigide dominant n'est pas une pose caméra de référence.

## Reproduire et vérifier

Depuis la racine, choisir des dossiers de sortie neufs :

```powershell
.\.venv\Scripts\python.exe scripts/run_reference_diagnostic.py --config configs/m18_50ms.json --output outputs/motion/M18_replay/long_50ms
.\.venv\Scripts\python.exe scripts/run_reference_diagnostic.py --config configs/m18_20ms.json --output outputs/motion/M18_replay/short_20ms
.\.venv\Scripts\python.exe scripts/compare_reference_windows.py --long outputs/motion/M18_replay/long_50ms --short outputs/motion/M18_replay/short_20ms --output outputs/motion/M18_replay/comparison
```

- [Rapport complet, empreintes et transitions par boîte](../outputs/motion/M18/comparison/summary.json).
- [Protocole 50 ms](../configs/m18_50ms.json), [protocole 20 ms](../configs/m18_20ms.json).
- [Comparateur](../scripts/compare_reference_windows.py), [tests des contrats temporels](../tests/test_reference_windows.py).
- Contrôle global : **182 tests réussis, 90 fichiers Python et 28 aides CLI vérifiés** ; [journal](../outputs/checks/M18/tests.log).
- Six panneaux comparatifs générés ; panneaux `04_b/134` et `04_e/134` inspectés visuellement.

## Décision et suite

Conserver 50 ms comme référence M17, sans abaisser le seuil pour obtenir artificiellement des candidats. Poursuivre par M19 : audit du checkpoint EMatch, de la représentation causale et de la provenance d'entraînement, avant une inférence bornée sur train. Comparer ensuite profondeur à support temporel fixé, puis couverture supplémentaire ; traiter séparément les boîtes sans suivi. Aucun apprentissage ni changement du test réservé n'est déclenché par M18.
