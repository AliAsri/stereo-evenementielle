# M06 — Comparer les méthodes à 10 et 20 ms

Date : 4 octobre 2026. Étape technique exécutée ; qualité réelle du mouvement **en attente d'annotations**.

## Ce qui est maintenant disponible

Le même ensemble de zones annotées peut être utilisé pour comparer quatre sorties archivées :

| Méthode | Pas des sorties | Rôle |
|---|---:|---|
| `absolute` | 10 ms | Référence M01 rejouée dans M05 |
| `relative` | 10 ms | Seuil tenant compte de l'activité globale |
| `relative_history` | 10 ms | Seuil global et historique causal |
| `global_residual_20ms` | 20 ms | Résidus après modèle de mouvement apparent global M03 |

Le périmètre est limité aux trois clips train `zurich_city_04_b_0`, `_1`, `_2`, de deux secondes chacun. Les prédictions existantes sont relues ; aucun nouvel entraînement ni rejeu des événements n'a été effectué. La validation et le test réservé ne servent pas à choisir des paramètres.

Exécution réelle : **2 100 sorties mesurées contrôlées** (600 par méthode M05 et 300 pour M03), soit 2 310 lignes avec échauffement. Ce ne sont pas 2 100 scènes indépendantes. Les 300 images d'annotation existantes sont réutilisées.

[Rapport exécuté](../outputs/motion/M06/summary.json) : `PENDING_ANNOTATIONS`, zéro ROI relue fournie, aucun score de qualité réel. L'absence d'annotation ne signifie jamais absence de mouvement ou zéro fausse alerte.

## Pourquoi cette adaptation était nécessaire

L'ancien évaluateur exigeait une prédiction par image d'annotation, soit toutes les 20 ms. Les sorties M05 arrivent toutes les 10 ms. Les réduire à une sortie sur deux aurait pu masquer une réponse précoce. Donner artificiellement une date exacte au début annoté aurait produit une précision injustifiée.

M06 conserve les bornes temporelles originales. Exemple purement analytique : début situé entre 40 et 60 ms, réponse à 50 ms ; le délai est **[-10, +10] ms**, pas un délai exact de 0 ms. La borne négative traduit l'incertitude et ne prouve pas une anticipation.

Le délai est mesuré dans le temps des événements enregistrés. Il n'inclut ni coût CPU, ni attente, ni affichage. Les coûts CPU restent ceux des expériences M03/M05 et ne sont pas remesurés ici.

## Contrats de l'évaluateur

- Pas de prédiction entier, positif, divisant le pas d'annotation, avec même origine temporelle. Les cas 10/20 ms sont supportés ; 50 ms face à des annotations de 20 ms est rejeté.
- Flux complet et ordonné, sans doublon ni trou. Une abstention doit être une ligne explicite `valid=false`, et non une ligne supprimée.
- Toutes les sorties sont contrôlées, même en l'absence d'annotations.
- Bornes d'annotation sur la grille d'origine à 20 ms, sans interpolation ni arrondi.
- Avant un début, une alerte déjà active ou un état inconnu n'est pas compté comme une réponse correcte au début.
- Les annotations incertaines, non relues et « déjà en mouvement » restent exclues de la mesure de début.
- Le critère spatial reste : centre d'une proposition dans la ROI native fixe. Il ne s'agit ni d'AP objet, ni de rappel de suivi.
- Les résultats restent par ROI ; les zones superposées et annotations de plusieurs personnes ne doivent pas être additionnées comme des observations indépendantes.
- Un ancien export contenant des clips de validation reste accepté : ces annotations sont explicitement signalées hors comparaison. Un identifiant inconnu est rejeté. Les indices du fichier original sont conservés dans les résultats.

Les durées d'alerte sont calculées par fenêtres à la cadence de chaque méthode ; elles ne constituent pas une connaissance continue du mouvement entre deux sorties.

## Vérifier le maintien de l'alerte

M05 a montré sur des contrôles artificiels que l'historique peut absorber une source d'activité persistante. Mesurer seulement la première réponse ne suffit donc pas.

L'annotateur M06 ajoute une durée **optionnelle**, explicitement relue, pendant laquelle le mouvement reste observable dans la même ROI après le début certain. Il exporte `active_interval_us` et `continuous_motion_reviewed=true`.

Pour cette durée, l'évaluateur calcule séparément : nombre de fenêtres, fenêtres valides, fenêtres en alerte, fenêtres valides sans alerte et fenêtres inconnues. La fraction d'alerte est conditionnelle aux sorties valides ; la couverture est toujours fournie à côté. Si aucune durée n'est annotée, le résultat est `NOT_ANNOTATED`, jamais une durée supposée jusqu'à la fin du clip.

