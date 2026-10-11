# M01 — Priorité à la détection rapide du mouvement

**Suite réalisée :** M02 accélère la lecture avec des événements et cartes identiques. Sur validation, comparaison appariée à 10 ms : 10,54→7,70 ms de coût combiné médian. Le rejeu autonome reste à 11,32 ms au p95 ; le temps réel n'est pas garanti. [Protocole et preuves M02](26_M02_INDEXED_READER.md). Les mesures M01 ci-dessous restent la référence historique.

Le 4 octobre 2026, l'utilisateur demande de concentrer le projet sur la détection rapide du mouvement. Y02 (entraînement YOLO plus long) est reporté dans l'ordre des priorités. YOLO, la stéréo et XYZ restent des exigences du PFE ; leur rôle est de compléter une réponse événementielle rapide par une classe et une position, sans bloquer cette réponse.

## Ce qui est réellement implémenté

`src/pfe_events/motion.py` propose des zones d'activité sans utiliser de classe, poids YOLO, boîte annotée ou profondeur GT. Une activité provenant d'un camion peut donc contribuer au signal même si le détecteur YOLO ne possède pas de classe camion. Cela ne garantit pas la localisation correcte du camion : le module regroupe des zones actives, pas des objets sémantiques.

Le module traite la vue gauche native avec des fenêtres causales contiguës `[début, fin[`. Chaque mise à jour produit une carte de taux d'événements, un masque de cellules actives et des rectangles autour de composantes connexes. Les paramètres sont fixés avant les essais réels et ne sont pas ajustés sur leurs résultats :

| Paramètre | Valeur M01 | Rôle |
|---|---:|---|
| Taille des cellules | 16 × 16 pixels | Réduire le coût du regroupement spatial |
| Seuil d'activité | 20 événements/(s·pixel) | Comparer les fenêtres dans la même unité |
| Support spatial minimal | 4 pixels distincts par cellule | Rejeter un pixel isolé très actif |
| Persistance | 20 ms de fenêtres candidates | Réduire les activations brèves |
| Taille minimale d'une zone | 2 cellules connexes, voisinage 8 | Écarter une cellule isolée |
| Activité étendue | ≥60 % des cellules candidates | Indicateur de répartition, sans compensation caméra |

La persistance est mesurée par fenêtres : deux fenêtres de 10 ms, une de 20 ms ou une de 50 ms. Elle ne prouve pas une activité continue durant chaque microseconde. Une cellule doit satisfaire seuil et support dans chaque fenêtre ; elle est réinitialisée immédiatement sinon. Une absence d'activité peut aussi correspondre à un objet peu contrasté ou dont les événements sont insuffisants.

Le taux utilise l'aire réelle des cellules, y compris si une dimension du capteur n'est pas divisible par 16. Aucun événement daté à la borne droite n'est accepté dans la fenêtre courante. Une fenêtre non contiguë est une erreur ; créer un nouveau détecteur pour un autre segment.

## Ce que cela mesure, et ce que cela ne mesure pas encore

