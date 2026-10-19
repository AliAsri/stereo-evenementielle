# Audit technique et scientifique du projet de stéréo événementielle

**Date de l’audit : 18 octobre 2026**  
**Projet :** Stéréo Vision par Caméras Événementielles pour la Détection Rapide de Mouvement  
**Dépôt local audité :** `C:\Users\moali\OneDrive\Desktop\PFE 3`  
**Priorités :** 1. rapidité ; 2. détection fiable du mouvement ; 3. estimation 3D.  
**Statut :** audit en lecture seule terminé ; aucune correction du code engagée.

> Ce document reprend le rapport d’audit présenté dans la conversation. Sa création et ses copies sont une opération documentaire ultérieure, demandée par l’utilisateur. Les mesures identifiées comme sauvegardées n’ont pas été reproduites pendant l’audit. Les références de lignes concernent l’état inspecté le 18 octobre 2026.

## Synthèse

**Le projet dispose d’un véritable prototype intégré, mais les deux objectifs prioritaires — rapidité et détection fiable du mouvement indépendant — ne sont pas encore démontrés.** La base technique est exploitable : lecture événementielle, YOLO, stéréo, reconstruction 3D et visualisation existent réellement. Le principal risque est désormais de confondre un pipeline qui s’exécute avec un système scientifiquement validé.

**Aucun fichier n’a été modifié pendant l’audit.** Aucun entraînement, téléchargement ou nouvel essai EVIMO2 n’a été lancé. La rédaction de ce Markdown ne constitue pas une autorisation d’implémenter les corrections proposées.

## 1. Périmètre et vérifications réalisées

L’inspection a couvert l’organisation du dépôt, les parcours principaux, les modules expérimentaux, les configurations, les notebooks, les tests, les dépendances et les résultats sauvegardés.

| Contrôle effectué pendant l’audit | Résultat observé |
|---|---|
| Analyse syntaxique et compilation en mémoire de 118 fichiers Python | Aucune erreur |
| Analyse des cellules Python des deux notebooks actuels | Aucune erreur syntaxique |
| Sous-ensemble de tests compatible avec une exécution sans écriture | **245 réussis, aucune erreur ni échec** |
| Vérification des huit entrées du démonstrateur | Tailles et SHA-256 conformes |
| Vérification complète des deux exports YOLO | Conforme : fichiers, labels, canaux et séparation des groupes |
| Empreintes des checkpoints `best` et `last` des deux entraînements pilotes | Conformes aux empreintes enregistrées |
| Ordre des timestamps de la séquence principale, gauche et droite | Non décroissant sur l’ensemble des deux fichiers |
| Recalcul indépendant des cartes de rectification | Écart maximal d’environ **0,0011 pixel** |
| Cohérence extrinsèques, baseline et matrice Q | Cohérente sur la calibration vérifiée |
| Contre-exemple synthétique de l’association 3D | Défaut de sélection du fond reproduit |

### Limites des vérifications

- Les **302 tests** mentionnés dans l’historique n’ont pas tous été réexécutés : certains créent des fichiers temporaires. Les 245 ci-dessus sont les tests effectivement exécutés pendant cet audit.
- Les entraînements et le démonstrateur complet n’ont pas été relancés. Leurs performances ci-dessous proviennent des résultats sauvegardés.
- La cohérence logicielle des timestamps ne prouve pas une synchronisation physique parfaite des capteurs.
- L’état distant de GitHub et une installation sur une machine vierge n’ont pas été vérifiés.
- Les contrôles effectués ne constituent pas une preuve d’absence de tout bug dans les scripts historiques.

## 2. Pipeline réellement implémenté

Le parcours principal est [scripts/run_integrated_demo.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/scripts/run_integrated_demo.py>).

```text
Événements DSEC gauche/droite
          │
          ├─ Fenêtres causales de 50 ms
          │
          ├─ Image native positive/négative/totale
          │        └─ YOLO11n → boîtes et classes
          │
          └─ Rectification + images événementielles
                   ├─ SGBM + contrôles → disparité → profondeur
                   │
                   └─ Coins + suivi LK + profondeur précédente
                            └─ PnP/RANSAC → modèle rigide dominant
                                     └─ Résidus par point
          │
          ▼
Association des boîtes aux surfaces 3D et aux points suivis
          │
          ▼
JSON / tableaux / visualisation / GIF
Mobilité des objets : UNCONFIRMED
```

