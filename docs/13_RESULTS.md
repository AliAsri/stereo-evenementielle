# Résultats réellement obtenus

**Archive des premiers résultats D00–M09.** Les expressions « dernière étape » ci-dessous sont datées. Pour Y02, le démonstrateur intégré et les vérifications du 15 octobre, consulter [le bilan actuel](20_NEXT_STEPS.md) ; pour toutes les étapes intermédiaires, [le journal](19_PROGRESS.md).

**Dernière étape : M09, terminée le 7 octobre 2026.** Coût médian du calcul d’activité réduit de **13,07–18,14 %** sur quatre cas appariés ; 3 660 comparaisons exactes et 9 600 fenêtres cadencées. L’effet sur le retard est variable, avec une régression sur un passage de `04_b`. **96 tests réussis.** [Résultats complets](37_M09_LOOKUP_ACTIVITY.md).

Mise à jour : 2026-10-07. D00 documente l'inspection initiale ; S01 apporte les premières métriques de disparité réellement prédite ; Y01 apporte le premier YOLO événementiel entraîné et évalué dans Colab, dont les archives ont été vérifiées localement.

## D00 — Inspection réelle d'une séquence DSEC

**Hypothèse :** une séquence du train permet de lire conjointement événements gauche/droite, calibration, disparité GT et annotations objets sans dépendance GPU.

**Configuration :** Windows, Python 3.14.6 ; versions exactes dans `requirements-inspection-lock.txt`. Source `zurich_city_04_e`, fenêtre causale 50 000 µs. Aucun modèle, aucun apprentissage et aucune seed aléatoire nécessaires pour cette inspection déterministe. Commande : `python scripts/inspect_sample.py --full-timestamp-audit` depuis l'environnement du projet.

**Preuves conservées :** [rapport complet](../outputs/reports/D00_inspection.json), [URLs/octets/SHA256](../outputs/reports/D00_downloads.json), [inventaire annotations](../outputs/reports/label_inventory.json), [journal tests](../outputs/reports/tests_initial.txt). Les hashes sont calculés localement après téléchargement ; ils détectent des modifications ultérieures mais ne sont pas des sommes publiées par l'auteur.

