# Mesure de rapidité et ressources

## Publication avant la stéréo courante — 18 octobre 2026

Dernier contrôle dédié Y01, contexte 100 ms : calcul jusqu'aux indices de mouvement **243,23→169,58 ms médians** après déplacement de la stéréo courante après leur publication. La profondeur t−100 ms reste requise et strictement datée ; la stéréo de t est toujours calculée pour la suite et les XYZ courants. **153 tableaux et 17 lignes scientifiques identiques**, 314 tests passent. Le calcul complet passe de **246,25 à 263,42 ms** : aucune amélioration globale de débit établie. Charge et caches variables sur une seule paire de rejeux ; aucun délai de début de mouvement mesuré, mobilité non validée. Mouvement seul et calcul complet dépassent 20 ms sur 17/17 dates. [Preuves](../outputs/motion_publication_20261018/verification.json).

Dans ce parcours, `motion_ready = read_representations + motion`. `stereo` mesure la stéréo courante et l'insertion dans le cache après publication ; la stéréo historique manquante reste incluse dans `motion`. `full_pipeline` additionne lecture/représentation, mouvement, stéréo courante, YOLO et association, en excluant le coût de publication enregistré séparément. Les mesures datées ci-dessous gardent leur périmètre historique.

## Mouvement prioritaire et contexte à 100 ms — 18 octobre 2026

Choix utilisateur : mouvement prioritaire, classe et 3D moins fréquentes. Comparaison dédiée entre contexte à chaque date source (20 ms) et toutes les 100 ms dataset : **17→4 appels YOLO/XYZ**, calcul complet médian **277,63→225,14 ms**. Les images, disparités et suivis sont identiques (153 tableaux), comme les 17 modèles de mouvement et les contextes aux quatre dates communes. Le coût jusqu'aux indices de mouvement est **218,11→220,72 ms** : la baisse des appels YOLO n'accélère pas le calcul propre de cette branche. **17/17 sorties dépassent toujours 20 ms.**

`motion_ready` est un sous-coût cumulé avant publication et contexte, pas une étape à additionner aux autres. Le flux `motion.jsonl` est écrit et vidé avant le YOLO éventuel ; son coût de publication figure séparément dans chaque ligne et dans le service séquentiel complet, pas dans `full_pipeline`. Le rejeu reste séquentiel : le contexte peut retarder la date de mouvement suivante. L'âge du contexte est exprimé en temps dataset, jamais en latence système. Une médiane YOLO proche de zéro sur l'ensemble des dates signifie que 13 dates n'exécutent pas YOLO, pas que le réseau est devenu instantané. Stéréo interne toujours calculée à chaque date ; aucune profondeur ancienne réutilisée à une mauvaise date.

Comparaison unique hors ligne avec variations des autres postes/démarrage ; aucun délai physique de début de mouvement, aucun rappel des objets entre actualisations du contexte. [Preuves et métriques complètes](../outputs/motion_priority_20261018/verification.json).

## Contrôle antérieur : représentations concurrentes

**Dernier contrôle Y01 — 18 octobre 2026.** Le worker stéréo existant prépare aussi l'image événementielle droite pendant la gauche. Préparation sur entrées résidentes, 17 dates et six répétitions appariées alternées par date : **108,32→89,76 ms médians**, p95 **135,10→108,64 ms**, 306 comparaisons exactes. Ce contrôle exclut lecture, initialisation, historique, inférence et rendu. [Mesures appariées](../outputs/representation_speed_20261018/paired_representations.json).

Rejeux intégrés avant/après : lecture/représentation **118,01→108,98 ms**, calcul complet **358,81→315,65 ms** médians. 153 tableaux et 17 résultats scientifiques identiques ; **17/17 dépassements de 20 ms**, aucun gain de fiabilité de mobilité annoncé. Les autres coûts et le démarrage varient ; ne pas attribuer toute la baisse globale au parallélisme, ni utiliser le rejeu à 270 ms du 17 octobre comme contrôle de vitesse. [Comparaison et scopes](../outputs/representation_speed_20261018/verification.json).

