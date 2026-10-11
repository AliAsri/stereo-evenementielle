# Problèmes techniques à corriger

Projet : Stéréo vision par caméras événementielles pour la détection rapide de mouvement (DSEC).
Source : lecture des 33 fichiers Markdown de l'archive. Le code et les figures n'ont pas été examinés.

Légende : **[doc]** = chiffre lu dans tes documents. **[calcul]** = déduit par moi à partir de tes paramètres, à confirmer par mesure.

## Vue d'ensemble

| # | Problème | Gravité | Effort | Bloque |
|---|---|---|---|---|
| P1 | Pilote YOLO sous-entraîné (~42 mises à jour) | Critique | Faible | Le mAP est ininterprétable |
| P2 | Seuil de M01 inférieur au débit moyen de la scène | Critique | Faible | La branche mouvement ne discrimine rien |
| P3 | Aucune vérité terrain de mouvement (M03) | Critique | Moyen | Toute mesure de délai et de fausses alertes |
| P4 | Mouvement propre de la caméra non séparé ; stéréo absente du mouvement | Critique | Élevé | La contribution du titre |
| P5 | Fusion boîtes → XYZ non implémentée, pipeline bout en bout absent | Haute | Moyen | Exigence de l'encadrant |
| P6 | Évaluation stéréo non comparable à la littérature | Haute | Faible | Toute conclusion sur la stéréo |
| P7 | Latence : plancher de fenêtre, p95 > pas, chaîne stéréo à ~400–500 ms | Haute | Moyen | Le mot « rapide » |
| P8 | Données trop petites et corrélées, sélection sur la validation | Moyenne | Moyen | Toute généralisation |
| P9 | Petits piétons (7–16 px) et couverture de classes | Moyenne | Faible | Rappel piéton |
| P10 | Fenêtres temporelles incohérentes entre branches | Moyenne | Faible | Fusion et affichage |
| P11 | Risques d'environnement et de mesure | Faible | Faible | Reproductibilité |

---

## P1 — Pilote YOLO sous-entraîné

**Constat.** Le pilote utilise 536 images, batch=4, nbs=64, 5 époques **[doc]**. Résultat : mAP50 23,73 %, AP50 piéton 9,49 % **[doc]**.

**Pourquoi c'est un problème.** Avec nbs=64 et batch=4, Ultralytics accumule 16 mini-batchs avant chaque mise à jour. Cela donne environ 134 / 16 ≈ 8 mises à jour par époque, soit **environ 42 au total** **[calcul]**. Y02 (30 époques, nbs=64) en donnerait environ 250 **[calcul]**. Le diagnostic avait révélé ce piège, mais le pilote ne l'a pas corrigé. Le score mesure donc surtout le manque d'optimisation, pas la capacité d'un YOLO sur images d'événements.

**Correction.**
1. Mettre nbs égal à la taille du batch (batch 16 ou 32 ; le pic mémoire de 1,09 Gio **[doc]** le permet).
2. Ajouter le compteur de pas d'optimisation (déjà prévu pour Y02) et le journaliser.
3. Viser au moins 50 à 100 époques, avec warm-up proportionné.
4. Remonter Y02 de « différé » à prioritaire, et le relancer avec ces réglages.
5. Comparer à un témoin : YOLO COCO non adapté, avec remapping des classes.

**Critère d'acceptation.** Nombre de mises à jour reporté dans le rapport ; courbes train/val stabilisées ; AP50 par classe avec le nombre de pas.

---

## P2 — Seuil de M01 inférieur au débit moyen

**Constat.** Seuil d'activité de 20 événements/(s·pixel), cellules 16×16, fenêtre 10 ms **[doc]**. Soit 51 événements par cellule **[calcul]**.

