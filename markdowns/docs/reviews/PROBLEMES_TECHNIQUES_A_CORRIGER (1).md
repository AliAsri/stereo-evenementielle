# Problèmes techniques à corriger — alignés sur la problématique

**Problématique :** Comment détecter rapidement et de façon causale un objet en mouvement dans une scène observée par une paire de caméras événementielles embarquées, puis estimer sa position 3D, avec un compromis mesuré entre latence et fiabilité ?

**Questions de recherche :**
- **Q1 — Compromis** : comment la taille de fenêtre (10/20/50 ms) et la persistance influencent-elles le délai de détection et les fausses alertes ?
- **Q2 — Apport de la stéréo** : la profondeur réduit-elle les fausses alertes dues au mouvement de la caméra, par rapport à une baseline sans profondeur ?
- **Q3 — Enrichissement** : peut-on ajouter classe (YOLO) et position 3D aux zones détectées sans dégrader la latence de la branche rapide ?

Source : lecture des 33 fichiers Markdown du projet DSEC. Le code et les figures n'ont pas été examinés.
Légende : **[doc]** = chiffre lu dans tes documents. **[calcul]** = déduit par moi à partir de tes paramètres, à confirmer par mesure.

---

## 1. Correspondance problématique ↔ problèmes

| Élément de la problématique | État actuel | Problèmes à corriger |
|---|---|---|
| Causale | Fait (fenêtres `[début, fin[`, aucun événement futur, testé) | — |
| Rapide | Partiel (coût mesuré, délai réel non mesuré) | P2, P7, P10 |
| Paire de caméras événementielles | Fait (SGBM), couverture faible | P6 |
| Objet **en mouvement** | Non fait (M01 détecte de l'activité, décor inclus) | P2, P3, P4 |
| Position 3D | Non fait (fusion ROI → XYZ non implémentée) | P5, P13 |
| Compromis latence / fiabilité mesuré | Non fait (délai et fausses alertes `null`) | P3, P7, P12 |
| YOLO (exigence de l'encadrant) | Fait mais résultat invalide | P1, P8, P9 |

## 2. Vue d'ensemble

| # | Problème | Gravité | Effort | Question | Bloque |
|---|---|---|---|---|---|
| P12 | « Fiabilité » et métriques non définies | Critique | Faible | Q1, Q2 | Toute la problématique |
| P3 | Aucune vérité terrain de mouvement | Critique | Moyen | Q1, Q2 | Délai, fausses alertes |
| P2 | Seuil de M01 inférieur au débit moyen | Critique | Faible | Q1 | La détection ne discrimine rien |
| P4 | Mouvement propre non séparé ; stéréo absente du mouvement | Critique | Élevé | Q2 | La contribution principale |
| P1 | Pilote YOLO sous-entraîné (~42 mises à jour) | Haute | Faible | Q3 | Le mAP est ininterprétable |
| P5 | Fusion boîtes → XYZ non implémentée, pipeline absent | Haute | Moyen | Q3 | Exigence de l'encadrant |
| P13 | Évaluation de la « position 3D » non définie | Haute | Faible | Q3 | Toute conclusion sur le 3D |
| P7 | Latence : plancher fenêtre, p95 > pas, chaîne stéréo lente | Haute | Moyen | Q1, Q3 | Le mot « rapide » |
| P6 | Évaluation stéréo non comparable à la littérature | Moyenne | Faible | Q2 | Conclusions sur la stéréo |
| P8 | Données trop petites et corrélées, sélection sur la validation | Moyenne | Moyen | Toutes | Généralisation |
| P9 | Petits piétons et couverture de classes | Moyenne | Faible | Q3 | Rappel piéton |
| P10 | Fenêtres temporelles incohérentes entre branches | Moyenne | Faible | Q3 | Fusion et affichage |
| P11 | Environnement et mesure | Faible | Faible | Toutes | Reproductibilité |

---

## P12 — « Fiabilité » et métriques non définies

**Constat.** La problématique parle de compromis latence/fiabilité, mais aucune de ces deux grandeurs n'est définie pour un détecteur de mouvement. Délai et fausses alertes valent `null` **[doc]**.

**Correction.** Écrire, avant toute expérience, les définitions suivantes :
1. **Délai de détection** = date de la première alerte correcte moins date de début du mouvement (vérité terrain), avec l'incertitude de l'annotation. Décomposer : attente de fenêtre + persistance + calcul + file d'attente.
2. **Détection correcte** = zone alertée qui recouvre l'objet mobile (seuil d'IoU à fixer) pendant au moins une fenêtre.
3. **Fiabilité** = rappel (objets mobiles détectés) et taux de fausses alertes par seconde sur segments sans objet mobile. Les rapporter ensemble, jamais séparément.
4. **Courbe du compromis** : délai médian et p95 contre fausses alertes par seconde, pour chaque (fenêtre, persistance, seuil).
5. Prévoir les intervalles de confiance par rééchantillonnage de segments (voir P8).

**Critère d'acceptation.** Un document de métriques figé avant les mesures, et un script qui calcule ces valeurs à partir des sorties.

---

## P3 — Aucune vérité terrain de mouvement

**Constat.** Le seul délai disponible (15 ms) vient d'un test synthétique **[doc]**. DSEC n'annonce pas de vérité terrain de mouvement indépendant.

**Correction (par ordre de coût).**
1. **Injection synthétique** : insérer un objet mobile (événements simulés) dans un fond réel, avec un instant de début exact. Contrôlé et mesurable, mais de réalisme limité : à déclarer comme tel.
2. **Segments véhicule à l'arrêt** : repérer dans DSEC des passages où le porteur est immobile (feux, etc.), où les événements viennent surtout d'objets mobiles. À vérifier sur les données (poses, vitesse, ou critère événementiel global).
3. **Annotation manuelle** d'un petit ensemble de débuts de mouvement avec incertitude, et de segments négatifs.
4. **Autre jeu de données** : examiner EV-IMO / EVIMO2 pour le mouvement indépendant (présence de stéréo à vérifier).

**Critère d'acceptation.** Un ensemble de segments avec instant de début, incertitude et segments négatifs, versionné avec manifeste et hashes.

---

## P2 — Seuil de M01 inférieur au débit moyen

**Constat.** Seuil de 20 événements/(s·pixel), cellules 16×16, fenêtre 10 ms **[doc]**, soit 51 événements par cellule **[calcul]**.

**Pourquoi c'est un problème.** Les débits moyens sont d'environ 24 ev/(s·px) sur `04_b`, 29 sur `04_e` et 40 sur `thun_00_a` **[calcul à partir des comptes d'événements du doc]**. Le seuil est sous la moyenne : toute zone texturée est « active » quand la caméra bouge. Cela explique des zones dans 100 % des fenêtres et ~34 % de cellules actives **[doc]**.

**Correction.**
1. Seuil relatif : débit de la cellule comparé à la médiane globale et au voisinage, avec écart robuste (MAD).
2. Historique temporel par cellule (comparaison à son propre débit récent).
3. Ablation fenêtre (10/20/50 ms) × persistance × seuil relatif, pour produire la courbe de Q1.
4. Choisir les paramètres sur la distribution des données d'entraînement, pas sur la validation.

**Critère d'acceptation.** Fraction de cellules actives nettement inférieure sur le décor seul ; courbe délai / fausses alertes (P12).

---

## P4 — Mouvement propre non séparé ; stéréo absente du mouvement

**Constat.** M01 ne compense pas le mouvement de la caméra **[doc]**. La stéréo (SGBM) et le mouvement sont deux branches indépendantes, alors que Q2 demande si la profondeur aide.

**Pourquoi c'est un problème.** La profondeur permet de prédire le mouvement apparent du décor statique (il varie en 1/Z) ; le résidu devient candidat d'objet mobile.

**Correction.**
1. Estimer un mouvement global (modèle paramétrique sur les événements, ou poses si disponibles : à vérifier dans DSEC).
2. **Variante sans profondeur** : résidu par rapport au modèle global (baseline de Q2).
3. **Variante avec profondeur stéréo** : mouvement apparent prédit par pixel, résidu local.
4. Comparer les variantes 2 et 3 sur la vérité terrain de P3, avec la latence ajoutée.
5. Documenter les cas d'échec : parallaxe, objets proches, éclairage, couverture de profondeur limitée (~36 % **[doc]**).
6. Prévoir un repli : si la profondeur n'apporte rien ou couvre trop peu, rapporter ce résultat négatif avec son diagnostic.

**Critère d'acceptation.** Gain mesuré (délai, fausses alertes) de la variante avec profondeur sur la baseline, ou échec documenté.

---

## P1 — Pilote YOLO sous-entraîné

**Constat.** 536 images, batch=4, nbs=64, 5 époques ; mAP50 23,73 %, AP50 piéton 9,49 % **[doc]**.

**Pourquoi c'est un problème.** Avec nbs=64 et batch=4, Ultralytics accumule 16 mini-batchs par mise à jour : environ 8 mises à jour par époque, soit **environ 42 au total** **[calcul]**. Y02 (30 époques, nbs=64) en donnerait environ 250 **[calcul]**. Le score mesure surtout le manque d'optimisation.

**Correction.**
1. Mettre nbs égal à la taille du batch (16 ou 32 ; le pic mémoire de 1,09 Gio **[doc]** le permet).
2. Journaliser le compteur de pas d'optimisation.
3. Viser au moins 50 à 100 époques, avec warm-up proportionné.
4. Remonter Y02 de « différé » à prioritaire.
5. Comparer à un témoin : YOLO COCO non adapté, avec remapping des classes.

**Critère d'acceptation.** Nombre de mises à jour dans le rapport ; courbes train/val stabilisées ; AP50 par classe.

---

## P5 — Fusion boîtes → XYZ non implémentée, pipeline absent

**Constat.** Fusion, XYZ, FPS, RAM et latence bout en bout : NOT RUN / NOT IMPLEMENTED **[doc]**.

**Correction.**
1. Implémenter l'algorithme conçu dans 09_3D_COORDINATES : ROI intérieure, mapping natif → rectifié, médiane et MAD, statut `insufficient_depth`.
2. Comparer centre, médiane et sélection robuste sur les mêmes détections.
3. **Brancher la fusion sur les zones de mouvement** (branche rapide), pas seulement sur les boîtes YOLO : c'est ce qui répond à « objet en mouvement … puis position 3D ».
4. Mesurer couverture de sorties et taux d'abstention.
5. Assembler un rejeu de 60 s sans crash, avec temps par étape, en utilisant des boîtes **prédites**.

**Critère d'acceptation.** Rejeu continu, sorties exportées, tableau de temps par étape, taux d'abstention publié.

---

## P13 — Évaluation de la « position 3D » non définie

**Constat.** DSEC n'a pas de vérité terrain de centre 3D d'objet **[doc, 09_3D_COORDINATES]**. Le système produit un point de surface visible.

**Correction.**
1. Écrire dans le mémoire que la sortie est un **point représentatif de surface visible** dans le repère caméra gauche rectifié, avec statut et dispersion.
2. Évaluer contre la profondeur LiDAR de référence (disparité GT) là où elle existe, et le dire : ce n'est pas une erreur de centre d'objet.
3. Rapporter l'erreur en mètres **par plage de distance** (l'erreur de profondeur croît avec Z², **[doc]**) et le taux d'abstention.
4. Distinguer profondeur axiale Z et distance radiale.

**Critère d'acceptation.** Tableau d'erreur par plage de distance, avec couverture et abstention, calculé uniquement sur des détections prédites.

---

## P7 — Latence

**Constat.**
- Lecture + activité : médiane 8,45 ms, p95 11,32 ms, 14 % de fenêtres > 10 ms **[doc]**.
- Chaîne stéréo : 404 à 505 ms de médiane, dont représentation 250–350 ms **[doc]**.
- Persistance de 20 ms (deux fenêtres de 10 ms) : plancher de latence de détection.

**Correction.**
1. Mesurer le délai bout en bout (voir P12) : attente de fenêtre + persistance + calcul + file d'attente.
2. Vectoriser le splat bilinéaire et éviter la double validation (`polarity_counts` dans `rectified_counts`, déjà identifiée dans 14_PERFORMANCE) ; vérifier l'équivalence exacte des sorties.
3. Tester la stabilité sur des segments longs (≥ 60 s) et à froid (cache), pas seulement 2 s répétés.
4. Rapporter l'âge de chaque sortie (activité, YOLO, profondeur) à cadences distinctes.
5. Mesurer YOLO et stéréo sur GPU Colab (p95 ≤ 100 ms visé dans ton cadrage **[doc]**).
6. Q3 : montrer que l'ajout de YOLO + XYZ ne modifie pas la latence de la branche rapide (deux cadences découplées).

---

## P6 — Évaluation stéréo non comparable

**Constat.** EPE 1,045 px à couverture 36 % ; 65,5 % de la vérité terrain est « erreur ou absent » **[doc]**. EMatch annonce un MAE de 0,49 px **[doc, PAPERS.md]** sur un protocole différent (non vérifié par moi). Seuil de réussite EPE ≤ 3 px, très lâche.

**Correction.**
1. Rapporter systématiquement EPE, couverture et métrique pénalisée (erreur ou absent).
2. Pour comparer à la littérature : comparer à couverture égale, ou évaluer sur la vérité terrain entière avec une règle d'imputation explicite.
3. Resserrer le seuil EPE ; publier l'erreur par plage de distance.
4. Faire l'ablation des causes de perte de couverture (masque d'activité, contrôle gauche-droite, rejets SGBM) : signalée comme non faite **[doc]**.
5. Stéréo profonde : décision avec date limite (≤ 2 jours, déjà dans ton plan) ; compatibilité Python/Torch/CUDA à vérifier (recette EMatch en Python 3.8 / Torch 2.0 **[doc]**).