Points importants :

- Les représentations événementielles alimentent réellement YOLO.
- La profondeur provient réellement de la stéréo, sans profondeur de référence injectée dans le démonstrateur.
- La compensation utilise la profondeur à la date précédente.
- Le modèle rigide estimé représente le mouvement dominant des correspondances. Il n’est pas automatiquement une pose caméra correcte.
- La branche historique d’activité rapide M01 n’est pas devenue une décision rapide de mobilité intégrée.
- Il n’existe pas encore, dans ce parcours, de suivi temporel des identités d’objets associé à une décision validée « mobile / immobile / indéterminé ».

## 3. Matrice de conformité aux objectifs

| Objectif | État réel | Évaluation |
|---|---|---|
| Exploiter des événements stéréo | Lecture, représentation et rectification implémentées | **Fonctionnel sur les données vérifiées** |
| Utiliser le Deep Learning et YOLO | YOLO11n entraîné et intégré | **Réalisé techniquement** |
| Détecter personnes et voitures | Détections et métriques disponibles | **Partiel : validation étroite** |
| Détecter les camions | Y02 entraîné avec cette classe | **Non qualifié : aucun camion en validation locale** |
| Détection rapide | Environ 258–270 ms de calcul médian, budget 20 ms | **Objectif non atteint** |
| Séparer mouvement objet/caméra | Compensation et résidus présents | **Non validé scientifiquement** |
| Estimer la profondeur | SGBM avec abstentions et métriques historiques | **Fonctionnel, couverture limitée** |
| Estimer les coordonnées 3D des objets | Point de surface associé à une boîte | **Partiel : appartenance à l’objet non garantie** |
| Mesurer fausses alertes et délai de détection | Références adaptées insuffisantes | **Non démontré** |
| Reproduction par un tiers | Provenance locale solide, publication incomplète | **Partiel** |

## 4. Ce que les résultats permettent réellement de dire

### 4.1. Détection YOLO

Les métriques sauvegardées donnent :

| Modèle | Classes entraînées | AP50 personne | AP50 voiture | AP50 camion | mAP50 |
|---|---|---:|---:|---:|---:|
| Y01 | Personne, voiture | 0,095 | 0,380 | — | 0,237 |
| Y02 | Personne, voiture, camion | 0,312 | 0,458 | Non mesurable | 0,385 |

Sources : [métriques Y01](<C:/Users/moali/OneDrive/Desktop/PFE 3/outputs/colab/Y01_20261003T191753Z/pilot-metrics.json>) et [métriques Y02](<C:/Users/moali/OneDrive/Desktop/PFE 3/outputs/colab/Y02_20261015T134856Z/pilot-metrics.json>).

**Y02 améliore les métriques enregistrées sur cette validation.** Cela ne démontre ni une bonne généralisation, ni la qualité de la classe camion, ni la détection du mouvement.

Les deux entraînements pilotes comportent cinq époques. Leurs pertes concernent la détection : localisation des boîtes, classification et DFL. Aucune perte n’apprend directement la mobilité indépendante ou la profondeur.

### 4.2. Rapidité du démonstrateur

| Résultat sauvegardé | Calcul médian | Premier appel | Dépassements du budget de 20 ms |
|---|---:|---:|---:|
| Y01, parcours par défaut | 270,0 ms | 3 523 ms | 17/17 |
| Y02, après optimisation stéréo | 257,8 ms | 3 172 ms | 17/17 |

Sources : [rejeu Y01](<C:/Users/moali/OneDrive/Desktop/PFE 3/outputs/demo_y01_20261017/summary.json>) et [rejeu Y02](<C:/Users/moali/OneDrive/Desktop/PFE 3/outputs/stereo_speed_20261017/after/summary.json>).

Ces mesures portent sur un extrait de développement appartenant à l’entraînement. Le GIF est un rejeu : son apparence fluide ne démontre pas le temps réel.

### 4.3. Stéréo

Le résultat historique S01 sur `thun_00_a` rapporte environ :

- **1,05 px** d’erreur moyenne de disparité sur l’intersection valide ;
- **36 %** de couverture des pixels de référence ;
- **65,5 %** de pixels de référence manquants ou présentant une erreur supérieure à 3 px ;
- **1,42 m** d’erreur absolue moyenne de profondeur sur l’intersection évaluée.

