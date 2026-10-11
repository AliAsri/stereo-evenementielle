# Bilan simple du PFE — Deuxième réunion

**Sujet : Stéréo Vision par Caméras Événementielles pour la Détection Rapide de Mouvement**  
**Préparé le 4 octobre 2026 pour la réunion du 5 octobre 2026.**

## 1. Ce que nous cherchons à réaliser

L'objectif est de détecter rapidement les zones en mouvement à partir de deux caméras événementielles, puis d'identifier les objets et d'estimer leur position en 3D.

Ces caméras enregistrent des changements de luminosité. Une activité peut venir d'un objet qui bouge, mais aussi du déplacement de la caméra ou d'un changement d'éclairage. C'est la principale difficulté du projet.

## 2. Ce qui a déjà été fait

- Préparation de trois séquences réelles du dataset **DSEC** et vérification des deux flux de données.
- Première estimation de profondeur avec **StereoSGBM**, choisi comme méthode de référence simple avant une méthode plus complexe.
- Premier entraînement de **YOLO11n** sur des images construites à partir des événements, pour reconnaître les personnes et les voitures.
- Création d'une branche rapide d'activité, indépendante de YOLO, puis accélération de la lecture des données.
- Essais pour distinguer l'activité locale du déplacement global de la scène.
- Préparation des outils d'annotation et de mesure. **67 tests du code réussissent.**

**Aujourd'hui : les premières briques fonctionnent, mais la détection fiable du mouvement et la fusion complète en 3D restent à terminer.**

## 3. Comment expliquer les cinq images

Les numéros ci-dessous suivent l'ordre des fichiers fournis. Toutes les figures proviennent d'expériences sur des données enregistrées.

### Image 1 — Le problème du mouvement de caméra

![Image 1 — Activité à gauche et déplacements résiduels à droite](<C:/Users/moali/OneDrive/Desktop/PFE 3/docs/assets/reunion_simple/01_mouvement_global.png>)

- **À gauche :** les rectangles violets entourent des zones actives. Les arbres, bâtiments et bords de route peuvent être sélectionnés quand la caméra se déplace.
- **À droite :** après estimation du déplacement global de l'image, les points et rectangles jaunes montrent des déplacements qui restent mal expliqués par ce modèle.
- Ces zones jaunes apparaissent encore sur le décor : elles ne prouvent pas la présence d'objets mobiles indépendants.

**À dire :** « J'ai testé une première méthode pour séparer le déplacement de la caméra du mouvement local. Le décor produit encore des réponses : c'est un problème que je dois améliorer. »

### Image 2 — Ce que le modèle devrait reconnaître

![Image 2 — Annotations de référence des objets](<C:/Users/moali/OneDrive/Desktop/PFE 3/docs/assets/reunion_simple/02_annotations_reference.jpg>)

- Les huit vues montrent la scène à plusieurs instants proches.
- Les rectangles et les noms `person` et `car` sont les **annotations de référence du dataset**, affichées sur les images événementielles.
- Ils indiquent les objets attendus pour évaluer YOLO. **Ce ne sont pas les prédictions du modèle.** Les couleurs de fond représentent les événements, pas les couleurs naturelles d'une photo.

**À dire :** « Cette image montre les objets annotés dans les données. Elle sert de référence pour vérifier ce que notre modèle détecte ou manque. »

### Image 3 — Ce que YOLO détecte réellement

![Image 3 — Prédictions du pilote YOLO](<C:/Users/moali/OneDrive/Desktop/PFE 3/docs/assets/reunion_simple/03_predictions_yolo.jpg>)

- Ce sont les mêmes vues que l'image 2, avec cette fois les **prédictions de YOLO**.
- Plusieurs voitures sont détectées, mais les personnes annotées dans l'image 2 ne sont pas signalées ici.
- `car 0.8` signifie « voiture, score de confiance 0,8 ». Ce n'est pas une précision globale de 80 %.

**À dire :** « Le premier entraînement détecte certaines voitures. La comparaison avec les annotations montre qu'il manque encore des objets, particulièrement les personnes. »

