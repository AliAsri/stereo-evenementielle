# Progression du PFE

Date de référence : 10 octobre 2026. Notes techniques, pas un texte de mémoire.

## Revue documentaire D01 — 10 octobre 2026

Les deux documents externes de conception et de veille ont été relus et corrigés : références centrales confrontées aux sources primaires, erreurs techniques et contradictions de périmètre traitées, pistes non revalidées identifiées. [Journal et versions corrigées](48_REVIEW_CONCEPTION_BIBLIOGRAPHIE.md). Originaux préservés et sauvegardés avec SHA256 dans `outputs/documentation/D01/`. Cette étape ne lance aucune nouvelle expérience ni entraînement ; les résultats M17 et la prochaine comparaison M18 restent inchangés.

## Terminé

- Cahier des charges fourni lu intégralement.
- Audit récursif du dossier, fichiers cachés compris : dossier initialement vide, aucun dépôt Git ni code existant.
- Environnement observé : Windows/PowerShell, Python 3.14.6, Git et ripgrep disponibles. Environ 44,7 Gio libres sur C: au début de l'audit.
- Recherche ciblée dans les publications et dépôts officiels DSEC, MVSEC, M3ED, EventScape, RVT, SE-CFF, EMatch et EventHub ; fiches bibliographiques avec sources et limites de lecture.
- Identifié le décalage de repère entre annotations DSEC-Detection et disparités DSEC.
- Documentation 00–20, README, architecture Mermaid, décisions et planning de 12–16 semaines créés avec contenu utile ; cahier des charges original conservé.
- Environnement CPU isolé installé et versions verrouillées ; imports vérifiés.
- Échantillon réel `zurich_city_04_e` téléchargé : gauche/droite, calibration, GT et labels ; provenance/hashes conservés.
- Lecteur par fenêtre, rectification d'inspection, comptage, audit calibration et reprojection implémentés.
- Ordre de 119 172 751 événements gauche et 95 364 500 droite vérifié intégralement ; fenêtre causale commune contrôlée.
- Inspection visuelle des vues événementielles et des annotations officielles effectuée.
- Inventaire de classes dans l'archive train des labels produit.
- 13 tests déterministes réussis ; preuves et rapport D00 archivés dans `outputs/reports/`.
- Centralisation demandée par l'utilisateur : copies des fichiers Markdown dans `markdowns/`, chemins relatifs conservés et script de synchronisation avec vérification SHA256. Règle persistante enregistrée dans `AGENTS.md`.

### Étape S01 — 3 octobre 2026

- Ajout de `zurich_city_04_b` et `thun_00_a`, contenant des piétons et voitures ; données originales et provenance conservées.
- Manifeste local par groupe de trajet : `04_e` et `04_b` côté train, `thun_00_a` côté validation, `09_b` réservé et non acquis.
- OpenCV CPU installé et verrouillage des dépendances actualisé.
- Comptage rectifié bilinéaire, trois canaux logarithmiques et normalisation figée sur train implémentés.
- Baseline SGBM avec masque d'activité et contrôle gauche-droite, profondeur prédite via Q et métriques avec couverture implémentés.
- Exécution réelle sur 60 fenêtres ; 723 007 877 timestamps audités dans les six flux.
- 21 tests synthétiques réussis ; 60 fichiers de prédiction relus pour vérifier unités, NaN, profondeur et métriques.
- Figures de référence/prédiction/erreur et exemples de labels produits ; cas d'échec de validation et vue native avec huit piétons inspectés visuellement.
- Rapports JSON/CSV, hashes du code, paramètres, normaliseur et guide S01 conservés. Documentation actualisée et copies dans `markdowns/` synchronisées.

## Étape Y00 terminée — 3 octobre 2026

- Export de 774 PNG événementiels natifs, 4 235 boîtes personne/voiture et partitions train/val par trajet.
- Conservation des timestamps, lignes source, track IDs, exclusions et hashes ; deux exemples négatifs train conservés.
- Paquet Colab de 151,26 Mio créé et vérifié ; normaliseur S01 train-only réutilisé.
- 27 tests réussis ; toutes les boîtes confrontées aux sources ; neuf images régénérées exactement ; vues annotées inspectées.
- Code de chargement Ultralytics 8.4.172 audité pour canaux et augmentations ; framework non installé localement.
- Notebook Colab créé, sept cellules Python compilées, protocole de contrôle puis surapprentissage et cinq époques préparé. GPU non exécuté à cette étape Y00 ; exécuté ensuite dans Y01.

