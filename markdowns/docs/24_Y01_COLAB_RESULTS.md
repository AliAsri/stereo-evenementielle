# Y01 — Résultats Colab reçus et vérifiés

Analyse du 4 octobre 2026, session `Y01_20261003T191753Z` exécutée le 3 octobre. Le diagnostic corrigé est réussi et le pilote de cinq époques est terminé. La détection sur une autre séquence reste faible, particulièrement pour les piétons. La fusion avec la profondeur n'est pas encore exécutée.

## Preuves et import local

Deux ZIP fournis par l'utilisateur ont été inventoriés et hachés. Ils contiennent 268 fichiers, totalisant 3 352 891 022 octets décompressés. Les 113 fichiers utiles à l'analyse (58 703 517 octets, environ 56 Mio) sont conservés dans `outputs/colab/Y01_20261003T191753Z/` : rapports, paramètres, courbes, images, poids initiaux et poids best/last des trois essais. Les 155 checkpoints intermédiaires restent dans les archives originales ; aucun fichier source n'a été supprimé. Le second ZIP ne contient que des checkpoints intermédiaires.

Le [rapport d'audit](../outputs/reports/Y01_colab_audit.json) conserve les chemins sources, SHA256 des deux ZIP, inventaire de chaque membre, CRC annoncé et hashes de chaque fichier extrait. Le CRC est vérifié pour les fichiers extraits seulement ; les snapshots d'époque non extraits ne sont pas annoncés comme vérifiés individuellement. Les archives entières sont hachées.

Neuf comparaisons SHA256 réussissent : manifeste et normaliseur comparés aux fichiers locaux et à la provenance Colab, archive de données comparée à la provenance, poids initiaux, best/last pilote et best du diagnostic corrigé comparés à leurs rapports. Les poids n'ont pas été désérialisés et aucune évaluation de modèle n'a été relancée localement. Les métriques ci-dessous proviennent des rapports Colab, rapprochés des CSV et figures.

Le statut racine est `PILOT_COMPLETE`. Les champs `NOT RUN` dans les rapports de préparation et `full_pilot: NOT RUN` dans le statut du diagnostic décrivent leur étape d'écriture ; ils n'annulent pas les résultats du pilote ultérieur. Les rapports originaux restent intacts.

## Environnement et données

Runtime enregistré : Tesla T4, Python 3.13.15, torch 2.11.0+cu130, CUDA 13.0, Ultralytics 8.4.172. YOLO11n est initialisé depuis `initial_weights/yolo11n.pt`. Les réglages effectifs sont conservés dans chaque `args.yaml`.

| Partition locale | Séquences | Images | Personnes | Voitures |
|---|---|---:|---:|---:|
| Train | `zurich_city_04_e`, `zurich_city_04_b` | 536 | 864 | 2 466 |
| Validation | `thun_00_a` | 238 | 238 | 667 |

Ces comptes sont ceux de l'export. Le contrôle runtime confirme six tenseurs, l'ordre positif/négatif/total et le letterbox de 80 pixels en haut et en bas. Le chargeur conserve 3 321 des 3 330 boîtes train : neuf sont filtrées par le framework. Le ZIP, le manifeste et le normaliseur correspondent exactement à Y00. Le test réservé `09_b` reste non acquis et non évalué.

## Trois essais à distinguer

Les AP/mAP sont exprimées en pourcentage. Les scores des deux diagnostics portent sur les huit mêmes images utilisées pour apprendre, contenant dix personnes et trente-neuf voitures. Ils ne mesurent pas la généralisation.

| Essai | Époques | AP50 personne | AP50 voiture | mAP50 | mAP50–95 |
|---|---:|---:|---:|---:|---:|
| Diagnostic initial | 50 | 30,69 | 80,56 | 55,63 | 47,94 |
| Diagnostic corrigé | 100 | 99,50 | 99,50 | 99,50 | 96,38 |
| Pilote, validation `thun_00_a` | 5 | 9,49 | 37,97 | 23,73 | 13,66 |

### Diagnostic corrigé : garde-fou passé

Le nouvel essai conserve le sous-ensemble et les poids initiaux, avec batch=4, nbs=4, AdamW, lr0=0,001 constant, warmup=0, weight_decay=0, augmentations désactivées et seed=42. Le compteur enregistre **200 pas réels de l'optimiseur**. Le seuil AP50≥0,80 par classe est dépassé et le statut est `PASSED`.

Le modèle parvient donc à mémoriser ce petit lot. Cela lève le blocage d'intégration initial. Le `nbs=64` de l'ancien essai est confirmé par son `args.yaml` ; ses treize pas restent une simulation du code, pas un compteur runtime. Plusieurs paramètres du diagnostic ayant changé ensemble, l'effet causal de `nbs` seul n'est pas isolé.

### Pilote : première mesure sur une autre séquence

Le pilote repart des poids COCO initiaux, pas des poids du diagnostic. Paramètres : cinq époques, batch=4, nbs=64, AdamW, lr0=0,001, lrf=0,01, warmup=1, weight_decay=0,0005, seed=42, taille 640, AMP et augmentations désactivés. Les réglages de mémorisation du petit lot n'ont pas été transférés au pilote.

La [réévaluation du best pilote](../outputs/colab/Y01_20261003T191753Z/pilot-metrics.json) rapporte :

| Métrique | Valeur |
|---|---:|
| mAP50 | 23,73 % |
| mAP50–95 | 13,66 % |
| Précision moyenne | 74,47 % |
| Rappel moyen | 21,67 % |
| AP50 / AP50–95 personne | 9,49 % / 4,94 % |
| AP50 / AP50–95 voiture | 37,97 % / 22,39 % |

La précision relativement élevée accompagne un rappel faible. Les scores P/R sont des moyennes par classe au point choisi par le framework sur la courbe F1 ; ils ne décrivent pas un seuil de déploiement fixé à l'avance. Une AP50 de 23,73 % ne signifie pas « 23,73 % des objets reconnus ».

La validation est séparée du train par groupe de trajet, mais sert aussi à choisir les poids. Ce n'est donc ni un test final indépendant ni le benchmark officiel DSEC. Un seul groupe de trajet est représenté de chaque côté ; les nombreuses images voisines ne sont pas autant de scènes indépendantes.

## Lecture des courbes et images

Dans le CSV du pilote, la perte de localisation train descend de 1,772 à 0,856 et la perte de classification de 2,115 à 0,757. La mAP50 validation fluctue au lieu de progresser régulièrement. Cinq époques montrent que l'apprentissage fonctionne, sans établir une convergence ou expliquer à elles seules l'écart train/validation.

Le meilleur mAP50–95 du CSV se situe à l'époque 3 (0,13597), tandis que le meilleur mAP50 se situe à l'époque 1 (0,25890). Le code de cette version sélectionne selon mAP50–95. La réévaluation finale de `best.pt` rapporte 0,13664 / 0,23731 ; ces valeurs sont distinctes des mesures pendant entraînement. Nous conservons les deux sources sans attribuer leur petit écart à une cause non vérifiée.

![Courbes du pilote](../outputs/colab/Y01_20261003T191753Z/pilot/results.png)

Sur le premier montage de validation inspecté, la voiture centrale apparaît dans les prédictions mais la petite personne annotée n'apparaît pas dans les boîtes affichées. Ce constat illustre un cas d'échec ; quatre images consécutives ne remplacent pas une analyse quantitative par taille et par scène. Les traînées événementielles sont visibles, sans démontrer qu'elles causent l'échec.

[Annotations du montage](../outputs/colab/Y01_20261003T191753Z/pilot_validation/val_batch0_labels.jpg) · [prédictions correspondantes](../outputs/colab/Y01_20261003T191753Z/pilot_validation/val_batch0_pred.jpg).

Attention à la [matrice de confusion](../outputs/colab/Y01_20261003T191753Z/pilot_validation/confusion_matrix.png) : elle est construite à confidence=0,001 et IoU d'appariement=0,45, d'après le code 8.4.172 archivé. Ce dernier seuil est distinct de l'IoU NMS=0,7. Le très grand nombre de prédictions classées comme fond ne correspond pas au point P/R du tableau. Les montages filtrent l'affichage à confidence=0,25, autre seuil encore. Il ne faut pas recalculer la précision de 74,47 % à partir de cette matrice ou des seuls montages.

## Poids, temps et limites

Le poids utilisable comme première référence est [pilot/weights/best.pt](../outputs/colab/Y01_20261003T191753Z/pilot/weights/best.pt), SHA256 `d520108bd92cceb3264ef3b4b83fde94e721c20f4d80b9ef88c0b2d4146a47d4`. Les poids du diagnostic à 99,5 % ne doivent pas le remplacer dans une démonstration de généralisation.

Le dernier temps cumulé du CSV pilote est 102,7 s ; celui du diagnostic corrigé est 117,395 s. Ce ne sont pas les durées totales de session avec installation et transfert. Le pic d'allocation GPU rapporté vaut 1 169 670 656 octets (environ 1,09 Gio de mémoire allouée par PyTorch), pas la consommation totale de VRAM. Aucune mesure end-to-end événements→XYZ ni validation du temps réel n'est disponible.

## Décision et prochaine expérience

Conserver Y01 comme première référence de détection événementielle réellement entraînée. Le blocage initial du diagnostic est résolu ; la qualité des piétons sur validation devient la priorité. Ne pas répéter le diagnostic réussi ni régénérer les données sans raison.

Préparer **Y02 avec un budget fixé à 30 époques**, depuis les mêmes poids initiaux, en conservant partitions, normaliseur, seed et réglages du pilote, notamment nbs=64. Compter les pas réels, relever AP par classe et courbes, conserver best/last et espacer les snapshots d'époque. Ce protocole teste un budget d'apprentissage plus long, avec son ordonnanceur étalé sur 30 époques ; il ne garantit pas un gain. Il ne s'agit pas d'une reprise avec optimiseur du `last.pt` nettoyé de Y01. Y02 n'est ni préparé dans un nouveau notebook ni lancé au moment de cet audit.

Avant de multiplier les essais, compléter le diagnostic par taille de boîte et examiner des dates réparties sur toute la validation, plutôt que seulement ses premières images. Si l'amélioration reste faible, examiner en priorité la diversité du train et la représentation des petits piétons, avec de nouveaux groupes exclusivement côté train. Garder le test réservé intact. La fusion géométrique peut ensuite être développée avec cette référence clairement étiquetée, en conservant l'abstention quand la profondeur manque ; sa qualité finale dépendra encore des deux branches.