Les capteurs événementiels répondent aux changements de luminosité. Séparer les événements associés à des objets mobiles de ceux produits par le déplacement de la caméra est un problème supplémentaire. Sources primaires consultées : [présentation des caméras événementielles, UZH](https://rpg.ifi.uzh.ch/research_dvs.html), [conduite et mouvement indépendant, UZH](https://rpg.ifi.uzh.ch/research_driving.html).

Dans M01, la causalité et le coût de calcul sont mesurés. Le module ne compense pas le mouvement de caméra, ne mesure pas de vitesse et ne confirme pas qu'un objet bouge dans le monde. Les boîtes orange du rejeu sont des **zones d'activité**, pas des détections YOLO ni des objets mobiles validés. Le seuil d'activité étendue ne suffit pas à reconnaître le mouvement de caméra : un tel mouvement peut n'activer qu'une partie de la scène texturée.

## Protocole exécuté

Deux séquences déjà présentes : `zurich_city_04_b` (train/debug) et `thun_00_a` (validation). Segment de deux secondes centré selon les bornes temporelles du fichier, précédé de 200 ms de préchauffage en temps dataset. Les segments sont choisis avant observation des résultats et sans lire les annotations d'objets. Le test réservé n'est pas ouvert.

Trois fenêtres/pas non recouvrants : 10, 20 et 50 ms. Même intervalle mesuré pour les trois tailles de chaque séquence : 14 709 193 événements sur `04_b`, 24 549 628 sur `thun_00_a`. Au total, 748 fenêtres traitées, dont 680 chronométrées après préchauffage. Pas d'entraînement ni de recherche de seuils.

L'exécution CPU est un rejeu disque sans temporisation : coût de lecture (recherche des bornes, décompression, vérification) et coût d'activité (validation, comptes et zones) sont mesurés séparément. L'affichage, les hashes et les écritures sont exclus. OpenCV utilise un thread ; NumPy conserve sa configuration. Les effets du cache et de l'ordre fixe 10→20→50 ms restent possibles. Deux secondes par séquence donnent une première mesure, pas un benchmark représentatif.

## Mesures obtenues

Temps en millisecondes ; les médianes de colonnes distinctes ne doivent pas être additionnées à la place de la médiane directement mesurée.

| Séquence | Fenêtre | Nombre mesuré | Activité médiane | Lecture + activité médiane | Lecture + activité p95 | Part dépassant le pas |
|---|---:|---:|---:|---:|---:|---:|
| `04_b` | 10 ms | 200 | 3,51 | 10,93 | 13,51 | 84,5 % |
| `04_b` | 20 ms | 100 | 4,93 | 13,12 | 16,91 | 0 % |
| `04_b` | 50 ms | 40 | 7,88 | 20,84 | 31,71 | 0 % |
| `thun_00_a` | 10 ms | 200 | 4,47 | 13,38 | 16,89 | 99,5 % |
| `thun_00_a` | 20 ms | 100 | 5,89 | 17,43 | 19,64 | 3 % |
| `thun_00_a` | 50 ms | 40 | 10,61 | 30,24 | 36,98 | 0 % |

La branche de calcul seule est légère par rapport à la lecture disque, mais le rejeu séquentiel de référence ne soutient pas la cadence de 10 ms sur ces segments. Une simulation de file d'attente à vitesse 1×, utilisant les durées mesurées et l'arrivée de chaque fenêtre à sa borne finale, donne jusqu'à 757,65 ms de retard de complétion sur `thun_00_a` à 10 ms. Ce retard est **simulé**, pas mesuré sur un capteur ou un rejeu réellement temporisé. L'affichage et les autres branches du PFE ne sont pas inclus.

Avec 20 ms, le coût mesuré devient généralement inférieur au pas sur ces segments. C'est un point de comparaison utile, pas une validation du temps réel global. Le délai entre début d'un mouvement et alerte inclut également l'attente de fenêtre, la règle de persistance et toute file d'attente.

## Inspection visuelle et limites observées

Des zones sont proposées dans 100 % des fenêtres mesurées, avec environ 34 % des cellules retenues en moyenne sur la validation à 10 ms. Cela ne constitue pas un taux de vrais positifs. Le montage inspecté montre de grandes zones sur les bordures et le décor ; il illustre la difficulté liée au déplacement de la caméra, sans en isoler quantitativement la cause.

![Exemple réel, activité native et grille](../outputs/motion/M01/thun_00_a/10ms/example.png)

Le [rejeu GIF de validation](../outputs/motion/M01/thun_00_a/10ms/replay.gif) couvre deux secondes, avec 40 images affichées à 20 Hz. Le calcul avait une fenêtre de 10 ms ; l'affichage ne montre qu'une mise à jour sur cinq. Il s'agit d'un rejeu précalculé, pas d'une inférence en direct.

Sans annotations temporelles de début de mouvement et de segments négatifs, le délai réel de détection et les fausses alertes par seconde restent **non mesurés**. Les champs correspondants sont `null`, pas zéro. Les annotations de classes du dataset ne remplacent pas cette vérité terrain.

## Vérifications et preuves

33 tests réussis, dont six nouveaux contrôles : début d'activité synthétique et persistance, bruit d'un pixel isolé, rejet d'événements futurs et de fenêtres disjointes, conservation des comptes et aire des cellules de bord, activité étendue, invalidité des entrées. Dans le cas synthétique, activité à 5 000 µs et première zone à 20 000 µs : réponse en 15 ms de temps simulé, sans coût de calcul ni extrapolation au réel.

Les 748 cartes NPZ ont été relues pour vérifier le nombre d'événements reconstitué depuis les taux, les timestamps contigus et la proportion de cellules actives. Les six CSV, les GIF et les hashes du code sont contrôlés. [Rapport principal](../outputs/motion/M01/summary.json) · [vérification](../outputs/motion/M01/verification.json). Les CSV distinguent préchauffage et mesures ; les paramètres et versions sont conservés dans les JSON.

## Prochaine étape centrée sur le sujet

1. Améliorer la lecture temporelle et vérifier l'équivalence exacte avec le lecteur de référence avant de revendiquer 10 ms soutenues. Préserver les mesures M01.
2. Constituer des segments annotés : début observable de mouvement, incertitude, négatifs, activité du décor et cas de mouvement de caméra. Définir les métriques de délai et fausses alertes sur ces références.
3. Tester un estimateur de mouvement apparent global et une activité résiduelle locale. Évaluer ses échecs (profondeurs différentes, parallaxe, éclairage) avant d'appeler les zones « objets mobiles indépendants ».
4. Associer ensuite la classe YOLO et la profondeur stéréo aux zones, avec timestamps, âge et abstention. Une classe inconnue ne doit pas empêcher la première réponse d'activité.

Y02 et l'extension à la classe camion ne sont pas les prochaines actions. Ils pourront améliorer la description sémantique une fois cette chaîne de mouvement mesurable.
