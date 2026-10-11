# D01 — Revue approfondie et correction des deux documents externes

10 octobre 2026. Demande : relire les documents de conception et de veille bibliographique, corriger leurs erreurs et problèmes avant de poursuivre les expériences.

## 1. Livrables et provenance

Versions corrigées maintenues dans le projet :

- [Conception technique v2](conception_pfe_stereo_evenementielle.md).
- [Veille technique v2](veille_bibliographique_pfe.md).

Aucune écriture ou suppression n'a été effectuée sur les entrées de `Downloads` pendant cette revue. Une sauvegarde exacte de chaque entrée, avec extension `.md.bak`, est archivée dans `outputs/documentation/D01/originals/`. Le [manifeste SHA256](../outputs/documentation/D01/originals-manifest.json) indique chemins et empreintes relevés à l'acquisition. Les sauvegardes sont des pièces historiques et ne sont pas des instructions actives.

Au contrôle final, les deux chemins d'entrée dans `Downloads` ne sont plus présents, pour une raison non déterminée ici. La sauvegarde de chaque fichier correspond toujours à son empreinte d'origine. Leur présence finale dans `Downloads` n'est donc pas annoncée comme vérifiée ; les versions corrigées et les sauvegardes du projet restent disponibles.

La revue concerne ces **deux documents externes** et leur cohérence avec le cahier des charges, les consignes persistantes, les résultats et le plan courant. Elle ne prétend pas auditer à nouveau tout le code ni chaque ancien Markdown du dépôt.

## 2. Méthode et portée de la preuve

Toutes les sections des deux fichiers ont été relues. Les références qui influencent les décisions ont été vérifiées sur des sources primaires : articles arXiv/CVF, notices des auteurs, dépôts et documentations officiels. Les parties expérimentales des graph cuts et le protocole d'annotation MOS ont été consultés, ainsi que les résultats officiels DSEC 2021 et les règles du benchmark.

Les autres références restent identifiées comme pistes partiellement vérifiées ou non revalidées. Cela corrige leur ancien statut « confirmé » sans les déclarer fausses. Une page introuvable ou une erreur de l'outil de navigation n'est pas une preuve d'inexistence ; plusieurs notices CVF ont été retrouvées par recherche après l'échec d'ouverture directe.

Les versions corrigées séparent : observation locale, information publiée, chiffre rapporté par un auteur, hypothèse de conception, tâche à réaliser. Aucun téléchargement de dataset, installation de modèle, entraînement, accès aux annotations test réservées ou nouvelle mesure expérimentale n'a été effectué pour D01.

## 3. Registre des corrections

Priorités : **P1** = pourrait invalider le périmètre ou les conclusions ; **P2** = erreur ou limite technique significative ; **P3** = traçabilité, formulation ou entretien documentaire. Ces priorités ne sont pas des notes de qualité globale.

