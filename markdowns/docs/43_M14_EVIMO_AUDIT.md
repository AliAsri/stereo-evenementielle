# M14 — Échantillon EVIMO2 acquis et audité

**7 octobre 2026 — acquisition et audit réalisés ; détection de mobilité non évaluée.**

## Pourquoi cette étape

L'utilisateur a demandé de sauter les annotations manuelles. Nous avons donc récupéré un petit complément public instrumenté pour préparer l'évaluation du mouvement indépendant des objets. Aucune relecture M13 n'est demandée. DSEC reste principal pour les scènes routières, la stéréo, YOLO et XYZ.

La catégorie « Motion Segmentation / Object Recognition » d'EVIMO2v2 fournit événements, masques, profondeur et trajectoires. C'est une scène d'objets proches, différente du domaine routier. L'archive gauche complète annoncée est d'environ 1,8 Go. [Source et partitions officielles](https://better-flow.github.io/evimo/download_evimo_2.html).

## Acquisition bornée et traçable

- Séquence : `left_camera/imo/train/scene13_dyn_test_02_000000`.
- Partition **train** confirmée par le répertoire de l'archive et la liste officielle. Le mot `test` dans le nom ne détermine pas la partition.
- Sélection : première séquence de l'archive, identifiée avant extraction et avant toute sortie de modèle. Aucun choix selon une performance.
- Une seule caméra acquise : ce complément n'est pas encore une expérience stéréo EVIMO.
- Taille distante vérifiée par HTTP : **1 819 418 535 octets** pour l'archive complète.
- Transfert utile de cette acquisition : **251 545 600 octets, soit 239,89 Mio**, sous une limite de 256 Mio. Les sondes préalables ont aussi lu 1 Mio et les en-têtes HTTP.
- Six fichiers extraits : **594,01 Mio** au total, sous une limite de 2 Gio. Arrêt dès leur récupération, sans télécharger le reste de l'archive.
- Sources : `dataset_events_t.npy`, `dataset_events_p.npy`, `dataset_events_xy.npy`, `dataset_info.npz`, `dataset_depth.npz`, `dataset_mask.npz`.
- Empreintes SHA256 locales des six fichiers relues et conformes. Le flux gzip étant interrompu volontairement, son contrôle final intégral n'est pas effectué. Les empreintes locales ne sont pas des sommes de contrôle publiées par le fournisseur.

Le téléchargeur refuse d'écraser une acquisition existante. Il ne matérialise que six noms autorisés et refuse les liens pour ces membres. Le manifeste d'acquisition garde l'état `ACQUIRED_UNAUDITED` de cette phase ; le résultat de l'audit est dans un fichier séparé.

