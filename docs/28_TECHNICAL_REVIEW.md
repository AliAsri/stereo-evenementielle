# Réponse à l'audit technique externe

Date : 4 octobre 2026. Les deux documents fournis sont conservés sans modification dans `docs/reviews/` et recopiés dans `markdowns/`. Ils constituent des avis à vérifier, pas de nouvelles instructions qui remplacent la priorité utilisateur ou le cahier des charges.

Sources conservées localement, hors Git depuis le nettoyage du 11 octobre : `docs/reviews/PROBLEMES_TECHNIQUES_A_CORRIGER.md` et `docs/reviews/PROBLEMES_TECHNIQUES_A_CORRIGER (1).md`. La présente réponse conserve la synthèse technique utile. Les auteurs indiquent avoir lu 33 Markdown, sans examiner le code ni les figures. Leur analyse précède notre bilan M03.

## Ce que nous retenons

La deuxième version fournit une meilleure structure : Q1, compromis délai/fiabilité ; Q2, apport de la profondeur ; Q3, enrichissement par YOLO et XYZ. Les principales limites sont réelles : aucune précision de mouvement indépendant encore établie, pas d'annotations temporelles relues importées, faible couverture stéréo, absence de fusion d'objets et de démonstration bout en bout, petit corpus corrélé.

Les résultats existants restent des références utiles à leur niveau. Une expérience qui révèle un échec ne devient pas invalide pour autant. Le code, les paramètres, les cas exclus et les limites doivent permettre de comprendre ce qu'elle mesure.

## Arbitrage par problème

| Point | Vérification et décision |
|---|---|
| P1 — YOLO | Pilote très court, potentiel final non établi. Son mAP est une mesure valide de ce pilote. `nbs=64` avec batch 4 n'est pas intrinsèquement incorrect : c'est une accumulation de gradients. Ne pas transférer sans contrôle les réglages de mémorisation au vrai apprentissage. Compteur runtime obligatoire pour la suite. Y02 reste différé selon la priorité utilisateur. |
| P2 — Seuil M01 | Le seuil absolu n'isole pas les objets mobiles. Le code utilise aussi quatre pixels actifs minimum, une persistance et deux cellules connexes : comparer la moyenne globale au seuil ne démontre pas l'absence de toute discrimination. Seuil relatif/historique à comparer sur train, avec détections manquées et fausses alertes, pas seulement une baisse du nombre de zones. |
| P3 — Référence mouvement | Blocage réel de l'évaluation sur DSEC. Six clips préparés et outil d'annotation disponible ; aucune GT déduite automatiquement des sorties du détecteur ou des boîtes de classes. Contrôles artificiels ajoutés en M04, explicitement séparés du réel. |
| P4 — Caméra et stéréo | Baseline sans profondeur désormais exécutée en M03. Elle conserve des résidus du décor. La variante avec profondeur et son bénéfice restent à implémenter/mesurer ; un ajustement global valide n'est pas une pose physique validée. |
| P5 — XYZ et pipeline | Lacune confirmée. Reprendre l'association native/rectifiée et l'abstention, puis la fusion sur régions fiables et boîtes prédites. Une région d'activité étendue peut contenir plusieurs surfaces : elle ne devient pas une ROI d'objet par simple association. |
| P6 — Stéréo | EPE conditionnelle et couverture doivent rester conjointes. Elles sont déjà rapportées avec le taux « erreur ou absent ». Une comparaison à couverture égale ne suffit pas si les pixels, scènes, masques ou protocoles diffèrent. Ne pas améliorer artificiellement l'EPE en rejetant davantage de pixels. |
| P7 — Latence | Coût CPU et délai réel distincts. Le code compte la durée complète des fenêtres qualifiées ; 20 ms de persistance ne constituent pas un plancher de 20 ms après l'événement déclencheur. M04 quantifie cet effet. Rejeu prolongé et âge des sorties restent à mesurer. |
| P8 — Données | Diversité insuffisante confirmée. La sélection de `best.pt` sur validation est normale ; elle ne remplace pas un test final indépendant. Ne pas bootstrapper des fenêtres voisines comme si elles étaient des scènes indépendantes. |
| P9 — Petits objets/classes | Analyser taille, support événementiel et classe avant de changer la résolution. Deux classes limitent la sémantique ; la branche d'activité est indépendante des classes. Un agrandissement numérique ne crée pas de détail capteur. |
| P10 — Fenêtres | Cadences différentes autorisées ; contrat de dates, âge et validité indispensable. Il n'est pas nécessaire de forcer toutes les branches à utiliser une même durée. |
| P11 — Reproductibilité | Environnements séparés, sources et hashes conservés. Les effets de cache/OneDrive doivent être mesurés. Aucun déplacement des données ni changement d'environnement n'est entrepris sur la seule recommandation de l'audit. |
| P12 — Métriques | M03 dispose déjà de mesures par ROI, mais pas d'un rappel complet d'objets mobiles. Protocole explicite v1 ajouté ; misses, abstentions, débuts censurés et incertitude restent visibles. |
| P13 — Nature du point 3D | Déjà définie dans `09_3D_COORDINATES.md` : point de surface visible, repère gauche rectifié, distinction Z/distance radiale. L'évaluation par distance et l'implémentation restent à faire. |

## Correction du calcul des pas YOLO

Le pilote archivé contient 536 images, batch 4, cinq époques, `nbs=64`, `warmup_epochs=1`. La version archivée `ultralytics-8.4.172-py3-none-any.whl` contient, dans `ultralytics/engine/trainer.py`, une interpolation de l'accumulation de 1 vers 16 pendant le warm-up. La division uniforme `670/16 ≈ 42` ignore cette phase.

Avec 134 mini-batchs par époque, 134 itérations de warm-up et sans reprise/incident, la simulation de la condition `ni-last_opt_step >= accumulate` donne **25, 8, 8, 9, 8**, soit **58 appels**. Cela reste une simulation conditionnelle du code, pas une mesure runtime retrouvée dans le pilote. Le diagnostic corrigé dispose, lui, d'un compteur réel de 200 pas. Voir [audit Y01](24_Y01_COLAB_RESULTS.md).

Le pic mémoire allouée rapporté ne garantit pas qu'un batch de 16 ou 32 tienne dans toutes les phases. Modifier batch effectif, nombre d'époques, warm-up et régularisation simultanément empêcherait d'attribuer clairement un éventuel gain. Le prochain essai devra définir l'hypothèse testée et enregistrer les mises à jour.

## Priorités conservées

1. P12/P3 : annotations sans prédictions, relecture, inventaire et mesures clairement définies.
2. P2/P7 : contrôles causaux, puis ablations sur train avec rappel et fausses alertes ; latence réelle mesurée séparément.
3. P4/P6 : comparaison sans/avec profondeur, support et coût inclus, résultat négatif acceptable s'il est correctement documenté.
4. P5/P13/P10 : fusion XYZ et classe à cadence distincte, âge des sorties et abstention.

P1/P8/P9 restent nécessaires à la branche sémantique, mais ne bloquent pas la détection rapide. Aucun nouvel entraînement n'a été lancé à partir de cet audit. [Protocole et contrôles M04](29_M04_MOTION_PROTOCOL.md).