La faible erreur conditionnelle doit donc toujours être accompagnée de la couverture. Ce résultat historique ne qualifie pas, à lui seul, toutes les modifications stéréo ultérieures.

Source : [résultats S01](<C:/Users/moali/OneDrive/Desktop/PFE 3/outputs/stereo/S01/summary.json>).

## 5. Problèmes identifiés et corrections proposées

Les éléments « bloquants » ci-dessous bloquent une **affirmation scientifique ou un objectif**, pas nécessairement l’exécution du programme. Les corrections et tests proposés n’ont pas été implémentés dans le cadre de cet audit.

### F1 — Bloquant : le budget temporel est largement dépassé

**Preuve.** Les deux rejeux dépassent 20 ms sur toutes leurs sorties. Sur Y01, les médianes par poste sont approximativement : lecture/représentation 108 ms, stéréo 75 ms, YOLO 38 ms et mouvement 27 ms. Plusieurs postes dépassent individuellement le budget.

**Localisation.** [scripts/run_integrated_demo.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/scripts/run_integrated_demo.py>), à partir de la ligne 127, et résumés temporels cités précédemment.

**Impact.** Le pipeline actuel ne peut pas soutenir cette cadence sur la configuration CPU mesurée. Le retard FIFO sauvegardé est une simulation, pas une mesure du délai réel d’alerte.

**Correction proposée.** Fixer le matériel cible et distinguer explicitement la cadence de décision du mouvement, celle de YOLO et celle de la 3D. Décider ensuite d’une modification du chemin critique. Un simple réglage supplémentaire de SGBM ne justifie pas l’espoir de passer de 270 à 20 ms.

**Vérification attendue.** Mesurer démarrage, médiane, p95, échéances manquées et qualité sur les mêmes entrées. Toute réutilisation de résultats anciens doit avoir un âge explicite et un contrat géométrique.

### F2 — Bloquant : la sortie finale ne confirme aucune mobilité

**Preuve.** [src/pfe_events/object_surface.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/src/pfe_events/object_surface.py>), ligne 118, retourne systématiquement `mobility: UNCONFIRMED`. Les autres champs comptent des supports et des candidats résiduels.

**Impact.** Une voiture détectée, un point résiduel et un objet réellement mobile restent trois notions différentes. L’objectif principal demeure incomplet.

**Correction proposée.** Définir une décision temporelle par objet avec trois états : mobile, immobile et indéterminé, accompagnée des conditions nécessaires pour chaque état. L’absence de suivi ou de profondeur doit conserver l’abstention.

**Vérification attendue.** Évaluation sur des références indépendantes et correctement alignées, comprenant mouvements indépendants et cas négatifs. Les boîtes seules ne suffisent pas.

### F3 — Bloquant : les contrôles internes du suivi et de la pose ne garantissent pas leur justesse

**Preuves.**

- Sur le contrôle EVIMO2 figé 211→217, seulement deux suivis longs de la cible subsistent, avec erreurs de référence d’environ **1,08 et 5,08 px**.
- L’essai de récence accepte une pose en interne, mais ses trois suivis cibles restent à plus de 3 px de la référence.
- Des tests existants montrent qu’une profondeur biaisée produit de faux candidats et qu’une couche mobile dominante peut être prise pour le mouvement rigide dominant.

**Localisation.** [src/pfe_events/clip_motion.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/src/pfe_events/clip_motion.py>), à partir de la ligne 52 ; [src/pfe_events/rigid_motion.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/src/pfe_events/rigid_motion.py>), à partir de la ligne 89 ; [tests/test_rigid_motion.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/tests/test_rigid_motion.py>), lignes 74 et 79 ; [docs/43_M14_EVIMO_AUDIT.md](<C:/Users/moali/OneDrive/Desktop/PFE 3/docs/43_M14_EVIMO_AUDIT.md>).

**Impact.** Un faible résidu peut correspondre à une mauvaise correspondance cohérente avec le modèle. Un grand résidu peut provenir de la profondeur, de l’appariement ou de la pose.

**Correction proposée.** Avant une nouvelle variante, identifier une hypothèse précise sur l’échec des correspondances et son critère de réussite. Un score continu peut aider l’analyse, mais ne corrige pas une correspondance fausse.