Pic d'allocations suivi par `tracemalloc` sur une fenêtre ancre, en contrôle distinct sans chronométrage : **63,7→69,8 Mio**. Entrées et tables de rectification déjà présentes exclues ; il ne s'agit pas du RSS du processus. Aucun cache temporel supplémentaire, un seul worker persistant partagé entre les phases représentation et stéréo. [Contrôle mémoire](../outputs/representation_speed_20261018/memory.json).

**Mesures historiques par composant.** Ne pas comparer directement les millisecondes M01/M02 aux coûts du pipeline complet. Le contrôle intégré Y02 du 17 octobre mesure 257,8 ms médians après parallélisme stéréo, contre 310,5 ms avant dans sa comparaison dédiée. La stéréo passe de 111,3 à 71,9 ms. Les autres postes varient aussi ; une seule paire de rejeux ne permet pas d'attribuer tout le gain global à cette correction. Mesures hors initialisation/rendu/export, pour un pas source de 20 ms : temps réel non atteint. [Mesures actuelles et portée](20_NEXT_STEPS.md).

## Lecture indexée — mesures M02

Comparaison appariée à paramètres et fenêtres identiques, deux passages avec ordre alterné. Sur `thun_00_a` à 10 ms : lecture médiane 6,91→4,18 ms ; lecture+activité médiane 10,54→7,70 ms et p95 12,27→9,47 ms. Événements, cartes et régions identiques. Les mesures historiques M01 ci-dessous ne servent pas de dénominateur à ce gain, car les conditions de cache/charge changent.

Rejeu autonome indexé : lecture+activité médiane 8,45 ms, p95 11,32 ms, 14 % de dépassements du pas de 10 ms. Coûts hors affichage/écriture, sans YOLO ni stéréo. Le lecteur est accéléré, mais la cadence soutenue et le délai réel de détection ne sont pas garantis. [Protocole, CSV et limites](26_M02_INDEXED_READER.md).

## Priorité mouvement — mesures M01

Fenêtres causales 10/20/50 ms, deux segments de deux secondes et 200 ms de préchauffage en temps dataset. Sur `thun_00_a` à 10 ms : lecture médiane 8,85 ms, activité médiane 4,47 ms, ensemble médiane 13,38 ms/p95 16,89 ms. 99,5 % des fenêtres mesurées coûtent plus que le pas de 10 ms. À 20 ms : ensemble médiane 17,43 ms/p95 19,64 ms et 3 % de dépassements. Le lecteur disque de référence est la première cible d'optimisation.

Ces coûts excluent affichage, hash et écriture ; ils n'incluent pas YOLO/stéréo. L'attente de fenêtre et la persistance s'ajoutent au délai de réponse. L'activité visuelle n'est pas un mouvement indépendant validé. Pas de GT de début de mouvement, donc pas de délai réel ni taux de fausses alertes mesurés. [Protocole et limites](25_M01_RAPID_ACTIVITY.md).

## Quatre temps à distinguer

1. Date du phénomène et attente de la fenêtre causale : entre 0 et sa durée selon la position de l'événement ; publier la définition de l'âge considéré.
2. Calcul : lecture/décompression, filtrage, rectification, représentation, stéréo, YOLO, fusion.
3. File d'attente et transfert CPU/GPU.
4. Visualisation/encodage et écriture des résultats.

La précision temporelle d'une caméra ne garantit pas une latence de calcul microseconde. Un rejeu traite des données déjà enregistrées ; il n'inclut pas les temps matériels de capteur/USB.

## Protocole cible

Utiliser `perf_counter` pour CPU et synchroniser explicitement CUDA autour des mesures GPU isolées. Mesurer aussi la chaîne complète sans additionner naïvement des temps de branches parallèles. Distinguer premier passage (chargement, compilation, cache) et régime stable. Prévoir 20 fenêtres de warm-up puis au moins 200 mesurées, ou expliquer pourquoi la séquence est trop courte.

