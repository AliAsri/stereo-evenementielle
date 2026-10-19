# Journal des décisions

**Journal historique.** Les décisions datées peuvent être remplacées par les demandes ultérieures de l’utilisateur. Les décisions actuelles sont résumées dans [la page active](20_NEXT_STEPS.md) et persistées dans `AGENTS.md`.

**18 octobre 2026 — choix utilisateur explicite : mouvement prioritaire ; classe et 3D moins fréquentes.** Première implémentation : indices de mouvement à chaque pas source de 20 ms, publication avant YOLO, contexte YOLO/XYZ toutes les 100 ms dataset par défaut. La stéréo interne reste à chaque date pour préserver la compensation. Âge du contexte explicite, aucune ancienne géométrie présentée comme actuelle. Les 20 ms sont le budget de comparaison du rejeu, pas une latence de début de mouvement validée. [Implémentation et limites](20_NEXT_STEPS.md).

Date commune du tableau historique ci-dessous : 2026-10-03. Une décision conditionnelle sera révisée après mesure, avec raison et conséquence conservées.

| ID | Décision | Alternatives | Motif | Conséquence / révision |
|---|---|---|---|---|
| D01 | DSEC principal | MVSEC, M3ED, EventScape | Stéréo et extension objets dans une même famille de données | Auditer intersection labels/GT/droite avant corpus final |
| D02 | MVSEC secondaire optionnel | M3ED immédiat | Géométrie historique, résolution plus basse | Pas de métriques objets sans labels |
| D03 | YOLO en vue native ; profondeur en vue rectifiée | Rectifier les boîtes pour tout unifier | Éviter approximation des rectangles non linéairement transformés | Mapping de ROI nécessaire pour XYZ |
| D04 | Event frames trois canaux pour YOLO | Voxels, E2VID, graphes, SNN | Compréhensibilité et initialisation réseau simple | Fine-tuning indispensable ; séparer rendu humain et encodage réseau |
| D05 | SGBM avant DL stéréo | Réseau profond immédiatement | Vérifier les bases sans dépendre CUDA | Carte éventuellement clairsemée, publier couverture |
| D06 | EMatch premier candidat DL à auditer | SE-CFF, baseline eventvppstereo | Code/poids disponibles et intérêt DSEC/MVSEC | Pas de choix final avant inférence et VRAM mesurées |
| D07 | PyTorch pour DL | TensorFlow | Cohérence avec dépôts et YOLO retenus | Isoler la pile GPU de l'inspection CPU |
| D08 | Activité rapide comme première composante mouvement | SLAM + segmentation dynamique | Sujet visible sans suringénierie | Ne pas revendiquer mouvement absolu ; mesurer délai et fausses alertes |
| D09 | Point 3D de surface robuste + abstention | Pixel central toujours valide, centre objet fictif | Limiter les sorties trompeuses | Rapporter support et dispersion, comparer à baseline |
| D10 | Un sous-ensemble borné avant téléchargement massif | Dataset entier | Disque et temps limités | Inventaire et hashes dès le premier fichier |
| D11 | Applications Python/PNG/JSON avant interface avancée | Application web complexe | Démonstration et diagnostic rapides | UI enrichie seulement après MVP |
| D12 | Référence de slicing binaire avant optimisation `ms_to_idx` | Index optimisé dès le départ | Simplicité du contrôle des bornes | Débit pas encore optimisé, comparaison exacte prévue |

## Décisions prises pour S01

