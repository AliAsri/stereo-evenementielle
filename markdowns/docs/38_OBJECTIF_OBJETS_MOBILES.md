# Priorité : détecter les objets mobiles

Décision utilisateur du 7 octobre 2026 : « on focus sur la detection des mouvement mobile ».

## Objectif concret

Localiser les objets dont le mouvement est distinct de celui du décor, y compris lorsque la caméra se déplace. Une personne qui marche, un véhicule qui roule ou un objet générique déplacé sont des cibles. Une voiture garée et un bâtiment ne deviennent pas mobiles simplement parce qu'ils produisent des événements.

Les prochaines étapes doivent améliorer cette distinction et en apporter des preuves. Les optimisations M08/M09 restent utilisables ; une nouvelle campagne de micro-optimisation ou un démonstrateur de simple activité n'est plus la priorité immédiate. YOLO, stéréo et XYZ restent des exigences du PFE, avec une place au service de cet objectif.

## État actuel vérifié

| Élément | Ce qu'il apporte | Ce qu'il ne prouve pas |
|---|---|---|
| M01/M05/M09 | Zones d'activité et variantes de calcul | Un objet bouge indépendamment de la caméra |
| M03 | Déplacement apparent global et résidus locaux | Une compensation complète de caméra ; la parallaxe reste confondante |
| YOLO Y01 | Classe et boîte d'un objet | Son état mobile ou immobile |
| Stéréo S01 | Disparité/profondeur avec abstention | Une vitesse monde ou un mouvement indépendant sans pose et temps cohérents |
| M06 | Évaluation temporelle avec incertitude | Une qualité réelle sans annotations relues |

M03 conserve des résidus dans 599/600 fenêtres, notamment sur le décor. Ce chiffre est une fréquence de sortie, pas un taux de fausses alertes. Les 129 tests du projet vérifient des contrats logiciels ; ils ne certifient pas encore la reconnaissance d'objets mobiles en scène réelle.

## M10 : prototype exécuté, validation de mobilité encore à faire

Le filtre de cohérence et persistance est implémenté et exécuté sur sept contrôles idéaux et trois extraits train. La parallaxe reste acceptée et la rotation locale peut être rejetée. Les points 1 et 4 ci-dessous restent à réaliser pour la qualité réelle ; le point 5 devient une piste prioritaire. [Résultats, images et limites M10](39_M10_MOBILE_CANDIDATES.md).

1. Constituer un petit ensemble de référence avec mouvement d'objet et mouvement de caméra distingués. Chercher d'abord les cas observables dans les clips train existants ; les cas ambigus restent inconnus. Les labels de classes DSEC ne sont pas réutilisés comme labels de mobilité.
2. Reprendre les correspondances temporelles de M03 pour estimer le mouvement apparent du décor et sa qualité. Conserver le modèle global comme référence, avec ses limites géométriques explicites.
3. Regrouper les déplacements locaux incompatibles avec le décor, puis tester leur cohérence spatiale et temporelle sur les seules fenêtres déjà reçues. Garder une sortie « candidat mobile » tant que l'origine objet n'est pas suffisamment étayée.
4. Mesurer les fausses alertes du décor, les objets manqués et le délai avec/sans cette cohérence temporelle. Une diminution du nombre de boîtes n'est pas à elle seule un progrès.
5. Si la parallaxe domine les erreurs, comparer une compensation géométrique utilisant profondeur et pose estimées. Une profondeur ou une pose GT ne peut servir qu'à un diagnostic oracle séparé, jamais être présentée comme une prédiction du pipeline.

La confirmation temporelle peut réduire les clignotements mais ajoute du délai. Elle ne supprime pas à elle seule une erreur persistante de parallaxe. Ce compromis doit être mesuré ; aucun nombre de fenêtres ni seuil de mouvement n'est déclaré optimal avant les essais train.

## Cas indispensables à vérifier

| Situation | Comportement recherché |
|---|---|
| Caméra fixe, objet immobile | Pas d'alerte mobile malgré un bruit éventuel |
| Caméra fixe, objet en déplacement | Proposition localisée puis mouvement confirmé lorsque justifié |
| Caméra en déplacement, décor immobile | Rejet du mouvement apparent du décor, ou abstention si le modèle échoue |
| Caméra et objet en déplacement | Séparation du mouvement relatif au décor |
| Objet qui s'arrête | Fin du signalement avec délai mesuré |
| Peu d'événements, occultation ou suivi perdu | État inconnu, pas une conclusion forcée « immobile » |

La rotation d'un objet peut aussi constituer un mouvement : ne pas limiter implicitement la vérité terrain au déplacement de son centre. Un objet qui sort de la zone suivie ne doit pas être interprété comme un objet qui s'arrête.

## Mesures à privilégier

- Faux signalements sur des zones de décor relues et leur durée.
- Réponses manquées et délai de première réponse sur des débuts réellement annotés, avec intervalle d'incertitude conservé.
- Maintien de l'alerte pendant une période de mouvement relue et délai d'extinction après arrêt.
- Localisation par rapport à des boîtes ou masques de référence, lorsque disponibles ; garder distincts les diagnostics par centre de ROI M06 et les mesures de détection d'objet.
- Part d'abstention, couverture, coût de calcul et âge de sortie. Un échec de suivi n'est pas un vrai négatif.

Les seuils sont définis sur train. Les trajets de validation et le test réservé ne servent pas à ajuster la méthode. Une annotation absente ne devient pas un label négatif.

## Données complémentaires : piste vérifiée, non téléchargée

DSEC reste le socle stéréo et routier. Pour lever le manque de référence de mouvement, EVIMO/EVIMO2 est une piste secondaire adaptée : le site des auteurs décrit des poses de caméra et d'objets issues de capture de mouvement, ainsi que des masques et de la profondeur. Il s'agit de scènes intérieures, ce qui limite le transfert direct aux véhicules routiers. [Site officiel EVIMO](https://better-flow.github.io/evimo/).

La documentation indique que les masques codent des identifiants d'objets et que les métadonnées contiennent les poses ; elle signale aussi un échantillonnage irrégulier de la GT lors d'occultations. Un masque d'objet ne doit donc pas être converti automatiquement en masque de mouvement instantané : vérifier poses, repères, dates et visibilité avant cette conversion. [Format officiel de la vérité terrain](https://better-flow.github.io/evimo/docs/ground-truth-format.html).

Statut : audit documentaire seulement. Aucun nouvel échantillon acquis, aucune évaluation EVIMO exécutée et aucun remplacement du dataset principal décidé. Avant acquisition : choisir un échantillon borné, vérifier taille, licence, données de pose utilisables et règles de partition.

## Livrable attendu

Un rejeu où les propositions d'objets mobiles sont distinguées de la simple activité, avec statut candidat/confirmé/inconnu, trajectoire courte si fiable et mesures de délai. Un objet non reconnu par YOLO doit pouvoir être signalé comme objet mobile de classe inconnue. Les coordonnées 3D viennent ensuite lorsque la profondeur est valide ; aucune vitesse métrique n'est affichée sans repère temporel et géométrique approprié.

Cette note fixe le recentrage. Le prototype M10 est désormais implémenté ; la séparation objet/caméra reste non résolue, comme le montre le bilan 39.
