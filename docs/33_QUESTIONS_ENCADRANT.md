# 50 questions possibles de l'encadrant et réponses proposées

**Projet : Stéréo Vision par Caméras Événementielles pour la Détection Rapide de Mouvement**  
**Préparation de la deuxième réunion — 5 octobre 2026**

Questions et réponses adaptées à l’état du projet au 4 octobre 2026, après M05. Les réponses sont formulées pour l’oral : adapte-les à tes mots et assure-toi de pouvoir expliquer les notions. Elles distinguent les résultats obtenus des travaux encore prévus ; elles ne remplacent pas une validation de l’encadrant.

**À préparer en premier si le temps est court : questions 1, 3, 5, 21, 25, 28, 31, 38, 41 et 46.**

## A. Compréhension du sujet et objectif

### 1. Comment expliquerais-tu ton sujet de PFE en une minute avec tes propres mots ?

**Réponse proposée :** Je cherche à repérer rapidement un mouvement à partir de deux caméras événementielles, puis à associer aux régions détectées une classe d'objet et une position 3D. Les premières briques fonctionnent sur DSEC. Le principal problème à résoudre est de distinguer le mouvement d'un objet du déplacement apparent du décor lorsque la caméra bouge.

### 2. Quel problème concret ton système doit-il résoudre et dans quelle situation pourrait-il être utilisé ?

**Réponse proposée :** Le problème est de signaler un mouvement utile avec peu de retard, sans multiplier les fausses alertes. Une application possible serait la perception embarquée d'un véhicule ou d'un robot. Pour l'instant, je travaille sur le rejeu de données enregistrées ; je n'ai pas validé une application embarquée ni un usage de sécurité.

### 3. Quelle est la différence entre détecter un objet, détecter de l'activité et détecter un objet qui bouge indépendamment de la caméra ?

**Réponse proposée :** Détecter un objet consiste à le localiser et à lui attribuer une classe, même s'il est immobile. Détecter de l'activité consiste à repérer des changements dans les événements. Détecter un objet mobile indépendant exige en plus de distinguer son mouvement de celui produit par la caméra. Mon détecteur d'activité ne suffit donc pas encore à cette troisième tâche.

### 4. Quelle contribution personnelle souhaites-tu démontrer au-delà de l'utilisation de méthodes existantes comme YOLO et StereoSGBM ?

**Réponse proposée :** La contribution visée est une chaîne causale évaluée, avec une branche d'activité rapide, une gestion du mouvement de caméra et un enrichissement par la profondeur et YOLO. Je veux mesurer le compromis entre délai, détections manquées et fausses alertes, ainsi que l'apport de la stéréo. Je ne prétends pas avoir inventé YOLO ou StereoSGBM, ni avoir déjà démontré un gain scientifique final.

### 5. Qu'as-tu réellement réalisé depuis notre première réunion, et quelle partie n'est encore qu'une proposition ?

**Réponse proposée :** Les données ont été préparées, la synchronisation et la géométrie contrôlées, une profondeur stéréo évaluée et un pilote YOLO entraîné. La branche d'activité, son lecteur accéléré et deux variantes adaptatives ont également été exécutés. En revanche, la qualité réelle du mouvement, la fusion XYZ des objets et le démonstrateur complet restent à valider.


## B. Caméras événementielles

### 6. Comment fonctionne une caméra événementielle par rapport à une caméra classique ?

**Réponse proposée :** Une caméra classique produit des images à une cadence donnée. Une caméra événementielle signale, pixel par pixel et de façon asynchrone, des variations de luminosité qui dépassent un seuil. Elle ne produit donc pas directement une suite d'images RGB classiques ; nous construisons des représentations adaptées aux algorithmes utilisés.

### 7. Quelles informations contient un événement et que signifie sa polarité ?

**Réponse proposée :** Un événement contient généralement une position x et y, une date t et une polarité p. La polarité indique le sens du changement de luminosité, augmentation ou diminution. Elle ne représente ni la couleur d'un objet ni la direction de son déplacement.

