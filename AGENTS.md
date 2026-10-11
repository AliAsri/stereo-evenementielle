# Consignes persistantes du projet

- Décision utilisateur du 11 octobre 2026 : mettre les nouvelles étapes en pause pour une revue globale, des contrôles et la correction des défauts confirmés. L'audit R02 est terminé ; attendre la reprise demandée par l'utilisateur avant le prochain diagnostic scientifique. Bilan et limites dans `docs/20_NEXT_STEPS.md`.

- Décision utilisateur du 10 octobre 2026 : simplifier le projet. Mettre en pause EMatch, les nouveaux datasets, les comparaisons d'architectures et les optimisations supplémentaires. Priorité à un extrait DSEC, une configuration existante 50 ms et un affichage clair, pour comprendre la séparation objet/caméra avant d'ajouter des composants. Conserver tous les acquis. Maintenir `docs/20_NEXT_STEPS.md` comme page active de progression ; éviter de multiplier rapports et variantes. YOLO, stéréo et XYZ restent dans le livrable final. La zone d'inspection d'un extrait n'est pas une annotation de mobilité à chaque instant.

- Décision utilisateur du 7 octobre 2026 : sauter les annotations manuelles. Ne pas demander à l’utilisateur de remplir M13 comme préalable. Conserver les artefacts, privilégier une référence publique de mobilité déjà disponible (à auditer) et poursuivre les diagnostics sans inventer de labels ni annoncer une précision/rappel non mesurée. DSEC reste principal.

- Priorité utilisateur du 7 octobre 2026 : se concentrer sur la détection des objets mobiles, en distinguant leur mouvement de celui de la caméra et du décor. Les gains de vitesse M08/M09 sont conservés ; les nouvelles micro-optimisations et le simple démonstrateur d'activité passent après cette séparation. Voir `docs/38_OBJECTIF_OBJETS_MOBILES.md`. Ne jamais assimiler activité événementielle, classe YOLO ou résidu global à une preuve de mouvement indépendant.
- Respecter le cahier des charges conservé dans `docs/PROJECT_BRIEF.md`.
- Priorité utilisateur du 4 octobre 2026 : concentrer les prochaines étapes sur la détection rapide du mouvement (causalité, délai, fausses alertes et mouvement de caméra). YOLO, stéréo et XYZ restent nécessaires, mais ne doivent pas bloquer la branche d'activité rapide. Voir `docs/25_M01_RAPID_ACTIVITY.md` et `docs/20_NEXT_STEPS.md`.
- À la demande de l'utilisateur, conserver une copie de tous les fichiers `.md` du projet dans le dossier racine `markdowns/`, tout au long du développement.
- Conserver les chemins relatifs dans cette copie pour éviter les collisions de noms : `docs/19_PROGRESS.md` devient `markdowns/docs/19_PROGRESS.md`.
- Modifier les documents sources, puis exécuter `python scripts/sync_markdowns.py` après chaque création ou modification de Markdown et avant de terminer l'étape de travail.
- Ne pas modifier directement les copies de `markdowns/`. Ne pas recopier récursivement ce dossier, les dépendances, les environnements virtuels ou les caches.
- La copie ne supprime aucun document source. Le script ne supprime pas non plus les anciennes copies ; tout nettoyage éventuel doit être explicite.