Attribution : **EVIMO / EVIMO2, équipe Better Flow**, [site du jeu de données](https://better-flow.github.io/evimo/). La [page de téléchargement](https://better-flow.github.io/evimo/download_evimo_2.html) annonce **CC BY-SA 4.0** pour les données. Conserver attribution et licence lors d'une redistribution des données ou de leurs dérivés. Notre planche est une visualisation dérivée des événements et des masques ; elle ne contient pas de prédictions. La licence des données est distincte de celle du code amont.

## Résultats mesurés localement

| Contrôle | Résultat |
|---|---:|
| Résolution | 640 × 480 |
| Événements | 62 915 815 |
| Intervalle événementiel | 0,01666746 à 13,01355648 s |
| Polarités 0 / 1 | 25 915 273 / 37 000 542 |
| Dates dans `frames` | 782 |
| Paires masque/profondeur réellement disponibles | 750 |
| Dates de métadonnées sans cartes | 32 |
| Intervalle maximal entre cartes disponibles | environ 400 ms |
| Échantillons de `full_trajectory` | 2 603 |
| Pas médian de cette trajectoire | 5 ms |
| Pas maximal de cette trajectoire | 5,77 ms |
| Dates GT avec fenêtre événementielle causale complète de 20 ms | 746 |
| Identifiants non nuls observés dans les masques | 5, 6, 11, 14, 15, 22, 23, 24 |
| Identifiants visibles sans pose à la date de leur masque | 0 |

Tous les événements ont été parcourus par blocs : dates finies et non décroissantes, coordonnées dans l'image, polarités binaires. Les six empreintes ont été vérifiées. Toutes les cartes ont été chargées sans pickle et rapprochées par leur identifiant, sans supposer l'ordre des clés NPZ.

Les 30 072 enregistrements de pose disponibles passent les contrôles numériques exécutés : translations et quaternions finis, norme quaternion proche de 1, décalage pose/date de groupe inférieur à 1,1 µs. Le maximum observé est d'environ 1 µs, compatible avec les dates écrites à six décimales. Cela ne valide ni la précision physique des poses, ni leur continuité, ni la présence de chaque objet à tous les instants.

## Points à résoudre avant une mesure de qualité

1. **Masque d'identité ≠ masque de mobilité.** Un objet possède un identifiant même lorsqu'il est immobile ; la valeur zéro n'est pas automatiquement un négatif fiable. Les masques ne deviennent pas des labels « mobile » par simple seuil non nul.
2. **Repères des poses.** Selon le [format officiel](https://better-flow.github.io/evimo/docs/ground-truth-format.html#transform-convention), les objets sont exprimés vers la caméra et la caméra vers le monde. La composition à utiliser est `T_monde_objet(t) = T_monde_camera(t) @ T_camera_objet(t)`. Il reste à implémenter et tester cette composition, confirmer les unités et traiter translation, rotation, bruit et trous temporels.
3. **Calibration incohérente entre deux champs.** `D = [-0.10828, 0.206233, 0, 0]`, alors que les métadonnées indiquent `p1 = -0.000650`, `p2 = -0.000555`. Vérifier le code producteur et les repères des cartes avant de sélectionner une convention de rectification. Aucun score pixel par pixel n'est calculé à ce stade.
4. **Références incomplètes.** Les 32 dates sans cartes et le trou maximal de 400 ms sont conservés. Pas d'interpolation silencieuse ; les fenêtres sans support complet doivent rester exclues ou inconnues. Les premières et dernières dates GT ne sont pas toutes couvertes par 20 ms d'événements.
5. **Profondeur de référence.** Les valeurs stockées positives vont de 223 à 2 685 ; couverture positive médiane 50,42 %. La documentation historique indique des millimètres ; confirmer la conversion v2 avant utilisation métrique. L'utiliser dans le détecteur constituerait une expérience oracle explicitement séparée d'une profondeur prédite.

Le [format EVIMO](https://better-flow.github.io/evimo/docs/ground-truth-format.html) décrit les fichiers, l'encodage des identifiants par multiples de 1000 et les dates irrégulières. Notre audit confirme ces propriétés sur l'échantillon acquis, sans garantir leur présence sur tout le corpus.

## Code, tests et aperçu

- `scripts/download_evimo_sample.py` : téléchargement borné d'une séquence fixée.
- `src/pfe_events/evimo_reference.py` : lecteur spécialisé des métadonnées, remplaçant les constructeurs NumPy sérialisés par des conteneurs locaux inertes ; les autres classes exécutables sont rejetées. Aucun `eval` ni chargement global `allow_pickle=True`.
- `scripts/audit_evimo_sample.py` : empreintes, événements, cartes, poses et aperçu reproductible.
- `tests/test_evimo_reference.py` : huit tests supplémentaires, dont rejet d'un objet sérialisé exécutable, de cycles et de dates invalides, ainsi que limites de lecture et sélection des membres d'archive.
- **137 tests réussis**, journal : `outputs/motion/M14/tests.log`. Quatre sources et leurs snapshots sont archivés dans le rapport.

La [planche d'inspection](../outputs/motion/M14/sample_preview.png) montre trois dates fixes : première, médiane et dernière date avec support causal complet, indices 2, 375 et 779. À gauche : événements natifs accumulés sur 20 ms, échelle logarithmique fixe saturant à 20 événements/pixel. À droite : couleurs d'identité officielles, zéro en noir. Les couleurs n'indiquent pas la vitesse et les cartes ne sont pas superposées avant validation de leur repère spatial.

Artefacts : [acquisition](../outputs/motion/M14/acquisition.json), [audit détaillé](../outputs/motion/M14/audit.json). Données locales : `data/raw/evimo2v2/left_camera/imo/train/scene13_dyn_test_02_000000/`.

Pour reproduire l’audit local sans télécharger (depuis R01, choisir un dossier neuf pour préserver M14) :

```powershell
.\.venv\Scripts\python.exe scripts/audit_evimo_sample.py --output outputs/motion/M14_audit_02
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Prochaine étape

Résoudre les conventions de calibration et d'horloge, puis construire une référence de mouvement dans le repère monde à partir des poses. Vérifier aussi la rotation locale et conserver un état inconnu près des seuils ou des trous. Ensuite seulement, comparer le détecteur aux références disponibles sur train, avec couverture explicite et séparation oracle/prédiction. Aucun travail manuel d'annotation demandé à l'utilisateur. Aucune nouvelle précision, aucun rappel ni délai de détection annoncé à l'issue de M14.