### 8. Quels avantages attends-tu des caméras événementielles pour la rapidité, et quelles difficultés introduisent-elles ?

**Réponse proposée :** J'attends surtout de leur fonctionnement asynchrone une information temporelle fine et la possibilité d'une réponse rapide. Les difficultés sont le bruit, le débit variable, le manque d'information dans certaines zones et la confusion entre objet, caméra et éclairage. La rapidité potentielle du capteur ne garantit pas celle de notre traitement : elle doit être mesurée sur toute la chaîne.

### 9. Pourquoi un objet immobile peut-il générer des événements lorsque la caméra se déplace ?

**Réponse proposée :** Quand la caméra bouge, l'image d'un objet immobile se déplace sur le capteur. Les contours passent devant différents pixels et produisent des variations de luminosité. Un arbre ou un bâtiment fixe peut ainsi générer beaucoup d'événements sans bouger dans le monde.

### 10. Pourquoi construire des images à partir des événements alors que le capteur fournit des données asynchrones ?

**Réponse proposée :** YOLO et StereoSGBM utilisent des représentations sous forme d'images. L'accumulation des événements dans une courte fenêtre permet de réutiliser ces méthodes et de construire une première référence expérimentale. En contrepartie, elle regroupe des dates différentes et peut créer des traînées ; le choix de la fenêtre doit donc être évalué.


## C. Dataset et organisation des données

### 11. Pourquoi as-tu choisi DSEC comme premier dataset plutôt qu'un autre jeu de données ?

**Réponse proposée :** DSEC permet de travailler avec une paire de flux événementiels, une calibration, des références de disparité et des annotations d'objets. Cela convient à la préparation d'une chaîne stéréo et de détection dans un même cadre de données. Sa limite pour mon objectif est que les annotations utilisées ne donnent pas directement les débuts de mouvement indépendant dont j'ai besoin.

### 12. Quelles données de DSEC utilises-tu réellement : événements, calibration, annotations d'objets et références de disparité ?

**Réponse proposée :** J'utilise les événements gauche et droite, leurs informations temporelles, la calibration et les cartes de rectification. Les disparités de référence servent à évaluer la profondeur prédite ; les boîtes et classes servent à entraîner ou évaluer YOLO selon la partition. La profondeur de référence n'est pas présentée comme une prédiction du système.

### 13. Comment as-tu réparti les séquences entre entraînement, validation et test pour éviter de mélanger des scènes trop proches ?

**Réponse proposée :** Les séquences zurich_city_04_e et zurich_city_04_b servent à l'entraînement et au débogage ; thun_00_a sert à la validation locale. Les subdivisions du même groupe 04 restent ensemble pour limiter les fuites entre trajets proches. La séquence de test réservée n'a pas été acquise ni utilisée. Les derniers rejeux adaptatifs M05 utilisent uniquement 04_b, côté train.

### 14. Pourquoi les trois séquences actuelles ne suffisent-elles pas à démontrer que le système fonctionne dans des situations routières variées ?

**Réponse proposée :** Les données sont peu diversifiées et de nombreuses fenêtres proches montrent presque la même scène. Les deux séquences d'entraînement appartiennent au même groupe de trajet et la validation ne couvre qu'une séquence. Les résultats vérifient donc surtout le fonctionnement du pilote ; il faudra davantage de trajets et de situations pour juger la généralisation.

### 15. Les annotations d'objets de DSEC permettent-elles de connaître directement l'instant où un objet commence à bouger ?

**Réponse proposée :** Non : les boîtes et classes utilisées indiquent où se trouvent des objets à certaines dates, pas le moment exact où ils démarrent. L'apparition d'un objet dans l'image ne prouve pas non plus qu'il vient de commencer à bouger. Il faut une annotation temporelle spécifique, avec une incertitude et des cas exclus lorsque le mouvement n'est pas observable.


## D. Préparation des événements et architecture

### 16. Comment passes-tu des événements bruts aux images utilisées par YOLO et par la stéréo ?

