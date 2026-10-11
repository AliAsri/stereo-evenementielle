# M19 — Audit d'intégration EMatch

**10 octobre 2026 — audit statique réalisé ; aucune inférence EMatch exécutée.** Le candidat peut servir à un diagnostic de profondeur sur train. Il ne peut pas être adopté directement comme remplacement de S01 ni servir à annoncer une évaluation indépendante sur nos séquences locales.

## Sources figées et candidat

Le [dépôt officiel](https://github.com/BIT-Vision/EMatch/tree/92e528bd9d0d1f1d7774385233a841c8bd6eb8d8) est figé au commit `92e528bd9d0d1f1d7774385233a841c8bd6eb8d8`. Les 113 fichiers texte acquis représentent 332 722 octets ; leurs tailles et SHA256 ont été vérifiés. Le code amont a été lu, sans import ni exécution. Les poids ne sont pas compris dans ce volume.

- [Manifeste des sources](../outputs/motion/M19/audit/manifest.json).
- [Audit structuré, paramètres et lignes de preuve](../outputs/motion/M19/static_audit.json).
- [Vérification locale reproductible](../outputs/motion/M19/check_static_audit.py).

Le script stéréo propose `checkpoints/ematch/disparity/dsec/default/stage2/final.pth`. Le [dossier officiel de cette variante](https://drive.google.com/drive/folders/1_sts647l1kq0o1h3nPMEAq2vKqUnn4TD) a été inspecté dans le navigateur : `final.pth`, taille affichée 25,7 Mo, modification affichée le 6 juillet 2025. La visionneuse montre un dossier interne `step_150000`. Ces métadonnées ne prouvent ni les clés des tenseurs ni la provenance effective d'entraînement.

La tentative de téléchargement a rencontré une confirmation Drive d'absence d'analyse antivirus et a été annulée. **Aucun fichier de poids acquis, désérialisé ou vérifié par hash.** L'audit du checkpoint binaire reste à réaliser ; le nom du dossier ne suffit pas à le déclarer compatible.

## 1. Chevauchement avec nos partitions

Le [fournisseur DSEC publié](https://github.com/BIT-Vision/EMatch/blob/92e528bd9d0d1f1d7774385233a841c8bd6eb8d8/datasets/DSEC/DSECProvider.py) énumère 41 séquences d'entraînement stéréo, dont les quatre séquences de notre protocole local :

| Séquence | Rôle local | Présente dans la liste train EMatch |
|---|---|---|
| `zurich_city_04_b` | Train/debug | Oui |
| `zurich_city_04_e` | Train/debug | Oui |
| `thun_00_a` | Petite validation locale | Oui |
| `zurich_city_09_b` | Test réservé local | Oui |

L'historique du fichier binaire n'est pas vérifié, mais la liste publiée interdit de présumer ces poids indépendants de notre validation ou de notre test. Les prochains essais restent des diagnostics sur `04_b` et `04_e`. Nous n'acquérons ni ne consultons les images/événements de `09_b` pour cet audit et ne changeons pas les partitions historiques.

Pour une future mesure de généralisation avec des poids suivant ce protocole, il faudra une référence réellement indépendante de leur entraînement, ou un entraînement documenté qui respecte nos exclusions. Le constat ne modifie pas rétroactivement les résultats S01/Y01, obtenus avec d'autres méthodes et poids.

## 2. Contrat d'entrée réel

Le [chargeur stéréo](https://github.com/BIT-Vision/EMatch/blob/92e528bd9d0d1f1d7774385233a841c8bd6eb8d8/datasets/DSEC/DSECSequence_ematch_disparity.py) et sa configuration demandent :

- deux grilles rectifiées gauche/droite de 640×480, 15 canaux temporels, float32 ;
- une fenêtre de 100 ms terminant à la date de disparité ;
- polarités signées −1/+1, interpolation spatiale et temporelle, standardisation des valeurs non nulles de chaque grille ;
- positions temporelles normalisées entre le premier et le dernier événement réellement présents ; ce n'est pas une normalisation par les seules bornes nominales de la fenêtre.

La paire de tenseurs seule représente **35,16 Mio** ; cette valeur calculée n'est pas la consommation GPU du réseau. Les activations, corrélations, poids et espaces temporaires s'y ajoutent. Aucun pic mémoire ni temps d'inférence n'a été mesuré.

La fenêtre est tournée vers le passé. Le [lecteur publié](https://github.com/BIT-Vision/EMatch/blob/92e528bd9d0d1f1d7774385233a841c8bd6eb8d8/datasets/DSEC/preLoader/Event.py) inclut toutefois l'événement à la borne de fin et tronque les demandes hors plage. Notre contrat `[début, fin)` et notre abstention sur historique incomplet exigent donc un adaptateur explicite. Pour une profondeur précédente à `t−20 ms`, il faut 120 ms d'historique complet avant la date courante `t`. Les deux premières dates M16 ne satisfont pas cette condition.

Remplacer directement les images logarithmiques 50 ms par ces voxels change à la fois méthode et représentation. Un essai EMatch natif à 100 ms doit être décrit ainsi, avec contrôle SGBM à 100 ms si l'on cherche à séparer cet effet. Un essai à 20/50 ms serait une variante hors du contrat nominal publié, pas une reproduction fidèle.

## 3. Défauts et adaptations identifiés

| Point vérifié dans le code | Conséquence pour le prochain essai |
|---|---|
| Le [générateur de cache stéréo](https://github.com/BIT-Vision/EMatch/blob/92e528bd9d0d1f1d7774385233a841c8bd6eb8d8/tools/DSEC_preprocess/events_to_npz_disparity.py) fait `dt = args.dt * 1000`, puis multiplie encore `dt` par 1000 dans `convert_npz` | Avec `--dt 100`, demande nominale de 100 secondes, ensuite tronquée par le lecteur. Le chemin direct du chargeur demande bien 100 ms. Ne pas reproduire ce générateur tel quel |
| Le [voxeliseur](https://github.com/BIT-Vision/EMatch/blob/92e528bd9d0d1f1d7774385233a841c8bd6eb8d8/datasets/DSEC/utils/EventToVoxel.py) accède au premier/dernier événement et divise par leur écart | Prévoir explicitement les fenêtres vides et les événements tous au même timestamp ; vérifier les valeurs finies |
| Le mode `train` du chargeur charge la disparité de référence et applique des augmentations | Un diagnostic sur une séquence train doit passer par un adaptateur d'inférence sans augmentation ni GT dans le modèle |
| Les configurations utilisent un cache non nul par défaut | Un cache nommé `dt100` ne prouve pas sa durée effective. Générer nos entrées traçables à partir des événements et dates explicites |
| La [soumission stéréo](https://github.com/BIT-Vision/EMatch/blob/92e528bd9d0d1f1d7774385233a841c8bd6eb8d8/submission_dsec_ematch_disparity.py) charge avec `strict=False` | Vérifier chaque clé manquante/inattendue et chaque forme ; ne pas accepter silencieusement un modèle partiellement initialisé |

Le défaut du générateur publié **ne prouve pas** que les poids diffusés ont été entraînés avec ce chemin défectueux. La provenance du prétraitement demeure inconnue ; conserver cette limite même si les poids se chargent correctement.

Le README propose Python 3.8 / PyTorch 2.0 / CUDA 11.7. Notre environnement local est Python 3.14.6 sans PyTorch. Une exécution nécessite donc un environnement séparé, et une vérification de compatibilité ; M19 n'a rien installé dans `.venv`. Aucun fichier de licence nommé LICENSE/COPYING n'est présent dans l'arbre consulté : conserver les attributions et clarifier les conditions avant redistribution ou incorporation du code.

## 4. Protocole de la prochaine étape

1. Préparer un adaptateur causal, indépendant des chargeurs d'entraînement : dates, polarités, rectification, interpolation, normalisation et abstention vérifiées sur des cas contrôlés. Ne pas intégrer le générateur de cache défectueux.
2. Préparer quatre paires gauche/droite aux dates précédentes M18 sur `04_b/04_e`, avec 100 ms d'historique, manifeste et hashes. Conserver les correspondances temporelles 50 ms de M17 pour isoler autant que possible l'effet du changement de profondeur. Conserver aussi un contrôle SGBM 100 ms.
3. Acquérir et auditer un seul checkpoint standard : hash, clés/formes, chargement restreint aux poids lorsque possible, provenance déclarée. Préparer une exécution Colab isolée avec versions enregistrées, batch 1 et aucune phase d'apprentissage.
4. Comparer validité et couverture de profondeur, puis résidus sur le support commun des points ; rapporter séparément les points rendus évaluables. Une carte dense n'est pas automatiquement fiable et ne répare pas les boîtes sans suivi.
5. Mesurer préparation, inférence, transfert, mémoire GPU et âge de sortie séparément. Conserver les inconnus et le modèle caméra ; un flux optique total ne prouve pas un mouvement propre d'objet.

Cette étape prépare un essai de profondeur au service de la séparation objet/caméra. Elle ne remplace pas l'objectif de mobilité par un nouveau cycle d'entraînement stéréo. Pas d'annotations manuelles demandées, pas de score sur le test réservé, pas de promesse de temps réel.

## Refaire l'audit hors ligne

```powershell
.\.venv\Scripts\python.exe outputs/motion/M19/check_static_audit.py
```

Ce contrôle relit les empreintes, extrait la liste d'entraînement par AST sans import, compare les séquences locales et sauvegarde les lignes de preuve. Les 182 tests du projet validés en M18 restent le dernier contrôle du code applicatif ; ils ne constituent pas des tests d'exécution EMatch.
