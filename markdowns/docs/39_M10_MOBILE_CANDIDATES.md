# M10 — Candidats de mouvement cohérents et persistants

Exécuté le 7 octobre 2026. **Prototype exécuté ; détection de mouvement indépendant non validée.** Cette étape répond à la priorité de détection des objets mobiles définie dans [l'objectif utilisateur](38_OBJECTIF_OBJETS_MOBILES.md).

## Résultat à retenir

Le prototype conserve les régions dont plusieurs points se déplacent dans une direction similaire, différente du mouvement global estimé, pendant trois observations consécutives. Il produit moins de propositions que M03 sur les trois extraits train examinés. Cela ne démontre pas une réduction des fausses alertes : la parallaxe persistante passe encore le filtre et une rotation locale peut être manquée.

Le système retourne **candidat provisoire**, **candidat persistant**, ou un état de modèle invalide. Aucun de ces résultats n'est une certification « objet mobile ». Une absence de candidat ne signifie pas « objet immobile ».

## Fonctionnement et choix

1. Lire les événements par fenêtres causales de 20 ms avec le lecteur M08. Construire la même image logarithmique de travail 320×240 que M03, à partir des événements natifs 640×480.
2. Reprendre les correspondances Lucas–Kanade avec contrôle aller-retour de M03 et son modèle de similarité globale. Ce modèle décrit le déplacement apparent dominant ; il ne fournit pas une pose caméra 3D.
3. Calculer les vecteurs résiduels après ce modèle. Les régions M03 proviennent des points dépassant 3 pixels natifs de résidu.
4. Garder une région si elle contient au moins 4 points résiduels, si la norme de la moyenne de leurs vecteurs unitaires atteint 0,8, et si sa boîte occupe au plus 15 % de l'image. Plusieurs motifs de rejet peuvent concerner une même région.
5. Transformer les anciennes boîtes avec le modèle global courant, puis associer les régions une à une par recouvrement décroissant, IoU ≥ 0,15. Après trois observations consécutives, la région devient persistante. Les seuils sont des choix d'ingénierie fixés avant ces essais, pas des paramètres optimaux démontrés.

La cohérence directionnelle est spatiale, dans une fenêtre ; la persistance temporelle vérifie le recouvrement des boîtes. Elle ne garantit ni une direction constante entre fenêtres, ni une identité d'objet. Les identifiants `C…` désignent des chaînes de candidats, pas des personnes ou véhicules reconnus.

Les observations absentes et les modèles globaux invalides cassent la persistance. Il n'y a pas de prolongation artificielle lors d'une occultation. Le vecteur exporté est en pixels natifs par pas de 20 ms, pas en mètres/seconde. YOLO, profondeur et GT ne participent pas à cette décision.

## Contrôles à correspondances idéales

Sept scénarios de dix étapes chacun sont exécutés. Les paires de points sont construites indépendamment à chaque étape ; elles servent à tester les règles, sans simuler une trajectoire physique complète ni les événements et leurs erreurs de suivi. La perturbation locale est active aux étapes 3 à 6.

| Cas | Sortie persistante | Interprétation |
|---|---|---|
| Caméra fixe, scène fixe | Aucune | Cas simple rejeté correctement |
| Translation globale seule | Aucune | Modèle global suffisant dans ce cas idéal |
| Translation locale seule | Étapes 5 et 6 | Candidat local retenu |
| Translation caméra + translation locale | Étapes 5 et 6 | Candidat local retenu |
| Résidus de directions opposées | Aucune | Filtre de cohérence actif |
| Couche statique proche, contre-exemple de parallaxe | Étapes 5 et 6 | **Échec : faux candidat persistant** |
| Rotation locale | Aucune | **Échec : mouvement réel du contrôle rejeté** |

La première observation locale est à 60 ms et la première sortie persistante à 100 ms : **40 ms supplémentaires pour la confirmation** dans ces contrôles. Ce nombre ne mesure pas le délai depuis un véritable début de mouvement physique. À 140 ms, après disparition du résidu, la sortie est vide ; cela vérifie la remise à zéro, sans reconnaître un arrêt d'objet.

Le contrôle de parallaxe utilise exactement les mêmes correspondances que le contrôle caméra + objet, avec une autre interprétation physique. Un filtre fondé uniquement sur ces correspondances et une similarité globale ne peut pas les distinguer. Augmenter la persistance ne résout donc pas cette ambiguïté.

## Diagnostic sur DSEC train

Trois extraits existants de `zurich_city_04_b`, deux secondes chacun, avec 200 ms d'échauffement. Aucun extrait de validation ni du test réservé n'est utilisé. Les 300 fenêtres mesurées et 30 fenêtres d'échauffement sont conservées. Les paramètres n'ont pas été réajustés après visualisation.

| Extrait | Régions M03 cumulées | Régions persistantes cumulées M10 | Fenêtres avec candidat persistant / 100 | Coût total médian / p95 |
|---|---:|---:|---:|---:|
| `04_b_0` | 151 | 22 | 22 | 13,22 / 15,37 ms |
| `04_b_1` | 177 | 78 | 55 | 15,71 / 17,91 ms |
| `04_b_2` | 167 | 78 | 56 | 21,57 / 25,99 ms |

Ces comptes additionnent les boîtes à chaque fenêtre : **ils ne comptent pas des objets distincts**. Les régions passent de 495 brutes à 178 persistantes, mais le rappel, les fausses alertes et le délai réel restent non évalués, faute de référence de mobilité relue. `real_motion_quality` reste `null` dans chaque rapport.

Le coût inclut lecture, représentation, suivi, modèle global et filtre de candidats. Le rendu et l'export sont exclus. Rejeu CPU non cadencé, OpenCV limité à un thread : pas de mesure d'attente ni de preuve de fonctionnement temps réel à 20 ms. Le troisième extrait dépasse déjà 20 ms en médiane. Les temps M03 historiques ne forment pas une comparaison appariée avec cette campagne.

## Images et limites visibles

Chaque PNG montre la date prédéfinie +1 000 ms de son extrait. À gauche : régions résiduelles M03 en orange. À droite : provisoires en gris, persistantes en vert. Le nombre entre parenthèses est le nombre d'observations consécutives.

![Comparaison de l'extrait 0](../outputs/motion/M10/clips/zurich_city_04_b_0/comparison.png)

Dans l'extrait 0, une région de route disparaît après filtrage ; une boîte reste sur le véhicule à droite. Cette seule image ne permet pas d'affirmer que ce véhicule bouge indépendamment de la caméra.

![Contre-exemple visible dans l'extrait 1](../outputs/motion/M10/clips/zurich_city_04_b_1/comparison.png)

Dans l'extrait 1, le candidat vert reste sur une région de chaussée au premier plan. Le filtre temporel conserve donc aussi des régions du décor. Cette observation qualitative n'est pas transformée en annotation de référence ni en taux de fausses alertes.

Rejeux de deux secondes affichés à 10 Hz, obtenus à partir du traitement à 20 ms : [extrait 0](../outputs/motion/M10/clips/zurich_city_04_b_0/comparison.gif), [extrait 1](../outputs/motion/M10/clips/zurich_city_04_b_1/comparison.gif), [extrait 2](../outputs/motion/M10/clips/zurich_city_04_b_2/comparison.gif). L'affichage sous-échantillonné ne mesure pas la cadence d'exécution.

Autres limites : les petits objets pauvres en points, les objets tournants et les grandes régions peuvent être rejetés ; un mouvement rapide peut rompre l'association. Le calcul de support porte sur les points dans la boîte, sans segmentation d'instance. Les contrôles idéaux ne vérifient pas toute la chaîne événement → suivi.

## Fichiers, reproduction et vérifications

- `src/pfe_events/mobile_candidates.py` : filtre, association et adaptateur image.
- `src/pfe_events/mobile_controls.py` : sept cas à correspondances idéales.
- `configs/m10_mobile_candidates.json` : protocole et seuils fixés.
- `scripts/run_mobile_candidates.py` : contrôles, rejeu train et visualisations.
- `tests/test_mobile_candidates.py` : neuf tests supplémentaires ; **105 tests réussis** dans le projet.
- [Rapport complet](../outputs/motion/M10/summary.json), [contrôles](../outputs/motion/M10/controls.json), [vérification](../outputs/motion/M10/verification.json), [journal des tests](../outputs/motion/M10/tests.log).

```powershell
# Préserver la campagne existante ; utiliser un nouveau dossier.
.\.venv\Scripts\python.exe scripts/run_mobile_candidates.py --output outputs/motion/M10_repeat
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/sync_markdowns.py
```

Les 14 empreintes de sources/protocole et leurs snapshots correspondent aux fichiers exécutés. Les 327 sorties valides du modèle brut, échauffement compris, sont exactement identiques aux références M03 aux mêmes dates. Les trois premières sorties d'initialisation sont invalides. Les grilles temporelles, comptes et trois GIF de 20 images sont vérifiés. Ces contrôles attestent de la cohérence des artefacts, pas de la qualité de mobilité.

## Prochaine étape

Constituer une référence qui distingue réellement mouvement d'objet et déplacement de caméra, en conservant les cas inconnus. Les images d'événements seules rendent certains cas ambigus : auditer un petit échantillon avec poses et masques, tel que la piste EVIMO déjà documentée, avant toute acquisition volumineuse. DSEC reste le jeu principal du PFE.

Comparer ensuite une compensation tenant compte de la géométrie et de la profondeur, avec couverture et abstention, sur des cas de parallaxe contrôlés. Séparer tout diagnostic utilisant poses/profondeurs GT d'un système utilisant des prédictions. Ne pas ajouter de nouvelles heuristiques ou augmenter la persistance sur la seule base d'une diminution du nombre de boîtes.