**Réponse proposée :** Je sélectionne les événements d'une fenêtre et les accumule spatialement. Pour YOLO, la représentation utilise trois canaux liés aux événements positifs, négatifs et totaux, avec transformation logarithmique et normalisation définie sur train. Pour la stéréo, les événements sont ramenés dans la géométrie rectifiée. Ces représentations sont des images d'événements, pas des photographies RGB.

### 17. Comment vérifies-tu que les fenêtres gauche et droite correspondent au même intervalle de temps ?

**Réponse proposée :** Les timestamps sont remis dans une horloge commune en tenant compte de l'offset propre à chaque fichier. J'utilise ensuite les mêmes bornes temporelles pour les deux flux et je contrôle l'ordre des événements ainsi que la plage commune disponible. Je ne réaligne pas arbitrairement chaque flux sur son premier événement, car cela pourrait modifier leur synchronisation.

### 18. Comment t'assures-tu qu'une sortie du système n'utilise aucun événement futur ?

**Réponse proposée :** Chaque fenêtre inclut son début et exclut sa fin, et le lecteur ne fournit que les événements appartenant à cet intervalle. Le détecteur conserve uniquement son état passé ; dans la variante historique, le seuil est calculé avant l'actualisation de l'historique. Les tests vérifient notamment le rejet d'un événement futur et l'absence de modification d'état après cette erreur.

### 19. Pourquoi tester des fenêtres de 10, 20 et 50 ms, et quel compromis attends-tu entre quantité d'information et délai ?

**Réponse proposée :** Une fenêtre courte permet des mises à jour fréquentes, mais contient parfois trop peu d'événements pour produire une réponse stable. Une fenêtre longue apporte davantage de support, mais mélange plus de temps et peut accentuer les traînées. Je compare 10, 20 et 50 ms pour mesurer ce compromis, sans supposer à l'avance que la plus courte sera toujours la meilleure.

### 20. Pourquoi avoir séparé la branche rapide d'activité, YOLO et la stéréo au lieu d'attendre tous les résultats avant chaque sortie ?

**Réponse proposée :** La branche d'activité doit pouvoir répondre sans attendre les traitements plus lourds. YOLO ajoute la classe et la stéréo ajoute la profondeur à une cadence qui peut être différente. Cette architecture nécessite de conserver les dates, l'âge et la validité de chaque sortie. Le fonctionnement complet avec ces échanges n'est pas encore démontré.


## E. Stéréo et profondeur

### 21. Comment obtiens-tu la profondeur à partir de deux caméras, et quel est le rôle de la disparité, de la focale et de l'écartement des caméras ?

**Réponse proposée :** La stéréo cherche des correspondances entre les vues gauche et droite. Leur décalage est la disparité d. Dans le cas rectifié simplifié, la profondeur suit Z = f × B / d, où f est la focale en pixels et B l'écartement des caméras en mètres. Le code utilise la calibration et la matrice de reprojection Q pour respecter la géométrie réelle ; une disparité invalide ne doit pas devenir une profondeur arbitraire.

### 22. À quoi servent la calibration et la rectification avant de comparer les vues gauche et droite ?

**Réponse proposée :** La calibration décrit les paramètres internes des caméras et leur position relative. La rectification transforme les vues pour faciliter la recherche des correspondances le long de lignes épipolaires, généralement horizontales. Sans une géométrie cohérente, une disparité peut être incorrecte même si l'image obtenue semble plausible.

### 23. Pourquoi avoir commencé avec StereoSGBM plutôt qu'avec un réseau de stéréo profonde ?

**Réponse proposée :** StereoSGBM fournit une première méthode de référence sans entraînement GPU. Cela permet de vérifier la lecture, la rectification, les unités, les masques et l'évaluation avant d'ajouter la complexité d'un réseau profond. Cette référence a une couverture limitée et un coût CPU élevé ; elle sert de point de comparaison, pas de solution finale déclarée.

### 24. Dans la figure stéréo à quatre panneaux, comment distingues-tu les données d'entrée, la référence, la prédiction et les erreurs ?

