# M04 — Protocole de réponse et contrôles artificiels

Date : 4 octobre 2026. **486 essais exécutés, 27 540 fenêtres ; contrôles artificiels uniquement.** Aucun résultat de précision ou de délai réel sur DSEC n'est ajouté par cette étape.

## Objectif et statut

La critique des deux audits est traduite en un contrat explicite : ce qui est mesuré, ce qui est exclu et ce qu'il faut annoter. Le fichier `configs/motion_protocol_v1.json` a été fixé avant le lancement de M04, puis archivé et haché. Toute modification du protocole doit créer une nouvelle version et de nouveaux résultats.

M01 reste inchangé. M04 vérifie ses effets de seuil et de quantification temporelle ; il ne sélectionne pas de nouveau réglage. M03 reste la référence de déplacement apparent global. Ni apprentissage YOLO ni téléchargement de nouvelles données ne sont nécessaires à ces contrôles.

## Trois niveaux de preuve à conserver séparés

| Niveau | Référence | Ce qu'on peut conclure |
|---|---|---|
| Contrôle artificiel M04 | Instant exact d'activation d'une source construite | Réponse algorithmique, effet des fenêtres et seuils, limites connues sur ces signaux |
| Diagnostic réel par ROI M03 | Annotation manuelle relue avec intervalle de temps | Réponse dans une ROI et activité injustifiée dans des ROI négatives, conditionnées à la validité |
| Détection d'objets mobiles | Identités/boîtes temporelles et mouvement indépendant annotés | Rappel d'objets, erreurs de localisation et compromis réel ; **pas encore implémenté ni évalué** |

Les 53 tests précédents, désormais 61, ne remplacent aucun de ces jeux de référence réels.

## Contrat des annotations réelles

Les six clips de M03 sont déjà disponibles dans `outputs/motion/M03/annotate.html`. L'outil conserve une résolution d'annotation de 20 ms. Il ne faut pas prétendre connaître un début à 1 ms à partir de ce rendu. Une future comparaison 10/20/50 ms devra garder le même intervalle de référence et accepter des dates de prédiction différentes ; l'évaluateur M03 actuel contrôle un alignement exact avec son manifeste à 20 ms.

Chaque annotation comporte clip, annotateur, source, relecture explicite, type, ROI native et, pour un début, intervalle possible/certain. Les quatre interprétations sont : début observable, déjà en mouvement, négatif sur tout le clip dans cette ROI, incertain. La relecture doit examiner le clip entier et les indices de déplacement de caméra ; l'absence d'événements seule ne prouve pas l'immobilité physique. Ne pas forcer un label lorsqu'on ne peut pas départager ces explications.

Une disparition, une occultation ou une entrée dans le champ ne sont pas automatiquement un début/arrêt de mouvement. Si les clips n'offrent pas assez de vrais débuts observables, il faudra sélectionner d'autres segments selon des règles documentées ou utiliser un autre corpus ; aucune annotation de commodité ne doit remplacer cette absence.

L'annotateur doit travailler sans consulter les cartes/prédictions du détecteur. Après export, une relecture humaine distincte est souhaitable ; désaccords et incertitudes sont conservés. Éviter plusieurs ROI qui représentent le même phénomène dans le futur comptage. Les annotations provisoires et exclues restent visibles dans l'inventaire.

## Métriques réelles fixées pour le diagnostic ROI

- Correspondance : centre de proposition dans la ROI fixe, uniquement pour diagnostiquer la réponse locale. Ce n'est ni une IoU d'objet, ni une AP, ni un rappel exhaustif.
- Délai : intervalle `[t_réponse − t_certain, t_réponse − t_possible]`, dans l'horloge des événements. Horizon de 200 ms après la borne certaine. Le calcul CPU, l'attente et l'affichage sont distincts.
- Comptage positif : publier le nombre d'annotations et tous les statuts, y compris absence de réponse, alerte antérieure, couverture insuffisante et fin de clip tronquée. Ne pas publier seulement les délais des succès.
- Négatifs : temps actif, fraction de fenêtres valides en alerte, départs confirmés, débuts censurés et durée observable. Une alerte permanente peut avoir très peu de départs : le taux de départs seul serait trompeur.
- Abstention : état inconnu, jamais absence de mouvement ; couverture publiée et pas de délai interprété à travers une lacune.
- Agrégation : par ROI et partition pour le moment. Pas de cumul naïf des ROI superposées ou des avis de plusieurs annotateurs. Aucun intervalle de confiance de généralisation à partir des cinq phases synthétiques ou d'une seule séquence de validation.

Pour le futur rappel d'objets, il faudra annoter des identités et une géométrie par date, fixer une correspondance spatiale et un appariement un-à-un, puis conserver les objets manqués/abstentions au dénominateur. Ce travail est explicitement signalé comme absent dans le protocole JSON.

## Banc d'essai artificiel exécuté

`src/pfe_events/motion_controls.py` construit des tableaux d'événements entiers triés. Géométrie réduite **128×96**, une seconde par essai. Ce n'est pas un simulateur physique de caméra événementielle, ni une injection dans un fond DSEC. Aucun déplacement d'objet, seuil de contraste, parallaxe, occultation ou stéréo n'est simulé. Aucun temps CPU de cette petite géométrie n'est présenté comme performance du capteur 640×480.