## Étape Y01 terminée ; audit des archives le 4 octobre 2026

Les deux ZIP fournis confirment trois essais : diagnostic initial échoué, diagnostic corrigé réussi, pilote complet de cinq époques terminé. 113 fichiers utiles sont importés (environ 56 Mio), les archives et 155 checkpoints intermédiaires restent conservés à leur emplacement d'origine. Neuf comparaisons de provenance/checkpoints réussissent ; les CSV et figures sont examinés. [Analyse Y01](24_Y01_COLAB_RESULTS.md).

- Contrôle runtime des tenseurs réussi ; neuf boîtes train filtrées par le framework sont comptées.
- Diagnostic corrigé : AP50 99,5 % par classe, 200 pas mesurés. Blocage initial résolu.
- Pilote : 536 images train, 238 validation, mAP50 23,73 %, mAP50–95 13,66 %. Le rappel et les piétons restent faibles.

## En cours / à préparer

- Priorité utilisateur : détection rapide du mouvement. Lecture accélérée M02 et diagnostic global M03 exécutés ; prochaine porte : annotations relues et mesures de réponse/fausses alertes par zone.
- Y02 : reporté dans l'ordre des priorités ; aucun nouvel entraînement lancé.
- Choix EMatch documenté mais conditionnel : compatibilité et VRAM Colab non testées.

## Étape M01 — 4 octobre 2026

- Branche d'activité causale implémentée sur grille 16×16, sans dépendance à YOLO ni classe connue.
- Comparaison 10/20/50 ms sur deux segments centrés de deux secondes ; 748 fenêtres traitées, 680 mesurées après préchauffage.
- Validation à 10 ms : activité médiane 4,47 ms ; lecture+activité 13,38 ms, p95 16,89 ms. Cadence de 10 ms non soutenue par le lecteur actuel.
- Cartes NPZ, CSV, rapports, exemples PNG et deux rejeux GIF produits ; conservation des comptes et des timestamps vérifiée.
- 33 tests réussis, dont six tests de causalité, unités, persistance et support spatial.
- Les zones de décor observées imposent une étude du mouvement de caméra. Délai réel de mouvement et fausses alertes non mesurés faute d'annotations temporelles. [Détail](25_M01_RAPID_ACTIVITY.md).

## Problèmes rencontrés

- M02 améliore le coût médian mais le rejeu autonome de validation dépasse encore 10 ms au p95 (11,32 ms). Aucune GT de début de mouvement n'est encore constituée.
- Pas de données, modèles, environnement isolé ou tests dans le dossier initial.
- Téléchargement depuis le terminal restreint : résolution DNS impossible. Accès au catalogue officiel réussi avec l'exécution réseau autorisée.
- Le lanceur `py` ne recense pas Python alors que la commande `python` fonctionne.
- Création initiale du venv bloquée par les permissions du répertoire temporaire, résolue avec exécution adaptée.
- Coupure du téléchargement gauche, résolue par reprise HTTP.
- Archives de labels imbriquées et sélection ambiguë par chemin absolu, corrigées.
- Aucun piéton dans le premier échantillon ; résolu pour le pilote par l'ajout de `04_b` et `thun_00_a`.
- Couverture limitée de S01 : 36 % de la GT sur validation ; grandes zones de profondeur manquante.
- Coût CPU élevé de la représentation bilinéaire de référence ; le temps réel n'est pas validé.

## Solutions appliquées

- Utiliser les pages et dépôts des auteurs pour les choix techniques.
- Limiter le premier téléchargement à une séquence et aux modalités nécessaires.
- Employer `python` puis le chemin explicite de l'environnement virtuel.
- Fenêtres dans une horloge absolue commune après ajout des offsets propres à chaque fichier.
- Lecture bornée en mémoire et erreurs explicites, sans fausse profondeur ni modèle fictif.
- Extraction des labels train et sélection par chemin relatif ; superposition de huit boîtes au temps inspecté.

