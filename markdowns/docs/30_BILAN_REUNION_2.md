# Deuxième réunion d'encadrement — Bilan d'avancement du PFE

**Sujet : Stéréo Vision par Caméras Événementielles pour la Détection Rapide de Mouvement**  
**Document préparé le : 4 octobre 2026**  
**Réunion prévue le : 5 octobre 2026**  
**But de la réunion :** présenter le travail réalisé depuis l'attribution du titre, discuter les premiers résultats et valider les priorités de la suite.

> **État général :** un premier socle expérimental fonctionne sur des données réelles : lecture d'événements stéréo, estimation de profondeur, entraînement YOLO et détection d'activité. Le principal problème encore ouvert est de distinguer un objet réellement mobile du décor qui se déplace dans l'image à cause du mouvement de la caméra. Le système complet avec position 3D des objets et délai réel validé n'est pas encore terminé.

## 1. Présentation orale courte pour commencer la réunion

« Depuis notre première réunion, j'ai traduit le titre en une architecture expérimentale et mis en place un environnement de travail reproductible. J'ai choisi un premier sous-ensemble du dataset DSEC, vérifié la lecture et la synchronisation des deux flux événementiels, puis obtenu une première profondeur par stéréo classique. J'ai également préparé des images à partir des événements et réalisé un premier entraînement YOLO pour les personnes et les voitures.

J'ai ensuite concentré le travail sur la détection rapide du mouvement. Une branche d'activité indépendante de YOLO fonctionne, et l'optimisation de la lecture a réduit son coût. Les essais montrent toutefois que l'activité événementielle seule ne permet pas de distinguer les objets mobiles du mouvement apparent du décor. Un premier modèle global de déplacement a été testé, mais il ne résout pas encore ce problème.

Aujourd'hui, les outils d'annotation et de mesure sont prêts. La prochaine étape est de constituer une petite référence de mouvement, de mesurer les délais et les fausses alertes, puis d'étudier l'apport de la profondeur. Je souhaite valider avec vous ce cadrage et les critères prioritaires pour la suite. »

## 2. Compréhension du sujet et problématique proposée

Une caméra événementielle fournit des événements décrivant des variations locales de luminosité, avec une position, une date et une polarité. Pour utiliser certains algorithmes d'image, ces événements sont regroupés dans de courtes fenêtres temporelles.

La difficulté est qu'un événement peut provenir d'un objet mobile, du déplacement de la caméra, d'un changement d'éclairage ou du bruit. **Détecter de l'activité ne signifie donc pas automatiquement détecter un objet mobile.**

La problématique de travail proposée, à discuter avec l'encadrant, est :

> Comment détecter rapidement et de façon causale un mouvement local dans une scène observée par une paire de caméras événementielles, puis enrichir cette détection avec la classe de l'objet et sa position 3D, en mesurant le compromis entre délai et fiabilité ?

Trois questions structurent le travail :

1. **Rapidité et fiabilité :** quel effet ont la durée des fenêtres, les seuils et la persistance sur le délai, les détections manquées et les fausses alertes ?
2. **Apport de la stéréo :** la profondeur aide-t-elle à distinguer les objets mobiles du mouvement apparent du décor ?
3. **Enrichissement :** comment ajouter YOLO et une position 3D sans ralentir excessivement la réponse initiale ?

Ces questions constituent un cadrage proposé à partir du titre et du travail exploratoire. Elles ne sont pas présentées comme un protocole déjà approuvé par l'encadrant. La place exacte de YOLO, de la stéréo profonde et des sorties 3D peut être précisée pendant cette réunion.

## 3. Choix techniques et raisons