**Réponse proposée :** En haut à gauche se trouvent les événements rectifiés ; en haut à droite, la disparité de référence. En bas à gauche se trouve notre prédiction SGBM. En bas à droite, le vert indique une erreur au plus égale à trois pixels, l'orange une erreur plus grande, le rose une prédiction absente et le noir l'absence de référence. Les cartes colorées représentent la disparité, pas directement des mètres.

### 25. Comment interprètes-tu une erreur moyenne de disparité de 1,045 pixel alors que seulement 36 % des pixels de référence ont une prédiction valide ?

**Réponse proposée :** L'erreur de 1,045 pixel est calculée seulement là où une prédiction et une référence valides sont disponibles. La couverture de 36 % signifie qu'environ 64 % des pixels de référence n'ont pas de prédiction retenue. Le score est donc conditionnel et ne démontre pas une profondeur dense de bonne qualité. Je rapporte aussi les absences et dois étudier les causes de cette faible couverture.


## F. YOLO et entraînement

### 26. Pourquoi avoir choisi YOLO11n et limité le premier pilote aux personnes et aux voitures ?

**Réponse proposée :** YOLO11n est un premier détecteur de petite taille permettant de limiter le coût du pilote. Les personnes et les voitures ont été retenues pour contrôler l'intégration sur un périmètre réduit. Ce choix ne couvre pas toutes les classes : un camion n'est pas appris comme une classe dédiée dans ce modèle. La détection d'activité reste indépendante de ce choix de classes.

### 27. Comment as-tu préparé les 774 images événementielles et vérifié que leurs boîtes d'annotation étaient correctement placées ?

**Réponse proposée :** Les images ont été construites depuis les événements et associées aux annotations natives, avec 536 images train et 238 de validation. L'export contient 4 235 boîtes personne/voiture. Les contrôles ont porté sur les coordonnées, l'ordre des canaux, les transformations du chargeur et la correspondance aux annotations source ; certaines images ont aussi été régénérées pour vérifier leur identité.

### 28. Pourquoi le diagnostic atteint-il 99,5 % d'AP50 par classe sur huit images d'entraînement alors que la mAP50 du pilote sur validation est de 23,73 % ?

**Réponse proposée :** Les 99,5 % proviennent d'un test de mémorisation : les mêmes huit images servent à apprendre et à mesurer le diagnostic. Cela vérifie que le modèle peut apprendre ce petit lot, pas qu'il généralise. Les 23,73 % de mAP50 concernent le pilote sur une autre séquence de validation. La différence montre pourquoi il faut séparer intégration, mémorisation et performance sur des données nouvelles.

### 29. Que peux-tu conclure après seulement cinq époques, et pourquoi faut-il aussi compter les mises à jour réelles de l'optimiseur ?

**Réponse proposée :** Les cinq époques donnent une première référence, mais ne permettent pas d'affirmer que le modèle a atteint son potentiel. Avec l'accumulation des gradients, un mini-batch ne correspond pas toujours à une mise à jour de l'optimiseur, et le warm-up modifie cette cadence. Pour ce pilote, une simulation du code donne 58 appels sous les hypothèses normales, mais ce n'est pas un compteur runtime enregistré. Le prochain essai devra journaliser les pas réels et les courbes.

### 30. Quelles hypothèses pourraient expliquer les résultats plus faibles sur les personnes que sur les voitures, et comment les vérifierais-tu ?

**Réponse proposée :** Les personnes peuvent être petites, avoir peu de support événementiel ou être moins bien représentées dans le petit corpus. La durée de fenêtre, les traînées et le budget d'entraînement peuvent aussi intervenir. Je dois examiner les erreurs par taille et par scène, puis tester des modifications contrôlées. Je ne peux pas attribuer la faiblesse à une seule cause avec les résultats actuels.


## G. Détection d'activité et mouvement

### 31. Dans l'animation, que représentent exactement les rectangles jaunes et la carte colorée, et prouvent-ils la présence d'objets mobiles ?

