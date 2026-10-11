# M13 — Extraits sans prédictions et sensibilité aux fenêtres temporelles

7 octobre 2026. **Six extraits produits, 24 essais exécutés ; annotations de mobilité en attente.**

**Décision utilisateur ultérieure du même jour : sauter les annotations manuelles.** Le mode d’emploi ci-dessous décrit un outil conservé, pas une tâche à réaliser ni un préalable à la suite. Aucune annotation n’a été créée à sa place ; les métriques de mobilité restent non évaluées. Voir [la suite actualisée](20_NEXT_STEPS.md).

M12 a raccordé profondeur prédite et modèle géométrique aux données réelles. M13 prépare l'examen de vrais mouvements et vérifie la sensibilité aux fenêtres, sans interpréter automatiquement les résidus comme des objets mobiles.

## Livrables pour examiner le mouvement

Six extraits train, deux secondes chacun, autour des paires M12 d'indices 3, 10 et 17 dans `zurich_city_04_b` et `zurich_city_04_e`. Ces indices répartis dans les séquences sont fixés dans le protocole, sans sélection selon le nombre de candidats. Les deux séquences appartiennent au même groupe de trajet de développement ; ce n'est pas une validation de généralisation.

Chaque extrait contient 100 images événementielles rectifiées de 20 ms, consécutives et non chevauchantes, soit **600 images et 12 secondes de données** au total. Il est centré sur la date d'une profondeur S01 existante. Les images utilisent le normaliseur S01 figé sur train.

Les vues de relecture ne contiennent ni boîte prédite, ni résidu, ni carte de profondeur. Un GIF et une planche de six instants accompagnent chaque extrait. Les GIF demandent un affichage de 20 ms par image ; la cadence réellement affichée dépend du lecteur et ne mesure pas les performances du pipeline.

| Extrait | Animation sans prédictions | Planche |
|---|---|---|
| `04_b_003` | [GIF](../outputs/motion/M13/clips/zurich_city_04_b_003/blind.gif) | [Images](../outputs/motion/M13/clips/zurich_city_04_b_003/contact.png) |
| `04_b_010` | [GIF](../outputs/motion/M13/clips/zurich_city_04_b_010/blind.gif) | [Images](../outputs/motion/M13/clips/zurich_city_04_b_010/contact.png) |
| `04_b_017` | [GIF](../outputs/motion/M13/clips/zurich_city_04_b_017/blind.gif) | [Images](../outputs/motion/M13/clips/zurich_city_04_b_017/contact.png) |
| `04_e_003` | [GIF](../outputs/motion/M13/clips/zurich_city_04_e_003/blind.gif) | [Images](../outputs/motion/M13/clips/zurich_city_04_e_003/contact.png) |
| `04_e_010` | [GIF](../outputs/motion/M13/clips/zurich_city_04_e_010/blind.gif) | [Images](../outputs/motion/M13/clips/zurich_city_04_e_010/contact.png) |
| `04_e_017` | [GIF](../outputs/motion/M13/clips/zurich_city_04_e_017/blind.gif) | [Images](../outputs/motion/M13/clips/zurich_city_04_e_017/contact.png) |

Sur la planche `04_b_003`, une personne et un véhicule apparaissent à droite aux premiers instants, puis sortent du champ pendant le déplacement apparent de la scène. Cette observation ne suffit pas à les étiqueter mobiles : une sortie du champ peut provenir du mouvement de caméra. Les images individuelles sont conservées pour une relecture plus précise.

## Comment relire les zones

Ouvrir [review.html](../outputs/motion/M13/review.html) dans un navigateur, en conservant le dossier M13 complet. La page peut être utilisée localement ; les fichiers d'images et de données restent à côté.

1. Choisir un extrait et examiner plusieurs images avant de décider.
2. Dessiner une zone rectangulaire. Choisir sa première et sa dernière image d'intérêt.
3. Indiquer **mouvement propre observable**, **immobile dans la scène** ou **inconnu**. Ne pas transformer un déplacement dans l'image en mouvement propre sans indices suffisants.
4. Indiquer séparément l'état observé de la caméra ou le laisser inconnu. Décrire les indices et ambiguïtés dans les notes.
5. Vérifier que la zone reste pertinente sur tout l'intervalle ; raccourcir cet intervalle si l'objet sort de la zone ou change d'état. Confirmer la relecture et ajouter l'annotation.
6. Exporter `M13_manual_review.json` avant de fermer. Les annotations sont en mémoire jusqu'à l'export ; la page ne les sauvegarde pas automatiquement.

Commencer par quelques zones bien observables : objet mobile si étayé, décor et cas ambigu. Aucun quota ne doit forcer un label. En cas d'ambiguïté persistante dans les vues événementielles, conserver `unknown` et rechercher une référence complémentaire plutôt que forcer un jugement.

L'intervalle porte sur un état observé dans une ROI fixe, pas sur un instant exact de début de mouvement ni sur une trajectoire d'objet. Une relecture manuelle n'est pas une vérité terrain instrumentée. Des annotations contradictoires ou ambiguës devront être arbitrées avant l'évaluation.

### Format et validation