| Contrôle | Observation réelle |
|---|---|
| Archives téléchargées | 536 897 112 octets, soit environ 512,03 Mio |
| Dossier données après extraction | 1 092 546 736 octets lors du relevé, environ 1,02 Gio |
| Événements gauche | 119 172 751 |
| Événements droite | 95 364 500 |
| Ordre temporel | Vérifié intégralement par blocs sur les deux flux : non décroissant |
| Intervalle commun | [36 880 800 104 ; 36 894 200 655] µs, soit ~13,400551 s |
| Fenêtre inspectée | [36 887 550 427 ; 36 887 600 427[ µs |
| Événements dans cette fenêtre | Gauche 386 255 ; droite 271 712 |
| Sorties hors champ après rectification arrondie | Gauche 31 501 ; droite 22 835 |
| Conservation des comptes | Vérifiée avant/après rectification et rejets |
| Intrinsics rectifiés | fx=fy≈569,287354 px, cx≈336,267841, cy≈222,288906 |
| Baseline issue des extrinsèques | ≈0,599033158 m |
| Baseline issue de Q | ≈0,599033158 m, cohérente avec la précédente |
| Références disparité | 135 PNG ; nombre cohérent avec les timestamps fournis |
| GT au timestamp inspecté | 81 868 pixels valides, couverture ≈26,65 % |
| Boîtes officielles au même timestamp | 8 |
| Tests automatisés | 13 réussis, sur fixtures synthétiques identifiées |

Les offsets des fichiers gauche et droite diffèrent : respectivement 36 880 799 656 et 36 880 800 104 µs. Ils ont été ajoutés séparément avant découpage sur une horloge commune. Aligner les flux en retranchant indépendamment le premier événement aurait modifié la synchronisation fournie.

## Diagnostic de référence, pas estimation d'objet

Sur les pixels GT valides de la carte sélectionnée, les percentiles 5/50/95 des profondeurs reprojetées valent environ 7,4167 / 25,8595 / 45,3987 m. Ce sont des **statistiques de la vérité terrain de surface de la scène**, pas des profondeurs prédites, ni des coordonnées d'objets détectés. Elles servent à vérifier la chaîne de décodage et la plausibilité des unités.

Le rapport conserve les temps ponctuels de lecture d'une fenêtre (~13,08 ms gauche et ~10,20 ms droite lors de l'exécution archivée). Ils incluent l'effet du cache et de la décompression et ne sont **ni un benchmark stable ni le temps d'une chaîne d'inférence**.

## Annotations : résultat qui change le choix d'échantillonnage

La séquence contient 0 boîte pedestrian, 62 rider, 1 614 car, 56 bus, 424 truck, 73 bicycle, 16 motorcycle et 0 train. Ce sont des instances annotées sur plusieurs dates, pas des objets distincts.

L'inventaire complet de l'archive train des labels a identifié notamment `zurich_city_00_b` (10 033 boîtes pedestrian, 3 993 car), `zurich_city_01_b` (2 293 pedestrian, 7 067 car) et `zurich_city_00_a` (1 107 pedestrian, 6 141 car). Leur sélection finale dépendra de leur taille, de l'intersection GT/droite et des groupes de partition. Certains fichiers de cette archive correspondent au split validation de détection : le nom de l'archive n'est pas une autorisation de les entraîner tous.

## Interprétation et décision

La chaîne d'accès et le contrôle de géométrie sont opérationnels sur une vraie paire. La vue produite et la superposition des huit annotations ont été inspectées visuellement. Les trous de la rectification arrondie sont visibles et documentés. Le résidu épipolaire quantitatif et la qualité d'annotation sur plusieurs dates ne sont pas encore mesurés.

Décision issue de D00 : conserver `04_e` comme séquence de débogage légère et ajouter des piétons avant YOLO. Cette suite est maintenant réalisée dans S01 ci-dessous.

## S01 — Première disparité et profondeur prédites

**Exécution réelle :** 60 fenêtres de 50 ms, 20 dates uniformément réparties par séquence, résolution 640×480. StereoSGBM CPU sans apprentissage, représentation logarithmique normalisée sur train seulement. Les paramètres sont restés identiques sur les trois séquences. [Protocole détaillé](21_STEREO_BASELINE.md).

| Séquence / usage local | Pixels GT évalués / disponibles | EPE px | RMSE px | Bad3 sur évalués | Couverture GT | Bad3 ou absent / toute GT | MAE Z sur intersection |
|---|---:|---:|---:|---:|---:|---:|---:|
| `zurich_city_04_e`, train/debug | 430 629 / 1 301 447 | 1,054 | 2,648 | 4,13 % | 33,09 % | 68,28 % | 2,809 m |
| `zurich_city_04_b`, train | 614 295 / 1 602 265 | 0,901 | 2,533 | 3,17 % | 38,34 % | 62,88 % | 1,412 m |
| `thun_00_a`, validation pilote | 423 860 / 1 177 427 | 1,045 | 3,011 | 4,26 % | 36,00 % | 65,54 % | 1,421 m |

Les agrégats pondèrent par le nombre de pixels, pas par une moyenne non pondérée des scores par image. Bad3 signifie `abs(erreur)>3 px`, sans condition relative ; ce n'est pas D1. La profondeur est une profondeur de **surface**, pas une position de centre d'objet. Les erreurs sont conditionnées par la disponibilité de la GT ET d'une prédiction valide. Les 64 % de GT sans prédiction sur validation ne doivent pas être oubliés : le score « Bad3 ou absent » les compte tous comme échecs. Ce score est un diagnostic local, pas une métrique officielle revendiquée.

Aucun pixel GT des 60 dates ne dépasse la plage `[0,96[` px ; la restriction de recherche n'explique donc pas à elle seule les pertes de couverture. La GT étant clairsemée, les prédictions hors de son support ne sont pas évaluables. Le masque d'activité, la cohérence gauche-droite, les bords non appariables et les rejets SGBM réduisent tous la couverture. Leur contribution causale séparée n'a pas fait l'objet d'une ablation.

**Cas d'échec conservé :** `thun_00_a`, index GT 69, temps 49 606 100 507 µs : EPE 2,144 px et couverture 29,18 % environ. La figure montre de grandes régions GT sans estimation et des erreurs près d'un bord vertical. Des traînées sont visibles dans l'accumulation événementielle ; elles sont une explication possible des difficultés, pas une cause isolée prouvée. Le cas est choisi automatiquement par le plus fort taux « Bad3 ou absent » parmi les vingt dates de cette séquence.

**Coût observé :** médianes lecture→profondeur de 404,4 / 405,9 / 505,3 ms pour `04_e` / `04_b` / `thun_00_a`, premier passage inclus, évaluation et écriture exclus. Ce n'est pas un benchmark temps réel ni la latence d'un pipeline YOLO complet. La représentation prend la plus grande part du temps instrumenté. [Détail des temps](14_PERFORMANCE.md).

**Contrôles :** 21 tests synthétiques réussis ; ordre temporel des six flux audité intégralement ; les 60 tableaux sauvés ont été relus pour vérifier échelle `/16`, masque/NaN, profondeur `fx*B/d` et recalcul indépendant EPE/Bad3/couverture. Les hashes du code correspondent au rapport. Les annotations de `04_b` ont été inspectées sur une vue contenant huit boîtes piéton ; elles restent des labels officiels, pas des détections du système.

**Preuves :** [résumé JSON](../outputs/reports/S01_summary.json), [métriques CSV](../outputs/reports/S01_metrics.csv), [vérifications](../outputs/reports/S01_verification.json), [figure de validation](../outputs/stereo/S01/thun_00_a/example.png), [cas d'échec](../outputs/stereo/S01/thun_00_a/worst_coverage_or_error.png). Les rapports par date, cartes NPZ, paramètres et normaliseur sont sous `outputs/stereo/S01/` (environ 21,3 Mio).

**Décision :** conserver cette référence pour les comparaisons, passer à l'export natif des labels et au pilote YOLO. La fusion devra s'abstenir quand une ROI n'a pas assez de support. Les résultats actuels ne satisfont pas encore l'objectif complet du PFE.

## Y00 — Export de détection et préparation Colab

Export réel : **774 PNG** (536 train, 238 validation), **4 235 boîtes** (3 330 train, 905 validation), classes personne/voiture. Les deux images négatives de train ont un fichier texte vide. Une date par séquence est exclue faute d'historique de 50 ms. Aucune image de test réservé n'est ouverte.

Contrôles : 27 tests réussis ; 1 560 fichiers couverts par SHA256 ; toutes les paires PNG/labels et les conventions Pillow/OpenCV vérifiées ; 4 235 boîtes comparées aux annotations source avec recalcul indépendant ; neuf PNG reconstruits depuis les événements et identiques pixel par pixel. Figures de `04_b` et `thun_00_a` inspectées. [Rapport d'export](../outputs/reports/Y00_export.json) et [vérifications](../outputs/reports/Y00_verification.json).

Le ZIP de transfert pèse 158 606 475 octets. Le notebook Y01 comprend 16 cellules dont sept cellules de code compilées. À l'étape Y00, seule la préparation locale était validée. Les contrôles runtime et l'entraînement sont désormais attestés par Y01 ci-dessous. [Guide détaillé](22_YOLO_EXPORT_COLAB.md).

## État des composants

Les archives confirment le premier diagnostic échoué (mAP50=0,556, AP50 personne=0,307), puis le diagnostic corrigé réussi (AP50=0,995 par classe, 200 pas d'optimisation). Les mêmes huit images train servent à apprendre et évaluer le diagnostic ; ce résultat ne mesure pas la généralisation.

Le pilote de cinq époques repart des poids initiaux sur 536 images train et est évalué sur les 238 images de `thun_00_a`. mAP50=0,237306 ; mAP50–95=0,136644 ; précision moyenne=0,744748 ; rappel moyen=0,216670. AP50 personne=0,094946 et voiture=0,379667. Les poids best/last et la provenance sont vérifiés par SHA256 ; aucune réévaluation locale n'a été exécutée. Le test réservé n'est pas utilisé. [Analyse des courbes, seuils et limites](24_Y01_COLAB_RESULTS.md).

| Élément | Statut |
|---|---|
| StereoSGBM, EPE et profondeur de surface | RUN — S01, 60 fenêtres, couverture limitée |
| Réseau stéréo profond / Colab | NOT RUN |
| Diagnostic YOLO sur huit images train | RUN — corrigé, seuil dépassé pour les deux classes |
| Fine-tuning YOLO, 536 train / 238 validation | RUN — cinq époques, mAP50 23,73 %, qualité limitée |
| Checkpoints et provenance Y01 | Importés et hachés ; 113 fichiers conservés |
| Fusion boîtes prédites/profondeur prédite | NOT RUN |
| Localisation XYZ d'objets détectés | NOT RUN |
| Activité événementielle causale | RUN — M01, zones et coûts CPU mesurés |
| Mouvement indépendant et délai réel d'apparition | NOT MEASURED — pas de GT temporelle constituée |
| Pic mémoire allouée PyTorch du pilote | Rapporté : 1 169 670 656 octets ; pas la VRAM totale |
| FPS, RAM et latence pipeline complet | NOT RUN |

Le PFE n'est donc pas encore fonctionnel de bout en bout. La première phase technique est validée à son niveau, avec les limites ci-dessus.

## M01 — Première branche d'activité rapide

Exécutée sur deux segments DSEC centrés de deux secondes, fenêtres 10/20/50 ms, 748 fenêtres traitées dont 680 après préchauffage. Seuils fixes, aucune classe ni GT utilisée pour les propositions. Sur validation à 10 ms : calcul d'activité médian 4,47 ms ; lecture+activité médiane 13,38 ms et p95 16,89 ms. Cadence 10 ms non soutenue par la lecture de référence. À 20 ms : médiane combinée 17,43 ms, p95 19,64 ms.

33 tests réussis ; cartes, comptes, timestamps et hashes contrôlés. Les régions visibles incluent le décor : activité ne signifie pas mouvement indépendant. Délai réel de première détection et fausses alertes restent non mesurés ; le délai de 15 ms du test est uniquement synthétique. [Protocole, rapports et rejeu](25_M01_RAPID_ACTIVITY.md).

## M03 — Mouvement apparent global et annotations

Six clips de deux secondes, 600 fenêtres mesurées : modèle global accepté par ses critères de support dans 600/600 fenêtres, régions résiduelles dans 599/600. Le décor produit encore des propositions ; ce nombre ne mesure pas les fausses alertes. Le coût total médian selon le clip est de 20,02 à 37,94 ms, p95 de 25,52 à 50,56 ms, pour un pas de 20 ms. L'intégration à cette cadence n'est pas validée.

Annotateur sans prédictions, 600 images et évaluateur par ROI relue disponibles. Aucun JSON d'annotations réelles relues encore importé : délai réel et fausses alertes restent **NOT EVALUATED**. 53 tests passent, dont 14 nouveaux contrôles synthétiques du modèle et des métriques. Images, dates et sources archivées vérifiées. [Détail M03 et commandes](27_M03_GLOBAL_MOTION.md).

## M04 — Contrôles artificiels et protocole

486 essais, 27 540 fenêtres sur géométrie artificielle 128×96. Au réglage M01 (10 ms, persistance 20 ms, seuil 20), les cinq phases d'une source moyenne donnent des délais événementiels de 18 à 25 ms ; la source faible est manquée. Une bouffée globale produit 90 ms d'activité sur une seconde. Ces signaux ne représentent pas un objet simulé physiquement ni une scène DSEC. Aucun gain réel de qualité mouvement revendiqué.

Protocole v1 fixé et vérificateur d'annotations disponibles ; inventaire sans export fourni : zéro ROI réelle relue. 61 tests réussis. [Résultats, limites et commandes M04](29_M04_MOTION_PROTOCOL.md).

## M05 — Activité relative et historique

306 essais artificiels, 600 fenêtres train comparées sur trois variantes. Au contrôle à 10 ms, source moyenne seule : même délai médian de 21 ms et 5/5 réponses pour les trois variantes. La bouffée uniforme est rejetée par les variantes adaptatives. Avec historique, la source durable n'est signalée que dans 9,7 % des sorties après début : conserver ce défaut visible.

Sur les trois clips train, la fraction moyenne de cellules actives passe de 19,45–50,14 % pour M01 à 0,47–1,09 % avec historique, sans mesure de rappel/fausses alertes réelle. Lecture partagée + calcul historique : médianes 6,20 / 6,56 / 11,30 ms, p95 7,99 / 9,81 / 13,78 ms. Ce protocole n'est pas une démonstration de cadence autonome. 67 tests réussis, référence préservée. [Rapport M05](31_M05_ADAPTIVE_ACTIVITY.md).


## M10 — Candidats de mouvement, 7 octobre 2026

Sept contrôles à correspondances idéales et trois extraits train de deux secondes exécutés. Sur ces extraits, 495 régions résiduelles M03 deviennent 178 régions persistantes cumulées ; ce ne sont ni des objets distincts ni une mesure de diminution des fausses alertes. Les sorties persistantes occupent respectivement 22, 55 et 56 fenêtres sur 100.

La translation locale des contrôles est retenue après 40 ms supplémentaires de confirmation. La parallaxe est aussi retenue à tort, et la rotation locale est manquée. Qualité réelle toujours non évaluée. Coûts totaux médians 13,22 / 15,71 / 21,57 ms, hors rendu et sans cadence imposée. 105 tests réussis. [Protocole, illustrations et preuves M10](39_M10_MOBILE_CANDIDATES.md).


## M11 — Compensation géométrique contrôlée

135 paires synthétiques (9 scénarios, 3 niveaux de bruit, 5 seeds). Avec profondeur exacte, le contrôle de parallaxe passe de 52 faux points résiduels M03 sur 124 à zéro avec le modèle rigide. Les contrôles de mouvement local en translation et rotation conservent leurs 16 points mobiles ; résultat inchangé pour les bruits de localisation testés. Les répétitions sans bruit sont identiques, pas des scènes indépendantes.

Deux échecs connus : profondeur locale multipliée par trois → 16 faux candidats ; couche mobile majoritaire → 108 points mobiles compatibles avec le mauvais modèle et 16 points statiques signalés. Profondeur insuffisante → abstention. Résultats par correspondance, pas détection d'objets ; oracle synthétique, aucune mesure réelle de mobilité. 117 tests réussis. [Preuves et figures M11](40_M11_RIGID_MOTION.md).


## M12 — Diagnostic réel avec profondeur prédite

38 paires train (`04_b`, `04_e`), deux paires de fin de fichier exclues faute d'événements futurs suffisants. Sur 14 818 points suivis, 8 630 ont une profondeur exploitable ; 6 188 sont inconnus. Sur le support évaluable commun, les modèles de similarité et rigide produisent respectivement 176 et 49 points candidats. Cela ne mesure pas une baisse des fausses alertes ni un rappel d'objets mobiles.

Les modèles rigides satisfont leurs critères de support sur 38/38 paires ; aucune référence de pose ne valide cette estimation. Fenêtres de 50 ms décalées de 20 ms, chevauchement de 30 ms. Coût total médian avec profondeur en cache 321,06 / 385,26 ms, p95 780,46 / 647,31 ms. Aucune cadence temps réel annoncée. 123 tests réussis ; cartes prédites, dates et résidus vérifiés. [Rapport et images M12](41_M12_REAL_RIGID_MOTION.md).


## M13 — Sensibilité aux fenêtres, sans sélection de gagnant

Six dates train, quatre conditions durée/écart : 20/20, 20/50, 50/20 et 50/50 ms. Les points candidats cumulés sont respectivement 2, 0, 5 et 3, pour 1 168, 1 131, 1 321 et 1 308 profondeurs exploitables. Les supports changent ; aucun gain de précision n'est inféré. Le seuil résiduel est exprimé à 150 px/s, avec un seuil RANSAC conservé à 1,5 pixel.

Les six reprises de M12 en 50/20 sont exactes. Six extraits sans prédictions et 600 images permettent maintenant une relecture indépendante des sorties. Aucune annotation reçue, aucune métrique réelle de mobilité. 129 tests réussis. [Tableau complet, limites et outil](42_M13_TEMPORAL_REVIEW.md).
