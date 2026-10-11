# M16 — Six correspondances DSEC-MOD vérifiées

**9 octobre 2026.** M16 résout l'alignement pour un petit échantillon train : trois images de `zurich_city_04_e` et trois de `zurich_city_04_b`. Il fournit **six dates vérifiées et 22 boîtes Moving**, utilisables pour un diagnostic local avec les limites géométriques ci-dessous. Il ne certifie pas encore l'indexation des 534 images ni la qualité du détecteur.

## Résultat principal

Les frames MOD **1, 134 et 267** correspondent aux fichiers DSEC **`000001.png`, `000134.png` et `000267.png`**, dans chacune des deux séquences. Le timestamp est donc la ligne d'indice zéro `i` du fichier officiel `image_timestamps.txt` pour ces six correspondances uniquement : `timestamps[i]`, et non `timestamps[i-1]`.

| Séquence | Frame MOD / index DSEC | Timestamp unifié (µs) | Boîtes | Écart RGB moyen / 255 |
|---|---:|---:|---:|---:|
| `04_e` | 1 | 36 880 850 382 | 3 | 0,362 |
| `04_e` | 134 | 36 887 500 430 | 3 | 0,508 |
| `04_e` | 267 | 36 894 150 365 | 5 | 0,360 |
| `04_b` | 1 | 36 607 350 934 | 4 | 0,554 |
| `04_b` | 134 | 36 614 000 936 | 5 | 0,542 |
| `04_b` | 267 | 36 620 651 570 | 2 | 0,618 |

Cette mesure compare des intensités d'image après projection. **Ce n'est ni une erreur de localisation en pixels ni une précision de détection.**

Les 269 images RGB DSEC sont indexées de 0 à 268, contre 1 à 267 côté MOD. Les observations sont compatibles avec l'omission de la première et de la dernière image. Cette explication n'est pas extrapolée automatiquement aux autres frames : l'export M15 demeure intact, et le nouveau manifeste n'attribue des dates qu'aux six cas réellement comparés.

## Comment les correspondances ont été vérifiées

Vingt-deux RGB DSEC originaux ont été acquis par accès partiel aux ZIP : indices 0/1/2/3, 133/134/135/136 et 266/267/268, pour chacune des deux séquences. Trois RGB MOD supplémentaires de `04_b` ont complété les trois de `04_e` acquis dans M15. Chaque PNG est contrôlé par le CRC de son archive et une empreinte SHA256. Une interruption réseau sur `04_b` a été reprise en vérifiant et réutilisant les fichiers présents.

Une première recherche exploratoire par points SIFT sur `04_e/1` a identifié l'image candidate. La vérification finale utilise une transformation **calculée à partir de la calibration**, sans ajuster ses paramètres sur les images ou les boîtes. Elle compare chaque image MOD à ses voisines candidates avant, au même indice, et après. Aucune prédiction de mobilité n'intervient dans ce choix.

Sur les six cas, l'erreur moyenne est de 0,360 à 0,618 niveau d'intensité sur 255. Le deuxième meilleur candidat est moins bon d'au moins **4,087 niveaux**. La comparaison porte sur les 97,24 % de pixels ayant un support complet après projection. Le contrôle refuse un résultat si l'erreur dépasse 1 niveau ou si l'écart avec le suivant est inférieur à 1 ; ces seuils de contrôle ont été fixés après le premier cas exploratoire `04_e/1`, avant les cinq autres. Ils ne constituent pas des seuils optimisés du détecteur.

[Rapport et scores de tous les candidats](../outputs/motion/M16/audit/report.json) · [Manifeste des six dates et 22 boîtes](../outputs/motion/M16/audit/verified_sample.json).

## Repère spatial identifié et limite de parallaxe

La calibration DSEC permet de calculer la projection de l'image RGB gauche rectifiée vers la grille événementielle gauche rectifiée :

```text
H = K_rect0 × R_rect0 × rotation(T_10)ᵀ × R_rect1ᵀ × inverse(K_rect1)
```