| Choix | Raison | Limite ou point à confirmer |
|---|---|---|
| **DSEC comme premier dataset** | Données événementielles stéréo, calibration, références de disparité et annotations d'objets disponibles | Les données utilisées ne fournissent pas directement une référence complète des débuts de mouvement indépendant |
| **Petit sous-ensemble avant extension** | Vérifier les données, la géométrie et le code avec un volume maîtrisé | Diversité encore insuffisante pour conclure à une généralisation |
| **Python et OpenCV en local ; Colab pour le GPU** | Faciliter le développement et utiliser une Tesla T4 pour l'apprentissage YOLO | Les mesures CPU locales et GPU Colab doivent rester distinctes |
| **StereoSGBM comme première référence** | Obtenir une profondeur prédite et vérifier la chaîne géométrique avant d'introduire un réseau stéréo plus complexe | Couverture limitée et coût CPU élevé |
| **YOLO11n sur une représentation événementielle** | Premier modèle léger, adaptation d'un détecteur profond à des images construites à partir des événements | Le pilote actuel est court et la détection des petits piétons reste faible |
| **Deux classes au départ : personne et voiture** | Réduire la complexité du pilote et contrôler l'intégration | Camions et autres classes ne sont pas reconnus comme classes dédiées par ce modèle |
| **Branche rapide indépendante de YOLO** | Signaler une activité sans attendre une classification ou une profondeur | L'activité seule ne démontre pas le mouvement indépendant d'un objet |
| **Fenêtres causales et cadences distinctes** | Utiliser uniquement les événements déjà disponibles et adapter le coût de chaque branche | La fusion devra gérer explicitement les dates et l'âge des estimations |

Architecture visée :

```text
Événements gauche/droite synchronisés
    ├── Branche rapide : activité → candidats de mouvement
    ├── Branche stéréo : disparité → profondeur
    └── Branche YOLO : boîtes → classes d'objets
                   ↓
    Association temporelle et géométrique
                   ↓
    Mouvement + classe + point 3D + indication de validité
```

La dernière partie, l'association complète des sorties, reste à implémenter et à évaluer.

## 4. Travail déjà réalisé

### 4.1. Données et préparation

- Téléchargement et organisation de trois séquences réelles : `zurich_city_04_e`, `zurich_city_04_b` et `thun_00_a`.
- Lecture des événements gauche/droite, contrôle de l'ordre temporel et prise en compte des offsets propres à chaque fichier.
- Vérification de la calibration, de la rectification et des unités utilisées pour la profondeur.
- Inspection des annotations d'objets et production de représentations visuelles des événements.
- Séparation locale : `04_e` et `04_b` pour entraînement/débogage ; `thun_00_a` pour validation. Les deux séquences d'entraînement appartiennent au même groupe de trajet.
- Une séquence réservée au test final reste non acquise et non utilisée.

### 4.2. Première estimation de profondeur — S01

- Implémentation d'une chaîne stéréo classique avec StereoSGBM.
- Évaluation sur **60 fenêtres réelles de 50 ms**, réparties entre les trois séquences.
- Sauvegarde des cartes prédites, des masques de validité, des figures et des métriques.

### 4.3. Détection d'objets — Y00/Y01

- Préparation de **774 images événementielles** : 536 pour l'entraînement et 238 pour la validation, avec **4 235 boîtes annotées**.
- Création du notebook Colab, contrôles des canaux d'image et de la géométrie des boîtes.
- Diagnostic de mémorisation sur huit images, puis premier entraînement YOLO11n de cinq époques sur GPU.
- Import et vérification des poids, paramètres et résultats du Colab.

### 4.4. Branche d'activité et accélération — M01/M02

- Détection causale d'activité par cellules, avec support spatial et persistance.
- Comparaison de fenêtres de **10, 20 et 50 ms**.
- Ajout d'un lecteur indexé pour accéder plus rapidement aux événements.
- Vérification que l'accélération conserve exactement les événements et les sorties d'activité sur **1 496 paires de fenêtres comparées**.

### 4.5. Mouvement global, annotations et contrôles — M03/M04