## Décisions importantes

- DSEC recommandé comme dataset principal ; MVSEC comme validation secondaire de géométrie, sous réserve de l'audit détaillé.
- Traiter séparément la détection dans la vue native et la profondeur dans la vue rectifiée, avec association géométrique explicite.
- Les résultats de stéréo classique et de YOLO sont disponibles. Le diagnostic corrigé passe ; la validation YOLO reste faible. Ne pas confondre mémorisation du petit lot et généralisation.
- Conserver `04_e` en train/debug. Préférer pour ce petit pilote les séquences `04_b` et `thun_00_a`, moins volumineuses que les premières candidates.
- La première composante profonde obligatoire sera YOLO affiné ; la stéréo profonde est une comparaison ultérieure, pas un prérequis au premier MVP.

## Résultats actuels

Inspection réelle D00, baseline S01, export Y00, pilote Y01, activité M01, lecture accélérée M02, diagnostic global M03 et contrôles artificiels M04 exécutés. Validation stéréo locale `thun_00_a` : EPE 1,045 px, Bad3 4,26 % sur les pixels évalués, couverture GT 36,00 %. MAE de profondeur de surface 1,421 m sur l'intersection valide. Export YOLO : 774 images, 4 235 boîtes. Socle actuel : 67 tests réussis. Voir [résultats détaillés et limites](13_RESULTS.md).

YOLO a été entraîné puis validé sur un autre groupe de trajet. AP50 personne 9,49 %, voiture 37,97 %, rappel moyen 21,67 %. Cette validation sert à la sélection du modèle, pas de test final. Activité causale exécutée ; séparation des objets mobiles et délai réel non évalués. Stéréo profonde et coordonnées d'objets : **NOT RUN**. Le PFE complet n'est pas encore fonctionnel.

## Prochaine étape

Relire les annotations des six clips M03 puis mesurer la réponse et les fausses alertes par ROI. Le prototype global produit encore des résidus de décor et ajoute environ 8 ms de suivi/ajustement : étudier les erreurs avant de modifier les seuils ou d'intégrer cette étape à la branche rapide. [Protocole et limites](27_M03_GLOBAL_MOTION.md). Aucune tâche distante autonome n'est démarrée.

## Étape M02 — 4 octobre 2026

- Lecteur indexé ajouté sans modifier le lecteur binaire de référence ; disponible dans le rejeu par `--reader indexed`.
- 1 496 paires de fenêtres comparées ; événements, cartes et régions identiques, artefacts M01 conservés.
- Sur validation à 10 ms, comparaison appariée : coût combiné médian 10,54→7,70 ms (−27 %), p95 12,27→9,47 ms.
- Rejeu indexé autonome : médiane 8,45 ms, p95 11,32 ms et 14 % de fenêtres au-dessus de 10 ms. Gain confirmé, cadence non garantie.
- 39 tests réussis, six contrôles supplémentaires du lecteur ; 2 992 lignes de mesure et les cartes autonomes vérifiées. Sources exécutées archivées avec hashes.
- Les zones d'activité restent inchangées : aucune amélioration de qualité mouvement revendiquée. [Bilan M02](26_M02_INDEXED_READER.md).

## Étape M03 — 4 octobre 2026 : prototype et outillage

- Suivi de points causal et similarité globale robuste, avec abstention ; régions résiduelles natives sauvegardées.
- Six clips fixes de deux secondes : 660 sorties dont 600 mesurées et 600 images d'annotation sans prédictions. Test réservé intact.
- 599/600 fenêtres avec propositions résiduelles ; des régions du décor subsistent. Ce n'est pas un taux de fausses alertes faute de GT.
- Coût total médian 20,02–37,94 ms selon le clip, pour un pas de 20 ms ; suivi/ajustement médian 8,14–8,62 ms. Cadence combinée insuffisante.
- Annotateur local chargé et rendu inspecté ; évaluateur par ROI testé sur cas synthétiques. Aucun score réel fabriqué avec les annotations absentes.
- 53 tests réussis ; images, timestamps et hashes des sources vérifiés. [Rapport M03](27_M03_GLOBAL_MOTION.md).

