# M14 — Échantillon EVIMO2 acquis et audité

**7 octobre 2026 — acquisition et audit réalisés ; détection de mobilité non évaluée.**

L'audit ci-dessous conserve son état historique. La reprise limitée autorisée le 16 octobre, ses conventions résolues et ses résultats sont décrits en fin de page.

## Pourquoi cette étape

L'utilisateur a demandé de sauter les annotations manuelles. Nous avons donc récupéré un petit complément public instrumenté pour préparer l'évaluation du mouvement indépendant des objets. Aucune relecture M13 n'est demandée. DSEC reste principal pour les scènes routières, la stéréo, YOLO et XYZ.

La catégorie « Motion Segmentation / Object Recognition » d'EVIMO2v2 fournit événements, masques, profondeur et trajectoires. C'est une scène d'objets proches, différente du domaine routier. L'archive gauche complète annoncée est d'environ 1,8 Go. [Source et partitions officielles](https://better-flow.github.io/evimo/download_evimo_2.html).

## Acquisition bornée et traçable

- Séquence : `left_camera/imo/train/scene13_dyn_test_02_000000`.
- Partition **train** confirmée par le répertoire de l'archive et la liste officielle. Le mot `test` dans le nom ne détermine pas la partition.
- Sélection : première séquence de l'archive, identifiée avant extraction et avant toute sortie de modèle. Aucun choix selon une performance.
- Une seule caméra acquise : ce complément n'est pas encore une expérience stéréo EVIMO.
- Taille distante vérifiée par HTTP : **1 819 418 535 octets** pour l'archive complète.
- Transfert utile de cette acquisition : **251 545 600 octets, soit 239,89 Mio**, sous une limite de 256 Mio. Les sondes préalables ont aussi lu 1 Mio et les en-têtes HTTP.
- Six fichiers extraits : **594,01 Mio** au total, sous une limite de 2 Gio. Arrêt dès leur récupération, sans télécharger le reste de l'archive.
- Sources : `dataset_events_t.npy`, `dataset_events_p.npy`, `dataset_events_xy.npy`, `dataset_info.npz`, `dataset_depth.npz`, `dataset_mask.npz`.
- Empreintes SHA256 locales des six fichiers relues et conformes. Le flux gzip étant interrompu volontairement, son contrôle final intégral n'est pas effectué. Les empreintes locales ne sont pas des sommes de contrôle publiées par le fournisseur.

Le téléchargeur refuse d'écraser une acquisition existante. Il ne matérialise que six noms autorisés et refuse les liens pour ces membres. Le manifeste d'acquisition garde l'état `ACQUIRED_UNAUDITED` de cette phase ; le résultat de l'audit est dans un fichier séparé.

