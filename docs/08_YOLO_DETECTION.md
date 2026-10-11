# Détection YOLO sur données événementielles

## Choix

Point de départ : YOLO11n avec PyTorch, affiné sur pseudo-images d'événements de la caméra gauche native. Le choix compact protège le budget Colab et permet un témoin reproductible ; aucune précision événementielle n'est supposée depuis les poids COCO. [Documentation du modèle](https://docs.ultralytics.com/models/yolo11/).

YOLO reçoit un tenseur image, jamais directement la liste `(x,y,t,p)`. Le passage événements → image est une partie réelle, testée et chronométrée du système.

## Annotation et classes

Lire les boîtes DSEC-Detection dans leur vue d'origine. Convertir `(x,y,w,h)` en centre/largeur/hauteur normalisés pour YOLO, après clipping et rejet des boîtes dégénérées. Conserver les identifiants de classe originaux dans le manifeste. Mapper `pedestrian` vers le libellé utilisateur « personne », et `car` vers « voiture » ; `rider` ne doit pas être fusionné silencieusement avec pedestrian.

Au pilote, entraîner deux classes prioritaires et documenter comment les autres annotations sont gérées. Si leurs boîtes sont simplement retirées, elles deviennent du fond pour le détecteur à deux classes ; ce choix doit rester constant entre entraînement et évaluation. Une extension à huit classes nécessite assez d'exemples par classe.

Ne pas prendre les détections d'un YOLO RGB comme vérité terrain du test de notre YOLO événementiel. Des pseudo-labels supplémentaires peuvent servir à l'entraînement, mais l'évaluation exige des références indépendantes et un contrôle manuel de qualité.

## Validation par étapes

1. Superposer boîtes officielles et événements de la fenêtre causale : vérifier repère, temps et mapping de classes.
2. Surapprendre volontairement un petit lot de train (diagnostic, pas résultat scientifique).
3. Entraîner sur un sous-ensemble par séquences et surveiller le jeu de validation séparé.
4. Évaluer une seule fois la configuration retenue sur test figé ; rapporter précision, rappel, mAP@0.5, mAP@0.5:0.95 par classe et nombre d'instances.

Le modèle est sélectionné par validation. Confidence et NMS sont inscrits au rapport ; le seuil visuel peut différer du seuil bas utilisé pour calculer une courbe précision/rappel. Les augmentations de teinte/saturation doivent être désactivées pour des canaux qui encodent la polarité. Les transformations spatiales doivent transformer les annotations de façon identique. [Configuration officielle](https://docs.ultralytics.com/usage/cfg/).

## Solutions de secours

Si les event frames sont insuffisantes : vérifier d'abord annotations et fenêtre ; ensuite comparer récence ou bins temporels. E2VID + YOLO reste une option plus coûteuse. Un témoin YOLO sur images peut aider à diagnostiquer, mais requiert une vraie reprojection intercaméra avant association à la profondeur événementielle. Il ne remplace pas la validation de la branche événements.

## Export Y00 et protocole Y01 préparés

Le pilote à deux classes est exporté et vérifié : 536 images train, 238 validation, classes `person` et `car`. Les boîtes sont bornées au capteur ; les autres classes sont du fond. Aucun filtre de petite taille à l'export. Les deux images négatives train ont un fichier label vide. Le manifeste conserve les correspondances aux labels DSEC originaux et les exclusions.

La version Ultralytics 8.4.172 a été auditée par lecture de sa distribution. Le notebook désactive HSV/BGR et passe une liste Albumentations vide ; il vérifie de vrais tenseurs avant entraînement et compte les petites boîtes supprimées par le filtre interne du framework. Ce contrôle runtime est réussi : six tenseurs vérifiés et neuf boîtes train filtrées. [Détails et lancement](22_YOLO_EXPORT_COLAB.md).

Statut au 4 octobre 2026 : YOLO11n entraîné dans Colab et poids importés localement. Diagnostic corrigé à 99,5 % d'AP50 par classe sur train ; pilote à 23,73 % de mAP50 sur validation. Ces scores concernent des protocoles distincts. Pas de nouvelle inférence exécutée sur Windows. [Analyse Y01](24_Y01_COLAB_RESULTS.md).