---

## P8 — Données trop petites, sélection sur la validation

**Constat.**
- Train : 2 séquences du même groupe (`04_e`, `04_b`) ; validation : 1 séquence (`thun_00_a`) **[doc]**.
- Fenêtres consécutives fortement corrélées.
- `best.pt` choisi sur la validation (mAP50–95), alors que le meilleur mAP50 est à l'époque 1 **[doc]**.

**Correction.**
1. Ajouter des séquences train (`00_a`, `00_b`, `01_b` sont repérées **[doc]**) et au moins une seconde séquence de validation.
2. Espacer ou sous-échantillonner les fenêtres voisines.
3. Intervalles de confiance par rééchantillonnage de séquences (et de segments pour la courbe de Q1), pas de fenêtres.
4. Garder le test réservé intact jusqu'à la configuration finale.
5. Vérifier qu'aucun checkpoint externe n'a vu le test réservé avant de le qualifier d'indépendant.

---

## P9 — Petits piétons et couverture de classes

**Constat.** Piétons de 7 à 16 px de large dans le lot de diagnostic ; 9 boîtes train filtrées par le framework ; rappel moyen 21,7 % **[doc]**. Deux classes seulement, alors que le cahier des charges évoque des objets génériques.

**Correction.**
1. Analyser l'AP par taille de boîte avant d'accuser la représentation.
2. Tester un `imgsz` plus grand ou un suréchantillonnage.
3. Tester des fenêtres plus courtes pour YOLO, avec ré-entraînement par fenêtre.
4. Fixer et justifier le périmètre de classes. Rappel : la branche mouvement ne dépend pas des classes.

