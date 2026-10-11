# M05 — Comparaison d'activité absolue, relative et avec historique

Date : 4 octobre 2026. **Prototype et comparaison exécutés : 306 essais artificiels, trois clips train, 67 tests réussis.** Qualité de mouvement indépendant sur DSEC : **non évaluée**.

## Résultat principal

Le seuil relatif rejette la bouffée uniforme artificielle qui déclenchait M01. Dans le contrôle combinant une source locale et cette bouffée, il permet de retrouver une proposition centrée dans la zone locale plus tôt que M01. L'ajout d'un historique local réduit fortement les zones actives, mais absorbe aussi une source persistante : une bonne première alerte ne garantit pas un bon signalement pendant toute la durée du phénomène.

Sur DSEC, les propositions diminuent, mais des régions de route et de décor subsistent dans les figures. Sans annotations relues, **moins de zones ne signifie pas moins de fausses alertes à rappel conservé**. M01 reste la référence. Les deux variantes sont conservées comme expériences, sans remplacement automatique du détecteur courant.

## Hypothèse et variantes fixées avant l'exécution

Le fichier `configs/m05_adaptive_activity.json` fixe les variantes, coefficients, témoins et séquences avant l'exécution. Le seuil absolu 20 événements/(s·pixel), les cellules 16×16, le support minimal et la persistance de 20 ms restent ceux de M01.

| Variante | Définition | Ce qu'elle ne résout pas |
|---|---|---|
| `absolute` | M01 inchangé : taux absolu, support et persistance | Activité de caméra et illumination incluses |
| `relative` | Taux de cellule comparé à la médiane et à la dispersion globale de la fenêtre | Une zone de décor très texturée peut rester atypique |
| `relative_history` | Même contrôle spatial, plus dépassement du niveau local observé dans le passé | Une activité persistante est progressivement absorbée ; ce n'est pas un suivi d'objet |

Pour une fenêtre courante, avec taux `r`, médiane globale `m` et MAD globale `d` :

```text
excès = r − m
seuil_spatial = max(20, 3 × 1,4826 × d)

relative : excès > seuil_spatial
relative_history : excès > max(seuil_spatial, historique + max(20, 3 × déviation_historique))
```

Les conditions de support de M01 s'appliquent aussi. L'historique et la déviation absolue sont des moyennes exponentielles, avec constante de temps 200 ms et `alpha = 1 − exp(−durée/200 ms)`. Les seuils sont calculés avec l'historique **avant** son actualisation. Le niveau courant est ensuite intégré à l'historique, y compris lorsque la cellule est active ; cela explique l'absorption d'un signal durable. La déviation historique n'est pas une MAD temporelle robuste.

Les variantes adaptatives utilisent 200 ms de préchauffage sans sortie valide. La persistance commence après cette période. Le statut de préchauffage est une abstention, pas une affirmation d'immobilité. Le modèle global de M03 n'est pas appelé : il s'agit ici de statistiques d'activité, sans estimation de pose ni compensation géométrique.

Pour préserver M01, le prototype adaptatif réutilise son calcul contrôlé des taux et du support, y compris le calcul interne de ses régions, puis calcule ses propres régions. Le coût mesuré inclut ce travail supplémentaire. Une factorisation du calcul partagé pourra être envisagée après validation de l'intérêt de la variante.

## Comparaison synthétique

Les signaux de M04 sont réutilisés avec seed 42, géométrie 128×96 et durée d'une seconde. Fenêtres de 10/20/50 ms, trois forces de source et cinq positions du début dans la fenêtre. Deux situations positives sont testées : source locale seule et source locale avec bouffée uniforme globale simultanée. Quatre témoins sont examinés : vide, pixel chaud, bouffée uniforme, activité locale artificielle persistante dès le début.

Cela représente **102 situations/configurations temporelles × 3 variantes = 306 essais**, dont 270 positifs et 36 négatifs. La période négative évaluée commence après les 200 ms de préchauffage commun de comparaison. Le témoin d'activité locale persistante est un facteur perturbateur construit de type scintillement local ; il ne constitue pas une scène réelle avec immobilité d'objet prouvée.

Chaque variante répond à 60 des 90 cas positifs ; les 30 cas faibles sont manqués. Ce sont des comptes sur le banc artificiel, pas un rappel d'objets mobiles. Les **45 cas de source locale de la référence absolue** ont les mêmes réponses et délais que M04 au réglage correspondant.

### Exemple à fenêtre 10 ms, force moyenne, cinq phases

| Mesure | M01 absolu | Relatif | Relatif + historique |
|---|---:|---:|---:|
| Source seule : réponses | 5/5 | 5/5 | 5/5 |
| Source seule : délai médian conditionnel | 21 ms | 21 ms | 21 ms |
| Source + bouffée : réponses | 5/5 | 5/5 | 5/5 |
| Source + bouffée : délai médian conditionnel | 105 ms | 21 ms | 21 ms |
| Source seule : fraction de sorties actives dans la ROI après début | 97,3 % | 97,3 % | 9,7 % |
| Bouffée seule : fraction des fenêtres évaluées en alerte | 11,25 % | 0 % | 0 % |
| Activité locale présente dès le début : fraction en alerte | 100 % | 98,75 % | 0 % |

