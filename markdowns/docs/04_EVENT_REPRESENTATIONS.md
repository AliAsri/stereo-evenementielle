# Représentations : choix et ablations

Les event frames logarithmiques sont maintenant implémentées et utilisées dans S01. Les autres représentations restent des variantes à tester ; aucune supériorité n'est démontrée.

| Représentation | Construction | Information conservée | Coût / risque | Usage |
|---|---|---|---|---|
| Event frame | Comptage spatial par polarité sur une fenêtre | Position, signe, quantité | O(N+HW), perd l'ordre fin ; long intervalle = traînées | MVP détection et baseline |
| Voxel grid | Répartir les événements en B cases temporelles, interpolation linéaire temporelle | Ordre temporel approximatif et localisation | O(N+BHW) ; format/normalisation dépend du modèle | Entrée du modèle profond retenu, si requise |
| Time surface | Dernier timestamp par pixel/polarité, éventuellement décroissance exponentielle | Récence locale | O(N+HW), constante de temps sensible au mouvement | Carte d'activité et ablation optionnelle |
| Reconstruction d'intensité | Réseau récurrent événements → images | Apparence reconstruite | Inférence additionnelle, artefacts, historique caché | Secours, pas le premier chemin |

La comparaison générale des familles est guidée par [Gallego et al.](https://arxiv.org/abs/1904.08405). Le voxel exact à fournir à un checkpoint sera celui de son code d'entraînement, pas une variante visuellement ressemblante.

## Représentation principale implémentée

Pour une fenêtre causale commune, calculer `C+` et `C-`, puis une pseudo-image trois canaux : `log1p(C+)`, `log1p(C-)`, `log1p(C+ + C-)`. Ce troisième canal est redondant mais permet une première adaptation d'un YOLO trois canaux sans changer l'architecture. Le registre des canaux fixe leur ordre ; ils ne représentent pas du RGB.

Pour l'entraînement, définir les facteurs de normalisation sur **train seulement**, les figer, écrêter puis convertir au format requis. Éviter la normalisation indépendante gauche/droite lorsqu'un coût stéréo compare directement les valeurs. Une normalisation par image peut servir à une figure illustrative mais doit être explicitement distinguée des données réseau.

Une image de visualisation rouge/bleu sur fond blanc est plus lisible pour l'humain ; elle ne devient pas automatiquement l'entrée d'entraînement choisie. Le script d'inspection initial produit seulement cette visualisation.

`log_channels` fixe l'ordre **positif, négatif, total** en HWC. `fit_log_normalizer` prélève au maximum 10 000 valeurs positives par canal et image, sans remise, avec seed 42 ; son percentile 99,5 % définit l'échelle, avec plancher `log(2)`. Cela évite qu'une majorité de zéros rende le percentile nul. Cet échantillonnage plafonné n'est pas le percentile exact de tous les pixels du corpus. Une image vide reste noire. `normalized_event_image` divise par les trois échelles figées, écrête dans [0,1], multiplie par 255 et arrondit en uint8.

S01 ajuste les échelles sur quatre dates uniformément réparties dans chacune des deux séquences train, avec les vues gauche/droite natives et rectifiées : 32 images de comptage au total. Échelles obtenues : **2,9957323 ; 2,5635023 ; 3,1354942**. Le fichier `outputs/stereo/S01/normalizer.json` conserve dates, indices, seed et nombre de valeurs échantillonnées. Aucun événement de validation/test ne participe à cet ajustement. Le futur export YOLO doit conserver le même ordre de canaux malgré les conventions RGB/BGR du chargeur ; ajouter un test du round-trip PNG→tenseur avant entraînement.

`rectified_counts` applique le mapping direct natif→rectifié et répartit chaque événement entre les quatre pixels voisins selon les poids bilinéaires. Les centres projetés hors de [0,W−1]×[0,H−1], ou non finis, sont rejetés. Pour les centres retenus, la somme des poids vaut un, y compris sur la frontière exacte. Le comptage se fait en float64 puis est exporté en float32. Les compteurs rectifiés ne sont donc plus nécessairement entiers. Aucun remplissage de trous n'est ajouté ensuite.

Cette règle de bord diffère légèrement de l'arrondi de D00 : un centre à −0,1 peut être arrondi à zéro pour l'inspection, mais sera rejeté pour S01. Il faut comparer les conservations avec leurs nombres de rejets respectifs. La disparition du motif de trous lié à l'arrondi ne résout pas l'absence physique d'événements ni les traînées temporelles.

## Paramètres de départ

Fenêtre 50 ms pour démarrer l'inspection ; alternatives 10, 20 et 50 ms pour l'ablation. Pas temporel et durée de fenêtre sont deux paramètres différents : une fenêtre de 50 ms décalée de 10 ms conserve une mémoire de 50 ms. La stéréo et YOLO doivent référencer la même date de sortie, même si leurs représentations diffèrent.

Pour comparer des fenêtres, affiner ou entraîner chaque modèle avec sa représentation correspondante. Changer uniquement la fenêtre au test mesure surtout un décalage de domaine, pas la supériorité intrinsèque d'une représentation.

## Tests attendus

Comptage avec plusieurs événements au même pixel, séparation des polarités, fenêtre vide, événement exactement à la borne droite exclu, frontières de bins, timestamps identiques, conservation de masse pour interpolation, absence d'overflow. Tous les exemples de ces tests doivent être étiquetés synthétiques.