**Vérification attendue.** Erreur de suivi contre référence, couverture de la cible, erreur de pose et coût mesurés séparément. Les essais clos ne doivent pas être relancés à l’identique ni remplacés par une paire choisie après observation des résultats.

### F4 — Bloquant pour la généralisation : validation beaucoup trop peu diversifiée

**Preuve vérifiée dans les annotations.**

- Validation : 238 images d’un seul extrait d’environ **11,85 secondes**.
- Les 238 annotations de personne correspondent à **un seul identifiant de piste**.
- Les voitures représentent neuf identifiants de piste.
- Aucun camion n’est présent.
- L’entraînement utilise deux séquences du même groupe `zurich_city_04`.
- Le démonstrateur intégré utilise un extrait d’entraînement.

Ces identifiants ne prouvent pas une diversité équivalente de personnes ou véhicules indépendants.

**Localisation.** [scripts/export_yolo_pilot.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/scripts/export_yolo_pilot.py>), [data/processed/dsec_yolo_pilot_v1](<C:/Users/moali/OneDrive/Desktop/PFE 3/data/processed/dsec_yolo_pilot_v1>) et [data/processed/dsec_yolo_truck_v1](<C:/Users/moali/OneDrive/Desktop/PFE 3/data/processed/dsec_yolo_truck_v1>).

**Impact.** Les métriques reflètent fortement une même scène et les mêmes trajectoires répétées. La qualification camion est impossible.

**Correction proposée.** Préparer une évaluation distincte, par séquences et objets, avec annotations publiques existantes. Toute extension du périmètre doit être décidée avant les résultats. Si elle est exclue, limiter explicitement les conclusions au prototype local.

**Vérification attendue.** Nombre de séquences, durées, pistes, instances par classe et cas négatifs ; séparation des groupes ; résultats par séquence.

**Aucune fuite train/validation n’a été trouvée dans les exports vérifiés.** Le problème démontré est la représentativité, pas une fuite avérée.

### F5 — Important : la 3D associée à une boîte peut être celle du fond

**Preuve reproduite pendant l’audit.** Sur un cas synthétique contenant une petite cible à **5 m** devant un fond à **20 m**, la fonction retourne `SURFACE_ESTIMATE` à **20 m**, avec support complet et dispersion interquartile nulle.

**Localisation.** [src/pfe_events/object_surface.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/src/pfe_events/object_surface.py>), lignes 81–100.

**Cause.** Lorsque le fond domine la zone intérieure, médiane et MAD le privilégient. Une faible dispersion n’établit pas l’appartenance à l’objet.

**Impact.** Les coordonnées peuvent être géométriquement correctes pour une surface qui n’appartient pas à l’objet détecté. Le code reconnaît déjà cette limite dans son intitulé « surface », ce qui est approprié.

**Correction proposée.** Renforcer l’association ou l’abstention lorsque l’appartenance est ambiguë, en commençant par une méthode simple comparée à l’existant.

**Vérification attendue.** Cas cible minoritaire, fond majoritaire, occultation et profondeur absente. Une correction doit éviter la fausse association sans seulement augmenter le nombre de coordonnées produites.

### F6 — Important : plage de profondeur effective plus limitée que le filtre annoncé

**Preuve.** [src/pfe_events/stereo.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/src/pfe_events/stereo.py>), ligne 11, limite la recherche à 96 disparités. Avec la calibration vérifiée, `f ≈ 569,29 px` et `B ≈ 0,599 m` : `f × B / 96 ≈ 3,55 m`.

La limite pratique proche est donc voisine de **3,6 m**, alors que `SurfaceConfig` accepte théoriquement les profondeurs à partir de 1 m ([object_surface.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/src/pfe_events/object_surface.py>), ligne 16).

**Impact.** Autoriser `min_z_m=1` ne rend pas les objets à 1 m reconstructibles. Leur absence de profondeur peut être structurelle.

**Correction proposée.** Documenter la plage effective et distinguer filtre de validité et capacité de recherche. N’augmenter la plage de disparités qu’avec une justification de besoin et de coût.

**Vérification attendue.** Plans synthétiques de disparités connues, cas hors plage et abstention explicite ; évaluation erreur/couverture par distance.

### F7 — Important : l’état local n’est pas encore une version reproductible publiée

**Preuve.** Git indique **47 fichiers suivis modifiés**, ainsi que des fichiers nécessaires non suivis, notamment :