- Premier suivi de points et estimation robuste du déplacement apparent global de l'image.
- Exécution sur **six clips de deux secondes**, soit 600 fenêtres mesurées de 20 ms.
- Préparation d'un outil local d'annotation avec images sans prédictions et intervalle d'incertitude du début de mouvement.
- Implémentation d'un évaluateur par zone annotée et d'un contrôle des annotations.
- Exécution de **486 essais artificiels**, représentant **27 540 fenêtres**, pour vérifier les effets des seuils, fenêtres et persistances.

### 4.6. Organisation et vérification

Le projet contient les scripts, configurations, notebooks, résultats et explications techniques. Les expériences disposent de paramètres et de sources archivés, avec des empreintes de fichiers pour vérifier leur intégrité. **61 tests automatisés ont réussi.** Ces tests vérifient des comportements du code ; ils ne prouvent pas à eux seuls la qualité sur des scènes réelles.

## 5. Principaux résultats et leur interprétation

### 5.1. Profondeur : une première référence fonctionne, mais elle est incomplète

Sur la petite validation locale `thun_00_a` :

| Mesure | Résultat |
|---|---:|
| Erreur moyenne absolue de disparité, EPE | **1,045 pixel** |
| Couverture des pixels de référence par une prédiction valide | **36,00 %** |
| Erreur absolue moyenne de profondeur de surface | **1,421 m** |
| Temps médian lecture → profondeur sur CPU | **505,3 ms** |

**Interprétation :** nous obtenons une profondeur prédite exploitable sur une partie de la scène. Les erreurs sont calculées uniquement là où la référence et la prédiction sont toutes deux valides. Environ **64 % des pixels de référence n'ont pas de prédiction retenue**. Nous ne pouvons donc pas présenter ce résultat comme une profondeur dense, ni comme du temps réel, ni le comparer directement à un score publié selon un autre protocole.

### 5.2. YOLO : intégration réussie, qualité encore faible

| Mesure sur les 238 images de validation | Résultat |
|---|---:|
| mAP à IoU 0,5 | **23,73 %** |
| mAP de 0,5 à 0,95 | **13,66 %** |
| AP50 personne | **9,49 %** |
| AP50 voiture | **37,97 %** |
| Rappel moyen rapporté | **21,67 %** |

**Interprétation :** le détecteur a réellement été entraîné sur les représentations événementielles. Il détecte mieux les voitures que les personnes, mais manque encore beaucoup d'objets. Les cinq époques et le petit corpus constituent un pilote ; ils ne permettent pas de conclure sur le potentiel final de YOLO.

Le diagnostic corrigé atteint **99,5 % d'AP50 par classe sur les huit images utilisées pour apprendre**. Ce résultat confirme la capacité à mémoriser le petit lot et aide à vérifier l'intégration ; il ne représente pas une performance sur des données nouvelles.

### 5.3. Activité rapide : gain de coût confirmé, cadence non garantie

| Mesure à fenêtres de 10 ms sur validation | Résultat |
|---|---:|
| Comparaison appariée, lecture + activité, médiane avant/après optimisation | **10,54 → 7,70 ms**, environ **−27 %** |
| Rejeu autonome avec lecteur optimisé, médiane | **8,45 ms** |
| Même rejeu, 95e percentile | **11,32 ms** |
| Fenêtres dont le calcul dépasse 10 ms | **14 %** |

**Interprétation :** l'optimisation accélère le traitement sans changer les sorties. Cependant, un coût médian inférieur à 10 ms ne garantit pas une sortie toutes les 10 ms. Ces nombres sont des **temps de lecture et de calcul**, pas des délais mesurés entre le début physique d'un mouvement et sa détection.

### 5.4. Séparation caméra/objet : problème principal encore ouvert

Le prototype global produit des zones résiduelles dans **599 fenêtres sur 600**, notamment sur le décor. Ce nombre décrit la fréquence de ses sorties ; ce n'est pas un taux de fausses alertes, car nous ne disposons pas encore des annotations permettant de les juger.