**Réponse proposée :** Les rectangles jaunes regroupent des cellules dont l'activité dépasse un seuil et persiste suffisamment. La carte colorée montre le taux d'événements par cellule : elle n'indique ni une vitesse ni une distance. Le décor, l'éclairage et le mouvement de caméra peuvent aussi produire ces réponses. Ce sont donc des propositions d'activité, pas des objets mobiles confirmés.

### 32. Comment fonctionnent le seuil d'activité, les cellules de 16×16 pixels et le support spatial minimal de M01 ?

**Réponse proposée :** L'image est divisée en cellules de 16×16 pixels. M01 calcule un taux d'événements rapporté au temps et à la surface, avec un seuil de 20 événements par seconde et par pixel. Il exige aussi au moins quatre pixels actifs dans une cellule, une persistance de 20 ms et au moins deux cellules connexes pour former une région. Ces conditions limitent certains bruits, sans séparer le mouvement de caméra.

### 33. Pourquoi ajouter une persistance temporelle, et pourquoi une persistance configurée à 20 ms ne correspond-elle pas forcément à un délai de détection de 20 ms ?

**Réponse proposée :** La persistance évite de retenir trop facilement des réponses très brèves. Mais l'implémentation additionne la durée complète des fenêtres qualifiées, même si le signal commence au milieu de la première. Le délai après le début réel dépend donc aussi de sa position dans la fenêtre et du seuil. Les contrôles montrent notamment qu'une configuration de persistance à 20 ms peut produire une réponse après 15 ms.

### 34. Comment ton modèle global tente-t-il d'expliquer le déplacement de la scène, et pourquoi reste-t-il des réponses sur le décor ?

**Réponse proposée :** Le prototype suit des points entre deux représentations successives et ajuste un modèle global de translation, rotation et échelle. Les déplacements mal expliqués deviennent des candidats résiduels. Un seul modèle ne décrit pas toutes les profondeurs ni toute la parallaxe ; des erreurs de suivi peuvent aussi subsister. Des résidus sur la route ne prouvent donc pas qu'elle bouge indépendamment de la caméra.

### 35. Comment la profondeur stéréo pourrait-elle aider à distinguer le mouvement apparent du décor de celui d'un objet ?

**Réponse proposée :** La profondeur, associée à une estimation du mouvement de caméra et à la calibration, permettrait de prévoir une partie du déplacement apparent d'une scène statique. On pourrait comparer ce déplacement attendu au déplacement observé. La profondeur seule ne suffit pas, et sa faible couverture actuelle limite cette approche. L'apport doit encore être mesuré face à la variante sans profondeur.


## H. Lecture critique des résultats et des figures

### 36. Parmi les deux mosaïques YOLO présentées, laquelle montre les annotations de référence et laquelle montre les prédictions du modèle ?

**Réponse proposée :** La mosaïque avec les noms person et car sans scores est celle des annotations de référence. La mosaïque avec des étiquettes comme car 0.8 montre les prédictions de YOLO sur les mêmes vues. Il faut les comparer pour identifier des objets manqués ou des boîtes discutables. Je ne dois pas présenter les annotations du dataset comme un résultat du modèle.

### 37. Que signifie l'étiquette « car 0.8 », et en quoi ce score diffère-t-il de la précision, du rappel et de la mAP ?

**Réponse proposée :** Car 0.8 est le score de confiance associé par le modèle à cette proposition de voiture. Ce n'est ni une garantie de probabilité calibrée ni une précision globale de 80 %. La précision mesure la part des détections retenues qui sont correctes, le rappel la part des objets de référence retrouvés. L'AP résume la courbe précision-rappel pour une règle de correspondance, et la mAP moyenne les AP selon les classes et le protocole.

### 38. Pourquoi des zones résiduelles dans 599 fenêtres sur 600 ne permettent-elles pas d'annoncer directement un taux de fausses alertes ?