| ID | Décision | Motif et conséquence |
|---|---|---|
| D13 | Ajouter `04_b` et `thun_00_a` | Piétons/voitures, volumes plus petits, modalités vérifiées ; corpus encore peu diversifié |
| D14 | Manifeste par groupe | `04_*` train, `thun_00` validation, `09_b` réservé ; aucune répartition aléatoire des fenêtres |
| D15 | Splat bilinéaire et normalisation train commune | Réduire les trous d'arrondi, préserver des intensités comparables ; coût CPU à profiler |
| D16 | EPE avec couverture et taux incluant les absents | Seulement 36 % de couverture GT sur validation ; abstention indispensable en fusion |
| D17 | Pilote YOLO à deux classes, données natives | Personne/voiture prioritaires ; autres classes comptées et traitées comme fond, rider non fusionné |
| D18 | Réutiliser la normalisation S01 train-only | Export reproductible sans ajustement sur validation ; nouvelle version si la normalisation change |
| D19 | Figer Ultralytics 8.4.172 et désactiver les augmentations de couleur implicites | Code inspecté ; ordre des canaux et filtrage réel à contrôler dans Colab avant entraînement |
| D20 | Petit lot diagnostique puis cinq époques pilote depuis les poids initiaux | Limiter le coût GPU tant que l'intégration n'est pas démontrée ; scores train et validation séparés |
| D21 | Corriger l'accumulation du petit lot après échec AP50 piéton | nbs=batch=4, LR constant, sans warm-up/weight decay, 100 époques ; même lot et seuil ; compter les mises à jour réelles, préserver v1 |
| D22 | Conserver Y01 comme référence, proposer Y02 sur 30 époques | Diagnostic corrigé réussi mais AP50 piéton validation 9,49 % ; garder données, normaliseur, initialisation et réglages pilote, compter les mises à jour ; gain non garanti |
| D23 | Importer rapports, figures et best/last, garder les autres poids dans les ZIP | 113 fichiers utiles, environ 56 Mio extraits ; inventaire et hashes conservés, aucune suppression des archives |
| D24 | Priorité utilisateur à la détection rapide du mouvement | Avancer M01 et ses mesures avant Y02 ; YOLO/stéréo/XYZ enrichissent la réponse sans la bloquer |
| D25 | M01 comme baseline d'activité, pas segmentation d'objets mobiles | Fenêtres 10/20/50 ms, support spatial et persistance ; mouvements de caméra/illumination non séparés, délai réel non mesuré |
| D26 | Optimiser la lecture avant de revendiquer 10 ms soutenues | Validation M01 : lecture+activité médiane 13,38 ms ; préserver référence, tester équivalence exacte et constituer GT de début de mouvement |
| D27 | Lecteur indexé optionnel, référence binaire conservée | M02 : index contrôlé, bornes exactes et repli borné ; 1 496 paires identiques, coût combiné validation −27 % dans comparaison appariée |
| D28 | Passer à la qualité mouvement après ce premier gain | Rejeu autonome encore à 11,32 ms p95 ; pas de GT temporelle ni compensation caméra, M03 doit mesurer réponse et fausses alertes |
| D29 | Conserver la similarité globale M03 comme diagnostic | 599/600 fenêtres ont des résidus ; un ajustement valide ne prouve pas un objet mobile. Ne pas remplacer la branche légère par cette chaîne plus coûteuse sans gain de qualité mesuré |
| D30 | Annotation sans prédictions et mesures par ROI relue | Incertitude temporelle, abstention et débuts d'alertes censurés explicites ; ni boîte de classe ni fréquence de sortie ne devient une GT de mouvement |
| D31 | Protocole v1 et contrôles M04 séparés du réel | 486 essais de sources artificielles vérifient phase/seuil/persistance, sans simuler physiquement un objet ni sélectionner un réglage ; les annotations DSEC restent nécessaires |
| D32 | Audits externes conservés mais arbitrés par les preuves | Corriger les affirmations sur l'accumulation YOLO, le plancher de persistance et la validation ; garder la priorité utilisateur mouvement et ne pas invalider les références existantes |
| D33 | M05 reste une comparaison, pas un remplacement de M01 | Le seuil relatif rejette une bouffée uniforme construite ; l'historique réduit les sorties mais absorbe une source persistante. Mesurer maintien et rappel réels avant toute sélection ; validation et test non rejoués |