Enregistrer moyenne, médiane, p95, maximum, nombre de fenêtres, durée de fenêtre et pas. Publier les événements/s, le nombre total traité et le volume mémoire. Un débit de 100 fenêtres/s de 50 ms recouvrantes ne signifie pas 5 s de nouvelle scène par seconde.

Rapporter débit de calcul maximal hors temporisation et cadence de rejeu à vitesse 1×. Une interface rafraîchie à 30 Hz avec profondeur calculée à 5 Hz doit afficher l'âge de la profondeur, pas annoncer 30 FPS d'inférence 3D.

## Budget proposé

Local : conserver la lecture par tranches, éviter les copies massives, viser moins de 8 Gio de RAM de processus pour laisser de la place au système. Le budget disque initial de données est plafonné à quelques séquences, compte tenu d'environ 44,7 Gio libres observés. Colab : batch 1 pour l'audit stéréo, batch YOLO ajusté après mesure, checkpoints sur stockage persistant.

Le dossier de travail est sous OneDrive : les données peuvent être synchronisées par le client de l'utilisateur. Aucun réglage OneDrive n'est modifié ici. Pour les expériences volumineuses, un chemin de données configurable hors synchronisation pourra être préférable.

## Optimisations par ordre utile

Profilage d'abord ; lecture indexée et cache borné ; représentation vectorisée ; résolution/intervalle appropriés ; mixed precision GPU si métriques conservées ; fréquence séparée de visualisation. N'introduire ONNX ou un moteur accéléré qu'après stabilité numérique de la référence PyTorch. Ne pas optimiser une fonction qui ne contribue pas sensiblement à la latence.

La durée de lecture d'une fenêtre dans le rapport d'inspection initial est une mesure ponctuelle d'E/S, pas un benchmark de modèle. RAM, latence end-to-end et FPS stables du pipeline : **NOT RUN**. Y01 rapporte un pic de mémoire allouée PyTorch ; il ne mesure pas la VRAM totale.

## Mesures Colab Y01 reçues le 4 octobre 2026

Tesla T4 ; le CSV pilote de cinq époques termine à 102,7 s cumulées, celui du diagnostic corrigé à 117,395 s. Ces valeurs excluent notamment la préparation de session et les transferts. `pilot-metrics.json` rapporte 1 169 670 656 octets au pic d'allocation GPU PyTorch, soit environ 1,09 Gio. Ne pas en déduire une consommation totale de VRAM ou la latence événements→détection→XYZ. [Preuves et limites](24_Y01_COLAB_RESULTS.md).

## Instrumentation CPU S01, non assimilable au protocole cible

OpenCV est limité à un thread ; le traitement appelle SGBM dans les deux sens. Chaque colonne ci-dessous est une médiane indépendante sur vingt dates : ne pas les additionner pour remplacer la médiane mesurée de la chaîne.

| Séquence | Lecture paire | Représentation paire | SGBM deux sens | Reprojection | Lecture→profondeur médiane / p95 |
|---|---:|---:|---:|---:|---:|
| `04_e` | 30,5 ms | 251,8 ms | 89,1 ms | 33,3 ms | 404,4 / 549,0 ms |
| `04_b` | 27,2 ms | 256,9 ms | 90,1 ms | 32,9 ms | 405,9 / 732,8 ms |
| `thun_00_a` | 33,8 ms | 349,7 ms | 89,9 ms | 33,2 ms | 505,3 / 724,9 ms |

Ces mesures incluent le premier passage, sans warm-up dédié, et dépendent du cache disque et de la charge du poste. Elles excluent audit global, ajustement initial du normaliseur, évaluation GT, compression NPZ, PNG et interface. Aucun GPU, YOLO, modèle de mouvement ni acquisition réelle n'est inclus. Une fenêtre de 50 ms demande ici plusieurs centaines de millisecondes de calcul : **le temps réel n'est pas démontré**.

