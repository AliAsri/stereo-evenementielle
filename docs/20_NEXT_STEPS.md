# État final du prototype et livraison locale

**22 octobre 2026 — décision utilisateur : finaliser le prototype actuel avec ses limites.** Le parcours scientifique est conservé. Aucune nouvelle campagne, acquisition, publication, entraînement ou modification de seuil n'est engagée. La maintenance nécessaire à la livraison est maintenant dans le périmètre ; une optimisation algorithmique demande une justification distincte.

## Résultat de référence

[GIF actuel](../outputs/object_surface/integrated_f2_20261022/clip.gif) · [Vérification](../outputs/object_surface/integrated_f2_20261022/verification.json).

- 17 dates, fenêtres causales de 50 ms, pas source 20 ms, suivi sur 100 ms.
- Huit entrées taille/SHA conformes ; 153 tableaux et 17 modèles/messages conservés ; cinq abstentions rigides.
- Quatre contextes, 18 occurrences : **2 mobiles estimées, 2 immobiles estimées, 14 indéterminées**. Les identités d'objets ne sont pas suivies.
- **13 surfaces XYZ, deux couches ambiguës, trois profondeurs insuffisantes.** Plage proche nominale de 3,590 m pour la configuration actuelle.
- Calcul médian observé : mouvement 109,1 ms, complet 230,6 ms, hors rendu/export. 17/17 sorties au-dessus du budget de 20 ms ; aucune promesse temps réel.

Ces comptes ne mesurent pas une exactitude physique. `physical_mobility=UNCONFIRMED` reste explicite. La décision F2 dépend de la surface et du modèle dominant ; le centre et la trajectoire 3D ne sont pas validés. Le support train, les erreurs possibles de suivi/profondeur/pose et les contre-exemples 108/16 et profondeur biaisée limitent les conclusions.

## Livraison préparée

Le [README](../README.md) contient la consultation, la commande de rejeu et les prérequis. Le paquet local est `outputs/delivery/reviewed_20261022/prototype-local.zip` : code courant, trois petits artefacts figés et résultats à présenter. Les cinq fichiers DSEC volumineux et les environnements Python restent externes ; leurs chemins/empreintes et les dépendances sont déclarés. Le paquet est un instantané local, pas un push GitHub.

La revue demandée avant publication corrige l'acceptation de seuils non finis/supports non entiers et ajoute un repli de police. Le contrôle des couches est extrait sans modifier les seuils. [Contrôles avant push](../outputs/reviews/prepush_20261022/checks/report.json) : **129 fichiers Python, 47 aides CLI et 391 tests passent**. `pip check` réussit dans les deux environnements ; les huit entrées figées sont conformes. Sur tableaux sauvegardés, **18 décisions et 17 rendus RGB exactement conservés** ; aucun nouveau rejeu ni entraînement. [Comparaison](../outputs/reviews/prepush_20261022/regression.json).

La livraison revue conserve les petits artefacts et le résultat de référence. Le ZIP et son manifeste seront contrôlés avant la publication du code ; données, poids et ZIP restent hors Git. Le paquet antérieur du 22 octobre est conservé comme version historique.

## Clôture de cette finalisation

1. **Vérifié :** contenu/empreintes, chargement des commandes et refus des prérequis externes absents ; le premier paquet a aussi été extrait et contrôlé.
2. **Conservé :** résultats scientifiques identiques au rejeu du 22 octobre pour les associations et rendus contrôlés, résultat de référence identifié et expériences locales intactes.
3. **Livré localement :** [prototype-local.zip](../outputs/delivery/reviewed_20261022/prototype-local.zip), avec `LIVRAISON.txt`, `README.md` et `DELIVERY_MANIFEST.json`. Consultation du GIF possible sans Python ; rejeu soumis aux données et dépendances déclarées.

Une installation neuve sur un autre poste, la validation indépendante, la qualification camion et le budget de 20 ms restent **non réalisés**. Ils ne sont pas des réussites implicites de la livraison locale. L'accès aux nouvelles références reste en attente ; le brouillon aux auteurs reste NON ENVOYÉ.

## Historique et règles conservées

Les corrections F5/F6, la règle F2, les protocoles et preuves détaillés sont conservés dans [l'objectif mouvement](38_OBJECTIF_OBJETS_MOBILES.md). Les expériences antérieures et limites sont dans [l'historique](19_PROGRESS.md). Les rejeux intégrés du 20 et du 22 octobre sont clos : ne pas les répéter inchangés ou ajuster les seuils selon les résultats. Homographie, ORB et les anciens contrôles EVIMO2 restent clos.

Modifier les sources Markdown puis lancer `python scripts/sync_markdowns.py`. Le miroir `markdowns/` reste local ; aucune copie récursive des environnements, caches ou du miroir lui-même.