Le coût total médian est d'environ **20 à 38 ms selon le clip**, pour un pas de 20 ms. Le modèle global apporte donc un coût supplémentaire et ne suffit pas encore à isoler les objets mobiles. La profondeur pourrait aider à traiter la parallaxe, mais ce bénéfice reste une hypothèse à tester.

### 5.5. Contrôles artificiels : comprendre le comportement avant de conclure

Les essais synthétiques montrent que :

- une source d'activité faible peut être manquée ;
- une bouffée globale d'événements peut déclencher une alerte sans objet mobile indépendant ;
- augmenter le seuil peut supprimer une détection utile sans supprimer ce facteur perturbateur ;
- une persistance configurée à 20 ms n'implique pas un délai minimal de 20 ms, car le code compte des fenêtres entières.

Ces essais sont réalisés sur des signaux artificiels de taille réduite. **Ils ne mesurent pas la précision ni le délai réel sur DSEC.**

## 6. Où se situe le projet aujourd'hui ?

| Composant | État actuel |
|---|---|
| Lecture, synchronisation et visualisation des événements | Réalisées et contrôlées |
| Première estimation stéréo de profondeur | Réalisée, couverture faible et calcul CPU lent |
| Premier entraînement YOLO | Réalisé, résultats de validation encore limités |
| Branche causale d'activité | Réalisée et accélérée |
| Séparation du mouvement de caméra et du mouvement d'objet | Premier prototype testé, problème non résolu |
| Outil d'annotation et mesures par zone | Disponibles |
| Annotations réelles de mouvement relues et importées | Pas encore disponibles |
| Délai réel, rappel des objets mobiles et fausses alertes | Pas encore validés |
| Association détections → profondeur → XYZ | Conçue, à implémenter |
| Stéréo profonde | Candidate à comparer, non exécutée |
| Démonstrateur complet prolongé | À assembler et à mesurer |

**Positionnement :** le projet a dépassé la préparation théorique et dispose de premières expériences reproductibles. Il se trouve maintenant à l'étape de validation de la détection du mouvement et de préparation de l'intégration. Il serait prématuré d'annoncer un système complet de détection 3D en temps réel.

## 7. Prochaines étapes proposées

| Priorité | Action | Livrable ou preuve attendue |
|---|---|---|
| **1** | Constituer et relire des annotations de début de mouvement et des zones négatives ; conserver les cas incertains | Petit ensemble de référence traçable et protocole validé |
| **2** | Mesurer la réponse actuelle, puis comparer seuil absolu, seuil relatif/historique, fenêtres et persistance sur train | Tableau délais/détections manquées/fausses alertes, avec couverture et limites |
| **3** | Comparer le modèle global seul à une variante exploitant la profondeur | Gain de fiabilité et coût additionnel mesurés, ou échec expliqué |
| **4** | Implémenter l'association robuste des régions/boîtes à la profondeur et aux coordonnées XYZ | Point 3D avec repère, support et abstention lorsque la profondeur manque |
| **5** | Améliorer la branche YOLO par un essai contrôlé et davantage de diversité de données | Nombre de mises à jour enregistré, scores par classe/taille et comparaison au pilote |
| **6** | Assembler les branches à des cadences adaptées et effectuer un rejeu prolongé | Démonstration visée de 60 s, âge des sorties, temps par étape et stabilité mesurés |

Les premières priorités portent sur le mouvement, conformément à l'orientation actuelle du travail. La stéréo et YOLO restent nécessaires à l'architecture envisagée, mais leurs traitements ne doivent pas bloquer systématiquement la première réponse d'activité.

Si les six clips actuels ne contiennent pas suffisamment de débuts de mouvement observables, il faudra sélectionner d'autres segments ou examiner un corpus complémentaire. Si la profondeur reste trop clairsemée pour améliorer la séparation des mouvements, ce résultat devra être documenté et le périmètre ajusté avec l'encadrant.