Les conventions de `T_10`, `R_rect0` et `R_rect1`, ainsi que les résolutions et timestamps, sont décrits dans le [format officiel DSEC](https://dsec.ifi.uzh.ch/data-format/). Les fichiers de calibration déjà acquis sont hachés dans le rapport.

Cette projection reproduit très bien les RGB MOD sur les six images. Elle identifie la grille **`camRect0`, 640×480**, également utilisée par M12/M13. Les boîtes publiées peuvent donc être placées dans cette grille pour le diagnostic, sans leur appliquer une deuxième rectification. Pour la branche d'activité native, il faut transformer les coordonnées des événements ; ne pas utiliser directement une boîte rectifiée comme boîte native.

**Limite conservée :** l'homographie est une projection par rotation, équivalente à une hypothèse de profondeur infinie. Les centres des caméras RGB et événementielle sont séparés d'environ **4,57 cm**. La parallaxe des objets à distance finie n'est pas corrigée par cette transformation. La bonne reproduction RGB confirme la convention de la projection publiée ; elle ne garantit pas des contours physiques événementiels exacts au pixel près, notamment pour les objets proches. Ne pas transformer ce constat en métrique pixel par pixel sans étude de cette incertitude.

## Inspection visuelle

Pour chaque ligne, de gauche à droite : RGB MOD publié ; RGB DSEC daté reprojeté ; activité événementielle rectifiée sur `[t−20 ms, t)`. Les rectangles jaunes sont partout **les annotations publiques**, pas des sorties de notre détecteur.

![Correspondances train 04_b](../outputs/motion/M16/audit/zurich_city_04_b_alignment.png)

[Voir aussi les trois cas 04_e](../outputs/motion/M16/audit/zurich_city_04_e_alignment.png).

Les deux planches ont été inspectées. Sur `04_b/1`, le camion annoté produit peu d'activité dans la fenêtre affichée ; sur d'autres images, façades et chaussée produisent beaucoup d'événements. Cela illustre la nécessité de séparer activité, mouvement de caméra et mobilité des objets. Une image fixe ou une faible activité ne permet pas de conclure qu'un objet est immobile.

Le rendu rectifié arrondit les coordonnées pour cette inspection uniquement, avec une échelle logarithmique fixe de 20 événements. Il ne modifie pas la représentation ni les algorithmes M12/M13.

## Temps et causalité

Les timestamps utilisés sont les dates **unifiées DSEC**, à conserver dans le même repère temporel que les événements après ajout de `t_offset`. Les fichiers d'exposition gauche ont aussi été acquis et contrôlés ; les six durées vont de **658 à 2 887 µs**. L'écart entre timestamp unifié et milieu d'exposition gauche vaut de 3,5 à 60 µs sur ces cas. Le manifeste conserve séparément date, début et fin d'exposition.

Les événements affichés ne dépassent pas `t`. L'image de référence possède néanmoins un intervalle d'exposition autour de sa date. Elle sert ici à l'audit hors ligne, jamais d'entrée future du détecteur causal. Ces annotations ne donnent pas un début de mouvement exact à la milliseconde ; aucun délai de détection n'est calculé.

## Code, preuves et vérification

- `src/pfe_events/http_range.py` : lecteur HTTP borné, refus d'une réponse complète ou d'un intervalle différent ; vérification de stabilité ETag lorsqu'il est disponible.
- `src/pfe_events/mod_alignment.py` : projection par calibration, comparaison photométrique, refus des correspondances ambiguës, dates et expositions séparées.
- `scripts/audit_mod_alignment.py` : audit hors ligne, contrôle des acquisitions, manifeste et planches. Refuse de réécrire un ancien dossier de résultat.
- `tests/test_mod_alignment.py` : onze tests sur directions de projection, parallaxe non représentée, ambiguïté, horodatages, budgets HTTP et réponses invalides.

**164 tests réussis**, syntaxe de 85 fichiers Python et aides de 26 commandes vérifiées. [Rapport des contrôles](../outputs/checks/M16/report.json) · [Journal des tests](../outputs/checks/M16/tests.log).

```powershell
.\.venv\Scripts\python.exe scripts/audit_mod_alignment.py --output outputs/motion/M16_repeat
.\.venv\Scripts\python.exe scripts/check_project.py --output outputs/checks/M16_repeat
```

Sources exécutées et empreintes conservées dans `outputs/motion/M16/sources/` et les rapports. Les algorithmes existants et résultats M15 restent conservés. Aucun téléchargement ou examen du test réservé ; aucune annotation manuelle demandée.

## Prochaine étape M17 — Diagnostic du détecteur sur ces références

Exécuter la séparation géométrique objet/caméra sur les fenêtres associées à ces six dates, avec profondeur prédite et abstention lorsqu'elle manque. Les annotations doivent rester dans l'évaluateur, sans guider l'estimation du mouvement de caméra ni servir de profondeur oracle.

Produire un diagnostic par boîte : activité disponible, correspondances suivies, profondeur exploitable, résidus, candidats et inconnus. Définir explicitement l'association aux boîtes et tester sa sensibilité aux bords et à la parallaxe. Une absence de support doit rester distincte d'un objet déclaré statique ; une zone sans boîte n'est pas automatiquement une référence négative vérifiée.

Ces six images train servent à comprendre les échecs, sans revendiquer une précision/rappel globale ni régler les seuils sur le test. L'extension à des extraits continus et à une validation indépendante viendra ensuite ; `thun_00_a` reste absent de MOD et `09_b` réservé. YOLO, stéréo et XYZ restent dans le périmètre.