## Étape M04 — 4 octobre 2026 : protocole et contrôles

- Deux audits fournis archivés sans modification ; remarques confrontées au code et décisions consignées.
- Protocole JSON figé avant les contrôles : réponse par ROI, incertitude, abstention, comptage des échecs et distinction avec le rappel d'objets.
- 486 essais artificiels et 27 540 fenêtres ; 405 essais de début de source et 81 témoins négatifs. Aucun usage de GT ou de scène DSEC pour ces résultats.
- Réglage M01 : source faible manquée, sources moyenne/forte détectées dans les cinq phases, bouffée globale confondante avec 90 ms d'alerte sur une seconde.
- Contrôle d'annotations ajouté : cible, doublons exacts, exclusions, inventaire par clip. État actuel : zéro ROI réelle relue fournie.
- 61 tests réussis, sources et unicité des essais vérifiées. [Rapport M04](29_M04_MOTION_PROTOCOL.md).

## Étape M05 — 4 octobre 2026 : activité relative et historique

Trois variantes comparées : M01 inchangé, seuil relatif global, seuil relatif avec historique causal. 306 essais artificiels et 600 fenêtres réelles de train (trois clips de deux secondes, trois variantes par fenêtre). Aucun nouveau rejeu sur validation/test.

Le seuil relatif rejette la bouffée uniforme construite. L'historique réduit la proportion de cellules actives sur train, mais dans le contrôle de source moyenne persistante, il ne signale la ROI que pendant 9,7 % des sorties après début, contre 97,3 % pour M01 et le relatif seul. Une amélioration du rappel réel ou des fausses alertes n'est pas démontrée.

67 tests réussis ; 45 réponses/délais de référence sont identiques à M04. Trois GIF et des comparaisons PNG sont disponibles. [Résultats, temps et limites M05](31_M05_ADAPTIVE_ACTIVITY.md). Prochaine porte : annotations relues et évaluation temporelle compatible avec les cadences, puis comparaison géométrique/de profondeur.


## M06 — Évaluation temporelle prête (4 octobre 2026)

- **Terminé :** évaluateur des sorties à 10/20 ms conservant les bornes d’annotation, comparaison de quatre méthodes et annotateur avec durée continue optionnelle.
- **Exécuté :** contrôle de 2 100 sorties mesurées sur trois clips train existants ; aucun nouvel accès test/validation ni rejeu lourd.
- **Vérifié :** 81 tests réussis, dont 14 nouveaux tests des contrats temporels et de la comparaison.
- **Problème résolu :** les prédictions M05 à 10 ms ne correspondaient pas à la grille d’annotation de 20 ms imposée par l’ancien évaluateur. Adaptation sans interpolation ni changement des bornes.
- **Limite restante :** aucun export réel relu fourni ; statut PENDING_ANNOTATIONS. Interface générée, contrôle interactif non effectué car les URL file: sont refusées par le navigateur intégré.
- **Décision :** résultat par ROI, pas de classement de méthodes ni de durée de mouvement supposée.
- **Prochaine étape :** annotations aveugles des trois clips, puis comparaison des réponses, fausses alertes et maintien. [Guide M06](34_M06_TEMPORAL_EVALUATION.md).


## M07 — Stabilité du rejeu cadencé (4 octobre 2026)

- **Terminé :** ordonnanceur causal de rejeu, métriques d’attente et d’âge de sortie, protocole train et traces CSV.
- **Exécuté :** deux séquences train, 12 secondes centrales, pas 10/20 ms, deux répétitions : huit cas complets, 7 200 fenêtres.
- **Résultat :** à 10 ms, retard final de 801,32 et 533,62 ms sur `04_b`. À 20 ms, âge de sortie p95 de 19,96 puis 123,97 ms sur cette séquence ; variabilité, pas de garantie stricte.
- **Problème rencontré :** protocole initial de 20 secondes incompatible avec les HDF5 locaux de 13,401 secondes. Échec avant mesure conservé dans M07 ; protocole 12 secondes exécuté dans M07_12s, avec contrôle de durée ajouté.
- **Vérifié :** 87 tests réussis, 7 200 fenêtres contiguës, mêmes comptes d’événements entre pas/répétitions, détecteur et lecteur inchangés depuis M05.
- **En attente :** annotations réelles relues ; aucune qualité de mouvement ni latence depuis un début physique annoncée.
- **Prochaine étape :** profilage de la fin de `04_b`, optimisation équivalente, comparaison appariée. [Preuves M07](35_M07_PACED_REPLAY.md).


