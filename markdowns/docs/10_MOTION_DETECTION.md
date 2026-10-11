# Mouvement : observable, mesure et limites

**Priorité utilisateur, 4 octobre 2026 :** la détection rapide du mouvement devient l'étape principale. M01 est implémenté et exécuté sur deux segments DSEC, à fenêtres de 10/20/50 ms. Il produit des zones d'activité sans attendre YOLO. [Algorithme, mesures et rejeu](25_M01_RAPID_ACTIVITY.md).

## Recentrage du 7 octobre 2026

La cible est désormais explicitement la détection des objets mobiles indépendamment du déplacement de la caméra. Le socle compte 129 tests réussis et les optimisations M08/M09 sont terminées ; les résultats historiques ci-dessous restent des mesures d’activité. M10 a ajouté la cohérence spatiale et trois observations consécutives sur les résidus M03. La parallaxe reste un contre-exemple accepté ; la rotation locale peut être rejetée. La distinction objet/décor reste donc à valider avant une nouvelle optimisation de coût. [Bilan M10](39_M10_MOBILE_CANDIDATES.md). [Plan opérationnel et cas indispensables](38_OBJECTIF_OBJETS_MOBILES.md).

## Deux sorties distinctes

Le MVP affiche une carte d'activité événementielle causale à cadence élevée et un score d'activité dans les ROI détectées. Cela met en évidence des changements visuels rapides. Cela ne sépare pas automatiquement mouvement d'objet, mouvement de caméra et illumination.

Une estimation facultative de déplacement relatif peut associer des boîtes de même classe entre deux dates proches par IoU et distance au centre. Une différence de positions dans le **repère caméra changeant** n'est pas une vitesse monde. Pour des vitesses métriques, il faut une pose fiable et transformer les points dans un repère commun avant différentiation ; sinon ne rapporter que le déplacement apparent et son intervalle temporel.

## Chemin léger proposé

Accumuler des fenêtres de 5 ou 10 ms dans une grille spatiale, calculer événements/(seconde×pixel) et une carte de récence. Conserver la référence temporelle exacte. Comparer l'activité d'une ROI à son voisinage et à sa propre histoire pour distinguer un changement local d'une augmentation globale. Seuils et lissage à définir sur train, avec validation séparée ; aucun seuil de mobilité n’est aujourd’hui validé.

Ne pas conditionner l'existence de cette sortie à une nouvelle inférence YOLO : sinon la latence du réseau détruit l'intérêt du chemin rapide. Si une ancienne boîte est utilisée, afficher son âge ; une boîte peut avoir quitté la ROI. Ce premier mécanisme reste un indicateur, pas un système de tracking multiobjet.

## Protocole de rapidité

Sélectionner des segments réellement présents, annoter manuellement un début observable d'activité et comparer les fenêtres 10/20/50 ms avec les mêmes règles. Mesurer délai de première réponse, taux de fausses alertes par seconde et persistance. L'incertitude de l'annotation temporelle doit apparaître ; des labels objets à faible cadence ne constituent pas une vérité terrain microseconde de début de mouvement.

Un test simulé de translation peut vérifier le calcul d'un délai, mais doit rester séparé des séquences réelles. Si aucune référence suffisamment précise n'est constituée, rapporter cadence/coût et démonstration qualitative, sans annoncer une précision de mouvement absolu.

## Références et choix

[Mitrokhin et al., CVPR 2020](https://openaccess.thecvf.com/content_CVPR_2020/html/Mitrokhin_Learning_Visual_Motion_Segmentation_Using_Event_Surfaces_CVPR_2020_paper.html) traite la segmentation de mouvement par graphe sur EV-IMO. Ce travail montre que segmenter des objets mobiles est une tâche spécifique ; nous ne réimplémentons pas ce réseau en plus de YOLO/stéréo. La [revue stéréo de Ghosh et Gallego](https://arxiv.org/abs/2409.17680) aide à distinguer les méthodes instantanées des méthodes dépendant d'une longue trajectoire caméra.

Statut : carte d'activité et zones causales **RUN — M01**. 33 tests réussis ; temps lecture/calcul mesurés. Sur validation à 10 ms : calcul médian 4,47 ms, lecture+calcul 13,38 ms ; cadence de 10 ms non soutenue par le rejeu de référence. Délai de réponse vérifié seulement sur un cas synthétique ; délai réel, fausses alertes et séparation du mouvement de caméra encore non évalués.

Suite **RUN — M02** : lecture indexée et équivalence exacte avec M01. Comparaison appariée sur validation à 10 ms : coût combiné médian 10,54→7,70 ms. Rejeu autonome indexé : 8,45 ms médiane / 11,32 ms p95. Socle actualisé à 39 tests. Aucune modification des zones ni amélioration de qualité de mouvement revendiquée ; M03 doit constituer la référence temporelle et examiner le mouvement de caméra. [Bilan M02](26_M02_INDEXED_READER.md).


## Suite M11 : compensation géométrique contrôlée

Le modèle rigide avec profondeur est implémenté et vérifié sur 135 paires 3D synthétiques. Il explique la parallaxe du contrôle, mais une profondeur biaisée ou une couche mobile dominante restent des échecs. Les références synthétiques sont explicitement oracle ; aucune inférence réelle M11 encore exécutée. [Résultats et préparation des entrées réelles](40_M11_RIGID_MOTION.md).


## Suite M12 : essai réel exécuté, mobilité encore à vérifier

Le modèle rigide reçoit désormais des correspondances rectifiées réelles et la profondeur prédite S01. 38 paires train exécutées, 58,2 % des points suivis évaluables ; les autres restent inconnus. Moins de résidus sur le support commun n'établit pas que les objets réellement mobiles sont mieux détectés. Fenêtres chevauchantes et profondeur partielle rendent nécessaire une référence relue et un contrôle du maintien des vrais mouvements. [Résultats et limites](41_M12_REAL_RIGID_MOTION.md).


## Suite M13 : interprétation temporelle et relecture

Six extraits continus non chevauchants de 20 ms sont disponibles sans prédictions. La comparaison 2×2 des durées et écarts confirme une sensibilité du suivi aux représentations temporelles ; les supports diffèrent et aucune meilleure configuration n'est démontrée. Le format de relecture sépare mouvement propre, immobilité et inconnu, sans transformer les prédictions en labels. [Vidéos et limites](42_M13_TEMPORAL_REVIEW.md).
