# Suivi simple du projet

**Mis à jour le 11 octobre 2026. Cette page est le point de reprise prioritaire.** Les anciennes feuilles de route restent historiques ; les actions EMatch proposées dans M19 sont mises en pause par la décision de simplification.

## Audit global R02 — 11 octobre 2026

**Audit terminé ; les nouvelles étapes restent en pause jusqu'à la reprise demandée par l'utilisateur.** La revue a porté sur les chemins critiques de lecture, causalité, géométrie, stéréo, suivi, pose, association XYZ, visualisation, import/export et évaluation. Elle complète les contrôles automatiques de l'ensemble `src/`, `scripts/` et `tests/`, ainsi que les contrôles supplémentaires des notebooks, configurations et diagnostics de l'extrait. Les 201 fichiers de travail sauvegardés avant correction et leurs empreintes sont conservés sous `outputs/review/R02/`.

Quatre défauts confirmés ont été corrigés :

- **Stéréo :** une tolérance gauche/droite infinie pouvait désactiver le contrôle de cohérence ; NaN pouvait supprimer tous les pixels. Ces valeurs et les paramètres SGBM de type ou signe incorrect sont désormais refusés. Les paramètres utilisés pour les résultats existants restent valides.
- **Commande de contrôle :** un délai dépassé ou un lancement impossible des tests pouvait empêcher la production du rapport. Le rapport `FAILED`, le motif et la sortie partielle sont maintenant conservés ; une source illisible est également signalée.
- **Lecteur HTML :** des tableaux de points de longueurs différentes pouvaient être tronqués silencieusement par `zip`. Le lecteur refuse maintenant ces fichiers incomplets avant de construire l'affichage. Aucun tableau incomplet n'a été trouvé dans les résultats actuels.
- **Image récapitulative :** au-delà de six détections, le texte des détections supplémentaires chevauchait le pied de page. L'espacement est corrigé et vérifié sur une image de test explicitement marquée, avec sept détections dupliquées uniquement pour contrôler la mise en page. L'extrait actuel ne dépasse pas six détections par image.

La description des environnements et le caractère historique de la feuille de maintenance R01 ont également été clarifiés. Aucun nouveau modèle, réglage scientifique, dataset ou entraînement n'a été ajouté.

| Contrôle | Résultat vérifié |
|---|---|
| Suite de tests | **215 réussis**, contre 207 avant correction ; huit nouveaux tests de régression |
| Code et commandes | **102 fichiers Python**, **30 aides CLI** ; dix fichiers Python supplémentaires de diagnostics/notebook compilés |
| Environnements | `pip check` réussi pour les deux environnements ; six et 42 versions verrouillées correspondent aux installations |
| Rejeu complet depuis les événements | **17 images**, **153 tableaux exactement identiques**, résultats scientifiques JSON identiques hors durées |
| YOLO et XYZ du rejeu | **77 occurrences de détection**, **45 estimations de surface**, **32 abstentions** ; aucune identité persistante déduite |
| Lecteurs DSEC | Les trois lecteurs concordent exactement sur **54 fenêtres**, dans les six flux gauche/droite des trois séquences acquises ; bornes `[début, fin)` vérifiées |
| Export YOLO | **774 images**, **1 560 empreintes** ; labels, séparation des groupes et canaux RGB/BGR vérifiés |
| Lecteur HTML reconstruit | Identique octet par octet au lecteur actuel : **17 images temporelles, 34 PNG intégrées** ; logique JavaScript contrôlée avec DOM/canvas simulés |
| Configurations et notebooks | 14 JSON lisibles ; 14 cellules de code compilées dans les deux notebooks, dont l'archive ; aucun entraînement exécuté |

**Limites restantes :** les tests ne démontrent pas la détection fiable du mouvement indépendant. La pose demeure sensible au support, YOLO reste limité aux deux classes du pilote et une surface XYZ peut appartenir au fond. La chaîne complète demeure hors temps réel : ce rejeu de contrôle donne environ **895 ms médians par sortie**, pour un pas source de 20 ms. Cette mesure unique, sous charge d'audit, n'est pas une comparaison de vitesse avec le rejeu précédent. Le rendu du lecteur dans un navigateur réel n'a pas été validé ; le contrôle JavaScript simulé ne le remplace pas. Les notebooks ont été compilés, pas réexécutés sur GPU. Les acquisitions réseau, l'ensemble des anciennes expériences et chaque instant des flux complets n'ont pas été rejoués. Les contrôles documentaires portent sur les destinations locales des liens, sans vérification des URL externes ni des ancres.

Preuves : [bilan de revue](../outputs/review/R02/report.json), [tests et CLI](../outputs/review/R02/final-checks/report.json), [journal des 215 tests](../outputs/review/R02/final-checks/tests.log), [comparaisons et contrôles supplémentaires](../outputs/review/R02/verification.json), [export YOLO](../outputs/review/R02/yolo-export.json), [environnements](../outputs/review/R02/environments.json), [interactions du lecteur](../outputs/review/R02/viewer/interaction-checks.json).

## Le livrable à construire

Un rejeu DSEC qui montre des candidats de mouvement indépendant, puis leur classe YOLO et une profondeur/position XYZ quand elles sont disponibles. Afficher aussi les cas inconnus et le temps de traitement. La reconnaissance d’une voiture ou l’activité d’un pixel ne suffit pas à prouver son mouvement propre.

Nous avançons sur un extrait et une configuration à la fois. La séparation objet/caméra reste l'objectif ; YOLO et XYZ sont maintenant réunis dans un affichage avec les indices de mouvement existants, sans attendre une validation complète de cette séparation.

## Ce que nous gardons / ce que nous mettons en pause

| Garder | Mettre en pause |
|---|---|
| DSEC et références publiques déjà acquises | Nouveaux datasets |
| Représentation de 50 ms, suivi et stéréo S01 | Intégration EMatch et nouvelles architectures |
| Compensation géométrique de la caméra | Réglages multiples et optimisations supplémentaires |
| YOLO existant pour l’intégration finale | Nouvel entraînement YOLO pour l’instant |
| Tous les anciens résultats, conservés | Nouveaux rapports numérotés pour chaque petite action |

Aucune annotation manuelle à réaliser. Aucun document source ni résultat historique supprimé.