## M08 — Optimisation de lecture à sorties identiques (4 octobre 2026)

- **Terminé :** profilage des trois dernières secondes de `04_b`, sous-classe du lecteur conservant les quatre handles HDF5, benchmark apparié et autonome.
- **Équivalence :** 3 600 fenêtres mesurées + 60 d’échauffement ; tous les champs événementiels et toutes les sorties du détecteur exactement identiques.
- **Résultat :** coût médian lecture + activité réduit de 8,87 à 14,44 % sur les quatre cas train appariés.
- **Rejeu :** huit passages de 12 secondes à 10 ms, 9 600 fenêtres ; âge p95 sur `04_b` de 997,22→261,11 ms au premier passage, mais seulement 358,15→351,19 ms au second. Gain variable, cadence stricte non acquise.
- **Vérifié :** 91 tests réussis, snapshots et onze empreintes vérifiés ; sources du lecteur de référence, du détecteur et de l’ordonnanceur préservées.
- **Décision :** lecteur optimisé disponible pour la suite ; conserver les lanceurs historiques avec leur lecteur d’origine.
- **Prochaine étape :** optimiser le calcul d’activité à sorties identiques ; les annotations M06 restent attendues pour la qualité du mouvement. [Bilan M08](36_M08_CACHED_READER.md).


## M09 — Calcul d’activité optimisé, terminé le 7 octobre 2026

- **Terminé :** table pixel→cellule, extraction des pixels occupés via masque booléen, copies de conversion évitées lorsque possible. Référence M01 préservée.
- **Vérifié :** 96 tests réussis, 3 660 comparaisons exactes des sorties et de l’état, empreintes événementielles identiques à M08.
- **Mesuré :** baisse du coût médian du calcul de 13,07–18,14 % ; lecture partagée + calcul réduite de 7,28–11,40 % dans les comparaisons appariées.
- **Limite :** huit rejeux autonomes (9 600 fenêtres) donnent un effet variable sur le retard ; un passage `04_b` régresse malgré le gain de coût apparié. Pas de cadence stricte garantie.
- **Reprise :** première campagne du 4 octobre interrompue après quatre rejeux ; résultats partiels conservés dans M09. Campagne complète séparée dans M09_20261007, sans regroupement des répétitions de jours différents.
- **Décision :** variante optimisée disponible comme option, mêmes seuils et règles ; ne pas confondre activité et mouvement indépendant.
- **Prochaine étape :** intégrer M08/M09 au démonstrateur avec choix de variante et affichage des retards. Annotations M06 toujours attendues pour la qualité réelle. [Bilan M09](37_M09_LOOKUP_ACTIVITY.md).


## Recentrage utilisateur — 7 octobre 2026

Priorité explicite : détection des objets mobiles. La séparation du mouvement d’objet et du mouvement apparent du décor passe avant de nouvelles micro-optimisations et avant un simple démonstrateur d’activité. Le code M08/M09 reste acquis ; la qualité de mobilité n’est toujours pas évaluée.

**Action réalisée :** objectif, cas caméra fixe/mobile, abstention, mesures de qualité et piste secondaire EVIMO documentés ; consigne persistante et architecture actualisées. **Suite : M10 exécuté ci-dessous** ; référence réelle de mobilité encore à constituer. [Plan](38_OBJECTIF_OBJETS_MOBILES.md).


## M10 — Candidats persistants, exécuté le 7 octobre 2026