Attribution : **EVIMO / EVIMO2, équipe Better Flow**, [site du jeu de données](https://better-flow.github.io/evimo/). La [page de téléchargement](https://better-flow.github.io/evimo/download_evimo_2.html) annonce **CC BY-SA 4.0** pour les données. Conserver attribution et licence lors d'une redistribution des données ou de leurs dérivés. Notre planche est une visualisation dérivée des événements et des masques ; elle ne contient pas de prédictions. La licence des données est distincte de celle du code amont.

## Résultats mesurés localement

| Contrôle | Résultat |
|---|---:|
| Résolution | 640 × 480 |
| Événements | 62 915 815 |
| Intervalle événementiel | 0,01666746 à 13,01355648 s |
| Polarités 0 / 1 | 25 915 273 / 37 000 542 |
| Dates dans `frames` | 782 |
| Paires masque/profondeur réellement disponibles | 750 |
| Dates de métadonnées sans cartes | 32 |
| Intervalle maximal entre cartes disponibles | environ 400 ms |
| Échantillons de `full_trajectory` | 2 603 |
| Pas médian de cette trajectoire | 5 ms |
| Pas maximal de cette trajectoire | 5,77 ms |
| Dates GT avec fenêtre événementielle causale complète de 20 ms | 746 |
| Identifiants non nuls observés dans les masques | 5, 6, 11, 14, 15, 22, 23, 24 |
| Identifiants visibles sans pose à la date de leur masque | 0 |

Tous les événements ont été parcourus par blocs : dates finies et non décroissantes, coordonnées dans l'image, polarités binaires. Les six empreintes ont été vérifiées. Toutes les cartes ont été chargées sans pickle et rapprochées par leur identifiant, sans supposer l'ordre des clés NPZ.

Les 30 072 enregistrements de pose disponibles passent les contrôles numériques exécutés : translations et quaternions finis, norme quaternion proche de 1, décalage pose/date de groupe inférieur à 1,1 µs. Le maximum observé est d'environ 1 µs, compatible avec les dates écrites à six décimales. Cela ne valide ni la précision physique des poses, ni leur continuité, ni la présence de chaque objet à tous les instants.

## Points à résoudre avant une mesure de qualité

1. **Masque d'identité ≠ masque de mobilité.** Un objet possède un identifiant même lorsqu'il est immobile ; la valeur zéro n'est pas automatiquement un négatif fiable. Les masques ne deviennent pas des labels « mobile » par simple seuil non nul.
2. **Repères des poses.** Selon le [format officiel](https://better-flow.github.io/evimo/docs/ground-truth-format.html#transform-convention), les objets sont exprimés vers la caméra et la caméra vers le monde. La composition à utiliser est `T_monde_objet(t) = T_monde_camera(t) @ T_camera_objet(t)`. Il reste à implémenter et tester cette composition, confirmer les unités et traiter translation, rotation, bruit et trous temporels.
3. **Calibration incohérente entre deux champs.** `D = [-0.10828, 0.206233, 0, 0]`, alors que les métadonnées indiquent `p1 = -0.000650`, `p2 = -0.000555`. Vérifier le code producteur et les repères des cartes avant de sélectionner une convention de rectification. Aucun score pixel par pixel n'est calculé à ce stade.
4. **Références incomplètes.** Les 32 dates sans cartes et le trou maximal de 400 ms sont conservés. Pas d'interpolation silencieuse ; les fenêtres sans support complet doivent rester exclues ou inconnues. Les premières et dernières dates GT ne sont pas toutes couvertes par 20 ms d'événements.
5. **Profondeur de référence.** Les valeurs stockées positives vont de 223 à 2 685 ; couverture positive médiane 50,42 %. La documentation historique indique des millimètres ; confirmer la conversion v2 avant utilisation métrique. L'utiliser dans le détecteur constituerait une expérience oracle explicitement séparée d'une profondeur prédite.

Le [format EVIMO](https://better-flow.github.io/evimo/docs/ground-truth-format.html) décrit les fichiers, l'encodage des identifiants par multiples de 1000 et les dates irrégulières. Notre audit confirme ces propriétés sur l'échantillon acquis, sans garantir leur présence sur tout le corpus.

## Code, tests et aperçu

- `scripts/download_evimo_sample.py` : téléchargement borné d'une séquence fixée.
- `src/pfe_events/evimo_reference.py` : lecteur spécialisé des métadonnées, remplaçant les constructeurs NumPy sérialisés par des conteneurs locaux inertes ; les autres classes exécutables sont rejetées. Aucun `eval` ni chargement global `allow_pickle=True`.
- `scripts/audit_evimo_sample.py` : empreintes, événements, cartes, poses et aperçu reproductible.
- `tests/test_evimo_reference.py` : huit tests supplémentaires, dont rejet d'un objet sérialisé exécutable, de cycles et de dates invalides, ainsi que limites de lecture et sélection des membres d'archive.
- **137 tests réussis**, journal : `outputs/motion/M14/tests.log`. Quatre sources et leurs snapshots sont archivés dans le rapport.

La [planche d'inspection](../outputs/motion/M14/sample_preview.png) montre trois dates fixes : première, médiane et dernière date avec support causal complet, indices 2, 375 et 779. À gauche : événements natifs accumulés sur 20 ms, échelle logarithmique fixe saturant à 20 événements/pixel. À droite : couleurs d'identité officielles, zéro en noir. Les couleurs n'indiquent pas la vitesse et les cartes ne sont pas superposées avant validation de leur repère spatial.

Artefacts : [acquisition](../outputs/motion/M14/acquisition.json), [audit détaillé](../outputs/motion/M14/audit.json). Données locales : `data/raw/evimo2v2/left_camera/imo/train/scene13_dyn_test_02_000000/`.

Pour reproduire l’audit local sans télécharger (depuis R01, choisir un dossier neuf pour préserver M14) :

```powershell
.\.venv\Scripts\python.exe scripts/audit_evimo_sample.py --output outputs/motion/M14_audit_02
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Prochaine étape

Résoudre les conventions de calibration et d'horloge, puis construire une référence de mouvement dans le repère monde à partir des poses. Vérifier aussi la rotation locale et conserver un état inconnu près des seuils ou des trous. Ensuite seulement, comparer le détecteur aux références disponibles sur train, avec couverture explicite et séparation oracle/prédiction. Aucun travail manuel d'annotation demandé à l'utilisateur. Aucune nouvelle précision, aucun rappel ni délai de détection annoncé à l'issue de M14.

## Contrôle limité avec poses de référence — 16 octobre 2026

**Périmètre explicitement autorisé :** échantillon EVIMO2 déjà acquis seulement, contrôle séparé, aucun nouveau modèle ni téléchargement de données. DSEC reste le parcours principal. Les six empreintes locales concordent avec le manifeste d'acquisition. Les images **60 et 66**, à **1,016667 et 1,116667 s**, sont fixées avant lecture des résultats ; aucun balayage de paires ni sélection selon la qualité.

### Conventions établies

- La pose caméra transforme les coordonnées caméra vers un repère fixe, celui de la caméra initiale dans le producteur. La pose objet transforme les coordonnées objet vers la caméra. Ainsi `T_monde_objet = T_monde_camera @ T_camera_objet` ; la compensation d'un point fixe est `inv(T_monde_camera_t1) @ T_monde_camera_t0`. Pour un point attaché à l'objet, la transformation complète est `T_camera_objet_t1 @ inv(T_camera_objet_t0)`. [Conventions officielles](https://better-flow.github.io/evimo/docs/ground-truth-format.html) et [export des poses](https://github.com/better-flow/evimo/blob/8897c6d9aa18384f9746b89b565d09cc7d8a059f/evimo/dataset_frame.h).
- Les dates `frames` et événements sont utilisées telles qu'exportées, sans ajout d'époque ROS ni interpolation. La tolérance de **1,1 µs** ne couvre que la sérialisation des dates de pose à six décimales. Les quaternions `w,x,y,z` doivent être unitaires à `1e-4` près ; seule cette erreur d'arrondi est normalisée.
- L'ambiguïté `D` est résolue **pour le modèle `radtan` de cet échantillon** : le convertisseur remplit `D=[k1,k2,k3,k4]`, tandis que le producteur utilise aussi `p1,p2`. Le contrôle utilise donc les paramètres nommés des métadonnées, dans l'ordre OpenCV `[k1,k2,p1,p2,k3,k4,0,0]`. `k3=k4=0` ici. [Projection du producteur](https://github.com/better-flow/evimo/blob/8897c6d9aa18384f9746b89b565d09cc7d8a059f/evimo/dataset.h) · [Convertisseur v2](https://github.com/better-flow/pydvs/blob/fa12a1434a02133321a1b03929a5383f4ec23009/samples/evimo-gen.py).
- Le producteur projette les cartes dans le repère natif avec distorsion, stocke la profondeur axiale `Z × 1000`, puis le convertisseur v2 conserve les canaux sans rectification. La profondeur est donc lue en millimètres et convertie en mètres. Elle est échantillonnée dans la carte **avant** correction de distorsion des coordonnées suivies. [Chaîne de génération v2](https://github.com/better-flow/evimo/blob/8897c6d9aa18384f9746b89b565d09cc7d8a059f/tools/evimo2_v2_generate/generate.sh). Les révisions consultées sont archivées ; la révision exacte ayant produit l'archive distribuée n'est pas connue. Le contrôle local ne mesure pas l'incertitude de calibration ou de Vicon.

### Calcul réalisé et résultats

Trois images causales de **50 ms**, aux dates `t0`, `t0+20 ms` et `t1`, utilisent une échelle logarithmique fixe saturant à 20 événements/pixel, sans ajustement sur le résultat. Les fonctions existantes de suivi LK/aller-retour et de pose sont réutilisées : graines vérifiées à 20 ms, suivi direct à 100 ms, puis **un seul ajustement PnP**. Les coordonnées suivies sont corrigées de leur distorsion avant le calcul géométrique. Cette représentation native et cette profondeur oracle diffèrent des entrées DSEC ; ce n'est pas un rejeu identique du démonstrateur routier.

| Contrôle | Résultat |
|---|---:|
| Graines initiales / après contrôle court | 400 / 384 |
| Suivis après contrôle à 100 ms | 276 |
| Hors image après correction de distorsion | 2 |
| Suivis retenus / avec profondeur | 274 / 240 |
| Même identité non nulle aux deux extrémités, avec profondeur | 237 |
| Identité nulle ou inconnue au départ / autre identité à l'arrivée | 34 / 3 |
| Déplacement de la caméra de référence | 4,607 mm ; 0,461° |
| Écart pose estimée / référence | 0,642 mm sur le vecteur translation ; 0,139° en rotation |
| Support de l'ajustement | 232/240 ; enveloppe couvrant 52,50 % de l'image |
| Résidu médian avec pose caméra de référence, sur les 237 points | 0,888 px |
| Résidu médian avec poses caméra + objet de référence, mêmes points | 0,885 px |
| Statuts du modèle estimé | 237 cohérents ; 3 candidats ; 34 inconnus |

Les déplacements des **origines d'objet** passent de **2,788–10,008 mm apparents** dans les coordonnées caméra à **0,021–0,083 mm dans le repère monde**. Les rotations monde vont de 0,0012° à 0,3331°. Ce sont des déplacements de référence sur 100 ms, pas des vitesses instantanées ni une garantie de précision submillimétrique. Aucun seuil de mobilité n'est déduit de ces petites valeurs ; une origine presque fixe ne suffit pas à exclure une rotation. Cette paire contrôle surtout la compensation caméra.

La profondeur de référence est une **entrée oracle explicitement déclarée**. Les poses caméra/objet et les masques d'identité ne sont jamais transmis à l'ajustement. L'identité zéro reste inconnue. Comparer uniquement des extrémités de même identité ne garantit ni la même surface physique ni l'absence d'occlusion. Parmi les 237 correspondances de même identité, **178 concernent l'objet 22** : leur distribution n'est pas équilibrée.

### Trois écarts qui ne disparaissent pas avec la pose de référence

| Indice sauvegardé | Aller-retour (px) | Résidu modèle (px) | Résidu poses caméra + objet GT (px) | Déplacement de projection dû au mouvement propre GT (px) |
|---|---:|---:|---:|---:|
| 48 | 0,279 | 4,967 | 4,450 | 0,094 |
| 49 | 0,548 | 6,690 | 7,411 | 0,104 |
| 99 | 0,00092 | 6,398 | 6,883 | 0,081 |

Ces trois points appartiennent à l'identité 22 aux deux dates. Le troisième a même un aller-retour presque nul malgré un écart géométrique important. **L'aller-retour ne suffit donc pas à valider une correspondance.** Le mouvement de référence de l'objet ne justifie pas ces écarts ; remplacer seulement la pose estimée ne les supprime pas. Restent à départager le suivi, le support temporel des images événementielles, l'association à la surface et les incertitudes des cartes. Les images accumulent 50 ms d'événements tandis que les cartes décrivent une date précise. Aucun candidat n'est converti en étiquette de mouvement ou de faux positif garanti.

**Décision :** conserver les seuils et le parcours DSEC. La prochaine correction doit partir de ces correspondances sauvegardées et d'une cause vérifiée, sans nouveau balayage, sans double ajustement et sans changement de paramètres fondé sur le seul nombre de candidats. Aucun score de précision/rappel, délai de début de mouvement, gain de vitesse ou validation DSEC n'est annoncé.

### Vérification et reproduction

**276 tests passent**, dont huit nouveaux tests de conventions, annulation du mouvement caméra, rotation d'objet à origine fixe, dates invalides, distorsion, projection et identités inconnues. Sur les tableaux sauvegardés, les projections sont vérifiées par `cv2.projectPoints` à **1,11 × 10⁻¹¹ px** près ; la correction puis réapplication de distorsion retrouve les points natifs à **9,10 × 10⁻¹³ px** près. Ces égalités vérifient le calcul, pas l'exactitude physique des références. Aucun second ajustement n'a été lancé pour ces vérifications.

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/check_evimo_pose.py --output outputs/motion/M14_pose_repeat
```

Choisir un dossier neuf. Les durées enregistrées proviennent d'un appel de diagnostic à froid, sans stéréo prédite ni YOLO ; elles ne sont pas comparables au budget du démonstrateur DSEC. [Résumé et protocole](../outputs/motion/M14_pose_control_20261016/summary.json) · [Tableaux](../outputs/motion/M14_pose_control_20261016/pair.npz) · [Vérifications et trois points](../outputs/motion/M14_pose_control_20261016/verification.json) · [Aperçu inspecté](../outputs/motion/M14_pose_control_20261016/preview.png) · [Tests](../outputs/motion/M14_pose_control_20261016/tests.log).

## Support spatial des trois correspondances — 16 octobre 2026

Relecture des événements des deux fenêtres originales, des correspondances et des poses sauvegardées, avec vérification des empreintes. **Aucun suivi, nouvel ajustement de pose ou changement de fenêtre**. Les trois indices sont ceux des candidats du résultat initial ; aucun autre cas choisi pour obtenir un résultat favorable.

| Point | Pixel natif dominant au départ | Événements avant / après au même pixel | Événements dans ses huit voisins, avant / après | Pixels actifs dans le bloc source 5×5 |
|---|---|---:|---:|---:|
| 48 | (587, 202) | 90 / 79 | 0 / 0 | 1 |
| 49 | (632, 183) | 42 / 42 | 0 / 0 | 1 |
| 99 | (530, 208) | 15 / 5 | 0 / 0 | 1 |

Le pixel dominant est le maximum de comptage dans la fenêtre LK native de 21×21 au départ ; ses coordonnées restent fixes pour les deux mesures. Les événements sont également comptés dans cinq sous-intervalles de 10 ms, sans changer les images suivies : leur répartition est conservée dans le JSON. La graine 49 est à six pixels du bord et sa fenêtre LK déborde aussi de l'image ; cela ne suffit pas à expliquer les deux autres cas. Les agrandissements montrent une activité ponctuelle isolée, plutôt qu'un contour local d'objet. Cette observation est compatible avec du bruit récurrent ; **elle ne constitue pas un diagnostic matériel de pixel défectueux**.

### Un seul garde-fou, sans réglage de seuil

Le mode `--inspect-tracks` du diagnostic existant teste la présence d'au moins une paire de pixels actifs **voisins au sens des huit directions**, dans le bloc natif **5×5** entourant la graine. La taille reprend le `blockSize=5` du détecteur de coins existant ; aucune recherche de taille, taux ou seuil de mobilité. Un bloc incomplet donne une abstention distincte ; aucun des 274 blocs n'est incomplet ici. Le calcul utilise exclusivement la fenêtre causale source, avant la date d'arrivée et sans référence géométrique. Les références servent ensuite à mesurer ce que le garde-fou retire.

| Support | Tous les suivis | Comparables à la référence objet | Écart GT >3 px | Écart GT ≤3 px |
|---|---:|---:|---:|---:|
| Initial | 274 | 237 | 3 | 234 |
| Conservé | 255 | 221 | 0 | 221 |
| Exclu | 19 | 16 | 3 | 13 |

Le garde-fou écarte les trois grandes erreurs observées, mais aussi **13 correspondances compatibles à 3 px**, soit **5,56 % des 234** initialement compatibles, et trois correspondances non évaluables. L'erreur moyenne du sous-ensemble conservé passe de 1,000 à 0,918 px, **par sélection du support**, pas par amélioration des coordonnées. La médiane varie très peu, de 0,885 à 0,884 px. Ce n'est ni un rappel objet ni une précision de mobilité, et cela ne prédit pas la pose qui résulterait d'un nouvel ajustement.

Un appel à froid du contrôle spatial prend **1,58 ms**, validation des entrées comprise, hors lecture et accumulation des événements. Aucun gain de temps de bout en bout n'est démontré. **280 tests passent** : quatre tests supplémentaires couvrent l'activité isolée même intense, les voisins diagonaux, les blocs incomplets/vides/invalides et le contre-exemple de la rectification.

**Décision : conserver le garde-fou uniquement dans le diagnostic.** Un pixel natif isolé peut se répartir en quatre pixels connectés par interpolation bilinéaire ; la même règle sur les images DSEC rectifiées ne vérifierait donc pas le support physique d'origine. En outre, la paire contient peu de mouvement propre et ne permet pas d'évaluer la perte de vrais points mobiles. Le prochain contrôle doit utiliser un intervalle du **même échantillon existant** choisi d'après les poses publiques avant toute prédiction, pour vérifier la conservation du support d'un objet effectivement mobile. Aucun nouveau modèle, acquisition ou balayage de paramètres requis. Les trois correspondances sont suffisamment expliquées pour ne pas répéter ce diagnostic.

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/check_evimo_pose.py --inspect-tracks outputs/motion/M14_pose_control_20261016 --output outputs/motion/M14_pose_control_20261016/track_support_repeat
```

[Mesures, coûts et protocole](../outputs/motion/M14_pose_control_20261016/track_support/summary.json) · [Agrandissements inspectés](../outputs/motion/M14_pose_control_20261016/track_support/patches.png) · [Tests](../outputs/motion/M14_pose_control_20261016/track_support/tests.log). Sources et tableaux de support conservés dans ce même sous-dossier.

## Contrôle positif et couverture des graines — 16 octobre 2026

**Sélection fixée avant prédiction :** première paire chronologique disponible espacée exactement de 100 ms, avec fenêtre source de 50 ms complète, cartes aux deux dates, déplacement d'une origine d'objet d'au moins **0,010 m dans le monde**, et masque non vide aux deux dates ; identifiants d'objet examinés dans l'ordre croissant. Le centimètre est un critère de sélection du contrôle, pas une règle de mobilité du détecteur. Aucun résultat de suivi ou de filtrage n'entre dans ce choix. [Manifeste enregistré avant exécution](../outputs/motion/M14_positive_control_20261016/selection.json).

Paire retenue : **images 68→74, 1,15→1,25 s, objet 24**. Déplacement de référence : **11,290 mm**, rotation monde **2,003°**. Le masque contient 629 pixels au départ et 1 112 à l'arrivée ; l'objet est partiellement visible au bord supérieur, dans les boîtes `[323,0,376,17]` et `[319,0,376,26]`. Cette faible visibilité limite le contrôle ; elle n'autorise pas à changer de paire après constat du résultat.

### Résultat principal : aucun point sur la cible avant le garde-fou

| Étape | Toute l'image | Objet 24 |
|---|---:|---:|
| Coins initiaux sélectionnés | 400 | **0** |
| Graines après aller-retour court | 393 | **0** |
| Suivis longs, dans l'image après correction de distorsion | 290 | **0** |
| Correspondances comparables aux références | 93 | **0** |

**Statut : `NO_TARGET_TRACKS_NOT_EVALUABLE`.** L'absence de points mobiles en entrée empêche de mesurer leur conservation par le filtre. Ce n'est pas un résultat de 100 % de conservation. Les erreurs de la cible restent `null` ; aucune précision/rappel de mobilité n'est calculée. Le contrôle utilise toujours une profondeur oracle et un seul ajustement de pose, sans réajustement après filtrage.

Sur l'ensemble de l'image, le garde-fou conserve 274/290 suivis et 86/93 références comparables ; il écarte une erreur >3 px, six correspondances ≤3 px et neuf non évaluables. Ces chiffres ne valident pas le support de l'objet mobile absent. Un appel isolé du garde-fou prend 0,658 ms, hors lecture/comptage et audit des graines ; ce n'est ni un benchmark de cadence ni un gain par rapport à l'appel précédent.

### Cause confirmée dans la sélection globale

La fenêtre source contient **104 événements sur 77 pixels actifs** du masque cible. Son absence n'est donc pas expliquée par une absence totale d'événements. Un audit relance uniquement la même extraction de coins, sans masque de référence en entrée, sans suivi ni estimation de pose supplémentaire :

- seuil de qualité relatif effectif : **0,0010923** ;
- score maximal sur le masque cible : **0,0187355** ;
- **398 pixels** du masque dépassent le seuil, avec **9 maxima locaux** avant l'espacement minimal ;
- score minimal parmi les 400 coins effectivement retenus : **0,0258952**.

Le budget global de 400 points est saturé par des coins plus forts ailleurs dans l'image. Tous les scores de la cible sont inférieurs au moins fort sélectionné. Le nombre de maxima locaux ne garantit toutefois ni leur survie à l'espacement minimal, ni un suivi valide ; la proximité du bord reste aussi une difficulté. Les masques sont utilisés pour compter la couverture après extraction, jamais pour orienter la sélection.

**Décision : garde-fou toujours non promu.** Le prochain correctif doit tester une distribution spatiale plus équilibrée du **même budget maximal de 400 points**, sur les cas figés, sans masque GT fourni au détecteur. Il devra mesurer la couverture après suivi, les erreurs et le coût ; augmenter simplement le nombre de coins irait à l'encontre de la priorité de rapidité. Aucun nouveau dataset, modèle ou intervalle choisi après prédiction.

**284 tests passent.** Les quatre nouveaux tests protègent les supports vides, la comptabilisation des bonnes correspondances perdues, le seuil strict de 3 px et un exemple synthétique où le budget global écarte une région pourtant au-dessus du seuil qualité. Les projections de référence des tableaux réels sont recoupées avec OpenCV à moins de `8,1e-12 px`, sans nouvel ajustement ; c'est une vérification numérique, pas une validation physique générale. L'aperçu de couverture a été inspecté.

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/check_evimo_pose.py --reference-selection outputs/motion/M14_positive_control_20261016/selection.json --output outputs/motion/M14_positive_repeat
```

Choisir une sortie neuve. Le résumé initial et son snapshot sont préservés ; l'audit des coins réalisé ensuite est séparé dans `coverage_audit.json`, et les exécutions futures le produisent dans le résumé. [Résumé initial](../outputs/motion/M14_positive_control_20261016/pair/summary.json) · [Audit de couverture](../outputs/motion/M14_positive_control_20261016/pair/coverage_audit.json) · [Aperçu de la cible](../outputs/motion/M14_positive_control_20261016/pair/coverage.png) · [Vérifications](../outputs/motion/M14_positive_control_20261016/pair/verification.json) · [Tests](../outputs/motion/M14_positive_control_20261016/pair/tests.log).

## Répartition spatiale à budget constant — 16 octobre 2026

Un seul essai fixé avant résultats : **grille 8×6**, sélection à tour de rôle d'un candidat par cellule occupée jusqu'à **400 points**, ordre décroissant de réponse à l'intérieur des cellules. Les cellules vides ne consomment pas de place. Les candidats proviennent du même seuil global de qualité (0,01), du même bloc de calcul (5×5) et du même espacement global (6 px). Les points retenus sont remis dans l'ordre initial de réponse pour ne pas ajouter une permutation arbitraire au solveur. Aucun masque, profondeur ou objet connu n'entre dans la sélection.

Le plafond de 400 s'applique aux points transmis au suivi. Pour constituer les listes de cellules, le mode expérimental énumère tous les candidats espacés, soit **2 388 candidats** sur l'image 68 ; ce travail supplémentaire est inclus dans le coût du sélecteur. Une grille uniforme n'assure donc ni coût identique ni présence de chaque petit objet.

| Paire | Méthode | Suivis longs | Références comparables | Écarts GT >3 px | Sélection médiane |
|---|---|---:|---:|---:|---:|
| 60→66 | Globale | 274 | 237 | 3 | 5,057 ms |
| 60→66 | Grille 8×6 | 236 | 202 | 4 | 5,615 ms |
| 68→74 | Globale | 290 | 93 | 1 | 5,119 ms |
| 68→74 | Grille 8×6 | 246 | 128 | 6 | 6,314 ms |

Les supports diffèrent : ces écarts ne constituent pas une comparaison appariée de précision de mobilité. Les **209 et 170 points source communs** aux deux méthodes, respectivement, gardent exactement les mêmes coordonnées d'arrivée. Chaque nouvelle sélection donne lieu à un seul ajustement oracle ; aucune pose n'est choisie selon le nombre d'inliers. Les médianes de coût proviennent d'un échauffement puis neuf appels alternés de chaque sélecteur sur les mêmes images. Lecture, représentation, suivi et pose sont exclus de ces temps ; aucun gain de bout en bout n'est annoncé.

**Objet 24 : toujours zéro graine et zéro suivi.** Les trois candidats de coin espacés disponibles sont `(346,7)`, `(342,1)` et `(361,4)`, classés globalement 590ᵉ, 1 040ᵉ et 1 331ᵉ. Dans leur cellule, ils sont 10ᵉ, 27ᵉ et 35ᵉ ; elle reçoit neuf places. La concurrence est donc encore présente dans la cellule. Aucun quota ni découpage n'a été modifié après cette observation. L'objet est peu visible et proche du bord ; sélectionner un de ses coins ne garantirait pas son suivi.

**Décision : essai non promu.** `TrackingConfig.selection` reste `global` par défaut ; `spatial_8x6` nécessite une activation explicite. Le démonstrateur intégré ne l'active pas. Le garde-fou de support natif reste lui aussi expérimental. Ne pas multiplier les grilles sur cette paire : avant une autre sélection, il faut établir que les trois coins de la cible sont suivables, dans un diagnostic distinct, sans alimenter le détecteur avec les masques publics.

**289 tests passent**, dont cinq nouveaux contrôlant l'identité de la sélection globale d'origine, la récupération d'une région faible synthétique à budget constant, l'espacement/ordre conservés, les cellules vides et le suivi d'une translation connue. Le succès synthétique ne remplace pas l'échec observé sur la cible réelle.

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/check_evimo_pose.py --spatial-seeds --output outputs/motion/M14_spatial_reference_repeat
.\.venv\Scripts\python.exe scripts/diagnostics/check_evimo_pose.py --reference-selection outputs/motion/M14_positive_control_20261016/selection.json --spatial-seeds --output outputs/motion/M14_spatial_positive_repeat
```

[Comparaison et chronométrages](../outputs/motion/M14_positive_control_20261016/spatial_seeds/comparison.json) · [Tableau visuel inspecté](../outputs/motion/M14_positive_control_20261016/spatial_seeds/comparison.png) · [Cas 60→66](../outputs/motion/M14_pose_control_20261016/spatial_seeds/summary.json) · [Cas 68→74](../outputs/motion/M14_positive_control_20261016/spatial_seeds/summary.json) · [Tests](../outputs/motion/M14_positive_control_20261016/spatial_seeds/tests.log).


## Suivabilité des trois coins de la cible — 17 octobre 2026

Reprise limitée explicitement autorisée par l'utilisateur. Même paire 68→74 et objet 24, mêmes trois coordonnées identifiées avant ce contrôle : `(346,7)`, `(342,1)`, `(361,4)`. Ces graines ciblées sont fournies **uniquement au diagnostic**, jamais au détecteur. La fonction LK existante est appelée une fois à 20 ms et une fois directement à 100 ms, sans ajustement de paramètres ni estimation de pose. Profondeur oracle, masques et poses évaluent ensuite les correspondances. Les projections sont recoupées numériquement avec `cv2.projectPoints`.

| Coin natif | Aller-retour à 20 ms | Aller-retour à 100 ms | Écart à la référence objet + caméra à 100 ms | Accepté |
|---|---:|---:|---:|---|
| (346,7) | 0,073 px | 25,450 px | 8,251 px | Non |
| (342,1) | 0,029 px | 7,303 px | 7,805 px | Non |
| (361,4) | 0,049 px | 11,304 px | 9,252 px | Non |

Les trois passent le contrôle court et les trois échouent au contrôle long (seuil aller-retour inchangé à 1 px). Le deuxième est également hors des limites après correction de distorsion. Les arrivées LK restent dans le masque de l'objet 24 : **conserver l'identité du masque ne garantit pas une correspondance correcte**. Deux coins passent le garde-fou de support natif ; cela ne suffit pas non plus à garantir leur suivi. Aucun suivi n'est accepté, donc aucun score de conservation du mouvement ne peut être revendiqué.

**Conclusion limitée :** récupérer ces coins par une nouvelle sélection ne suffirait pas avec le suivi direct actuel à 100 ms. Le rejet protège ici contre des écarts importants à la référence. Le passage du contrôle court n'est pas une preuve de justesse à 20 ms : les fenêtres de 50 ms se chevauchent alors de 30 ms, contrairement aux images séparées de 100 ms. La proximité du bord et le changement d'apparence événementielle sont des hypothèses, pas des causes isolées par ce seul contrôle.

**Décision :** ne modifier ni grille ni seuil, ne promouvoir aucun garde-fou. Si une correction de suivi est poursuivie, tester une seule liaison temporelle par pas courts sur cette même paire, avec contrôle de dérive final contre la référence et coût complet, avant toute intégration DSEC. Ce contrôle ne valide pas la pose caméra DSEC. **294 tests passent** ; aperçu inspecté ; sources figées conservées.

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/check_evimo_pose.py --reference-selection outputs/motion/M14_positive_control_20261016/selection.json --inspect-target-corners --output outputs/motion/M14_target_corners_repeat
```

[Résumé et mesures](../outputs/motion/M14_positive_control_20261016/target_corners_20261017/summary.json) · [Aperçu](../outputs/motion/M14_positive_control_20261016/target_corners_20261017/preview.png).


## Chaînage unique par pas de 20 ms — 17 octobre 2026

Même paire 68→74, mêmes trois graines imposées au diagnostic, mêmes fenêtres de 50 ms. Cinq appels successifs au suivi existant (20, 40, 60, 80, 100 ms), avec aller-retour ≤1 px à chaque pas ; une graine rejetée ne revient jamais. Aucun réajustement de pose, nouveau seuil ou masque fourni au suivi. Les images source/courte/finale, profondeurs oracle, projections de référence et empreintes des données sont identiques au contrôle direct sauvegardé.

| Coin | Survie native à 100 ms | Limites après correction de distorsion | Erreur finale à la référence | Décision |
|---|---|---|---:|---|
| (346,7) | Oui | Passe | **7,716 px** | Accepté par les contrôles locaux, mais écart important à la référence |
| (342,1) | Oui | Échoue | **8,387 px** | Rejeté |
| (361,4) | Non, perdu à 80 ms | Non évaluable | Non évaluable | Rejeté, jamais réintroduit |

Survivants par pas : **3, 3, 3, 2, 2** ; un seul passe aussi les limites finales. **Zéro correspondance acceptée à erreur ≤3 px.** Le chaînage fait passer une correspondance que le suivi direct rejetait, sans obtenir une précision finale satisfaisante. L'aller-retour du dernier pas (0,606 px pour le premier coin) ne mesure pas la dérive cumulée sur 100 ms. La présence dans le masque objet ne la valide pas davantage.

Coût d'un appel à froid sur ces trois graines : **43,38 ms de suivi**, **1 235,91 ms de lecture/représentation des six images**, **307,69 ms d'évaluation oracle**. Acquisition/empreintes, initialisation et rendu/export exclus. Ce n'est ni un benchmark DSEC ni une comparaison de vitesse au suivi direct, dont le précédent contrôle n'avait pas enregistré le coût.

**Décision : essai non promu, contrôle borné clos.** Pas d'intégration DSEC, pas de seuil assoupli, pas d'autre pas temporel essayé pour obtenir un résultat favorable. Ce résultat montre l'insuffisance des vérifications locales sur ce cas, sans isoler à lui seul le rôle du bord, du chevauchement des fenêtres ou de l'apparence événementielle. Conserver le suivi direct et ses abstentions ; ne pas annoncer une amélioration de mobilité. **296 tests passent**, dont non-réintroduction d'une graine rejetée et traitement d'un support vide.

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/check_evimo_pose.py --reference-selection outputs/motion/M14_positive_control_20261016/selection.json --chain-target-corners --output outputs/motion/M14_target_chain_repeat
```

[Mesures](../outputs/motion/M14_positive_control_20261016/target_chain_20261017/summary.json) · [Comparabilité vérifiée](../outputs/motion/M14_positive_control_20261016/target_chain_20261017/verification.json).


## Recherche bornée d'un contrôle mieux visible — 17 octobre 2026

Extension explicitement autorisée par l'utilisateur après clôture du chaînage. Protocole enregistré dans `outputs/motion/M14_visible_control_20261017/protocol.json` **avant lecture des masques pour la sélection** : première paire chronologique à 100 ms exacts (tolérance numérique 1e-10 s), puis identifiant d'objet croissant ; fenêtre source de 50 ms complète ; cartes aux deux dates ; déplacement monde de l'origine ≥1 cm ; au moins 1 000 pixels de masque par date ; boîte du masque à au moins 10 pixels des bords. Ces deux derniers critères servent à chercher un support plus visible, pas à définir la mobilité ni à garantir l'absence d'occlusion. Aucun résultat de suivi n'est consulté.

**Résultat : `NO_ELIGIBLE_PAIR`.** Dans la séquence locale de 782 images, 616 paires respectent l'intervalle exact ; 4 n'ont pas l'historique événementiel complet et 20 n'ont pas les cartes requises. Dans les paires restantes, 220 cas objet/intervalle dépassent le déplacement minimal : 179 échouent au critère de surface ; les 41 autres échouent à la marge au bord. Aucun cas ne satisfait tous les critères. Ce décompte décrit les critères dans cet ordre, pas des causes indépendantes.

Les six fichiers d'acquisition sont vérifiés par SHA256. **Aucun détecteur, aucun suivi et aucun ajustement de pose exécuté.** Aucun seuil relâché, aucun nouvel extrait téléchargé. Le cas 68→74 reste conservé comme échec ; une absence de candidat selon ces critères ne signifie pas absence de tout mouvement dans EVIMO2.

**Décision : clore cette recherche locale.** Le prochain contrôle mieux visible nécessiterait un autre extrait ou une nouvelle décision explicite de protocole, établie avant ses résultats. Ne pas relancer un balayage des critères sur ce même échantillon pour obtenir un cas favorable. DSEC reste inchangé. Dernière suite de tests du projet : 296 réussis ; elle n'a pas été relancée pour cette sélection de références sans modification du détecteur.

[Protocole fixé](../outputs/motion/M14_visible_control_20261017/protocol.json) · [Audit et provenance](../outputs/motion/M14_visible_control_20261017/selection_audit.json) · [Script de sélection archivé](../outputs/motion/M14_visible_control_20261017/select_reference.py).


## Autre extrait autorisé : cas admissible fixé — 17 octobre 2026

Après accord explicite pour un autre extrait, le téléchargeur choisit la **première autre séquence train dans l'ordre de l'archive officielle**, sans examiner de résultat du détecteur : `left_camera/imo/train/scene15_dyn_test_00_000000`. Plafonds fixés à 512 Mio transférés et 2 Gio extraits. Six fichiers acquis, **334 325 760 octets transférés** et **153 736 071 octets extraits** ; aucune donnée antérieure écrasée. Empreintes SHA256 des six fichiers vérifiées avant sélection. Le flux gzip reste partiel : les empreintes locales ne sont pas des signatures d'intégrité publiées par les auteurs. La première tentative sans réseau avait échoué ; la demande d'approbation automatique a ensuite échoué temporairement pour limite d'utilisation, puis la reprise autorisée a abouti.

Protocole identique à la recherche locale précédente, enregistré avant lecture des masques pour la sélection. **Premier cas admissible : images 211→217, 3,533333→3,633333 s, objet 6.** Déplacement de l'origine dans le monde **0,120452 m**, rotation **11,964°**. Masques de **5 608 et 4 853 pixels**, boîtes demi-ouvertes `[269,10,352,107]` et `[272,84,345,183]`. La marge de 10 px est satisfaite, sans prétendre garantir une absence d'occlusion.

Avant ce choix : 212 paires temporelles exactes examinées, 4 sans historique complet ; 165 cas objet/intervalle avec déplacement requis, dont 88 rejetés par surface et 76 par marge. Le 165ᵉ est retenu. **Aucun suivi, aucun détecteur, aucun ajustement de pose exécuté.** Calibration radtan lue ; aperçu événementiel avec contours de référence inspecté après sélection. Le cas précédent et ses échecs sont conservés.

**Prochaine action :** appliquer une seule fois le suivi global par défaut et le contrôle de référence existant à cette paire, avec sélection indépendante des masques. Évaluer couverture, erreur finale et abstentions avant toute correction ; ne pas choisir une autre paire selon le résultat. Cela reste un contrôle train EVIMO2 séparé, pas une validation DSEC. **297 tests passent**, dont isolation de la nouvelle séquence dans la liste de fichiers autorisés.

[Acquisition](../outputs/motion/M14_next_sample_20261017/acquired/acquisition.json) · [Sélection figée](../outputs/motion/M14_next_sample_20261017/selection.json) · [Audit](../outputs/motion/M14_next_sample_20261017/selection_audit.json) · [Aperçu des références](../outputs/motion/M14_next_sample_20261017/selection_preview.png).


## Contrôle global sur 211→217 / objet 6 — 17 octobre 2026

Une seule inférence sur la paire figée, sélection globale à 400 coins, fenêtres de 50 ms, contrôle court à 20 ms et suivi direct à 100 ms inchangés. Aucun masque ou point cible fourni au suivi. Profondeur oracle à la date source pour un seul ajustement rigide ; poses et masques utilisés pour l'évaluation, jamais pour choisir les inliers.

| Étape | Toute l'image | Objet 6 |
|---|---:|---:|
| Coins globaux initiaux | 400 | 50 |
| Contrôle court passé | 317 | 33 |
| Suivi long après limites rectifiées | 39 | 2 |
| Références comparables | 25 | 2 |

40 suivis natifs passent le contrôle long, dont un hors limites après correction de distorsion ; 26 des 39 restants ont une profondeur oracle. Les deux suivis de la cible restent sur son identité et présentent **5,079 px et 1,081 px** d'écart à la référence caméra + objet. Un seul est ≤3 px. Le passage de 33 à 2 décrit une rétention de points, **pas un rappel objet**. Le masque source contient 35 654 événements : la cible n'est pas dépourvue d'activité et la sélection initiale la couvre.

**Pose refusée : `INSUFFICIENT_RIGID_SUPPORT`.** 22 inliers sur 26 profondeurs (84,62 %), mais enveloppe spatiale de **9,592 %**, sous le minimum inchangé de 10 %. La pose n'est donc pas publiée ; erreur de pose `null`, 39 statuts de points `UNKNOWN`. Ne pas abaisser le seuil au vu de ce cas proche de la limite. L'erreur des trajectoires contre les poses publiques reste calculable indépendamment de cet ajustement refusé ; elle ne constitue pas une détection produite par le système.

Le garde-fou natif expérimental conserve les deux suivis cibles, y compris celui à 5,079 px. Sur toute l'image, il écarte deux références avec erreur >3 px mais aussi trois à erreur ≤3 px. **Non promu.** Une concordance locale ou une identité de masque n'est pas une garantie de précision.

Coût isolé à froid : lecture/représentation/suivi **184,31 ms**, cartes/échantillonnage/correction **10,14 ms**, ajustement rigide **2,39 ms** ; hors empreintes, métadonnées initiales, évaluation des références et rendu. Pas une mesure de cadence DSEC. Les projections objet sont recoupées numériquement avec OpenCV, données sauvegardées vérifiées par empreinte, aperçu inspecté. **298 tests passent**, dont verrouillage des paires, identifiants et critères des deux contrôles.

**Décision :** le contrôle mieux visible est maintenant évaluable, mais ne valide pas une détection fiable. Le blocage observable principal devient la perte de correspondances pendant le suivi long, et le support rigide restant est insuffisant. Conserver cette paire pour toute correction future, sans chercher un autre exemple favorable. Aucune modification du détecteur DSEC, des grilles ou des seuils. Ne pas relancer une inférence identique comme prochaine étape : une correction future doit viser le suivi à grand déplacement et être comparée à cette référence, avec coût et dérive mesurés.

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/check_evimo_pose.py --visible-control --output outputs/motion/M14_visible_pair_repeat
```

[Résultat](../outputs/motion/M14_next_sample_20261017/pair/summary.json) · [Vérifications](../outputs/motion/M14_next_sample_20261017/pair/verification.json) · [Aperçu](../outputs/motion/M14_next_sample_20261017/pair/preview.png).


## Un niveau de pyramide supplémentaire, non promu — 17 octobre 2026

Hypothèse fixée avant essai dans `pyramid3_protocol.json` : le déplacement de référence de la cible (environ 72 px sur les correspondances comparables du contrôle précédent) peut dépasser la capacité pratique du suivi actuel. Un seul changement : `maxLevel=3` au lieu de 2 pour les deux sens du suivi long, sans changer le contrôle court, les 317 graines, les images de 50 ms, la fenêtre LK 21×21, le seuil aller-retour de 1 px ou les contrôles de pose. Aucun déplacement de référence n'est fourni pour initialiser LK.

| Mesure | Défaut, niveau 2 | Essai, niveau 3 |
|---|---:|---:|
| Suivis conservés dans toute l'image | 39 | 26 |
| Suivis issus du masque cible | 2 | 9 |
| Références cibles comparables | 2 | 8 |
| Cibles comparables avec erreur ≤3 px | 1 | 1 |
| Cibles comparables avec erreur >3 px | 1 | 7 |
| Erreur cible médiane | 3,080 px | 5,061 px |
| Inliers / profondeurs utilisables | 22/26 | 10/21 |
| Pose publiée | Non | Non |

La neuvième correspondance issue de la cible change d'identité en arrivée et n'entre pas dans les huit comparables. Le niveau supplémentaire récupère du support apparent mais aucun point supplémentaire à erreur ≤3 px ; les supports diffèrent, donc cette table n'est pas un taux de précision objet. Le garde-fou de support natif garde les neuf suivis cibles : il ne corrige pas ce résultat.

Coût du suivi long seul sur les mêmes 317 graines : **5,155 → 5,564 ms médians**, après un échauffement puis six appels alternés par méthode. Aucun ajustement de pose répété pour ce chronométrage. Les correspondances sauvegardées de chaque méthode sont reproduites exactement, entrées et graines identiques. Ces coûts excluent lecture, représentation, stéréo, pose et rendu : aucun gain de cadence globale revendiqué.

**Décision : non promu.** `track_seeds` conserve `max_level=2` par défaut ; le niveau 3 est explicite dans le diagnostic `--visible-control --coarse-tracking`. Le démonstrateur ne l'active pas. Ne pas balayer d'autres niveaux ou fenêtres sur cette paire. La perte de précision et de support global ne justifie pas l'intégration. **299 tests passent**, dont défaut identique au niveau 2 explicite, translation connue pour les correspondances acceptées et refus des niveaux non autorisés. Le contrôle synthétique ne garantit pas la conservation de tous les points au niveau 3.

[Résultat](../outputs/motion/M14_next_sample_20261017/pyramid3/summary.json) · [Comparaison et coûts](../outputs/motion/M14_next_sample_20261017/pyramid3/comparison.json) · [Protocole antérieur au résultat](../outputs/motion/M14_next_sample_20261017/pyramid3_protocol.json).

## Image linéaire du dernier événement, non promue — 17 octobre 2026

Hypothèse enregistrée avant résultat dans `time_surface_protocol.json` : le comptage accumule les contours d'âges différents sur 50 ms. Essai unique d'une image de récence : pixel inactif = 0 ; sinon `1 + floor(254 × (dernier_timestamp - début) / 0,050)`, événements dans `[début, fin)`, polarités regroupées. Aucune constante de décroissance ajustée. La même paire 211→217 / objet 6, les fenêtres de 50 ms, le contrôle court à 20 ms, LK niveau 2, sa fenêtre 21×21 et le seuil aller-retour de 1 px sont conservés. La sélection globale à budget 400 est recalculée sur chaque représentation : comparaison de représentations complètes, pas de LK sur graines identiques. Les masques interviennent uniquement après le suivi, pour l'évaluation.

| Mesure | Comptage initial | Récence linéaire |
|---|---:|---:|
| Coins initiaux sur la cible | 50 | 39 |
| Graines cibles après contrôle court | 33 | 35 |
| Suivis cibles longs comparables | 2 | 3 |
| Erreur cible ≤3 px | 1 | 0 |
| Erreur cible >3 px | 1 | 3 |
| Suivis conservés dans toute l'image | 39 | 42 |
| Profondeurs oracle utilisables | 26 | 27 |
| Références comparables, tous objets | 25 | 25 |
| Références à erreur ≤3 px, tous objets | 20 | 20 |
| Pose acceptée par les contrôles internes | Non | Oui |

Erreurs des trois suivis cibles : **5,539 / 3,963 / 7,669 px**. Le garde-fou de support natif conserve les trois. La pose acceptée a un écart de rotation **0,270°** et de vecteur translation **4,661 mm** à la référence. Aucun seuil de réussite de pose n'avait été fixé pour ces écarts : ils sont descriptifs, pas une qualification. Une pose acceptée ne valide pas les trajectoires de l'objet ; aucun seuil existant n'a été abaissé. La médiane d'erreur globale passe de 2,235 à 1,546 px mais les points diffèrent et la cible se dégrade : ne pas retenir uniquement cette médiane favorable.

Coût mesuré avec un échauffement puis six appels alternés par méthode, sur les mêmes trois tranches d'événements en mémoire : représentation **14,22→16,68 ms**, suivi court + long et sélection **12,72→12,37 ms**, total **26,87→28,90 ms** médians. Les médianes par composant ne s'additionnent pas exactement. Le comptage nécessaire à l'audit est inclus dans les deux parcours. Lecture disque, cartes, pose, référence et rendu sont exclus ; aucune inférence sur la cadence DSEC. Les positions et erreurs aller-retour sauvegardées sont reproduites exactement à chaque appel, sans réestimer la pose. Les empreintes d'entrée, dates, événements et paramètres communs sont identiques. L'ancien rapport ne possédait pas le champ de niveau LK : sa valeur 2 a été vérifiée dans son code archivé.

**Décision : non promue.** Aucun suivi cible à erreur ≤3 px ; coût légèrement supérieur. Ce résultat ne réfute pas toutes les représentations temporelles, mais ne justifie pas cette intégration. Pas de balayage de décroissances ou de fenêtres sur la même paire. DSEC reste inchangé ; ce contrôle utilise une profondeur oracle et un cas train choisi selon des critères de visibilité, sans mesure de précision/rappel de mobilité. Aperçu inspecté. **302 tests passent**, dont causalité de la fenêtre, exclusion de sa borne droite, priorité du dernier événement, invariance aux répétitions et entrées vides/invalides.

[Résultat](../outputs/motion/M14_next_sample_20261017/time_surface/summary.json) · [Comparaison et coûts](../outputs/motion/M14_next_sample_20261017/time_surface/comparison.json) · [Protocole antérieur au résultat](../outputs/motion/M14_next_sample_20261017/time_surface_protocol.json).