Sur l'ensemble de validation du pilote de cinq époques : **mAP50 = 23,73 %**, AP50 personne = **9,49 %**, AP50 voiture = **37,97 %**. Ce sont des résultats préliminaires, pas ceux d'un modèle final.

### Image 4 — La première estimation de profondeur

![Image 4 — Événements, disparité de référence, prédiction et erreurs](<C:/Users/moali/OneDrive/Desktop/PFE 3/docs/assets/reunion_simple/04_stereo.png>)

| Partie de l'image | Explication simple |
|---|---|
| En haut à gauche | Image construite à partir des événements, après correction géométrique |
| En haut à droite | Disparité de référence fournie par le dataset |
| En bas à gauche | Disparité prédite par notre méthode StereoSGBM |
| En bas à droite | Comparaison : vert = erreur ≤ 3 pixels ; orange = erreur > 3 pixels ; rose = prédiction absente ; noir = référence absente |

La **disparité** est le décalage entre les vues gauche et droite ; elle permet de calculer la profondeur avec la calibration. Les cartes colorées affichent ici des disparités, pas directement des mètres.

Pour **cette image**, l'erreur moyenne est de **1,362 pixel**, avec **34,1 % de couverture**. Sur l'ensemble de validation stéréo évalué, les valeurs sont **1,045 pixel et 36 %**. L'erreur ne porte que sur les pixels où une prédiction et une référence sont disponibles.

**À dire :** « Nous obtenons une première estimation de profondeur, mais elle contient beaucoup de trous. La prochaine amélioration doit augmenter la couverture tout en contrôlant les erreurs. »

### Image 5 — L'animation de la branche rapide

![Image 5 — Rejeu animé des événements et de la carte d'activité](<C:/Users/moali/OneDrive/Desktop/PFE 3/docs/assets/reunion_simple/05_activite.gif>)

- **À gauche :** événements et rectangles jaunes des zones actives persistantes.
- **À droite :** carte du taux d'événements. Les couleurs chaudes indiquent davantage d'activité ; elles n'indiquent ni la vitesse d'un objet ni sa distance.
- Le calcul utilise des fenêtres de **10 ms**. Le GIF affiche des vues à **20 images/s** : c'est un rejeu, pas une preuve de fonctionnement en direct.
- Les temps affichés en bas concernent la fenêtre montrée. Sur le rejeu optimisé de validation, lecture + activité prennent **8,45 ms en médiane**, avec un p95 de **11,32 ms**.

**À dire :** « Cette branche repère rapidement l'activité sans attendre YOLO. Elle fonctionne, mais elle doit encore distinguer les objets mobiles du mouvement apparent du décor. »

## 4. Où nous en sommes et ce qui vient ensuite

Les données, la première profondeur, le pilote YOLO et la détection d'activité sont disponibles. Des seuils adaptatifs ont également été comparés : ils réduisent certaines réponses artificielles, mais peuvent aussi supprimer une activité utile lorsqu'elle dure longtemps.

Les prochaines étapes sont :

1. **Annoter et relire des exemples de mouvement** pour disposer d'une référence fiable.
2. **Mesurer les délais, les mouvements manqués et les fausses alertes**, puis comparer les méthodes.
3. **Tester l'apport de la profondeur** pour mieux distinguer le décor des objets mobiles.
4. **Associer mouvement, classe YOLO et position 3D**, puis évaluer le système complet.

Le délai réel de détection du mouvement n'est pas encore validé. La cadence complète en temps réel et les coordonnées 3D des objets ne sont pas encore démontrées.

## 5. Phrase courte pour conclure à l'oral

« J'ai construit les premières briques et obtenu des résultats sur des données réelles. Le point principal maintenant est de rendre la détection de mouvement fiable malgré le déplacement de la caméra, puis d'y associer la profondeur et l'identité de l'objet. »

**Ordre conseillé pour montrer les figures :** animation 5 → référence et prédictions YOLO 2–3 → stéréo 4 → problème de caméra 1.