- Filtre de support, direction et taille, puis association sur trois observations consécutives ; sorties provisoires/persistantes explicitement non confirmées comme objets mobiles.
- Sept contrôles idéaux : translation locale retenue avec 40 ms supplémentaires de confirmation ; bruit directionnel rejeté. Contre-exemples conservés : parallaxe acceptée et rotation locale manquée.
- Trois extraits train de deux secondes, 300 fenêtres mesurées : 495 régions brutes et 178 régions persistantes cumulées. Pas de qualité réelle déduite de cette diminution.
- Coût total médian 13,22 / 15,71 / 21,57 ms suivant l'extrait ; rejeu non cadencé, sans garantie temps réel.
- 105 tests réussis ; 14 empreintes et snapshots vérifiés ; 327 sorties valides brutes exactement conformes à M03, échauffement inclus. Trois GIF et PNG exportés.
- Prochaine étape : référence de mobilité et traitement géométrique de la parallaxe, avant de nouvelles heuristiques. [Rapport M10](39_M10_MOBILE_CANDIDATES.md).


## M11 — Modèle rigide assisté par profondeur, 7 octobre 2026

- Module PnP/RANSAC avec profondeur au premier instant, contrôle du support, résidus rectifiés et abstention ; provenance prédiction/oracle explicite.
- Référence 3D à deux instants : 9 scénarios × 3 niveaux de bruit × 5 seeds, soit 135 essais et 16 740 correspondances archivées. Pas de simulation du capteur événementiel ni de LK.
- Dans le contrôle de translation caméra devant scène fixe, les 52/124 faux points candidats M03 sont expliqués par M11. Les 16 points mobiles des contrôles de translation/rotation locale sont retenus. Profondeur synthétique exacte dans ces cas.
- Échecs conservés : profondeur locale biaisée et mouvement majoritaire pris pour le décor. Aucune qualité réelle de mobilité annoncée.
- 117 tests réussis ; 135 artefacts relus, résidus recalculés, six empreintes/snapshots et neuf figures vérifiés.
- Inventaire réalisé : 40 profondeurs S01 prédites sur train, espacées d'environ 700 ms. Prochaine étape : suivi rectifié à leurs dates et +20 ms, contrôle de couverture/abstention, puis référence réelle de mobilité. [Bilan M11](40_M11_RIGID_MOTION.md).


## M12 — Modèle géométrique sur DSEC réel, 7 octobre 2026

- Suivi sur images rectifiées 640×480 et profondeur S01 prédite au premier instant ; normalisation figée train, contrôle des dates/calibration/masques, aucune GT dans la décision.
- 40 cartes examinées, 38 paires complètes exécutées ; les deux fins de fichier sans événements jusqu'à +20 ms sont exclues explicitement.
- 14 818 correspondances suivies, 8 630 évaluables (58,2 %), 6 188 inconnues. Sur le support commun, 176 candidats par similarité contre 49 par modèle rigide. Aucune précision/rappel réel ni réduction de fausses alertes déduite.
- Images de 50 ms décalées de 20 ms, chevauchement 30 ms ; approximation temporelle documentée. Pas de suivi continu ni de mesure de début de mouvement.
- Médianes 321,06 / 385,26 ms avec profondeur déjà calculée ; représentation dominante. Cadence 20 ms non soutenue.
- 123 tests réussis ; 15 sources/protocole et snapshots, six fichiers de données, 38 paires et leurs résidus vérifiés.
- Prochaine étape : extraits continus et référence de mobilité relue, puis contrôle du chevauchement et du maintien du signal sur objets mobiles. [Résultats M12](41_M12_REAL_RIGID_MOTION.md).


## M13 — Sensibilité temporelle et paquet de relecture, 7 octobre 2026

- Six extraits train de deux secondes aux indices M12 3/10/17 ; 600 PNG rectifiés sans prédictions, six GIF et six planches produits.
- 24 comparaisons : durées 20/50 ms × écarts 20/50 ms × six dates. Même profondeur prédite S01 au premier instant ; seuil de candidat 150 px/s, seuil RANSAC inchangé.
- Candidats cumulés 2 / 0 / 5 / 3 selon les quatre conditions ; supports différents, aucune configuration déclarée meilleure. Les durées, le chevauchement et les correspondances changent ensemble.
- Six cas 50/20 exactement conformes à M12. 129 tests réussis ; 17 sources/protocole, 600 images et 24 paires contrôlés.
- Outil de relecture et validateur de format disponibles. Aucune annotation réelle relue enregistrée : qualité toujours en attente. Syntaxe JavaScript vérifiée, interaction complète navigateur non testée automatiquement.
- Prochaine étape : relecture des zones et contrôle des indices de mobilité, puis évaluation sur les dates réellement couvertes. [Bilan et accès M13](42_M13_TEMPORAL_REVIEW.md).


