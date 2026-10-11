# M17 — Diagnostic des candidats dans les boîtes publiques

**10 octobre 2026.** Le prototype géométrique est exécuté aux dates train vérifiées dans M16, puis ses points sont rapprochés des annotations publiques. **Aucun résidu ne dépasse le seuil actuel de 3 px sur les quatre paires traitables.** Les références révèlent donc une limite concrète de cette configuration ; cette expérience ne valide pas encore une détection d'objets mobiles.

## Bilan des 22 boîtes

| Diagnostic avec les boîtes originales | Nombre | Interprétation |
|---|---:|---|
| Historique insuffisant | 7 | Aux deux premières dates, environ 50 ms sont disponibles, alors que le protocole exige 70 ms |
| Aucun point suivi validé dans la boîte | 4 | Le modèle ne peut pas examiner le mouvement de cette région |
| Points suivis, aucune profondeur exploitable | 3 | Le modèle rigide s'abstient pour ces points |
| Points avec profondeur, aucun résidu supérieur à 3 px | 8 | Le modèle n'émet pas de candidat dans ces boîtes ; cela ne prouve pas l'immobilité |

Les 15 boîtes avec historique complet correspondent aux frames 134 et 267 de `04_b` et `04_e`. Il s'agit de boîtes à des dates, pas de 15 identités distinctes. Aucun pourcentage de rappel objet n'est déduit de ces comptes : le modèle produit encore des états de points, sans détecteur de boîtes prédites ni règle IoU validée.

[Rapport complet](../outputs/motion/M17/summary.json) · [Analyse des amplitudes](../outputs/motion/M17/support_analysis.json) · [Protocole figé](../configs/m17_reference_diagnostic.json).

## Protocole exécuté

Pour une référence datée `t`, le protocole conserve les fenêtres M12 :

```text
Image précédente gauche/droite : [t − 70 ms, t − 20 ms)
Image courante gauche          : [t − 50 ms, t)
Profondeur prédite à t − 20 ms ; suivi et modèle rigide jusqu'à t
Durée de chaque image : 50 ms ; écart : 20 ms ; chevauchement : 30 ms
```

Les deux dates initiales sont conservées comme abstentions explicites. Aucune fenêtre tronquée, profondeur future, interpolation de profondeur ou date de remplacement n'est utilisée. Leur activité courante peut être affichée, car la fenêtre courante de 50 ms est complète.

La profondeur est **recalculée avec S01** sur les événements stéréo à la date précédente : SGBM, 96 disparités, bloc de 5 pixels, contrôles d'activité et de cohérence gauche-droite. Même normaliseur appris sur train, même suivi M12, mêmes seuils du modèle rigide. Aucune GT de profondeur, classe YOLO ou boîte de référence n'entre dans ces calculs.

Toutes les inférences sont enregistrées avant la phase qui consulte les boîtes. Le diagnostic associe ensuite les points selon leur position courante dans chaque rectangle `x1 ≤ x < x2`, `y1 ≤ y < y2`. Un point dans une boîte peut appartenir au fond visible à l'intérieur ; l'association ne certifie pas son appartenance physique à l'objet.

## Ce que l'on observe

| Paire | Points suivis | Profondeur exploitable | Résidu maximal, tous points évalués | Coût CPU complet mesuré |
|---|---:|---:|---:|---:|
| `04_b / 134` | 398 | 257 | 1,102 px | 689,0 ms |
| `04_b / 267` | 396 | 273 | 2,000 px | 1 151,3 ms |
| `04_e / 134` | 384 | 203 | 2,341 px | 620,6 ms |
| `04_e / 267` | 380 | 195 | 1,426 px | 417,9 ms |

Au total : **1 558 correspondances**, dont **928 avec profondeur** et **630 inconnues**. Tous les points évalués sont compatibles avec le modèle selon le seuil fixé. Cela ne garantit pas que le modèle dominant soit la vraie pose caméra : les objets mobiles peuvent aussi contribuer au consensus.

Dans l'union des boîtes, il existe 201 points suivis distincts, dont 141 avec profondeur. Un point est partagé par deux boîtes de `04_e/267` ; il n'est pas compté comme deux observations indépendantes. Le résidu maximal à l'intérieur des boîtes vaut **1,516 px**. Sur 20 ms, le seuil de 3 px correspond à une vitesse résiduelle apparente de 150 px/s, sans être une vitesse 3D ni un seuil universel de mobilité.

Les déplacements médians bruts sont de 1,14 à 2,80 px selon la paire, mais les résidus médians après le modèle sont de 0,118 à 0,238 px. Les déplacements existent donc ; ils sont largement expliqués par le modèle ou restent sous le seuil. Le chevauchement des représentations, la faible vitesse relative, le consensus et les erreurs de profondeur sont des explications possibles, **pas des causes isolées démontrées** par cet essai.

### Suivi et profondeur : obstacles distincts

Sur `04_e/267`, les tubes 6 et 7, correspondant aux véhicules devant, n'ont aucun point suivi retenu ; leurs boîtes ne présentent qu'environ 0,4 % et 3,8 % de pixels actifs dans cette représentation. Le manque de support existe avant la décision sur le résidu. Diminuer le seuil de résidu ne peut pas créer ces correspondances manquantes.