**Pourquoi c'est un problème.** Les débits moyens sont d'environ 24 ev/(s·px) sur `04_b`, 29 sur `04_e` et 40 sur `thun_00_a` **[calcul à partir des comptes d'événements du doc]**. Le seuil est sous la moyenne : toute zone texturée est « active » quand la caméra bouge. Cela explique zones dans 100 % des fenêtres et ~34 % de cellules actives **[doc]**.

**Correction.**
1. Remplacer le seuil absolu par un seuil relatif : débit de la cellule comparé à la médiane globale et au voisinage, avec écart robuste (MAD).
2. Ajouter un historique temporel par cellule (comparaison à son propre débit récent).
3. Faire une ablation fenêtre (10/20/50 ms) × persistance × seuil relatif.
4. Fixer les paramètres à partir de la distribution des données d'entraînement, pas de la validation.

**Critère d'acceptation.** Fraction de cellules actives sensiblement inférieure à la moyenne actuelle sur le décor seul ; courbe délai contre fausses alertes par seconde.

---

## P3 — Aucune vérité terrain de mouvement

**Constat.** Délai réel et fausses alertes sont `null` ; le seul délai (15 ms) vient d'un test synthétique **[doc]**. DSEC n'annonce pas de vérité terrain de mouvement indépendant.

**Correction (par ordre de coût).**
1. **Injection synthétique** : insérer un objet mobile (événements simulés) dans un fond réel, avec instant de début exact. Réalisme limité, mais contrôlé et mesurable.
2. **Segments véhicule à l'arrêt** : repérer dans DSEC des passages où le porteur est immobile (feux, etc.), où les événements viennent surtout d'objets mobiles. À vérifier sur les données (poses, vitesse, ou critère événementiel global).
3. **Autre jeu de données** : examiner EV-IMO / EVIMO2 pour le mouvement indépendant (présence de stéréo à vérifier).
4. Annoter à la main un petit ensemble de débuts de mouvement avec incertitude, et des segments négatifs.

**Critère d'acceptation.** Délai médian et p95 avec intervalle d'incertitude de l'annotation ; fausses alertes par seconde sur segments négatifs.

---

## P4 — Mouvement propre non séparé ; stéréo absente du mouvement

**Constat.** M01 ne compense pas le mouvement de la caméra ; le décor est actif **[doc]**. La stéréo (SGBM) et le mouvement sont deux branches indépendantes.

**Pourquoi c'est un problème.** Le titre associe stéréo et détection de mouvement, mais rien ne les relie. Or la profondeur permet de prédire le mouvement apparent du décor statique (il varie en 1/Z).

**Correction.**
1. Estimer un mouvement global (modèle paramétrique sur les événements, ou poses si disponibles : à vérifier dans DSEC).
2. Version sans profondeur : résidu par rapport au modèle global (baseline).
3. Version avec profondeur stéréo : mouvement apparent prédit par pixel, résidu local.
4. Comparer 2 et 3 sur la vérité terrain de P3, avec latence ajoutée.
5. Documenter les cas d'échec : parallaxe, objets proches, éclairage, faible profondeur disponible (couverture ~36 %).

**Critère d'acceptation.** Gain mesuré (délai, fausses alertes) de la version avec profondeur par rapport à la baseline, ou échec documenté.

---

## P5 — Fusion XYZ non implémentée, pipeline bout en bout absent

**Constat.** Fusion boîtes/profondeur, XYZ, FPS, RAM et latence bout en bout : NOT RUN / NOT IMPLEMENTED **[doc]**. L'encadrant impose YOLO, stéréo et coordonnées 3D.

**Correction.**
1. Implémenter l'algorithme déjà conçu (09_3D_COORDINATES) : ROI intérieure, mapping natif → rectifié, médiane et MAD, statut `insufficient_depth`.
2. Comparer centre, médiane et sélection robuste sur les mêmes détections.
3. Mesurer la couverture de sorties et le taux d'abstention (lié à P6).
4. Assembler un rejeu bout en bout de 60 s sans crash, avec temps par étape.
5. Utiliser des boîtes **prédites** (pas la vérité terrain) pour la démonstration finale.

**Critère d'acceptation.** Rejeu continu, sorties exportées, tableau de temps par étape, taux d'abstention publié.

---

## P6 — Évaluation stéréo non comparable

**Constat.** EPE 1,045 px, mais couverture 36 % ; 65,5 % de la vérité terrain est « erreur ou absent » **[doc]**. EMatch rapporte MAE 0,49 px sur DSEC **[doc, PAPERS.md]**, sur un protocole d'évaluation différent (non vérifié par moi). Seuil de réussite fixé à EPE ≤ 3 px, très lâche.

**Correction.**
1. Rapporter systématiquement EPE, couverture et métrique pénalisée (erreur ou absent).
2. Pour comparer à la littérature : comparer à couverture égale, ou évaluer sur la vérité terrain entière avec une règle d'imputation explicite.
3. Resserrer le seuil EPE, et publier les erreurs par plage de distance.
4. Faire l'ablation des causes de perte de couverture (masque d'activité, contrôle gauche-droite, rejets SGBM) : elle est signalée comme non faite **[doc]**.
5. Décider de la stéréo profonde avec une date limite (≤ 2 jours, déjà dans ton plan) ; vérifier la compatibilité Python/Torch/CUDA du candidat (recette EMatch en Python 3.8 / Torch 2.0 **[doc]**).

---

## P7 — Latence