- `configs/demo_assets.json` ;
- `scripts/manage_demo_assets.py` ;
- `notebooks/Y02_yolo11n_truck.ipynb` ;
- plusieurs nouveaux tests.

Le [README.md](<C:/Users/moali/OneDrive/Desktop/PFE 3/README.md>), ligne 82, décrit pourtant le manifeste comme versionné. Le paquet d’artefacts est local et exclu de Git.

**Impact.** Copier le dépôt actuellement enregistré ne garantit pas de retrouver l’état audité. Aucune conclusion n’est formulée sur l’état distant de GitHub, qui n’a pas été contrôlé.

**Correction proposée.** Après autorisation d’implémenter, préparer un état Git cohérent et un mode de récupération des artefacts avec empreintes, sans ajouter les données volumineuses au dépôt.

**Vérification attendue.** Reconstruction depuis un clone neuf, acquisition contrôlée des entrées, vérification des empreintes et exécution du parcours documenté.

### F8 — Important : incompatibilité conditionnelle de la cellule de reprise YOLO

**Preuve.**

- Le générateur actuel [scripts/build_yolo_notebook.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/scripts/build_yolo_notebook.py>), ligne 259, définit `metrics_dict(metrics, purpose, support)`.
- La cellule [notebooks/Y01_retry_overfit_cell.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/notebooks/Y01_retry_overfit_cell.py>), ligne 77, appelle cette fonction avec deux arguments.

Cela produit un argument obligatoire manquant avec l’API actuelle.

**Nuance.** Le notebook Y01 déjà conservé utilise encore l’ancienne signature : sa reprise historique n’est pas déclarée cassée. Le défaut apparaît avec un notebook régénéré selon la nouvelle API.

**Impact.** Échec possible de la cellule de reprise après un entraînement coûteux.

**Correction proposée.** Aligner la cellule sur la signature actuelle ou figer explicitement sa compatibilité avec l’ancien notebook.

**Vérification attendue.** Contrôle des signatures et exécution des cellules de reporting avec métriques simulées, sans entraînement.

### F9 — Important : reproductibilité des entraînements incomplète

**Preuve.** Le générateur Colab [scripts/build_yolo_notebook.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/scripts/build_yolo_notebook.py>), à partir de la ligne 74, fixe Ultralytics, mais ne verrouille pas initialement toute la pile. Les environnements Colab et local diffèrent notamment en Python et PyTorch. Les versions et empreintes sont ensuite enregistrées, ce qui est utile.

**Impact.** Les poids existants sont identifiables, mais une reproduction future de l’entraînement peut utiliser une autre pile. Une seule exécution ne permet pas de mesurer la variabilité.

**Correction proposée.** Conserver un environnement d’entraînement précisément défini, les arguments effectifs, la provenance des poids initiaux et les graines. Les deux environnements locaux inspection/démonstration ont une utilité ; leur fusion n’est pas nécessaire.

**Vérification attendue.** Installation propre, contrôle des tenseurs d’entrée et petit essai reproductible. Une répétition d’entraînement n’est justifiée qu’après stabilisation du protocole de validation.

### F10 — Important : vérification des entrées disponible mais non imposée par le parcours principal

**Preuve.** `check_inputs`, dans [scripts/run_integrated_demo.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/scripts/run_integrated_demo.py>), ligne 31, vérifie la présence des fichiers. Le démonstrateur enregistre ensuite leurs empreintes, mais ne les confronte pas systématiquement au manifeste attendu. Cette comparaison existe dans l’outil séparé de gestion des artefacts.

**Impact.** Des entrées remplacées peuvent produire un nouveau résultat sans correspondre à l’expérience de référence. Les entrées présentes ont toutefois passé la vérification pendant cet audit.

**Correction proposée.** Rendre explicite le mode « reproduction figée » avec vérification préalable du manifeste, et distinguer ce mode d’une expérience volontairement différente.

**Vérification attendue.** Une entrée altérée doit être refusée avant le calcul dans le mode de reproduction.

### F11 — Modéré : portabilité limitée et paramètres d’expérience dispersés

**Preuve.** [scripts/run_integrated_demo.py](<C:/Users/moali/OneDrive/Desktop/PFE 3/scripts/run_integrated_demo.py>), lignes 44–45, charge une police par chemin Windows fixe. La séquence temporelle est fixée dans le script à partir de la ligne 127.