## Changement de parcours — annotations manuelles sautées

7 octobre 2026 : demande utilisateur explicite de sauter cette partie. La relecture M13 n'est plus un préalable ; artefacts et diagnostics conservés, aucune annotation inventée. Prochaine étape : audit d'un petit échantillon public avec référence de mobilité exploitable, piste EVIMO/EVIMO2. DSEC reste principal ; aucune donnée supplémentaire acquise et aucune métrique de mobilité réelle ajoutée lors de ce changement.


## M14 — EVIMO2 acquis sans annotations utilisateur, 7 octobre 2026

- Une séquence officielle train, caméra gauche : 239,89 Mio transférés pour six fichiers (594,01 Mio), 62 915 815 événements sur environ 13 secondes.
- 750 paires masque/profondeur sur 782 dates de métadonnées, huit identifiants visibles, 2 603 dates de trajectoire. Les trous de référence restent explicites : jusqu’à 400 ms entre cartes.
- Six hashes vérifiés, toutes les cartes et tous les événements inspectés, lecteur spécialisé de métadonnées sans exécution de classes importées, planche de trois dates fixes produite.
- 137 tests réussis. Pas de métrique de mobilité calculée.
- Prochaine étape : résoudre les champs de calibration divergents et composer les poses dans le monde pour construire la référence de mobilité. DSEC reste principal ; aucune annotation manuelle demandée. [Rapport et aperçu M14](43_M14_EVIMO_AUDIT.md).


## R01 — Nettoyage et refactoring, 8 octobre 2026

- Quatre modules partagés extraits ; seize scripts adaptés, commandes existantes conservées hors protection de sortie neuve pour l’audit EVIMO.
- README simplifié, carte du code et commande `check_project.py` ajoutées.
- 144 tests, syntaxe de 78 fichiers Python et aides de 24 CLI vérifiées.
- Rejeu M11 : 135 cas et 1 620 tableaux identiques hors durées. Audit M14 et aperçu identiques hors provenance.
- 4 381 anciens fichiers de données/résultats inchangés en taille/date, modules algorithmiques existants inchangés par SHA256. Sauvegardes conservées.
- Prochaine étape : petit audit DSEC-MOD, EVIMO conservé en complément, aucune annotation manuelle requise. [Bilan R01](44_PROJECT_MAINTENANCE.md).


## M15 — Référence routière DSEC-MOD, 8 octobre 2026

- Cache officiel et sources figés par commit/SHA256 ; 1 794 boîtes Moving sur 534 frames de `04_e` et `04_b`, côté train uniquement.
- Trois RGB de `04_e` acquis par lectures partielles de l'archive de 15 Go, CRC et hashes vérifiés ; aperçu des annotations produit.
- Deux fichiers de dates RGB DSEC acquis : 269 dates contre 267 images MOD par séquence. Aucun timestamp ni repère événementiel supposé ; aucune métrique réelle de mobilité.
- La réserve `09_b` figure dans le cache commun acquis, mais ses boîtes numériques et images n'ont pas été inspectées. Le groupe `09` traverse les splits MOD officiels ; le protocole local par groupe reste prioritaire.
- Adaptateur spécialisé, commande d'audit hors ligne et neuf tests ajoutés ; 153 tests réussis, syntaxe de 81 fichiers et 25 aides CLI vérifiées. Prochaine étape M16 : correspondance des frames aux dates et repères DSEC, puis comparaison des candidats géométriques. [Audit M15](45_M15_DSEC_MOD_AUDIT.md).


## M16 — Alignement de six références train, 9 octobre 2026

