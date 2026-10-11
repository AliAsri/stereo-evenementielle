# Associer les boîtes à des coordonnées 3D

## Ce que le point représente

Le résultat sera un **point représentatif de surface visible** dans le repère gauche rectifié, accompagné d'un statut et d'une dispersion. Une boîte 2D et une profondeur médiane ne déterminent pas le centre physique d'un objet ni ses dimensions 3D. Afficher explicitement le repère : X vers la droite, Y vers le bas, Z vers l'avant. La distance radiale `sqrt(X²+Y²+Z²)` diffère de la profondeur axiale Z.

## Association proposée

**Implémentée le 11 octobre 2026** dans `src/pfe_events/object_surface.py` et exécutée sur le rejeu décrit dans [20_NEXT_STEPS.md](20_NEXT_STEPS.md). Il s'agit d'une association géométrique fonctionnelle ; sa précision sur les surfaces d'objets n'est pas encore évaluée.

1. Ramener la boîte YOLO de sa taille d'entrée à l'image native, en retirant padding et facteur de redimensionnement.
2. Construire une ROI intérieure, par exemple les 60 % centraux de largeur/hauteur ; fraction à régler sur train/debug, puis à figer avant évaluation sur validation.
3. Transformer **les pixels de la ROI** par la carte native → rectifiée et ne garder que les coordonnées finies et dans le champ.
4. Échantillonner disparité/masque au plus proche voisin pour la première version, puis dédupliquer les pixels rectifiés afin de ne pas les surpondérer.
5. Rejeter les disparités invalides, les profondeurs hors plage et les points de faible confiance si la méthode fournit une confiance exploitable.
6. Calculer médiane et MAD des profondeurs, retirer les valeurs manifestement éloignées, puis vérifier nombre minimum, taux de support et dispersion relative.
7. Choisir parmi les points retenus celui proche de la profondeur médiane et du centre géométrique de la ROI, puis le reprojeter avec Q. Ce choix fournit un vrai rayon observé plutôt qu'un centre de boîte mélangé à une profondeur étrangère.
8. Retourner XYZ et diagnostic ou `insufficient_depth`, jamais une profondeur par défaut.

Cas MAD nul : ne pas diviser par zéro ; garder les valeurs dans une tolérance de profondeur minimale explicite. Une médiane peut encore sélectionner le fond si l'objet n'occupe qu'une petite partie de la ROI. La fraction intérieure et le rejet statistique ne sont pas un masque de segmentation.

## Formules

Avec intrinsics rectifiés compatibles : `X=(u-cx)*Z/fx`, `Y=(v-cy)*Z/fy`. Pour convertir vers la caméra native gauche : `P_native = R_rect0.T @ P_rectified`. Ne pas annoncer des coordonnées monde sans pose caméra. La forme Q est préférable lorsque les points principaux diffèrent. Voir [géométrie](06_STEREO_VISION.md) et [profondeur](07_DEPTH_ESTIMATION.md).

## Expérience principale de valeur ajoutée

Comparer pixel central, médiane ROI et sélection robuste sur **les mêmes détections**. Mesurer erreur de profondeur de surface là où une référence est disponible, couverture de sorties et temps additionnel. Une réduction d'erreur au prix d'une forte abstention doit être visible. Ne pas nommer « erreur de centre 3D d'objet » une comparaison à une surface LiDAR ; la GT de centre 3D n'est pas établie pour le protocole DSEC choisi.

## Paramètres de la première intégration

ROI intérieure de 60 %, au moins 12 pixels et 10 % de support, profondeur entre 1 et 80 m. Abstention si l'écart interquartile divisé par la médiane dépasse 0,35. Rejet au-delà de `max(0,25 m, 3 × MAD)` autour de la médiane, puis nouvelle vérification du support. Ce sont des paramètres de démonstration fixés avant le rejeu, sans optimisation ni validation de leur qualité.

L'API Ultralytics restitue directement les boîtes dans l'image native passée à `predict` ; aucun second retrait de padding n'est appliqué. La carte DSEC transforme les pixels intérieurs, puis les pixels rectifiés sont dédupliqués. La profondeur stéréo est recalculée à la date de détection ; l'association refuse une profondeur d'une autre date. Les numéros de détection dans l'affichage sont propres à chaque image, sans suivi d'identité.

Neuf tests passent : surface de géométrie connue, profondeur périmée/future, manque de support, valeur aberrante avec MAD nul, mélange de deux profondeurs, profondeur invalide, boîtes invalides/hors champ, carte décalée/dupliquée et association des points de mouvement dans le bon repère. Les 45 XYZ du rejeu ont aussi été contrôlés par les formules calibrées indépendamment de la fonction Q. Ce contrôle vérifie le calcul, pas l'appartenance réelle de la surface à l'objet. Les comparaisons de méthodes proposées plus haut restent différées.