**Réponse proposée :** Le nombre 599 sur 600 indique seulement la fréquence des fenêtres contenant une proposition résiduelle. Pour parler de fausse alerte, il faut savoir si un mouvement cible était réellement présent à cette date et à cet endroit. Les annotations relues nécessaires ne sont pas encore disponibles. Ce résultat signale une difficulté du prototype, sans fournir un taux de fausses alertes.

### 39. Qu'apportent les 486 contrôles artificiels de M04 et les 306 comparaisons de M05, et quelles conclusions sur les scènes réelles ne permettent-ils pas de tirer ?

**Réponse proposée :** M04 vérifie les effets des fenêtres, seuils et persistances sur des sources d'activité dont le début est connu. M05 compare M01 aux variantes relative et historique, avec des facteurs perturbateurs supplémentaires. Ces contrôles mettent en évidence des comportements et des échecs reproductibles. Ils ne simulent pas physiquement toute une scène et ne démontrent ni le rappel ni le délai réel sur DSEC.

### 40. Si l'historique réduit fortement le nombre de zones affichées mais finit aussi par absorber une activité persistante, comment décider si la méthode est réellement meilleure ?

**Réponse proposée :** Il faut examiner les détections manquées et la durée du signalement, pas seulement compter les zones restantes. Dans le contrôle de source moyenne persistante à 10 ms, l'historique conserve la première réponse, mais ne signale la ROI que dans environ 9,7 % des sorties après début, contre 97,3 % pour la référence. Je conserve donc cette variante comme expérience ; sa réduction des sorties ne prouve pas une meilleure qualité globale.


## I. Rapidité, tests et reproductibilité

### 41. Quelle différence fais-tu entre le coût de calcul, le délai après le début réel du mouvement et la cadence d'affichage du GIF ?

**Réponse proposée :** Le coût de calcul mesure le temps passé à traiter les données, avec un périmètre précisé, par exemple lecture plus activité. Le délai de détection commence au début réel du mouvement et peut inclure attente de fenêtre, persistance, calcul et file d'attente. La cadence du GIF décrit seulement la visualisation du rejeu, ici 20 images par seconde. Ces trois grandeurs ne sont pas interchangeables.

### 42. Avec 8,45 ms de temps médian et 11,32 ms au p95 pour des fenêtres de 10 ms, peux-tu garantir un fonctionnement continu à 100 sorties par seconde ?

**Réponse proposée :** Non. Une médiane sous 10 ms ne garantit pas que toutes les fenêtres seront traitées à temps ; dans ce rejeu, 14 % dépassent 10 ms. Si le traitement prend du retard, une file d'attente peut se former. Il faut mesurer la stabilité sur une durée plus longue, la politique de traitement et la latence complète avant d'annoncer 100 sorties par seconde garanties.

### 43. Comment as-tu obtenu le gain d'environ 27 % sur la lecture et l'activité, et comment as-tu vérifié que les sorties restaient identiques ?

**Réponse proposée :** Le lecteur optimisé utilise l'index temporel disponible pour réduire le travail nécessaire à la localisation des événements, avec contrôles des bornes et repli si nécessaire. Sur la comparaison appariée de validation à 10 ms, la médiane lecture plus activité passe de 10,54 à 7,70 ms, soit environ 27 % de moins. Les événements et les sorties ont été comparés sur 1 496 paires de fenêtres et sont identiques dans ces contrôles.

### 44. Que vérifient les 67 tests automatisés, et quelles propriétés du système restent à mesurer sur des données réelles ?

**Réponse proposée :** Les tests couvrent notamment les limites temporelles, la lecture, la géométrie, les représentations, le support spatial, la persistance et les métriques. Ils contrôlent aussi l'historique causal, l'abstention et certains facteurs perturbateurs artificiels. Les 67 tests réussis ne prouvent pas une bonne détection des objets dans la réalité. Le rappel, les fausses alertes et le délai réel nécessitent encore une référence annotée.

### 45. Comment un autre étudiant pourrait-il reproduire tes expériences en tenant compte du matériel, des versions logicielles, des paramètres et des données utilisées ?