Le schéma `pfe-motion-review-v1` est distinct de M06. Il exige l'identifiant exact du manifeste, une ROI dans le repère rectifié, un intervalle inclusif d'indices d'images, l'auteur, les indices observés et deux confirmations explicites. Les états inconnus restent distincts des zones statiques. Une liste vide retourne `PENDING_REVIEW`, jamais un résultat négatif.

```powershell
.\.venv\Scripts\python.exe scripts/check_motion_review.py "C:\chemin\M13_manual_review.json"
```

Le validateur vérifie le format et l'accord avec le manifeste ; il ne certifie pas la justesse des labels. L'import des annotations dans les métriques existantes M06 n'est pas automatique : les repères, les dates et la définition de la cible diffèrent.

## Comparaison temporelle exécutée

Pour chacune des six dates, quatre conditions croisent durée de fenêtre (20/50 ms) et écart entre leurs fins (20/50 ms). Les quatre conditions partagent la même date initiale et la même profondeur prédite S01, issue d'une accumulation de 50 ms. La profondeur n'est pas recalculée avec les fenêtres de 20 ms : cette différence de représentation temporelle reste une limite.

Le seuil de candidat est fixé à **150 pixels par seconde de résidu apparent** : 3 pixels sur 20 ms et 7,5 pixels sur 50 ms. Ce seuil ne représente pas une vitesse physique en mètres/seconde. Le seuil RANSAC reste à 1,5 pixel, car il concerne l'erreur de reprojection. Aucun seuil n'est réajusté après inspection.

| Fenêtre | Écart | Chevauchement | Points suivis cumulés | Points avec profondeur | Points candidats | Médiane des vitesses médianes par paire |
|---|---|---|---:|---:|---:|---:|
| 20 ms | 20 ms | 0 ms | 2 309 | 1 168 | 2 | 117,74 px/s |
| 20 ms | 50 ms | 0 ms, intervalle vide de 30 ms entre fenêtres | 2 125 | 1 131 | 0 | 113,71 px/s |
| 50 ms | 20 ms | 30 ms | 2 349 | 1 321 | 5 | 69,80 px/s |
| 50 ms | 50 ms | 0 ms | 2 226 | 1 308 | 3 | 77,25 px/s |

Chaque ligne regroupe six paires. Les vitesses du tableau concernent le **déplacement observé de tous les points suivis**, avant compensation, pas la vitesse résiduelle des candidats ni celle d'objets indépendants.

Les modèles satisfont leurs critères de support dans les 24 essais. Les six cas 50/20 reproduisent exactement M12 : images, points suivis, profondeurs échantillonnées et résultats du modèle rigide.

**Interprétation :** la durée de fenêtre et l'écart temporel modifient les correspondances, la couverture et le mouvement mesuré. Les points suivis ne sont pas identiques entre les conditions ; la densité d'événements, le flou temporel et l'accord avec la profondeur S01 changent aussi. Cette comparaison ne démontre pas que le chevauchement est à lui seul responsable d'une atténuation. Les zéro candidat du cas 20/50 ne constituent pas une meilleure performance.

Aucune configuration n'est sélectionnée comme gagnante. Les 24 comparaisons sont effectuées aux six dates centrales ; le modèle géométrique n'est **pas** exécuté sur chaque image des six clips et aucun suivi continu d'objet n'est revendiqué.

## Vérifications et provenance

**129 tests réussis**, dont six tests du contrat de relecture. Les 17 sources/protocole sont archivés et leurs empreintes vérifiées. Les 600 PNG sont vérifiés contre le manifeste, les six GIF contiennent chacun 100 images de 20 ms et les six planches ont les dimensions attendues. Les 24 paires, 9 009 correspondances cumulées et résidus exportés sont contrôlés. Les six reproductions M12 sont exactes.

La syntaxe JavaScript de la page est vérifiée avec Node, et le modèle d'export vide passe le validateur en état `PENDING_REVIEW`. L'interaction complète dans un navigateur n'a pas été testée automatiquement ; les contrôles de format et les fichiers rendus ne prouvent pas à eux seuls le bon fonctionnement de tous les gestes de l'interface.

[Rapport](../outputs/motion/M13/summary.json), [vérification](../outputs/motion/M13/verification.json), [manifeste sans prédictions](../outputs/motion/M13/review_manifest.json), [état de relecture](../outputs/motion/M13/review_status.json), [tests](../outputs/motion/M13/tests.log).

```powershell
# Reproduire dans un dossier neuf pour préserver la campagne existante.
.\.venv\Scripts\python.exe scripts/prepare_temporal_review.py --output outputs/motion/M13_repeat
node --check scripts/motion_review.js
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/sync_markdowns.py
```

## Ce qui reste à faire

Le paquet est prêt pour la relecture, mais **aucune annotation réelle relue n'est encore enregistrée**. Les résultats ne contiennent donc aucune précision/rappel ni délai réel de mouvement. Après relecture, contrôler les zones et leur couverture aux dates effectivement évaluées, puis vérifier si les objets mobiles restent signalés. Si les événements ne suffisent pas à distinguer objet et caméra, une référence complémentaire sera nécessaire. Les annotations manquantes ne deviennent jamais des labels « immobile ».