**Interprétation du délai 105→21 ms :** le critère de M04/M05 exige le centre d'une proposition dans la ROI locale. Pendant la bouffée, M01 regroupe une grande partie de l'image en une région dont le centre est hors de cette ROI. Il émet donc déjà une alerte globale ; la mesure de 105 ms indique l'arrivée d'une proposition localisée selon notre critère, pas 105 ms sans aucune activité détectée. Le résultat dépend de ce critère et de la scène construite.

**Interprétation du 9,7 % :** la variante historique conserve le début de la source moyenne mais cesse rapidement de la signaler. Ce défaut serait masqué par une analyse limitée au premier délai. Elle ne doit pas remplacer M01 pour visualiser durablement un objet en mouvement sur la seule base de ses sorties plus rares.

Les cinq phases sont des conditions déterministes et ne donnent pas un intervalle de confiance routier. Les statistiques restent en temps événementiel, sans coût CPU ni affichage. Les signaux ne simulent pas physiquement une caméra, un objet, une profondeur ou une parallaxe.

## Rejeu DSEC : entraînement uniquement

Les trois clips `zurich_city_04_b_0/1/2` de M03 sont repris aux mêmes dates : deux secondes par clip, précédées de 200 ms. Pas de 10 ms : **600 fenêtres mesurées**, chacune traitée par les trois variantes. Aucun nouveau rejeu sur validation, aucun accès au test réservé.

Les données sont lues une seule fois par fenêtre et fournies aux trois détecteurs, chacun avec son état propre. Leur ordre d'exécution tourne entre les fenêtres. Les appels sont séquentiels, le rejeu n'est pas cadencé. Rendu et export sont exclus des temps.

### Proportion moyenne de cellules actives

| Clip train | M01 absolu | Relatif | Relatif + historique |
|---|---:|---:|---:|
| Début, `04_b_0` | 19,45 % | 16,68 % | 0,47 % |
| Milieu, `04_b_1` | 32,97 % | 12,30 % | 1,09 % |
| Fin, `04_b_2` | 50,14 % | 13,57 % | 0,70 % |

Ces nombres mesurent uniquement la surface signalée. Les trois modèles peuvent encore produire au moins une région dans une grande partie des fenêtres. La variante historique en produit dans 72 %, 97,5 % et 99 % des fenêtres selon le clip. Les figures montrent encore du décor sélectionné ; aucune baisse mesurée des fausses alertes n'est revendiquée.

### Lecture partagée + un appel de détecteur : médiane / p95 en ms

| Clip train | M01 absolu | Relatif | Relatif + historique |
|---|---:|---:|---:|
| `04_b_0` | 5,95 / 8,00 | 6,28 / 8,41 | 6,20 / 7,99 |
| `04_b_1` | 6,40 / 9,29 | 6,74 / 9,27 | 6,56 / 9,81 |
| `04_b_2` | 11,03 / 13,47 | 11,42 / 14,09 | 11,30 / 13,78 |

Le coût du seul calcul adaptatif reste ici proche de celui de M01 : environ 2,84–4,98 ms de médiane pour la variante historique selon le clip. Le dernier clip dépasse 10 ms même en médiane lecture+calcul. Aucun fonctionnement garanti à 100 Hz n'est démontré.

Ces colonnes réutilisent le même coût de lecture pour estimer le coût de chaque variante prise séparément. Elles ne représentent pas le temps total de l'exécution des trois modèles, ni une mesure autonome avec acquisition et affichage. Ne pas les comparer directement au chiffre de validation M02 pour conclure à une nouvelle accélération : données, charge et protocole diffèrent.

## Fichiers et reproduction

```powershell
.\.venv\Scripts\python.exe scripts/run_adaptive_activity.py --output outputs/motion/M05_rerun
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
python scripts/sync_markdowns.py
```

Le script refuse un dossier existant. Le dossier `outputs/motion/M05/` contient :

- `summary.json` : protocole, paramètres, versions, résultats par condition et par clip ;
- `synthetic_trials.json`, `synthetic_event_hashes.json`, `synthetic_timelines/` : essais et chronologies artificielles ;
- `train/*/predictions.json` : dates, régions et coûts des trois variantes ;
- `train/*/comparison.png` et `comparison.gif` : panneaux absolu / relatif / historique ;
- `source_snapshot/` : code, paramètres, tests et manifeste d'entrée archivés ;
- `verification.json` : intégrité, unicité des essais, équivalence des 45 cas M04 et contrôles des trois GIF.

Les GIF affichent une fenêtre de 10 ms toutes les 50 ms, à 20 images/s. Ils sont des visualisations échantillonnées du rejeu ; ils ne prouvent pas la latence de calcul du système. La comparaison PNG du clip central a été inspectée.

**67 tests réussis**, dont six nouveaux : source locale/bouffée, préchauffage et persistance, historique antérieur, rejet du futur sans changement d'état, absorption de source persistante et paramètres invalides.

## Décision et suite

Conserver M01, `relative` et `relative_history` comme variantes séparées. Le rejet de la bouffée artificielle justifie de poursuivre la comparaison ; l'absorption d'une activité durable interdit de conclure que l'historique est globalement meilleur.

La prochaine preuve de qualité doit porter sur des annotations réelles relues, avec débuts et maintien du mouvement, pas seulement le nombre de boîtes ou le premier délai. Il faudra adapter le rapprochement temporel de l'évaluateur M03 à ces sorties 10 ms tout en conservant l'incertitude d'annotation de 20 ms. La compensation géométrique avec profondeur reste une autre comparaison nécessaire ; les statistiques de débit ne la remplacent pas.