| ID | Priorité | Problème dans les documents d'entrée | Correction appliquée / justification |
|---|---|---|---|
| D01-01 | P1 | YOLO absent du pipeline proposé | Réintroduit dans l'architecture et le jalon d'intégration, conformément au cahier des charges |
| D01-02 | P1 | Détection d'objets, activité et mobilité trop facilement rapprochées | Définitions séparées ; AED reclassé comme détecteur d'objets ; résidu traité comme candidat |
| D01-03 | P1 | Plan d'entraînement EVIMO2 après décision d'unifier sur DSEC | Parcours DSEC cohérent ; EVIMO2 complément sous conditions |
| D01-04 | P1 | Recommencer loaders, architecture et environnement | Réemploi de R01 et des acquis S01/Y01/M01–M17 ; aucun refactoring supplémentaire déclenché |
| D01-05 | P1 | Planning de vingt semaines et rédaction du mémoire par l'agent | Jalons techniques à estimer depuis l'état actuel ; retrait du livrable mémoire, exclu par le brief |
| D01-06 | P1 | Bloc CLAUDE/AGENTS concurrent avec de nouvelles obligations | Remplacé par les contrats techniques ; AGENTS.md persistant reste la source de consignes |
| D01-07 | P1 | Latence réduite à fenêtre + inférence + post-traitement | Durée de support, service, âge, file et délai de détection distingués ; cas d'amorçage précisé |
| D01-08 | P1 | Pas de 10 ms assimilé à une sortie disponible toutes les 10 ms | Condition de débit et politique de surcharge explicites ; mesures en rejeu cadencé nécessaires |
| D01-09 | P1 | Comparaison directe de MAE issues de protocoles différents | Domaine GT, couverture, abstentions, unités et partitions exigés ; S01 séparé du benchmark officiel |
| D01-10 | P1 | Masques/boîtes et absence de label assimilés à une référence complète | GT adaptée à la tâche ; pas de masque inventé à partir du rectangle ni de négatif garanti hors annotation |
| D01-11 | P1 | Répartition des données et provenance des poids insuffisantes | Partitions locales rappelées, groupe 09 protégé, dates d'intersection et préentraînements à auditer |
| D01-12 | P1 | Vitesse 3D obtenue directement par Kalman sur positions caméra | Repère commun et compensation requis pour vitesse monde ; position de surface distincte du centre/boîte 3D |
| D01-13 | P2 | Poids partagés « garantissent » la cohérence gauche-droite | Partage des paramètres distingué de la cohérence géométrique ; gain de paramètres limité à la partie partagée |
| D01-14 | P2 | AANet présenté comme approche à convolutions 3D coûteuses | Correction à partir de l'article CVPR 2020 : agrégation adaptative remplaçant ces convolutions |
| D01-15 | P2 | MADNet-ε confondu avec un réseau pyramidal générique ; SNN exclus ailleurs | Représentation 10 ms et récurrence impulsionnelle précisées ; résultat >140 FPS attribué aux auteurs |
| D01-16 | P2 | Meilleure robustesse d'une petite tête apprise affirmée | Reformulée en hypothèse ; protocole, labels et comparaison requis |
| D01-17 | P2 | Baseline classique supposée assurer un résultat | Résultat négatif M17 intégré ; référence de comparaison sans garantie de détection |
| D01-18 | P2 | Disparité maximale de 192 px et plage EVIMO2 prédéterminées | Choix selon calibration et distances ; validité de bord à examiner |
| D01-19 | P2 | Formule Z = fB/d utilisée sans conventions | Cas des points principaux décalés, signe, unités, rectification et usage de Q explicités |
| D01-20 | P2 | Profondeur dense assimilée à profondeur fiable | Confiance, support, âge et abstentions obligatoires dans les rapports |
| D01-21 | P2 | Même famille DSEC supposée offrir tous les labels simultanément | Manifestes et masques de disponibilité distincts selon tâche ; GT hors entrée du détecteur géométrique |
| D01-22 | P2 | EVIMO2/Vicon déclaré automatiquement plus fiable que MOS | Hiérarchie non mesurée retirée ; erreurs de pose/CAD, masques et alignement à examiner séparément |
| D01-23 | P2 | Toutes les tâches promises sur M3ED/MVSEC | Évaluation conditionnée aux GT réellement fournies et auditées |
| D01-24 | P2 | Graph cuts attribué à Parameshwara | Auteurs corrigés : Yi Zhou, Guillermo Gallego, Xiuyuan Lu, Siqi Liu et Shaojie Shen |
| D01-25 | P2 | Chiffre graph cuts EVIMO2 insuffisamment contextualisé | **64,38 % conservé car confirmé** au §VI-B ; protocole et coût distincts signalés |
| D01-26 | P2 | Temporal Event Stereo déclaré SOTA sur quatre datasets | Formulation limitée aux résultats MVSEC/DSEC documentés par la source consultée |
| D01-27 | P2 | DERD-Net listé sans sa dépendance à des poses connues | Entrée pose signalée avant toute comparaison avec notre chaîne |
| D01-28 | P2 | EV-LayerSegNet proposé sans domaine expérimental | Mouvements affines simulés précisés ; aucune généralisation DSEC présumée |
| D01-29 | P2 | MTevent indiqué CVPR 2025 sans préciser l'atelier | Corrigé en CVPR Workshops 2025 ; baseline RGB/pose distinguée de l'événementiel |
| D01-30 | P2 | DSEC-Detection réduit aux 53 séquences d'origine | Extension incluant de nouvelles séquences explicitée ; nombre exact à lire dans son manifeste |
| D01-31 | P2 | DSEC-MOS « huit catégories » potentiellement compris comme huit codes de masque | Diversité d'objets distinguée du format des labels ; encodage local non supposé |
| D01-32 | P2 | « OpenEB archivé » marqué confirmé malgré réserve | Affirmation non confirmée par le dépôt consulté, retirée ; aucun statut de maintenance global inventé |
| D01-33 | P2 | Exclusion absolue des flips stéréo | Flip naïf interdit dans la proposition ; transformations cohérentes possibles sous contrôles explicites |
| D01-34 | P2 | Perte multi-échelle et BCE/Dice insuffisamment définies | Unités, échelles, GT absentes, masques vides et inconnus explicités |
| D01-35 | P2 | Absence d'effet futur/cadre causal dans les comparaisons | Contexte passé/futur, états récurrents et enseignant d'entraînement distingués |
| D01-36 | P2 | Ablations multiples déclarées obligatoires, causalité des effets implicite | Trois comparaisons prioritaires ; M18 change aussi densité et stéréo ; comparaison de systèmes distinguée d'ablation d'entrée |
| D01-37 | P2 | GPU 12–16 Go déclaré suffisant sans architecture ni batch | Remplacé par essai mémoire/temps sur un checkpoint avant entraînement |
| D01-38 | P2 | « Pas de flou », « latence µs » généralisés au pipeline | Capteur et représentation accumulée distingués ; étalement temporel possible |
| D01-39 | P3 | Résultats bibliographiques transformés en objectifs MAE/IoU | Cibles non justifiées retirées ; résultats historiques vérifiés conservés et datés |
| D01-40 | P3 | Échec d'un transfert MVSEC→DSEC généralisé à tous les modèles | Conclusion universelle retirée ; protocole particulier à identifier avant réutilisation |
| D01-41 | P3 | Lacunes bibliographiques et absence de mémoire similaire assimilées à nouveauté | Hypothèses de positionnement ; pas d'affirmation d'originalité démontrée |
| D01-42 | P3 | Liste de sources et outils entièrement « vérifiés » | Statuts détaillés, réserve des références non revalidées, distinction code disponible/code exécuté |
| D01-43 | P3 | Déclarations non justifiées de lourdeur, SOTA, « premier » ou taux d'acceptation | Suppression des superlatifs inutiles ; comparaison matérielle et protocole nécessaires |
| D01-44 | P3 | Thèses/offres/ateliers traités au même niveau que résultats scientifiques | Ressources exploratoires séparées ; références incomplètes explicitement signalées |