**Impact.** Échec possible sur une autre machine et changement d’extrait nécessitant une modification du code.

**Correction proposée.** Une configuration d’expérience unique et un repli de police suffisent. Aucun nouveau framework n’est nécessaire.

**Vérification attendue.** Démarrage sans cette police et validation de la configuration avant tout calcul long.

### F12 — Modéré : documentation et historique rendent l’état courant difficile à identifier

**Preuve.** Le dépôt contient 47 scripts Python, 57 documents Markdown à la racine de `docs`, une progression de plus de 1 300 lignes et une feuille de route d’environ 150 lignes. Le [README.md](<C:/Users/moali/OneDrive/Desktop/PFE 3/README.md>), ligne 27, affiche encore 345,8 ms comme dernier benchmark CPU Y02, alors qu’un résultat ultérieur existe.

Par ailleurs, [.gitignore](<C:/Users/moali/OneDrive/Desktop/PFE 3/.gitignore>) exclut `outputs/`, mais pas les dossiers locaux `output/` et `tmp/`, actuellement non suivis.

**Impact.** Risque de présenter un ancien résultat comme état courant, de relancer un essai clos ou d’ajouter involontairement des fichiers de génération au dépôt.

**Correction proposée.** Séparer clairement parcours actif, outils maintenus et expériences historiques. Corriger les informations courantes et les exclusions ciblées, sans supprimer les acquis.

**Vérification attendue.** Toutes les affirmations courantes renvoient à une preuve datée ; la commande principale et la prochaine décision sont immédiatement identifiables.

## 6. Géométrie, synchronisation et causalité : ce qui est rassurant

Aucune inversion de transformation ou erreur de baseline n’a été confirmée dans le parcours vérifié :

- baseline issue des extrinsèques et de Q : environ **0,599033 m**, cohérente ;
- rotation relative après rectification : numériquement proche de l’identité ;
- cartes cohérentes avec les paramètres de calibration ;
- décodage de la disparité fixe et rejet des valeurs invalides présents ;
- contrôle de cohérence gauche/droite présent ;
- fenêtres causales et provenance temporelle explicites.

La contrainte `depth_us == previous_us` est **un garde-fou correct du modèle actuel**. La supprimer pour réutiliser une profondeur ancienne créerait un problème géométrique. Une architecture à deux cadences nécessiterait un transport temporel défini, une limite d’âge et une validation.

Deux limites restent à conserver :

- une représentation de 50 ms agrège des événements de plusieurs instants ;
- l’alignement DSEC-MOD utilisant la rotation seule ne supprime pas la parallaxe due à la translation entre capteurs. Il ne constitue donc pas une référence parfaite au pixel près.

## 7. Risques prioritaires

| Risque | Niveau | Conséquence |
|---|---|---|
| Confondre résidu et mouvement indépendant | Critique | Conclusion scientifique injustifiée |
| Confondre coût partiel, cadence de rejeu et délai réel | Critique | Revendication de rapidité incorrecte |
| Généraliser depuis une seule courte scène de validation | Élevé | Performances surestimées |
| Associer le fond à l’objet en 3D | Élevé | Distance d’objet incorrecte malgré un calcul cohérent |
| Multiplier les variantes sur les mêmes contrôles | Élevé | Surajustement expérimental et perte de temps |
| Dépendre de fichiers locaux non publiés | Élevé | Reproduction impossible pour un tiers |
| Accumuler des rapports et chemins d’exécution | Modéré | Maintenance et présentation difficiles |

## 8. Feuille de route pour terminer le PFE

L’ordre **rapidité → fiabilité → 3D** reste pertinent. La définition de l’évaluation constitue un préalable transversal.

| Étape | Travail proposé | Critère de sortie |
|---|---|---|
| **1. Figer une référence auditable** | Identifier une version de code, les entrées, les poids, le matériel et les métriques ; corriger les incohérences de reproduction | Un tiers sait exactement ce qui est exécuté et ce qui est revendiqué |
| **2. Décider le chemin rapide** | Exploiter les coûts existants pour choisir une seule modification architecturale utile | Gain mesuré avec qualité et fraîcheur préservées, ou limite de cadence explicitement acceptée |
| **3. Débloquer la validation du mouvement** | Définir une référence adaptée et une hypothèse méthodologique précise | Erreur de suivi/pose, couverture, abstentions et décision de mobilité évaluables |
| **4. Qualifier la détection** | Évaluer sur une diversité suffisante ; qualifier séparément camion | Résultats par classe et séquence, sans classe annoncée sans référence |
| **5. Fiabiliser l’association 3D** | Traiter fond/objet, plage de distance et données manquantes | Erreur et couverture mesurées, abstention sur les cas ambigus |
| **6. Finaliser la démonstration** | Un parcours, une configuration, une présentation des résultats et limites | Démonstration reproductible et conclusions défendables |