## 8. Points à discuter avec l'encadrant pendant cette réunion

1. **Périmètre du mouvement :** faut-il prioritairement détecter un déplacement apparent, ou identifier un objet qui bouge indépendamment d'une caméra embarquée ?
2. **Critère de rapidité :** quelle cible privilégier pour le PFE — délai de première alerte, cadence de mise à jour, ou latence complète jusqu'à la sortie 3D ?
3. **Rôle de la stéréo :** sert-elle principalement à localiser en 3D, ou souhaite-t-on démontrer aussi son apport à la séparation du mouvement de caméra ?
4. **Référence d'évaluation :** un petit ensemble annoté manuellement, complété par des contrôles synthétiques, convient-il pour la première comparaison ?
5. **Livrable minimal :** confirmer les classes prioritaires, la place de YOLO et d'une éventuelle stéréo profonde, ainsi que l'acceptation d'un point de surface visible plutôt qu'un centre 3D complet d'objet.
6. **Prochaine échéance :** fixer le résultat concret attendu à la réunion suivante, en priorité un premier bilan quantitatif du mouvement sur des annotations relues.

## 9. Éléments que l'on peut montrer pendant la réunion

Les liens suivants pointent vers les fichiers de ce poste. Pour les partager sur un autre ordinateur, il faudra joindre les fichiers correspondants.

| Élément | Fichier à ouvrir | Ce qu'il montre |
|---|---|---|
| Profondeur stéréo | [Exemple S01](<C:/Users/moali/OneDrive/Desktop/PFE 3/outputs/stereo/S01/thun_00_a/example.png>) | Prédiction, référence et limites de couverture |
| Résultats YOLO | [Bilan Y01](<C:/Users/moali/OneDrive/Desktop/PFE 3/docs/24_Y01_COLAB_RESULTS.md>) | Diagnostic, pilote, métriques et limites |
| Activité rapide | [Bilan M01 et rejeux](<C:/Users/moali/OneDrive/Desktop/PFE 3/docs/25_M01_RAPID_ACTIVITY.md>) | Zones actives indépendantes des classes YOLO |
| Effet du décor | [Diagnostic M03](<C:/Users/moali/OneDrive/Desktop/PFE 3/outputs/motion/M03/clips/thun_00_a_1/diagnostic.png>) | Activité et résidus apparents ; aucune preuve automatique d'objet mobile |
| Annotation | [Outil local](<C:/Users/moali/OneDrive/Desktop/PFE 3/outputs/motion/M03/annotate.html>) | Clips sans prédictions et préparation des références |
| Protocole et contrôles | [Bilan M04](<C:/Users/moali/OneDrive/Desktop/PFE 3/docs/29_M04_MOTION_PROTOCOL.md>) | Définition des mesures et résultats artificiels séparés du réel |

## 10. Repères pour expliquer les chiffres

- **EPE :** erreur moyenne de disparité en pixels ; ici calculée sur les pixels où référence et prédiction sont valides.
- **Couverture :** proportion des pixels de référence pour lesquels une prédiction valide est disponible.
- **AP/mAP :** mesures de détection qui combinent précision et rappel selon les seuils ; une mAP de 23,73 % ne signifie pas simplement « 23,73 % des images sont correctes ».
- **IoU :** mesure de recouvrement entre deux boîtes.
- **p95 :** 95e percentile des temps mesurés ; il met en évidence des traitements plus lents que la médiane.
- **Causal :** une sortie utilise uniquement les événements disponibles jusqu'à sa date.
- **Abstention :** le système indique qu'il ne dispose pas d'assez d'information pour fournir une estimation fiable.

**Message essentiel à porter :** le travail a permis de construire et de mesurer les premières briques, puis d'identifier précisément le verrou scientifique et technique : obtenir une détection de mouvement indépendante, fiable et rapide avant de l'enrichir en 3D.