- Vingt-deux RGB originaux DSEC et trois RGB MOD supplémentaires acquis par accès partiel, CRC/SHA256 vérifiés ; deux fichiers d'exposition ajoutés.
- MOD 1/134/267 correspond à DSEC 1/134/267 sur `04_e` et `04_b`. Six dates et 22 boîtes exportées ; aucune extrapolation à toutes les frames.
- Projection RGB rectifié → `camRect0` calculée par calibration ; erreur photométrique moyenne 0,360–0,618/255, candidats voisins nettement moins proches. Translation physique de 4,57 cm non corrigée : parallaxe conservée comme limite.
- Deux planches RGB MOD / RGB reprojeté / activité causale 20 ms produites et inspectées. Les rectangles sont des références publiées, pas des prédictions.
- 164 tests réussis, syntaxe de 85 fichiers et 26 aides CLI vérifiées. Prochaine étape M17 : diagnostic de couverture et candidats dans les boîtes aux six dates, sans labels dans le détecteur. [Rapport M16](46_M16_DSEC_MOD_ALIGNMENT.md).


## M17 — Diagnostic sur références publiques, 10 octobre 2026

- Six dates M16 conservées, profondeur S01 recalculée sans GT ; quatre paires traitées, deux abstentions de démarrage faute des 70 ms d'historique nécessaires.
- 1 558 correspondances, 928 profondeurs exploitables, 630 inconnues ; aucun résidu supérieur à 3 px. Le modèle dominant n'est pas une preuve de pose caméra correcte.
- Sur 22 boîtes : 7 sans historique, 4 sans suivi, 3 sans profondeur, 8 avec points évalués sans résidu. Aucun score de rappel/precision objet annoncé ; marges −5/0/+5 px documentées.
- Deux boîtes sans profondeur contiennent 25 points dans la bande gauche de 96 colonnes, sans profondeur SGBM valide. Les autres limites de support restent distinctes.
- Médiane CPU 654,8 ms avec calcul stéréo frais, hors initialisation et rendu ; cadence 20 ms non atteinte.
- 174 tests réussis, syntaxe de 88 fichiers et aides de 27 commandes vérifiées. Six panneaux, sorties d'inférence, diagnostics, sources et hashes conservés. Prochaine étape M18 : comparer 50/20 et 20/20 ms sur support temporel commun, seuils conservés. [Résultats M17](47_M17_REFERENCE_DIAGNOSTIC.md).

## M18 — Fenêtres 50 ms et 20 ms, 10 octobre 2026

- Quatre dates communes, 15 boîtes, seuils et normaliseur conservés ; profondeur recalculée pour chaque représentation. Les six sorties 50 ms reproduisent exactement M17 hors temps.
- Support de profondeur dans l'union des boîtes : 141 → 72 points ; aucun candidat dans les boîtes. Deux boîtes perdent tout suivi avec 20 ms. Le seul candidat des dates communes est hors référence, sans label négatif certifié.
- Deux dates de démarrage analysées séparément : 20 ms devient traitable, sans candidat dans les sept boîtes. Pas de gain de délai de détection d'objet déduit.
- Médianes CPU 544,96 / 324,08 ms, exécutions uniques hors ligne ; temps réel non atteint. La référence 50 ms est conservée.
- 182 tests réussis, syntaxe de 90 fichiers Python et 28 aides CLI vérifiées ; six panneaux et rapports traçables. [Bilan M18](49_M18_TEMPORAL_WINDOWS.md).

## M19 — Audit statique EMatch, 10 octobre 2026

- 113 fichiers texte officiels figés au commit `92e528bd9d0d1f1d7774385233a841c8bd6eb8d8`, tailles et SHA256 vérifiés, aucun code amont exécuté.
- Entrées nominales : voxels stéréo 100 ms / 15 canaux. Générateur de cache publié avec double conversion temporelle ; provenance effective des caches d'entraînement inconnue.
- Les quatre séquences locales figurent dans la liste train stéréo publiée ; ne pas déclarer le checkpoint indépendant de `thun_00_a` ou `09_b`.
- Poids standard identifiés sur Drive (25,7 Mo affichés), non acquis ni chargés. Aucune installation PyTorch, aucune inférence et aucune mesure GPU.
- Prochaine étape : adaptateur causal et contrôle SGBM 100 ms sur quatre dates train, puis audit binaire des poids et essai isolé. [Constats et protocole M19](50_M19_EMATCH_AUDIT.md).