## Action réalisée : comprendre un camion

Nous avons repris le camion de `zurich_city_04_b`, tube public 11, frame MOD 134. Le prototype existant est rejoué sur **21 dates couvrant 0,4 seconde**, avec fenêtres de 50 ms et pas de 20 ms. Aucun seuil ni algorithme modifié.

La boîte publique n’est vérifiée qu’à la dernière date. Dans les images précédentes, le même rectangle sert de **zone fixe d’inspection** : il n’est ni une annotation interpolée, ni une trajectoire d’objet. Les points sont redétectés à chaque paire et ne représentent pas des identités persistantes. La zone contient aussi du fond.

| Étape | Résultat |
|---|---|
| Suivi dans la zone | 70 à 83 points selon la date |
| Profondeur disponible | 59 à 77 points selon la date |
| Résidu maximal dans la zone sur l’extrait | 1,073 px, inférieur au seuil de 3 px |
| Candidats au-dessus du seuil dans la zone | Aucun sur les 21 dates |
| À la date annotée | 76 points suivis, 65 avec profondeur ; résidu médian 0,366 px, maximal 0,809 px |

**Constat : le signal atteint le suivi et la profondeur, mais il n’est pas suffisamment distinct du mouvement prédit par le modèle rigide pour déclencher le critère actuel.** Cela n’établit pas la cause physique exacte et ne prouve pas que le camion est immobile. La compensation, le suivi sur fenêtres chevauchantes et la validité temporelle de la référence restent des limites.

Un contrôle supplémentaire a retiré les 65 points de la boîte de l’estimation de pose, puis évalué ces mêmes points avec la pose obtenue. Leur résidu médian monte à **0,768 px**, le maximum à **1,314 px** ; aucun ne dépasse 3 px. L’influence du camion sur le modèle existe, mais son retrait seul ne suffit pas à faire apparaître un candidat. Ce contrôle utilise une référence publique après coup : ce n’est pas un détecteur autonome ni une preuve de pose caméra correcte. Le reste de l’image n’est pas certifié statique.

## Voir et vérifier

- [Rejeu de l’extrait](../outputs/focused_truck/run_01/clip.gif), ralenti ×5 : chaque pas de 20 ms est affiché pendant 100 ms. Ce n’est pas une démonstration de calcul temps réel.
- [Image du diagnostic](../outputs/focused_truck/run_01/diagnostic.png).
- [Valeurs par date et provenance](../outputs/focused_truck/run_01/summary.json), [contrôle de l’influence sur la pose](../outputs/focused_truck/run_01/camera_influence.json).
- La dernière paire reproduit exactement les tableaux et résultats M17, hors temps de calcul ; sources algorithmiques et fichiers d’entrée contrôlés par hash. Le code applicatif est inchangé.

Pour reproduire le rejeu depuis la racine dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe outputs/focused_truck/run_diagnostic.py --output outputs/focused_truck/run_02
```

## Suite réalisée : regarder sur 100 ms

Le même extrait a été comparé sur **20 ms et 100 ms**, sans nouveau modèle et sans modifier les seuils. Les images restent des accumulations de 50 ms. Les deux suivis partent du même instant, 100 ms avant la référence ; leurs arrivées sont respectivement 80 ms avant la référence et à la référence. La même profondeur au départ est utilisée pour les deux.

Sur les 400 points de départ déjà suivis à 20 ms, 369 passent aussi le contrôle aller-retour à 100 ms. Ces **369 mêmes identifiants** servent aux deux estimations de pose. Après les estimations, la boîte finale sélectionne 73 points, dont 60 avec profondeur exploitable et 13 inconnus. Les valeurs ci-dessous portent sur ce même groupe ; la boîte n'est pas utilisée pour choisir les points du modèle caméra. La sélection finale est rétrospective et ne constitue pas une détection causale d'objet.

| Mesure dans ce groupe | 20 ms | 100 ms |
|---|---:|---:|
| Déplacement observé médian, 73 points | 1,077 px | 5,851 px |
| Résidu médian après compensation, 60 points | 0,347 px | 2,637 px |
| Résidu maximal | 0,649 px | 6,858 px |
| Points dépassant 3 px | 0 | 24 |
| Résidu médian divisé par la durée | 17,4 px/s | 26,4 px/s |
| Erreur aller-retour LK médiane, 73 points | 0,009 px | 0,031 px |

**Le signal est plus visible sur 100 ms.** Cela justifie d'en examiner la continuité ; cela ne valide pas encore le mouvement propre du camion. Hors de ce groupe, cinq autres points dépassent 3 px à 100 ms : ils ne sont pas des fausses alertes certifiées.

Le seuil fixe de 3 px correspond à 150 px/s sur 20 ms, mais 30 px/s sur 100 ms. En conservant le seuil de 150 px/s, aucun point du groupe ne le dépasse dans les deux cas. On ne peut donc pas conclure à une amélioration de qualité sur la seule apparition de 24 candidats. Les images se chevauchent de 30 ms dans le cas court et ne se chevauchent plus dans le cas long. Les erreurs de suivi, de profondeur et de pose restent possibles ; le contrôle aller-retour ne mesure pas toute cette incertitude. Les 31 points perdus à 100 ms sont exclus des deux estimations comparées, ce qui introduit une sélection des points qui restent suivables.

[Voir la comparaison](../outputs/focused_truck/interval_01/comparison.png) · [Données et modèles](../outputs/focused_truck/interval_01/summary.json) · [Vérification](../outputs/focused_truck/interval_01/verification.json).

Contrôles effectués : reproduction du suivi court à 0,0001 px près, conservation des identifiants et de la date de profondeur, résidus recalculés par reprojection, empreintes des entrées/sources et deux cas de suivi synthétiques contrôlés. Le code applicatif et les résultats précédents sont inchangés. La comparaison se reproduit dans un dossier neuf avec :

```powershell
.\.venv\Scripts\python.exe outputs/focused_truck/compare_intervals.py --output outputs/focused_truck/interval_02
```

## Action envisagée après reprise — en pause

Le rejeu glissant et un essai de répartition spatiale des points sont réalisés. Ce dernier ne résout pas la stabilité de la pose ; la référence actuelle est conservée. Les fluctuations observées ne justifient pas de déclarer un objet mobile dès qu'un point dépasse 3 px.

**La répartition du support explique mieux la bascule 2 → 3** : sur les mêmes points, T3 gagne 48 points de support, surtout à gauche, et en perd 45, surtout à droite. Son gain global de trois points masque donc une redistribution importante. Le lecteur actuel conserve les mesures de sensibilité par date. Après reprise demandée par l'utilisateur, l'action envisagée reste d'examiner séparément l'effet de la variation de rotation et de translation sur ces mêmes points, comme contrôle numérique pour comprendre ce transfert, sans estimer une nouvelle pose ni remplacer les prédictions. Cette action n'a pas été exécutée pendant l'audit. Aucun nouveau modèle, corpus, entraînement ou réglage de variante ; la mobilité reste non confirmée.

## Dernier résultat : rejeu glissant de 100 ms

**17 paires exécutées**, une sortie toutes les 20 ms, de −320 ms à la date annotée. Les images de 50 ms, la profondeur à chaque début de paire et les paramètres du modèle sont conservés. Les images/profondeurs déjà calculées sont réutilisées : ce rejeu ne mesure pas une vitesse de traitement de bout en bout.

| Observation | Résultat |
|---|---|
| Modèle rigide disponible | 17 dates sur 17 |
| Dates avec candidats dans la zone fixe | 17 sur 17, soit 320 ms entre première et dernière sortie |
| Nombre de candidats dans la zone | 5 à 27 par date |
| Nombre de candidats hors zone | 3 à 47 par date |

La présence de candidats dans la zone est récurrente, mais **leur localisation fluctue**. Par exemple, à −280 ms : 9 candidats dans la zone et 47 ailleurs ; à −140 ms : 24 dans la zone et 3 ailleurs. Les points compatibles avec la pose à moins de 1,5 px passent de 68/81 points évalués dans la zone à 13/64. Cela suggère une variation du compromis choisi par l'estimation de pose, sans établir une pose caméra exacte ni certifier le fond immobile. Ce problème doit être traité avant de qualifier la détection de stable.

Les points sont redétectés pour chaque paire : **ces 17 présences ne prouvent pas le maintien des mêmes points ni de la même identité d'objet**. Les paires se recouvrent temporellement et ne sont pas 17 observations indépendantes. La zone reste un rectangle d'inspection, avec une référence publique vérifiée seulement à la dernière date. Le seuil de 3 px reste différent en vitesse apparente selon l'intervalle, comme expliqué plus haut.

[Voir le rejeu 100 ms](../outputs/focused_truck/sliding_01/clip.gif) · [Comparer deux localisations](../outputs/focused_truck/sliding_01/localization_check.png) · [Résultats par date](../outputs/focused_truck/sliding_01/summary.json) · [Vérifications](../outputs/focused_truck/sliding_01/verification.json).

Les résidus des 17 paires ont été recalculés à partir des poses et profondeurs ; dates, identifiants, compteurs, empreintes et GIF vérifiés. La dernière paire reproduit exactement la comparaison 100 ms précédente. Aucun changement du code applicatif. Reproduction dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe outputs/focused_truck/replay_100ms.py --output outputs/focused_truck/sliding_02
```