**Constat.**
- Lecture + activité : médiane 8,45 ms, p95 11,32 ms, 14 % de fenêtres > 10 ms **[doc]**.
- Chaîne stéréo : 404 à 505 ms médiane, dont représentation 250–350 ms **[doc]**.
- Persistance de 20 ms (deux fenêtres de 10 ms) : plancher de latence de détection **[doc, lecture de M01]**.

**Correction.**
1. Définir et mesurer le délai bout en bout : attente de fenêtre + persistance + calcul + file d'attente.
2. Vectoriser le splat bilinéaire et éviter la double validation (`polarity_counts` dans `rectified_counts`, déjà identifiée dans 14_PERFORMANCE) ; vérifier l'équivalence exacte des sorties.
3. Tester la stabilité sur des segments longs (≥ 60 s) et à froid (cache), pas seulement 2 s répétés.
4. Rapporter l'âge de chaque sortie (activité, YOLO, profondeur) à cadences distinctes.
5. Mesurer YOLO et stéréo sur GPU Colab (p95 ≤ 100 ms visé dans ton cadrage **[doc]**).

---

## P8 — Données trop petites, sélection sur la validation

**Constat.**
- Train : 2 séquences du même groupe (`04_e`, `04_b`) ; validation : 1 séquence (`thun_00_a`) **[doc]**.
- Fenêtres consécutives fortement corrélées.
- `best.pt` est choisi sur la validation (mAP50–95), alors que le meilleur mAP50 est à l'époque 1 **[doc]**.

**Correction.**
1. Ajouter des séquences train (`00_a`, `00_b`, `01_b` sont déjà repérées **[doc]**) et au moins une seconde séquence de validation.
2. Espacer ou sous-échantillonner les fenêtres voisines.
3. Intervalles de confiance par rééchantillonnage de séquences, pas de fenêtres.
4. Conserver le test réservé intact jusqu'à la configuration finale ; ne pas le consulter avant.
5. Vérifier qu'aucun checkpoint externe (EMatch) n'a vu le test réservé avant de le qualifier d'indépendant.

---

## P9 — Petits piétons et couverture de classes

**Constat.** Piétons de 7 à 16 px de large et 15 à 45 px de haut dans le lot de diagnostic ; 9 boîtes train filtrées par le framework ; le rappel moyen est de 21,7 % **[doc]**. Le cahier des charges demande aussi des « objets génériques » ; seules 2 classes sont entraînées.

**Correction.**
1. Analyser l'AP par taille de boîte avant d'accuser la représentation.
2. Tester `imgsz` plus grand (ou suréchantillonnage) pour les petits objets.
3. Examiner les traînées événementielles : tester des fenêtres plus courtes pour YOLO (avec ré-entraînement par fenêtre, pas seulement au test).
4. Décider explicitement du périmètre classes (2 classes vs 8) et le justifier.

---

## P10 — Fenêtres temporelles incohérentes

**Constat.** Stéréo et YOLO utilisent 50 ms ; M01 utilise 10/20/50 ms **[doc]**. Les sorties n'ont pas la même date ni la même mémoire.

**Correction.**
1. Fixer une date de sortie commune et un format de métadonnées : `t_sortie`, `durée_fenêtre`, `âge`.
2. Pour comparer des fenêtres, ré-entraîner ou ré-évaluer chaque modèle avec sa propre représentation (T01) ; changer seulement la fenêtre au test mesure un décalage de domaine **[doc]**.

---

## P11 — Environnement et mesure

- **Python 3.14 local vs 3.13 Colab vs 3.8 EMatch** **[doc]** : isoler les piles ; prévoir un environnement Colab dédié à la stéréo profonde.
- **Données sous OneDrive** **[doc]** : sortir `data/raw` (3,19 Gio) du dossier synchronisé, car la synchronisation peut perturber les mesures de lecture.
- **Mesures répétées sur le même segment de 2 s** **[doc]** : les comparaisons M02 ne sont pas indépendantes ; ajouter des segments distincts.
- **Dépôt non initialisé sous Git** **[doc]** : initialiser Git et versionner code, configs et documents (pas les données).
- **Normaliseur ajusté sur 32 images** **[doc]** : vérifier sa stabilité sur davantage de dates de train, sans toucher à la validation.

---

## Ordre de traitement proposé

1. P1 et P2 (rapides, invalident des résultats actuels).
2. P3 (nécessaire avant de mesurer quoi que ce soit sur le mouvement).
3. P6 et P8 (protocoles d'évaluation).
4. P4 (contribution principale).
5. P5 et P7 (pipeline bout en bout et latence).
6. P9, P10 et P11 en continu.
