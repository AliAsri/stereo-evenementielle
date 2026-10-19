# Priorité : détecter les objets mobiles

Décision utilisateur du 7 octobre 2026 : « on focus sur la detection des mouvement mobile ».

## Validation indépendante proposée — 19 octobre 2026

**Statut : préparation choisie, acquisition autorisée puis close au plafond ; références non obtenues, évaluation non exécutée.** Après l'échec ORB, l'utilisateur choisit de préparer une validation avec une référence publique indépendante. Le lot et son budget ont été proposés avant téléchargement, puis approuvés dans une réponse explicite. Les contrôles EVIMO2 train déjà explorés restent clos. Aucun changement du démonstrateur DSEC, de ses paramètres ou de son checkpoint.

### Référence retenue pour la proposition

**EVIMO2v2, nouveaux enregistrements du split officiel `eval`.** Son [article](https://arxiv.org/abs/2205.03467) décrit profondeur, segmentation et poses caméra/objets ; la [page officielle](https://better-flow.github.io/evimo/download_evimo_2.html) distingue scènes avec objets indépendants et scènes rigides. La [documentation des repères](https://better-flow.github.io/evimo/docs/ground-truth-format.html#transform-convention) explicite les transformations. Sources relues le 19 octobre 2026. C'est la référence candidate pour contrôler le mécanisme géométrique ; aucune donnée candidate n'a encore été qualifiée localement.

| Cas proposé | Séquence listée dans `eval` sur le site officiel | Rôle |
|---|---|---|
| Objets indépendants, catégorie `imo`, caméra gauche | `scene14_dyn_test_03_000000` | Examiner suivi, pose estimée et signal propre de l'objet |
| Scène rigide, catégorie `sfm`, caméra gauche | `scene_03_00_000000` | Examiner les candidats produits par le seul mouvement de caméra |

Ces noms sont fixés avant acquisition/prédiction : première entrée publiée de la scène IMO 14, absente des deux scènes 13/15 utilisées localement ; première entrée publiée du lot SfM d'évaluation. Les chemins attendus sont `left_camera/{imo,sfm}/eval/<séquence>`, à confirmer dans les archives. Aucun des deux noms n'est présent dans les données locales ni dans les documents/configurations/scripts/tests inspectés. Cela établit une séparation des enregistrements locaux, **pas une indépendance certifiée des objets, du dispositif ou de la distribution**. Le suffixe `test` ne détermine jamais le split : les deux anciens extraits portant ce suffixe sont bien dans `train`.

### Acquisition bornée ensuite approuvée

Deux séquences, six fichiers chacune : `dataset_info.npz`, `dataset_depth.npz`, `dataset_mask.npz`, `dataset_events_t.npy`, `dataset_events_xy.npy`, `dataset_events_p.npy`. Aucune caméra droite/RGB, aucun poids ni archive complète stockée. **Plafond proposé : 512 Mio de corps HTTP lus au total, sondes/reprises comprises ; 4 Gio extraits au total.** Dossier neuf, manifeste des octets lus et des membres rencontrés, taille/SHA-256 de chaque fichier, aucune réécriture des acquis.

**Faisabilité non démontrée :** les archives officielles de la caméra gauche sont annoncées à environ 1,8 Go (`imo`) et 22 Go (`sfm`). Le [script des auteurs](https://github.com/better-flow/evimo/blob/master/tools/evimo2_v2_downloader/download_evimo2_v2.sh) utilise des `tar.gz`. Un décodeur gzip ordinaire doit traverser le préfixe : une requête HTTP Range ne permet pas de sauter directement à une séquence sans index de décompression. Si les séquences sont trop loin, arrêter au plafond et conclure acquisition incomplète ; ne pas changer de séquence ou augmenter le budget implicitement. La préparation initiale n'avait lancé aucun transfert binaire. Le lecteur historique ne sélectionnait que `train` ; un mode explicite `--validation-reference` a ensuite été ajouté et vérifié avant la tentative décrite ci-dessous.

### Sélection temporelle avant inférence

Après acquisition autorisée et contrôle d'intégrité, lire seulement les métadonnées et les en-têtes pour qualifier split, calibration, format, unités, horloges et présence des références. Fixer, par séquence, la première date GT `t0` disposant de 50 ms d'historique événementiel. Prévoir au plus **dix intervalles successifs de 100 ms** depuis cette date ; leurs bornes doivent correspondre aux dates GT à la tolérance de sérialisation existante de 1,1 µs. Les timestamps entiers passés au moteur doivent aussi respecter un écart de 100 000 µs et une profondeur exactement à la date source ; sinon l'intervalle reste indisponible. Aucune interpolation ou date voisine substituée.

Un intervalle sans référence exacte, fichier, pose ou historique est compté indisponible, jamais remplacé par un intervalle ultérieur plus favorable. Aucun filtre de surface de cible, déplacement, nombre de graines, réussite PnP ou score ne sélectionne les dates. La liste des dates/IDs disponibles et indisponibles, les empreintes et les paramètres sont enregistrés **avant de produire les images et les correspondances**. Un extrait court ou sans mouvement exploitable donne un contrôle insuffisant ; pas de recherche d'une autre paire après prédiction.

### Parcours figé et séparation des références

Utiliser le parcours natif du diagnostic EVIMO existant : images de comptage causales 50 ms, normalisation fixe `uint8(255 × clip(log1p(count)/log(21), 0, 1))`, GFTT global 400, qualité 0,01, distance minimale 6 px ; contrôle LK court 20 ms puis suivi direct 100 ms, fenêtre 21×21, niveau 2 et aller-retour ≤1 px. Aucun ORB, grille, récence, chaînage ou deuxième ajustement de pose. Une calibration non prise en charge par le lecteur existant arrête la qualification ; pas de modèle de distorsion substitué.

Le modèle conserve `RigidMotionConfig` : au moins 20 profondeurs, 16 inliers, fraction 0,6, enveloppe 0,1, consensus 1,5 px, candidat >3 px, 500 itérations. Prévoir OpenCV et versions figés, OpenCL désactivé, deux threads CPU ; `seed=42` reste la métadonnée historique du backend. Une pose refusée reste `UNKNOWN`.

**Profondeur oracle explicite :** seul ce contrôle géométrique emploie la profondeur de référence à la date source, `depth_source=dataset_reference`. Il ne teste donc ni SGBM prédit, ni YOLO, ni XYZ, ni tout le pipeline DSEC. Les images/normalisations EVIMO diffèrent aussi du parcours rectifié DSEC. Aucun masque, ID cible, pose caméra ou déplacement GT n'entre dans la sélection, le suivi ou le PnP. Masques et poses ne sont ouverts par l'évaluation qu'après sauvegarde des prédictions ; la profondeur oracle est l'exception déclarée, pas une entrée dissimulée.

### Référence ponctuelle et comparaisons prévues

Pour une graine source avec identité et profondeur GT connues, reconstruire `X0` dans la caméra source. Les poses donnent `T_camera = inverse(T_W_C1) × T_W_C0` et, pour un objet identifié, `T_object = T_C1_O1 × inverse(T_C0_O0)`. Leur projection permet d'obtenir le point attendu avec l'objet et le point attendu si seul le mouvement caméra intervenait. Dans le cas SfM annoncé rigide, la correspondance attendue utilise `T_camera` ; les poses d'objets servent à contrôler la cohérence de référence. Translation **et rotation** sont prises en compte ; le déplacement de l'origine de l'objet ne suffit pas.

- **C0 :** déplacement suivi brut `||q_suivi − p||`.
- **C1, profondeur oracle :** `||q_suivi − projection(T_estimé, X0)||` avec l'unique modèle estimé.
- **C2, témoin oracle après inférence :** `||q_suivi − projection(T_camera, X0)||`. Ce calcul n'est pas un second ajustement, n'entre jamais dans C1 et ne sert pas à choisir une pose.

Comparer C0/C1/C2 sur la même intersection de points valides, en publiant séparément toute la couverture initiale. L'erreur du suivi se mesure contre la projection objet de référence, et l'erreur de pose contre `T_camera`. Mesures dans le plan pinhole non distordu ; les correspondances entre ce plan et les rasters de référence restent explicites.

L'admissibilité d'une référence dépend de la **projection GT**, pas de la destination prédite : identité connue aux deux dates au pixel GT projeté, profondeur positive, projection intérieure à une marge de 1 px et voisinage 3×3 d'identité constante ; profondeur GT à l'arrivée cohérente à `max(1 cm, 1 % de Z)` près. Ces deux marges sont des conventions d'évaluation proposées, pas des incertitudes physiques certifiées. Publier les exclusions par motif. Si une correspondance prédite aboutit à un autre objet alors que sa projection GT est admissible, **compter son erreur**, sans la faire disparaître du dénominateur. Masque zéro, projection occultée ou référence manquante restent inconnus ; le [générateur officiel de flux](https://better-flow.github.io/evimo/docs/evimo-flow.html) signale lui-même des régions sans profondeur/flux.

Pour le bilan de séparation relatif aux références : négatifs = points admissibles du cas SfM annoncé rigide ; positifs IMO = points d'objets dont les deux projections GT (objet/caméra seule) diffèrent de **plus de 3 px**. Les autres points IMO ne sont pas automatiquement statiques. Ce seuil d'observabilité est fixé avant résultats et ne prétend pas détecter tout mouvement 3D. Si calibration, visibilité ou qualité de pose rendent ces associations non admissibles, garder les erreurs descriptives et suspendre la matrice de séparation ; aucune AUC physique artificielle.

### Mesures et règle d'arrêt

| Mesure à produire | Dénominateur et interprétation |
|---|---|
| Suivi | Graines référencées initiales, pertes, suivis évaluables, erreurs médiane/p95, nombre ≤3 px ; fraction correcte rapportée aussi aux graines initiales, pertes incluses |
| Pose | Intervalles tentés/acceptés, erreurs rotation/translation ; refus comptés séparément, jamais erreur nulle |
| Séparation C0/C1/C2 | Décisions au seuil strict >3 px sur points communs ; occurrences positives/rigides par intervalle, candidats sur rigide et positifs récupérés ; abstentions et couverture publiées séparément |
| Coût local | Lecture/représentation, suivi, ajustement ; premier appel séparé, médiane/p95 des appels disponibles, références évaluées hors temps d'inférence ; aucun FPS DSEC ou délai de début déduit |

**Seuil minimal proposé pour comparer la séparation :** au moins trois intervalles et vingt points référencés dans chacun des deux cas. C'est une règle de suffisance descriptive, pas une puissance statistique. Si elle échoue, déclarer le lot insuffisant sans prolonger l'extrait. Pour soutenir un intérêt local de la compensation, C1 doit réduire les candidats sur le cas rigide sans perdre les positifs par rapport à C0, sur support commun ; tout compromis ou abstention supplémentaire doit être explicite. C2 sert à distinguer une limite de suivi d'une limite du modèle estimé, pas à revendiquer la réussite de C1. Une valeur manquante reste `null`.

Deux enregistrements et dix intervalles au plus ne permettent pas une généralisation statistique ; les points et fenêtres sont corrélés. Publier les deux cas séparément, pas une précision globale mélangeant des populations sélectionnées. Aucun AP d'objet, rappel pixel dense ou onset sans protocole correspondant. Même un résultat favorable ne promeut pas une méthode sur DSEC. Toute correction choisie après consultation de ce lot en fait du développement pour cette correction ; elle ne peut plus être retestée comme si le lot était resté aveugle.

**Accord ensuite reçu :** acquisition bornée et qualification seulement, sans inférence/entraînement. Le mode `--validation-reference` du lecteur existant fixe deux parts de 256 Mio avant tout HTTP ; plan dans `outputs/motion/independent_reference_20261019/acquisition_plan.json`. **340 tests passent**, dont sept nouveaux contrôles de compteurs communs, allowlist, intégrité des fichiers écrits, absence d'écrasement, refus des liens et dépassements de taille. La première exécution ciblée avait échoué sur le répertoire temporaire du sandbox Windows ; le même test passe avec les temporaires dans le projet. Aucune nouvelle évaluation scientifique ; l'acquisition est désormais close.

### Résultat de l'acquisition autorisée — 19 octobre 2026

**Arrêt au plafond, zéro fichier cible obtenu.** Le plan enregistré avant HTTP fixe les mêmes deux noms, six fichiers par séquence et deux parts non transférables de 256 Mio, sous plafond commun 512 Mio / 4 Gio extraits. Aucun retry, changement de séquence, extraction de fichiers voisins, modèle ou inférence.

| Archive | Corps HTTP lus | Séquences rencontrées dans le préfixe | Fichiers cibles |
|---|---:|---|---:|
| IMO gauche | 268 435 456 octets | `train/scene13_dyn_test_02_000000`, début de `train/scene15_dyn_test_00_000000` | 0/6 |
| SfM gauche | 268 435 456 octets | `train/seq_1_2_000000` | 0/6 |
| Total | **536 870 912 octets = 512 Mio** | Cibles `eval` non atteintes | **0/12 ; zéro octet extrait** |

Réponses HTTP 206 et bornes `0–268435455` enregistrées, compteurs individuels/commun concordants. Les archives annoncent respectivement **1 819 418 535** et **21 974 770 503 octets** ; ni leur intégrité complète ni la présence des deux chemins cibles dans les octets non visités ne sont certifiées par ce transfert. Les douze fichiers des deux anciens extraits ont été revérifiés par taille/SHA-256 : tous conformes, sans nouvelle inférence.

**Qualification : `ACQUISITION_CLOSED_REFERENCE_UNAVAILABLE`.** Aucun dossier cible créé ; aucune date, calibration, pose ou masque nouveau qualifié. Pas de métrique, manifeste temporel d'évaluation ou test de mobilité. [Plan préalable](../outputs/motion/independent_reference_20261019/acquisition_plan.json) · [Bilan d'acquisition](../outputs/motion/independent_reference_20261019/acquisition.json) · [Qualification de l'accès et intégrité des anciens fichiers](../outputs/motion/independent_reference_20261019/qualification.json). Rapports HTTP/membres et empreintes dans le même dossier ; source exacte exécutée conservée dans `source_snapshot/` (SHA-256 du lecteur `7b46d085df97d5c3ee790c7e37e6827b5bbe5810b9e31fb71ed7844874805777`). Le docstring CLI a seulement été clarifié après acquisition, sans changer le fonctionnement.

**Leçon de coût :** la relecture du manifeste ancien, effectuée trop tard, montre déjà 334 325 760 octets consommés avant d'avoir terminé les deux premiers extraits train IMO. Il permettait de prévoir que 256 Mio n'atteindraient pas une séquence ultérieure. Ce préfixe n'aurait pas dû être relu pour retrouver cette information. Conserver le constat pour éviter une nouvelle dépense ; il ne certifie pas la position comprimée des cibles non visitées.

**Décision : clore cet accès sous la répartition approuvée.** Ne pas réessayer, réallouer le plafond ou acquérir les archives complètes implicitement. Le résultat établit l'échec dans ces deux préfixes, pas une impossibilité universelle sous 512 Mio. Toute nouvelle proposition doit d'abord établir un accès par séquence ou un coût réaliste et être soumise avant transfert. Les anciens contrôles train et ORB restent clos ; le protocole ci-dessus reste une préparation, sans réussite expérimentale.

### Recherche d'accès ciblé et coût documenté — 19 octobre 2026

**Lecture documentaire uniquement : aucun nouvel octet de dataset, aucune inférence ni entraînement.** Après l'échec d'accès borné, examen du script des auteurs et des échanges du dépôt officiel par le connecteur GitHub ; lecture de la documentation ETAP, puis vérification du miroir dans le navigateur. [Sources conservées](../outputs/motion/independent_reference_20261019/access_review_20261019.json).

- Le [script officiel](https://github.com/better-flow/evimo/blob/master/tools/evimo2_v2_downloader/download_evimo2_v2.sh) distribue toujours des archives de catégorie/caméra ; aucun accès aux deux séquences individuelles n'y est défini.
- Un auteur fournit un [miroir Drive dans la discussion #33](https://github.com/better-flow/evimo/issues/33#issuecomment-2613657285). Le lien exact répond **404 dans notre visite du navigateur** ; aucun fichier cliqué ni téléchargé. Cela ne prouve pas une suppression définitive ou une indisponibilité sous toute autre permission.
- La [préparation EVIMO2 d'ETAP](https://github.com/tub-rip/ETAP#evaluation-evimo2-samsung-dvs-gen3-640-x-480-px) renvoie à l'archive officielle Samsung et propose des tracks pré-calculés : aucun remplacement vérifié des six fichiers des deux séquences gauche fixées ici. Aucun poids, autre caméra ou méthode ETAP acquis/intégré.
- La [clarification des auteurs sur la disponibilité des caméras](https://github.com/better-flow/evimo/issues/36#issuecomment-5430830874) explique les onze séquences train gauche/droite, contre vingt et une pour Samsung, et annonce toutes les caméras sur le test IMO. Le nombre de séquences ne se transfère donc pas d'une caméra à l'autre. Cette réponse ne remplace pas la qualification locale des cibles non acquises.

**Conclusion bornée : aucun lien individuel confirmé dans ces sources, sans preuve d'une absence universelle.** Le miroir défaillant est un blocage d'accès, pas un défaut de la détection. Les cibles et le protocole restent inchangés.

| Lecture maximale si les deux archives entières doivent être traversées | Octets conservés dans les en-têtes du 19 octobre |
|---|---:|
| IMO gauche | 1 819 418 535 |
| SfM gauche | 21 974 770 503 |
| Total | **23 794 189 038 = 23,79 Go / 22,16 Gio** |

Les offsets des cibles restent inconnus : le coût réel peut être inférieur, et ces tailles supposent des archives inchangées. Les préfixes de 256 Mio avaient pris environ 145 s et 172 s pour HTTP/décompression/parcours ; leur extrapolation aux archives donne **environ 4,2 h**, très incertaines. Ce n'est pas un débit réseau pur ni une durée promise. Même avec un budget élargi, la présence, la taille extraite et l'admissibilité des cibles restent à vérifier ; un plafond d'extraction de 4 Gio pourrait aussi arrêter l'acquisition.

**Choix proposés, aucun encore autorisé :** publier la demande ciblée ci-dessous (recommandé), autoriser une nouvelle acquisition plafonnée à **24 000 000 000 octets HTTP et 4 Gio extraits** sans inférence/entraînement, ou laisser le protocole en attente. Le plafond précédent de 512 Mio est épuisé ; il n'est pas repris implicitement. Une acquisition éventuellement approuvée doit confirmer tailles/identité des archives avant lecture, sans retry automatique, remplacement de cible ou dépassement.

**Brouillon public prêt à relire :** [texte exact](../outputs/motion/independent_reference_20261019/access_request_draft.txt), titre `Per-sequence access to two EVIMO2v2 eval sequences`, destination proposée : nouvelle issue publique sur [better-flow/evimo](https://github.com/better-flow/evimo/issues), avec le compte GitHub connecté. Le message donne les deux chemins et les six noms de fichiers, demande des liens par séquence/fichier et leurs tailles/empreintes ; il ne contient ni chemins locaux, résultats privés, pièce jointe ou coordonnées personnelles. **Non envoyé.** Une publication nécessite l'instruction explicite de l'utilisateur, conformément à la règle de communication externe. Le dernier bilan logiciel reste 340 tests de l'étape précédente, non réexécutés pour cette recherche documentaire.

## Protocole de validation préparé — 18 octobre 2026

**Statut : protocole préparé, nouvelle évaluation NON EXÉCUTÉE.** Le parcours DSEC, ses seuils et ses abstentions sont conservés. Les sections plus anciennes ci-dessous décrivent leur état historique ; l'ordre actuel est rapidité, fiabilité, puis 3D. Cette préparation ne rouvre pas les essais EVIMO2 clos.

### Références réellement disponibles

| Support local vérifié | Mesure permise | Conclusion non permise |
|---|---|---|
| M16 : six dates, 22 boîtes Moving ; les six indicateurs `temporal_onset_ground_truth` sont faux | Support et résidus dans les boîtes, avec réserve de parallaxe et de fond intérieur | Précision/rappel de mobilité, faux positifs hors boîte, délai de début de mouvement |
| M17 : configuration historique à intervalle 20 ms et images de 50 ms | Diagnostic de cette configuration archivée | Transférer ses AUC ou résidus au parcours actuel à intervalle 100 ms |
| Contrôles EVIMO2 sauvegardés, dont 211→217 / objet 6, split train | Erreurs de correspondance et de pose contre référence, sous les conditions oracle documentées | Test indépendant, validation routière DSEC, validation du pipeline avec profondeur prédite |
| Rejeu intégré Y01 à 17 dates | Coût, conservation des sorties, âge du contexte et abstentions | Latence capteur, délai de début de mouvement ou précision physique des candidats |

Sources : [manifeste M16](../outputs/motion/M16/audit/verified_sample.json), [configuration M17](../configs/m17_reference_diagnostic.json), [contrôle EVIMO2](../outputs/motion/M14_next_sample_20261017/pair/summary.json), [dernier contrôle intégré](../outputs/motion_publication_20261018/verification.json). Les fichiers JSON ont été relus ; aucune inférence ni nouvelle sélection n'a été exécutée pour ce protocole. Les 534 images inventoriées ne sont pas déclarées toutes alignées.

### Hypothèse à examiner avant une correction du suivi

**La compensation doit mieux séparer le mouvement indépendant du mouvement apparent que le déplacement brut, sur les mêmes correspondances évaluables.** C'est une hypothèse à tester, pas un résultat acquis. Les valeurs `residual_px` sont déjà enregistrées : aucun nouveau score appris ni seuil adaptatif n'est nécessaire pour poser cette comparaison.

- Témoin C0 : norme du déplacement observé `||q-p||` en pixels.
- Candidat C1 : résidu géométrique `||q-projection(T_est, Z_précédent, p)||`, déjà produit par le modèle accepté.
- Comparer C0 et C1 sur exactement les mêmes points et les mêmes intervalles. Publier séparément le nombre initial de graines, de suivis conservés, de profondeurs valides et de points évaluables ; l'intersection ne doit pas masquer les pertes de couverture.
- Pose refusée, profondeur absente ou suivi perdu : abstention, jamais score nul ou classe immobile. Conserver aussi les points où seul C0 est disponible dans le bilan de couverture.
- Cette comparaison concerne d'abord des points référencés. Un score médian dans une boîte est seulement exploratoire tant que l'appartenance des points à l'objet n'est pas établie. Aucun rappel d'objets ne sera calculé sans règle de regroupement et d'appariement de sorties définie à l'avance.

### Conditions obligatoires avant exécution

1. **Référence indépendante de la prédiction :** dates, repères et visibilité vérifiés ; cas positifs et négatifs explicites. Les régions non annotées et les identités zéro restent inconnues. Pour une référence dérivée de poses, examiner translation ET rotation ainsi que l'incertitude ; une origine presque immobile ne suffit pas à étiqueter l'objet statique.
2. **Sélection figée avant les résultats :** noms de séquences, dates, critères d'admission/exclusion et empreintes conservés. Les cas et ensembles déjà explorés restent du développement ; aucune nouvelle désignation rétroactive comme test indépendant. Pas de sélection d'une paire favorable après inférence.
3. **Périmètre maîtrisé :** DSEC reste le démonstrateur principal. Un contrôle oracle secondaire ne remplace pas la qualité DSEC. Aucun masque, pose ou profondeur GT ajouté au chemin de prédiction ; un calcul oracle éventuel est identifié séparément et n'est pas confondu avec C1 prédit.
4. **Paramètres figés :** mêmes fenêtres et intervalle, mêmes correspondances pour la comparaison C0/C1, aucun seuil réglé sur les résultats d'évaluation. Si un seuil de décision devient nécessaire, le choisir sur un ensemble de développement distinct puis le geler.

### Critères de décision et mesures

| Question | Mesure et règle de décision prévues |
|---|---|
| Le signal compensé discrimine-t-il mieux ? | Courbes précision-rappel/ROC et AUC sur des labels positifs/négatifs admissibles, par séquence ; gain seulement s'il dépasse l'incertitude mesurable. Aucun intervalle de généralisation fondé sur des points corrélés d'une seule paire. |
| La méthode a-t-elle seulement supprimé les cas difficiles ? | Couverture et abstentions sur l'ensemble admissible initial, en plus des métriques sur points communs. Une amélioration conditionnelle accompagnée d'une perte de couverture doit être rapportée comme compromis. |
| Une future correction du suivi aide-t-elle ? | Erreur contre déplacement de référence, nombre de correspondances correctes à ≤3 px (repère diagnostique existant), distribution des erreurs, erreurs de pose et coût. Davantage de points acceptés par LK ne suffit pas. Aucun essai de variante autorisé par ce seul document. |
| La sortie arrive-t-elle plus tôt ? | Calcul jusqu'à publication et service séquentiel complet, médiane/p95, premier appel séparé, mêmes entrées et matériel documenté. Le pas source de 20 ms reste un budget de comparaison. |
| Quel est le délai de début de mouvement ? | `NON MESURABLE` tant que l'instant de début et la première réponse correcte ne sont pas référencés. Ne pas additionner mécaniquement fenêtre 50 ms, intervalle 100 ms et coût de calcul. |

**Décision de préparation : aucune ROC, précision, rappel ou latence de début ne peut encore être annoncée à partir des seuls labels locaux DSEC vérifiés.** Il manque un protocole de référence admissible avec négatifs et séparation développement/évaluation. L'acquisition limitée autorisée ensuite est décrite ci-dessous ; elle ne suffit pas à valider les labels de chaque point suivi. Aucun entraînement, annotation manuelle, nouveau réseau ni reprise EVIMO2. Les derniers 314 tests logiciels réussis appartiennent à l'étape précédente ; cette qualification de fichiers ne les réexécute pas.

### Acquisition DSEC-MOS autorisée et réalisée — 18 octobre 2026

Après accord utilisateur, les six masques et six RGB prévus ont été acquis par plages HTTP. L'archive annonce **6 014 321 385 octets** ; seuls **12 607 641 octets de corps HTTP (12,02 Mio)** ont été lus, sondes et deux lectures d'index incluses. La première sélection a été arrêtée car l'organisation réelle est `DSEC-MOS/type/séquence/fichier`, sans dossier `training`, contrairement au schéma README. Les douze chemins autorisés étaient bien présents ; la reprise a conservé dates, périmètre et compteur cumulé. Aucune archive complète, aucun événement, aucun poids ou fichier `prior` acquis. CRC ZIP, taille et SHA-256 vérifiés pour les douze PNG. L'intégrité globale de l'archive n'a pas été contrôlée ; les SHA-256 locaux ne sont pas des signatures de l'éditeur.

**Résolution réelle : 640×440 ; masques PNG mode `1`, décodés en booléens.** Six comparaisons pixel à pixel avec les sources MOD hachées de M16 identifient exactement le recadrage `MOD[0:440, :]` ; les 40 autres décalages verticaux sont tous différents. Aucun redimensionnement ni ajustement photométrique requis. Les six dates se transfèrent par cette égalité d'image. Le mapping dans la grille M16 garde x et y, uniquement sur les 440 premières lignes : **25 600 pixels des 40 dernières lignes doivent rester non évalués**, jamais rembourrés comme négatifs. Cette égalité ne supprime pas la parallaxe entre les capteurs RGB et événementiel.

| Séquence | Image | Pixels positifs du masque | Recadrage RGB exact |
|---|---:|---:|---|
| 04_b | 1 | 8 324 | Oui, lignes 0:440 |
| 04_b | 134 | 27 213 | Oui, lignes 0:440 |
| 04_b | 267 | 20 120 | Oui, lignes 0:440 |
| 04_e | 1 | 12 135 | Oui, lignes 0:440 |
| 04_e | 134 | 1 365 | Oui, lignes 0:440 |
| 04_e | 267 | 1 815 | Oui, lignes 0:440 |

**Statut : qualification partielle de référence, aucune inférence.** Aperçu des six superpositions inspecté ; ce sont les annotations publiées, pas des sorties du détecteur. La forme plus précise des masques ne certifie ni la mobilité physique de chaque pixel, ni l'exhaustivité, ni le statut statique de tout pixel nul. Les dates sont déjà explorées en développement ; l'archive n'encode pas le split dans ses dossiers et seul le train MOD des deux séquences a été vérifié localement. Ni test indépendant, ni onset, ni pose caméra ne sont apportés par ces masques.

[Manifeste des douze fichiers](../outputs/dsec_mos_reference_20261018/acquisition_selected.json) · [Script de qualification conservé](../outputs/dsec_mos_reference_20261018/qualify.py) · [Résultats de qualification](../outputs/dsec_mos_reference_20261018/qualification.json) · [Planche de référence](../outputs/dsec_mos_reference_20261018/reference_preview.png).

**Périmètre proposé puis approuvé, conservé ci-dessous pour traçabilité :**

**Candidat : annotations DSEC-MOS**, déjà repérées dans [la bibliographie](veille_bibliographique_pfe.md). Le [dépôt officiel](https://github.com/ZZY-Zhou/DSEC-MOS) décrit des masques `gt_mask` et des RGB `image_calib`. L'[article v3, §IV-A](https://arxiv.org/html/2305.00126v3#S4.SS1) décrit leur production à partir de boîtes MOD, suivie de corrections humaines. Cela motive leur examen ; cela ne prouve ni leur alignement exact avec les événements ni leur exhaustivité. Sources consultées le 18 octobre 2026. Le lien officiel mène à une archive Google Drive ; son volume et la possibilité d'extraction partielle ne sont pas établis par la page consultée.

Proposition bornée approuvée : inspecter l'index de l'archive et, si l'accès partiel le permet, acquérir seulement les six masques et les six RGB des frames **1, 134, 267 de `zurich_city_04_b` et `zurich_city_04_e`**, sous plafond cumulé de **64 Mio transférés**. Enregistrer provenance, tailles et SHA-256 ; conserver les critères avant ouverture des prédictions. Arrêter si le serveur impose l'archive complète, si les entrées manquent ou si le plafond serait dépassé. Aucun téléchargement d'événements, poids ou séquence supplémentaire ; aucune inférence ou annotation manuelle.

Vérifier ensuite encodage/valeurs inconnues, résolution, correspondance RGB avec les dates M16, repère, bordures et limites de parallaxe. Ne pas supposer que tout zéro est un négatif physique fiable. Ces six dates restent **train/développement** : ce lot qualifie la référence, pas la généralisation, le début du mouvement ou la pose. En cas de défaut non résolu, conclure non admissible sans ajuster les seuils du détecteur. Le réseau EmoFormer associé au dataset n'est pas proposé à l'intégration.

### Support des correspondances sauvegardées — 19 octobre 2026

Contrôle exécuté sans relancer le détecteur : [script maintenu](../scripts/diagnostics/analyze_saved_mask_support.py), [résultats avec empreintes](../outputs/dsec_mos_support_20261019/verified/summary.json). Les six masques, le manifeste d'acquisition et les dates M16 sont vérifiés contre la qualification. Les snapshots de source des deux archives sont contrôlés par les SHA-256 enregistrés ; chaque inférence JSON est identique à sa copie dans le résumé original. Les nouvelles empreintes des NPZ identifient les fichiers lus aujourd'hui, sans prétendre à une signature de l'éditeur ou à un hash historique des NPZ absent des anciens manifestes.

Association uniquement par le pixel le plus proche, `floor(coordonnée+0,5)`, dans le crop 640×440. Un arrondi hors crop est inconnu ; aucun masque redimensionné ou rempli à zéro. Une frontière positive est signalée si son voisinage 3×3 contient un zéro ou sort du crop : c'est une description du raster, pas une borne de parallaxe. Les valeurs zéro restent inconnues au sens de mobilité physique.

| Résultats archivés | Suivis dans le masque positif | Profondeur/résidu évaluables | Candidats >3 px | Historique insuffisant |
|---|---:|---:|---:|---:|
| M17, intervalle 20 ms | 163 | 120 | 0 | Deux dates sur six |
| 100 ms, bord stéréo corrigé le 15 octobre | 156 | 133 | 53 | Deux dates sur six |

Les 53 occurrences résiduelles se répartissent en 21 (`04_b/134`), 31 (`04_b/267`) et une (`04_e/267`). Elles ne représentent pas 53 objets distincts ni des vrais positifs certifiés. Dans la configuration 100 ms, `04_e/134` et `04_e/267` n'ont que 5 et 4 suivis sur leurs masques, contre 72 et 75 dans `04_b`. Les régions MOS couvrent respectivement 1 365/1 815 pixels dans les deux cas `04_e`, avec 880/280 pixels d'activité courante sauvegardée : ce sont des observations de support, pas une cause unique démontrée de la perte de suivi.

À 100 ms, 35 autres candidats sont sur des pixels de masque zéro et un hors du crop. Ils ne sont pas étiquetés faux positifs. Il y a 19 suivis sur une frontière positive 3×3, dont cinq candidats ; le reste n'est pas déclaré exempt de parallaxe. Les distributions C0/C1 sont publiées **sur les mêmes points évaluables**, avec les comptes de suivis et abstentions séparés. Une diminution du résidu sur ces points ne mesure pas à elle seule une meilleure séparation mobile/statique.

La source stéréo et le protocole de suivi diffèrent entre les deux archives : aucun gain causal n'est attribué au seul passage de 20 à 100 ms. À `04_b/134`, trois tableaux et le modèle sauvegardés à 100 ms sont exactement identiques à ceux de la dernière date du démonstrateur actuel ; les autres dates ne sont pas recertifiées par cette égalité ponctuelle. Les deux premières dates restent explicitement sans historique suffisant.

**320 tests passent**, dont six nouveaux contrôles logiciels de l'analyse. Aucun coût du pipeline ni précision/rappel/ROC ou délai de début n'a été mesuré. Ce contrôle borné est clos ; il ne justifie ni baisse de seuil, ni promotion de modèle, ni répétition des essais EVIMO2. La décision suivante concerne l'admissibilité spatiale des labels, en particulier autour des candidats hors masque positif.

### Admissibilité géométrique des candidats hors masque — 19 octobre 2026

Les 35 candidats du raster zéro dans l'archive à 100 ms ont été examinés sans nouvelle inférence. Le point hors du crop reste non évalué. Leurs coordonnées, profondeurs précédentes, résidus et erreurs aller-retour sont lus dans les NPZ/JSON déjà hachés ; les calibrations correspondent aux empreintes des archives. Aucun modèle de pose n'est réajusté et aucun événement n'est relu.

Pour un point rectifié événementiel `q` à profondeur axiale courante `Z`, le passage par la vraie caméra RGB puis l'homographie de rotation donne :

```text
v = R_rect0 × rotation(T_10)ᵀ × translation(T_10)
d = (fx*v_x − (q_x−cx)*v_z, fy*v_y − (q_y−cy)*v_z)
q_MOD(Z) = q + d / (Z + v_z)
```

L'utilitaire `parallax_mask_reachability` de [mod_alignment.py](../src/pfe_events/mod_alignment.py) cherche les intersections de cette droite projective avec les carrés fermés des pixels positifs pour tout `Z>0`, sauf la singularité. Il inclut les deux branches projectives lorsque `v_z<0`, pour éviter une exclusion injustifiée. Cette enveloppe peut admettre une géométrie non visible physiquement dans RGB ; elle est donc conservatrice. Elle n'intègre pas une incertitude statistique de calibration ou de contours. La translation effective vaut environ `[-0,043668 ; 0,000531 ; -0,013577] m` dans les deux séquences.

| Date | Candidats sur raster zéro | Sans intersection pour tout Z>0 | Intersection possible |
|---|---:|---:|---:|
| 04_b / 134 | 19 | 4 | 15 |
| 04_b / 267 | 14 | 4 | 10 |
| 04_e / 267 | 2 | 1 | 1 |
| Total | 35 | 9 | 26 |

Pour neuf des 26 cas géométriquement possibles, la profondeur compatible maximale est de 0,145 à 0,487 m. Les profondeurs précédentes ne sont pas réutilisées pour accepter ou refuser cette possibilité à t. Pour les neuf sans intersection, la distance au masque varie de 0,68 à 184 px : quatre sont proches de frontières (≤5,68 px), cinq sont à au moins 66 px. Ces observations sont conditionnelles au modèle de projection et aux annotations, pas une mesure de faux positifs.

À la seule date commune `04_b/134`, l'export du démonstrateur contient déjà une disparité/prédiction courante à la date exacte. Seize des 19 candidats disposent d'une profondeur courante valide échantillonnée au pixel le plus proche. Leur reprojection associe six pixels au masque positif (profondeurs prédites environ 10,64–18,43 m). C'est une illustration de l'effet de parallaxe, pas une validation par GT ; les trois profondeurs manquantes et les autres dates restent inconnues. Aucun ajout de profondeur dans le détecteur, aucun transport temporel et aucun réglage de masque.

Les neuf sans intersection ont des erreurs aller-retour LK de 0,009 à 0,891 px (médiane 0,162 px) et des résidus de 3,35 à 40,32 px. L'aller-retour accepté ne certifie donc pas une association compatible avec cette référence ; il ne distingue pas une erreur de suivi, de pose ou de masque. Aucun verdict causal sur ces erreurs n'est produit.

**326 tests passent**, dont six nouveaux contrôles de signe/direction, rotations, branche projective, limites de profondeur, contacts de frontière et absence de translation. La formule est également vérifiée contre la chaîne complète des deux caméras sur les 16 profondeurs courantes présentes : écart maximal 3,34×10⁻¹³ px. Cette égalité confirme le calcul, pas la précision physique des entrées.

[Inspection figée](../outputs/dsec_mos_parallax_20261019/inspect_saved.py) · [Résultats par point et empreintes](../outputs/dsec_mos_parallax_20261019/summary.json) · [Vérification indépendante de l'algèbre](../outputs/dsec_mos_parallax_20261019/geometry_verification.json) · [Planche](../outputs/dsec_mos_parallax_20261019/candidates.png).

**Conclusion de ce contrôle borné :** ne pas traiter tous les pixels de masque zéro comme des négatifs physiques, ni attribuer automatiquement tous les écarts à la parallaxe. Pas de ROC/précision/rappel de mobilité, pas de nouvelle variante ni de répétition du contrôle inchangé. Les masques restent une référence de développement avec des incertitudes spatiales ; le démonstrateur et ses abstentions sont conservés.

### Contrôle ORB — autorisé, exécuté et clos sans promotion

**19 octobre : protocole préparé avant essai, puis explicitement autorisé par l'utilisateur.** Les neuf écarts géométriques DSEC n'identifient pas une cause unique. La [page de téléchargement des auteurs DSEC](https://dsec.ifi.uzh.ch/dsec-datasets/download/) ne liste pas de fichiers optical_flow pour 04_b/04_e : aucune référence de flux n'est supposée disponible pour ces séquences. Le contrôle local EVIMO2 possède déjà profondeur et poses pour examiner les correspondances. Le protocole ci-dessous est conservé tel qu'il a été proposé avant résultats ; bilan de l'essai ensuite.

**Hypothèse :** un front-end à descripteurs appariés globalement peut récupérer davantage de correspondances correctes lors du grand déplacement observé sur la paire 211→217. L'appariement ORB/Hamming réciproque est décrit dans la [documentation OpenCV](https://docs.opencv.org/4.12.0/dc/dc3/tutorial_py_matcher.html) ; cela ne démontre pas son efficacité sur nos images d'événements. Le matching réciproque n'est pas une vérité terrain de justesse, comme l'aller-retour LK. Le risque principal est une faible stabilité des descripteurs sur les contours événementiels et la perte de petites cibles/bords.

| Élément | Protocole proposé avant tout résultat |
|---|---|
| Données | Échantillon EVIMO2 existant `scene15_dyn_test_00_000000`, paire 211→217 / objet 6 ; aucune autre sélection |
| Représentation | Comptages natifs, 50 ms, échelle logarithmique historique saturant à 20 événements/pixel ; pas de récence ou fenêtre nouvelle |
| Source et destination | ORB global, budget 400 points sur chaque image ; masque et identité cible interdits en entrée |
| Filtre court | Même contrôle LK à 20 ms, niveau 2 et seuil aller-retour 1 px, appliqué aux points ORB source ; aucun niveau supplémentaire |
| Association longue | BFMatcher Hamming avec `crossCheck=True` entre descripteurs des sources conservées et des destinations ; pas de seuil de distance ajusté, pas de ratio ou filtrage GT |
| ORB | OpenCV 4.14.0 local ; nfeatures=400, scaleFactor=1.2, nlevels=8, edgeThreshold=31, firstLevel=0, WTA_K=2, HARRIS_SCORE, patchSize=31, fastThreshold=20 ; valeurs par défaut lues dans le runtime, pas ajustées sur les résultats |
| Étendue de la modification | Front-end de sélection et association comparé comme un ensemble : ce n'est pas une ablation du seul appariement sur les mêmes graines GFTT |
| Géométrie | Même distorsion/calibration, profondeur oracle et conventions du diagnostic existant ; références de pose/masques uniquement dans l'évaluation, un seul PnP avec les garde-fous inchangés |
| Comparateur | Résultats LK déjà sauvegardés du contrôle par défaut ; aucune réexécution scientifique des anciennes variantes |
| Coût | Mesurer représentation, détection/descripteurs, contrôle court, association et pose séparément ; coût CPU de ce contrôle uniquement, pas délai DSEC ni temps réel. Pas de gain de vitesse revendiqué contre un ancien chronométrage non apparié |

**Baseline lue dans `pair/support.npz`, sans inférence :** 25 correspondances évaluables, dont 20 à erreur de référence ≤3 px ; deux évaluables sur la cible, dont une ≤3 px. Ces chiffres sont conditionnels aux critères oracle déjà documentés, notamment identité concordante aux extrémités, qui ne prouve pas à elle seule la même surface visible.

**Critères fixés pour considérer la piste utile à poursuivre, sans promotion automatique :** au moins deux correspondances cibles ≤3 px, au moins 25 correspondances évaluables globales, au moins 20 correctes globales et fraction correcte au moins 20/25 sur le support évaluable. Publier aussi toutes les graines, pertes au contrôle court, appariements, identités changées/inconnues, profondeurs manquantes et visibilité non certifiée, sans masquer les abstentions. Les erreurs de pose sont rapportées si le modèle est accepté ; un modèle refusé reste refusé, sans seuil relâché. Un résultat positif reste un contrôle de développement unique, jamais une validation DSEC ou une nouvelle précision de mobilité.

**Arrêt :** un seul candidat à ce protocole, résultats conservés même négatifs. Pas de changement de paire, paramètre ORB, seuil, grille ou fenêtre après observation ; pas d'intégration DSEC pendant ce contrôle. Si l'amélioration de correspondances est absente, clore cette hypothèse. Si elle apparaît, examiner ensuite le compromis de coût avant toute décision d'intégration ; aucune supériorité de rapidité n'est présumée.

**Bilan exécuté :** 381 points ORB source, 400 destination ; 297 sources passent le contrôle court, 78 appariements Hamming réciproques sont conservés, tous dans le repère pinhole valide. Profondeur oracle exploitable pour 56 ; 23 correspondances ont une identité concordante et une référence évaluable. Seulement **deux sont à erreur ≤3 px**, contre 20/25 dans LK sauvegardé. Sur l'objet 6 : 102 graines ORB initiales, 57 après contrôle court, 20 appariements ; 12 ont une identité différente/inconnue à l'arrivée, huit sont évaluables et une seule correcte. Les sept autres erreurs évaluables de la cible vont de 11,50 à 84,05 px ; la correcte est à 2,255 px. Aucun masque cible n'a été transmis à la détection, au contrôle court ou au matcher.

Le modèle PnP est refusé (`POSE_FIT_FAILED`), sans deuxième ajustement ou seuil relâché. Les quatre critères prédéfinis échouent : cible correcte 1<2, support évaluable 23<25, correctes globales 2<20, fraction conditionnelle 2/23<20/25. Cette fraction mesure la concordance des correspondances oracle admissibles, jamais la précision de mobilité.

Coût CPU d'un appel à froid : représentation/lecture 107,65 ms ; front-end 31,10 ms, décomposé en détection/descripteurs 25,78 ms, LK court 4,70 ms et matching 0,61 ms ; chargement des cartes/échantillonnage/undistortion 8,40 ms, PnP 21,09 ms. Le coût de matching seul ne représente pas la méthode entière. OpenCV 4.14.0, 12 threads, OpenCL désactivé. Hashes/métadonnées initiaux et évaluation GT exclus de ces mesures ; pas de benchmark DSEC ni comparaison de vitesse appariée avec LK.

**333 tests passent**, dont sept tests du front-end : déplacement synthétique de 70 px, budget et unicité des matches, correspondance des indices après rejet court, images vides, absence de destination, rejets courts, entrées/options incompatibles. Le contrôle expérimental a été exécuté une seule fois ; le témoin LK provient uniquement de ses résultats sauvegardés. Entrées, événements des trois fenêtres, références et paramètres de géométrie communs sont vérifiés identiques ; les fichiers de baseline n'ont pas été modifiés. `fb_px` du candidat désigne seulement le contrôle court à 20 ms, pas une validation aller-retour de l'appariement à 100 ms.

[Protocole enregistré avant inférence](../outputs/motion/M14_next_sample_20261017/orb_protocol_20261019.json) · [Résumé et provenance](../outputs/motion/M14_next_sample_20261017/orb_20261019/summary.json) · [Comparaison et critères](../outputs/motion/M14_next_sample_20261017/orb_20261019/comparison.json) · [Illustration inspectée](../outputs/motion/M14_next_sample_20261017/orb_20261019/comparison.png).

**Décision : non promu, contrôle clos.** L'appariement réciproque fournit ici plus de matches mais beaucoup moins de correspondances correctes. Ne pas retoucher les paramètres, tester un autre descripteur ou changer de paire par défaut. DSEC garde son suivi LK et ses abstentions ; cette expérience oracle négative ne constitue pas une validation de sa mobilité.

## Historique de l'objectif — 7 octobre 2026

## Objectif concret

Localiser les objets dont le mouvement est distinct de celui du décor, y compris lorsque la caméra se déplace. Une personne qui marche, un véhicule qui roule ou un objet générique déplacé sont des cibles. Une voiture garée et un bâtiment ne deviennent pas mobiles simplement parce qu'ils produisent des événements.

Les prochaines étapes doivent améliorer cette distinction et en apporter des preuves. Les optimisations M08/M09 restent utilisables ; une nouvelle campagne de micro-optimisation ou un démonstrateur de simple activité n'est plus la priorité immédiate. YOLO, stéréo et XYZ restent des exigences du PFE, avec une place au service de cet objectif.

## État actuel vérifié

| Élément | Ce qu'il apporte | Ce qu'il ne prouve pas |
|---|---|---|
| M01/M05/M09 | Zones d'activité et variantes de calcul | Un objet bouge indépendamment de la caméra |
| M03 | Déplacement apparent global et résidus locaux | Une compensation complète de caméra ; la parallaxe reste confondante |
| YOLO Y01 | Classe et boîte d'un objet | Son état mobile ou immobile |
| Stéréo S01 | Disparité/profondeur avec abstention | Une vitesse monde ou un mouvement indépendant sans pose et temps cohérents |
| M06 | Évaluation temporelle avec incertitude | Une qualité réelle sans annotations relues |

M03 conserve des résidus dans 599/600 fenêtres, notamment sur le décor. Ce chiffre est une fréquence de sortie, pas un taux de fausses alertes. Les 129 tests du projet vérifient des contrats logiciels ; ils ne certifient pas encore la reconnaissance d'objets mobiles en scène réelle.

## M10 : prototype exécuté, validation de mobilité encore à faire

Le filtre de cohérence et persistance est implémenté et exécuté sur sept contrôles idéaux et trois extraits train. La parallaxe reste acceptée et la rotation locale peut être rejetée. Les points 1 et 4 ci-dessous restent à réaliser pour la qualité réelle ; le point 5 devient une piste prioritaire. [Résultats, images et limites M10](39_M10_MOBILE_CANDIDATES.md).

1. Constituer un petit ensemble de référence avec mouvement d'objet et mouvement de caméra distingués. Chercher d'abord les cas observables dans les clips train existants ; les cas ambigus restent inconnus. Les labels de classes DSEC ne sont pas réutilisés comme labels de mobilité.
2. Reprendre les correspondances temporelles de M03 pour estimer le mouvement apparent du décor et sa qualité. Conserver le modèle global comme référence, avec ses limites géométriques explicites.
3. Regrouper les déplacements locaux incompatibles avec le décor, puis tester leur cohérence spatiale et temporelle sur les seules fenêtres déjà reçues. Garder une sortie « candidat mobile » tant que l'origine objet n'est pas suffisamment étayée.
4. Mesurer les fausses alertes du décor, les objets manqués et le délai avec/sans cette cohérence temporelle. Une diminution du nombre de boîtes n'est pas à elle seule un progrès.
5. Si la parallaxe domine les erreurs, comparer une compensation géométrique utilisant profondeur et pose estimées. Une profondeur ou une pose GT ne peut servir qu'à un diagnostic oracle séparé, jamais être présentée comme une prédiction du pipeline.

La confirmation temporelle peut réduire les clignotements mais ajoute du délai. Elle ne supprime pas à elle seule une erreur persistante de parallaxe. Ce compromis doit être mesuré ; aucun nombre de fenêtres ni seuil de mouvement n'est déclaré optimal avant les essais train.

## Cas indispensables à vérifier

| Situation | Comportement recherché |
|---|---|
| Caméra fixe, objet immobile | Pas d'alerte mobile malgré un bruit éventuel |
| Caméra fixe, objet en déplacement | Proposition localisée puis mouvement confirmé lorsque justifié |
| Caméra en déplacement, décor immobile | Rejet du mouvement apparent du décor, ou abstention si le modèle échoue |
| Caméra et objet en déplacement | Séparation du mouvement relatif au décor |
| Objet qui s'arrête | Fin du signalement avec délai mesuré |
| Peu d'événements, occultation ou suivi perdu | État inconnu, pas une conclusion forcée « immobile » |

La rotation d'un objet peut aussi constituer un mouvement : ne pas limiter implicitement la vérité terrain au déplacement de son centre. Un objet qui sort de la zone suivie ne doit pas être interprété comme un objet qui s'arrête.

## Mesures à privilégier

- Faux signalements sur des zones de décor relues et leur durée.
- Réponses manquées et délai de première réponse sur des débuts réellement annotés, avec intervalle d'incertitude conservé.
- Maintien de l'alerte pendant une période de mouvement relue et délai d'extinction après arrêt.
- Localisation par rapport à des boîtes ou masques de référence, lorsque disponibles ; garder distincts les diagnostics par centre de ROI M06 et les mesures de détection d'objet.
- Part d'abstention, couverture, coût de calcul et âge de sortie. Un échec de suivi n'est pas un vrai négatif.

Les seuils sont définis sur train. Les trajets de validation et le test réservé ne servent pas à ajuster la méthode. Une annotation absente ne devient pas un label négatif.

## Données complémentaires : piste vérifiée, non téléchargée

DSEC reste le socle stéréo et routier. Pour lever le manque de référence de mouvement, EVIMO/EVIMO2 est une piste secondaire adaptée : le site des auteurs décrit des poses de caméra et d'objets issues de capture de mouvement, ainsi que des masques et de la profondeur. Il s'agit de scènes intérieures, ce qui limite le transfert direct aux véhicules routiers. [Site officiel EVIMO](https://better-flow.github.io/evimo/).

La documentation indique que les masques codent des identifiants d'objets et que les métadonnées contiennent les poses ; elle signale aussi un échantillonnage irrégulier de la GT lors d'occultations. Un masque d'objet ne doit donc pas être converti automatiquement en masque de mouvement instantané : vérifier poses, repères, dates et visibilité avant cette conversion. [Format officiel de la vérité terrain](https://better-flow.github.io/evimo/docs/ground-truth-format.html).

Statut : audit documentaire seulement. Aucun nouvel échantillon acquis, aucune évaluation EVIMO exécutée et aucun remplacement du dataset principal décidé. Avant acquisition : choisir un échantillon borné, vérifier taille, licence, données de pose utilisables et règles de partition.

## Livrable attendu

Un rejeu où les propositions d'objets mobiles sont distinguées de la simple activité, avec statut candidat/confirmé/inconnu, trajectoire courte si fiable et mesures de délai. Un objet non reconnu par YOLO doit pouvoir être signalé comme objet mobile de classe inconnue. Les coordonnées 3D viennent ensuite lorsque la profondeur est valide ; aucune vitesse métrique n'est affichée sans repère temporel et géométrique approprié.

Cette note fixe le recentrage. Le prototype M10 est désormais implémenté ; la séparation objet/caméra reste non résolue, comme le montre le bilan 39.