**Réponse proposée :** Les données et les partitions sont décrites par des manifestes ; les paramètres, versions et commandes sont documentés. Les résultats sont archivés avec le code exécuté et des empreintes de fichiers, et les scripts demandent un dossier neuf pour une nouvelle expérience. Il faut aussi préciser le matériel, le périmètre des chronométrages et les effets possibles du cache. Les mesures CPU locales et GPU Colab doivent rester séparées.


## J. Évaluation future et prochaines étapes

### 46. Quelle est la prochaine expérience prioritaire et quel résultat mesurable souhaites-tu présenter à la prochaine réunion ?

**Réponse proposée :** La priorité est d'obtenir un petit ensemble d'annotations réelles relues, comprenant des débuts observables et des zones négatives. Je pourrai ensuite comparer les variantes avec des mesures de réponse et de fausses alertes, en conservant l'incertitude des annotations. Le livrable visé est un premier tableau de qualité sur des scènes réelles, accompagné d'exemples de réussites et d'échecs, plutôt qu'une simple réduction visuelle du nombre de boîtes.

### 47. Comment vas-tu annoter les débuts de mouvement, traiter les cas incertains et constituer des exemples négatifs sans te laisser guider par les prédictions ?

**Réponse proposée :** L'outil montre les clips sans prédictions. Il permet de choisir une zone et un intervalle de début possible/certain, ou de signaler un cas négatif, déjà mobile ou incertain. Je dois examiner tout le clip, éviter de confondre entrée dans le champ et démarrage, puis faire relire les annotations. Une zone non annotée n'est jamais automatiquement négative ; si les clips sont trop ambigus, il faudra compléter les données.

### 48. Comment mesureras-tu ensemble les mouvements détectés, les mouvements manqués, le délai, les fausses alertes et les périodes d'abstention ?

**Réponse proposée :** Je dois publier ensemble les réponses obtenues, les absences de réponse, les alertes antérieures et les périodes non interprétables. Les délais seront accompagnés de leur incertitude ; sur les zones négatives, je mesurerai le temps en alerte et les nouveaux épisodes, avec la durée observable. L'évaluateur actuel reste un diagnostic par ROI. Pour annoncer un rappel complet d'objets mobiles, il faudra des identités et des annotations temporelles adaptées, en gardant les objets manqués au dénominateur.

### 49. Comment associeras-tu une détection à la profondeur pour produire un point XYZ, en précisant son repère et la différence entre point de surface visible et centre d'objet ?

**Réponse proposée :** Je prévois de transformer les pixels de la ROI native dans la géométrie rectifiée, de sélectionner des disparités valides et d'estimer une profondeur robuste. Un pixel retenu et sa disparité seront reprojetés avec la calibration, notamment Q, dans le repère de la caméra gauche rectifiée. La sortie représentera un point de surface visible, pas automatiquement le centre physique de l'objet. Si le support est insuffisant, le système devra s'abstenir ; cette fusion reste à implémenter.

### 50. Quel démonstrateur minimal peux-tu viser dans le temps restant, et quel plan de repli prévois-tu si la profondeur ou la séparation des mouvements reste insuffisante ?

**Réponse proposée :** Je propose un rejeu prolongé, avec une cible de 60 secondes, montrant activité, classe et point 3D lorsqu'ils sont disponibles, ainsi que leurs dates et leur validité. Le périmètre et l'échéance doivent être confirmés avec vous. Si la profondeur ou la séparation des mouvements reste insuffisante, je conserverai les références, publierai les limites et les comparaisons négatives, puis proposerai un périmètre réduit explicitement validé. Je n'annoncerai pas une détection 3D fiable ou du temps réel si les mesures ne le démontrent pas.


---

**Méthode de préparation :** pour chaque question, prépare une réponse courte avec une idée principale, une preuve ou une figure, puis la limite actuelle. Distingue toujours ce qui est réalisé, ce qui est mesuré et ce qui reste à tester. Si un résultat n'est pas encore disponible, explique comment tu prévois de le mesurer.
