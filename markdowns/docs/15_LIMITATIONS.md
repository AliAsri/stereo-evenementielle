# Limites et risques suivis

| Risque | Conséquence | Contrôle / repli |
|---|---|---|
| Pas de caméra physique | Aucun test acquisition ou synchronisation matérielle locale | Démonstration explicitement par rejeu |
| Données clairsemées / objet immobile | Peu d'information pour détection ou matching | Statut profondeur indisponible, contexte temporel limité |
| Mouvement caméra et illumination | Activité confondue avec mouvement d'objet | Nommer activité/flux apparent ; pose nécessaire pour mouvement monde |
| Boîtes et profondeur dans des vues différentes | XYZ plausible mais faux | Mapping de ROI complet et tests géométriques |
| Labels générés puis corrigés | Erreurs d'annotation et omissions | Audit visuel et limites explicites |
| GT de profondeur incomplète | Métriques biaisées par les pixels évalués | Masques/couverture et découpes par distance |
| GT centre 3D absent | Impossible de mesurer exactement localisation du centre d'objet | Mesurer surface représentative et disponibilité |
| Séquences d'un même trajet proches | Fuite entraînement/validation | Partition par groupe de trajet |
| Checkpoint déjà entraîné sur notre test local | Score de généralisation non indépendant | Vérifier provenance/splits ; signaler tout chevauchement |
| Colab variable ou déconnecté | Entraînement interrompu, performances fluctuantes | Petits budgets, checkpoints, journal matériel |
| Anciennes extensions CUDA | Installation scientifique coûteuse | Limite de deux jours/candidat et repli documenté |
| Dépendances Python 3.14 | Pile DL historique potentiellement incompatible | Environnement GPU séparé ; socle CPU seulement validé ici |
| ROI contaminée par fond | Profondeur médiane erronée | Support/dispersion, comparaison avec pixel central |
| Longue fenêtre d'événements | Traînées et âge des informations | Compromis 10/20/50 ms mesuré |

Les seuils de réussite définis au cadrage ne sont pas garantis. Une expérimentation négative bien diagnostiquée reste une information ; elle doit déclencher une adaptation du périmètre technique, sans supprimer les contraintes centrales.

S01 a mesuré ces limites sur données réelles : seulement 36 % des pixels GT de la petite validation locale disposent d'une prédiction conservée, malgré une EPE conditionnelle de 1,045 px. La chaîne lecture→profondeur prend une médiane d'environ 505 ms sur cette séquence, hors export. Aucune qualité de profondeur d'objet ou rapidité de détection ne découle directement de ces chiffres. Le corpus train est limité à un groupe de trajet et la validation à un autre petit groupe : il sert à valider l'intégration, pas à soutenir une conclusion statistique générale.

Le système final ne sera pas présenté comme dispositif de sécurité automobile ni comme validation d'un usage réel à haute vitesse. Il s'agit d'un prototype scientifique sur données publiques avec limites mesurées.