---

## P10 — Fenêtres temporelles incohérentes

**Constat.** Stéréo et YOLO utilisent 50 ms ; M01 utilise 10/20/50 ms **[doc]**.

**Correction.**
1. Fixer une date de sortie commune et des métadonnées : `t_sortie`, `durée_fenêtre`, `âge`.
2. Pour comparer des fenêtres, ré-entraîner ou ré-évaluer chaque modèle avec sa propre représentation ; changer seulement la fenêtre au test mesure un décalage de domaine **[doc]**.

---

## P11 — Environnement et mesure

- **Python 3.14 local, 3.13 Colab, 3.8 pour EMatch** **[doc]** : isoler les piles ; environnement Colab dédié à la stéréo profonde.
- **Données sous OneDrive** **[doc]** : sortir `data/raw` (3,19 Gio) du dossier synchronisé, car la synchronisation peut perturber les mesures de lecture.
- **Mesures répétées sur le même segment de 2 s** **[doc]** : les comparaisons M02 ne sont pas indépendantes ; ajouter des segments distincts.
- **Dépôt sans Git** **[doc]** : initialiser Git (code, configs, documents, pas les données).
- **Normaliseur ajusté sur 32 images** **[doc]** : vérifier sa stabilité sur davantage de dates de train, sans toucher à la validation.

---

## 3. Ordre de traitement

| Étape | Problèmes | Résultat attendu |
|---|---|---|
| 1 | P12, P3 | Métriques figées et vérité terrain de mouvement |
| 2 | P2, P7 (mesure) | Courbe délai / fausses alertes : réponse à Q1 |
| 3 | P1, P8, P9 | YOLO interprétable, données élargies |
| 4 | P4, P6 | Baseline sans profondeur, puis avec profondeur : réponse à Q2 |
| 5 | P5, P13, P10, P7 (cadences) | Pipeline bout en bout, 3D évaluée : réponse à Q3 |
| 6 | P11 | Reproductibilité, en continu |

Repli si l'étape 4 échoue (profondeur trop clairsemée) : tu gardes Q1 et la baseline de Q2, qui restent des résultats défendables, et tu documentes l'échec.