## 4. Éléments confirmés, à conserver

La revue ne remplace pas une affirmation douteuse par son contraire sans source :

- Les quatre lignes du classement DSEC 2021 ont été confirmées sur la [page officielle](https://dsec.ifi.uzh.ch/cvpr-2021-competition-results/) ; elles restent historiques.
- Le chiffre graph cuts EVIMO2 est présent dans [l'article complet, §VI-B](https://arxiv.org/html/2012.08730v3). L'erreur principale de la veille était l'attribution des auteurs.
- La description de génération puis correction humaine des masques MOS est documentée dans [le §IV-A](https://arxiv.org/html/2305.00126v3).
- La [documentation Tonic](https://tonic.readthedocs.io/en/latest/autoapi/tonic/datasets/index.html) expose bien DSEC, MVSEC et TUMVIE ; pas de raison de remplacer nos lecteurs pour autant.
- MADNet-ε, EventHub et EventCV ont bien des notices en 2026 ; leur date récente n'est pas un motif pour les déclarer inexistants. Les limites de vérification sont indiquées dans la veille.

## 5. Limites restantes et décisions

La revue bibliographique ne valide pas les chiffres non extraits des tableaux sources, les scores de SSTNet, les détails des thèses ou les outils non essayés. Ces entrées sont conservées dans le registre de pistes, pas utilisées pour justifier le pipeline.

MADNet-ε : notice institutionnelle et description vérifiées, mais code/poids, matériel et périmètre détaillé du chronométrage restent à auditer. Les autres checkpoints n'ont pas été téléchargés ni exécutés. Aucun modèle n'est adopté par défaut à la suite de D01.

Les objectifs persistants sont conservés : DSEC principal ; pas d'annotations manuelles demandées ; séparation objet/caméra prioritaire ; YOLO, stéréo, Deep Learning et XYZ présents dans le résultat final. La prochaine expérience reste M18. Les documents v2 proposent une conception compatible avec ces contraintes sans annoncer son implémentation.

## 6. Vérification des fichiers

Les contrôles documentaires portent sur l'UTF-8, les blocs de code fermés, les liens locaux des documents corrigés, la conservation des sources externes et l'identité des copies `markdowns/`. Les liens Web sont des références de consultation ; aucun contrôle automatique de disponibilité permanente n'est annoncé.

Les preuves de validation et hashes des fichiers livrés sont conservés dans `outputs/documentation/D01/validation.json` après finalisation. Aucun nouveau test algorithmique n'est nécessaire pour cette modification documentaire. Les 174 tests mentionnés dans M17 restent un résultat historique, pas un nouveau résultat d'exécution D01.
