# Registre et protocoles d'expérience

Registre historique : la priorité actuelle et la prochaine action sont maintenues dans [20_NEXT_STEPS.md](20_NEXT_STEPS.md).

## En-tête obligatoire d'une exécution

Identifiant, date, hypothèse, commande, version du code, matériel, versions Python/bibliothèques, dataset/séquences, hashes, split, représentation, fenêtre/pas, modèle/hash, hyperparamètres, seeds, métriques, temps et sorties. Puis résultat, interprétation et décision. Une expérience interrompue conserve son statut et son erreur.

## Expériences prévues

| ID | Hypothèse / contrôle | Variable | Mesure principale | Statut |
|---|---|---|---|---|
| D00 | Les modalités d'un échantillon peuvent être alignées | Aucune : inspection | Schéma, timestamps, calibration, labels | RUN — inspection validée |
| S01 | Une accumulation stéréo fournit une profondeur utile | Paramètres baseline figés | EPE, Bad3, couverture, temps | RUN — 60 fenêtres ; couverture limitée, voir 13 et 21 |
| Y00 | Export événementiel et labels YOLO restent alignés | Repère natif, deux classes, normaliseur S01 | 774 images, hashes, canaux, 4 235 boîtes | RUN — export et contrôles réussis |
| Y01 | Le pilote peut apprendre les classes prioritaires | Surapprentissage puis fine-tuning court | AP sur petit lot séparée de mAP validation | RUN, archives vérifiées : diagnostic corrigé AP50=0,995 ; validation pilote mAP50=0,2373 |
| Y02 | Un budget plus long améliore la validation | 30 époques proposées, même corpus/initialisation et réglages pilote | AP par classe, mAP50–95, pas d'optimisation et erreurs par taille | NOT RUN — différé, priorité au mouvement |
| S02 | Un checkpoint événementiel dépasse S01 | SGBM / réseau candidat | Erreur à couverture rapportée, coût | NOT RUN |
| F01 | Une ROI robuste réduit les outliers | Centre / médiane / robuste | Erreur de surface, abstention, surcoût | NOT RUN |
| T01 | Fenêtres plus courtes réduisent délai mais perdent du signal | 10/20/50 ms, un modèle adapté par fenêtre | Erreur/mAP/délai/coût | NOT RUN |
| M01 | Une branche d'activité peut fonctionner sans attendre YOLO | Fenêtres 10/20/50 ms, seuils fixes | Coût lecture/activité, zones ; délai réel et fausses alertes à annoter | RUN — 748 fenêtres, 33 tests ; activité seule, sans compensation caméra |
| M02 | L'index temporel réduit le coût sans modifier les sorties | Lecteur binaire / indexé, mêmes fenêtres et activité | Égalité exacte, coûts appariés et rejeu autonome | RUN — 1 496 paires ; coût médian validation 10 ms −27 % ; cadence non garantie |
| M03 | Séparer activité du décor et mouvement local, mesurer la réponse | Mouvement global et résidus ; évaluation annotée non réalisée | Délai et fausses alertes non mesurés ; limites caméra/parallaxe observées | RUN — prototype sur 600 fenêtres, résidus dans 599 ; mobilité indépendante non validée, voir [27](27_M03_GLOBAL_MOTION.md) |

Priorité historique lors de ce protocole : M01 → coût et délai de réponse → contrôle du mouvement de caméra → association YOLO/stéréo/XYZ. La décision de simplification du 10 octobre, consignée dans la page active, prévaut désormais sur les expériences proposées ici.

S01, exécuté le 2026-10-03 sur le poste local Windows/Python 3.14.6/OpenCV 4.14.0.94 : 20 dates uniformes par séquence, deux séquences train du même groupe et une validation d'un autre groupe. Configuration et normalisation enregistrées avant l'évaluation de la validation ; aucun balayage d'hyperparamètres réalisé. Code identifié par SHA256 de chaque module dans `outputs/reports/S01_summary.json`. Commande, masque et limites détaillés dans [21_STEREO_BASELINE.md](21_STEREO_BASELINE.md). L'hypothèse d'une profondeur dense utile partout n'est pas validée : seulement 36 % de la GT de validation reçoit une estimation retenue.

## Métriques précises

Disparité scalaire : EPE/MAE = moyenne de `abs(d_pred-d_gt)` sur le masque d'évaluation. RMSE = racine de la moyenne des carrés. Bad3 = fraction avec erreur strictement >3 pixels. Rapporter masque GT valide, prédictions finies, plage retenue, pixels exclus et couverture prédite sur GT. Une prédiction invalide ne peut pas simplement disparaître du bilan : donner son taux séparément et une métrique pénalisée si le benchmark la définit.

Profondeur : MAE/RMSE en mètres et AbsRel = moyenne `abs(Z_pred-Z_gt)/Z_gt` pour Z_gt>0. Fixer la plage sur validation et publier résultats par distance. Une conversion en Z amplifie l'erreur des petites disparités.

Détection : P/R pour le seuil déclaré ; AP intégrée sur la courbe précision/rappel ; mAP@0.5 et moyenne des AP sur IoU 0.50:0.05:0.95. Conserver le nombre d'instances par classe et les filtres de taille. Comparer au protocole officiel seulement avec son split et ses filtres.

3D : si seules des surfaces de profondeur sont disponibles, comparer les surfaces correspondantes, pas des centres d'objets supposés. Si une GT de centre 3D est ajoutée, documenter comment elle est obtenue, son repère et son indépendance vis-à-vis des prédictions.

## Échantillonnage et reproductibilité

Partition par trajet/groupe ; ne pas mélanger des fenêtres contiguës entre ensembles. Pour les modèles récurrents, réinitialiser l'état à chaque séquence et documenter le warm-up. Éviter les intervalles centrés qui utilisent le futur. Conserver les tentatives ratées et effectuer une vérification manuelle des cas où la métrique contredit l'image.

Pour l'expérience principale, si le budget le permet, répéter sur trois seeds. Les intervalles de confiance doivent rééchantillonner des séquences, pas traiter chaque fenêtre recouvrante comme indépendante. Au premier pilote, une seule seed suffit pour valider l'exécution, sans revendiquer de robustesse statistique.