La priorité locale de profilage est la représentation : validation/comptage intermédiaire, splat bilinéaire et allocations. `rectified_counts` utilise actuellement `polarity_counts` pour valider son entrée, ce qui reconstruit des comptes natifs temporaires. Réutiliser une validation sans comptage puis comparer exactement les sorties est une optimisation possible. Elle n'a pas été appliquée à S01 ; préserver cette référence avant toute optimisation.

## Branche rapide mesurée ensuite : M02 et M03

M02 réduit la lecture sans changer les sorties : sur la comparaison appariée de validation à 10 ms, médiane lecture+activité 10,54→7,70 ms. Le rejeu autonome reste à 11,32 ms au p95 : pas de garantie de cadence 10 ms. [Mesures M02](26_M02_INDEXED_READER.md).

M03 ajoute représentation réduite, suivi de points et similarité globale. Sur six clips de deux secondes à pas de 20 ms : coût total médian de 20,02 à 37,94 ms selon le clip et p95 de 25,52 à 50,56 ms. Le suivi/ajustement seul coûte environ 8,14–8,62 ms en médiane. L'export et l'affichage sont exclus ; aucune cadence temps réel combinée n'est démontrée. Les clips diffèrent de M02 : aucune comparaison causale directe entre les deux expériences.

L'évaluateur des annotations rapporte un délai en temps des événements ; pour un délai système il faudra aussi mesurer calcul, attente et affichage. Aucun délai réel n'est encore disponible faute d'annotations relues. [Protocole M03](27_M03_GLOBAL_MOTION.md).


## M07 — Mesure réelle de l’attente pendant un rejeu cadencé

Huit passages de 12 secondes à 10/20 ms sur les deux séquences train, deux répétitions par cas. Toutes les fenêtres sont traitées ; l’âge des sorties après disponibilité est mesuré avec une horloge monotone. Sur `04_b` à 10 ms, la moyenne du service reste sous 10 ms mais les trois dernières secondes demandent en moyenne 12,21 et 11,48 ms par fenêtre : retard final 801,32 et 533,62 ms.

Le pas 20 ms réduit ce retard, avec une variabilité entre passages (âge p95 19,96 et 123,97 ms sur `04_b`). Cette mesure exclut acquisition, affichage, YOLO et stéréo. Le temps depuis le début réel du mouvement reste inconnu. [Tableau complet, définitions et limites](35_M07_PACED_REPLAY.md).


## M08 — Réutilisation des datasets HDF5

Le profilage de 300 fenêtres train montre des récupérations répétées des datasets. La nouvelle sous-classe conserve leurs quatre handles ; caches configurés de 8 Mio par champ (32 Mio au total, pas la RAM totale mesurée). Les contrôles de causalité, données et budget restent hérités.

Sur quatre cas appariés de 12 secondes, coût médian lecture + activité réduit de 8,87–14,44 %, sorties exactement identiques sur 3 660 fenêtres avec échauffement. En rejeu autonome à 10 ms, le gain d’âge des sorties varie beaucoup : sur `04_b`, p95 997,22→261,11 ms puis 358,15→351,19 ms selon la répétition. Ne pas déduire une amélioration garantie de latence de mouvement. [Tableaux complets](36_M08_CACHED_READER.md).


## M09 — Table pixel-cellule (7 octobre 2026)

Deux détecteurs comparés avec le même lecteur M08 : 3 660 sorties/états exactement identiques, calcul médian réduit de 13,07–18,14 %. La table permanente ajoute 2,344 Mio sur cet environnement 64 bits, sans mesurer la RAM totale.

L’amélioration du coût ne prouve pas celle de toutes les latences : âge p95 sur `04_b` 17,56→109,44 ms au premier passage autonome, puis 260,16→141,18 ms au second. Sur `04_e`, 14,07→8,58 ms puis 12,16→9,04 ms. Les causes de la variabilité ne sont pas isolées. Acquisition, affichage et délai depuis le début physique du mouvement exclus. [Protocole et tableaux](37_M09_LOOKUP_ACTIVITY.md).