## Essai terminé : répartir les points utilisés pour la pose

Une seule variante a été évaluée sur les mêmes 17 paires : grille fixe de 8 × 6 cases, au plus quatre points par case, choisis selon leur erreur de suivi aller-retour. La pose utilise ce sous-ensemble ; tous les points avec profondeur sont ensuite évalués. La boîte du camion ne participe pas à l'estimation. Les paramètres géométriques restent inchangés.

La variation médiane entre translations de deux poses successives passe de **0,162 m à 0,045 m**, mais le maximum reste voisin de **0,338 m**. Ces écarts comparent des estimations sur des intervalles glissants de 100 ms ; ce ne sont ni une erreur mesurée contre une pose vraie, ni une accélération physique. Les candidats continuent de fluctuer : 5 à 34 dans la zone, 4 à 47 ailleurs.

**Décision technique : ne pas activer cette variante par défaut.** Le résultat est partiel et ne démontre pas une meilleure séparation des mouvements. Le module expérimental et les résultats sont conservés ; aucune nouvelle série de réglages n'est engagée.

[Résultats de l'essai](../outputs/focused_truck/balanced_01/summary.json) · [Module optionnel](../src/pfe_events/balanced_pose.py). Vérification du projet réussie : 188 tests, 92 fichiers Python et 28 aides CLI. L'essai a été lancé par une commande Python ponctuelle ; les entrées et sources sont identifiées par empreintes dans le résultat.

## Première intégration : YOLO, profondeur et mouvement dans un affichage

Le modèle **Y01 pilote existant** est exécuté sur les 17 dates du même extrait `zurich_city_04_b`. Images événementielles de 50 ms et normalisation S01 conservées ; aucun entraînement ajouté. La stéréo S01 est recalculée à la date de chaque détection. Les boîtes natives sont associées aux pixels rectifiés pour obtenir un point de surface XYZ, avec abstention si le support est insuffisant. La zone publique du camion n'entre pas dans cette association.

| Résultat sur les 17 images | Valeur |
|---|---:|
| Détections cumulées, seuil YOLO 0,25 | 77 |
| Détections avec une estimation de surface XYZ | 45 |
| Détections sans XYZ, support insuffisant | 32 |

Ces nombres comptent des détections image par image, **pas 77 objets distincts**. Les numéros affichés recommencent à chaque image. À la dernière date, deux détections de personnes ont une profondeur estimée de 13,12 m et 12,87 m ; une troisième de faible confiance reçoit 43,30 m. La voiture détectée à gauche reste sans XYZ. Ces valeurs sont des estimations, sans référence de profondeur objet pour mesurer leur erreur ; une ROI peut contenir le fond. Le camion n'est pas reconnu par le modèle à deux classes `person`/`car`, tandis que des résidus apparaissent dans sa zone.

L'affichage garde **« mouvement propre non confirmé »**. Les comptes de points résiduels dans chaque boîte fournissent un indice local et ne prouvent pas la mobilité de l'objet. Dans cette première version `integrated_02`, les mouvements proviennent du rejeu `sliding_01`, à la même date d'arrivée, et sont relus ; YOLO et la stéréo sont calculés à nouveau. Cette version historique est une **intégration hors ligne avec mouvement précalculé**, remplacée par le calcul complet décrit ci-dessous. Le clip est ralenti ×5.

- [Voir la démonstration](../outputs/focused_truck/integrated_02/clip.gif) et [l'image finale](../outputs/focused_truck/integrated_02/preview.png).
- [Résultats détaillés](../outputs/focused_truck/integrated_02/summary.json) et [contrôles](../outputs/focused_truck/integrated_02/verification.json).
- 197 tests passent ; les 45 XYZ sont recalculés indépendamment, les dates sont vérifiées et l'image native finale reproduit exactement l'export Y00. Le second rendu conserve les mêmes résultats numériques que le premier.

Exécution dans l'environnement CPU isolé `.venv-demo` (Ultralytics 8.4.172, torch 2.14.1+cpu ; l'ancien environnement `.venv` est conservé) :

```powershell
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --output outputs/focused_truck/integrated_04
```

Pour recréer cet environnement : `python -m venv --without-pip .venv-demo`, puis `.\.venv\Scripts\python.exe -m pip --python .venv-demo\Scripts\python.exe install -r requirements-demo-lock.txt`. Le verrou des versions est dans [requirements-demo-lock.txt](../requirements-demo-lock.txt). Le script de synchronisation Markdown exclut cet environnement. Les archives `integrated_01` (premier rendu) et les expériences précédentes restent conservées.

## Résultat actuel : calcul complet et coût mesuré

`integrated_03` recalcule **YOLO, stéréo actuelle, XYZ et mouvement depuis les événements bruts**, sans lire les anciennes prédictions. La méthode de mouvement est inchangée : profondeur à `t−100 ms`, points présélectionnés par suivi jusqu'à `t−80 ms`, puis suivi direct jusqu'à `t`. Les images restent des accumulations de 50 ms. Cette sélection requiert 150 ms d'historique ; elle n'utilise pas d'événements postérieurs à la date de sortie.

Les 17 poses et tableaux de suivi reproduisent **exactement** `sliding_01`. Les détections, coordonnées XYZ et disparités actuelles reproduisent exactement `integrated_02` : toujours 77 détections cumulées, 45 surfaces estimées et 32 abstentions. L'intégration ne change donc pas la qualité observée ni les limites de mobilité.

| Mesure CPU, une exécution sur 17 sorties | Résultat |
|---|---:|
| Calcul complet médian, hors rendu/export | 1 049,5 ms |
| Médiane après la première sortie | 1 031,5 ms |
| Première sortie, premier appel YOLO compris | 3 766,0 ms |
| Calcul cumulé des 17 sorties | 21,20 s |
| Sorties dépassant le budget de 20 ms | 17 / 17 |

Les médianes par étape sont : lecture/représentation actuelle 298,9 ms ; YOLO 40,5 ms ; stéréo actuelle 132,9 ms ; branche mouvement 557,7 ms ; association 10,3 ms. La branche mouvement comprend ses propres lectures, représentations historiques, stéréo précédente, suivi et pose. **Les médianes par étape ne s'additionnent pas pour obtenir la médiane totale.**

Cette exécution séquentielle CPU est hors ligne : environ 0,80 sortie/s en moyenne, premier appel compris, en ne comptant que le calcul. Le programme entier prend 27,98 s avant l'écriture du résumé final, initialisation, empreintes et exports compris. OpenCV et PyTorch utilisent chacun un thread de calcul ; les caches HDF5/système sont actifs. Ce petit extrait et cette exécution unique ne constituent pas un benchmark général, un délai de détection de début de mouvement ou une cadence temps réel. Aucune optimisation supplémentaire engagée.

- [Voir la démonstration recalculée](../outputs/focused_truck/integrated_03/clip.gif) · [Image finale](../outputs/focused_truck/integrated_03/preview.png).
- [Résultats et temps par sortie](../outputs/focused_truck/integrated_03/summary.json) · [Vérifications](../outputs/focused_truck/integrated_03/verification.json).
- 201 tests passent, 97 fichiers Python et 29 aides CLI contrôlés. Les dates causales, l'identité numérique avec les anciens résultats, l'addition des temps par étape, les empreintes et les 17 images du GIF sont vérifiées. Les sources de cette exécution sont conservées dans son dossier ; l'ancien script avec mouvement précalculé est sauvegardé dans `integrated_02/sources/`.

## Lecteur d'inspection disponible

Ouvrir [le lecteur HTML autonome](../outputs/focused_truck/viewer_01/index.html) dans un navigateur. Les 17 dates et leurs images sont intégrées dans ce fichier d'environ 8 Mo ; aucun serveur, framework DL ou accès réseau n'est nécessaire pour le consulter. Il relit uniquement `integrated_03`, sans exécuter le modèle ni enregistrer d'annotations.

- **Lire/pause, précédent/suivant, début/fin et curseur temporel.** Lecture au ralenti ×5, ×12,5 ou ×25 ; la lecture ne mesure pas la vitesse du pipeline.
- **Cliquer une boîte ou une ligne du tableau** affiche le score YOLO, les XYZ disponibles, le support de profondeur et les comptes de points. Les points associés sont mis en évidence dans l'image rectifiée. La sélection est effacée à chaque changement d'image : les numéros ne sont pas des identités persistantes.
- **Cliquer un point à droite** affiche son déplacement observé, le déplacement prédit par le modèle, le résidu et la profondeur au départ. Les flèches sont à leur échelle réelle : blanc pour le suivi, bleu pour le modèle, orange pour le résidu ; leur origine appartient à l'image précédente.
- Cases pour afficher les boîtes, les points ou uniquement les candidats résiduels. La mention « mouvement propre non confirmé » reste visible.

Le navigateur a permis de vérifier lecture/pause, navigation, raccourci flèche, inspection avec/sans XYZ, clic sur un point et filtre résiduel, sans erreur JavaScript observée. Les 34 images intégrées sont identiques aux tableaux sources et les comptes associés aux boîtes sont vérifiés. Les contrôles du projet passent : 201 tests, 98 fichiers Python, 30 aides CLI. [Vérifications](../outputs/focused_truck/viewer_01/verification.json) · [Aperçu](../outputs/focused_truck/viewer_01/preview.jpg).

Pour reconstruire le lecteur dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe scripts/build_inspection_viewer.py --output outputs/focused_truck/viewer_05 --sensitivity outputs/focused_truck/pose_switch_01 --clip-sensitivity outputs/focused_truck/clip_sensitivity_01
```

## Ce que montrent trois points inspectés

[Comparaison illustrée](../outputs/focused_truck/inspection_01/comparison.png) · [Coordonnées et calculs](../outputs/focused_truck/inspection_01/examples.json). Les numéros ci-dessous correspondent aux **points du lecteur**, pas aux détections YOLO. Les exemples sont choisis après observation, à des positions différentes ; ils ne suivent pas une même identité entre les dates.

| Exemple visuel | Image / point | Déplacement observé | Déplacement prédit | Résidu |
|---|---|---:|---:|---:|
| Zone basse du camion, compatible avec le modèle | 3 / 11 | 7,14 px | 7,63 px | 0,54 px |
| Zone de façade, candidat résiduel | 3 / 158 | 7,37 px | 5,41 px | 3,85 px |
| Zone basse du camion, candidat résiduel | 10 / 14 | 4,70 px | 2,45 px | 4,12 px |

Un grand déplacement dans l'image peut être bien expliqué par le modèle : le premier point ne dépasse pas le seuil de 3 px. Le deuxième dépasse ce seuil dans une zone visuellement associée au décor. Le troisième dépasse le seuil dans la zone du camion. **La couleur orange désigne donc une incompatibilité avec le modèle, pas une preuve de mouvement propre.**

Le résidu vaut `norme(position_observée − position_prédite)`. Il tient compte des directions : il ne vaut pas simplement la différence des longueurs affichées. Par exemple, les 7,37 et 5,41 px du deuxième cas donnent un résidu de 3,85 px, et non 1,96 px.

Ces cas illustrent pourquoi le détecteur peut manquer un objet ou produire un candidat sur le décor. Ils ne permettent pas de départager quantitativement une erreur de pose, de profondeur, de correspondance ou un mouvement réel. La variation du compromis de pose observée auparavant reste une explication possible. Aucun fond n'est certifié statique, aucune précision/rappel n'est déduite de ces trois exemples. La visualisation de zones conserve donc cette incertitude.

Les trois résidus et leurs statuts ont été recalculés à partir des positions enregistrées ; ils reproduisent les valeurs sources. Les empreintes des entrées et du script de figure sont conservées. Aucun code d'inférence, réglage ni résultat antérieur n'a changé ; aucun entraînement ou annotation ajouté.

## Zones candidates ajoutées au lecteur

[Lecteur historique des zones](../outputs/focused_truck/viewer_02/index.html) · [Zones par date](../outputs/focused_truck/viewer_02/regions.json) · [Vérifications](../outputs/focused_truck/viewer_02/verification.json).

Les points dont le résidu dépasse strictement 3 px sont regroupés dans l'image rectifiée, sans utiliser les boîtes YOLO pour créer les zones. Le principe et les réglages spatiaux de M03 sont repris : cellules de 32 px, dilatation 3 × 3, connexité à 8 voisins, au moins trois points et marge de 8 px autour des points. Le modèle de mouvement reste le modèle rigide actuel ; le modèle apparent 2D de M03 n'est pas réactivé. Si le modèle est indisponible, aucune zone n'est proposée.

Sur les 17 images : **22 occurrences de zones**, avec une ou deux zones par image. **12 occurrences n'ont aucun point partagé avec les boîtes YOLO.** Cela montre que le regroupement fonctionne aussi hors du support des détections sémantiques ; cela ne mesure ni 22 objets distincts ni 12 objets manqués par YOLO. À la dernière date, la zone est `[95, 117, 281, 305]` dans l'image rectifiée et contient 29 points ; elle recouvre la région d'inspection du camion sans point partagé avec YOLO.

La case « Zones candidates » commande les cadres orange. Les boutons Z1/Z2 permettent d'examiner leurs points, le résidu médian et maximal, leurs coordonnées et les éventuels points communs avec YOLO. Les numéros recommencent à chaque image ; aucune association temporelle n'est ajoutée.

**Limite importante : le regroupement peut fusionner plusieurs surfaces.** Une chaîne de cellules proches peut produire un grand cadre contenant à la fois un objet et du décor. À la troisième image, une zone de 46 points s'étend sur `[159, 16, 570, 279]` et partage des points avec deux détections YOLO. Un cadre n'est donc ni une segmentation d'objet ni une preuve de mouvement indépendant.

Les données historiques du lecteur sont inchangées : mêmes suivis, images, détections, XYZ et temps enregistrés. Le regroupement est un post-traitement des résidus sauvegardés ; aucun entraînement ni calcul complet relancé. Les temps de `integrated_03` n'incluent pas ce nouveau post-traitement.

Vérifications : 207 tests passent, 100 fichiers Python et 30 aides CLI contrôlés. Les 34 images intégrées, 39 empreintes sources, les membres des zones, les cadres, statistiques et points communs avec YOLO ont été vérifiés ; la syntaxe JavaScript passe aussi. **Le rendu interactif de `viewer_02` n'a pas été vérifié dans le navigateur** : sa politique bloque les URL de fichiers locaux. Les contrôles navigateur de `viewer_01` restent historiques et ne valent pas validation de cette nouvelle interface.

## Stabilité spatiale : présence répétée, localisation variable

[Comparaison visuelle et tableau des 17 dates](../outputs/focused_truck/stability_01/comparison.png) · [Mesures détaillées](../outputs/focused_truck/stability_01/summary.json) · [Vérifications](../outputs/focused_truck/stability_01/verification.json).

Le diagnostic compare les 16 transitions entre images consécutives, espacées de 20 ms. Il mesure le recouvrement de **l'union des cadres** par l'IoU : aire de l'intersection divisée par celle de l'union. Il compare aussi les cellules de 32 px occupées par les points regroupés, sans dilatation. Aucune identité n'est associée entre dates ; les numéros Z1/Z2 ne servent pas à apparier des objets.

| Mesure descriptive | Minimum | Médiane | Maximum |
|---|---:|---:|---:|
| IoU des emprises des cadres entre dates | 0,034 | 0,425 | 0,951 |
| IoU des cellules occupées entre dates | 0,027 | 0,372 | 0,850 |
| Surface totale des cadres, en % de l'image | 8,5 % | 21,0 % | 44,7 % |

La transition **image 7 → image 8**, de −200 à −180 ms, présente le plus faible recouvrement des cadres : **3,4 %**, et 3,1 % pour les cellules. La figure montre une zone autour de la région du camion, puis deux zones dont une grande à droite. La dernière image retrouve une zone autour de la région du camion. Cela décrit une redistribution des propositions dans l'image ; ce n'est pas une mesure du déplacement physique du camion.

Les grands cadres peuvent masquer une redistribution des points : entre les images 2 et 3, leur IoU vaut environ 0,33, contre seulement 0,06 pour les cellules occupées. Les cadres remplis ne sont pas des masques d'objet. La grille dépend également de ses frontières et ne comprend que les points retenus dans des zones d'au moins trois points.

**Décision : conserver le statut « zone candidate » et ne pas ajouter de confirmation de mobilité fondée uniquement sur sa répétition.** Le diagnostic quantifie une variabilité de localisation déjà visible. Il ne sépare pas encore les effets de la pose, de la profondeur, du suivi et du mouvement réel. Les comparaisons se font dans les coordonnées de l'image, sans compensation entre dates ; les fenêtres de 50 ms et les paires de 100 ms se recouvrent. Ces observations ne sont donc ni indépendantes, ni une évaluation de précision/rappel.

Les 17 surfaces et les 16 IoU des cadres sont vérifiées indépendamment par partition géométrique des rectangles, sans utiliser les masques raster du calcul initial. Les empreintes des 20 entrées, du script et de la figure sont contrôlées ; la figure a été inspectée visuellement. Aucun code d'inférence ni résultat historique modifié. Le contrôle précédent à 207 tests reste inchangé ; cette étape a fait l'objet de vérifications spécifiques aux nouveaux calculs.

Reproduction dans un dossier neuf, avec l'environnement existant :

```powershell
.\.venv\Scripts\python.exe outputs/focused_truck/analyze_region_stability.py --output outputs/focused_truck/stability_02
```

## Bascule 7 → 8 : forte sensibilité au modèle rigide

[Comparaison illustrée](../outputs/focused_truck/pose_switch_01/comparison.png) · [Calculs détaillés](../outputs/focused_truck/pose_switch_01/summary.json) · [Vérifications](../outputs/focused_truck/pose_switch_01/verification.json).

Le contrôle garde **tous les points, déplacements observés et profondeurs de l'image 8**, puis remplace uniquement sa transformation T8 par la transformation T7 enregistrée à l'image précédente. Les deux transformations décrivent des intervalles de 100 ms décalés de 20 ms. Réutiliser T7 est une hypothèse numérique de sensibilité, pas une pose caméra validée sur le nouvel intervalle. Aucun appariement des identités entre images ni nouvel ajustement de pose n'est effectué.

| Résultat | Image 7, T7 originale | Image 8, T8 originale | Image 8, hypothèse T7 |
|---|---:|---:|---:|
| Points évalués avec profondeur | 263 | 255 | 255 |
| Candidats, résidu > 3 px | 30 | 47 | 26 |
| Candidats dans la moitié gauche | 28 | 8 | 24 |
| Candidats dans la moitié droite | 2 | 39 | 2 |
| Support, résidu ≤ 1,5 px | 183 | 194 | 176 |

Les moitiés sont définies par `x < 320` et `x ≥ 320` dans l'image rectifiée ; ce ne sont pas des labels objet/fond. Les candidats isolés sont comptés même s'ils ne forment pas de zone : les 30 et 47 candidats originaux diffèrent donc des 28 et 45 points regroupés dans les cadres.

Sur les **mêmes 255 points** de l'image 8, 67 changent de statut au seuil de 3 px : en passant de T8 à T7, 44 candidats deviennent compatibles avec le modèle et 23 compatibles deviennent candidats. Trois points restent candidats dans les deux cas. Ce contrôle montre qu'une variation de transformation suffit à redistribuer les alertes, même sans modifier le suivi ou la profondeur de cette image.

T8 possède davantage de support à 1,5 px sur l'image 8 (194 contre 176 pour l'hypothèse T7), alors que T7 donne moins de candidats à 3 px (26 contre 47). Ces deux seuils mesurent des aspects différents de la distribution des résidus. **Choisir le modèle ayant le plus de support, ou le moins de candidats, ne prouve pas une meilleure séparation objet/caméra.**

Les paramètres de translation estimés diffèrent d'une norme de 0,337 m, et les rotations de 0,219°. Ces valeurs comparent deux transformations sur des intervalles décalés ; elles ne sont ni une erreur de pose mesurée, ni une vitesse ou accélération physique. Les médianes de cohérence aller-retour du suivi sont proches (0,0318 px puis 0,0308 px parmi les points évalués), mais cette cohérence ne garantit pas des correspondances exactes. La profondeur médiane identique ne démontre pas non plus une profondeur correcte : les points sont redétectés et les ensembles diffèrent.

**Décision : ne pas remplacer T8 par T7 et ne pas introduire de lissage à ce stade.** Le contrôle établit une sensibilité au modèle ; il n'explique pas encore pourquoi les estimations divergent, ni quelle transformation correspond à la caméra réelle. Les résultats YOLO, stéréo, XYZ et mouvement de `integrated_03` restent inchangés.

Vérifications : les projections et résidus originaux des images 7 et 8 sont reproduits à partir de leurs profondeurs et transformations ; les zones originales sont également reproduites. Une seconde projection avec `cv2.projectPoints` vérifie les trois cas, avec un écart maximal de coordonnées inférieur à `1,3 × 10⁻¹¹ px`. Les 67 changements de statut, les sept empreintes d'entrée, le script et les artefacts sont contrôlés ; la figure a été inspectée. Ces vérifications numériques ne constituent pas une validation de mobilité contre une vérité terrain. Aucun code d'inférence modifié ; la suite générale à 207 tests n'a pas été relancée pour ce diagnostic isolé.

Reproduction dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe outputs/focused_truck/analyze_pose_switch.py --output outputs/focused_truck/pose_switch_02
```

## Comparaison de poses intégrée au lecteur

**[Lecteur de la première comparaison de poses](../outputs/focused_truck/viewer_03/index.html)** : cliquer sur **« Comparer les poses · image 8 »**. Le lecteur se met en pause et affiche deux vues de la même image rectifiée : T8 enregistrée à gauche, hypothèse T7 à droite. Un avertissement rappelle que le contrôle ne désigne pas la bonne pose et ne confirme pas de mobilité. Cette fonction est conservée dans le lecteur actuel, indiqué en fin de page.

- Les vues montrent 47 candidats avec T8, contre 26 avec l'hypothèse T7, sur les mêmes 255 points évalués.
- La case « Afficher uniquement les points qui changent de statut » isole les 67 points concernés. Les cadres restent ceux de l'ensemble des candidats de chaque cas.
- Un clic sur un point dans l'une des vues sélectionne ce même point dans les deux vues et affiche ses deux résidus et statuts. Les boutons « Premier point modifié » et « Point modifié suivant » permettent aussi une inspection sans clic précis.
- Le panneau est réservé à l'image 8 et se masque lorsqu'on change de date. La sélection est réinitialisée à chaque changement d'image. Les vues principales, les boîtes YOLO, les XYZ et les zones enregistrées conservent leurs valeurs originales.

La comparaison est intégrée au fichier HTML autonome : aucune lecture de fichier supplémentaire ni inférence dans le navigateur. Le constructeur accepte le diagnostic via l'option facultative `--sensitivity`. Il vérifie les empreintes, la correspondance des dates, les prédictions originales et les comptes ; un diagnostic associé à une autre source ou à des prédictions différentes est rejeté. Sans cette option, le lecteur reste utilisable sans panneau de comparaison.

Vérifications : **207 tests, 100 fichiers Python et 30 aides CLI** passent. Les 17 résultats et les 34 images intégrées sont identiques à `viewer_02`, de même que les zones originales ; 41 empreintes sources sont vérifiées. Les données incompatibles sont refusées. Les interactions sont testées avec un DOM/canvas simulé : accès direct, navigation, filtre à 67 points, sélection commune, effacement, pause et absence de diagnostic. **Ce contrôle ne vérifie pas le rendu réel dans un navigateur**, dont l'accès automatisé aux fichiers locaux avait été bloqué ; cette limite reste explicite.

[Vérifications des données](../outputs/focused_truck/viewer_03/verification.json) · [Vérifications des interactions](../outputs/focused_truck/viewer_03/interaction-checks.json). Les anciennes versions sont conservées.

## Sensibilité sur tout l'extrait : la bascule n'est pas isolée

[Tableau illustré des 16 transitions](../outputs/focused_truck/clip_sensitivity_01/comparison.png) · [Mesures et provenance](../outputs/focused_truck/clip_sensitivity_01/summary.json) · [Vérifications](../outputs/focused_truck/clip_sensitivity_01/verification.json).

Le même contrôle est appliqué aux images 2 à 17 : conserver leurs points, déplacements et profondeurs, puis remplacer uniquement leur transformation par celle de l'image précédente. La première image n'a pas de comparaison faute de pose précédente dans cet extrait. Le seuil résiduel reste strictement supérieur à 3 px. Il n'y a ni nouvel ajustement de pose, ni suivi d'identité entre les dates.

| Observation sur les 16 transitions | Résultat |
|---|---:|
| Huit transitions avec davantage de changements | 26,3 à 30,7 % des points évalués |
| Huit autres transitions | 0,4 à 5,4 % |
| Plus grand pourcentage : 2 → 3 | 81 / 264 points, soit 30,68 % |
| Cas déjà étudié : 7 → 8 | 67 / 255 points, soit 26,27 %, huitième rang décroissant |
| Changement de disponibilité de projection entre les deux poses | 0 point sur les 16 comparaisons |

Les deux plages sont une **description après observation** : elles sont séparées par le plus grand écart entre pourcentages triés. Aucun seuil opérationnel n'en est déduit. Les huit transitions de la plage supérieure sont 2 → 3, 3 → 4, 7 → 8, 9 → 10, 10 → 11, 11 → 12, 14 → 15 et 16 → 17. La médiane des 16 pourcentages vaut 15,85 % ; elle tombe entre les plages observées et ne décrit donc pas un cas typique de cet extrait.

Les sommes donnent 613 changements sur 4 132 occurrences de points évalués. Les points sont redétectés et les intervalles se recouvrent : **ce ne sont pas 4 132 points distincts, ni 613 erreurs de détection**. À chaque date, le dénominateur est l'ensemble des points projetables sous les deux transformations ; ici, cet ensemble est identique dans les deux cas. Le taux de changement ne dissimule donc pas un changement de disponibilité des projections sur cet extrait.

**Décision : rendre la sensibilité visible sans choisir arbitrairement une « bonne » pose.** Le phénomène est récurrent sur ce petit extrait. Une faible sensibilité n'établit pas davantage une pose correcte : deux transformations proches peuvent partager un même biais. Réutiliser une transformation correspondant à un intervalle de 100 ms décalé de 20 ms reste une hypothèse numérique. Ce contrôle ne mesure ni précision/rappel de mobilité, ni erreur de pose caméra, ni généralisation à d'autres scènes.

Vérifications : les projections originales des 17 images sont reproduites ; les 16 hypothèses sont vérifiées indépendamment par `cv2.projectPoints` avec une rétroprojection par l'inverse de la matrice intrinsèque. L'écart maximal de coordonnées est inférieur à `3,9 × 10⁻¹¹ px`. Les effectifs, masques et indices des points modifiés sont contrôlés ; le cas 7 → 8 reproduit exactement ses tableaux précédents. Les 42 empreintes d'entrées et de sources sont vérifiées, et le tableau illustré est inspecté. Aucun code applicatif, lecteur ou résultat d'inférence n'a été modifié ; les 207 tests de la dernière étape restent le dernier contrôle général, sans relance inutile pour ce diagnostic isolé.

Reproduction dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe outputs/focused_truck/analyze_clip_sensitivity.py --output outputs/focused_truck/clip_sensitivity_02
```

## Sensibilité par date affichée dans le lecteur

**[Ouvrir le lecteur actuel](../outputs/focused_truck/viewer_04/index.html)**. Sous la date, le lecteur affiche la part des points dont le statut change si l'on utilise la pose précédente, ainsi que le numérateur et le dénominateur. La mise à jour suit le curseur, la navigation et la lecture. Exemples :

| Image | Affichage de sensibilité |
|---|---|
| 1 | Comparaison indisponible, sans pose précédente dans cet extrait |
| 2 | 1,16 %, soit 3 / 259 points |
| 3 | 30,68 %, soit 81 / 264 points |
| 8 | 26,27 %, soit 67 / 255 points |
| 17 | 27,64 %, soit 68 / 246 points |

Le dénominateur comprend les points évaluables sous les deux poses ; un éventuel changement de disponibilité de projection est affiché séparément. Ici, ce changement est nul à toutes les dates. Une absence de comparaison n'est jamais présentée comme 0 %. Le texte rappelle qu'une faible sensibilité ne garantit pas une pose correcte et que ce pourcentage ne confirme pas de mobilité. Aucun seuil ni code couleur de qualité n'a été ajouté.

L'option facultative `--clip-sensitivity` charge le diagnostic existant. La construction vérifie les empreintes, les dates, l'ordre des images, les masques, les résidus, les effectifs et les pourcentages à partir des tableaux sauvegardés. Le lecteur peut encore être construit sans diagnostic par date ou sans comparaison détaillée de l'image 8. Ces deux ajouts restent indépendants.

Les 17 prédictions, 34 images intégrées, zones candidates, résultats YOLO/XYZ et comparaison détaillée de l'image 8 sont identiques à `viewer_03`. Aucun calcul d'inférence relancé ; aucun artefact historique remplacé.

Vérifications : **207 tests, 100 fichiers Python, 30 aides CLI** passent. Les 43 empreintes sources et les 16 mesures affichées sont contrôlées. Des données à date, ordre, effectif, pourcentage ou source incompatibles sont rejetées. Le test JavaScript avec DOM/canvas simulé parcourt les 17 images, vérifie les effectifs et pourcentages, l'absence initiale de comparaison, le cas sans support commun, les diagnostics facultatifs et les interactions historiques. **Le rendu réel dans un navigateur reste non vérifié** ; ces tests de logique ne sont pas une validation visuelle.

[Vérifications des données](../outputs/focused_truck/viewer_04/verification.json) · [Vérifications des interactions](../outputs/focused_truck/viewer_04/interaction-checks.json).

## Support de pose 2 → 3 : un petit gain global masque une redistribution

[Carte du support sur l'image 3](../outputs/focused_truck/pose_support_01/comparison.png) · [Effectifs, indices et profondeurs](../outputs/focused_truck/pose_support_01/summary.json) · [Vérifications](../outputs/focused_truck/pose_support_01/verification.json).

Le contrôle utilise les mêmes 264 points évaluables de l'image 3 et compare T3 enregistrée à l'hypothèse T2 précédente. Les 99 autres points restent inconnus. Le **support final** désigne ici les points dont le résidu est inférieur ou égal à **1,5 px**, après ajustement ; ce n'est pas la liste initiale des points sélectionnés par RANSAC. Le seuil de candidat mobile potentiel reste distinct, à **plus de 3 px**.

| Ensemble de support sur l'image 3 | Total | Moitié gauche | Moitié droite | Profondeur médiane estimée au départ |
|---|---:|---:|---:|---:|
| Commun à T2 et T3 | 147 | 37 | 110 | 49,16 m |
| T2 seulement, perdu avec T3 | 45 | 5 | 40 | 15,28 m |
| T3 seulement, gagné avec T3 | 48 | 47 | 1 | 10,87 m |
| Aucune des deux à 1,5 px | 24 | 17 | 7 | 14,21 m |

T2 soutient **192 points**, T3 **195** : le gain net n'est que de trois points, alors que **93 points changent d'appartenance au support**. Le recouvrement des ensembles de support, intersection sur union, vaut 0,6125. Les 93 changements au seuil de 1,5 px ne sont pas les 81 changements de statut candidat mesurés au seuil de 3 px.

La carte place les points propres à T3 surtout à gauche, autour de la région du camion visible, et ceux propres à T2 surtout à droite. Cette lecture visuelle ne crée pas de labels de mobilité. Les moitiés utilisent `x < 320` et `x ≥ 320` dans l'image rectifiée actuelle ; aucune boîte de référence ni annotation manuelle n'est utilisée pour classer les points. Les profondeurs sont les estimations stéréo à `t−100 ms`, avec leurs erreurs possibles.

**Interprétation limitée : le comptage global du support masque un changement des surfaces expliquées.** Un ensemble commun, à profondeur médiane estimée plus grande, reste compatible avec les deux transformations, tandis que d'autres groupes entrent ou sortent du support. Cela n'établit ni une caméra correcte, ni un camion immobile ou mobile, ni la cause exacte du changement de pose. Réutiliser T2 sur l'image 3 reste une hypothèse sur un intervalle de 100 ms décalé de 20 ms.

**Décision : conserver les poses et poursuivre l'explication géométrique, sans choisir automatiquement celle qui a le plus de support.** La variante historique d'équilibrage spatial déjà testée reste inchangée et n'est pas relancée. Aucun composant ni réglage ajouté au détecteur.

Vérifications : les ensembles forment une partition exacte des 264 points évalués ; les 195 points de T3 et leur couverture convexe reproduisent le modèle enregistré. Une projection indépendante avec `cv2.projectPoints` reproduit les résidus des deux cas avec un écart inférieur à `1,5 × 10⁻¹¹ px`. Les indices, effectifs, statistiques de profondeur et sept empreintes d'entrées/sources sont vérifiés ; les statistiques conservent la précision des tableaux sources. La figure est inspectée visuellement. Aucun code applicatif ni lecteur modifié ; les 207 tests de la dernière étape restent le dernier contrôle général.

Reproduction dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe outputs/focused_truck/analyze_pose_support.py --output outputs/focused_truck/pose_support_02
```