La source locale occupe deux cellules adjacentes de 16×16. Elle commence après 400 ms plus un décalage de 0, 20, 50, 70 ou 90 % de la fenêtre. Elle émet 2, 8 ou 24 événements par milliseconde et par cellule, soit environ 7,81, 31,25 ou 93,75 événements/(s·pixel) lorsqu'elle occupe une fenêtre entière. Un bruit uniforme déterministe de 1 000 événements/s est ajouté avec seed 42. Les mêmes événements sont réutilisés pour les configurations compatibles, avec hashes enregistrés.

Le balayage contient trois fenêtres (10/20/50 ms), trois persistances (10/20/40 ms), trois seuils (10/20/40), trois forces et cinq phases : **405 essais positifs**. Trois témoins négatifs par configuration ajoutent **81 essais** : flux vide, pixel chaud isolé et bouffée globale de 100 ms. Cette dernière représente un facteur perturbateur artificiel de type illumination, pas un modèle de mouvement de caméra.

Les cinq phases sont des conditions déterministes, pas cinq scènes indépendantes. Le p95 indiqué résume ces cinq conditions avec interpolation NumPy ; il ne doit pas servir d'estimation statistique du p95 routier. Une réponse manquée garde un délai `null`, jamais zéro.

## Résultats pour les réglages M01 (10 ms / 20 ms / seuil 20)

| Source locale | Réponses dans 200 ms | Délais des cinq phases (ms) | Médiane conditionnelle / p95 (ms) |
|---|---:|---|---:|
| Faible, 2 événements/ms/cellule | 0/5 | Absents | Non définis |
| Moyenne, 8 événements/ms/cellule | 5/5 | 20, 18, 25, 23, 21 | 21 / 24,6 |
| Forte, 24 événements/ms/cellule | 5/5 | 20, 18, 15, 13, 21 | 18 / 20,8 |

Les témoins vide et pixel chaud ne produisent aucune région. La bouffée globale produit **un départ d'alerte et 90 ms d'activité sur une seconde**, soit 9 % des fenêtres. Cette alerte est injustifiée pour la cible « objet mobile indépendant », mais correspond au comportement attendu d'un détecteur d'activité. Elle illustre pourquoi on ne doit pas changer le nom d'une sortie d'activité pour la présenter comme un objet mobile.

À fenêtre 10 ms et persistance 20 ms, la source moyenne obtient 5/5 réponses au seuil 10 (médiane 20 ms), 5/5 au seuil 20 (21 ms), puis 0/5 au seuil 40. La bouffée globale déclenche des alertes dans les **27 configurations** du balayage. Une hausse du seuil peut donc perdre un signal local sans éliminer ce facteur perturbateur ; ce contrôle justifie une comparaison plus structurée, pas le choix automatique d'un seuil relatif.

Le cas fort montre un délai de 13 ms malgré une persistance configurée à 20 ms. Le code additionne la durée complète des fenêtres qualifiées ; la première contient parfois un signal commencé en cours de fenêtre. Une persistance par fenêtres et une durée physique de signal continu ne sont donc pas équivalentes. Le résultat ne justifie pas de supprimer la persistance : il impose d'en documenter la définition.

## Inventaire des annotations

`scripts/check_motion_annotations.py` contrôle la cible du manifeste, utilise la validation de l'évaluateur, rejette les doublons exacts d'annotations relues et produit un inventaire par clip/partition. Les brouillons et cas incertains ne deviennent pas des négatifs. Un compteur d'annotations non nul ne prouve ni la qualité de la relecture ni une taille d'échantillon suffisante.

L'exécution sans fichier fourni produit `annotation_readiness.json` avec **`PENDING_REVIEWED_ANNOTATIONS` et zéro ROI éligible**. Aucun export n'a été trouvé lors de la recherche ciblée dans le dossier M03 et à la racine de Downloads ; cela n'exclut pas un fichier enregistré ailleurs ou des annotations encore en mémoire dans le navigateur.

## Commandes et preuves

```powershell
# Reproduction des contrôles dans un nouveau dossier.
.\.venv\Scripts\python.exe scripts/run_motion_controls.py --output outputs/motion/M04_controls_rerun

# Après export JSON de l'annotateur ; adapter le chemin si nécessaire.
.\.venv\Scripts\python.exe scripts/check_motion_annotations.py --annotations outputs/motion/M03/M03_manual_annotations.json --output outputs/motion/M03/annotation_inventory_v1.json
.\.venv\Scripts\python.exe scripts/evaluate_motion_annotations.py --annotations outputs/motion/M03/M03_manual_annotations.json --output outputs/motion/M03/evaluation_v1.json

.\.venv\Scripts\python.exe -m unittest discover -s tests -v
python scripts/sync_markdowns.py
```

Le dossier `outputs/motion/M04_controls/` contient `summary.json`, `trials.json`, `trials.csv`, les chronologies du réglage M01, les hashes des événements artificiels, les sources archivées et `verification.json`. Les 486 essais sont uniques, les sources correspondent aux hashes et les délais manqués sont nuls au sens JSON `null`. **61 tests réussissent**, dont cinq nouveaux contrôles du générateur/réponse et trois du contrôle d'annotations.

Prochaine action nécessaire pour une mesure réelle : exporter et relire des annotations exploitables depuis les clips, puis calculer le diagnostic sans changer les seuils sur validation. La comparaison seuil relatif/historique doit ensuite conserver la baseline et mesurer les détections perdues autant que les alertes supprimées.
