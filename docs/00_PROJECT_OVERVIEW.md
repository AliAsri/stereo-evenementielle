# Périmètre technique et critères de réussite

Référence : 2026-10-03. Ce dépôt contient du code et des notes de travail, pas le mémoire.

**Réorientation du 4 octobre 2026 :** priorité demandée par l'utilisateur à la détection rapide du mouvement. Développer d'abord une réponse événementielle causale mesurable, puis l'enrichir avec classe YOLO et profondeur/XYZ. M01 fournit une première carte d'activité et ses coûts ; la séparation mouvement de caméra/objet et le délai réel restent à évaluer. [Bilan](25_M01_RAPID_ACTIVITY.md).

## Résultat visé

Lire deux flux événementiels publics synchronisés, produire une profondeur stéréo, détecter au moins les piétons et voitures avec YOLO entraîné sur une représentation événementielle, associer des points 3D aux détections et visualiser leur activité temporelle. Le fonctionnement sera d'abord démontré par rejeu de données enregistrées. Ce rejeu ne valide ni un pilote de caméra ni la latence d'acquisition matérielle.

Le système minimal combine une stéréo classique et un YOLO profond. Il satisfait la contrainte Deep Learning par la détection. Une comparaison avec une stéréo profonde est prévue dans le plan final, sans rendre la première démonstration dépendante de son entraînement. L'ordre est intentionnel : des erreurs de temps ou de calibration rendraient tout entraînement peu utile.

## Audit initial

Le dossier partagé a été parcouru récursivement, fichiers cachés compris : zéro fichier. Aucun `.git`, `AGENTS.md`, notebook, dataset, checkpoint ou résultat préexistant. Aucun travail antérieur n'a été supprimé. Les caractéristiques CPU/RAM proviennent du cahier des charges ; seules les versions logicielles et l'espace disque ont été inspectés. Python accessible : 3.14.6. Le lanceur `py` ne le recense pas. Le GPU AMD intégré n'est pas une cible CUDA.

## Niveaux de validation

| Niveau | Preuve requise | Ce qui ne suffit pas |
|---|---|---|
| Données | Deux HDF5 réels, horloges et calibration vérifiées, visualisation datée | Quelques tableaux simulés |
| Géométrie | Tests analytiques et erreurs sur disparité de référence | Convertir uniquement la vérité terrain en 3D |
| Détection | Poids YOLO adaptés aux événements, test sur séquences exclues de l'entraînement, métriques par classe | Boîtes RGB transposées approximativement |
| Fusion | Repère et timestamp identiques, profondeur robuste, statut indisponible explicite | Profondeur arbitraire au centre de chaque boîte |
| Mouvement | Carte d'activité causale et mesure du délai de réponse ; mouvement relatif clairement nommé | Déclarer chaque événement « objet mobile » |
| Démonstrateur | Rejeu de 60 s continus sans crash, sorties exportables et étapes chronométrées | Vidéo précalculée présentée comme inférence en direct |
| Reproductibilité | Manifestes, partitions, versions, paramètres, poids et commandes exactes | Une capture seule |

## Seuils d'ingénierie proposés, pas des résultats

- Sur validation, viser mAP@0.5 >= 0,30 pour chacune des deux classes prioritaires et rapporter aussi mAP@0.5:0.95. Ce seuil initial est un critère d'alerte PFE, pas une référence scientifique.
- Sur pixels GT valides et prédictions valides, viser EPE <= 3 px ; publier aussi la couverture, les erreurs par distance et le taux de prédictions invalides sur GT. Une faible EPE obtenue en ne conservant que quelques pixels ne vaut pas validation.
- Viser une profondeur exploitable pour >= 50 % des détections correctes de taille suffisante dans la plage d'évaluation fixée sur validation ; publier les refus et leur cause.
- Cible accélérée : au moins 10 sorties 3D/s et latence de calcul p95 <= 100 ms sur le GPU Colab effectivement attribué, hors téléchargement. Rapporter séparément attente de fenêtre et affichage.
- Cible mouvement : mises à jour d'activité toutes les 5 à 10 ms de temps dataset ; mesurer coût CPU et délais réels avant de qualifier ce chemin de « rapide ».

Les seuils seront confirmés après le pilote de la semaine 2, avant l'ouverture du test final. Aucun ne constitue aujourd'hui un résultat atteint. Une cible ratée se documente ; elle ne se masque pas.

## Livrable et priorité

MUST : événements réels, stéréo, YOLO profond, XYZ, mouvement visible, démonstrateur, métriques et documentation. SHOULD : stéréo profonde reproductible, comparaison de fenêtres et fusion robuste. NICE : tracking élaboré, SNN, reconstruction complète, déploiement embarqué. Les tests de géométrie et de temps sont obligatoires dans notre réalisation même si le cahier des charges classe certains tests en SHOULD.

Parcours de lecture : [datasets](02_DATASETS.md), [choix de méthodes](01_STATE_OF_THE_ART.md), [architecture](05_PROJECT_ARCHITECTURE.md), [planning](PLAN.md), [progression](19_PROGRESS.md).