Deux autres boîtes sans profondeur sont les tubes 9 de `04_b/134` et 12 de `04_b/267`. Leurs 8 et 17 points suivis précédents se trouvent tous dans les 96 premières colonnes. Les cartes prédites n'ont aucune profondeur valide dans cette bande, ce qui est cohérent avec la zone défavorable de la recherche SGBM à 96 disparités. Le troisième cas sans profondeur, tube 7 de `04_b/134`, est central et contient un seul point : cette explication par le bord ne s'y applique pas. [Contrôle des cartes au bord gauche](../outputs/motion/M17/left_border_support.json).

Il ne faut ni remplir ces trous par une GT, ni assimiler profondeur absente et objet immobile. Les panneaux montrent les références en cyan, les points compatibles en vert et les points inconnus en gris. Les points orange indiqueraient un résidu dépassant le seuil ; aucun n'est présent ici.

![Diagnostic 04_b frame 134](../outputs/motion/M17/zurich_city_04_b_000134.png)

[Voir le manque de suivi sur 04_e frame 267](../outputs/motion/M17/zurich_city_04_e_000267.png).

## Sensibilité aux limites des boîtes

L'évaluation est répétée après retrait ou ajout de 5 px de chaque côté, **sans relancer ni modifier le détecteur**. Cette variation ne constitue pas une correction calibrée de parallaxe.

| Marge | Historique insuffisant | Région vide après réduction | Sans suivi | Sans profondeur | Points évalués sans résidu |
|---|---:|---:|---:|---:|---:|
| −5 px | 7 | 3 | 6 | 2 | 4 |
| 0 px | 7 | 0 | 4 | 3 | 8 |
| +5 px | 7 | 0 | 3 | 4 | 8 |

Aucune variante ne produit d'association à un candidat résiduel. Les petites boîtes sont sensibles à leurs limites ; trois disparaissent avec la réduction de 5 px. Les points hors référence ne deviennent pas des faux positifs certifiés : l'exhaustivité des annotations et leur précision spatiale événementielle restent des limites héritées de M15/M16.

## Vitesse mesurée

La médiane des quatre coûts est **654,8 ms**, incluant lecture des fenêtres, représentation, stéréo fraîche, profondeur, suivi et estimation rigide. Elle exclut initialisation des lecteurs/cartes, évaluation et écriture des images. Ces quatre mesures CPU hors ligne ne constituent ni un débit soutenu ni un délai de détection, mais elles montrent que cette configuration ne tient pas un pas de 20 ms.

Les gains M08/M09 restent conservés. Il faut toutefois résoudre le support et la séparation objet/caméra avant de consacrer la suite à de nouvelles micro-optimisations.

## Code et preuves

- `src/pfe_events/reference_diagnostic.py` : association aux boîtes, support et abstentions ; recouvrement de références explicite, sans annoncer un état mobile/statique.
- `scripts/run_reference_diagnostic.py` : inférence causale puis diagnostic séparé, nouvelles cartes de profondeur, tableaux NPZ et six panneaux.
- `configs/m17_reference_diagnostic.json` : six dates conservées, paramètres figés et limites.
- `tests/test_reference_diagnostic.py` : dix tests sur bords semi-ouverts, chevauchements, profondeurs absentes, abstentions et régions vides.

**174 tests réussis**, syntaxe de 88 fichiers et aides de 27 commandes vérifiées. [Contrôles](../outputs/checks/M17/report.json) · [Journal](../outputs/checks/M17/tests.log). Les sources, quatre fichiers d'événements et calibrations sont hachés ; snapshots des sources dans `outputs/motion/M17/sources/`. Les rapports de chaque inférence indiquent `depth_source: predicted` et `oracle: false` pour les paires traitées.

```powershell
.\.venv\Scripts\python.exe scripts/run_reference_diagnostic.py --output outputs/motion/M17_repeat
.\.venv\Scripts\python.exe scripts/check_project.py --output outputs/checks/M17_repeat
```

Le programme exige un nouveau dossier. Les expériences antérieures et leurs données sont conservées ; aucun test réservé inspecté, aucune annotation utilisateur requise, aucun nouvel apprentissage YOLO.

## Prochaine étape M18 — Comparaison temporelle avec référence

Comparer la configuration 50 ms / pas 20 ms à **20 ms / pas 20 ms**, sur les mêmes quatre dates traitables, avec les mêmes réglages de suivi et de modèle rigide. Les fenêtres de la seconde variante ne partagent plus d'événements. Recalculer la profondeur pour chaque représentation, conserver les inconnus et examiner support dans les boîtes, résidus et stabilité du modèle. Les deux dates initiales pourront être analysées séparément si leur historique devient suffisant ; elles ne doivent pas modifier silencieusement le support commun de comparaison.

Cette comparaison change aussi la quantité d'événements et la qualité de stéréo : elle ne permettra pas d'attribuer toutes les différences au seul chevauchement. Ne pas baisser le seuil pour forcer des détections sur ces quelques positifs, ni choisir une variante au seul nombre de résidus. Un éventuel réglage nécessitera des contrôles d'erreurs et une validation indépendante.

L'expérience suivante prolonge les essais temporels M13 avec les nouvelles références publiques. YOLO et l'association XYZ restent dans le périmètre ; ce diagnostic porte sur la branche géométrique de mobilité.