Sources et détails : [datasets](02_DATASETS.md), [état de l'art](01_STATE_OF_THE_ART.md), [architecture](05_PROJECT_ARCHITECTURE.md), [baseline exécutée](21_STEREO_BASELINE.md), [résultats YOLO](24_Y01_COLAB_RESULTS.md). SGBM et YOLO sont exécutés ; la stéréo profonde reste à auditer. Aucun abandon expérimental de modèle profond n'est enregistré.


## D34 — Conserver l’incertitude temporelle pour comparer M03/M05

**4 octobre 2026.** Comparer les quatre méthodes à leurs dates de sortie natives (10/20 ms), avec les mêmes bornes d’annotation à 20 ms. Rejet des flux incomplets et des cadences incompatibles ; pas d’interpolation. L’évaluateur v1 reste conservé pour la provenance M03.

**Alternative écartée :** sous-échantillonner M05 ou transformer une annotation en date exacte, ce qui masque une réponse précoce ou donne une précision injustifiée.

**Maintien :** intervalle de mouvement continu optionnel explicitement relu dans la même ROI ; ne pas le déduire du début. Cette mesure répond au risque d’absorption de l’activité par l’historique M05.

**Conséquence :** 2 100 sorties contrôlées mais aucune qualité réelle annoncée sans annotations. Résultats par ROI, comparaison limitée aux trois clips train. [Protocole M06](34_M06_TEMPORAL_EVALUATION.md).


## D35 — Mesurer l’attente avant de revendiquer une cadence rapide

**4 octobre 2026.** M07 mesure les sorties d’un rejeu cadencé de 12 secondes, à 10 et 20 ms, avec fenêtres conservées et même algorithme. Alternative écartée : conclure au temps réel sur une médiane de coût ou sauter silencieusement les fenêtres en retard.

La moyenne sous 10 ms cache un retard final de 534–801 ms sur `04_b` à 10 ms. Le pas 20 ms réduit l’attente mais varie entre répétitions. Ne pas annoncer une cadence stricte ni changer automatiquement la fenêtre. Profiler et optimiser à résultats équivalents ; utiliser ensuite les annotations M06 pour le compromis délai/qualité. Les huit cas restent train et les répétitions ne deviennent pas des scènes indépendantes. [Preuves M07](35_M07_PACED_REPLAY.md).


## D36 — Conserver les handles HDF5 avant de changer l’algorithme

**4 octobre 2026.** M08 réutilise les quatre datasets via une sous-classe du lecteur indexé. Les contrôles, les événements renvoyés et le détecteur restent inchangés. Alternatives non retenues à cette étape : supprimer des validations ou changer les seuils pour réduire le coût.

3 660 comparaisons exactes réussissent et le coût médian lecture + activité baisse de 8,87–14,44 % dans les quatre cas appariés. Le gain sur l’attente varie en rejeu autonome et ne garantit pas 10 ms. Le cache persistant est borné par les limites HDF5 enregistrées (32 Mio au total observés).

Utiliser cette classe pour les prochaines intégrations, tout en conservant les références historiques. Le prochain poste à examiner est le calcul d’activité, avec exigence d’équivalence. [Preuves M08](36_M08_CACHED_READER.md).


## D37 — Optimiser la géométrie répétée, conserver une variante explicite

**7 octobre 2026.** M09 préconstruit la correspondance pixel→cellule, recherche les pixels occupés sur un masque booléen et évite certaines copies de conversion. Seuils, persistance et propositions inchangés. 3 660 comparaisons exactes et 96 tests réussis.

Le calcul médian baisse de 13,07–18,14 % dans les cas appariés, mais l’âge des sorties autonomes est variable et régresse sur un des quatre couples séquence/répétition. Conserver la variante comme option ; aucune garantie de cadence 10 ms ni remplacement silencieux des références.

La campagne initiale partielle reste archivée ; seules les répétitions de la campagne complète du 7 octobre forment les tableaux finaux. Prochaine intégration : démonstrateur avec choix explicite de variante et retard affiché. [Preuves M09](37_M09_LOOKUP_ACTIVITY.md).


## D38 — Priorité à la détection des objets mobiles

**7 octobre 2026, instruction utilisateur.** La séparation objet mobile / décor devient le prochain objectif. Conserver les gains M08/M09 et différer les nouvelles micro-optimisations ainsi que le simple démonstrateur d’activité. YOLO, stéréo et XYZ restent requis ; une classe ou une activité ne prouvent pas la mobilité.

Préparer M10 avec référence de mouvement, compensation du décor, cohérence temporelle et abstention. DSEC reste principal ; EVIMO est une piste complémentaire documentée, non acquise. Aucun résultat de mobilité supplémentaire annoncé. [Objectif détaillé](38_OBJECTIF_OBJETS_MOBILES.md).


## D39 — Conserver l'incertitude après filtrage temporel

**7 octobre 2026.** M10 ajoute support spatial, cohérence directionnelle et persistance de trois observations aux résidus M03. Sept contrôles idéaux et trois extraits train sont exécutés, avec 105 tests réussis et modèle brut préservé.

La diminution de 495 à 178 régions cumulées ne prouve pas un meilleur détecteur d'objets mobiles. Un contre-exemple de parallaxe passe le filtre ; une rotation locale est rejetée. Décision : conserver ces échecs dans les résultats, ne jamais renommer les candidats persistants « objets mobiles confirmés », et ne pas régler les seuils sur les seules boîtes affichées.

Prochaine étape : référence distinguant objet/caméra, puis compensation adaptée à la géométrie avec abstention et distinction oracle/prédiction. Les 40 ms de confirmation du contrôle idéal ne sont pas un délai de détection réel. [Preuves M10](39_M10_MOBILE_CANDIDATES.md).


## D40 — Tester la géométrie avant d'ajouter des heuristiques de persistance

**7 octobre 2026, suite à l'accord utilisateur sur la revue d'architecture.** M11 estime un modèle rigide 3D avec profondeur au premier instant et correspondances 2D au second. Contrairement à la similarité globale, ce modèle peut expliquer la parallaxe de points statiques à différentes profondeurs.

La preuve actuelle est limitée à 135 paires synthétiques avec profondeur oracle. Les échecs liés à une profondeur biaisée et à une couche mobile dominante sont conservés. Le statut compatible modèle ne signifie pas immobile, le résidu ne signifie pas mobile confirmé. Aucune cadence réelle n'est inférée du coût PnP seul.

La prochaine expérience utilisera les profondeurs prédites S01 train et des correspondances rectifiées aux dates compatibles, sans réutilisation arbitraire de profondeur ancienne. Les paramètres de ROI XYZ sont réglés sur train/debug, formulation du document 09 corrigée. Aucun changement de nbs ou relancement YOLO à cette étape. [Bilan M11](40_M11_RIGID_MOTION.md).


## D41 — Valider le raccord réel sans confondre résidu et mobilité

**7 octobre 2026.** M12 utilise les profondeurs S01 prédites, aux dates exactes, et des correspondances dans le repère rectifié. Aucun recours à une pose ou profondeur GT. Deux paires de fin de fichier sont exclues, pas complétées silencieusement.

38 paires exécutées, 8 630 points évaluables sur 14 818. La réduction de 176 à 49 résidus sur le support commun n'est pas interprétée comme un gain de précision. Les points inconnus, le chevauchement des accumulations et le coût excluant le calcul de profondeur restent affichés.

Prochaine étape : référence réelle de mobilité et contrôle de l'effet des fenêtres chevauchantes, avant de sélectionner une méthode sur le nombre de candidats ou d'optimiser le seul coût. Les résultats M11/M12 restent séparés : oracle synthétique et diagnostic réel avec prédictions. [Bilan M12](41_M12_REAL_RIGID_MOTION.md).


## D42 — Examiner les mouvements sans montrer les prédictions à l'annotateur

**7 octobre 2026.** M13 produit six clips train sans sorties du modèle et une relecture indépendante des résidus. Les annotations ne sont pas préremplies ; les cas ambigus restent inconnus. Le format vérifie une ROI fixe pertinente sur tout l'intervalle, sans prétendre fournir un début de mouvement précis.

La comparaison 20/50 ms de durée et d'écart conserve les seuils documentés et la profondeur S01. Les supports diffèrent, donc les 2/0/5/3 points candidats ne déterminent pas une configuration gagnante. Six cas historiques M12 reproduits exactement. Les modèles ne sont exécutés qu'aux six dates centrales ; les GIF ne constituent pas un détecteur continu.

La prochaine porte est une référence de mobilité exploitable, pas une nouvelle réduction automatique des résidus. Une annotation absente ou incertaine ne devient jamais négative. [Protocole et résultats M13](42_M13_TEMPORAL_REVIEW.md).


## D43 — Supprimer la dépendance aux annotations manuelles utilisateur

**7 octobre 2026, instruction utilisateur : « mieu skip cette partie annotations ».** Le travail demandé de relecture M13 est sauté. Les outils et résultats sont conservés ; aucune suppression des preuves ni génération de faux labels.

La prochaine piste est une référence publique déjà instrumentée, à commencer par un échantillon EVIMO/EVIMO2 borné. La documentation officielle décrit masques d'identité et poses de caméra/objets ; il faut encore vérifier repères, dates, disponibilité et conversion éventuelle vers l'état de mobilité. [Format officiel](https://better-flow.github.io/evimo/docs/ground-truth-format.html).

DSEC reste le socle principal. Les métriques de mobilité DSEC restent non évaluées tant qu'une référence adaptée n'existe pas. Cette décision ne remplace pas l'annotation manuelle par les résidus du modèle, et ne constitue pas une évaluation EVIMO exécutée. Aucun téléchargement réalisé à ce stade.


## D44 — Petit complément EVIMO2 train, références séparées du détecteur

**7 octobre 2026.** M14 acquiert la première séquence de l’archive gauche IMO, officiellement train malgré le mot `test` dans son nom. Le téléchargement s’arrête après six fichiers : 239,89 Mio transférés, aucune séquence eval récupérée.

Les 750 masques indiquent l’identité ; ils ne sont pas transformés en labels mobiles par simple présence. Les poses doivent être composées caméra→monde et objet→caméra, avec contrôles de dates, bruit, rotation et abstention. Une divergence entre les champs de distorsion doit être résolue avant un score pixel par pixel.

DSEC reste principal. Ce complément mono-caméra est un support d’audit, pas une preuve de généralisation routière ni une expérience stéréo. Les références publiques ne deviennent pas des entrées du détecteur sans marquage explicite oracle. Aucune annotation utilisateur requise ; aucune qualité de mobilité annoncée. [Audit M14](43_M14_EVIMO_AUDIT.md).


## D45 — Consolider avant le nouvel audit de données

**8 octobre 2026.** À la demande de l’utilisateur, R01 extrait les utilitaires partagés et clarifie les points d’entrée avant la suite. Les algorithmes, seuils, partitions, données et expériences historiques sont conservés. Les rapports gardent leurs formats ; toute future exécution archive aussi ses nouvelles dépendances.

La revue de l’architecture v2 conduit à prioriser un audit borné de DSEC-MOD, tout en conservant EVIMO. Elle ne supprime ni la compensation caméra, ni YOLO/Deep Learning/XYZ du cahier des charges, et n’adopte pas de nouveaux filtres sans comparaison. Aucun nouveau corpus acquis pendant R01. [Maintenance et preuves](44_PROJECT_MAINTENANCE.md).


## D46 — Auditer les annotations MOD avant de noter le mouvement

**8 octobre 2026.** M15 exploite les annotations officielles Moving de RENet sur les deux séquences locales train, sans demander d'annotations utilisateur. Les trois RGB de contrôle sont acquis par accès partiel, avec validation d'intégrité ; les références ne sont pas présentées comme des prédictions.

La différence 269 timestamps DSEC / 267 images MOD interdit un appariement implicite par indice. L'export conserve les dates et transformations inconnues. M16 doit vérifier le lien aux RGB originaux puis au repère du détecteur avant précision/rappel ou délai de mobilité.

Le cache global inclut les octets test ; le lecteur n'en matérialise pas les tableaux numériques. La réserve locale reste exclue des inspections de boîtes et du réglage. Le train MOD `09_e` ne sera pas ajouté au réglage en gardant `09_b` comme groupe indépendant ; `thun_00_a` est absent de ce corpus. Les limites de licence, couverture et précision temporelle restent explicites. [Rapport M15](45_M15_DSEC_MOD_AUDIT.md).


## D47 — Vérifier des correspondances explicites et conserver la parallaxe

**9 octobre 2026.** M16 confirme six paires de frames RGB MOD/DSEC sur train par reproduction photométrique avec une homographie issue de la calibration. Seules ces dates sont exportées comme vérifiées ; le reste du cache garde ses dates inconnues. Aucune déduction générale de suppression des deux extrémités sur le seul nombre de frames.

Les boîtes appartiennent à la grille rectifiée `camRect0` de la projection RGB. Ne pas les rectifier une deuxième fois ni les appliquer telles quelles aux événements natifs. L'homographie par rotation ne corrige pas la parallaxe des capteurs séparés de 4,57 cm ; son identification ne prouve pas une précision événementielle au pixel près.

M17 utilisera les 22 boîtes uniquement pour un diagnostic de support et d'association, sans les injecter dans la compensation caméra. Les durées d'exposition restent explicites ; aucun début de mouvement exact ni score de généralisation n'est déduit des six images. [Preuves M16](46_M16_DSEC_MOD_ALIGNMENT.md).


## D48 — Conserver l'échec observé et séparer défaut de support et absence de résidu

**10 octobre 2026.** M17 exécute le prototype M12 avec profondeur S01 fraîche sur les dates M16. Les 50 ms de représentation et le pas de 20 ms sont conservés ; les premières dates n'ont pas assez d'historique. Aucun remplacement de date ou de profondeur par une référence.

L'inférence est enregistrée avant la consultation des boîtes. Les régions sans suivi, sans profondeur ou sans modèle exploitable restent distinctes des régions évaluées sans résidu. Un point partagé par des boîtes n'est pas plusieurs observations indépendantes ; les zones non annotées ne deviennent pas des négatifs certifiés.

Aucun résidu >3 px n'est observé sur les quatre paires traitables. Ce résultat défavorable est conservé sans abaisser le seuil pour produire des candidats. M18 comparera des fenêtres sans chevauchement avec les références, sur quatre dates communes ; les changements de densité et de stéréo seront aussi mesurés. Cette expérience ne valide ni mobilité réelle, ni précision/rappel globale, ni temps réel. [Rapport M17](47_M17_REFERENCE_DIAGNOSTIC.md).

## D49 — Ne pas adopter la fenêtre courte au seul gain de calcul

**10 octobre 2026.** M18 reproduit M17 avec 50 ms. La variante 20 ms réduit le support de profondeur dans les références et ne produit aucun candidat dans les 15 boîtes communes. Les deux dates supplémentaires de démarrage restent séparées. Conserver 50 ms, les seuils et les inconnus ; aucun résidu hors annotation n'est automatiquement une fausse alerte. [Bilan M18](49_M18_TEMPORAL_WINDOWS.md).

## D50 — EMatch comme diagnostic train, provenance et représentation explicites

**10 octobre 2026.** L'audit statique M19 identifie un contrat 100 ms / 15 canaux, un défaut d'unités dans le générateur de cache publié et une liste train qui inclut nos quatre séquences locales. Aucun poids n'a été chargé ; ces observations ne prouvent pas quel cache a servi au checkpoint diffusé.

Préparer un adaptateur d'inférence sans GT ni augmentation, puis un essai borné sur train. Conserver le suivi M17 pour la comparaison de profondeur et rapporter le support commun séparément de la couverture gagnée. Ne pas appeler `09_b` indépendant d'un checkpoint qui aurait suivi le protocole publié. Aucune nouvelle inspection du test réservé, aucun entraînement, aucune adoption automatique d'EMatch. [Audit M19](50_M19_EMATCH_AUDIT.md).