**Le dépôt actuel ne permet pas, à lui seul, de terminer la validation scientifique de la mobilité.** Il faudra soit autoriser un protocole de référence adapté, soit réduire explicitement la portée du résultat final. Cela ne nécessite pas de demander des annotations manuelles à l’utilisateur.

### Comparaisons et ablations raisonnables

Il ne faut pas lancer toutes ces expériences automatiquement. Chacune doit répondre à une question encore ouverte.

| Comparaison | Question | Mesures |
|---|---|---|
| YOLO préentraîné sans adaptation vs Y01/Y02 | L’adaptation événementielle apporte-t-elle un gain sur les mêmes données ? | AP par classe, rappel, coût, même prétraitement |
| Variante temporelle proposée vs parcours conservé | Le gain de vitesse conserve-t-il l’information utile ? | Coût complet, âge des sorties, qualité et abstentions |
| SGBM avec/sans contrôle gauche-droite, sur référence existante | Quel compromis erreur/couverture apporte ce contrôle ? | EPE, couverture, erreurs ou absences sur toute la GT, coût |
| Association 3D actuelle vs méthode simple alternative | Réduit-on les associations au fond ? | Erreur, fausses associations, couverture, coût |
| Mouvement apparent sans compensation vs résidu compensé | La compensation améliore-t-elle réellement la séparation ? | Uniquement avec référence alignée et cas négatifs adaptés |

Les contrôles EVIMO2 déjà clos restent des preuves d’échec et des cas de régression. Ils ne doivent pas devenir un jeu sur lequel chercher indéfiniment une variante gagnante.

## 9. Documentation à maintenir

Il est recommandé de consolider les fichiers existants plutôt que créer une nouvelle série de rapports :

| Fichier | Rôle |
|---|---|
| `README.md` | Exécution, état actuel, résultat principal et limites |
| `docs/PROJECT_BRIEF.md` | Objectifs et critères de réussite |
| `docs/05_PROJECT_ARCHITECTURE.md` | Pipeline, repères, timestamps et contrats |
| `docs/02_DATASETS.md` | Provenance, groupes, annotations et limites |
| `docs/11_TRAINING.md` | Environnement, pertes, paramètres et checkpoints |
| `docs/12_EXPERIMENTS.md` | Protocoles et comparaisons prévues |
| `docs/13_RESULTS.md` | Résultats datés avec liens vers leurs preuves |
| `docs/15_LIMITATIONS.md` | Affirmations autorisées et non démontrées |
| `docs/20_NEXT_STEPS.md` | Une prochaine décision et ses critères d’acceptation |

`docs/19_PROGRESS.md` peut rester l’historique, sans être la porte d’entrée du projet. Le miroir `markdowns/` reste une copie locale, pas une seconde source éditoriale.

## 10. Conclusion de l’audit

**Le projet est dans la bonne direction pour un prototype de stéréo événementielle intégrant YOLO et une estimation de surface 3D. Il n’a pas encore démontré un détecteur rapide et fiable d’objets mobiles.**

Les affirmations suivantes restent non étayées :

- fonctionnement temps réel au pas de 20 ms ;
- détection fiable du mouvement indépendant ;
- précision/rappel de mobilité ou délai de début de mouvement ;
- performance camion indépendante ;
- coordonnées garanties sur l’objet plutôt que sur le fond ;
- généralisation au-delà des quelques extraits disponibles.

La priorité n’est pas une refonte générale. Elle est de **figer une version reproductible, choisir une modification utile du chemin critique, puis résoudre le manque de référence pour la mobilité**. Les corrections de notebook, de publication et de documentation sont concrètes ; elles ne doivent pas être présentées comme des progrès de précision scientifique.

**Aucune correction ni implémentation n’a été engagée par cet audit. Toute mise en œuvre nécessite une nouvelle instruction explicite de l’utilisateur.**
