# État actuel et prochaines étapes

**19 octobre 2026 — page de reprise unique.** Priorités : **1. rapidité, 2. détection fiable du mouvement indépendant, 3. estimation 3D**. Le projet est un prototype intégré hors ligne ; temps réel et mobilité fiable restent à démontrer. [Audit daté](AUDIT_TECHNIQUE_SCIENTIFIQUE_18_OCTOBRE_2026.md) · [Historique et preuves détaillées](19_PROGRESS.md).

## Décision actuelle : démonstrateur DSEC sur le PC actuel

**Cible confirmée par l'utilisateur : PC actuel, démonstration locale simple.** Conserver le parcours CPU, le mouvement prioritaire et YOLO/XYZ moins fréquents. Aucun portage Colab/GPU requis pour la démonstration. Le budget de 20 ms reste non atteint.

Après clarification de l'impasse d'accès aux données, l'utilisateur demande de passer à la prochaine étape du projet. La validation indépendante reste **en attente** : aucune issue publiée, aucune acquisition supplémentaire. Le plafond de 512 Mio est épuisé sans fichier cible ; la proposition de 23,79 Go n'est pas une obligation pour poursuivre. [Historique de l'accès](19_PROGRESS.md#recherche-daccès-ciblé--miroir-indisponible-et-coût-établi--19-octobre-2026).

**Correction intégrée :** la rectification alloue directement ses quatre blocs de contributions, en conservant l'ordre des additions non nulles et les sorties. Contrôle sur 34 fenêtres résidentes : **39,77→32,25 ms médians** pour ce poste seul, comptes exacts. La publication du mouvement avant RGB/stéréo courante reste conservée. [Contrôle intégré](../outputs/rectifier_buffers_20261019/verification.json).

## Où nous en sommes

| Objectif | Acquis observé | Blocage restant |
|---|---|---|
| Rapidité | Dernier contrôle intégré Y01 : calcul jusqu’au mouvement **103,8 ms médians**, calcul complet **224,2 ms** ; 153 tableaux et 17 résultats scientifiques conservés | **17/17 sorties hors budget de comparaison de 20 ms**, même pour le mouvement ; délai physique de début non mesuré |
| Mouvement indépendant | Suivi à 100 ms, profondeur source exacte, modèle rigide, résidus continus et abstentions | Exactitude du suivi et pose caméra non validées sur DSEC ; aucune précision/rappel de mobilité indépendante |
| Classes YOLO | Y01 personne/voiture par défaut ; Y02 personne/voiture/camion entraîné et rejoué explicitement | Validation locale sans camion et faible diversité ; une classe ne prouve pas un mouvement |
| Stéréo et XYZ | Disparité avec contrôles de support/cohérence, point de surface 3D et abstentions | Couverture partielle, surface pouvant appartenir au fond ; centre et trajectoire 3D non validés |
| Reproduction | Dossier isolé avec sources actuelles et huit entrées vérifiées : 153 tableaux et 17 résultats exacts | Environnement Python existant partagé ; installation neuve et clone GitHub encore à vérifier |

[Dernier contrôle Y01 du 19 octobre](../outputs/rectifier_buffers_20261019/verification.json) : calcul jusqu'au mouvement **135,3→103,8 ms médians**, calcul complet **266,5→224,2 ms**. Un couple de rejeux, autres coûts variables : aucun gain stable global démontré. Le contrôle résident alterné isole mieux le gain de rectification. **342 tests passent** ; 153 tableaux, 17 lignes scientifiques, 17 messages de mouvement et quatre contextes communs exacts. La fidélité numérique ne valide pas la mobilité. Les anciens contrôles restent dans l'historique ; ne pas comparer directement des sessions différentes pour estimer un gain.

<a id="priorités-actives--recadrage-du-16-octobre-2026"></a>

## Parcours conservé et priorités actives

Commande principale : `scripts/run_integrated_demo.py`, un extrait DSEC de 17 dates, fenêtres causales de 50 ms, pas source de 20 ms et Y01 par défaut. [Exécution et prérequis](../README.md) · [Dernier GIF intégré](../outputs/rectifier_buffers_20261019/after/clip.gif).

1. Lire les événements gauche/droite et préparer les représentations rectifiées causales, avec le worker existant.
2. Suivre les points sur 100 ms et compenser avec la profondeur **exactement à t−100 ms** ; publier `motion.jsonl`.
3. Calculer ensuite l’image native couleur, puis la stéréo de t pour l’historique et les surfaces courantes.
4. Actualiser YOLO et les surfaces XYZ toutes les **100 ms dataset**, puis exporter/rendre. `--context-step-ms 20` fournit le contrôle à chaque date.

Le traitement reste séquentiel ; aucun ordonnanceur indépendant. Sur une date sans contexte, `objects=[]` avec `context.updated=false` signifie non calculé. Les boîtes/XYZ anciens restent datés, sans superposition à l'image courante. Aucune profondeur approximative ni future utilisée. Conserver les acquis ; éviter les variantes et les micro-optimisations sans cause et décision concrètes.

## Conclusion sur les preuves disponibles

- **MOS :** six dates de développement, masques 640×440. À 100 ms : 156 occurrences de suivis sur pixels positifs, 133 évaluables et 53 candidats résiduels ; pas 53 objets ou vrais positifs. Les zéros et les 40 lignes hors crop ne sont pas des négatifs physiques certifiés. [Support vérifié](../outputs/dsec_mos_support_20261019/verified/summary.json).
- **Parallaxe :** sur 35 candidats du raster zéro, neuf n'ont aucune intersection avec un positif à toute profondeur admissible sous le modèle exact ; 26 ont une possibilité géométrique. Ce contrôle ne certifie ni faux positifs ni correction de la profondeur réelle. [Détail](../outputs/dsec_mos_parallax_20261019/summary.json).
- **ORB clos et non promu :** 2/23 correspondances évaluables correctes à ≤3 px, contre 20/25 dans LK sauvegardé ; cible une correcte dans les deux cas, pose refusée, quatre critères échoués. [Comparaison](../outputs/motion/M14_next_sample_20261017/orb_20261019/comparison.json). Aucun balayage ni répétition des anciens contrôles EVIMO2.

Les erreurs aller-retour faibles, un grand consensus ou la conservation numérique des sorties ne prouvent pas leur exactitude physique. Les résultats historiques à 20/100 ms utilisent aussi des versions différentes : ce n'est pas une ablation isolée de l'intervalle. Le [document d'objectif](38_OBJECTIF_OBJETS_MOBILES.md) conserve méthodes, limites et références.

## Y02 : personne, voiture, camion

Y02 est disponible uniquement par `--weights outputs/colab/Y02_20261015T134856Z/pilot/weights/best.pt`. Sur la même validation personne/voiture de 238 images, mAP50 Y02 **38,52 %**, Y01 **23,73 %** ; aucune référence camion. Ces résultats ne mesurent pas la mobilité. Y01 reste le défaut ; aucune nouvelle classe ou promotion sans entraînement et vérification appropriés. [Archives et historique](19_PROGRESS.md#étape-active-y02--entraînement-reçu-et-rejeu-intégré-vérifié--15-octobre-2026).

## La suite utile

1. **Conserver ce parcours unique.** Le mouvement sort avant RGB, stéréo courante et YOLO/XYZ. Ne pas répéter cette comparaison inchangée ni relancer EVIMO2 à chaque « continue ».
2. **Rapidité encore bloquée :** 17/17 dates restent hors budget. PC local confirmé ; conserver la sortie de candidats de mouvement et mesurer son coût réel. Aucun seuil, saut de date ou baisse de résolution implicite pour afficher 20 ms. Le contrôle de rectification est clos ; ne pas enchaîner des variantes sans cause précise.
3. **Fiabilité encore ouverte :** la sortie est un candidat résiduel, pas un objet mobile confirmé. Conserver les abstentions et limites ; l'accès aux nouvelles références est en attente, sans bloquer la maintenance du démonstrateur.
4. **Reproduction locale de la version avant cette rectification vérifiée :** dossier neuf, sources sauvegardées, huit entrées conformes, 153 tableaux/17 résultats/17 messages exacts. [Preuves](../outputs/reproduction/isolated_20261019/verification.json). Python existant partagé ; pas de clone GitHub ni installation neuve vérifiés. Le manifeste et le script de restauration sont inclus dans la version préparée pour GitHub à la demande de l’utilisateur. Données, poids, résultats et miroirs restent locaux ; clone neuf avec installation encore à vérifier. Ne pas répéter ce contrôle inchangé.

## Repères de maintenance

[Commandes](16_COMMANDS.md) · [Cahier des charges](PROJECT_BRIEF.md) · [Maintenance](44_PROJECT_MAINTENANCE.md). La version précédente de cette page est conservée intégralement dans [l'historique](19_PROGRESS.md#archive-de-la-feuille-de-route-avant-simplification--19-octobre-2026), sans suppression d'expérience. Modifier les sources Markdown puis lancer `.\.venv\Scripts\python.exe scripts/sync_markdowns.py` ; ne pas éditer directement `markdowns/`.