Ce diagnostic ne permet pas de suivre un objet qui quitte la ROI. Il faut arrêter l'intervalle lorsque le mouvement devient ambigu, s'interrompt ou sort de la zone. Les objets déjà en mouvement au début ne disposent pas encore d'une mesure de maintien dans ce protocole.

## Utilisation de l'annotateur

Ouvrir [l'interface M06](../outputs/motion/M06/annotate.html) dans un navigateur local. Conserver ensemble les dossiers `outputs/motion/M03` et `M06` : les images sont référencées depuis M03.

1. Examiner un clip entier, puis avancer image par image.
2. Dessiner une ROI autour du phénomène et choisir une interprétation. Utiliser « incertain » si le mouvement local ne peut pas être distingué du mouvement apparent du décor.
3. Pour un début observable, marquer le début possible et le début certain.
4. Facultativement, aller à la fin de la période de mouvement continu, utiliser le nouveau bouton, puis cocher la confirmation de relecture de cette période.
5. Renseigner l'annotateur, cocher la relecture du clip, ajouter l'annotation.
6. Exporter `M06_manual_annotations.json` avant de fermer. Les annotations restent en mémoire tant qu'elles ne sont pas exportées.

Ne pas consulter les prédictions pour décider des labels. Une image qui change ne suffit pas à confirmer un mouvement indépendant d'objet. Ces annotations visuelles restent provisoires et doivent être discutées si l'incertitude est forte.

## Commandes

Depuis la racine du projet, dans PowerShell :

```powershell
# Contrôle sans labels : déjà exécuté dans outputs/motion/M06.
# Choisir un NOUVEAU dossier pour toute nouvelle exécution.
.\.venv\Scripts\python.exe scripts/compare_motion_annotations.py --output outputs/motion/M06_check_02

# Après export manuel, exemple de chemin à adapter au fichier réellement obtenu :
.\.venv\Scripts\python.exe scripts/compare_motion_annotations.py --annotations "C:\Users\moali\Downloads\M06_manual_annotations.json" --output outputs/motion/M06_reviewed_01

.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/sync_markdowns.py
```

Le script refuse un dossier de sortie existant. Il sauvegarde quatre rapports, un résumé, l'entrée d'annotations, le manifeste des clips, une interface d'annotation, les sources et les empreintes SHA256 des entrées. Le hash du manifeste M03 est vérifié par rapport à celui enregistré dans M05 avant la comparaison.

## Code et vérification

`src/pfe_events/multirate_evaluation.py` : `evaluate_multirate` valide les grilles, prépare un manifeste temporel à la cadence native des prédictions, appelle l'évaluateur v1 préservé, puis ajoute le diagnostic de maintien. Entrées : manifeste, annotations, dictionnaire de sorties par clip, dictionnaire des pas et horizon de réponse (200 ms par défaut). Sortie : rapport JSON compatible avec les diagnostics v1, enrichi et versionné v2. Dépendances : bibliothèque standard et module local `motion_evaluation`.

`scripts/compare_motion_annotations.py` : charge les archives, adapte les trois variantes M05 au format commun, sélectionne les clips train, préserve les indices d'annotations, lance les quatre évaluations et archive le résultat. Aucun ajustement des seuils.

`scripts/motion_annotation_v2.html` : interface sans prédictions, durée continue optionnelle, bornes et enregistrement désactivés pendant le chargement d'une image. Le changement de ROI, de clip ou de bornes annule la confirmation de durée. L'interface M03 d'origine reste conservée.

**81 tests automatisés réussis**, dont 14 nouveaux contrôles : conservation de l'incertitude, égalité des résultats v1 à même cadence, exposition négative à 10 ms, doublons, trous, abstentions, durée non inventée, indices conservés et comparaison sans labels. Les fixtures de test sont synthétiques, distinctes des annotations réelles.

Les 300 chemins d'images sont vérifiés lors de la génération. La vérification interactive dans le navigateur intégré n'a pas été réalisée : sa politique interdit les URL locales `file:`. L'interface doit encore être vérifiée à l'usage dans le navigateur de l'utilisateur, notamment dessin et export. Cette limite ne concerne pas les tests Python ni l'exécution du comparateur.

## Prochaine étape

Annoter les trois clips sans prédictions, relire les cas observables, puis exécuter la comparaison par ROI. Si les clips ne contiennent pas de début exploitable, conserver ce constat et constituer de nouveaux segments train selon une règle de sélection explicite. Ne pas créer artificiellement des débuts pour obtenir un tableau de délais.

Ces observations permettront ensuite de décider si le seuil relatif est utile et si l'historique doit être modifié. La réduction du nombre de boîtes à elle seule ne permet pas de choisir une méthode.
