# Progression du PFE

**Journal historique du 3 au 19 octobre 2026.** Les mentions « prochaine étape », « actuel » ou « décision active » ci-dessous décrivent leur date de rédaction. Pour travailler aujourd’hui, utiliser uniquement [la feuille de route active](20_NEXT_STEPS.md). Notes techniques, pas un texte de mémoire.

## Cible locale confirmée et rectification simplifiée — 19 octobre 2026

L'utilisateur choisit explicitement **son PC actuel pour une démonstration locale simple**. Le cahier des charges décrit un Ryzen 5 PRO 7535U, 6 cœurs/12 threads, 16 Go, Radeon intégrée. La lecture CIM a été refusée dans le bac à sable ; l'environnement expose 12 processeurs logiques et un identifiant AMD, sans confirmation matérielle complète. Le parcours CPU existant reste la cible, avec mouvement prioritaire et contexte YOLO/XYZ toutes les 100 ms dataset. Les 20 ms restent un budget de comparaison, pas une performance acquise ni une exigence de latence physique validée. Aucun portage GPU ou nouveau composant.

Correction dans `BilinearRectifier.counts` : les quatre blocs d'indices et de poids sont alloués directement, sans listes de tableaux filtrés puis concaténation. Les contributions de poids nul sont conservées ; leur destination au-delà du dernier pixel est bornée, sans effet sur la somme. Ordre des contributions non nulles, précision, géométrie, fenêtres et contrôles de masse inchangés. Aucun nouveau cache ni worker.

Contrôle apparié sur les **34 fenêtres gauche/droite** du même extrait, événements résidents et ordre avant/après alterné : 34 comptes exactement identiques, **39,77→32,25 ms médians** pour la rectification seule (hors lecture/normalisation/inférence). [Mesures](../outputs/rectifier_buffers_20261019/paired_counts.json). Test ajouté pour les centres entiers, bords, capteur 1×1 et lignes/colonnes uniques ; **342 tests passent**.

Un couple de rejeux Y01 sur les 17 dates : **153 tableaux / 17 lignes scientifiques / 17 messages de mouvement exacts**, quatre contextes. Lecture/représentations **96,55→72,46 ms médians**, calcul jusqu'au mouvement **135,32→103,84 ms**, complet **266,54→224,21 ms**. Première date complète **6850,26→4617,47 ms**, incluse. Les autres postes varient aussi ; ne pas attribuer tout l'écart à la modification ni comparer ces valeurs à une autre session pour conclure à une régression. **17/17 hors budget**, mobilité toujours non validée. [Vérification et empreintes](../outputs/rectifier_buffers_20261019/verification.json). Correction retenue ; contrôle clos, pas de répétition inchangée. La reproduction isolée précédente reste une preuve de sa version sauvegardée, pas d'une nouvelle installation ni du code modifié aujourd'hui.

## Reproduction locale en dossier isolé — 19 octobre 2026

Contrôle du parcours actuel sans changement algorithmique : 40 fichiers de sources/configuration copiés avec empreintes, aucun ancien résultat d'inférence copié. Le précontrôle sur dossier vide échoue comme prévu en listant les huit entrées absentes. Le paquet local des trois artefacts est restauré deux fois sans conflit ; les cinq fichiers DSEC sont copiés localement. Total des huit entrées : **555 080 505 octets**, conservés dans le dossier isolé. Les vérifications de tailles/SHA-256 passent. Aucun téléchargement, entraînement ou publication.

Rejeu avec le Python `.venv-demo` existant, options `-I -B`, répertoire courant et sources dans `outputs/reproduction/isolated_20261019/workspace`. **153 tableaux / 17 résultats scientifiques / 17 messages de mouvement exacts**, quatre contextes, sources et versions identiques au dernier rejeu conservé. Un environnement Ultralytics local au dossier isolé est créé. [Préparation](../outputs/reproduction/isolated_20261019/preparation.json) · [Vérification](../outputs/reproduction/isolated_20261019/verification.json). La comparaison ignore uniquement les chronométrages ; aucune revendication de nouveau gain de vitesse ou de validation physique.

Limites : environnement Python partagé, Windows et polices existantes ; pas d'installation neuve ni de clone GitHub. `scripts/manage_demo_assets.py` et `configs/demo_assets.json` ne sont pas encore suivis par Git localement. La livraison doit inclure ces fichiers et les modifications courantes. README corrigé : résultats du 19 octobre, restauration hors ligne, portée exacte du contrôle. Pas de modification du code ; suite logicielle non répétée, dernier bilan **341 tests**. Ne pas réexécuter ce contrôle inchangé.

## Retour à DSEC : RGB retiré du chemin avant publication du mouvement — 19 octobre 2026

L'utilisateur demande de poursuivre après l'explication de l'impasse d'acquisition. L'accès aux nouvelles références reste en attente ; aucune publication externe ni donnée supplémentaire. Correction de dépendance dans `scripts/run_integrated_demo.py` : publication du mouvement à partir des images rectifiées, puis calcul de l'image native pour YOLO/export. `stereo_event_images(..., include_native=False)` évite ce travail en amont ; son comportement par défaut reste compatible. Une nouvelle mesure additive `native_representation` sépare le coût RGB de la stéréo. Aucun calcul supprimé, aucune cadence source, géométrie ou décision scientifique changée.

Contrôle unique avant/après avec précontrôles tailles/SHA-256, Y01, CPU OpenCV 2 threads, contexte 100 ms dataset, mêmes 17 dates : **153 tableaux / 17 résultats scientifiques / 17 messages de mouvement exacts**, quatre contextes communs exacts. Calcul jusqu'au mouvement **138,05→98,91 ms médians**, complet **225,31→214,46 ms** ; RGB différé **20,78 ms**. Première date complète **4662,76→3067,41 ms**, incluse dans les statistiques. Les autres coûts varient : pas de causalité attribuée à toute la différence ni gain stable démontré. **17/17 hors budget 20 ms** dans les deux parcours, même pour le mouvement ; délai de début et mobilité toujours non validés.

[Preuves et vérificateur](../outputs/native_deferred_20261019/verification.json) · [GIF](../outputs/native_deferred_20261019/after/clip.gif). Sources avant/après conservées localement. Test ajouté : le mode différé ne calcule pas le RGB, conserve les images rectifiées avec et sans worker, et le RGB calculé ensuite reste exact. Suite complète **341 tests réussis** (journal `outputs/native_deferred_20261019/tests.log`). Cette correction est retenue pour son ordre de publication ; pas de nouveau diagnostic EVIMO2, entraînement ou téléchargement. Suite : stabiliser la reproduction du parcours, clarifier matériel/sortie avant toute nouvelle architecture de vitesse.

## Recherche d'accès ciblé : miroir indisponible et coût établi — 19 octobre 2026

Sources officielles relues par le connecteur GitHub : script de téléchargement par archives, réponse de l'auteur avec un miroir Drive, clarification de disponibilité par caméra ; README ETAP également consulté. Le miroir exact répond 404 dans le navigateur et aucun lien ciblé pour les deux séquences gauche n'est vérifié. Coût maximal des deux archives d'après les en-têtes déjà acquis : **23 794 189 038 octets** ; extrapolation des durées de préfixes d'environ 4,2 h, très incertaine. [Preuves et coût](../outputs/motion/independent_reference_20261019/access_review_20261019.json). Aucune nouvelle donnée, inférence, modification de code ou métrique ; 340 tests restent le dernier bilan logiciel, non réexécutés.

Une [demande ciblée](../outputs/motion/independent_reference_20261019/access_request_draft.txt) est préparée pour une issue publique `better-flow/evimo`, mais non envoyée. Décision proposée : autoriser cette publication, choisir une nouvelle acquisition sous plafond de 24 milliards d'octets HTTP / 4 Gio extraits, ou garder le protocole en attente. Aucun de ces choix n'est encore approuvé ; anciens contrôles et acquisition de 512 Mio clos, aucune relance automatique. Cette recherche conclut sur les sources consultées, sans affirmer l'inexistence de tout autre accès.

## Acquisition indépendante bornée close sans référence — 19 octobre 2026

Après proposition puis accord explicite utilisateur, le lecteur existant reçoit un mode `--validation-reference` : deux cibles `eval` figées, allowlist de six fichiers chacune, compteurs communs HTTP/extraction, deux parts de 256 Mio et aucun retry. **340 tests passent**, dont sept nouveaux contrôles. La première exécution ciblée avait échoué sur les permissions du répertoire temporaire Windows ; elle passe en plaçant les temporaires dans le projet. Source exacte du transfert figée avant clarification ultérieure du docstring.

**Résultat : 536 870 912 octets HTTP lus, zéro fichier cible, zéro octet extrait.** Les deux préfixes se terminent encore dans des séquences train ; aucune référence `eval` qualifiée, aucune inférence ni métrique. Douze fichiers anciens revérifiés taille/SHA-256, tous conformes. [Qualification et provenance](../outputs/motion/independent_reference_20261019/qualification.json). La relecture du manifeste ancien IMO aurait dû précéder le transfert : ses 334 325 760 octets montrent déjà que 256 Mio ne suffisent pas à dépasser les deux premiers extraits train. Ne pas répéter cette dépense. Accès clos sans autre cible ni budget ; établir d'abord une voie ciblée ou un coût documenté avant toute nouvelle proposition. Le protocole reste prêt, mais la validation indépendante n'est pas exécutée ; DSEC et les contrôles clos sont conservés.

## Préparation d'une validation indépendante et feuille de route raccourcie — 19 octobre 2026

Après clôture d'ORB, l'utilisateur choisit une préparation avec référence publique indépendante. Sources officielles EVIMO2 relues : proposition de deux nouveaux enregistrements `eval`, un IMO et un SfM rigide, avec profondeur oracle explicite ; le contrôle ne validerait pas le système DSEC complet. Sélection temporelle, comparaisons brut/modèle estimé/témoin oracle, couverture, abstentions et règle d'arrêt décrites dans [le protocole](38_OBJECTIF_OBJETS_MOBILES.md#validation-indépendante-proposée--19-octobre-2026). Acquisition encore à approuver : 512 Mio HTTP cumulés, 4 Gio extraits ; atteindre les séquences dans les archives gzip n'est pas garanti. Aucune donnée acquise, inférence, nouvelle métrique ou modification de code. La page active passe de 249 à 59 lignes ; ses anciens octets sont conservés et hachés dans l'archive en fin de ce journal. README et consignes alignés ; dernier bilan logiciel historique : 333 tests, non réexécutés pour ces documents.

## Contrôle ORB explicitement autorisé — 19 octobre 2026

Après protocole figé et accord utilisateur, un seul front-end ORB400 + contrôle court LK2 + matching Hamming réciproque a été évalué sur EVIMO2 211→217 / objet 6. 381 points source, 297 après contrôle court, 78 appariements ; 23 évaluables et deux corrects ≤3 px, contre 25/20 dans LK sauvegardé. Cible : 102 graines initiales, 57 courtes, 20 appariements, huit évaluables et une correcte (LK : deux évaluables, une correcte). PnP refusé ; les quatre critères prédéfinis échouent. Front-end 31,10 ms sur un appel CPU à froid, hors représentation et pose ; aucune comparaison de vitesse appariée. 333 tests passent, dont sept nouveaux tests ; aucune baseline scientifique recalculée. [Preuves](../outputs/motion/M14_next_sample_20261017/orb_20261019/comparison.json). Hypothèse close, non promue ; DSEC et les anciens contrôles conservés, aucun téléchargement ou nouveau modèle.

## Admissibilité spatiale des 35 candidats hors masque — 19 octobre 2026

Sur les résultats 100 ms déjà sauvegardés, la géométrie intercapteur et l'homographie RGB permettent neuf exclusions conditionnelles d'une explication par seule parallaxe pour toute profondeur positive ; 26 points ont une intersection possible à certaines profondeurs, dont neuf uniquement sous environ 0,49 m. Ce ne sont pas des labels de faux positifs. À la date commune 04_b/134, 16 profondeurs courantes prédites sont déjà disponibles pour les 19 points examinés ; six se projettent dans le masque positif, sans GT injectée ni profondeur ancienne substituée. Les erreurs aller-retour des neuf cas sans intersection restent sous 1 px. Utilitaire de diagnostic ajouté à mod_alignment, hors inférence ; 326 tests passent. Chaîne complète 3D/RGB/homographie et formule concordent à 3,34×10⁻¹³ px sur les 16 cas, contrôle d'algèbre uniquement. [Preuves](../outputs/dsec_mos_parallax_20261019/summary.json). Contrôle clos sans réétiquetage, seuil changé, nouvelle inférence ou reprise EVIMO2.

## Support MOS sur résultats sauvegardés — 19 octobre 2026

Lecture des six références acquises, sans nouvelle inférence : M17 20 ms = 163 suivis dans les masques positifs, 120 évaluables, zéro candidat ; archive 100 ms avec bord corrigé = 156 suivis, 133 évaluables, 23 abstentions et 53 candidats. Il s'agit d'occurrences de points et de deux configurations historiques différentes, pas d'une ablation isolant l'intervalle ou de vrais positifs. Deux dates initiales sans historique. À 100 ms, 35 candidats restent dans le raster zéro non certifié statique et un hors du crop ; pas de précision/rappel/ROC. Les 17/18 snapshots source sont vérifiés ; date commune 04_b/134 : tableaux précédent/courant/profondeur et modèle identiques au démonstrateur actuel. 320 tests passent, dont six contrôles de crop/arrondi/abstention. [Preuves](../outputs/dsec_mos_support_20261019/verified/summary.json). Contrôle de support clos ; admissibilité spatiale des labels encore ouverte.

## Qualification limitée des références DSEC-MOS — 18 octobre 2026

Après protocole écrit puis accord explicite pour six masques et six RGB sous plafond 64 Mio, acquisition HTTP partielle terminée : 12 607 641 octets de corps lus, douze PNG contrôlés par CRC ZIP, tailles et SHA-256. Première sélection arrêtée sans extraction devant une structure de dossiers différente du README ; chemins réels retrouvés dans l'index, reprise au même périmètre et avec budget cumulé. Découverte : masques binaires 1 bit et images 640×440, exactement les 440 premières lignes des six sources MOD déjà datées par M16. Les 40 dernières lignes de la grille événementielle restent inconnues ; parallaxe et exhaustivité non résolues. Aucun rejeu, entraînement ou métrique de mobilité, aucun événement ou poids téléchargé. [Qualification et provenance](../outputs/dsec_mos_reference_20261018/qualification.json). Les 314 tests sont le bilan de la dernière modification du pipeline, non réexécutés ici.

## Publication avant la stéréo courante — 18 octobre 2026

La compensation ne consomme pas la profondeur courante : son calcul et la publication du mouvement précèdent maintenant la stéréo de t, conservée pour les XYZ courants et le futur historique exact. Aucun nouveau modèle, cache, seuil ou essai EVIMO2. Rejeux dédiés Y01 à contexte 100 ms : 153 tableaux, 17 lignes scientifiques et 17 messages de mouvement identiques ; quatre contextes conservés. Calcul jusqu'au mouvement 243,23→169,58 ms médians, calcul complet 246,25→263,42 ms : disponibilité plus tôt sur ce contrôle, pas de gain global démontré. 314 tests passent ; 17/17 dates hors budget de 20 ms, mobilité non validée. [Preuves](../outputs/motion_publication_20261018/verification.json).

## Mouvement avant contexte moins fréquent — 18 octobre 2026

Choix utilisateur explicite : mouvement prioritaire ; classe et 3D moins fréquentes. Parcours réordonné pour publier 17 résultats de mouvement dans `motion.jsonl` avant le YOLO éventuel ; contexte toutes les 100 ms dataset par défaut, quatre appels sur les 17 dates, contrôle explicite à 20 ms. Stéréo interne et profondeur t−100 ms conservées pour la compensation ; aucun contexte ancien projeté sur la scène courante. Âge/source du contexte explicites, non-calcul distinct d'une détection vide. Contrôle 20 ms : toutes les sorties scientifiques du parcours précédent conservées. Contrôle 100 ms : 153 tableaux et 17 modèles exacts ; mêmes objets aux quatre dates communes ; 18 occurrences fraîches, 15 surfaces, 3 abstentions. Calcul médian 277,63→225,14 ms ; disponibilité des indices de mouvement 218,11→220,72 ms (aucun gain propre à cette branche). Comparaison unique hors ligne, autres coûts variables ; 313 tests passent, 17/17 sorties encore hors budget. La fréquence demandée n'est pas atteinte et une présence brève entre dates de contexte peut échapper à YOLO. [Preuves](../outputs/motion_priority_20261018/verification.json). Aucun nouvel entraînement, dataset ou essai EVIMO2.

## Représentations concurrentes intégrées — 18 octobre 2026

Après mesure des sous-postes, priorité à la rectification (~70 ms gauche/droite) plutôt qu'à un cache de lecture (~12 ms). Réutilisation du worker persistant stéréo pour préparer la représentation droite en parallèle de la gauche ; attente avant YOLO, mêmes opérations et ordre d'accumulation par image. Contrôle apparié sur 17 dates, six répétitions alternées par date : préparation résidente 108,32→89,76 ms médians, 306 comparaisons d'images exactes. Rejeux Y01 dédiés : lecture/représentation 118,01→108,98 ms, calcul complet 358,81→315,65 ms médians ; charge/démarrage/autres postes variables, pas d'attribution intégrale du gain global. 153 tableaux et 17 lignes scientifiques conservés exactement ; 77 détections, 66 surfaces, 11 abstentions ; 17/17 dépassements de 20 ms. Pic tracemalloc sur la fenêtre ancre 63,7→69,8 Mio, hors entrées et tables déjà résidentes, pas RSS. 311 tests passent ; erreurs du worker propagées et travail droit terminé avant retour sur erreur gauche. Aucun changement de modèle, fenêtre, seuil ou suivi. [Preuves](../outputs/representation_speed_20261018/verification.json). Prochaine décision : sortie et matériel visés par le budget de rapidité, sans relancer une série de variantes.

## Reproductibilité après audit — 18 octobre 2026

Reprise explicitement demandée après l'audit : contrôle obligatoire des tailles/SHA-256 avant inférence, huit entrées pour Y01, sept entrées de scène et checkpoint explicite identifié séparément avec `--weights`. Précontrôles réels Y01 et Y02 réussis, sans charger le réseau. La cellule de reprise Y01 adapte son appel à la signature de reporting historique ou générée et vérifie le support personne/voiture avant entraînement. Six tests ajoutés, **308 tests réussis** au total ; altération à taille identique ou différente, manifeste incomplet/dupliqué, conservation des contrôles avec poids explicites, API ancienne/actuelle et rejet d'API incompatible couverts. README actualisé avec les coûts enregistrés du 17 octobre. Aucun entraînement, aucun nouveau rejeu, aucune amélioration scientifique revendiquée ; publication Git et reproduction sur clone neuf encore non réalisées. Audit et archives conservés.

## Représentation par récence non promue — 17 octobre 2026

Hypothèse enregistrée avant essai : le comptage sur 50 ms mélange les âges d'événements sur les contours mobiles. Comparaison unique à une image linéaire du dernier événement par pixel, même paire 211→217, mêmes paramètres LK et sélection globale sans masque. Cible 39 coins →35 graines courtes →3 suivis longs ; aucun à erreur ≤3 px (contre un auparavant). Pose acceptée en interne, écarts à la référence 0,270° et 4,661 mm, mais correspondances cibles insuffisamment précises. Représentation + suivi 26,87→28,90 ms médians sur les mêmes tranches résidentes, hors pipeline complet. Non promu ; DSEC inchangé ; 302 tests passent. [Détail et limites](43_M14_EVIMO_AUDIT.md#image-linéaire-du-dernier-événement-non-promue--17-octobre-2026).

## Niveau LK supplémentaire non promu — 17 octobre 2026

Essai unique fixé avant inférence, paire 211→217 / objet 6 : maxLevel long 2→3, autres paramètres et 317 graines identiques. Cible 2→9 suivis, dont 8 comparables : 7 >3 px et 1 ≤3 px, donc aucun gain du nombre de correspondances précises. Global 39→26 suivis ; modèle toujours refusé, 10/21 inliers. Coût LK isolé 5,155→5,564 ms médians en six appels alternés après échauffement ; aucune pose réestimée pour la mesure, correspondances sauvegardées reproduites exactement. 299 tests passent ; niveau 2 par défaut et DSEC inchangés. [Détail](43_M14_EVIMO_AUDIT.md#un-niveau-de-pyramide-supplémentaire-non-promu--17-octobre-2026).

## Contrôle figé 211→217 : cible couverte, suivi long défaillant — 17 octobre 2026

Une inférence globale sans graines imposées : objet 6, 50 coins initiaux →33 après contrôle court →2 après suivi long ; erreurs caméra+objet 5,079 et 1,081 px. Toute l'image : 39 suivis après limites, 26 profondeurs oracle. Modèle refusé pour support spatial 9,592 % sous 10 %, malgré 22 inliers ; aucune pose ni mobilité validée. Le garde-fou ne corrige pas le mauvais suivi cible, non promu. Projections recoupées avec OpenCV ; aperçu inspecté ; 298 tests passent. Pas de changement DSEC ni de seuil. [Bilan et limites](43_M14_EVIMO_AUDIT.md#contrôle-global-sur-211217--objet-6--17-octobre-2026).

## Nouvelle séquence EVIMO2 autorisée, cas sélectionné avant inférence — 17 octobre 2026

Acquisition bornée de la première autre séquence train dans l'archive : `scene15_dyn_test_00_000000`. 334 325 760 octets transférés, 153 736 071 extraits ; six fichiers vérifiés par SHA256. Même protocole de visibilité, sans relâchement : paire 211→217 / objet 6 retenue, déplacement 12,045 cm, 5 608 et 4 853 pixels de masque, marge ≥10 px. Aucune inférence exécutée ; aperçu des références inspecté. 297 tests passent. DSEC et échecs précédents conservés. [Provenance et sélection](43_M14_EVIMO_AUDIT.md#autre-extrait-autorisé--cas-admissible-fixé--17-octobre-2026).

## Recherche de référence mieux visible sans candidat — 17 octobre 2026

Utilisateur autorise l'examen d'un autre objet/intervalle dans EVIMO2 déjà présent, avant toute inférence. Protocole figé : 100 ms exacts, déplacement ≥1 cm, masques ≥1 000 pixels et marge de 10 px aux deux dates, cartes/historique disponibles. Six empreintes d'acquisition vérifiées. 616 paires temporelles exactes, dont 4 sans historique complet et 20 sans cartes ; 220 cas objet/intervalle atteignent le critère de déplacement parmi les autres. 179 échouent à la surface visible, 41 à la marge. Aucun candidat admissible : aucune inférence, aucun seuil révisé, aucun téléchargement. Recherche close, sans conclusion d'absence de mouvement dans le dataset. [Audit](../outputs/motion/M14_visible_control_20261017/selection_audit.json).

## Retour DSEC et vérification du modèle par défaut — 17 octobre 2026

Exécution de `scripts/run_integrated_demo.py` sans poids explicites vers `outputs/demo_y01_20261017`, donc Y01. 153 tableaux et 17 lignes scientifiques identiques au rejeu Y01 `outputs/demo_border_20261015/targeted`, empreintes d'entrée identiques. 77 occurrences détectées, 66 surfaces estimées, 11 abstentions ; aperçu inspecté. Coût médian 270,0 ms, premier appel 3 523,0 ms, 17/17 dépassements de 20 ms. Vérification historique de non-régression uniquement : pas de nouveau gain de vitesse, précision ou mobilité annoncé. Aucun code modifié ; dernier contrôle de tests 296 réussis. [Preuve](../outputs/demo_y01_20261017/verification.json).

## Chaînage temporel non promu — 17 octobre 2026

Contrôle unique sur les trois mêmes graines EVIMO2, cinq pas de 20 ms et seuils inchangés. Survivants : 3, 3, 3, 2, 2 ; un seul passe les limites après correction de distorsion, mais son erreur finale de référence reste 7,716 px. Le deuxième a 8,387 px d'écart et reste hors limites ; le troisième est perdu à 80 ms. Aucun suivi accepté à erreur ≤3 px. Les petits aller-retour locaux ne garantissent donc pas la justesse finale. Données, images communes et projections identiques au contrôle direct vérifiées ; aucune pose ajustée. Suivi à froid 43,38 ms, lecture/représentation 1 235,91 ms, évaluation oracle 307,69 ms ; pas de benchmark de cadence. **296 tests passent**. Essai non promu ; contrôle clos, DSEC inchangé. [Détails et reproduction](43_M14_EVIMO_AUDIT.md#chaînage-unique-par-pas-de-20-ms--17-octobre-2026).

## Reprise limitée EVIMO2 : trois coins non suivables à 100 ms — 17 octobre 2026

Après autorisation explicite, contrôle des trois coins déjà identifiés sur 68→74 / objet 24, sans nouveau dataset ni réglage. Trois contrôles aller-retour courts passent ; zéro long accepté. Erreurs finales de référence : 8,251 / 7,805 / 9,252 px ; aller-retour : 25,450 / 7,303 / 11,304 px. Le masque cible aux arrivées ne suffit pas à valider la correspondance. Aucune pose ajustée ; profondeur et poses oracle utilisées uniquement pour évaluer. Les contrôles existants restent actifs. Améliorer la sélection seule ne résout donc pas ce cas. Fenêtres courtes chevauchantes : pas de preuve de suivi correct à 20 ms. 294 tests passent, projections recoupées avec OpenCV et aperçu inspecté. [Détails](43_M14_EVIMO_AUDIT.md#suivabilité-des-trois-coins-de-la-cible--17-octobre-2026).

## Relecture de fiabilité DSEC et arrêt de la boucle de diagnostics — 17 octobre 2026

Relecture seule des six fichiers `outputs/demo_border_20261015/reference/*_diagnostic.json`, associations à marge nulle : 7 boîtes sans historique ; sur 15 traitables, 4 sans trajectoire, 2 sans profondeur, 6 sans résidu observé, 3 avec candidat exclusif. Les boîtes sans trajectoire sont `04_e/134` tube 6 (54,97 % actifs), `04_e/267` tubes 6, 7, 9 (0,43 %, 3,84 %, 5,56 % actifs). Ce support partiel ne permet pas d'attribuer toutes les absences à un manque d'activité, ni de mesurer la détection indépendante. Pas de modification du solveur ni d'abaissement du seuil justifié. Les anciens contrôles de profondeur et de permutation ne sont pas relancés.

La feuille de route remplace sa proposition répétitive de reprendre les objets manqués par la condition réelle : référence indépendante de déplacement/pose alignée, absente du périmètre local DSEC actuel. EVIMO2 demeure en pause ; aucun nouveau dataset, modèle ou annotation demandé. Aucun code modifié, donc aucune nouvelle exécution de tests ; le dernier contrôle reste 294 tests réussis. Cette étape clarifie le blocage, elle ne constitue pas un gain de fiabilité.

## Appariements stéréo concurrents — 17 octobre 2026

Contrôle ciblé de l'ancre existante à deux threads OpenCV : appariements direct et inverse environ 32 ms chacun ; récupération du bord environ 6 ms ; contrôles environ 14–15 ms. Les trois calculs et les contrôles sont conservés. Un worker persistant exécute l'inverse sur un matcher distinct ; le thread appelant calcule le direct et le bord, puis attend l'inverse avant validation. L'exécution séquentielle demeure disponible dans `predict_stereo` sans executor ; aucune cadence ni recherche de disparité modifiée. Le démonstrateur utilise aussi ce worker pour les profondeurs historiques manquantes.

Rejeu avant/après dédié : stéréo 111,34 → 71,94 ms médians (−35,4 %), calcul complet 310,53 → 257,76 ms (−17,0 % observé). Les autres coûts varient : ce dernier pourcentage ne constitue pas un gain isolé causal de la stéréo. 153 tableaux et 17 résultats scientifiques identiques, entrées identiques, 294 tests passent. 17/17 sorties hors budget 20 ms. Deux tâches d'appariement simultanées utilisent davantage de ressources CPU ; aucun gain universel promis sur d'autres machines. Y01 par défaut, Y02 explicite pour le contrôle, mobilité non validée. [Preuves](../outputs/stereo_speed_20261017/verification.json). Libellé de portée temporelle du résumé corrigé après rejeu pour préciser la concurrence ; empreintes des sources exécutées et mesures conservées.

## Rectification pré-calculée du démonstrateur — 17 octobre 2026

Le profil existant désigne la préparation des images comme premier poste régulier. Contrôle ciblé sur la fenêtre gauche : 364 240 événements, lecture 9,44 ms et rectification 57,54 ms. Ajout de `BilinearRectifier`, qui pré-calcule les destinations et poids par pixel natif, conserve l'ordre des additions et possède ses tables immuables. Utilisé pour les images courantes du parcours intégré ; reconstruction historique inchangée. Tests des collisions, polarités, centres invalides, bords, entrée vide et indépendance vis-à-vis des mutations de la carte.

Huit contrôles alternés sur la même fenêtre : rectification 60,94 → 38,51 ms médians. Rejeu Y02 explicite avant/après sur 17 dates : préparation 149,29 → 136,61 ms, calcul 342,60 → 335,85 ms médians. Moyenne complète 626,18 → 682,86 ms : démarrage et autres étapes variables, pas de gain global robuste établi. Préparation fixe 41,12 ms et 25 190 400 octets de tables. 153 tableaux et 17 lignes scientifiques identiques, empreintes des entrées identiques. **292 tests passent**. Budget 20 ms toujours dépassé sur 17/17 dates ; Y01 reste par défaut et mobilité non validée. [Preuves](../outputs/speed_20261017/verification.json). Aucun ancien résultat supprimé.

## Recadrage sur les blocages majeurs — 16 octobre 2026

L'utilisateur demande de traiter les points majeurs et critiques avant les points secondaires, après constat d'une dérive vers les diagnostics EVIMO2. Ordre conservé : rapidité, fiabilité du mouvement, puis 3D. Branche EVIMO2 et suivi des trois coins au bord mis en pause ; aucune expérience ni donnée supprimée. Reprise prévue sur le coût dominant du démonstrateur DSEC, à partir des mesures existantes, avec une modification et une comparaison avant/après. Les corrections indispensables à la validité des calculs restent prioritaires. [Priorités actives](20_NEXT_STEPS.md#priorités-actives--recadrage-du-16-octobre-2026).

## Grille spatiale à budget constant non promue — 16 octobre 2026

Essai unique 8×6 avec au plus 400 points, seuils et espacement conservés, sur 60→66 et 68→74. La cible reste absente : ses trois coins sont classés 10ᵉ, 27ᵉ et 35ᵉ dans une cellule recevant neuf places. Moins de suivis longs sur les deux paires et surcoût du sélecteur seul de 0,56 à 1,19 ms. Les extrémités des points communs sont identiques. **289 tests passent**, aperçu comparatif inspecté ; sélection globale conservée par défaut. Aucun autre réglage de grille tenté. [Résultats et limites](43_M14_EVIMO_AUDIT.md#répartition-spatiale-à-budget-constant--16-octobre-2026).

## Contrôle positif EVIMO2 : objet absent des graines — 16 octobre 2026

Paire 68→74 / objet 24 sélectionnée exclusivement par poses et visibilité avant suivi : premier déplacement d'origine monde ≥1 cm sur 100 ms, ici 11,29 mm. Le contrôle de conservation du garde-fou est non évaluable : zéro graine initiale sur l'objet partiellement visible. Le budget global de 400 coins est saturé ; les coins de l'objet passent le seuil de qualité mais sont tous moins forts que les 400 sélectionnés. Aucun autre intervalle n'a été essayé pour contourner ce résultat. **284 tests passent** ; références projetées vérifiées sur tableaux sans nouvel ajustement.

Décision : prochaine correction limitée à une meilleure répartition spatiale des 400 points, sans masque GT comme entrée et sans augmenter leur nombre. Le garde-fou natif reste expérimental. [Sélection, mesures et aperçu](43_M14_EVIMO_AUDIT.md#contrôle-positif-et-couverture-des-graines--16-octobre-2026).

## Activité isolée dans les trois correspondances EVIMO2 — 16 octobre 2026

Les trois candidats sauvegardés reposent chacun sur un seul pixel actif dans leur bloc source 5×5, sans activité dans ses huit voisins aux deux fenêtres. Un garde-fou spatial causal exploratoire exclut 19/274 suivis, dont les trois grandes erreurs, 13 correspondances à erreur GT ≤3 px et trois non évaluables. Coût isolé 1,58 ms, hors lecture/comptage ; aucun suivi ni ajustement de pose relancé. **280 tests réussis** et agrandissements inspectés.

Décision : ne pas activer le filtre sur DSEC avant un contrôle positif de conservation des points mobiles ; la rectification peut artificiellement connecter un pixel isolé. [Preuves et compromis](43_M14_EVIMO_AUDIT.md#support-spatial-des-trois-correspondances--16-octobre-2026). Ce contrôle clôt l'examen des trois points sans revendiquer une amélioration de détection de mobilité.

## Contrôle EVIMO2 à pose de référence — 16 octobre 2026

Après autorisation explicite d'utiliser uniquement l'échantillon EVIMO2 déjà présent, contrôle séparé sur les images 60→66 fixées avant résultats (100 ms). Conventions caméra/objet, dates, profondeur axiale en millimètres et distorsion radtan vérifiées dans les sources officielles ; le tableau historique `D` omet les paramètres tangentiels, donc utilisation des coefficients nommés. Six empreintes d'acquisition vérifiées ; aucune donnée supplémentaire acquise.

Un seul ajustement avec profondeur oracle : 274 suivis, 240 profondeurs, écart à la pose de référence 0,139° / 0,642 mm. Les origines d'objet se déplacent peu dans le monde sur cette paire ; elle contrôle surtout la compensation caméra. Les trois candidats gardent des résidus de 4,45 à 7,41 px même avec les poses caméra et objet de référence, alors que leur contrôle aller-retour passe. Cela justifie d'examiner les correspondances et leur support temporel, sans prétendre avoir validé la mobilité ou corrigé la pose DSEC. Aucun changement du parcours principal ni des seuils.

**276 tests réussis**, aperçu inspecté, projections vérifiées indépendamment sur les tableaux sauvegardés sans second ajustement. [Conventions, résultats et reproduction](43_M14_EVIMO_AUDIT.md#contrôle-limité-avec-poses-de-référence--16-octobre-2026). Détails conservés dans M14, sans les dupliquer dans le journal.

## Revue documentaire D01 — 10 octobre 2026

Les deux documents externes de conception et de veille ont été relus et corrigés : références centrales confrontées aux sources primaires, erreurs techniques et contradictions de périmètre traitées, pistes non revalidées identifiées. [Journal et versions corrigées](48_REVIEW_CONCEPTION_BIBLIOGRAPHIE.md). Originaux préservés et sauvegardés avec SHA256 dans `outputs/documentation/D01/`. Cette étape ne lance aucune nouvelle expérience ni entraînement ; les résultats M17 et la prochaine comparaison M18 restent inchangés.

## Terminé

- Cahier des charges fourni lu intégralement.
- Audit récursif du dossier, fichiers cachés compris : dossier initialement vide, aucun dépôt Git ni code existant.
- Environnement observé : Windows/PowerShell, Python 3.14.6, Git et ripgrep disponibles. Environ 44,7 Gio libres sur C: au début de l'audit.
- Recherche ciblée dans les publications et dépôts officiels DSEC, MVSEC, M3ED, EventScape, RVT, SE-CFF, EMatch et EventHub ; fiches bibliographiques avec sources et limites de lecture.
- Identifié le décalage de repère entre annotations DSEC-Detection et disparités DSEC.
- Documentation 00–20, README, architecture Mermaid, décisions et planning de 12–16 semaines créés avec contenu utile ; cahier des charges original conservé.
- Environnement CPU isolé installé et versions verrouillées ; imports vérifiés.
- Échantillon réel `zurich_city_04_e` téléchargé : gauche/droite, calibration, GT et labels ; provenance/hashes conservés.
- Lecteur par fenêtre, rectification d'inspection, comptage, audit calibration et reprojection implémentés.
- Ordre de 119 172 751 événements gauche et 95 364 500 droite vérifié intégralement ; fenêtre causale commune contrôlée.
- Inspection visuelle des vues événementielles et des annotations officielles effectuée.
- Inventaire de classes dans l'archive train des labels produit.
- 13 tests déterministes réussis ; preuves et rapport D00 archivés dans `outputs/reports/`.
- Centralisation demandée par l'utilisateur : copies des fichiers Markdown dans `markdowns/`, chemins relatifs conservés et script de synchronisation avec vérification SHA256. Règle persistante enregistrée dans `AGENTS.md`.

### Étape S01 — 3 octobre 2026

- Ajout de `zurich_city_04_b` et `thun_00_a`, contenant des piétons et voitures ; données originales et provenance conservées.
- Manifeste local par groupe de trajet : `04_e` et `04_b` côté train, `thun_00_a` côté validation, `09_b` réservé et non acquis.
- OpenCV CPU installé et verrouillage des dépendances actualisé.
- Comptage rectifié bilinéaire, trois canaux logarithmiques et normalisation figée sur train implémentés.
- Baseline SGBM avec masque d'activité et contrôle gauche-droite, profondeur prédite via Q et métriques avec couverture implémentés.
- Exécution réelle sur 60 fenêtres ; 723 007 877 timestamps audités dans les six flux.
- 21 tests synthétiques réussis ; 60 fichiers de prédiction relus pour vérifier unités, NaN, profondeur et métriques.
- Figures de référence/prédiction/erreur et exemples de labels produits ; cas d'échec de validation et vue native avec huit piétons inspectés visuellement.
- Rapports JSON/CSV, hashes du code, paramètres, normaliseur et guide S01 conservés. Documentation actualisée et copies dans `markdowns/` synchronisées.

## Étape Y00 terminée — 3 octobre 2026

- Export de 774 PNG événementiels natifs, 4 235 boîtes personne/voiture et partitions train/val par trajet.
- Conservation des timestamps, lignes source, track IDs, exclusions et hashes ; deux exemples négatifs train conservés.
- Paquet Colab de 151,26 Mio créé et vérifié ; normaliseur S01 train-only réutilisé.
- 27 tests réussis ; toutes les boîtes confrontées aux sources ; neuf images régénérées exactement ; vues annotées inspectées.
- Code de chargement Ultralytics 8.4.172 audité pour canaux et augmentations ; framework non installé localement.
- Notebook Colab créé, sept cellules Python compilées, protocole de contrôle puis surapprentissage et cinq époques préparé. GPU non exécuté à cette étape Y00 ; exécuté ensuite dans Y01.

## Étape Y01 terminée ; audit des archives le 4 octobre 2026

Les deux ZIP fournis confirment trois essais : diagnostic initial échoué, diagnostic corrigé réussi, pilote complet de cinq époques terminé. 113 fichiers utiles sont importés (environ 56 Mio), les archives et 155 checkpoints intermédiaires restent conservés à leur emplacement d'origine. Neuf comparaisons de provenance/checkpoints réussissent ; les CSV et figures sont examinés. [Analyse Y01](24_Y01_COLAB_RESULTS.md).

- Contrôle runtime des tenseurs réussi ; neuf boîtes train filtrées par le framework sont comptées.
- Diagnostic corrigé : AP50 99,5 % par classe, 200 pas mesurés. Blocage initial résolu.
- Pilote : 536 images train, 238 validation, mAP50 23,73 %, mAP50–95 13,66 %. Le rappel et les piétons restent faibles.

## En cours / à préparer

- Priorité utilisateur : détection rapide du mouvement. Lecture accélérée M02 et diagnostic global M03 exécutés ; prochaine porte : annotations relues et mesures de réponse/fausses alertes par zone.
- Y02 : reporté dans l'ordre des priorités ; aucun nouvel entraînement lancé.
- Choix EMatch documenté mais conditionnel : compatibilité et VRAM Colab non testées.

## Étape M01 — 4 octobre 2026

- Branche d'activité causale implémentée sur grille 16×16, sans dépendance à YOLO ni classe connue.
- Comparaison 10/20/50 ms sur deux segments centrés de deux secondes ; 748 fenêtres traitées, 680 mesurées après préchauffage.
- Validation à 10 ms : activité médiane 4,47 ms ; lecture+activité 13,38 ms, p95 16,89 ms. Cadence de 10 ms non soutenue par le lecteur actuel.
- Cartes NPZ, CSV, rapports, exemples PNG et deux rejeux GIF produits ; conservation des comptes et des timestamps vérifiée.
- 33 tests réussis, dont six tests de causalité, unités, persistance et support spatial.
- Les zones de décor observées imposent une étude du mouvement de caméra. Délai réel de mouvement et fausses alertes non mesurés faute d'annotations temporelles. [Détail](25_M01_RAPID_ACTIVITY.md).

## Problèmes rencontrés

- M02 améliore le coût médian mais le rejeu autonome de validation dépasse encore 10 ms au p95 (11,32 ms). Aucune GT de début de mouvement n'est encore constituée.
- Pas de données, modèles, environnement isolé ou tests dans le dossier initial.
- Téléchargement depuis le terminal restreint : résolution DNS impossible. Accès au catalogue officiel réussi avec l'exécution réseau autorisée.
- Le lanceur `py` ne recense pas Python alors que la commande `python` fonctionne.
- Création initiale du venv bloquée par les permissions du répertoire temporaire, résolue avec exécution adaptée.
- Coupure du téléchargement gauche, résolue par reprise HTTP.
- Archives de labels imbriquées et sélection ambiguë par chemin absolu, corrigées.
- Aucun piéton dans le premier échantillon ; résolu pour le pilote par l'ajout de `04_b` et `thun_00_a`.
- Couverture limitée de S01 : 36 % de la GT sur validation ; grandes zones de profondeur manquante.
- Coût CPU élevé de la représentation bilinéaire de référence ; le temps réel n'est pas validé.

## Solutions appliquées

- Utiliser les pages et dépôts des auteurs pour les choix techniques.
- Limiter le premier téléchargement à une séquence et aux modalités nécessaires.
- Employer `python` puis le chemin explicite de l'environnement virtuel.
- Fenêtres dans une horloge absolue commune après ajout des offsets propres à chaque fichier.
- Lecture bornée en mémoire et erreurs explicites, sans fausse profondeur ni modèle fictif.
- Extraction des labels train et sélection par chemin relatif ; superposition de huit boîtes au temps inspecté.

## Décisions importantes

- DSEC recommandé comme dataset principal ; MVSEC comme validation secondaire de géométrie, sous réserve de l'audit détaillé.
- Traiter séparément la détection dans la vue native et la profondeur dans la vue rectifiée, avec association géométrique explicite.
- Les résultats de stéréo classique et de YOLO sont disponibles. Le diagnostic corrigé passe ; la validation YOLO reste faible. Ne pas confondre mémorisation du petit lot et généralisation.
- Conserver `04_e` en train/debug. Préférer pour ce petit pilote les séquences `04_b` et `thun_00_a`, moins volumineuses que les premières candidates.
- La première composante profonde obligatoire sera YOLO affiné ; la stéréo profonde est une comparaison ultérieure, pas un prérequis au premier MVP.

## Résultats actuels

Inspection réelle D00, baseline S01, export Y00, pilote Y01, activité M01, lecture accélérée M02, diagnostic global M03 et contrôles artificiels M04 exécutés. Validation stéréo locale `thun_00_a` : EPE 1,045 px, Bad3 4,26 % sur les pixels évalués, couverture GT 36,00 %. MAE de profondeur de surface 1,421 m sur l'intersection valide. Export YOLO : 774 images, 4 235 boîtes. Socle actuel : 67 tests réussis. Voir [résultats détaillés et limites](13_RESULTS.md).

YOLO a été entraîné puis validé sur un autre groupe de trajet. AP50 personne 9,49 %, voiture 37,97 %, rappel moyen 21,67 %. Cette validation sert à la sélection du modèle, pas de test final. Activité causale exécutée ; séparation des objets mobiles et délai réel non évalués. Stéréo profonde et coordonnées d'objets : **NOT RUN**. Le PFE complet n'est pas encore fonctionnel.

## Prochaine étape

Relire les annotations des six clips M03 puis mesurer la réponse et les fausses alertes par ROI. Le prototype global produit encore des résidus de décor et ajoute environ 8 ms de suivi/ajustement : étudier les erreurs avant de modifier les seuils ou d'intégrer cette étape à la branche rapide. [Protocole et limites](27_M03_GLOBAL_MOTION.md). Aucune tâche distante autonome n'est démarrée.

## Étape M02 — 4 octobre 2026

- Lecteur indexé ajouté sans modifier le lecteur binaire de référence ; disponible dans le rejeu par `--reader indexed`.
- 1 496 paires de fenêtres comparées ; événements, cartes et régions identiques, artefacts M01 conservés.
- Sur validation à 10 ms, comparaison appariée : coût combiné médian 10,54→7,70 ms (−27 %), p95 12,27→9,47 ms.
- Rejeu indexé autonome : médiane 8,45 ms, p95 11,32 ms et 14 % de fenêtres au-dessus de 10 ms. Gain confirmé, cadence non garantie.
- 39 tests réussis, six contrôles supplémentaires du lecteur ; 2 992 lignes de mesure et les cartes autonomes vérifiées. Sources exécutées archivées avec hashes.
- Les zones d'activité restent inchangées : aucune amélioration de qualité mouvement revendiquée. [Bilan M02](26_M02_INDEXED_READER.md).

## Étape M03 — 4 octobre 2026 : prototype et outillage

- Suivi de points causal et similarité globale robuste, avec abstention ; régions résiduelles natives sauvegardées.
- Six clips fixes de deux secondes : 660 sorties dont 600 mesurées et 600 images d'annotation sans prédictions. Test réservé intact.
- 599/600 fenêtres avec propositions résiduelles ; des régions du décor subsistent. Ce n'est pas un taux de fausses alertes faute de GT.
- Coût total médian 20,02–37,94 ms selon le clip, pour un pas de 20 ms ; suivi/ajustement médian 8,14–8,62 ms. Cadence combinée insuffisante.
- Annotateur local chargé et rendu inspecté ; évaluateur par ROI testé sur cas synthétiques. Aucun score réel fabriqué avec les annotations absentes.
- 53 tests réussis ; images, timestamps et hashes des sources vérifiés. [Rapport M03](27_M03_GLOBAL_MOTION.md).

## Étape M04 — 4 octobre 2026 : protocole et contrôles

- Deux audits fournis archivés sans modification ; remarques confrontées au code et décisions consignées.
- Protocole JSON figé avant les contrôles : réponse par ROI, incertitude, abstention, comptage des échecs et distinction avec le rappel d'objets.
- 486 essais artificiels et 27 540 fenêtres ; 405 essais de début de source et 81 témoins négatifs. Aucun usage de GT ou de scène DSEC pour ces résultats.
- Réglage M01 : source faible manquée, sources moyenne/forte détectées dans les cinq phases, bouffée globale confondante avec 90 ms d'alerte sur une seconde.
- Contrôle d'annotations ajouté : cible, doublons exacts, exclusions, inventaire par clip. État actuel : zéro ROI réelle relue fournie.
- 61 tests réussis, sources et unicité des essais vérifiées. [Rapport M04](29_M04_MOTION_PROTOCOL.md).

## Étape M05 — 4 octobre 2026 : activité relative et historique

Trois variantes comparées : M01 inchangé, seuil relatif global, seuil relatif avec historique causal. 306 essais artificiels et 600 fenêtres réelles de train (trois clips de deux secondes, trois variantes par fenêtre). Aucun nouveau rejeu sur validation/test.

Le seuil relatif rejette la bouffée uniforme construite. L'historique réduit la proportion de cellules actives sur train, mais dans le contrôle de source moyenne persistante, il ne signale la ROI que pendant 9,7 % des sorties après début, contre 97,3 % pour M01 et le relatif seul. Une amélioration du rappel réel ou des fausses alertes n'est pas démontrée.

67 tests réussis ; 45 réponses/délais de référence sont identiques à M04. Trois GIF et des comparaisons PNG sont disponibles. [Résultats, temps et limites M05](31_M05_ADAPTIVE_ACTIVITY.md). Prochaine porte : annotations relues et évaluation temporelle compatible avec les cadences, puis comparaison géométrique/de profondeur.


## M06 — Évaluation temporelle prête (4 octobre 2026)

- **Terminé :** évaluateur des sorties à 10/20 ms conservant les bornes d’annotation, comparaison de quatre méthodes et annotateur avec durée continue optionnelle.
- **Exécuté :** contrôle de 2 100 sorties mesurées sur trois clips train existants ; aucun nouvel accès test/validation ni rejeu lourd.
- **Vérifié :** 81 tests réussis, dont 14 nouveaux tests des contrats temporels et de la comparaison.
- **Problème résolu :** les prédictions M05 à 10 ms ne correspondaient pas à la grille d’annotation de 20 ms imposée par l’ancien évaluateur. Adaptation sans interpolation ni changement des bornes.
- **Limite restante :** aucun export réel relu fourni ; statut PENDING_ANNOTATIONS. Interface générée, contrôle interactif non effectué car les URL file: sont refusées par le navigateur intégré.
- **Décision :** résultat par ROI, pas de classement de méthodes ni de durée de mouvement supposée.
- **Prochaine étape :** annotations aveugles des trois clips, puis comparaison des réponses, fausses alertes et maintien. [Guide M06](34_M06_TEMPORAL_EVALUATION.md).


## M07 — Stabilité du rejeu cadencé (4 octobre 2026)

- **Terminé :** ordonnanceur causal de rejeu, métriques d’attente et d’âge de sortie, protocole train et traces CSV.
- **Exécuté :** deux séquences train, 12 secondes centrales, pas 10/20 ms, deux répétitions : huit cas complets, 7 200 fenêtres.
- **Résultat :** à 10 ms, retard final de 801,32 et 533,62 ms sur `04_b`. À 20 ms, âge de sortie p95 de 19,96 puis 123,97 ms sur cette séquence ; variabilité, pas de garantie stricte.
- **Problème rencontré :** protocole initial de 20 secondes incompatible avec les HDF5 locaux de 13,401 secondes. Échec avant mesure conservé dans M07 ; protocole 12 secondes exécuté dans M07_12s, avec contrôle de durée ajouté.
- **Vérifié :** 87 tests réussis, 7 200 fenêtres contiguës, mêmes comptes d’événements entre pas/répétitions, détecteur et lecteur inchangés depuis M05.
- **En attente :** annotations réelles relues ; aucune qualité de mouvement ni latence depuis un début physique annoncée.
- **Prochaine étape :** profilage de la fin de `04_b`, optimisation équivalente, comparaison appariée. [Preuves M07](35_M07_PACED_REPLAY.md).


## M08 — Optimisation de lecture à sorties identiques (4 octobre 2026)

- **Terminé :** profilage des trois dernières secondes de `04_b`, sous-classe du lecteur conservant les quatre handles HDF5, benchmark apparié et autonome.
- **Équivalence :** 3 600 fenêtres mesurées + 60 d’échauffement ; tous les champs événementiels et toutes les sorties du détecteur exactement identiques.
- **Résultat :** coût médian lecture + activité réduit de 8,87 à 14,44 % sur les quatre cas train appariés.
- **Rejeu :** huit passages de 12 secondes à 10 ms, 9 600 fenêtres ; âge p95 sur `04_b` de 997,22→261,11 ms au premier passage, mais seulement 358,15→351,19 ms au second. Gain variable, cadence stricte non acquise.
- **Vérifié :** 91 tests réussis, snapshots et onze empreintes vérifiés ; sources du lecteur de référence, du détecteur et de l’ordonnanceur préservées.
- **Décision :** lecteur optimisé disponible pour la suite ; conserver les lanceurs historiques avec leur lecteur d’origine.
- **Prochaine étape :** optimiser le calcul d’activité à sorties identiques ; les annotations M06 restent attendues pour la qualité du mouvement. [Bilan M08](36_M08_CACHED_READER.md).


## M09 — Calcul d’activité optimisé, terminé le 7 octobre 2026

- **Terminé :** table pixel→cellule, extraction des pixels occupés via masque booléen, copies de conversion évitées lorsque possible. Référence M01 préservée.
- **Vérifié :** 96 tests réussis, 3 660 comparaisons exactes des sorties et de l’état, empreintes événementielles identiques à M08.
- **Mesuré :** baisse du coût médian du calcul de 13,07–18,14 % ; lecture partagée + calcul réduite de 7,28–11,40 % dans les comparaisons appariées.
- **Limite :** huit rejeux autonomes (9 600 fenêtres) donnent un effet variable sur le retard ; un passage `04_b` régresse malgré le gain de coût apparié. Pas de cadence stricte garantie.
- **Reprise :** première campagne du 4 octobre interrompue après quatre rejeux ; résultats partiels conservés dans M09. Campagne complète séparée dans M09_20261007, sans regroupement des répétitions de jours différents.
- **Décision :** variante optimisée disponible comme option, mêmes seuils et règles ; ne pas confondre activité et mouvement indépendant.
- **Prochaine étape :** intégrer M08/M09 au démonstrateur avec choix de variante et affichage des retards. Annotations M06 toujours attendues pour la qualité réelle. [Bilan M09](37_M09_LOOKUP_ACTIVITY.md).


## Recentrage utilisateur — 7 octobre 2026

Priorité explicite : détection des objets mobiles. La séparation du mouvement d’objet et du mouvement apparent du décor passe avant de nouvelles micro-optimisations et avant un simple démonstrateur d’activité. Le code M08/M09 reste acquis ; la qualité de mobilité n’est toujours pas évaluée.

**Action réalisée :** objectif, cas caméra fixe/mobile, abstention, mesures de qualité et piste secondaire EVIMO documentés ; consigne persistante et architecture actualisées. **Suite : M10 exécuté ci-dessous** ; référence réelle de mobilité encore à constituer. [Plan](38_OBJECTIF_OBJETS_MOBILES.md).


## M10 — Candidats persistants, exécuté le 7 octobre 2026

- Filtre de support, direction et taille, puis association sur trois observations consécutives ; sorties provisoires/persistantes explicitement non confirmées comme objets mobiles.
- Sept contrôles idéaux : translation locale retenue avec 40 ms supplémentaires de confirmation ; bruit directionnel rejeté. Contre-exemples conservés : parallaxe acceptée et rotation locale manquée.
- Trois extraits train de deux secondes, 300 fenêtres mesurées : 495 régions brutes et 178 régions persistantes cumulées. Pas de qualité réelle déduite de cette diminution.
- Coût total médian 13,22 / 15,71 / 21,57 ms suivant l'extrait ; rejeu non cadencé, sans garantie temps réel.
- 105 tests réussis ; 14 empreintes et snapshots vérifiés ; 327 sorties valides brutes exactement conformes à M03, échauffement inclus. Trois GIF et PNG exportés.
- Prochaine étape : référence de mobilité et traitement géométrique de la parallaxe, avant de nouvelles heuristiques. [Rapport M10](39_M10_MOBILE_CANDIDATES.md).


## M11 — Modèle rigide assisté par profondeur, 7 octobre 2026

- Module PnP/RANSAC avec profondeur au premier instant, contrôle du support, résidus rectifiés et abstention ; provenance prédiction/oracle explicite.
- Référence 3D à deux instants : 9 scénarios × 3 niveaux de bruit × 5 seeds, soit 135 essais et 16 740 correspondances archivées. Pas de simulation du capteur événementiel ni de LK.
- Dans le contrôle de translation caméra devant scène fixe, les 52/124 faux points candidats M03 sont expliqués par M11. Les 16 points mobiles des contrôles de translation/rotation locale sont retenus. Profondeur synthétique exacte dans ces cas.
- Échecs conservés : profondeur locale biaisée et mouvement majoritaire pris pour le décor. Aucune qualité réelle de mobilité annoncée.
- 117 tests réussis ; 135 artefacts relus, résidus recalculés, six empreintes/snapshots et neuf figures vérifiés.
- Inventaire réalisé : 40 profondeurs S01 prédites sur train, espacées d'environ 700 ms. Prochaine étape : suivi rectifié à leurs dates et +20 ms, contrôle de couverture/abstention, puis référence réelle de mobilité. [Bilan M11](40_M11_RIGID_MOTION.md).


## M12 — Modèle géométrique sur DSEC réel, 7 octobre 2026

- Suivi sur images rectifiées 640×480 et profondeur S01 prédite au premier instant ; normalisation figée train, contrôle des dates/calibration/masques, aucune GT dans la décision.
- 40 cartes examinées, 38 paires complètes exécutées ; les deux fins de fichier sans événements jusqu'à +20 ms sont exclues explicitement.
- 14 818 correspondances suivies, 8 630 évaluables (58,2 %), 6 188 inconnues. Sur le support commun, 176 candidats par similarité contre 49 par modèle rigide. Aucune précision/rappel réel ni réduction de fausses alertes déduite.
- Images de 50 ms décalées de 20 ms, chevauchement 30 ms ; approximation temporelle documentée. Pas de suivi continu ni de mesure de début de mouvement.
- Médianes 321,06 / 385,26 ms avec profondeur déjà calculée ; représentation dominante. Cadence 20 ms non soutenue.
- 123 tests réussis ; 15 sources/protocole et snapshots, six fichiers de données, 38 paires et leurs résidus vérifiés.
- Prochaine étape : extraits continus et référence de mobilité relue, puis contrôle du chevauchement et du maintien du signal sur objets mobiles. [Résultats M12](41_M12_REAL_RIGID_MOTION.md).


## M13 — Sensibilité temporelle et paquet de relecture, 7 octobre 2026

- Six extraits train de deux secondes aux indices M12 3/10/17 ; 600 PNG rectifiés sans prédictions, six GIF et six planches produits.
- 24 comparaisons : durées 20/50 ms × écarts 20/50 ms × six dates. Même profondeur prédite S01 au premier instant ; seuil de candidat 150 px/s, seuil RANSAC inchangé.
- Candidats cumulés 2 / 0 / 5 / 3 selon les quatre conditions ; supports différents, aucune configuration déclarée meilleure. Les durées, le chevauchement et les correspondances changent ensemble.
- Six cas 50/20 exactement conformes à M12. 129 tests réussis ; 17 sources/protocole, 600 images et 24 paires contrôlés.
- Outil de relecture et validateur de format disponibles. Aucune annotation réelle relue enregistrée : qualité toujours en attente. Syntaxe JavaScript vérifiée, interaction complète navigateur non testée automatiquement.
- Prochaine étape : relecture des zones et contrôle des indices de mobilité, puis évaluation sur les dates réellement couvertes. [Bilan et accès M13](42_M13_TEMPORAL_REVIEW.md).


## Changement de parcours — annotations manuelles sautées

7 octobre 2026 : demande utilisateur explicite de sauter cette partie. La relecture M13 n'est plus un préalable ; artefacts et diagnostics conservés, aucune annotation inventée. Prochaine étape : audit d'un petit échantillon public avec référence de mobilité exploitable, piste EVIMO/EVIMO2. DSEC reste principal ; aucune donnée supplémentaire acquise et aucune métrique de mobilité réelle ajoutée lors de ce changement.


## M14 — EVIMO2 acquis sans annotations utilisateur, 7 octobre 2026

- Une séquence officielle train, caméra gauche : 239,89 Mio transférés pour six fichiers (594,01 Mio), 62 915 815 événements sur environ 13 secondes.
- 750 paires masque/profondeur sur 782 dates de métadonnées, huit identifiants visibles, 2 603 dates de trajectoire. Les trous de référence restent explicites : jusqu’à 400 ms entre cartes.
- Six hashes vérifiés, toutes les cartes et tous les événements inspectés, lecteur spécialisé de métadonnées sans exécution de classes importées, planche de trois dates fixes produite.
- 137 tests réussis. Pas de métrique de mobilité calculée.
- Prochaine étape : résoudre les champs de calibration divergents et composer les poses dans le monde pour construire la référence de mobilité. DSEC reste principal ; aucune annotation manuelle demandée. [Rapport et aperçu M14](43_M14_EVIMO_AUDIT.md).


## R01 — Nettoyage et refactoring, 8 octobre 2026

- Quatre modules partagés extraits ; seize scripts adaptés, commandes existantes conservées hors protection de sortie neuve pour l’audit EVIMO.
- README simplifié, carte du code et commande `check_project.py` ajoutées.
- 144 tests, syntaxe de 78 fichiers Python et aides de 24 CLI vérifiées.
- Rejeu M11 : 135 cas et 1 620 tableaux identiques hors durées. Audit M14 et aperçu identiques hors provenance.
- 4 381 anciens fichiers de données/résultats inchangés en taille/date, modules algorithmiques existants inchangés par SHA256. Sauvegardes conservées.
- Prochaine étape : petit audit DSEC-MOD, EVIMO conservé en complément, aucune annotation manuelle requise. [Bilan R01](44_PROJECT_MAINTENANCE.md).


## M15 — Référence routière DSEC-MOD, 8 octobre 2026

- Cache officiel et sources figés par commit/SHA256 ; 1 794 boîtes Moving sur 534 frames de `04_e` et `04_b`, côté train uniquement.
- Trois RGB de `04_e` acquis par lectures partielles de l'archive de 15 Go, CRC et hashes vérifiés ; aperçu des annotations produit.
- Deux fichiers de dates RGB DSEC acquis : 269 dates contre 267 images MOD par séquence. Aucun timestamp ni repère événementiel supposé ; aucune métrique réelle de mobilité.
- La réserve `09_b` figure dans le cache commun acquis, mais ses boîtes numériques et images n'ont pas été inspectées. Le groupe `09` traverse les splits MOD officiels ; le protocole local par groupe reste prioritaire.
- Adaptateur spécialisé, commande d'audit hors ligne et neuf tests ajoutés ; 153 tests réussis, syntaxe de 81 fichiers et 25 aides CLI vérifiées. Prochaine étape M16 : correspondance des frames aux dates et repères DSEC, puis comparaison des candidats géométriques. [Audit M15](45_M15_DSEC_MOD_AUDIT.md).


## M16 — Alignement de six références train, 9 octobre 2026

- Vingt-deux RGB originaux DSEC et trois RGB MOD supplémentaires acquis par accès partiel, CRC/SHA256 vérifiés ; deux fichiers d'exposition ajoutés.
- MOD 1/134/267 correspond à DSEC 1/134/267 sur `04_e` et `04_b`. Six dates et 22 boîtes exportées ; aucune extrapolation à toutes les frames.
- Projection RGB rectifié → `camRect0` calculée par calibration ; erreur photométrique moyenne 0,360–0,618/255, candidats voisins nettement moins proches. Translation physique de 4,57 cm non corrigée : parallaxe conservée comme limite.
- Deux planches RGB MOD / RGB reprojeté / activité causale 20 ms produites et inspectées. Les rectangles sont des références publiées, pas des prédictions.
- 164 tests réussis, syntaxe de 85 fichiers et 26 aides CLI vérifiées. Prochaine étape M17 : diagnostic de couverture et candidats dans les boîtes aux six dates, sans labels dans le détecteur. [Rapport M16](46_M16_DSEC_MOD_ALIGNMENT.md).


## M17 — Diagnostic sur références publiques, 10 octobre 2026

- Six dates M16 conservées, profondeur S01 recalculée sans GT ; quatre paires traitées, deux abstentions de démarrage faute des 70 ms d'historique nécessaires.
- 1 558 correspondances, 928 profondeurs exploitables, 630 inconnues ; aucun résidu supérieur à 3 px. Le modèle dominant n'est pas une preuve de pose caméra correcte.
- Sur 22 boîtes : 7 sans historique, 4 sans suivi, 3 sans profondeur, 8 avec points évalués sans résidu. Aucun score de rappel/precision objet annoncé ; marges −5/0/+5 px documentées.
- Deux boîtes sans profondeur contiennent 25 points dans la bande gauche de 96 colonnes, sans profondeur SGBM valide. Les autres limites de support restent distinctes.
- Médiane CPU 654,8 ms avec calcul stéréo frais, hors initialisation et rendu ; cadence 20 ms non atteinte.
- 174 tests réussis, syntaxe de 88 fichiers et aides de 27 commandes vérifiées. Six panneaux, sorties d'inférence, diagnostics, sources et hashes conservés. Prochaine étape M18 : comparer 50/20 et 20/20 ms sur support temporel commun, seuils conservés. [Résultats M17](47_M17_REFERENCE_DIAGNOSTIC.md).

## M18 — Fenêtres 50 ms et 20 ms, 10 octobre 2026

- Quatre dates communes, 15 boîtes, seuils et normaliseur conservés ; profondeur recalculée pour chaque représentation. Les six sorties 50 ms reproduisent exactement M17 hors temps.
- Support de profondeur dans l'union des boîtes : 141 → 72 points ; aucun candidat dans les boîtes. Deux boîtes perdent tout suivi avec 20 ms. Le seul candidat des dates communes est hors référence, sans label négatif certifié.
- Deux dates de démarrage analysées séparément : 20 ms devient traitable, sans candidat dans les sept boîtes. Pas de gain de délai de détection d'objet déduit.
- Médianes CPU 544,96 / 324,08 ms, exécutions uniques hors ligne ; temps réel non atteint. La référence 50 ms est conservée.
- 182 tests réussis, syntaxe de 90 fichiers Python et 28 aides CLI vérifiées ; six panneaux et rapports traçables. [Bilan M18](49_M18_TEMPORAL_WINDOWS.md).

## M19 — Audit statique EMatch, 10 octobre 2026

- 113 fichiers texte officiels figés au commit `92e528bd9d0d1f1d7774385233a841c8bd6eb8d8`, tailles et SHA256 vérifiés, aucun code amont exécuté.
- Entrées nominales : voxels stéréo 100 ms / 15 canaux. Générateur de cache publié avec double conversion temporelle ; provenance effective des caches d'entraînement inconnue.
- Les quatre séquences locales figurent dans la liste train stéréo publiée ; ne pas déclarer le checkpoint indépendant de `thun_00_a` ou `09_b`.
- Poids standard identifiés sur Drive (25,7 Mo affichés), non acquis ni chargés. Aucune installation PyTorch, aucune inférence et aucune mesure GPU.
- Prochaine étape : adaptateur causal et contrôle SGBM 100 ms sur quatre dates train, puis audit binaire des poids et essai isolé. [Constats et protocole M19](50_M19_EMATCH_AUDIT.md).



## Journal détaillé archivé le 15 octobre 2026

Le contenu suivant provient intégralement de l’ancienne feuille de route. Les expériences, mesures et décisions sont conservées ; leurs anciennes consignes de reprise ne sont plus actives.

<details>
<summary>Consulter les étapes et preuves détaillées du 10 au 15 octobre</summary>

# Suivi simple du projet

**Mis à jour le 15 octobre 2026. Cette page est le point de reprise prioritaire.** Les anciennes feuilles de route restent historiques ; les actions EMatch proposées dans M19 sont mises en pause par la décision de simplification.

## Décision active : rapidité, fiabilité, 3D — 14 octobre 2026

Ordre confirmé par l'utilisateur : **1. rapidité, 2. détection fiable, 3. estimation 3D**. Il remplace la priorité précédente donnée à la séparation objet/caméra avant les optimisations. Le parcours reste le démonstrateur intégré existant, un extrait DSEC et un `clip.gif`. Aucune nouvelle architecture ni dataset. Les essais de regroupement ci-dessous restent clos ; la mobilité indépendante reste non validée.

### Étape active Y02 : entraînement reçu et rejeu intégré vérifié — 15 octobre 2026

Après la question sur les autres classes, l'utilisateur a demandé de poursuivre l'extension YOLO. **Décision : commencer par personne/voiture/camion, conserver YOLO11n et les données existantes.** Cette préparation ne remplace pas le modèle actuellement intégré, toujours à deux classes. La vérification de la pose reste un blocage scientifique conservé ci-dessous.

L'ordre des huit classes source a été vérifié dans le [dépôt officiel DSEC-Detection](https://github.com/uzh-rpg/dsec-det#data-format). L'inventaire local porte uniquement sur les dates déjà exportées des trois séquences de développement, sans ouvrir les images du test réservé. Pour les camions : 690 boîtes officielles éligibles dans le train, soit 6 identités de suivi dans `zurich_city_04_e` et 1 dans `zurich_city_04_b`. Ces identités sont propres aux séquences, pas une preuve de sept objets physiques distincts. Après clipping et rejet des géométries inutilisables, **687 boîtes camion** restent exportées.

| Classe YOLO | ID source DSEC → ID YOLO | Boîtes train exportées | Boîtes validation exportées |
|---|---|---:|---:|
| person | 0 → 0 | 864 | 238 |
| car | 2 → 1 | 2 466 | 667 |
| truck | 4 → 2 | 687 | 0 |

**536 images train, 238 images validation.** Les 774 images sont identiques octet pour octet à Y00, les annotations personne/voiture et les partitions par groupe sont conservées exactement. Seules les annotations officielles camion sont ajoutées. Le normaliseur reste celui de S01, ajusté sur le train. Les autres classes restent exclues : le corpus courant contient peu d'identités de bus, rider, vélo et moto et aucun exemple positif de ces classes en validation ; la classe train est absente. Aucun ajout de nom dans la tête du modèle n'est présenté comme une classe apprise.

**Livrables prêts :** [notebook Y02](../notebooks/Y02_yolo11n_truck.ipynb) et [archive de données, environ 159 Mo](../data/processed/dsec_yolo_truck_v1.zip). Le convertisseur et l'exporteur existants acceptent l'extension explicite `--include-truck`, avec profil à deux classes conservé par défaut. Le générateur de notebook existant accepte le rapport d'export et la destination ; Y01 est conservé. Aucun nouveau lecteur ou pipeline de détection parallèle.

Le notebook prévoit les mêmes contrôles de tenseurs, puis un diagnostic de surapprentissage sur huit images couvrant les trois classes (100 époques), et un pilote de cinq époques repartant des poids COCO YOLO11n. Ces budgets sont des diagnostics, pas une promesse de qualité. Les canaux événementiels et les augmentations restent contrôlés. **Préparation initiale :** aucun entraînement n'avait été exécuté localement. L'utilisateur a ensuite fourni le run Colab `Y02_20261015T134856Z`, audité et testé ci-dessous. Le notebook local conserve des cellules sans sorties ; les preuves d'exécution viennent des archives Colab.

**Limite bloquante pour une validation camion : zéro camion dans `thun_00_a`.** Le vérificateur autorise cette absence uniquement si elle est explicitement déclarée pour la classe camion ; il continue à exiger les classes d'entraînement et les deux classes de validation historiques. Le notebook publie une AP camion `null` et `NOT_EVALUATED` sur cette validation, même si le framework fournit une valeur de remplacement. Le checkpoint `best.pt` est choisi sur les classes évaluables personne/voiture : il ne peut pas être qualifié de meilleur modèle camion. Les prédictions sur le train ne constitueront pas une validation indépendante.

**Contrôles locaux : 249 tests réussis.** Le vérificateur complet accepte les deux exports. Le chargeur Ultralytics réel a vérifié six images train/validation, leurs classes, boîtes, canaux et letterbox. Il charge 4 008 boîtes train sur 4 017 exportées, neuf petites boîtes étant filtrées par le framework ; le rapport de tenseurs fournit aussi les comptes par classe. L'aperçu des annotations a été inspecté ; il montre des labels officiels, pas des prédictions. [Préparation et empreintes](../outputs/yolo/Y02_preparation/preparation.json) · [Contrôle des tenseurs](../outputs/yolo/Y02_preparation/tensor-check.json) · [Export](../outputs/reports/Y00_truck_export.json).

**Résultats Colab reçus :** les deux ZIP fournis contiennent 180 fichiers. L'importeur existant accepte désormais `--run` et `--dataset` ; 75 fichiers utiles, environ 42 Mo, sont importés. Les 105 checkpoints d'époque restent dans les ZIP d'origine, sans extraction supplémentaire ni suppression. Les CRC des fichiers retenus et les SHA-256 des archives, du paquet, des poids, du manifeste et du normaliseur ont été contrôlés. Les logs attestent 100 époques de surapprentissage, 200 pas d'optimiseur et cinq époques du pilote. [Audit](../outputs/reports/Y02_colab_audit.json).

| Mesure Colab | Y01 à deux classes | Y02 à trois classes |
|---|---:|---:|
| mAP50, validation personne/voiture | 23,73 % | 38,52 % |
| mAP50–95, mêmes classes | 13,66 % | 20,04 % |
| AP50 person, Y02 | — | 31,22 % |
| AP50 car, Y02 | — | 45,82 % |
| AP50 truck sur validation indépendante | non applicable | non évaluée |

Le diagnostic de surapprentissage Y02 atteint 99,5 % d'AP50 pour chacune des trois classes sur les huit images utilisées pour l'apprentissage. Ce score n'est pas une généralisation. La meilleure époque du pilote selon la mAP50–95 de validation est la deuxième ; cinq époques ont bien été exécutées. La validation finale du checkpoint sauvegardé diffère légèrement de la ligne CSV, avec mAP50 0,385203 contre 0,38544. Ce petit corpus et ces essais uniques ne démontrent pas un gain universel ; la qualité absolue reste limitée.

**Rejeu complet avec le modèle Y02 :** l'option `--weights` du script intégré sélectionne explicitement le nouveau checkpoint et vérifie les classes. Trois exécutions successives ont utilisé Y01, Y02 puis Y01 de contrôle, avec les mêmes données et réglages. Les **153 tableaux et les 17 modèles de mouvement sont exactement identiques**. Le contrôle Y01 reproduit aussi exactement ses détections et associations. Les sorties sémantiques changent naturellement avec Y02 : 42 occurrences person, 24 car et **17 truck**, contre 48 person et 29 car avec Y01. Une occurrence camion est présente sur chacune des 17 images, avec surface XYZ disponible. Le total passe de 66 surfaces/11 abstentions à **74 surfaces/9 abstentions**. Davantage de sorties ne signifie pas davantage de détections correctes.

À la dernière image, la surface associée au camion est estimée à X=−2,73 m, Y=−0,26 m, Z=9,74 m dans camRect0 ; ce point ne constitue pas son centre réel. Le score YOLO vaut environ 0,99, sans interprétation comme probabilité calibrée. **Cet extrait est dans le train** : il valide le raccordement de la classe camion au parcours existant, pas la reconnaissance d'un camion nouveau ni son mouvement indépendant. L'aperçu a été inspecté.

| Calcul CPU médian, hors initialisation/rendu/export | Y01 avant | Y02 | Y01 contrôle après |
|---|---:|---:|---:|
| YOLO | 46,5 ms | 44,8 ms | 45,5 ms |
| Association des boîtes à la surface et aux points de mouvement | 14,7 ms | 51,4 ms | 15,7 ms |
| Chaîne complète | 444,9 ms | 462,5 ms | 395,9 ms |
| Chaîne complète, 12 dernières images | 396,1 ms | 448,1 ms | 388,8 ms |

La charge du poste varie, mais le surcoût de la branche association apparaît dans les deux comparaisons. Le calcul YOLO seul ne présente pas d'augmentation mesurée ici. Le coût supplémentaire de l'association accompagne les nouvelles boîtes, notamment celle du camion plus étendue ; sa cause précise reste à profiler. Aucune accélération ni temps réel revendiqué : toutes les images dépassent le pas source de 20 ms. **250 tests réussis**, dont le refus d'un checkpoint demandé mais absent, sans repli silencieux vers Y01.

**Décision : Y02 est utilisable dans le parcours intégré avec sélection explicite des poids ; Y01 reste la référence par défaut.** [Rejeu Y02](../outputs/yolo/Y02_comparison/y02/clip.gif) · [Comparaison et empreintes](../outputs/yolo/Y02_comparison/verification.json). Aucun nouveau lecteur et aucune modification des seuils de stéréo ou de mouvement.

```powershell
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --weights outputs/colab/Y02_20261015T134856Z/pilot/weights/best.pt --output outputs/demo_y02_repeat
```

### Surcoût de l'association Y02 corrigé — 15 octobre 2026

**Décision : conserver le tri des pixels par indices entiers dans `mapped_roi`.** Le profil sur les cinq détections de l'image finale, tableaux déjà chargés, montre que le tri des couples de coordonnées occupait 333 ms sur 485 ms pour dix associations complètes. Il concerne le calcul de surface et l'association des points de mouvement aux boîtes. Le premier profil incluait aussi des lectures NPZ ; seuls les profils avec tableaux préchargés sont utilisés pour cette attribution.

La fonction encode chaque pixel par `x × hauteur + y`, supprime les doublons par tri d'entiers puis restitue les couples. Elle conserve exactement l'ordre lexicographique x puis y de la fonction précédente, nécessaire au choix du point 3D lors d'égalités. Aucun pixel supplémentaire n'est supprimé ; coordonnées, arrondis, limites, contrôles de profondeur, seuils et modèle sont inchangés. Aucun nouveau cache ou lecteur n'est ajouté.

Trois exécutions successives du même extrait avec Y02, deux threads OpenCV et les mêmes entrées : avant, optimisée, puis contrôle chargeant uniquement l'ancienne fonction dans son processus. Le contrôle consigne cette substitution et l'empreinte de sa source conservée localement.

| Médiane CPU, hors initialisation/rendu/export | Avant | Optimisée | Contrôle original après |
|---|---:|---:|---:|
| Association surface et mouvement aux boîtes | 63,4 ms | 15,4 ms | 56,6 ms |
| Chaîne complète, 17 images | 475,6 ms | 345,8 ms | 452,6 ms |
| Chaîne complète, 12 dernières images | 452,9 ms | 332,8 ms | 435,9 ms |

La réduction de l'association est de **72,7 % par rapport au contrôle après**. Le contrôle isolé de l'image finale, huit appels par méthode avec ordre alterné et tableaux préchargés, passe de **56,3 à 20,8 ms** en médiane. Le profil corrigé réduit le temps propre de tri de 333 à 5 ms pour dix associations complètes. Les temps isolés et ceux du rejeu ne sont pas directement interchangeables. La lecture/représentation et d'autres étapes sont aussi plus rapides pendant le rejeu optimisé : ne pas attribuer toute la réduction du calcul complet à cette seule modification. Le pic de mémoire n'a pas été mesuré.

**Conservation exacte vérifiée : 153 tableaux et les résultats scientifiques des 17 images**, dont les boîtes YOLO, coordonnées XYZ, supports, abstentions et modèles de mouvement. Toujours 83 occurrences détectées, 74 surfaces estimées, neuf abstentions et un camion par image. Les versions et empreintes des entrées concordent dans les trois exécutions. **252 tests réussis** ; les deux nouveaux tests couvrent les collisions de coordonnées, arrondis aux demi-pixels, cartes float32/float64 non contiguës, limites invalides, ordre des pixels, région intérieure et départage du point de surface. Y01 reste le modèle par défaut ; la même optimisation s'applique au chemin d'association partagé.

[Vérification, profils et mesures](../outputs/yolo/Y02_association_speed/verification.json) · [Rejeu Y02 optimisé actuel](../outputs/yolo/Y02_association_speed/fast/clip.gif). Les résultats précédents sont conservés. Toutes les sorties dépassent encore le budget source de 20 ms ; le temps réel et la mobilité indépendante restent non démontrés.

**Prochaine étape :** la qualification du camion sur des données indépendantes reste le blocage principal avant de promouvoir Y02 par défaut. Il faut une séquence DSEC annotée d'un autre groupe ; ne pas déplacer d'images train en validation ni demander d'annotations manuelles. La fiabilité du mouvement reste distincte de la reconnaissance des classes. Le surcoût identifié d'association est traité ; ne pas multiplier les nouvelles micro-optimisations sans décision concrète.

### Reprise ciblée : pourquoi certains objets restent sans indice de mouvement — 15 octobre

Après discussion des limites, l'utilisateur a demandé de passer à l'analyse des objets manqués et à une correction visant une cause précise, avec coût mesuré. Les optimisations acquises restent actives. Les références sont les six dates publiques déjà vérifiées : 22 boîtes, dont sept aux deux dates sans historique suffisant. Avant la correction ciblée décrite ci-dessous, le bilan sur les quatre dates traitables était :

| Situation dans les 15 boîtes | Nombre |
|---|---:|
| Aucun point suivi disponible | 4 |
| Points suivis, sans profondeur exploitable | 4 |
| Points évalués, aucun résidu supérieur à 3 px | 5 |
| Au moins un candidat résiduel | 2 |

Ce tableau décrit le support dans des boîtes, pas une précision/rappel objet. Les références sont partielles, sur le train, et la parallaxe RGB/événements reste une incertitude. Un point dans une boîte peut appartenir au fond.

**Cause concrète confirmée pour deux boîtes : le bord de recherche stéréo.** À `04_b/134`, les 13 points du tube 9 ont leurs pixels précédents entre x=10 et x=53. À `04_b/267`, les 18 points du tube 12 sont entre x=23 et x=71. Avec la recherche SGBM de 96 disparités, les 31 points ont une disparité brute invalide dans cette bande gauche. Ils sont rejetés avant le calcul du résidu de mouvement. Abaisser le seuil de 3 px ou changer le regroupement ne leur donnerait pas de profondeur.

Les deux autres boîtes sans profondeur ont trois points au total, au centre de l'image (x=327 à 340), également sans disparité brute valide. Le défaut de bord ne les explique donc pas. Les cinq boîtes évaluées sans candidat ont des résidus maximaux entre 0,585 et 2,377 px ; ce constat ne permet pas de choisir entre mouvement peu observable, support du fond, erreur de pose ou erreur de profondeur.

**Un seul essai de correction, non intégré :** ajouter 96 colonnes nulles du côté de recherche pour chaque calcul SGBM, recadrer, puis conserver tous les contrôles de support réel et de cohérence gauche/droite. Les boîtes servent uniquement à examiner les sorties après calcul. Sur un plan synthétique texturé de disparité connue 8 px, cette extension donne 10 401 pixels valides sur 10 560 dans la bande testée, contre zéro auparavant, avec une erreur moyenne de 0,00042 px sur les pixels prédits. Aucun pixel n'est accepté dans la zone sans correspondant de ce cas synthétique ; des images vides restent sans profondeur.

Sur les données réelles, cet essai fournit des profondeurs pour 10/13 et 18/18 points des deux boîtes de bord. **Ces 28 valeurs ne sont pas des profondeurs validées, ni 28 détections de mouvement.** Les trois points manquants au centre restent sans profondeur. L'extension modifie aussi 9 953 à 14 835 pixels hors de la bande gauche sur les trois paires examinées ; ces changements ne sont pas automatiquement des erreurs, mais dépassent la correction ciblée. La médiane du calcul stéréo seul augmente de 9 à 11 ms, environ 12 à 15 %, sur trois appels par méthode et par paire. Ces temps isolés ne se comparent pas directement à ceux du démonstrateur complet.

**Décision : rejeter cette extension globale pour l'intégration.** Cet essai a conduit au traitement limité au bord décrit ci-dessous. Ne pas réduire le seuil de mouvement, utiliser les boîtes pour guider l'inférence ou déclarer les zones non annotées statiques.

[Preuves, code de l'essai et décision](../outputs/focused_truck/missed_depth_check.json). Les profondeurs de départ ont été reproduites exactement aux trois dates examinées ; les répétitions stéréo sont identiques. Les catégories, les effectifs et les empreintes des résultats sources ont été vérifiés. Les gros fichiers d'événements bruts n'ont pas été rehachés pendant ce premier contrôle. Cet essai global n'avait modifié aucun code applicatif ni résultat historique.

### Correction du bord gauche conservée — 15 octobre 2026

`predict_stereo` effectue désormais un calcul supplémentaire sur une bande recadrée : les 96 premières colonnes et le contexte du bloc SGBM, avec une marge nulle identique dans les deux vues. Seules les disparités brutes auparavant invalides de cette bande peuvent être complétées. La vérification droite/gauche reste calculée sur les images natives, avec les contrôles de coordonnées et de support événementiel existants. Aucun seuil de mouvement, boîte de référence ou nouveau modèle ne guide cette correction. La politique est consignée dans `StereoConfig.to_dict()` et le résumé du démonstrateur.

**Décision : conserver cette correction bornée.** Elle résout une absence systématique de profondeur observable au bord, au prix d'un calcul supplémentaire. Elle ne constitue pas une optimisation de vitesse. [Vérification complète](../outputs/demo_border_20261015/verification.json) · [Rejeu actuel](../outputs/demo_border_20261015/targeted/clip.gif) · [Essai isolé préalable](../outputs/focused_truck/targeted_border_check.json).

Sur le même extrait de 17 images, YOLO conserve ses **77 occurrences**, les images et les trajectoires sont exactement identiques. Toutes les disparités hors des 96 premières colonnes, toutes les profondeurs déjà disponibles et les 45 estimations de surface antérieures sont conservées exactement. **21 estimations de surface supplémentaires** deviennent disponibles : **66 estimations et 11 abstentions**. Ce sont des occurrences dans des images, pas 66 objets uniques ni 66 positions validées.

Les quatre dates publiques traitables ont été recalculées depuis les événements, les boîtes n'étant consultées qu'après l'inférence. La boîte `04_b/134`, tube 9, passe de 0 à 10 profondeurs exploitables sur 13 trajectoires, avec 10 candidats résiduels. La boîte `04_b/267`, tube 12, passe de 0 à 18 profondeurs sur 18 trajectoires, sans candidat résiduel. Sur les 15 boîtes : **3 avec candidat, 6 évaluées sans candidat, 2 sans profondeur et 4 sans trajectoire**. Les sept boîtes sans historique restent inconnues. Ce bilan partiel sur le train ne mesure pas une précision/rappel objet.

**Contrôle de profondeur réel, limité à une date exactement alignée :** à `36614000936`, 3 577 des 10 269 nouveaux pixels disposent d'une disparité DSEC de référence. Sur ces 3 577 pixels, l'erreur moyenne est **0,851 px** et **180 pixels, soit 5,03 %, dépassent 3 px d'erreur**. La couverture de l'ensemble des pixels de référence de cette image passe de 39,14 % à 44,24 %. L'erreur moyenne sur les pixels évaluables passe de 1,042 à 1,020 px ; les ensembles évalués diffèrent. Les pixels sans référence, les autres dates, les profondeurs historiques utilisées pour le mouvement et les nouvelles coordonnées XYZ ne sont pas validés par ce seul contrôle.

**Effet sur la pose :** les nouvelles profondeurs alimentent le même ajustement robuste. Les 17 modèles restent valides selon les critères internes, mais **550 statuts de points déjà évalués changent** : 266 deviennent candidats résiduels et 284 redeviennent compatibles avec le modèle. Les 301 nouvelles profondeurs suivies donnent 256 candidats et 45 points compatibles. Ces occurrences ne sont pas indépendantes. La conservation des anciennes profondeurs ne garantit donc pas la conservation du modèle de caméra ni une meilleure détection réelle.

| Médiane de calcul CPU, hors initialisation/rendu/export | Avant | Correction ciblée | Contrôle original après |
|---|---:|---:|---:|
| Chaîne complète, 17 images | 357,4 ms | 417,2 ms | 450,2 ms |
| Chaîne complète, 12 dernières images | 347,2 ms | 371,3 ms | 428,3 ms |
| Stéréo courante | 113,1 ms | 130,3 ms | 130,3 ms |

La charge du poste varie nettement : ces trois exécutions ne permettent pas d'isoler précisément le surcoût complet. L'essai stéréo isolé sur quatre paires donnait un ajout de **6 à 18 ms**. Aucun gain de vitesse n'est revendiqué ; les 17 sorties dépassent toujours les 20 ms du pas source. Le contrôle après, avec la fonction d'origine chargée uniquement dans son processus et explicitement consignée, reproduit exactement les **153 tableaux et les résultats scientifiques avant correction**. Les entrées et versions concordent ; les fichiers bruts ont été rehachés pour ces rejeux.

**Tests : 243 réussis.** Les nouveaux tests couvrent la récupération de plans synthétiques de disparité 8, 32 et 80 px, la conservation de l'intérieur et des profondeurs antérieures, l'absence de mutation des images et le manque de support. Un autre motif synthétique révèle quatre correspondances imparfaites parmi 1 024 pixels occultés, toutes au pixel voisin de la limite d'occlusion, avec une erreur au plus égale à 1 px : les contrôles ne garantissent pas l'absence de toute erreur de correspondance. Le test d'images vides reste réussi. L'aperçu du nouveau rejeu a été inspecté ; les avertissements de mobilité non confirmée restent visibles.

**Prochain blocage concret :** distinguer, sur ce même extrait et avec les références déjà disponibles, l'effet des profondeurs récupérées de l'instabilité de la pose dominante. Les 550 changements de statut empêchent de conclure que davantage de candidats signifie davantage d'objets correctement détectés. Ne pas ajouter de regroupement ou abaisser le seuil avant cette vérification ; conserver le coût de calcul comme critère de décision.

### Première optimisation conservée : réutiliser les calculs historiques exacts

La branche mouvement relisait et reconstruisait les images à t−100 ms et t−80 ms, et recalculait la stéréo à t−100 ms, même lorsque ces sorties avaient déjà été calculées comme images courantes. `ClipMotionCache`, dans le module existant `clip_motion.py`, conserve maintenant jusqu'à six résultats courants du même rejeu. Le démonstrateur l'utilise par défaut. Sur un manque de cache, le calcul original depuis les événements reste utilisé.

La recherche porte sur un timestamp exact, sans profondeur ancienne substituée, interpolation, image future ni lecture de prédictions sauvegardées. Le cache appartient aux mêmes lecteurs, cartes de rectification, calibration et normaliseur ; ces paramètres restent fixes pendant le rejeu. Il possède des copies non modifiables, et reste borné à six dates dans les 100 dernières ms (12,9 Mo de tableaux à 640 × 480, hors autres données du pipeline). Suivi, seuils, YOLO et calcul XYZ restent inchangés.

Mesure séquentielle sur le même extrait de 17 sorties, CPU et bibliothèques identiques : exécution originale, exécution avec cache, puis contrôle sans cache pour observer la variation du poste. [Données et vérification](../outputs/demo_speed_20261014/verification.json).

| Mesure, hors rendu/export | Original avant modification | Avec cache | Contrôle sans cache après |
|---|---:|---:|---:|
| Calcul médian sur 17 sorties | 956,1 ms | 568,9 ms | 885,4 ms |
| Calcul médian après la première sortie | 951,1 ms | 558,3 ms | 883,4 ms |
| Calcul médian sur les 12 dernières sorties | 951,1 ms | 507,5 ms | 887,7 ms |
| Branche mouvement, médiane sur les 12 dernières sorties | 488,1 ms | 74,2 ms | 462,4 ms |

**Décision : conserver l'optimisation.** Gain médian observé de 35,7 % par rapport au contrôle sans cache après, ou 42,8 % sur les 12 sorties disposant de la stéréo historique en mémoire. Ces trois exécutions ne constituent pas une garantie statistique ou matérielle. Les premières sorties incluent les coûts de démarrage ; ne pas interpréter leur différence comme un gain du cache.

Les 153 tableaux sauvegardés et les résultats scientifiques des 17 images sont exactement identiques dans les trois exécutions, ainsi que les versions et empreintes des entrées. Les temps et informations de réutilisation diffèrent. La stéréo passée est réutilisée 12 fois et l'image de contrôle à t−80 ms 13 fois. Toujours 77 occurrences YOLO, 45 surfaces estimées et 32 abstentions. Les 17 sorties dépassent encore le budget source de 20 ms : **le temps réel n'est pas atteint**, et le GIF conserve son rejeu ralenti ×5.

**Contrôles :** 233 tests réussis, syntaxe de 115 fichiers Python et 41 aides CLI vérifiées ([rapport](../outputs/demo_speed_20261014/checks/report.json)). Les quatre nouveaux tests couvrent la reproduction des trajectoires et du modèle sur une translation synthétique, le refus de dates approximatives, de données futures ou d'un autre contexte, ainsi que la mémoire bornée et les copies non modifiables. L'aperçu du rejeu optimisé a été inspecté ; les limites de mobilité et les abstentions restent visibles.

Commande habituelle, dossier de sortie neuf :

```powershell
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --output outputs/demo_speed_repeat
```

Ajouter `--no-history-cache` pour désactiver cette réutilisation dans un autre dossier neuf. Cette option ne désactive pas l'optimisation des représentations décrite ci-dessous. [Rejeu avec cache](../outputs/demo_speed_20261014/cached/clip.gif). `outputs/demo` et tous les résultats précédents restent conservés.

### Deuxième optimisation conservée : accumulation des événements

Dans `representations.py`, les comptes natifs et la projection bilinéaire utilisent maintenant `np.bincount` à la place de `np.add.at`. La rectification valide les coordonnées sans construire une image native inutilisée. Les contributions bilinéaires gardent le même ordre d'accumulation, y compris lorsque plusieurs événements et plusieurs décalages aboutissent au même pixel. Aucun seuil ni paramètre scientifique n'est modifié. Les tableaux temporaires dépendent du nombre d'événements ; le pic de mémoire de cette étape n'a pas été mesuré.

Trois rejeux du même extrait de 17 sorties, avec le cache historique actif dans les trois cas : avant modification, accumulation optimisée, puis contrôle avec les fonctions originales chargées uniquement dans le processus. Le contrôle consigne cette substitution dans son `summary.json` ; le code original est conservé localement dans `representations_original.py`. [Mesures et comparaison exacte](../outputs/demo_speed_20261014/representations_verification.json).

| Mesure médiane, hors rendu/export | Avant | Optimisé | Contrôle original après |
|---|---:|---:|---:|
| Calcul complet, 17 sorties | 581,1 ms | 462,3 ms | 565,0 ms |
| Lecture et représentations, 17 sorties | 276,8 ms | 190,7 ms | 286,4 ms |
| Calcul complet, 12 dernières sorties | 564,9 ms | 456,9 ms | 552,1 ms |

**Décision : conserver l'optimisation.** Réduction de 18,2 % du calcul médian par rapport au contrôle après, et de 33,4 % pour la lecture et les représentations. Ce résultat porte sur un extrait court et trois exécutions locales ; il ne garantit pas le même gain sur tout matériel ou toute séquence. Le chargement initial du programme et le rendu/export sont exclus ; le premier appel d'inférence reste inclus dans la première sortie.

Les **153 tableaux et les résultats scientifiques des 17 images sont exactement identiques** avant, après et dans le contrôle. Les entrées et versions concordent. Toujours 77 occurrences YOLO, 45 surfaces et 32 abstentions. Toutes les sorties dépassent encore 20 ms : **temps réel non atteint, mobilité indépendante non validée**. [Rejeu optimisé actuel](../outputs/demo_speed_20261014/representations_fast/clip.gif), toujours ralenti ×5.

**Contrôles :** 236 tests réussis, syntaxe de 115 fichiers Python et 41 aides CLI vérifiées ([rapport](../outputs/demo_speed_20261014/representations_checks/report.json)). Les trois nouveaux tests couvrent les collisions de comptes natifs, l'égalité exacte de la projection bilinéaire avec l'accumulation séquentielle (cartes float32/float64 et limites), et le rejet d'événements invalides. L'aperçu du rejeu a été inspecté : les abstentions et la mention « mouvement propre non confirmé » restent visibles.

Le contrôle du coût de la stéréo courante a conduit au réglage d'exécution ci-dessous.

### Troisième optimisation conservée : deux threads OpenCV

Sur la paire réelle à la date finale, les deux appels SGBM représentent environ 84 % du temps de `predict_stereo` dans un profil ponctuel (87 ms sur 104 ms). La création du matcher et les opérations de contrôle coûtent beaucoup moins. Un essai alternant un et deux threads conserve exactement les disparités brutes, les disparités filtrées, le masque et les compteurs d'abstention ([mesure locale](../outputs/demo_speed_20261014/stereo_threads_probe.json)).

Le démonstrateur utilise désormais **deux threads OpenCV**, avec PyTorch toujours à un thread. Cela permet à OpenCV de paralléliser ses opérations existantes ; le script traite toujours les étapes et les dates dans le même ordre. SGBM, la vérification gauche/droite, les fenêtres temporelles et tous les seuils restent identiques. Le réglage est consigné dans `summary.json`, champ `cpu_execution`. L'option `--opencv-threads 1` permet de reproduire le contrôle. Elle ne désactive ni le cache historique ni l'accumulation optimisée.

Trois rejeux complets du même extrait, effectués successivement avec un, deux, puis un thread :

| Médiane, hors rendu/export | Un thread avant | Deux threads | Un thread après |
|---|---:|---:|---:|
| Calcul complet, 17 sorties | 484,2 ms | 444,2 ms | 508,0 ms |
| Stéréo courante, cache inclus | 171,7 ms | 138,9 ms | 166,1 ms |
| Calcul complet, 12 dernières sorties | 479,1 ms | 438,8 ms | 484,8 ms |

**Décision : conserver deux threads par défaut.** Réduction observée de 8,3 à 12,6 % du calcul médian complet par rapport aux deux contrôles, et de 16,4 à 19,1 % pour la stéréo courante. La charge du poste varie : la lecture/représentation, qui n'est pas directement modifiée par ce réglage, est aussi plus rapide pendant l'essai à deux threads. Ne pas attribuer tout l'écart du pipeline à la parallélisation ni le comparer directement aux mesures d'une autre session. La consommation et le pic de mémoire n'ont pas été mesurés.

Les **153 tableaux et les résultats scientifiques des 17 images sont exactement identiques** dans les trois rejeux ; les versions, empreintes d'entrée et règles de réutilisation concordent. Toujours 77 occurrences YOLO, 45 surfaces estimées et 32 abstentions. [Vérification](../outputs/demo_speed_20261014/threads_verification.json) · [Rejeu actuel](../outputs/demo_speed_20261014/threads_two/clip.gif). Les 17 sorties restent au-dessus de 20 ms : le temps réel et la mobilité indépendante restent à démontrer. Le GIF reste ralenti ×5.

**Contrôles :** 237 tests réussis, syntaxe de 115 fichiers Python et 41 aides CLI vérifiées ([rapport](../outputs/demo_speed_20261014/threads_checks/report.json)). Le nouveau test compare exactement les disparités brutes et filtrées, les masques et les compteurs entre un et deux threads sur un décalage synthétique avec occlusion et zones sans activité ; le réglage initial de threads est restauré après le test. L'aperçu du rejeu a été inspecté et conserve les limites affichées.

Le contrôle suivant traite la reprojection de profondeur utilisée par le suivi. Le nombre de threads reste fixé à deux ; aucun contrôle de fiabilité n'est supprimé.

### Quatrième optimisation conservée : profondeur aux seuls pixels échantillonnés

La branche mouvement projetait toute la disparité historique, soit 307 200 pixels, en XYZ avant d'échantillonner la profondeur d'au plus 400 points. `sample_disparity_depth`, dans le module existant `rectified_tracking.py`, projette désormais uniquement les pixels nécessaires avec la même matrice Q. La sélection des pixels est partagée avec le sampler historique : arrondi `floor(x+.5)`, masque, refus des bords hors carte et conservation de la première occurrence d'un pixel. Le contrôle XYZ complet, le rejet des points derrière la caméra et l'arrondi float32 des profondeurs sont conservés. Les coordonnées de projection sont celles du pixel arrondi, pas celles du point subpixel.

La disparité reste calculée sur l'image entière, à la même date t−100 ms ; les positions XYZ associées aux objets restent calculées comme auparavant. Aucun point de suivi ni seuil n'est supprimé. Une carte XYZ/de profondeur complète n'est simplement plus construite pour le suivi. Le pic mémoire du processus n'a pas été mesuré.

Trois rejeux du même extrait, avec cache, accumulation optimisée et deux threads actifs : avant modification, projection ciblée, puis contrôle avec l'ancienne fonction `infer_clip_motion` chargée uniquement dans le processus. Le contrôle conserve le helper partagé d'échantillonnage actuel ; cette substitution et le code original sont identifiés dans son `summary.json`. [Mesures et vérification](../outputs/demo_speed_20261014/depth_verification.json).

| Médiane, hors rendu/export | Avant | Projection ciblée | Contrôle après |
|---|---:|---:|---:|
| Calcul complet, 17 sorties | 471,0 ms | 420,8 ms | 442,2 ms |
| Branche mouvement, 17 sorties | 80,3 ms | 35,0 ms | 79,3 ms |
| Calcul complet, 12 dernières sorties | 448,7 ms | 400,1 ms | 436,5 ms |

**Décision : conserver l'optimisation.** Gain observé de 4,8 à 10,6 % sur le calcul médian complet, et d'environ 56 % sur la branche mouvement. La charge du poste varie entre les trois exécutions ; ne pas généraliser ces pourcentages à d'autres séquences. Un contrôle isolé de reprojection/échantillonnage, sur les 369 points retenus à la dernière date et leur disparité historique, donne 32,97 ms contre 0,63 ms (médianes de cinq appels alternés), avec les mêmes profondeurs. Ce dernier chiffre n'est pas une latence du pipeline complet.

Les **153 tableaux et les résultats scientifiques des 17 images sont exactement identiques** avant, après et dans le contrôle. Toujours 77 occurrences YOLO, 45 surfaces estimées et 32 abstentions. [Rejeu actuel](../outputs/demo_speed_20261014/depth_sparse/clip.gif), toujours ralenti ×5. Les 17 sorties dépassent encore 20 ms : temps réel non atteint et mobilité indépendante non validée.

Les mesures internes séparent maintenant `previous_stereo`, `depth_sampling` et `tracking` ; l'ancien champ `previous_stereo_depth` reste uniquement dans les résultats historiques. Comparer les temps complets de branche pour éviter de confondre ce changement de découpage avec un gain.

**Contrôles :** 239 tests réussis, syntaxe de 115 fichiers Python et 41 aides CLI vérifiées ([rapport](../outputs/demo_speed_20261014/depth_checks/report.json)). Les deux nouveaux tests comparent les profondeurs et les statistiques à la projection complète sur des matrices Q canonique, générale, singulière et avec points derrière la caméra ; ils couvrent aussi arrondis, doublons, trous, bords, valeurs invalides et liste vide. L'aperçu du rejeu a été inspecté ; les limites restent affichées.

La lecture/représentation a fait l'objet de la simplification suivante, sans changement de fenêtre ni de méthode.

### Cinquième optimisation conservée : calcul des indices de rectification

Le profil de la lecture/représentation montre que la rectification domine cette étape. Dans `rectified_counts`, chaque événement recalculait ses indices de destination pour chacun des quatre décalages bilinéaires. La base entière est maintenant calculée une fois, puis décalée. Les poids flottants, leur ordre d'accumulation et les contrôles restent identiques. Aucun cache supplémentaire ni nouvelle configuration ; le vecteur temporaire d'indices dépend du nombre d'événements, et le pic mémoire n'a pas été mesuré.

Sur la fenêtre gauche réelle de 364 240 événements, cinq appels alternés donnent une médiane de 108,44 ms avant et 85,90 ms après, avec des comptes exactement identiques ([essai isolé](../outputs/demo_speed_20261014/flat_index_probe.json)). Ce chiffre porte uniquement sur la rectification, pas sur la chaîne complète. Trois rejeux complets, avec toutes les optimisations précédentes actives :

| Médiane, hors rendu/export | Avant | Indices réutilisés | Contrôle après |
|---|---:|---:|---:|
| Calcul complet, 17 sorties | 405,1 ms | 380,3 ms | 438,3 ms |
| Lecture et représentations | 164,9 ms | 138,5 ms | 168,6 ms |
| Calcul complet, 12 dernières sorties | 398,7 ms | 375,2 ms | 403,7 ms |

**Décision : conserver l'optimisation.** Réduction observée de 16 à 18 % de la lecture/représentation, et de 6 à 13 % du calcul médian complet. La charge du poste fluctue, particulièrement pendant le contrôle après ; ne pas attribuer tout cet écart à la modification. Le contrôle recharge uniquement l'ancienne fonction de rectification dans son processus et consigne cette substitution dans `summary.json`. [Vérification des trois rejeux](../outputs/demo_speed_20261014/flat_verification.json).

Les **153 tableaux et les résultats scientifiques des 17 images sont exactement identiques**. Toujours 77 occurrences YOLO, 45 surfaces et 32 abstentions. Les **239 tests passent**, notamment les tests existants de collisions bilinéaires, limites et fenêtres vides ([journal](../outputs/demo_speed_20261014/flat_tests.log)). Aucun test supplémentaire n'a été ajouté pour cette simplification d'indices. [Rejeu actuel](../outputs/demo_speed_20261014/flat_fast/clip.gif), aperçu vérifié et ralenti ×5 ; toutes les sorties dépassent encore 20 ms. Temps réel et mobilité indépendante restent non validés.

Le calcul des canaux inutilisés dans les images rectifiées a ensuite été supprimé comme décrit ci-dessous.

### Sixième optimisation conservée : normaliser uniquement le canal utilisé

Le suivi et la stéréo n'utilisent que le canal total des événements. `normalized_event_image(..., total_only=True)` produit désormais directement cette image 2D ; les images natives de YOLO conservent leurs trois canaux. La somme float32 des comptes, le logarithme, l'échelle figée sur le train, la saturation et l'arrondi restent identiques. Les contrôles des comptes et des trois échelles restent appliqués. Le parcours et la commande de lancement ne changent pas.

Trois rejeux successifs du même extrait, avec toutes les optimisations précédentes actives :

| Médiane, hors rendu/export | Trois canaux avant | Canal total seul | Trois canaux après |
|---|---:|---:|---:|
| Calcul complet, 17 sorties | 382,8 ms | 373,5 ms | 385,4 ms |
| Lecture et représentations | 141,8 ms | 127,1 ms | 140,2 ms |
| Calcul complet, 12 dernières sorties | 377,3 ms | 368,2 ms | 379,2 ms |

**Décision : conserver la suppression de ce calcul inutilisé.** Gain modeste : 2,4 à 3,1 % du calcul médian complet, et 9,4 à 10,4 % de la lecture/représentation. Sur une image rectifiée réelle, sept appels alternés donnent 10,58 ms pour normaliser trois canaux puis sélectionner le total, contre 3,68 ms pour le total seul. Ce test isolé n'est pas la latence du pipeline. La charge du poste varie ; le pic mémoire n'a pas été mesuré. Le contrôle après recharge l'ancienne normalisation dans son processus et sélectionne ensuite le canal total, substitution consignée dans son `summary.json`. [Mesures et vérification](../outputs/demo_speed_20261014/channels_verification.json).

Les **153 tableaux et les résultats scientifiques des 17 images sont exactement identiques** avant, après et dans le contrôle. Toujours 77 occurrences YOLO, 45 surfaces et 32 abstentions. **241 tests réussis**, dont deux nouveaux tests sur les formats numériques, les entrées non contiguës, les seuils d'arrondi, l'absence de mutation des entrées et le rejet des comptes/échelles invalides ([journal](../outputs/demo_speed_20261014/channels_tests.log)). [Rejeu actuel](../outputs/demo_speed_20261014/channels_total/clip.gif), aperçu vérifié, toujours ralenti ×5.

**Limite actuelle :** toutes les sorties dépassent encore 20 ms et la mobilité indépendante reste non validée. Les gains de ces étapes sont des gains d'exécution, pas de précision. La stéréo courante coûte encore environ 145 ms et la lecture/représentation 127 ms dans ce rejeu. Un gain majeur nécessitera une hypothèse différente de la simple suppression de calculs inutilisés ; ne pas modifier la résolution, les fenêtres ou les contrôles de fiabilité sans évaluer leurs effets.

## Association aux annotations DSEC-MOD — 14 octobre 2026

Après la discussion des guides géométriques et deep learning, reprise ciblée sur l'association des sorties aux objets annotés. Lecture seule des résultats existants, sans nouvelle inférence, nouveau modèle, seuil modifié ou lecteur supplémentaire.

Le rapprochement exact par séquence et timestamp entre `outputs/demo/summary.json` et `outputs/motion/M16/audit/verified_sample.json` trouve une seule date : `zurich_city_04_b`, frame MOD 134, timestamp 36614000936 µs (`outputs/demo/400000.json`). Les quatre boîtes YOLO sont natives ; leur comparaison directe avec les boîtes MOD rectifiées serait incorrecte. Leurs pixels intérieurs sont projetés avec la calibration existante par `object_surface.mapped_roi`, puis comparés aux pixels des rectangles MOD dans `camRect0`. Les IoU ci-dessous portent sur ces supports raster, sans seuil d'acceptation ni attribution de classe Moving aux prédictions.

| Tube MOD | Meilleur recouvrement avec une sortie YOLO | Support de mouvement dans la boîte MOD |
|---|---|---|
| 7 | Aucun pixel commun | 2 points suivis, aucune profondeur exploitable |
| 8 | IoU 0,763 avec la quatrième détection, person | 1 point évaluable, aucun candidat |
| 9 | IoU 0,820 avec la troisième détection, car | 13 points suivis, aucune profondeur exploitable |
| 10 | IoU 0,778 avec la deuxième détection, person | 8 points évaluables sur 11 suivis, aucun candidat |
| 11, région du camion | Aucun pixel commun | 24 candidats sur 60 points évaluables, 73 suivis |

Les supports de mouvement ont été recalculés à partir des tableaux sauvegardés avec `reference_diagnostic.box_support` et concordent avec le diagnostic précédent. Les quatre sorties YOLO ont toutes zéro candidat résiduel associé. L'IoU utilise les rectangles de référence, pas des masques physiques d'objets ; la parallaxe RGB/événements reste une incertitude.

**Blocage identifié :** imposer une détection YOLO comme préalable à une sortie de mobilité ferait perdre le signal observé dans la région du camion. Le pipeline actuel conserve déjà les candidats géométriques indépendamment de YOLO : il faut préserver cette séparation. Un recouvrement élevé pour les tubes 8, 9 et 10 ne confirme pas leur mobilité prédite, et les points du tube 11 peuvent encore appartenir au fond.

**Suite ciblée :** pour passer du diagnostic par points à une détection d'objets mobiles, il faut obtenir une région prédite à partir des seuls candidats géométriques, puis l'associer aux boîtes MOD après inférence. Examiner d'abord le regroupement existant `residual_regions.group_residual_regions` : ses cellules dilatées peuvent fusionner plusieurs surfaces. Ne pas utiliser les rectangles MOD pour construire les régions prédites. Aucun nouveau tracker, réentraînement YOLO ni score global ne se justifie par cette seule date train. Cette étape a établi la limite d'association, sans prétendre améliorer l'algorithme.

### Contrôle du regroupement existant — 14 octobre 2026

Application en mémoire de `residual_regions.group_residual_regions` aux tableaux déjà sauvegardés dans `outputs/focused_truck/reference_100ms`, sans nouvelle inférence ni modification des paramètres : cellules de 32 px, dilatation 3 × 3, connexité 8, au moins trois candidats, marge de 8 px. Les boîtes MOD sont consultées uniquement après formation des régions. Les deux dates sans historique restent inconnues.

| Date train | Candidats / régions produites | Association spatiale à la référence |
|---|---|---|
| `04_b/134` | 29 / 1 | Région `[95,117,281,305]`, IoU 0,844 avec le tube 11 ; 24 candidats dans la boîte, 5 hors des boîtes publiées |
| `04_b/267` | 43 / 1 | Région `[117,71,419,297]`, IoU 0,244 avec le tube 11 ; 34 candidats dans la boîte, 9 hors des boîtes publiées |
| `04_e/134` | 1 / 0 | Support insuffisant pour une région |
| `04_e/267` | 3 / 0 | Aucun groupe spatial n'atteint trois candidats |

Le calcul à `04_b/134` sur `outputs/demo/400000.json` et `.npz` donne également la même région. À `04_b/267`, la référence du tube 11 est `[84,141,234,294]`, alors que des candidats regroupés atteignent x = 410,9 et y = 79,1. La dilatation des cellules relie ces supports éloignés dans une seule composante. Ce constat explique l'extension du rectangle ; il ne prouve pas que les points extérieurs sont du décor, leur mobilité n'étant pas annotée de façon exhaustive.

**Conclusion de cette étape :** le regroupement existant donne une localisation encourageante à une date et trop étendue à l'autre. Il ne constitue pas encore une détection d'objet mobile validée. Le seuil minimal de trois points empêche aussi une sortie sur les deux dates `04_e`, sans démontrer l'absence d'objets mobiles. Aucun seuil IoU n'a été choisi pour convertir ces observations en succès/échecs et aucune précision/rappel globale n'est calculée.

**Prochain changement justifiable :** traiter spécifiquement la fusion de supports éloignés dans le regroupement, à partir des points prédits uniquement. Garder suivi, profondeur, pose et seuil de résidu fixes pour isoler l'effet du changement. Les boîtes de référence servent à l'évaluation après calcul, jamais à découper la région prédite. Une amélioration sur ces dates train demanderait ensuite une validation indépendante. Le démonstrateur principal et ses résultats restent inchangés ; aucun nouveau lecteur, rapport ou résultat visuel n'a été créé.

### Essai unique de regroupement sans dilatation : rejeté — 14 octobre 2026

Une seule modification a été exécutée sur les quatre dates traitables déjà sauvegardées : supprimer la dilatation 3 × 3 des cellules. Grille 32 px, connexité 8, minimum trois candidats, marge 8 px et résidu >3 px restent identiques. Aucune recherche d'hyperparamètres. Le code substitué existe uniquement dans le processus d'essai ; le module applicatif est inchangé. [Résultat et code exact de l'essai](../outputs/focused_truck/grouping_without_dilation.json), avec empreintes des entrées et indices des points par région.

| Date | Regroupement historique | Sans dilatation |
|---|---|---|
| `04_b/134` | Une région de 29 points, IoU 0,844 avec le tube 11 | Deux régions de 9 et 16 points, IoU 0,098 et 0,205 ; quatre candidats ne forment plus de groupe suffisant |
| `04_b/267` | Une région de 43 points, IoU 0,244 avec le tube 11 | Une région de 35 points, IoU 0,706 ; une autre de 6 points sans intersection avec les boîtes publiées ; deux candidats sans groupe suffisant |
| Les deux dates `04_e` | Aucune région | Aucune région |

**Décision : rejet.** La séparation des supports éloignés améliore la localisation à la seconde date mais fragmente l'objet à la première. La région hors référence n'est pas déclarée fausse alerte. Ce changement n'est pas intégré au démonstrateur, aucune nouvelle inférence ni image n'est produite, et les sorties historiques sont conservées. Aucun test applicatif relancé puisque aucun code applicatif n'a changé ; les deux formulations ont été exécutées sur exactement les mêmes tableaux sauvegardés.

**Conséquence :** une simple réduction de la connexion spatiale ne suffit pas. La prochaine évolution éventuelle devra exploiter une information de cohérence du mouvement pour séparer des surfaces, plutôt que rechercher un rayon qui convient à ces deux images. Cette piste reste à justifier avant implémentation ; aucun gain de mobilité ni de vitesse n'est acquis par cet essai.

### Vérification de la cohérence directionnelle — 14 octobre 2026

Lecture des projections rigides sauvegardées aux dates `04_b/134` et `04_b/267`. Le vecteur résiduel est `current - predicted_pixels` ; sa norme a été vérifiée égale au résidu enregistré pour tous les points évalués (inconnus conservés). Les groupes examinés sont ceux de l'essai sans dilatation, construits sans annotations. Leur direction est l'angle de la moyenne des vecteurs unitaires, pour éviter l'erreur de moyenne arithmétique autour de −180°/+180°.

| Date et support | Direction circulaire (image : x droite, y bas) | Norme résiduelle médiane |
|---|---:|---:|
| `04_b/134`, groupe supérieur, 9 points | 110,37° | 3,483 px |
| `04_b/134`, groupe inférieur, 16 points | −176,66° | 4,519 px |
| `04_b/267`, groupe gauche, 35 points | 151,79° | 5,325 px |
| `04_b/267`, groupe droit, 6 points | 178,82° | 18,718 px |

Les deux groupes qui recouvrent la référence du camion à la première date diffèrent de 72,97°, contre 27,04° entre les groupes spatialement séparés à la seconde date. Une règle simple « fusionner si les directions moyennes sont proches » ne peut donc pas préserver le premier rapprochement tout en rejetant le second. Cela réfute cette règle pour ces supports, pas toute méthode utilisant le mouvement. Une boîte de référence ne certifie pas que tous ses points appartiennent physiquement à l'objet.

L'amplitude plus élevée du groupe droit est une observation, pas une vitesse 3D ni une preuve d'objet distinct. Un résidu dépend aussi du suivi, de la profondeur et du modèle de pose. Aucun seuil angulaire ou d'amplitude n'a été ajusté, aucun filtre n'a été ajouté, aucun résultat du démonstrateur n'a changé.

**Clôture du contrôle :** ni la suppression de dilatation ni cette règle de direction moyenne ne justifient une intégration. L'amélioration du regroupement reste non résolue. Ne pas poursuivre une série de seuils sur ces deux dates train ; conserver les candidats comme non confirmés. Une suite algorithmique devra définir une hypothèse plus solide et une évaluation indépendante, au lieu de présenter l'ajout d'un filtre comme une correction acquise.

## Décision active : simplifier — 12 octobre 2026

L’utilisateur constate que le projet est devenu trop complexe. Nous recentrons le travail sur **une commande existante, un extrait et un résultat principal**, sans nouvelle couche logicielle.

```powershell
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --output outputs/demo
```

Depuis la racine avec l’environnement et les données préparés. Sortie principale : `outputs/demo/clip.gif`. Le dossier doit être neuf. Pour présenter le travail sans recalcul : [démonstration principale](../outputs/demo/clip.gif).

**Consolidation réalisée le 12 octobre :** la commande ci-dessus a été exécutée depuis les événements bruts. `outputs/demo/` est désormais le résultat principal ; il existe déjà et ne doit pas être écrasé. [Vérification](../outputs/demo/verification.json) : 153 tableaux identiques à `integrated_03`, 17 résultats scientifiques identiques hors durées, GIF de 17 images à 100 ms chacune, aperçu final inspecté. Toujours 77 détections cumulées, 45 surfaces estimées et 32 abstentions. Calcul médian de cette exécution : 921,8 ms par sortie, hors rendu/export ; ce n’est pas un gain de vitesse démontré ni du temps réel. Aucune modification de l’algorithme. La vidéo GIF, l’aperçu et les deux JSON sont également copiés dans `Bureau/resultats/demo/`.

**Acquis :** événements → YOLO + stéréo/XYZ + indices de mouvement, sur 17 images. **Limite :** la mobilité indépendante reste non validée et l’exécution reste hors ligne. Une classe YOLO, un résidu ou une sensibilité à la pose ne constitue pas une preuve de mobilité.

**Arrêt des extensions :** pas de nouveau lecteur, diagnostic de pose/profondeur, rapport numéroté, modèle ou dataset dans le parcours courant. Les acquis restent à leur emplacement ; aucune suppression ni déplacement des fichiers nécessaires à la reproduction. Les anciennes « prochaines étapes » ci-dessous sont historiques et ne constituent plus une liste de tâches.

### Conclusion sur les preuves disponibles

La relecture des rapports existants est terminée. **Le prototype produit des candidats de mouvement ; il ne démontre pas encore une séparation fiable entre objet et caméra.** Il existe une référence publique partielle : dire « aucune référence disponible » serait inexact.

| Preuve déjà acquise | Conclusion permise |
|---|---|
| [M16 : six dates, 22 boîtes Moving](../outputs/motion/M16/audit/verified_sample.json) | Référence ponctuelle sur train, avec limite de parallaxe RGB/événements. Le rapprochement exact des timestamps avec le démonstrateur trouve uniquement l’image 17 sur 17. Les autres dates ne sont pas déclarées négatives. |
| [M18 : quatre dates communes, 15 boîtes](../outputs/motion/M18/comparison/summary.json) | Avec un suivi de 20 ms, aucune des deux fenêtres testées (50 ou 20 ms) ne produit de candidat dans ces boîtes. Avec la fenêtre de 50 ms : quatre boîtes sans suivi, trois sans profondeur exploitable, huit avec des points évalués mais sans résidu >3 px. C’est un résultat défavorable, pas un rappel global mesuré. |
| [Comparaison du suivi à 20 et 100 ms](../outputs/focused_truck/interval_01/summary.json) | À 100 ms, 24 points dépassent 3 px parmi 60 points évaluables du groupe sélectionné dans la boîte finale. Le seuil en pixels correspond toutefois à une vitesse apparente cinq fois plus faible : cela ne prouve pas un gain de qualité. La boîte peut contenir du décor. |
| [Sensibilité aux poses sur le clip](../outputs/focused_truck/clip_sensitivity_01/summary.json) | Des points changent de statut avec une autre hypothèse de pose ; leur répétition ne suffit pas à confirmer la mobilité. |

**Ce qui manque pour valider la version actuelle :** une confrontation des sorties du suivi à 100 ms à une référence temporelle et spatiale adaptée, avec association des objets et traitement explicite des inconnus. Les mesures M18 concernent le suivi à 20 ms : elles ne sont pas une évaluation de la version actuelle. Les zones hors des boîtes publiques ne sont pas des négatifs certifiés ; elles ne permettent pas de compter toutes les fausses alertes.

**Décision :** conserver le démonstrateur comme prototype intégré hors ligne et présenter la séparation objet/caméra comme l’objectif non atteint à ce stade. Aucun seuil abaissé pour fabriquer une réussite. Aucun nouveau diagnostic ni modification algorithmique justifié par cette seule relecture.

### Comparaison à 100 ms réalisée — 12 octobre 2026

[Rapport](../outputs/focused_truck/reference_100ms/summary.json) · [Exemple à la date du démonstrateur](../outputs/focused_truck/reference_100ms/zurich_city_04_b_000134.png).

L’outil existant `run_reference_diagnostic.py` appelle désormais, avec `--demo-motion`, **la même fonction `infer_clip_motion` que le démonstrateur**, y compris le contrôle des points à 20 ms avant suivi à 100 ms. Aucun nouvel algorithme, modèle, dataset ou réglage du seuil. Les boîtes ne sont consultées qu’après l’inférence. Ce contrôle porte sur la branche mouvement ; YOLO et XYZ des objets ne sont pas recalculés.

Les six dates vérifiées sont conservées. Deux dates initiales (sept boîtes) restent inconnues, faute des 150 ms d’historique nécessaires. Sur les quatre dates traitables :

| Situation des 15 boîtes de référence | Nombre |
|---|---:|
| Au moins un candidat résiduel | 2 |
| Points évaluables, aucun candidat | 5 |
| Suivi présent, profondeur inexploitable | 4 |
| Aucun suivi retenu | 4 |

Les deux boîtes avec candidats correspondent au tube 11 de `zurich_city_04_b`, aux frames 134 et 267 : respectivement **24 points candidats sur 60 évaluables**, puis **34 sur 58**. Il s’agit de deux occurrences de référence, pas de deux objets distincts détectés. Le nombre de boîtes avec candidats reste deux avec les marges −5/+5 px ; les autres catégories varient avec les limites des boîtes.

**Conclusion :** le suivi actuel produit un signal dans certaines régions annotées Moving, mais manque de support ou de résidu dans la majorité des boîtes de ce petit échantillon train. Ce résultat est plus informatif que le seul affichage du clip ; il ne constitue pas une précision/rappel objet. Le seuil fixe de 3 px, le support de points différent, la parallaxe et l’incertitude de pose empêchent d’attribuer l’apparition des candidats au seul mouvement propre.

**Vérifications :** à la frame 134 de `04_b`, pose et cinq tableaux de mouvement sont exactement identiques à `integrated_03/400000`. Les 20 tests ciblés de référence et de fenêtres passent, dont deux nouveaux contrôles du mode démonstrateur (historique insuffisant et rejet de paramètres différents). Le panneau de cette date a été inspecté. Aucun contrôle général supplémentaire n’a été lancé. Les six panneaux et le rapport sont copiés dans le dossier des résultats du Bureau.

```powershell
.\.venv\Scripts\python.exe scripts/run_reference_diagnostic.py --demo-motion --output outputs/focused_truck/reference_100ms_repeat
```

**Examen des huit abstentions, sans nouvelle inférence :** lecture du code de suivi/stéréo et des tableaux sauvegardés. Deux boîtes sans profondeur (`04_b/134`, tube 9 ; `04_b/267`, tube 12) ont respectivement 13 et 18 points précédents, tous dans les 96 premières colonnes, zone défavorable à la recherche SGBM actuelle à 96 disparités. Cette localisation est cohérente avec la limitation du bord ; les cartes de profondeur complètes ne sont pas exportées dans ce rejeu, donc nous n’attribuons pas individuellement chaque rejet à un filtre stéréo. Les deux autres boîtes sans profondeur sont centrales et n’ont que deux points (`04_b/134`, tube 7) et un point (`04_e/134`, tube 5).

Parmi les quatre boîtes sans suivi, trois à `04_e/267` ont 0,43 %, 3,84 % et 5,56 % de pixels actifs. La quatrième, `04_e/134` tube 6, atteint 54,97 % : activité et suivi utilisable ne sont pas équivalents. Les sorties finales ne permettent pas de séparer, pour chaque objet, absence de points initiaux, rejet au contrôle de 20 ms et perte à 100 ms. Aucun de ces huit cas ne serait résolu par une baisse du seuil de résidu : ils sont bloqués avant cette décision.

**Conséquence pratique :** aucun bug confirmé à corriger dans cet examen ciblé. Ne pas remplir les profondeurs absentes ni déclarer ces objets immobiles. Une évolution éventuelle devra améliorer le support de suivi ou de profondeur et être évaluée comme un changement de méthode ; elle ne doit pas être présentée comme une simple correction. Cet examen clôt l’analyse des sorties disponibles, sans nouveau script, figure ou campagne de tests.

**Essai ciblé suivant : répartition des points, rejetée.** Une seule sélection spatiale 4 × 4 a été essayée sur les mêmes six dates, sans boîte en entrée ni changement de seuil. Les coins satisfaisant la qualité et la distance minimale globales existantes sont sélectionnés à tour de rôle par cellule, dans la limite de 400. La substitution est limitée au processus Python de cet essai ; aucun module applicatif n’est modifié. Le code exact de la substitution et la décision sont enregistrés dans le [rapport de l’essai](../outputs/focused_truck/reference_100ms_spread/summary.json).

Sur les quatre dates traitables, les points suivis passent de **1 242 à 950**, et ceux avec profondeur de **779 à 600**. Les catégories par boîte restent identiques : deux avec candidats, cinq sans résidu, quatre sans profondeur, quatre sans suivi. Les sept boîtes initiales restent inconnues. Les mêmes entrées et le même protocole ont été vérifiés, ainsi que la limite de 400 points initiaux. Ces résultats ne démontrent aucun gain de mobilité ; la modification est rejetée, sans nouvelle recherche de grille ou de seuil. Pas de suite générale relancée puisque le code applicatif reste inchangé. Les images de cet essai sont des résultats expérimentaux rejetés, pas la nouvelle démonstration.

**Décision :** conserver ce bilan comme résultat de la confrontation, sans baisser le seuil ni lancer une nouvelle série de variantes. Le prototype reste une détection de candidats hors ligne. Une amélioration de l’algorithme devra cibler une limite précise (suivi, profondeur ou séparation des mouvements) ; multiplier les visualisations ne corrigera pas ces limites.


Le README présente désormais ce parcours en premier ; les détails d’installation sont repliés. Aucun code du détecteur ni résultat scientifique n’est modifié pour cette simplification.

<details>
<summary>Historique conservé : diagnostics, vérifications et anciennes étapes</summary>

## Lecture des incertitudes dans le démonstrateur — 12 octobre 2026

[Ouvrir le lecteur actualisé](../outputs/focused_truck/viewer_05/index.html).

L'affichage disposait déjà des candidats orange, des points inconnus gris et du pourcentage global de sensibilité à la pose. Nous ajoutons une localisation : **un contour violet indique les points dont le statut candidat change lorsqu'on utilise la pose précédente comme hypothèse**. La couleur centrale conserve le résultat enregistré. Ce contour peut entourer un point orange ou vert ; il ne constitue pas une nouvelle classe d'objet.

Au clic sur un point, le lecteur distingue comparaison indisponible, point non comparable sous les deux poses, statut modifié et statut inchangé. « Inchangé » ne signifie pas validé. La légende rappelle également que la compatibilité avec le modèle ne prouve pas l'immobilité. La première image ne dispose pas de comparaison ; le contrôle est désactivé à cette date. Les profondeurs hypothétiques du diagnostic précédent ne sont pas utilisées pour modifier le détecteur.

**Vérifications :** les indices des contours et des points comparables sont identiques aux masques sauvegardés sur les 16 transitions. L'image 3 contient bien 81 contours. Les données des 17 images et la comparaison détaillée existante restent exactement identiques au lecteur précédent. Trois tests du lecteur réussissent et la syntaxe JavaScript passe `node --check`. Le contrôle visuel interactif reste non réalisé : l'outil de navigation bloque le protocole local `file://`. Aucun contournement effectué. Aucune nouvelle suite générale lancée.

Le lecteur autonome, son manifeste et les régions sont également copiés dans `Bureau/resultats/tous_les_resultats/focused_truck/viewer_05/`, avec vérification SHA256. Les anciennes versions restent disponibles.

```powershell
.\.venv\Scripts\python.exe scripts/build_inspection_viewer.py --output outputs/focused_truck/viewer_06 --sensitivity outputs/focused_truck/pose_switch_01 --clip-sensitivity outputs/focused_truck/clip_sensitivity_01
```

**Prochaine étape :** vérifier visuellement ce lecteur sur l'extrait, puis établir ce qui manque encore pour confirmer un mouvement indépendant. Ne pas transformer les contours violets en filtre automatique ni annoncer une précision sans référence de mobilité.

## Sensibilité à la profondeur — 11 octobre 2026

[Tableau visuel](../outputs/focused_truck/pose_components_03/depth_sensitivity.png) · [Mesures et provenance](../outputs/focused_truck/pose_components_03/summary.json).

Le contrôle prévu est réalisé dans `scripts/diagnostics/analyze_pose_components.py`. Les 264 points évaluables, leurs rayons dans l'image précédente, les poses et les groupes restent fixes. Nous remplaçons uniquement les profondeurs par cinq hypothèses uniformes prédéfinies : 10, 15, 30, 50 et 100 m. Ce sont des scénarios numériques, pas des profondeurs mesurées ou corrigées. Aucun point n'est perdu dans les projections ; les 99 points initialement inconnus restent exclus.

| Profondeur hypothétique | Effet translation médian | Changement total médian |
|---|---:|---:|
| 10 m | 9,349 px | 7,202 px |
| 15 m | 6,159 px | 4,207 px |
| 30 m | 3,044 px | 1,481 px |
| 50 m | 1,818 px | 0,632 px |
| 100 m | 0,906 px | 1,247 px |

L'effet translation correspond à R3,t2 → R3,t3 ; le total à R2,t2 → R3,t3. À 50 m pour tous, l'effet translation reste différent entre les groupes : 2,148 px pour les communs, 1,773 px pour les perdus et 1,014 px pour les gagnés. **La profondeur seule ne suffit donc pas à expliquer les différences : la position des points intervient également.** Le changement total n'est pas monotone, car rotation et translation se compensent partiellement. Son minimum parmi ces cinq valeurs ne désigne pas une profondeur correcte.

**Contrôles réalisés :** les 20 projections artificielles sont comparées indépendamment à OpenCV (écart maximal 1,57 × 10⁻¹¹ px). La rotation pure sans translation est invariante à la profondeur à 1,14 × 10⁻¹³ px près. Les tableaux, groupes et résultats du diagnostic précédent sont exactement conservés. Fermeture vectorielle contrôlée et figure inspectée. La suite générale de 227 tests n'a pas été relancée pour cet ajout descriptif.

**Décision :** clore ce contrôle géométrique sans modifier les seuils, les poses ni les profondeurs du détecteur. Il explique une sensibilité, sans valider la mobilité ni mesurer une erreur de profondeur. La prochaine étape sera de rendre ces limites directement lisibles dans le démonstrateur existant : distinguer clairement candidat, résultat sensible à la pose et information indisponible, sur le même extrait. Vérifier d'abord les indications déjà présentes pour éviter un affichage redondant ; aucun nouveau modèle ni dataset.

Les nouvelles figures et le rapport sont copiés dans `Bureau/resultats/tous_les_resultats/focused_truck/pose_components_03/`, avec vérification des empreintes. Le manifeste initial reste historique. Reproduction :

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/analyze_pose_components.py --output outputs/focused_truck/pose_components_04
```

Le dossier de sortie doit être neuf. Cette commande reproduit les trois niveaux du diagnostic dans un seul dossier.

## Localisation de la compensation par groupes — 11 octobre 2026

[Carte et mesures par groupe](../outputs/focused_truck/pose_components_02/groups.png) · [Rapport complet](../outputs/focused_truck/pose_components_02/summary.json).

Le diagnostic précédent est prolongé dans le même script, sans nouvelle architecture. Les groupes sont exactement ceux du support final de la paire 2 → 3, définis après observation au seuil de 1,5 px. Les 264 points forment une partition de 147 communs, 45 perdus, 48 gagnés et 24 hors des deux supports. Les 99 points inconnus ne sont pas évalués.

Nous décomposons le changement de projection **R2,t2 → R3,t2 → R3,t3**, puis vérifions aussi l'ordre inverse **R2,t2 → R2,t3 → R3,t3**. La somme des deux vecteurs retrouve exactement le changement total pour chaque point. Les médianes des normes, elles, ne s'additionnent pas.

| Groupe | Points | Profondeur médiane estimée | Effet rotation, médiane | Effet translation, médiane | Changement total, médiane |
|---|---:|---:|---:|---:|---:|
| Commun aux poses | 147 | 49,16 m | 2,26 px | 2,32 px | 0,49 px |
| Perdu avec T3 | 45 | 15,28 m | 2,29 px | 6,16 px | 3,88 px |
| Gagné avec T3 | 48 | 10,87 m | 2,30 px | 4,55 px | 2,58 px |
| Hors des deux supports | 24 | 14,21 m | 2,40 px | 2,08 px | 1,83 px |

Ces valeurs décrivent le premier ordre. Dans les deux ordres, les effets rotation/translation ont un produit scalaire négatif pour chacun des 264 points : ils s'opposent partiellement. Sur le groupe commun, leurs directions sont presque opposées (angle médian de 171,1° pour le premier ordre) et leurs normes proches, d'où le faible changement final.

**Interprétation :** les deux hypothèses expliquent de façon proche un groupe plus lointain, tout en modifiant davantage les projections des groupes perdus/gagnés. Mais l'effet n'est pas une simple fonction décroissante de la profondeur : le groupe gagné, plus proche en médiane, présente un effet translation inférieur au groupe perdu. Position dans l'image, profondeur et sélection par le support sont mêlées. Ces groupes ne sont ni des objets identifiés ni des labels de fond/mobile.

**Vérification ciblée :** projections et résultats précédents exactement conservés ; indices des quatre groupes identiques au diagnostic de support ; fermeture vectorielle vérifiée dans les deux ordres ; comparaison indépendante par OpenCV conservée ; nouvelle figure inspectée. Les 227 tests du dernier contrôle général restent la référence : aucune nouvelle suite générale n'a été relancée pour cet ajout descriptif au diagnostic.

Les deux figures et le rapport sont aussi copiés dans `Bureau/resultats/tous_les_resultats/focused_truck/pose_components_02/`. Le manifeste de l'export initial reste historique ; les nouvelles copies sont vérifiées séparément.

**Décision conservée :** ne pas retenir arbitrairement la pose qui soutient le plus de points et ne pas attribuer l'instabilité à la seule profondeur. Le contrôle de sensibilité à profondeur variable alors proposé est réalisé ci-dessus.

## Rotation et translation : diagnostic réalisé le 11 octobre 2026

[Figure des quatre hypothèses](../outputs/focused_truck/pose_components_01/comparison.png) · [Mesures, vérifications et provenance](../outputs/focused_truck/pose_components_01/summary.json).

La paire 2 → 3 a été étudiée sur les **264 mêmes points évaluables de l'image 3**, avec les mêmes profondeurs estimées au début du suivi. Les 99 autres points restent inconnus. Aucun suivi, ajustement de pose ou seuil n'a été modifié. Nous avons recombiné les composantes des transformations sauvegardées : R désigne la rotation ; t la translation des coordonnées des points, pas directement la position de la caméra.

| Hypothèse sur les points de l'image 3 | Support final ≤ 1,5 px | Candidats > 3 px | Résidu médian |
|---|---:|---:|---:|
| R2, t2 : pose précédente | 192 | 29 | 0,603 px |
| R3, t2 : seule rotation remplacée | 16 | 78 | 2,308 px |
| R2, t3 : seule translation remplacée | 31 | 61 | 2,382 px |
| R3, t3 : pose enregistrée de l'image 3 | 195 | 56 | 0,524 px |

À translation t2 fixée, remplacer R2 par R3 déplace les projections de **2,289 px en médiane**. À rotation R2 fixée, remplacer t2 par t3 les déplace de **2,561 px**. Remplacer les deux ensemble donne **1,129 px**. Ces médianes ne sont pas additives. Les combinaisons artificielles ont un support bien inférieur aux deux poses complètes : les effets des composantes se compensent partiellement dans cette comparaison et leur cohérence conjointe compte fortement.

**Conclusion limitée :** la bascule ne peut pas être attribuée simplement à la rotation seule ou à la translation seule. Ce contrôle montre une sensibilité aux composantes combinées ; il ne mesure pas une erreur de pose, ne prouve pas une dégénérescence de l'estimation et ne confirme aucun objet mobile. T2 et T3 concernent deux intervalles de 100 ms décalés de 20 ms ; leurs mélanges ne sont pas des trajectoires physiques mesurées. Le support final n'est pas le sous-ensemble initial de RANSAC.

**Contrôle général : 227 tests réussis, 115 fichiers Python et 41 aides CLI vérifiés.**

**Vérifications :** les quatre projections sont contrôlées indépendamment par `cv2.projectPoints` ; le modèle original reproduit les résidus enregistrés. Les 192/195 points de support, les 93 changements de support et les 81 changements de statut candidat retrouvent les diagnostics précédents. Aucun point projetable n'est perdu entre les quatre hypothèses. La figure a été inspectée. Le script conserve les empreintes de ses entrées et de ses artefacts.

Reproduction dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/analyze_pose_components.py --output outputs/focused_truck/pose_components_02
```

**Action alors proposée, réalisée ci-dessus :** examiner sur cette même paire les déplacements vectoriels et les profondeurs des groupes de support commun, perdu et gagné, pour localiser cette compensation. Conserver les poses actuelles ; aucune nouvelle architecture ni baisse arbitraire du seuil.

## Reprise : démonstrateur restaurable — 11 octobre 2026

L'utilisateur a demandé de passer à l'étape suivante après la revue. La dépendance aux trois artefacts locaux cachés est maintenant traitée par un paquet de transfert du démonstrateur existant : poids Y01, normaliseur S01 et image de contrôle Y00. Aucun entraînement, nouvelle architecture, annotation ou changement de seuil.

- [Paquet local](../outputs/reproduction/demo-assets-v1.zip) : **5 092 777 octets**, trois fichiers ; événements bruts et anciens résultats exclus. Il reste ignoré par Git et n'a pas été publié sur GitHub.
- [Configuration versionnée](../configs/demo_assets.json) : chemins, tailles et SHA256 des huit entrées figées, dont les cinq fichiers DSEC à acquérir séparément.
- [Commande de gestion](../scripts/manage_demo_assets.py) : `--pack`, `--restore`, `--verify`. La restauration vérifie tout le paquet et les conflits avant installation ; elle refuse les données modifiées et n'écrase pas un fichier existant différent. Elle ne désérialise pas les poids.
- Parcours de restauration et installation documenté dans le [README](../README.md#restaurer-les-artefacts-préparés).

**Validation réalisée :** restauration du vrai paquet dans une copie propre des sources, ajout des cinq fichiers bruts déjà acquis, vérification des huit empreintes puis rejeu CPU. Les **153 tableaux et les résultats scientifiques des 17 images sont exactement identiques**, hors temps de calcul. **227 tests, 114 fichiers Python et 40 aides CLI** passent ; six tests supplémentaires vérifient notamment les conflits, modifications de contenu et membres ZIP inattendus.

**Portée :** le test utilise les données DSEC déjà présentes et l'interpréteur `.venv-demo` existant. Il ne vérifie ni un nouveau téléchargement réseau, ni une installation sur une autre machine. Le paquet local doit encore être transmis au destinataire ; le dépôt public seul ne suffit pas. Les empreintes sont des identités locales figées, pas des signatures du fournisseur. Le paquet conserve un modèle limité à `person` et `car` et n'améliore pas la qualité de détection.

Preuves : [restauration et rejeu](../outputs/reproduction/restore-verification.json), [égalité des résultats](../outputs/reproduction/comparison.json), [contrôles logiciels](../outputs/reproduction/checks_01/report.json).

**Étape alors prévue, réalisée ci-dessus :** revenir à la paire 2 → 3 déjà étudiée et séparer l'effet de la rotation et de la translation dans la projection des mêmes points, avec les mêmes profondeurs. Objectif : expliquer la redistribution du support avant de modifier le détecteur. Ces composantes restent des hypothèses estimées ; aucune pose de référence ni mobilité confirmée ne doit être déduite de ce diagnostic.

## Versionnement GitHub — 11 octobre 2026

À la demande de l'utilisateur, le dépôt public s'appelle désormais [`AliAsri/stereo-evenementielle`](https://github.com/AliAsri/stereo-evenementielle), branche `main`. La première publication comprenait 266 fichiers, soit environ 6,4 Mo avant compression Git. Le nettoyage retire du suivi Git 74 fichiers redondants ou réservés au travail local : miroir Markdown, ancien notebook, avis externes bruts, préparations de réunion et leurs illustrations. Ils restent sur le disque local ; l'historique Git antérieur est conservé. Le dépôt courant contient 192 fichiers.

Les neuf programmes Python auparavant suivis dans `outputs/focused_truck/` sont maintenant dans `scripts/diagnostics/`, avec les chemins de leurs dépendances corrigés. Leurs anciens exemplaires restent locaux pour conserver la provenance des expériences. Les commandes de cette page utilisent les nouveaux chemins. Tout `outputs/` est désormais ignoré par Git, ainsi que les environnements Python, données acquises, poids et archives. `markdowns/` reste synchronisé à chaque modification documentaire, mais n'est plus publié. Le code utilisé, ses tests, le notebook actuel et la documentation technique utile sont conservés.

Après rangement, les contrôles couvrent 111 fichiers Python et 37 aides CLI, avec 215 tests réussis. L'augmentation de couverture vient des neuf diagnostics désormais sous `scripts/` ; aucun algorithme n'a été ajouté. Les liens vers les documents et programmes suivis, les anciennes URL du dépôt et la conservation locale des fichiers retirés sont vérifiés. Le contenu de la version courante représente environ 1,33 Mo, hors historique Git.

Une copie isolée des fichiers suivis par Git, sans `data/` ni les résultats historiques, passe les 215 tests, le contrôle de 111 fichiers Python et les 37 aides CLI avec l'interpréteur d'inspection existant. Cela vérifie l'autonomie des contrôles logiciels, pas celle de la démonstration complète, qui nécessite toujours les données et poids locaux. Le README explique cette distinction et l'installation. Cette mise en version ne reprend pas les expériences scientifiques mises en pause.

## Revue complémentaire du dossier et de la reproduction — 11 octobre 2026

À la demande de l'utilisateur, revue ciblée avant toute nouvelle expérience. Corrections effectuées :

- Une extraction ZIP interrompue ou rejetée pour CRC incorrect laissait un fichier final incomplet, empêchant la reprise. Chaque membre est maintenant écrit temporairement puis publié après lecture complète, sans écraser de données existantes. Un test corrompt réellement une archive puis vérifie la reprise après réparation.
- Le rejeu intégré dépendait d'une image Y00 contrôlée uniquement à la dernière date et absente du manifeste des entrées. Les huit fichiers requis sont désormais contrôlés avant de charger YOLO ; l'image figure aussi dans les empreintes. `--check-inputs` liste les absences sans calcul ni création de résultats. Il ne valide pas le contenu des fichiers.
- Deux diagnostics historiques (`check_camera_influence.py` et `explain_points.py`) s'exécutaient dès leur import. Ils disposent maintenant d'une fonction principale et d'une sortie explicite neuve. Le premier ne peut plus réécrire silencieusement `run_01/camera_influence.json`.
- Les commandes actives ne présentent plus R01 et ses 144 tests comme l'état courant. Le README décrit les dépendances locales du rejeu et la limite de reproduction après clonage.

**Validation : 221 tests, 112 fichiers Python et 39 aides CLI réussis.** Les mêmes contrôles passent dans une copie isolée des sources, sans données ni résultats historiques. Le précontrôle y signale correctement les huit entrées absentes. Les six nouveaux tests couvrent la reprise d'extraction, la protection des données, les chemins ZIP, les entrées manquantes et les imports des diagnostics. Le rejeu complet conserve exactement les **153 tableaux et les résultats des 17 images**, hors durées mesurées ; aucun seuil ni algorithme scientifique n'a été changé.

L'inventaire confirme qu'aucun fichier de `data/`, `outputs/`, `markdowns/` ou des environnements n'est suivi par Git. Les deux environnements représentent environ 28 800 fichiers et les données environ 4,4 Go : le volume local est principalement constitué de dépendances et d'acquisitions. Rien n'a été supprimé ; les anciennes copies des diagnostics dans `outputs/` restent des traces de provenance, les versions maintenues étant dans `scripts/diagnostics/`.

**Limite à traiter avant de promettre une reproduction complète :** le téléchargement DSEC ne fournit pas le checkpoint Y01, le normaliseur S01 ni l'export de contrôle Y00. Leur préparation est explicitée dans le README, mais leur distribution ou régénération depuis un clonage reste à organiser. Les téléchargements réseau et l'entraînement n'ont pas été rejoués lors de cette revue.

Preuves locales : [contrôles](../outputs/review/reproduction_01/checks/report.json), [comparaison du rejeu](../outputs/review/reproduction_01/replay-comparison.json), [inventaire des dossiers](../outputs/review/reproduction_01/folder_inventory.json), [contrôles en copie isolée](../outputs/review/reproduction_01/clean-checks/report.json).

## Audit global R02 — 11 octobre 2026

**Audit terminé ; reprise demandée le 11 octobre (voir étape de reproduction ci-dessus).** La revue a porté sur les chemins critiques de lecture, causalité, géométrie, stéréo, suivi, pose, association XYZ, visualisation, import/export et évaluation. Elle complète les contrôles automatiques de l'ensemble `src/`, `scripts/` et `tests/`, ainsi que les contrôles supplémentaires des notebooks, configurations et diagnostics de l'extrait. Les 201 fichiers de travail sauvegardés avant correction et leurs empreintes sont conservés sous `outputs/review/R02/`.

Quatre défauts confirmés ont été corrigés :

- **Stéréo :** une tolérance gauche/droite infinie pouvait désactiver le contrôle de cohérence ; NaN pouvait supprimer tous les pixels. Ces valeurs et les paramètres SGBM de type ou signe incorrect sont désormais refusés. Les paramètres utilisés pour les résultats existants restent valides.
- **Commande de contrôle :** un délai dépassé ou un lancement impossible des tests pouvait empêcher la production du rapport. Le rapport `FAILED`, le motif et la sortie partielle sont maintenant conservés ; une source illisible est également signalée.
- **Lecteur HTML :** des tableaux de points de longueurs différentes pouvaient être tronqués silencieusement par `zip`. Le lecteur refuse maintenant ces fichiers incomplets avant de construire l'affichage. Aucun tableau incomplet n'a été trouvé dans les résultats actuels.
- **Image récapitulative :** au-delà de six détections, le texte des détections supplémentaires chevauchait le pied de page. L'espacement est corrigé et vérifié sur une image de test explicitement marquée, avec sept détections dupliquées uniquement pour contrôler la mise en page. L'extrait actuel ne dépasse pas six détections par image.

La description des environnements et le caractère historique de la feuille de maintenance R01 ont également été clarifiés. Aucun nouveau modèle, réglage scientifique, dataset ou entraînement n'a été ajouté.

| Contrôle | Résultat vérifié |
|---|---|
| Suite de tests | **215 réussis**, contre 207 avant correction ; huit nouveaux tests de régression |
| Code et commandes | **102 fichiers Python**, **30 aides CLI** ; dix fichiers Python supplémentaires de diagnostics/notebook compilés |
| Environnements | `pip check` réussi pour les deux environnements ; six et 42 versions verrouillées correspondent aux installations |
| Rejeu complet depuis les événements | **17 images**, **153 tableaux exactement identiques**, résultats scientifiques JSON identiques hors durées |
| YOLO et XYZ du rejeu | **77 occurrences de détection**, **45 estimations de surface**, **32 abstentions** ; aucune identité persistante déduite |
| Lecteurs DSEC | Les trois lecteurs concordent exactement sur **54 fenêtres**, dans les six flux gauche/droite des trois séquences acquises ; bornes `[début, fin)` vérifiées |
| Export YOLO | **774 images**, **1 560 empreintes** ; labels, séparation des groupes et canaux RGB/BGR vérifiés |
| Lecteur HTML reconstruit | Identique octet par octet au lecteur actuel : **17 images temporelles, 34 PNG intégrées** ; logique JavaScript contrôlée avec DOM/canvas simulés |
| Configurations et notebooks | 14 JSON lisibles ; 14 cellules de code compilées dans les deux notebooks, dont l'archive ; aucun entraînement exécuté |

**Limites restantes :** les tests ne démontrent pas la détection fiable du mouvement indépendant. La pose demeure sensible au support, YOLO reste limité aux deux classes du pilote et une surface XYZ peut appartenir au fond. La chaîne complète demeure hors temps réel : ce rejeu de contrôle donne environ **895 ms médians par sortie**, pour un pas source de 20 ms. Cette mesure unique, sous charge d'audit, n'est pas une comparaison de vitesse avec le rejeu précédent. Le rendu du lecteur dans un navigateur réel n'a pas été validé ; le contrôle JavaScript simulé ne le remplace pas. Les notebooks ont été compilés, pas réexécutés sur GPU. Les acquisitions réseau, l'ensemble des anciennes expériences et chaque instant des flux complets n'ont pas été rejoués. Les contrôles documentaires portent sur les destinations locales des liens, sans vérification des URL externes ni des ancres.

Preuves : [bilan de revue](../outputs/review/R02/report.json), [tests et CLI](../outputs/review/R02/final-checks/report.json), [journal des 215 tests](../outputs/review/R02/final-checks/tests.log), [comparaisons et contrôles supplémentaires](../outputs/review/R02/verification.json), [export YOLO](../outputs/review/R02/yolo-export.json), [environnements](../outputs/review/R02/environments.json), [interactions du lecteur](../outputs/review/R02/viewer/interaction-checks.json).

## Le livrable à construire

Un rejeu DSEC qui montre des candidats de mouvement indépendant, puis leur classe YOLO et une profondeur/position XYZ quand elles sont disponibles. Afficher aussi les cas inconnus et le temps de traitement. La reconnaissance d’une voiture ou l’activité d’un pixel ne suffit pas à prouver son mouvement propre.

Nous avançons sur un extrait et une configuration à la fois. La séparation objet/caméra reste l'objectif ; YOLO et XYZ sont maintenant réunis dans un affichage avec les indices de mouvement existants, sans attendre une validation complète de cette séparation.

## Ce que nous gardons / ce que nous mettons en pause

| Garder | Mettre en pause |
|---|---|
| DSEC et références publiques déjà acquises | Nouveaux datasets |
| Représentation de 50 ms, suivi et stéréo S01 | Intégration EMatch et nouvelles architectures |
| Compensation géométrique de la caméra | Réglages multiples et optimisations supplémentaires |
| YOLO existant pour l’intégration finale | Nouvel entraînement YOLO pour l’instant |
| Tous les anciens résultats, conservés | Nouveaux rapports numérotés pour chaque petite action |

Aucune annotation manuelle à réaliser. Aucun document source ni résultat historique supprimé.

## Action réalisée : comprendre un camion

Nous avons repris le camion de `zurich_city_04_b`, tube public 11, frame MOD 134. Le prototype existant est rejoué sur **21 dates couvrant 0,4 seconde**, avec fenêtres de 50 ms et pas de 20 ms. Aucun seuil ni algorithme modifié.

La boîte publique n’est vérifiée qu’à la dernière date. Dans les images précédentes, le même rectangle sert de **zone fixe d’inspection** : il n’est ni une annotation interpolée, ni une trajectoire d’objet. Les points sont redétectés à chaque paire et ne représentent pas des identités persistantes. La zone contient aussi du fond.

| Étape | Résultat |
|---|---|
| Suivi dans la zone | 70 à 83 points selon la date |
| Profondeur disponible | 59 à 77 points selon la date |
| Résidu maximal dans la zone sur l’extrait | 1,073 px, inférieur au seuil de 3 px |
| Candidats au-dessus du seuil dans la zone | Aucun sur les 21 dates |
| À la date annotée | 76 points suivis, 65 avec profondeur ; résidu médian 0,366 px, maximal 0,809 px |

**Constat : le signal atteint le suivi et la profondeur, mais il n’est pas suffisamment distinct du mouvement prédit par le modèle rigide pour déclencher le critère actuel.** Cela n’établit pas la cause physique exacte et ne prouve pas que le camion est immobile. La compensation, le suivi sur fenêtres chevauchantes et la validité temporelle de la référence restent des limites.

Un contrôle supplémentaire a retiré les 65 points de la boîte de l’estimation de pose, puis évalué ces mêmes points avec la pose obtenue. Leur résidu médian monte à **0,768 px**, le maximum à **1,314 px** ; aucun ne dépasse 3 px. L’influence du camion sur le modèle existe, mais son retrait seul ne suffit pas à faire apparaître un candidat. Ce contrôle utilise une référence publique après coup : ce n’est pas un détecteur autonome ni une preuve de pose caméra correcte. Le reste de l’image n’est pas certifié statique.

## Voir et vérifier

- [Rejeu de l’extrait](../outputs/focused_truck/run_01/clip.gif), ralenti ×5 : chaque pas de 20 ms est affiché pendant 100 ms. Ce n’est pas une démonstration de calcul temps réel.
- [Image du diagnostic](../outputs/focused_truck/run_01/diagnostic.png).
- [Valeurs par date et provenance](../outputs/focused_truck/run_01/summary.json), [contrôle de l’influence sur la pose](../outputs/focused_truck/run_01/camera_influence.json).
- La dernière paire reproduit exactement les tableaux et résultats M17, hors temps de calcul ; sources algorithmiques et fichiers d’entrée contrôlés par hash. Le code applicatif est inchangé.

Pour reproduire le rejeu depuis la racine dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/run_diagnostic.py --output outputs/focused_truck/run_02
```

## Suite réalisée : regarder sur 100 ms

Le même extrait a été comparé sur **20 ms et 100 ms**, sans nouveau modèle et sans modifier les seuils. Les images restent des accumulations de 50 ms. Les deux suivis partent du même instant, 100 ms avant la référence ; leurs arrivées sont respectivement 80 ms avant la référence et à la référence. La même profondeur au départ est utilisée pour les deux.

Sur les 400 points de départ déjà suivis à 20 ms, 369 passent aussi le contrôle aller-retour à 100 ms. Ces **369 mêmes identifiants** servent aux deux estimations de pose. Après les estimations, la boîte finale sélectionne 73 points, dont 60 avec profondeur exploitable et 13 inconnus. Les valeurs ci-dessous portent sur ce même groupe ; la boîte n'est pas utilisée pour choisir les points du modèle caméra. La sélection finale est rétrospective et ne constitue pas une détection causale d'objet.

| Mesure dans ce groupe | 20 ms | 100 ms |
|---|---:|---:|
| Déplacement observé médian, 73 points | 1,077 px | 5,851 px |
| Résidu médian après compensation, 60 points | 0,347 px | 2,637 px |
| Résidu maximal | 0,649 px | 6,858 px |
| Points dépassant 3 px | 0 | 24 |
| Résidu médian divisé par la durée | 17,4 px/s | 26,4 px/s |
| Erreur aller-retour LK médiane, 73 points | 0,009 px | 0,031 px |

**Le signal est plus visible sur 100 ms.** Cela justifie d'en examiner la continuité ; cela ne valide pas encore le mouvement propre du camion. Hors de ce groupe, cinq autres points dépassent 3 px à 100 ms : ils ne sont pas des fausses alertes certifiées.

Le seuil fixe de 3 px correspond à 150 px/s sur 20 ms, mais 30 px/s sur 100 ms. En conservant le seuil de 150 px/s, aucun point du groupe ne le dépasse dans les deux cas. On ne peut donc pas conclure à une amélioration de qualité sur la seule apparition de 24 candidats. Les images se chevauchent de 30 ms dans le cas court et ne se chevauchent plus dans le cas long. Les erreurs de suivi, de profondeur et de pose restent possibles ; le contrôle aller-retour ne mesure pas toute cette incertitude. Les 31 points perdus à 100 ms sont exclus des deux estimations comparées, ce qui introduit une sélection des points qui restent suivables.

[Voir la comparaison](../outputs/focused_truck/interval_01/comparison.png) · [Données et modèles](../outputs/focused_truck/interval_01/summary.json) · [Vérification](../outputs/focused_truck/interval_01/verification.json).

Contrôles effectués : reproduction du suivi court à 0,0001 px près, conservation des identifiants et de la date de profondeur, résidus recalculés par reprojection, empreintes des entrées/sources et deux cas de suivi synthétiques contrôlés. Le code applicatif et les résultats précédents sont inchangés. La comparaison se reproduit dans un dossier neuf avec :

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/compare_intervals.py --output outputs/focused_truck/interval_02
```

## Action envisagée après reprise — en pause

Le rejeu glissant et un essai de répartition spatiale des points sont réalisés. Ce dernier ne résout pas la stabilité de la pose ; la référence actuelle est conservée. Les fluctuations observées ne justifient pas de déclarer un objet mobile dès qu'un point dépasse 3 px.

**La répartition du support explique mieux la bascule 2 → 3** : sur les mêmes points, T3 gagne 48 points de support, surtout à gauche, et en perd 45, surtout à droite. Son gain global de trois points masque donc une redistribution importante. Le lecteur actuel conserve les mesures de sensibilité par date. Après reprise demandée par l'utilisateur, l'action envisagée reste d'examiner séparément l'effet de la variation de rotation et de translation sur ces mêmes points, comme contrôle numérique pour comprendre ce transfert, sans estimer une nouvelle pose ni remplacer les prédictions. Cette action n'a pas été exécutée pendant l'audit. Aucun nouveau modèle, corpus, entraînement ou réglage de variante ; la mobilité reste non confirmée.

## Dernier résultat : rejeu glissant de 100 ms

**17 paires exécutées**, une sortie toutes les 20 ms, de −320 ms à la date annotée. Les images de 50 ms, la profondeur à chaque début de paire et les paramètres du modèle sont conservés. Les images/profondeurs déjà calculées sont réutilisées : ce rejeu ne mesure pas une vitesse de traitement de bout en bout.

| Observation | Résultat |
|---|---|
| Modèle rigide disponible | 17 dates sur 17 |
| Dates avec candidats dans la zone fixe | 17 sur 17, soit 320 ms entre première et dernière sortie |
| Nombre de candidats dans la zone | 5 à 27 par date |
| Nombre de candidats hors zone | 3 à 47 par date |

La présence de candidats dans la zone est récurrente, mais **leur localisation fluctue**. Par exemple, à −280 ms : 9 candidats dans la zone et 47 ailleurs ; à −140 ms : 24 dans la zone et 3 ailleurs. Les points compatibles avec la pose à moins de 1,5 px passent de 68/81 points évalués dans la zone à 13/64. Cela suggère une variation du compromis choisi par l'estimation de pose, sans établir une pose caméra exacte ni certifier le fond immobile. Ce problème doit être traité avant de qualifier la détection de stable.

Les points sont redétectés pour chaque paire : **ces 17 présences ne prouvent pas le maintien des mêmes points ni de la même identité d'objet**. Les paires se recouvrent temporellement et ne sont pas 17 observations indépendantes. La zone reste un rectangle d'inspection, avec une référence publique vérifiée seulement à la dernière date. Le seuil de 3 px reste différent en vitesse apparente selon l'intervalle, comme expliqué plus haut.

[Voir le rejeu 100 ms](../outputs/focused_truck/sliding_01/clip.gif) · [Comparer deux localisations](../outputs/focused_truck/sliding_01/localization_check.png) · [Résultats par date](../outputs/focused_truck/sliding_01/summary.json) · [Vérifications](../outputs/focused_truck/sliding_01/verification.json).

Les résidus des 17 paires ont été recalculés à partir des poses et profondeurs ; dates, identifiants, compteurs, empreintes et GIF vérifiés. La dernière paire reproduit exactement la comparaison 100 ms précédente. Aucun changement du code applicatif. Reproduction dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/replay_100ms.py --output outputs/focused_truck/sliding_02
```

## Essai terminé : répartir les points utilisés pour la pose

Une seule variante a été évaluée sur les mêmes 17 paires : grille fixe de 8 × 6 cases, au plus quatre points par case, choisis selon leur erreur de suivi aller-retour. La pose utilise ce sous-ensemble ; tous les points avec profondeur sont ensuite évalués. La boîte du camion ne participe pas à l'estimation. Les paramètres géométriques restent inchangés.

La variation médiane entre translations de deux poses successives passe de **0,162 m à 0,045 m**, mais le maximum reste voisin de **0,338 m**. Ces écarts comparent des estimations sur des intervalles glissants de 100 ms ; ce ne sont ni une erreur mesurée contre une pose vraie, ni une accélération physique. Les candidats continuent de fluctuer : 5 à 34 dans la zone, 4 à 47 ailleurs.

**Décision technique : ne pas activer cette variante par défaut.** Le résultat est partiel et ne démontre pas une meilleure séparation des mouvements. Le module expérimental et les résultats sont conservés ; aucune nouvelle série de réglages n'est engagée.

[Résultats de l'essai](../outputs/focused_truck/balanced_01/summary.json) · [Module optionnel](../src/pfe_events/balanced_pose.py). Vérification du projet réussie : 188 tests, 92 fichiers Python et 28 aides CLI. L'essai a été lancé par une commande Python ponctuelle ; les entrées et sources sont identifiées par empreintes dans le résultat.

## Première intégration : YOLO, profondeur et mouvement dans un affichage

Le modèle **Y01 pilote existant** est exécuté sur les 17 dates du même extrait `zurich_city_04_b`. Images événementielles de 50 ms et normalisation S01 conservées ; aucun entraînement ajouté. La stéréo S01 est recalculée à la date de chaque détection. Les boîtes natives sont associées aux pixels rectifiés pour obtenir un point de surface XYZ, avec abstention si le support est insuffisant. La zone publique du camion n'entre pas dans cette association.

| Résultat sur les 17 images | Valeur |
|---|---:|
| Détections cumulées, seuil YOLO 0,25 | 77 |
| Détections avec une estimation de surface XYZ | 45 |
| Détections sans XYZ, support insuffisant | 32 |

Ces nombres comptent des détections image par image, **pas 77 objets distincts**. Les numéros affichés recommencent à chaque image. À la dernière date, deux détections de personnes ont une profondeur estimée de 13,12 m et 12,87 m ; une troisième de faible confiance reçoit 43,30 m. La voiture détectée à gauche reste sans XYZ. Ces valeurs sont des estimations, sans référence de profondeur objet pour mesurer leur erreur ; une ROI peut contenir le fond. Le camion n'est pas reconnu par le modèle à deux classes `person`/`car`, tandis que des résidus apparaissent dans sa zone.

L'affichage garde **« mouvement propre non confirmé »**. Les comptes de points résiduels dans chaque boîte fournissent un indice local et ne prouvent pas la mobilité de l'objet. Dans cette première version `integrated_02`, les mouvements proviennent du rejeu `sliding_01`, à la même date d'arrivée, et sont relus ; YOLO et la stéréo sont calculés à nouveau. Cette version historique est une **intégration hors ligne avec mouvement précalculé**, remplacée par le calcul complet décrit ci-dessous. Le clip est ralenti ×5.

- [Voir la démonstration](../outputs/focused_truck/integrated_02/clip.gif) et [l'image finale](../outputs/focused_truck/integrated_02/preview.png).
- [Résultats détaillés](../outputs/focused_truck/integrated_02/summary.json) et [contrôles](../outputs/focused_truck/integrated_02/verification.json).
- 197 tests passent ; les 45 XYZ sont recalculés indépendamment, les dates sont vérifiées et l'image native finale reproduit exactement l'export Y00. Le second rendu conserve les mêmes résultats numériques que le premier.

Exécution dans l'environnement CPU isolé `.venv-demo` (Ultralytics 8.4.172, torch 2.14.1+cpu ; l'ancien environnement `.venv` est conservé) :

```powershell
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --output outputs/focused_truck/integrated_04
```

Pour recréer cet environnement : `python -m venv --without-pip .venv-demo`, puis `.\.venv\Scripts\python.exe -m pip --python .venv-demo\Scripts\python.exe install -r requirements-demo-lock.txt`. Le verrou des versions est dans [requirements-demo-lock.txt](../requirements-demo-lock.txt). Le script de synchronisation Markdown exclut cet environnement. Les archives `integrated_01` (premier rendu) et les expériences précédentes restent conservées.

## Résultat actuel : calcul complet et coût mesuré

`integrated_03` recalcule **YOLO, stéréo actuelle, XYZ et mouvement depuis les événements bruts**, sans lire les anciennes prédictions. La méthode de mouvement est inchangée : profondeur à `t−100 ms`, points présélectionnés par suivi jusqu'à `t−80 ms`, puis suivi direct jusqu'à `t`. Les images restent des accumulations de 50 ms. Cette sélection requiert 150 ms d'historique ; elle n'utilise pas d'événements postérieurs à la date de sortie.

Les 17 poses et tableaux de suivi reproduisent **exactement** `sliding_01`. Les détections, coordonnées XYZ et disparités actuelles reproduisent exactement `integrated_02` : toujours 77 détections cumulées, 45 surfaces estimées et 32 abstentions. L'intégration ne change donc pas la qualité observée ni les limites de mobilité.

| Mesure CPU, une exécution sur 17 sorties | Résultat |
|---|---:|
| Calcul complet médian, hors rendu/export | 1 049,5 ms |
| Médiane après la première sortie | 1 031,5 ms |
| Première sortie, premier appel YOLO compris | 3 766,0 ms |
| Calcul cumulé des 17 sorties | 21,20 s |
| Sorties dépassant le budget de 20 ms | 17 / 17 |

Les médianes par étape sont : lecture/représentation actuelle 298,9 ms ; YOLO 40,5 ms ; stéréo actuelle 132,9 ms ; branche mouvement 557,7 ms ; association 10,3 ms. La branche mouvement comprend ses propres lectures, représentations historiques, stéréo précédente, suivi et pose. **Les médianes par étape ne s'additionnent pas pour obtenir la médiane totale.**

Cette exécution séquentielle CPU est hors ligne : environ 0,80 sortie/s en moyenne, premier appel compris, en ne comptant que le calcul. Le programme entier prend 27,98 s avant l'écriture du résumé final, initialisation, empreintes et exports compris. OpenCV et PyTorch utilisent chacun un thread de calcul ; les caches HDF5/système sont actifs. Ce petit extrait et cette exécution unique ne constituent pas un benchmark général, un délai de détection de début de mouvement ou une cadence temps réel. Aucune optimisation supplémentaire engagée.

- [Voir la démonstration recalculée](../outputs/focused_truck/integrated_03/clip.gif) · [Image finale](../outputs/focused_truck/integrated_03/preview.png).
- [Résultats et temps par sortie](../outputs/focused_truck/integrated_03/summary.json) · [Vérifications](../outputs/focused_truck/integrated_03/verification.json).
- 201 tests passent, 97 fichiers Python et 29 aides CLI contrôlés. Les dates causales, l'identité numérique avec les anciens résultats, l'addition des temps par étape, les empreintes et les 17 images du GIF sont vérifiées. Les sources de cette exécution sont conservées dans son dossier ; l'ancien script avec mouvement précalculé est sauvegardé dans `integrated_02/sources/`.

## Lecteur d'inspection disponible

Ouvrir [le lecteur HTML autonome](../outputs/focused_truck/viewer_01/index.html) dans un navigateur. Les 17 dates et leurs images sont intégrées dans ce fichier d'environ 8 Mo ; aucun serveur, framework DL ou accès réseau n'est nécessaire pour le consulter. Il relit uniquement `integrated_03`, sans exécuter le modèle ni enregistrer d'annotations.

- **Lire/pause, précédent/suivant, début/fin et curseur temporel.** Lecture au ralenti ×5, ×12,5 ou ×25 ; la lecture ne mesure pas la vitesse du pipeline.
- **Cliquer une boîte ou une ligne du tableau** affiche le score YOLO, les XYZ disponibles, le support de profondeur et les comptes de points. Les points associés sont mis en évidence dans l'image rectifiée. La sélection est effacée à chaque changement d'image : les numéros ne sont pas des identités persistantes.
- **Cliquer un point à droite** affiche son déplacement observé, le déplacement prédit par le modèle, le résidu et la profondeur au départ. Les flèches sont à leur échelle réelle : blanc pour le suivi, bleu pour le modèle, orange pour le résidu ; leur origine appartient à l'image précédente.
- Cases pour afficher les boîtes, les points ou uniquement les candidats résiduels. La mention « mouvement propre non confirmé » reste visible.

Le navigateur a permis de vérifier lecture/pause, navigation, raccourci flèche, inspection avec/sans XYZ, clic sur un point et filtre résiduel, sans erreur JavaScript observée. Les 34 images intégrées sont identiques aux tableaux sources et les comptes associés aux boîtes sont vérifiés. Les contrôles du projet passent : 201 tests, 98 fichiers Python, 30 aides CLI. [Vérifications](../outputs/focused_truck/viewer_01/verification.json) · [Aperçu](../outputs/focused_truck/viewer_01/preview.jpg).

Pour reconstruire le lecteur dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe scripts/build_inspection_viewer.py --output outputs/focused_truck/viewer_05 --sensitivity outputs/focused_truck/pose_switch_01 --clip-sensitivity outputs/focused_truck/clip_sensitivity_01
```

## Ce que montrent trois points inspectés

[Comparaison illustrée](../outputs/focused_truck/inspection_01/comparison.png) · [Coordonnées et calculs](../outputs/focused_truck/inspection_01/examples.json). Les numéros ci-dessous correspondent aux **points du lecteur**, pas aux détections YOLO. Les exemples sont choisis après observation, à des positions différentes ; ils ne suivent pas une même identité entre les dates.

| Exemple visuel | Image / point | Déplacement observé | Déplacement prédit | Résidu |
|---|---|---:|---:|---:|
| Zone basse du camion, compatible avec le modèle | 3 / 11 | 7,14 px | 7,63 px | 0,54 px |
| Zone de façade, candidat résiduel | 3 / 158 | 7,37 px | 5,41 px | 3,85 px |
| Zone basse du camion, candidat résiduel | 10 / 14 | 4,70 px | 2,45 px | 4,12 px |

Un grand déplacement dans l'image peut être bien expliqué par le modèle : le premier point ne dépasse pas le seuil de 3 px. Le deuxième dépasse ce seuil dans une zone visuellement associée au décor. Le troisième dépasse le seuil dans la zone du camion. **La couleur orange désigne donc une incompatibilité avec le modèle, pas une preuve de mouvement propre.**

Le résidu vaut `norme(position_observée − position_prédite)`. Il tient compte des directions : il ne vaut pas simplement la différence des longueurs affichées. Par exemple, les 7,37 et 5,41 px du deuxième cas donnent un résidu de 3,85 px, et non 1,96 px.

Ces cas illustrent pourquoi le détecteur peut manquer un objet ou produire un candidat sur le décor. Ils ne permettent pas de départager quantitativement une erreur de pose, de profondeur, de correspondance ou un mouvement réel. La variation du compromis de pose observée auparavant reste une explication possible. Aucun fond n'est certifié statique, aucune précision/rappel n'est déduite de ces trois exemples. La visualisation de zones conserve donc cette incertitude.

Les trois résidus et leurs statuts ont été recalculés à partir des positions enregistrées ; ils reproduisent les valeurs sources. Les empreintes des entrées et du script de figure sont conservées. Aucun code d'inférence, réglage ni résultat antérieur n'a changé ; aucun entraînement ou annotation ajouté.

## Zones candidates ajoutées au lecteur

[Lecteur historique des zones](../outputs/focused_truck/viewer_02/index.html) · [Zones par date](../outputs/focused_truck/viewer_02/regions.json) · [Vérifications](../outputs/focused_truck/viewer_02/verification.json).

Les points dont le résidu dépasse strictement 3 px sont regroupés dans l'image rectifiée, sans utiliser les boîtes YOLO pour créer les zones. Le principe et les réglages spatiaux de M03 sont repris : cellules de 32 px, dilatation 3 × 3, connexité à 8 voisins, au moins trois points et marge de 8 px autour des points. Le modèle de mouvement reste le modèle rigide actuel ; le modèle apparent 2D de M03 n'est pas réactivé. Si le modèle est indisponible, aucune zone n'est proposée.

Sur les 17 images : **22 occurrences de zones**, avec une ou deux zones par image. **12 occurrences n'ont aucun point partagé avec les boîtes YOLO.** Cela montre que le regroupement fonctionne aussi hors du support des détections sémantiques ; cela ne mesure ni 22 objets distincts ni 12 objets manqués par YOLO. À la dernière date, la zone est `[95, 117, 281, 305]` dans l'image rectifiée et contient 29 points ; elle recouvre la région d'inspection du camion sans point partagé avec YOLO.

La case « Zones candidates » commande les cadres orange. Les boutons Z1/Z2 permettent d'examiner leurs points, le résidu médian et maximal, leurs coordonnées et les éventuels points communs avec YOLO. Les numéros recommencent à chaque image ; aucune association temporelle n'est ajoutée.

**Limite importante : le regroupement peut fusionner plusieurs surfaces.** Une chaîne de cellules proches peut produire un grand cadre contenant à la fois un objet et du décor. À la troisième image, une zone de 46 points s'étend sur `[159, 16, 570, 279]` et partage des points avec deux détections YOLO. Un cadre n'est donc ni une segmentation d'objet ni une preuve de mouvement indépendant.

Les données historiques du lecteur sont inchangées : mêmes suivis, images, détections, XYZ et temps enregistrés. Le regroupement est un post-traitement des résidus sauvegardés ; aucun entraînement ni calcul complet relancé. Les temps de `integrated_03` n'incluent pas ce nouveau post-traitement.

Vérifications : 207 tests passent, 100 fichiers Python et 30 aides CLI contrôlés. Les 34 images intégrées, 39 empreintes sources, les membres des zones, les cadres, statistiques et points communs avec YOLO ont été vérifiés ; la syntaxe JavaScript passe aussi. **Le rendu interactif de `viewer_02` n'a pas été vérifié dans le navigateur** : sa politique bloque les URL de fichiers locaux. Les contrôles navigateur de `viewer_01` restent historiques et ne valent pas validation de cette nouvelle interface.

## Stabilité spatiale : présence répétée, localisation variable

[Comparaison visuelle et tableau des 17 dates](../outputs/focused_truck/stability_01/comparison.png) · [Mesures détaillées](../outputs/focused_truck/stability_01/summary.json) · [Vérifications](../outputs/focused_truck/stability_01/verification.json).

Le diagnostic compare les 16 transitions entre images consécutives, espacées de 20 ms. Il mesure le recouvrement de **l'union des cadres** par l'IoU : aire de l'intersection divisée par celle de l'union. Il compare aussi les cellules de 32 px occupées par les points regroupés, sans dilatation. Aucune identité n'est associée entre dates ; les numéros Z1/Z2 ne servent pas à apparier des objets.

| Mesure descriptive | Minimum | Médiane | Maximum |
|---|---:|---:|---:|
| IoU des emprises des cadres entre dates | 0,034 | 0,425 | 0,951 |
| IoU des cellules occupées entre dates | 0,027 | 0,372 | 0,850 |
| Surface totale des cadres, en % de l'image | 8,5 % | 21,0 % | 44,7 % |

La transition **image 7 → image 8**, de −200 à −180 ms, présente le plus faible recouvrement des cadres : **3,4 %**, et 3,1 % pour les cellules. La figure montre une zone autour de la région du camion, puis deux zones dont une grande à droite. La dernière image retrouve une zone autour de la région du camion. Cela décrit une redistribution des propositions dans l'image ; ce n'est pas une mesure du déplacement physique du camion.

Les grands cadres peuvent masquer une redistribution des points : entre les images 2 et 3, leur IoU vaut environ 0,33, contre seulement 0,06 pour les cellules occupées. Les cadres remplis ne sont pas des masques d'objet. La grille dépend également de ses frontières et ne comprend que les points retenus dans des zones d'au moins trois points.

**Décision : conserver le statut « zone candidate » et ne pas ajouter de confirmation de mobilité fondée uniquement sur sa répétition.** Le diagnostic quantifie une variabilité de localisation déjà visible. Il ne sépare pas encore les effets de la pose, de la profondeur, du suivi et du mouvement réel. Les comparaisons se font dans les coordonnées de l'image, sans compensation entre dates ; les fenêtres de 50 ms et les paires de 100 ms se recouvrent. Ces observations ne sont donc ni indépendantes, ni une évaluation de précision/rappel.

Les 17 surfaces et les 16 IoU des cadres sont vérifiées indépendamment par partition géométrique des rectangles, sans utiliser les masques raster du calcul initial. Les empreintes des 20 entrées, du script et de la figure sont contrôlées ; la figure a été inspectée visuellement. Aucun code d'inférence ni résultat historique modifié. Le contrôle précédent à 207 tests reste inchangé ; cette étape a fait l'objet de vérifications spécifiques aux nouveaux calculs.

Reproduction dans un dossier neuf, avec l'environnement existant :

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/analyze_region_stability.py --output outputs/focused_truck/stability_02
```

## Bascule 7 → 8 : forte sensibilité au modèle rigide

[Comparaison illustrée](../outputs/focused_truck/pose_switch_01/comparison.png) · [Calculs détaillés](../outputs/focused_truck/pose_switch_01/summary.json) · [Vérifications](../outputs/focused_truck/pose_switch_01/verification.json).

Le contrôle garde **tous les points, déplacements observés et profondeurs de l'image 8**, puis remplace uniquement sa transformation T8 par la transformation T7 enregistrée à l'image précédente. Les deux transformations décrivent des intervalles de 100 ms décalés de 20 ms. Réutiliser T7 est une hypothèse numérique de sensibilité, pas une pose caméra validée sur le nouvel intervalle. Aucun appariement des identités entre images ni nouvel ajustement de pose n'est effectué.

| Résultat | Image 7, T7 originale | Image 8, T8 originale | Image 8, hypothèse T7 |
|---|---:|---:|---:|
| Points évalués avec profondeur | 263 | 255 | 255 |
| Candidats, résidu > 3 px | 30 | 47 | 26 |
| Candidats dans la moitié gauche | 28 | 8 | 24 |
| Candidats dans la moitié droite | 2 | 39 | 2 |
| Support, résidu ≤ 1,5 px | 183 | 194 | 176 |

Les moitiés sont définies par `x < 320` et `x ≥ 320` dans l'image rectifiée ; ce ne sont pas des labels objet/fond. Les candidats isolés sont comptés même s'ils ne forment pas de zone : les 30 et 47 candidats originaux diffèrent donc des 28 et 45 points regroupés dans les cadres.

Sur les **mêmes 255 points** de l'image 8, 67 changent de statut au seuil de 3 px : en passant de T8 à T7, 44 candidats deviennent compatibles avec le modèle et 23 compatibles deviennent candidats. Trois points restent candidats dans les deux cas. Ce contrôle montre qu'une variation de transformation suffit à redistribuer les alertes, même sans modifier le suivi ou la profondeur de cette image.

T8 possède davantage de support à 1,5 px sur l'image 8 (194 contre 176 pour l'hypothèse T7), alors que T7 donne moins de candidats à 3 px (26 contre 47). Ces deux seuils mesurent des aspects différents de la distribution des résidus. **Choisir le modèle ayant le plus de support, ou le moins de candidats, ne prouve pas une meilleure séparation objet/caméra.**

Les paramètres de translation estimés diffèrent d'une norme de 0,337 m, et les rotations de 0,219°. Ces valeurs comparent deux transformations sur des intervalles décalés ; elles ne sont ni une erreur de pose mesurée, ni une vitesse ou accélération physique. Les médianes de cohérence aller-retour du suivi sont proches (0,0318 px puis 0,0308 px parmi les points évalués), mais cette cohérence ne garantit pas des correspondances exactes. La profondeur médiane identique ne démontre pas non plus une profondeur correcte : les points sont redétectés et les ensembles diffèrent.

**Décision : ne pas remplacer T8 par T7 et ne pas introduire de lissage à ce stade.** Le contrôle établit une sensibilité au modèle ; il n'explique pas encore pourquoi les estimations divergent, ni quelle transformation correspond à la caméra réelle. Les résultats YOLO, stéréo, XYZ et mouvement de `integrated_03` restent inchangés.

Vérifications : les projections et résidus originaux des images 7 et 8 sont reproduits à partir de leurs profondeurs et transformations ; les zones originales sont également reproduites. Une seconde projection avec `cv2.projectPoints` vérifie les trois cas, avec un écart maximal de coordonnées inférieur à `1,3 × 10⁻¹¹ px`. Les 67 changements de statut, les sept empreintes d'entrée, le script et les artefacts sont contrôlés ; la figure a été inspectée. Ces vérifications numériques ne constituent pas une validation de mobilité contre une vérité terrain. Aucun code d'inférence modifié ; la suite générale à 207 tests n'a pas été relancée pour ce diagnostic isolé.

Reproduction dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/analyze_pose_switch.py --output outputs/focused_truck/pose_switch_02
```

## Comparaison de poses intégrée au lecteur

**[Lecteur de la première comparaison de poses](../outputs/focused_truck/viewer_03/index.html)** : cliquer sur **« Comparer les poses · image 8 »**. Le lecteur se met en pause et affiche deux vues de la même image rectifiée : T8 enregistrée à gauche, hypothèse T7 à droite. Un avertissement rappelle que le contrôle ne désigne pas la bonne pose et ne confirme pas de mobilité. Cette fonction est conservée dans le lecteur actuel, indiqué en fin de page.

- Les vues montrent 47 candidats avec T8, contre 26 avec l'hypothèse T7, sur les mêmes 255 points évalués.
- La case « Afficher uniquement les points qui changent de statut » isole les 67 points concernés. Les cadres restent ceux de l'ensemble des candidats de chaque cas.
- Un clic sur un point dans l'une des vues sélectionne ce même point dans les deux vues et affiche ses deux résidus et statuts. Les boutons « Premier point modifié » et « Point modifié suivant » permettent aussi une inspection sans clic précis.
- Le panneau est réservé à l'image 8 et se masque lorsqu'on change de date. La sélection est réinitialisée à chaque changement d'image. Les vues principales, les boîtes YOLO, les XYZ et les zones enregistrées conservent leurs valeurs originales.

La comparaison est intégrée au fichier HTML autonome : aucune lecture de fichier supplémentaire ni inférence dans le navigateur. Le constructeur accepte le diagnostic via l'option facultative `--sensitivity`. Il vérifie les empreintes, la correspondance des dates, les prédictions originales et les comptes ; un diagnostic associé à une autre source ou à des prédictions différentes est rejeté. Sans cette option, le lecteur reste utilisable sans panneau de comparaison.

Vérifications : **207 tests, 100 fichiers Python et 30 aides CLI** passent. Les 17 résultats et les 34 images intégrées sont identiques à `viewer_02`, de même que les zones originales ; 41 empreintes sources sont vérifiées. Les données incompatibles sont refusées. Les interactions sont testées avec un DOM/canvas simulé : accès direct, navigation, filtre à 67 points, sélection commune, effacement, pause et absence de diagnostic. **Ce contrôle ne vérifie pas le rendu réel dans un navigateur**, dont l'accès automatisé aux fichiers locaux avait été bloqué ; cette limite reste explicite.

[Vérifications des données](../outputs/focused_truck/viewer_03/verification.json) · [Vérifications des interactions](../outputs/focused_truck/viewer_03/interaction-checks.json). Les anciennes versions sont conservées.

## Sensibilité sur tout l'extrait : la bascule n'est pas isolée

[Tableau illustré des 16 transitions](../outputs/focused_truck/clip_sensitivity_01/comparison.png) · [Mesures et provenance](../outputs/focused_truck/clip_sensitivity_01/summary.json) · [Vérifications](../outputs/focused_truck/clip_sensitivity_01/verification.json).

Le même contrôle est appliqué aux images 2 à 17 : conserver leurs points, déplacements et profondeurs, puis remplacer uniquement leur transformation par celle de l'image précédente. La première image n'a pas de comparaison faute de pose précédente dans cet extrait. Le seuil résiduel reste strictement supérieur à 3 px. Il n'y a ni nouvel ajustement de pose, ni suivi d'identité entre les dates.

| Observation sur les 16 transitions | Résultat |
|---|---:|
| Huit transitions avec davantage de changements | 26,3 à 30,7 % des points évalués |
| Huit autres transitions | 0,4 à 5,4 % |
| Plus grand pourcentage : 2 → 3 | 81 / 264 points, soit 30,68 % |
| Cas déjà étudié : 7 → 8 | 67 / 255 points, soit 26,27 %, huitième rang décroissant |
| Changement de disponibilité de projection entre les deux poses | 0 point sur les 16 comparaisons |

Les deux plages sont une **description après observation** : elles sont séparées par le plus grand écart entre pourcentages triés. Aucun seuil opérationnel n'en est déduit. Les huit transitions de la plage supérieure sont 2 → 3, 3 → 4, 7 → 8, 9 → 10, 10 → 11, 11 → 12, 14 → 15 et 16 → 17. La médiane des 16 pourcentages vaut 15,85 % ; elle tombe entre les plages observées et ne décrit donc pas un cas typique de cet extrait.

Les sommes donnent 613 changements sur 4 132 occurrences de points évalués. Les points sont redétectés et les intervalles se recouvrent : **ce ne sont pas 4 132 points distincts, ni 613 erreurs de détection**. À chaque date, le dénominateur est l'ensemble des points projetables sous les deux transformations ; ici, cet ensemble est identique dans les deux cas. Le taux de changement ne dissimule donc pas un changement de disponibilité des projections sur cet extrait.

**Décision : rendre la sensibilité visible sans choisir arbitrairement une « bonne » pose.** Le phénomène est récurrent sur ce petit extrait. Une faible sensibilité n'établit pas davantage une pose correcte : deux transformations proches peuvent partager un même biais. Réutiliser une transformation correspondant à un intervalle de 100 ms décalé de 20 ms reste une hypothèse numérique. Ce contrôle ne mesure ni précision/rappel de mobilité, ni erreur de pose caméra, ni généralisation à d'autres scènes.

Vérifications : les projections originales des 17 images sont reproduites ; les 16 hypothèses sont vérifiées indépendamment par `cv2.projectPoints` avec une rétroprojection par l'inverse de la matrice intrinsèque. L'écart maximal de coordonnées est inférieur à `3,9 × 10⁻¹¹ px`. Les effectifs, masques et indices des points modifiés sont contrôlés ; le cas 7 → 8 reproduit exactement ses tableaux précédents. Les 42 empreintes d'entrées et de sources sont vérifiées, et le tableau illustré est inspecté. Aucun code applicatif, lecteur ou résultat d'inférence n'a été modifié ; les 207 tests de la dernière étape restent le dernier contrôle général, sans relance inutile pour ce diagnostic isolé.

Reproduction dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/analyze_clip_sensitivity.py --output outputs/focused_truck/clip_sensitivity_02
```

## Sensibilité par date affichée dans le lecteur

**[Ouvrir le lecteur actuel](../outputs/focused_truck/viewer_04/index.html)**. Sous la date, le lecteur affiche la part des points dont le statut change si l'on utilise la pose précédente, ainsi que le numérateur et le dénominateur. La mise à jour suit le curseur, la navigation et la lecture. Exemples :

| Image | Affichage de sensibilité |
|---|---|
| 1 | Comparaison indisponible, sans pose précédente dans cet extrait |
| 2 | 1,16 %, soit 3 / 259 points |
| 3 | 30,68 %, soit 81 / 264 points |
| 8 | 26,27 %, soit 67 / 255 points |
| 17 | 27,64 %, soit 68 / 246 points |

Le dénominateur comprend les points évaluables sous les deux poses ; un éventuel changement de disponibilité de projection est affiché séparément. Ici, ce changement est nul à toutes les dates. Une absence de comparaison n'est jamais présentée comme 0 %. Le texte rappelle qu'une faible sensibilité ne garantit pas une pose correcte et que ce pourcentage ne confirme pas de mobilité. Aucun seuil ni code couleur de qualité n'a été ajouté.

L'option facultative `--clip-sensitivity` charge le diagnostic existant. La construction vérifie les empreintes, les dates, l'ordre des images, les masques, les résidus, les effectifs et les pourcentages à partir des tableaux sauvegardés. Le lecteur peut encore être construit sans diagnostic par date ou sans comparaison détaillée de l'image 8. Ces deux ajouts restent indépendants.

Les 17 prédictions, 34 images intégrées, zones candidates, résultats YOLO/XYZ et comparaison détaillée de l'image 8 sont identiques à `viewer_03`. Aucun calcul d'inférence relancé ; aucun artefact historique remplacé.

Vérifications : **207 tests, 100 fichiers Python, 30 aides CLI** passent. Les 43 empreintes sources et les 16 mesures affichées sont contrôlées. Des données à date, ordre, effectif, pourcentage ou source incompatibles sont rejetées. Le test JavaScript avec DOM/canvas simulé parcourt les 17 images, vérifie les effectifs et pourcentages, l'absence initiale de comparaison, le cas sans support commun, les diagnostics facultatifs et les interactions historiques. **Le rendu réel dans un navigateur reste non vérifié** ; ces tests de logique ne sont pas une validation visuelle.

[Vérifications des données](../outputs/focused_truck/viewer_04/verification.json) · [Vérifications des interactions](../outputs/focused_truck/viewer_04/interaction-checks.json).

## Support de pose 2 → 3 : un petit gain global masque une redistribution

[Carte du support sur l'image 3](../outputs/focused_truck/pose_support_01/comparison.png) · [Effectifs, indices et profondeurs](../outputs/focused_truck/pose_support_01/summary.json) · [Vérifications](../outputs/focused_truck/pose_support_01/verification.json).

Le contrôle utilise les mêmes 264 points évaluables de l'image 3 et compare T3 enregistrée à l'hypothèse T2 précédente. Les 99 autres points restent inconnus. Le **support final** désigne ici les points dont le résidu est inférieur ou égal à **1,5 px**, après ajustement ; ce n'est pas la liste initiale des points sélectionnés par RANSAC. Le seuil de candidat mobile potentiel reste distinct, à **plus de 3 px**.

| Ensemble de support sur l'image 3 | Total | Moitié gauche | Moitié droite | Profondeur médiane estimée au départ |
|---|---:|---:|---:|---:|
| Commun à T2 et T3 | 147 | 37 | 110 | 49,16 m |
| T2 seulement, perdu avec T3 | 45 | 5 | 40 | 15,28 m |
| T3 seulement, gagné avec T3 | 48 | 47 | 1 | 10,87 m |
| Aucune des deux à 1,5 px | 24 | 17 | 7 | 14,21 m |

T2 soutient **192 points**, T3 **195** : le gain net n'est que de trois points, alors que **93 points changent d'appartenance au support**. Le recouvrement des ensembles de support, intersection sur union, vaut 0,6125. Les 93 changements au seuil de 1,5 px ne sont pas les 81 changements de statut candidat mesurés au seuil de 3 px.

La carte place les points propres à T3 surtout à gauche, autour de la région du camion visible, et ceux propres à T2 surtout à droite. Cette lecture visuelle ne crée pas de labels de mobilité. Les moitiés utilisent `x < 320` et `x ≥ 320` dans l'image rectifiée actuelle ; aucune boîte de référence ni annotation manuelle n'est utilisée pour classer les points. Les profondeurs sont les estimations stéréo à `t−100 ms`, avec leurs erreurs possibles.

**Interprétation limitée : le comptage global du support masque un changement des surfaces expliquées.** Un ensemble commun, à profondeur médiane estimée plus grande, reste compatible avec les deux transformations, tandis que d'autres groupes entrent ou sortent du support. Cela n'établit ni une caméra correcte, ni un camion immobile ou mobile, ni la cause exacte du changement de pose. Réutiliser T2 sur l'image 3 reste une hypothèse sur un intervalle de 100 ms décalé de 20 ms.

**Décision : conserver les poses et poursuivre l'explication géométrique, sans choisir automatiquement celle qui a le plus de support.** La variante historique d'équilibrage spatial déjà testée reste inchangée et n'est pas relancée. Aucun composant ni réglage ajouté au détecteur.

Vérifications : les ensembles forment une partition exacte des 264 points évalués ; les 195 points de T3 et leur couverture convexe reproduisent le modèle enregistré. Une projection indépendante avec `cv2.projectPoints` reproduit les résidus des deux cas avec un écart inférieur à `1,5 × 10⁻¹¹ px`. Les indices, effectifs, statistiques de profondeur et sept empreintes d'entrées/sources sont vérifiés ; les statistiques conservent la précision des tableaux sources. La figure est inspectée visuellement. Aucun code applicatif ni lecteur modifié ; les 207 tests de la dernière étape restent le dernier contrôle général.

Reproduction dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe scripts/diagnostics/analyze_pose_support.py --output outputs/focused_truck/pose_support_02
```

</details>

</details>


## Contrat de cadence du démonstrateur — 15 octobre 2026

Après la revue, le parcours principal consigne le budget source de 20 ms, les coûts séquentiels avec rendu/écritures par image et une simulation FIFO explicitement séparée de la latence réelle. Le contrôle Y02 donne 349,8 ms médians de calcul, 468,2 ms avec rendu/écritures, 17 dépassements sur 17 et 11,17 s de retard final simulé pour le traitement séquentiel. Le calcul hors YOLO reste à 311,0 ms médians ; accélérer ce seul réseau serait insuffisant. Premier appel inclus, initialisation et publication finale exclues. Aucune cadence ou politique de saut n’est modifiée.

259 tests réussis ; 153 tableaux et 17 résultats scientifiques identiques au rejeu de revue. [Preuves](../outputs/demo_contract_20261015/verification.json), [résumé](../outputs/demo_contract_20261015/summary.json). La prochaine action utile concerne le blocage de fiabilité de la compensation, sans annoncer la cadence ou la mobilité comme validées.


## Sensibilité de la compensation à données fixes — 16 octobre 2026

Les anciennes comparaisons de poses sur des intervalles décalés de 20 ms ne permettaient pas d'isoler la sensibilité du solveur. Le nouveau contrôle conserve tous les points, profondeurs et dates : un ordre initial, puis une permutation NumPy `default_rng(42).permutation(N)` réinitialisée pour chaque image. Les indices sont restaurés et les projections vérifiées indépendamment. Les références ne participent pas à l'ajustement.

Le backend classique de `solvePnPRansac` utilise un RNG local fixé à −1 dans OpenCV 4.14 ; `cv2.setRNGSeed` ne modifiait donc pas son tirage. L'appel est retiré pour préserver le générateur global ; `RigidMotionConfig.seed=42` est conservé comme métadonnée historique, les autres valeurs sont refusées explicitement. Deux tests couvrent ce contrat et l'absence de modification du flux aléatoire global. Cette correction ne change pas l'estimateur par défaut.

Résultat sur le rejeu : 567 occurrences de statut changent dans 16/17 images. Sur les quatre dates publiques traitables : 12 changements dans trois dates ; les 15 catégories de boîtes restent identiques. Deux boîtes changent de nombre de points résiduels (24 vers 19, 35 vers 40), sans changer de catégorie. Les deux dates de démarrage et leurs sept boîtes restent sans historique. Une permutation ne fournit ni intervalle de confiance, ni vérité caméra ; les deux poses peuvent partager un biais.

Les 21 modèles par défaut et toutes les associations publiques sont reproduits exactement. Les ajustements supplémentaires coûtent 2,55 ms médians sur le rejeu et 1,70 ms sur les références, hors préparation et association : mesures descriptives d'une exécution, pas latence d'un système modifié. 261 tests passent. Aucun gain de qualité n'est établi, aucune double estimation n'est ajoutée au démonstrateur. La décision reste de conserver les candidats non confirmés et d'exiger une preuve géométrique pour départager les poses, sans nouvelle campagne de permutations.

Reproduction dans un dossier neuf : `.venv\Scripts\python.exe scripts/diagnostics/analyze_pose_components.py --check-point-order --output outputs/focused_truck/pose_order_repeat`.

[Résultats, modèles, empreintes et sources OpenCV](../outputs/focused_truck/pose_order_20261016/summary.json) · [Tests](../outputs/focused_truck/pose_order_20261016/tests.log).


## Contrôle exact des profondeurs de compensation — 16 octobre 2026

Après constat de zéro date de référence exactement commune aux profondeurs historiques du rejeu (0/17) et aux dates publiques traitables (0/4), un contrôle unique reconstruit la même séquence à la date DSEC `36613900994 µs`, choisie avant lecture des erreurs, puis suit les points pendant 100 ms. Les fonctions du parcours actif sont réutilisées ; les références restent réservées à l’évaluation après inférence. La règle d’arrondi et de suppression des doublons s’applique aux graines avant le filtrage du suivi long, comme dans le parcours actif. Une assertion vérifie la reproduction des profondeurs échantillonnées.

369 points suivis, 258 profondeurs prédites, 103 références, 83 paires évaluables ; 20 références sans prédiction et 175 prédictions sans référence. Sur les paires : MAE disparité 0,571 px, Bad3 2/83 (2,41 %), MAE profondeur 1,720 m, erreur absolue médiane 0,956 m et relative médiane 3,73 %. Ces erreurs sont conditionnelles au support commun et ne valident pas la pose. La date est décalée de +58 µs de la dernière paire du démonstrateur : aucune référence voisine n’est appliquée aux anciennes profondeurs.

Le contrôle ne modifie ni le démonstrateur ni ses performances revendiquées. Son temps isolé est conservé avec un périmètre explicite, sans comparaison à la chaîne complète. Trois tests protègent les dénominateurs, les supports vides et le seuil strict Bad3 ; la suite complète passe à 264 tests.

Reproduction dans un dossier neuf : `.venv\Scripts\python.exe scripts/diagnostics/analyze_pose_components.py --check-exact-depth --output outputs/focused_truck/depth_exact_repeat`. [Résultat et empreintes](../outputs/focused_truck/depth_exact_20261016/summary.json). Décision et suite dans `20_NEXT_STEPS.md`.

## Effet des erreurs de profondeur sur les projections à pose fixe — 16 octobre 2026

Le diagnostic existant relit les 83 paires du contrôle exact, leurs correspondances et leur pose sauvegardée ; aucun événement n'est retraité, aucun solveur n'est relancé. Les empreintes des tableaux et de la calibration sont contrôlées. Les projections/résidus d'origine sont reproduits à 1e-8 px et les deux projections vérifiées indépendamment par `cv2.projectPoints` à 1e-7 px. Les 83 paires sont projetables dans les deux cas, sans perte de support masquée.

Le changement de profondeur déplace les projections de 0,054 px en médiane, 0,125 px en moyenne, 0,433 px au percentile 95 et 2,247 px au maximum. Les mêmes 74 points restent dans le support ≤1,5 px et les mêmes 6 restent candidats >3 px ; aucune entrée ni sortie de catégorie. Le résidu médian passe de 0,341 à 0,326 px, mais sa moyenne de 0,932 à 0,951 px : ce n'est pas une amélioration générale ni un score de qualité caméra.

Décision : clore ce contrôle local sans modifier le détecteur. Cette substitution numérique conditionnelle à une pose figée n'élimine pas le biais éventuel introduit lors de son ajustement avec les profondeurs prédites. Elle ne valide ni le suivi, ni la pose, ni la mobilité ; les 175 prédictions sans référence restent hors de la comparaison. Aucun gain de vitesse ou de détection revendiqué.

Quatre tests supplémentaires vérifient l'effet inverse de la profondeur sous translation, l'indépendance sous rotation pure, les points sans profondeur/derrière caméra et le rejet d'une transformation non rigide. **268 tests passent**. Reproduction dans un dossier neuf : `.venv\Scripts\python.exe scripts/diagnostics/analyze_pose_components.py --check-depth-projection --output outputs/focused_truck/depth_projection_repeat`. [Mesures, transitions, sources et empreintes](../outputs/focused_truck/depth_projection_20261016/summary.json) · [Tests](../outputs/focused_truck/depth_projection_20261016/tests.log).


## Archive de la feuille de route avant simplification — 19 octobre 2026

La page active était redevenue un journal de 249 lignes. Son contenu intégral est conservé ci-dessous ; les actions présentées comme futures y appartiennent à leur date. La décision courante se trouve dans [20_NEXT_STEPS.md](20_NEXT_STEPS.md). SHA-256 des octets source archivés : `69c98968ee78144d9a07df76533bbd28245cca5f4997b1ba16b5718dc68b1478`.

<details>
<summary>Feuille de route historique intégrale, avant simplification</summary>

<!-- BEGIN ROADMAP SNAPSHOT 20261019 69c98968 -->
# État actuel et prochaines étapes

**19 octobre 2026 — page de reprise unique.** Priorités : **1. rapidité, 2. détection fiable, 3. estimation 3D**. [Audit en lecture seule du 18 octobre](AUDIT_TECHNIQUE_SCIENTIFIQUE_18_OCTOBRE_2026.md) ; [historique des interventions](19_PROGRESS.md).

## Contrôle ORB autorisé et terminé — non promu

**19 octobre 2026.** Après accord explicite de l'utilisateur sur le protocole préparé, un seul contrôle ORB400 + LK court inchangé + Hamming réciproque a été exécuté sur **211→217 / objet 6**. Données existantes vérifiées par taille/SHA-256, protocole enregistré avant essai, aucun masque/GT dans le front-end ; profondeur oracle et un seul PnP dans le diagnostic séparé. Aucune réexécution scientifique de LK ou des anciennes variantes.

| Mesure | LK sauvegardé | ORB testé |
|---|---:|---:|
| Correspondances retenues après géométrie | 39 | 78 |
| Évaluables avec référence et identité concordante | 25 | 23 |
| Erreur de correspondance ≤3 px | 20 | 2 |
| Cible : évaluables / correctes ≤3 px | 2 / 1 | 8 / 1 |
| Pose | Support rigide insuffisant | Ajustement refusé |

Les **quatre critères fixés échouent**. ORB place pourtant davantage de graines sur la cible (102 initiales, 57 après contrôle court), puis 20 appariements, dont 12 changent/perdent l'identité à l'arrivée. Le nombre de correspondances ne mesure pas leur justesse. **Coût front-end : 31,10 ms** sur un appel CPU à froid (25,78 détection/descripteurs + 4,70 contrôle court + 0,61 matching), hors représentation et pose. OpenCV 12 threads, OpenCL désactivé ; pas de gain de vitesse revendiqué contre les anciens temps non appariés. **333 tests passent**, dont sept nouveaux tests logiciels de ce front-end sur images synthétiques et cas limites.

[Comparaison vérifiée](../outputs/motion/M14_next_sample_20261017/orb_20261019/comparison.json) · [Illustration](../outputs/motion/M14_next_sample_20261017/orb_20261019/comparison.png) · [Protocole figé](../outputs/motion/M14_next_sample_20261017/orb_protocol_20261019.json). **Décision : hypothèse close, aucune intégration DSEC.** Conserver LK niveau 2, les abstentions et le démonstrateur actuel. Aucun balayage de descripteurs, seuils, niveaux ou autre paire justifié par ce résultat ; EVIMO2 est de nouveau clos. L'échec concerne ce contrôle et cette représentation, sans conclusion universelle sur ORB. La mobilité DSEC reste non validée ; une nouvelle correction doit viser une cause établie avec référence et coût, sans prolonger automatiquement la série de variantes.

## Géométrie des 35 candidats hors masque — 19 octobre 2026

Contrôle des mêmes résultats sauvegardés, sans inférence ni modification du détecteur : la translation RGB/événements et le modèle de projection permettent de tester l'intersection d'un point avec les pixels positifs MOS pour **toute profondeur axiale positive**. Les carrés de pixels sont fermés pour admettre conservativement les contacts de frontière ; visibilité et occultation ne sont pas certifiées.

- **9/35 points n'ont aucune intersection possible** sous ce modèle de calibration et de masque exacts : la translation intercapteur seule ne suffit pas. Quatre sont à environ 0,68–5,68 px d'un masque, cinq à 66–184 px. Cela ne les transforme pas en faux positifs certifiés : incertitudes de masque, suivi et pose restent distinctes.
- **26/35 ont une intersection géométrique possible** à certaines profondeurs ; pour neuf d'entre eux, toute profondeur compatible est inférieure à environ 0,49 m. Une possibilité géométrique n'est donc pas une correction démontrée à la profondeur réelle.
- À `04_b/134`, la profondeur SGBM courante exacte est déjà sauvegardée pour **16 des 19 candidats hors masque**. Leur projection physique vers la grille RGB puis son warp associe **six** points au masque positif. Aucune profondeur t−100 ms n'est utilisée comme profondeur courante ; les 19 autres candidats des autres dates n'ont pas de profondeur courante évaluée ici.

Les neuf points sans intersection passent tous le contrôle aller-retour LK (0,009–0,891 px), ce qui ne garantit pas leur justesse. **326 tests passent**, dont six nouveaux contrôles de la géométrie de parallaxe. Sur les 16 profondeurs courantes sauvegardées, formule et chaîne complète 3D/RGB/homographie concordent à **3,34×10⁻¹³ px** près : contrôle d'algèbre, pas validation de la profondeur ou de la mobilité.

[Résultats détaillés](../outputs/dsec_mos_parallax_20261019/summary.json) · [Planche des candidats](../outputs/dsec_mos_parallax_20261019/candidates.png) · [Vérification géométrique](../outputs/dsec_mos_parallax_20261019/geometry_verification.json). L'utilitaire ajouté à `mod_alignment.py` est réservé au diagnostic, absent du parcours d'inférence.

**Décision : contrôle géométrique clos.** Aucun remplissage/dilatation des masques, réétiquetage de tous les zéros ou baisse de seuil justifiés. Les associations naïves par pixel peuvent être erronées ; inversement, la parallaxe ne suffit pas à expliquer tous les écarts. Toute future métrique doit annoncer son niveau de référence et ses incertitudes, et toute correction du suivi/pose doit avoir une preuve indépendante. Pas de nouvel essai automatique à la même configuration, pas de reprise EVIMO2.

## Support des résultats sauvegardés dans les masques — 19 octobre 2026

Lecture locale réalisée, **aucune nouvelle inférence, aucun téléchargement ou changement du détecteur**. Les six dates MOS sont associées par timestamp exact aux archives ; les deux premières dates restent sans historique suffisant. Deux configurations historiques sont conservées séparément : M17 à 20 ms et référence du 15 octobre à 100 ms avec correction du bord stéréo. Ce n'est pas une ablation isolant le seul intervalle.

| Archive | Points associés aux pixels positifs MOS | Avec profondeur et résidu évaluables | Abstentions parmi ces points | Candidats résiduels >3 px |
|---|---:|---:|---:|---:|
| M17, 20 ms | 163 | 120 | 43 | 0 |
| Archive 100 ms, bord corrigé | 156 | 133 | 23 | 53 |

**Interprétation :** un signal résiduel existe sur les masques publiés dans la configuration à 100 ms ; les 53 occurrences ne sont ni 53 objets ni 53 vrais positifs validés. Parmi elles, 21 sont sur `04_b/134`, 31 sur `04_b/267`, une sur `04_e/267`. Le support reste faible sur `04_e` : 5 puis 4 suivis associés, dont 4 évaluables à chacune des deux dates. Hors pixels positifs, 35 candidats sont dans la zone zéro non certifiée statique et un dans les 40 lignes non annotées : aucune précision/rappel/ROC calculée. Les 19 associations positives à une frontière 3×3 sont signalées sans les transformer en marge de parallaxe validée.

À la date commune **04_b/134**, les tableaux précédent/courant/profondeur et le modèle 100 ms archivés sont **exactement identiques au démonstrateur actuel** du 18 octobre ; cette égalité ne s'étend pas automatiquement aux autres dates. Les 17 et 18 snapshots source des deux archives sont vérifiés par leurs empreintes ; 78 fichiers d'entrée sont identifiés. **320 tests passent**, dont six contrôles du recadrage, de l'arrondi et des abstentions du lecteur d'analyse. La date exacte, le crop 640×440 et l'absence de remplissage négatif restent obligatoires.

[Résultats et provenance](../outputs/dsec_mos_support_20261019/verified/summary.json) · [Date commune illustrée](../outputs/dsec_mos_support_20261019/verified/common_date_preview.png). Commande maintenue : `python scripts/diagnostics/analyze_saved_mask_support.py --output outputs/mos_support_repeat` dans l'environnement `.venv`, dossier neuf. Aucun moteur d'inférence n'est appelé.

**Décision à l'issue de ce contrôle de support :** ne pas baisser le seuil pour créer un signal déjà présent ni présenter le bilan comme une amélioration de qualité. La question de parallaxe a ensuite été examinée dans le contrôle décrit en tête de page ; erreurs de suivi/pose et incertitudes de référence restent ouvertes. Pas de nouvelle grille, variante de suivi ou reprise EVIMO2 justifiée par ces comptes.

## Décision active — préparer une évaluation valide du mouvement

Après revue des deux avis externes, [le protocole de comparaison est préparé dans la note d'objectif](38_OBJECTIF_OBJETS_MOBILES.md#protocole-de-validation-préparé--18-octobre-2026), sans refonte du pipeline. Hypothèse : les résidus compensés doivent mieux séparer mobilité et mouvement apparent que le déplacement brut, sur les mêmes points évaluables, avec couverture et abstentions publiées. Les résidus continus existent déjà ; aucune baisse de seuil ni nouvelle variante de suivi n'est lancée.

**Précontrôle documentaire :** manifeste M16 = six dates/22 boîtes, aucun début de mouvement référencé ; M17 utilise l'intervalle historique 20 ms, distinct des 100 ms actuels ; EVIMO2 fournit des contrôles oracle train déjà explorés. Les régions hors boîtes ne sont pas des négatifs certifiés. Le protocole n'est donc **pas prêt pour une mesure indépendante de précision/rappel** sur le seul DSEC local vérifié. Il fixe les conditions de référence, sélection, comparaison et mesure ; aucune nouvelle performance scientifique n'est produite.

**Condition avant évaluation de qualité :** établir des références positives/négatives admissibles et une partition séparée. L'extension limitée DSEC-MOS a été autorisée et réalisée ci-dessous ; cet accord ne couvre pas une campagne indépendante ou un téléchargement supplémentaire. Le démonstrateur actuel reste inchangé ; dernier contrôle logiciel : 314 tests réussis lors de l'étape précédente.

**Acquisition limitée autorisée puis réalisée :** six masques DSEC-MOS et leurs six RGB aux dates M16 fixées (frames 1/134/267, séquences 04_b/04_e). **12 607 641 octets de corps HTTP lus, soit 12,02 Mio, sous plafond 64 Mio**, index et sondes inclus ; archive de 6 014 321 385 octets lue partiellement. Douze fichiers contrôlés par CRC ZIP, taille et SHA-256, aucun événement ou poids acquis. La disposition de l'archive diffère du README : le premier examen a arrêté la sélection sans extraction ; le second utilise les douze chemins exacts constatés, mêmes dates et budget cumulé.

**Découverte de qualification :** RGB et masques MOS = **640×440**, masques PNG 1 bit (booléens), et non images 640×480. Pour chacun des six RGB, parmi les 41 recadrages verticaux possibles de MOD, **seul `[0:440, :]` est exactement identique**. Les six dates M16 se transfèrent à ces images ; coordonnées x/y inchangées dans cette zone. Les lignes événementielles **440 à 479 restent inconnues**, jamais ajoutées comme fond négatif. La parallaxe RGB/événements demeure : égalité des RGB projetés ≠ vérité physique au pixel près. L'archive n'explicite pas de dossier de partition ; appartenance train des deux séquences vérifiée contre MOD, pas nouvelle certification du split MOS.

[Acquisition et empreintes](../outputs/dsec_mos_reference_20261018/acquisition_selected.json) · [Qualification](../outputs/dsec_mos_reference_20261018/qualification.json) · [Aperçu des références, pas des prédictions](../outputs/dsec_mos_reference_20261018/reference_preview.png). Aucun rejeu ou entraînement, aucune métrique de détection produite ; 314 tests restent le dernier bilan logiciel, non réexécuté pour ces acquisitions.

**Suite de cette acquisition réalisée le 19 octobre :** support des correspondances sauvegardées lu et résumé en tête de page. Avant ROC/précision/rappel, résoudre le traitement des limites de masque et de parallaxe, ainsi que l'admissibilité des négatifs. Les six dates restent du développement ; aucune performance indépendante, pose caméra ou latence de début de mouvement validée.

## Reprise après audit — 18 octobre 2026

Première correction bornée de reproductibilité : le démonstrateur vérifie désormais les tailles et SHA-256 avant de charger YOLO ou de créer une sortie. Y01 vérifie huit entrées figées ; `--weights` conserve la vérification des sept entrées de scène et enregistre le checkpoint explicite comme non vérifié contre Y01. Les empreintes sont réutilisées dans le résumé, sans seconde lecture pour les calculer. Le contrôle préalable est hors coût de calcul par image.

La cellule de reprise Y01 vérifie les deux classes et la compatibilité du reporting avant l'entraînement ; elle accepte l'ancien notebook et l'API du générateur actuel. Elle reste réservée à personne/voiture. **308 tests passent**, dont les refus d'entrées altérées et la compatibilité des deux fonctions de métriques réelles. Précontrôles sur les données réelles : **8/8 entrées Y01 conformes** ; **7/7 entrées de scène Y02 conformes**, empreinte du checkpoint explicite relevée. Aucun entraînement ni rejeu complet lancé, aucune nouvelle métrique scientifique. F8 et F10 de l'audit sont traités ; F7 (publication/reproduction sur clone neuf) reste ouvert. L'audit daté est conservé sans réécriture rétroactive.

**Intervention suivante réalisée — représentations concurrentes, 18 octobre.** Le profil sépare environ 12 ms de lecture des 70 ms de rectification gauche/droite : le cache temporel envisagé n'est pas ajouté. Le worker stéréo déjà présent prépare maintenant l'image droite pendant la préparation gauche, puis les deux résultats sont attendus avant YOLO. Aucun nouvel executor, aucune agrégation/réorganisation des événements, aucun changement de fenêtre, cadence, normaliseur ou seuil.

- Contrôle apparié sur les mêmes entrées résidentes : 17 dates × six répétitions en ordre alterné, préparation **108,32 → 89,76 ms médians (−17,1 %)**, p95 **135,10 → 108,64 ms** ; **306 comparaisons d'images exactes**. Lecture, historique, inférence et rendu exclus de ce contrôle.
- Rejeux complets Y01 avant/après : lecture/représentation **118,01 → 108,98 ms**, calcul complet **358,81 → 315,65 ms** médians. Les autres postes et le démarrage varient ; toute la baisse globale n'est pas attribuable à cette correction. Les 270 ms du 17 octobre ne sont pas le contrôle de cette comparaison.
- **153 tableaux et 17 lignes scientifiques identiques**, 77 occurrences YOLO, 66 surfaces, 11 abstentions. **311 tests passent**. Pic d'allocations suivi par `tracemalloc` sur la seule fenêtre ancre : **63,7 → 69,8 Mio**, hors entrées/tables déjà résidentes ; ce n'est pas le RSS du processus.

[Mesures appariées](../outputs/representation_speed_20261018/paired_representations.json) · [Vérification complète](../outputs/representation_speed_20261018/verification.json) · [Rejeu Y01 actuel](../outputs/representation_speed_20261018/after/clip.gif).

## Mouvement prioritaire, contexte moins fréquent — décision utilisateur du 18 octobre

Choix explicite : **« Mouvement prioritaire ; classe et 3D moins fréquentes »**. Le budget de comparaison de 20 ms vient du pas source ; ce n'est pas une latence physique imposée par le cahier des charges. La cible reste la mobilité indépendante, jamais la simple activité. Aucun délai de début de mouvement n'est validé.

Première mise en œuvre : indices de mouvement calculés à chacune des 17 dates (pas source 20 ms), publiés dans `motion.jsonl` avant le YOLO de la même date ; contexte YOLO et surfaces XYZ toutes les **100 ms de temps dataset** par défaut. C'est un choix initial explicite, pas une cadence optimale ou tenue en temps réel. `--context-step-ms 20` fournit le contrôle avec contexte à chaque date. Traitement toujours séquentiel : un appel YOLO peut retarder la prochaine date de mouvement ; aucun ordonnanceur temps réel indépendant n'est revendiqué.

**La profondeur interne nécessaire à la compensation reste calculée à chaque date**, avec profondeur précédente exactement à t−100 ms. Seule l'association XYZ des objets suit le contexte moins fréquent. Les contextes anciens portent leur timestamp, âge dataset et fichier de référence ; aucune ancienne boîte ni coordonnée n'est dessinée sur l'image courante. `objects=[]` sur une date sans contexte signifie **non calculé**, pas absence d'objet ; voir `context.updated`.

Contrôle dédié : **17→4 appels YOLO/XYZ**, 18 occurrences fraîches sur ces quatre dates (15 surfaces, 3 abstentions). **153 tableaux et 17 modèles de mouvement identiques**, contextes identiques aux quatre dates communes ; le contrôle à 20 ms conserve aussi toutes les sorties scientifiques du parcours précédent. Calcul médian **277,63→225,14 ms** ; disponibilité calculée des indices de mouvement **218,11→220,72 ms**, donc aucun gain démontré du coût propre de cette branche. Autres postes/démarrage variables, comparaison unique. **313 tests passent**, 17 lignes de flux vérifiées, 17/17 sorties encore hors budget. Un objet visible uniquement entre deux dates de contexte peut manquer sa classification ; aucun rappel conservé sur ces dates non évaluées n'est annoncé.

[Preuves](../outputs/motion_priority_20261018/verification.json) · [Démonstrateur actuel](../outputs/motion_priority_20261018/context_100ms/clip.gif). La séparation de cadence est intégrée ; elle ne résout ni la fiabilité ni le coût de la compensation. **Blocage suivant :** la branche mouvement dépend encore d'une représentation stéréo et d'une profondeur coûteuses. Une nouvelle méthode ou une réutilisation de profondeur doit être motivée et évaluée avec référence ; ne pas relâcher la synchronisation, réduire les seuils ou reprendre les essais EVIMO2 clos. Les sections datées ci-dessous conservent les décisions et preuves antérieures.

## Publication avant la stéréo courante — 18 octobre 2026

La relecture des dépendances a identifié une attente évitable : la compensation utilise la profondeur exacte à **t−100 ms**, pas celle de t. Le démonstrateur publie désormais `motion.jsonl` **avant le calcul stéréo courant**, puis calcule cette profondeur et la conserve pour les dates suivantes et le contexte XYZ courant. Aucun calcul stéréo supprimé, aucune profondeur décalée, aucun nouvel executor ou ordonnanceur.

Contrôle dédié sur les mêmes 17 dates Y01 et contexte 100 ms : **153 tableaux, 17 lignes scientifiques et 17 lignes de mouvement identiques**, quatre contextes identiques. Calcul jusqu'à publication : **243,23→169,58 ms médians**. Calcul complet : **246,25→263,42 ms médians** ; aucun gain global de débit démontré. La différence de coût jusqu'au mouvement comprend le retrait de la stéréo courante de cette attente et les variations de charge des autres postes. Une seule comparaison hors ligne, pas une mesure de délai physique de détection. **314 tests passent**, dont conservation des résultats avant/après insertion de la stéréo courante dans le cache, au démarrage et avec cache rempli. Les 17 sorties restent au-dessus de 20 ms, y compris le mouvement seul.

[Vérification reproductible des sorties](../outputs/motion_publication_20261018/verify.py) · [Mesures](../outputs/motion_publication_20261018/verification.json) · [Dernier rejeu](../outputs/motion_publication_20261018/after/clip.gif).

**Suite ciblée :** ce déplacement traite l'attente identifiée, pas la fiabilité. La représentation reste coûteuse et les correspondances d'objets mobiles restent non validées. Avant de changer la méthode de suivi, fixer une hypothèse et ses critères d'évaluation indépendants ; ne pas relancer les essais EVIMO2 clos, abaisser les seuils ou choisir une autre paire favorable. Les faibles erreurs aller-retour LK ne garantissent pas de bonnes correspondances. Aucun nouvel essai de fiabilité n'a été exécuté dans cette étape.

## Priorités actives — recadrage du 16 octobre 2026

Décision utilisateur : **traiter les points majeurs et critiques avant les points secondaires**. Cette décision remplace la prochaine étape EVIMO2 proposée auparavant. Retour au parcours principal `scripts/run_integrated_demo.py`, sur l'extrait DSEC et la configuration existants. Les acquis sont conservés.

| Ordre | Blocage majeur | Travail attendu | Preuve nécessaire |
|---|---|---|---|
| 1 — rapidité | Environ 258 ms médians de calcul par sortie pour un budget de 20 ms | Identifier le poste dominant à partir des mesures existantes, puis corriger une cause de coût importante dans le parcours intégré | Comparaison avant/après sur le même extrait, coût complet explicite et contrôle des sorties ; aucun gain revendiqué par simple accélération du GIF |
| 2 — fiabilité du mouvement | La séparation objet/caméra n'est pas validée | Améliorer la décision dans le démonstrateur DSEC et vérifier les objets manqués et les candidats injustifiés avec les références disponibles | Résultats mesurés avec couverture et abstentions ; classe YOLO ou résidu ne valent pas preuve de mobilité |
| 3 — estimation 3D | Profondeur et point de surface partiels | Consolider l'estimation associée aux objets, une fois les blocages précédents traités | Erreur et couverture aux dates de référence, sans présenter un point de surface comme un centre d'objet |

La fiabilité reste une contrainte pendant les optimisations de vitesse : une accélération qui dégrade les résultats sans compromis explicite n'est pas une amélioration validée. Les erreurs de calibration, de synchronisation ou de données qui invalident le calcul restent critiques et doivent être corrigées immédiatement si elles sont confirmées.

**En pause hors contrôle limité autorisé le 17 octobre ci-dessous :** branche EVIMO2 ; nouvelles grilles, variantes de seuils, nouveaux modèles/datasets, extensions de classes, améliorations de présentation et nouveaux rapports autonomes. Les défauts critiques déjà identifiés ne sont pas classés secondaires ; seules les pistes et finitions sans effet démontré sur le livrable sont différées. Y01 reste par défaut ; la qualification indépendante de Y02 sera nécessaire avant toute promotion, sans lancer maintenant une campagne dédiée.

**Correction réalisée le 17 octobre :** pré-calcul de la géométrie bilinéaire des deux cartes de calibration pour les images courantes du démonstrateur. Aucun événement agrégé ou réordonné, aucun seuil modifié. La reconstruction historique conserve sa voie de référence. Y01 reste par défaut ; comparaison avec Y02 explicite pour rester comparable au contrôle existant.

- Rectification seule, même fenêtre gauche de 364 240 événements, huit passages en ordre alterné : **60,94 → 38,51 ms médians (−36,8 %)**.
- Rejeu complet avant/après : préparation des images **149,29 → 136,61 ms médians** ; calcul complet **342,60 → 335,85 ms médians (−2,0 % observé)**. La moyenne complète augmente de 626,18 à 682,86 ms, avec un démarrage et d'autres postes plus lents : aucun gain global robuste annoncé sur cette unique paire de rejeux.
- Surcoût fixe explicite : **41,12 ms de préparation**, **25 190 400 octets** de tables pour les deux caméras, hors calcul par image et inclus dans le temps global d'exécution.
- **153 tableaux et 17 résultats scientifiques exactement identiques**, entrées de mêmes empreintes ; **292 tests passent**. Les 17 sorties restent hors budget de 20 ms. Mobilité toujours non validée.

[Preuves avant/après](../outputs/speed_20261017/verification.json) · [Rejeu conservé](../outputs/speed_20261017/after/clip.gif).

**Stéréo accélérée le 17 octobre :** l'appariement inverse s'exécute sur un unique worker persistant, avec son propre matcher OpenCV, pendant l'appariement direct et la récupération du bord. Le contrôle gauche/droite attend les deux résultats. Les images restent traitées dans l'ordre ; même résolution, recherche de disparité, seuils et fenêtres. Le même worker sert à l'historique manquant. OpenCV reste configuré à deux threads ; deux appariements peuvent maintenant consommer du CPU simultanément.

Comparaison dédiée avant/après, même extrait et Y02 explicite : stéréo **111,34 → 71,94 ms médians (−35,4 %)** ; calcul complet **310,53 → 257,76 ms médians (−17,0 % observé)**. Les autres postes varient également : toute la baisse globale ne peut pas être attribuée au parallélisme. **153 tableaux et 17 résultats scientifiques exactement identiques ; 294 tests passent**, dont équivalence parallèle/séquentiel et propagation d'une erreur du worker. **17/17 sorties restent hors budget**. [Preuves](../outputs/stereo_speed_20261017/verification.json) · [Rejeu actuel](../outputs/stereo_speed_20261017/after/clip.gif).

**Fiabilité — décision après relecture du 17 octobre :** les six diagnostics DSEC existants confirment 22 occurrences de boîtes, dont 7 sans historique et 15 traitables. Parmi ces 15 : 4 sans trajectoire, 2 sans profondeur exploitable, 6 évaluées sans résidu élevé, 3 avec candidat résiduel. Ce sont des états de support, pas des faux négatifs ou vrais positifs validés. Trois des quatre boîtes sans trajectoire ont seulement 0,43 %, 3,84 % et 5,56 % de pixels actifs ; la quatrième en a 54,97 %. L'activité faible est donc un obstacle observé dans trois cas, pas une cause universelle démontrée. Une boîte active peut aussi contenir du fond.

**Décision : aucune nouvelle correction de seuil, de grille ou de pose justifiée par ces éléments.** Baisser le seuil ne crée ni trajectoire ni profondeur et risque d'accroître les candidats injustifiés. Les contrôles de profondeur et de sensibilité de pose ci-dessous ont déjà été réalisés ; ne pas les recommencer. La proposition précédente « reprendre les objets manqués » conduisait à une boucle : elle est close par cette relecture, sans nouvelle inférence ni nouvelle mesure de qualité.

**Condition pour la prochaine avancée scientifique :** disposer d'une référence indépendante et alignée permettant d'évaluer le déplacement ou la pose. Le périmètre local DSEC actuel n'en fournit pas pour cette compensation ; les seules boîtes ne valident ni le suivi de chaque point ni la pose. L'extension de ce périmètre ou la reprise du contrôle EVIMO2 mis en pause exige un choix explicite de l'utilisateur. En attendant, conserver le démonstrateur accéléré comme prototype hors ligne et ses abstentions, sans prétendre avoir fiabilisé la mobilité. Aucune annotation manuelle demandée, aucun téléchargement ou changement de dataset effectué.

## Contrôle limité autorisé et réalisé — 17 octobre 2026

L'utilisateur a autorisé la reprise EVIMO2 existante pour vérifier les trois coins de l'objet 24 sur la paire figée 68→74. **Trois contrôles courts passent ; zéro suivi long accepté.** À 100 ms, les écarts à la référence sont 8,25 / 7,80 / 9,25 px et les erreurs aller-retour 25,45 / 7,30 / 11,30 px. Le détecteur n'a reçu aucune graine de référence : ces trois graines imposées sont réservées à ce diagnostic. Aucun ajustement de pose ni de seuil. Le contrôle court utilise des fenêtres chevauchantes et ne démontre pas à lui seul la justesse du déplacement.

**Décision :** améliorer la sélection seule ne suffit pas sur cette cible. Conserver les rejets. Une éventuelle correction devra porter sur le suivi temporel, testée sur la même paire contre la référence finale, sans multiplier les grilles ou les intervalles. La liaison par cinq pas de 20 ms a ensuite été testée : 3, 3, 3, 2, 2 survivants ; un seul passe les limites finales, mais son erreur de référence reste **7,72 px**. **Zéro suivi accepté à erreur ≤3 px : essai non promu.** Suivi seul 43,38 ms sur trois graines, hors lecture/représentation (1 235,91 ms) et oracle (307,69 ms), un appel à froid ; aucune performance DSEC déduite. Les images et références communes sont identiques au contrôle direct. Le contrôle limité est clos : pas de nouvelle grille, de seuil assoupli ou de balayage de pas temporels. Le démonstrateur DSEC et ses abstentions restent inchangés. **296 tests passent.** [Résultat détaillé](43_M14_EVIMO_AUDIT.md#suivabilité-des-trois-coins-de-la-cible--17-octobre-2026).

## Recherche d'un objet mieux visible — 17 octobre 2026

Extension autorisée sur le seul échantillon EVIMO2 existant. Critères enregistrés avant sélection : intervalle 100 ms, déplacement monde ≥1 cm, masques ≥1 000 pixels aux deux dates, marge au bord ≥10 pixels, historique et cartes complets. **Aucun candidat admissible.** 616 paires à intervalle exact examinées ; 4 exclues pour historique incomplet et 20 pour cartes manquantes. Parmi 220 cas objet/intervalle mobiles selon le critère de déplacement, 179 échouent à la surface visible et les 41 restants à la marge. La visibilité du masque ne garantit pas l'absence d'occlusion.

**Aucune inférence lancée, aucun critère relâché.** Recherche locale close ; les échecs précédents restent conservés. Une validation sur un objet mieux visible exige un autre extrait ou un nouveau protocole explicitement décidé avant résultats. Pas de nouvelle variante implicite à lancer sur ces données. [Protocole et audit](43_M14_EVIMO_AUDIT.md#recherche-bornée-dun-contrôle-mieux-visible--17-octobre-2026).

## Nouvel extrait autorisé et paire figée — 17 octobre 2026

Après accord utilisateur pour un autre extrait : `scene15_dyn_test_00_000000`, première autre séquence train dans l'archive officielle, téléchargée sous plafond de 512 Mio (319 Mio transférés, environ 147 Mio extraits). Les mêmes critères de visibilité et déplacement donnent un cas admissible : **objet 6, images 211→217**, **12,045 cm sur 100 ms**, masques de **5 608 / 4 853 pixels**, marge ≥10 px. Sélection enregistrée avant toute inférence ; aperçu de référence inspecté. **297 tests passent.** Aucun résultat de détection annoncé, DSEC inchangé.

**Contrôle exécuté une fois :** 50 coins initiaux sur la cible, 33 après contrôle court, **2 après suivi long** ; écarts de référence **1,081 et 5,079 px**. Toute l'image : 39 suivis conservés, 26 profondeurs oracle. Pose refusée malgré 22 inliers : support spatial **9,592 % < 10 %**. Tous les statuts restent `UNKNOWN`, aucune mobilité confirmée. Le garde-fou natif conserve aussi le mauvais suivi cible : non promu. **298 tests passent.**

**Correction unique testée, non promue :** un niveau de pyramide supplémentaire pour le suivi long, mêmes graines/images et seuil aller-retour. La cible passe de 2 à 9 suivis, mais 8 seulement sont comparables et **7 dépassent 3 px d'erreur** ; le nombre ≤3 px reste **1**. Le support global baisse de 39 à 26, la pose reste refusée. Coût LK seul 5,155→5,564 ms médians (appels alternés sur mêmes entrées). Défaut niveau 2 conservé, **299 tests passent**. [Comparaison](../outputs/motion/M14_next_sample_20261017/pyramid3/comparison.json).

**Hypothèse distincte testée ensuite :** remplacer le comptage par la date du dernier événement de chaque pixel, sur les mêmes 50 ms. Même sélection globale (recalculée sans GT), même LK niveau 2 et mêmes seuils. **Trois suivis cibles, tous >3 px** (3,963 / 5,539 / 7,669), contre un suivi ≤3 px auparavant. La pose passe les contrôles internes, avec écart oracle 0,270° / 4,661 mm ; cela ne valide pas le suivi de l'objet. Coût représentation + suivi sur entrées résidentes **26,87→28,90 ms médians**, hors lecture/cartes/pose/rendu. **Non promu, 302 tests passent.** [Comparaison](../outputs/motion/M14_next_sample_20261017/time_surface/comparison.json).

**Suite :** ces corrections locales ne résolvent pas le suivi de l'objet mobile. Clore aussi l'essai de récence, conserver le parcours DSEC et ses limites explicites. Aucun balayage de niveaux, fenêtres, décroissances, grilles ou seuils, et pas d'autre paire choisie pour obtenir un succès. Avant une autre modification du suivi, il faut une proposition méthodologique motivée et un critère de réussite fixé ; un nouveau « continue » ne justifie pas une autre variante automatique. Ce contrôle oracle ne valide pas DSEC. [Sélection et provenance](43_M14_EVIMO_AUDIT.md#autre-extrait-autorisé--cas-admissible-fixé--17-octobre-2026).

## Parcours par défaut Y01 vérifié — 17 octobre 2026

Retour au livrable principal après clôture du contrôle EVIMO2. Exécution sans `--weights`, donc Y01 personne/voiture, avec les optimisations de rectification et de stéréo conservées. Comparaison au rejeu historique `outputs/demo_border_20261015/targeted` : **mêmes empreintes d'entrée, 153 tableaux et 17 lignes scientifiques exactement identiques**. Aperçu inspecté. **77 occurrences de détection, 66 estimations de surface et 11 abstentions** ; ce ne sont pas 77 objets uniques.

Calcul médian **270,0 ms**, premier appel **3 523,0 ms**, 17/17 sorties au-delà de 20 ms. Comparaison de non-régression historique, pas benchmark apparié de vitesse ; cet extrait de développement appartient au train. Les résultats Y02 ci-dessus ne remplacent pas ce contrôle du modèle par défaut. Pas de changement du code dans cette étape ; dernier ensemble de tests : **296 réussis**.

[Résultat principal Y01](../outputs/demo_y01_20261017/clip.gif) · [Vérification](../outputs/demo_y01_20261017/verification.json).

**Point d'arrêt technique :** parcours intégré reproductible, rapidité insuffisante et mobilité non validée. Les deux contrôles de suivi EVIMO2 sont clos sans promotion. Ne pas interpréter un nouveau rejeu identique comme une avancée de fiabilité et ne pas relancer ces contrôles à chaque « continue ». La prochaine modification du détecteur doit apporter une hypothèse nouvelle justifiée et une référence adaptée à son évaluation.

## Où nous en sommes

Le projet est un **prototype intégré sur données enregistrées**. Il lit les événements DSEC, produit des images causales, détecte des classes avec YOLO11n, estime une disparité stéréo et un point de surface 3D, puis calcule des résidus après compensation d’un modèle rigide. Le résultat principal reste `clip.gif`, produit par `scripts/run_integrated_demo.py`.

| Objectif | Acquis vérifié | Limite actuelle |
|---|---|---|
| Rapidité | Optimisations du lecteur, représentations, historique exact et association ; sorties comparées avant/après | Contrôle Y02 du 17 octobre après parallélisme stéréo : médiane 257,8 ms pour un pas source de 20 ms, hors initialisation/rendu/export. Temps réel non atteint. |
| Détection de classes | Y01 personne/voiture par défaut ; Y02 ajoute camion, entraîné dans Colab | Reconnaître une classe ne prouve pas un mouvement propre ; validation camion indépendante absente. |
| Objets mobiles | Suivi causal sur 100 ms, profondeur à la date précédente, modèle rigide et abstentions | Pose caméra non validée ; des erreurs de profondeur, de suivi ou de pose peuvent produire un résidu. Pas de précision/rappel de mobilité démontrée. |
| Stéréo et XYZ | Cohérence gauche/droite, contrôle du support et estimation de surface visible | Couverture partielle ; ce point peut appartenir au fond, ce n’est pas un centre d’objet ni une trajectoire 3D. |
| Reproduction | Huit entrées identifiées et vérifiées par SHA256 ; export de données et paquet local disponibles | Un clonage seul ne contient ni données, ni poids, ni résultats ; distribution publique des artefacts non organisée. |

## Y02 : personne, voiture, camion

Y02 utilise les mêmes 536 images train et 238 images validation que Y01. Les classes exportées sont `person`, `car`, `truck` ; les 687 boîtes camion proviennent des annotations publiques existantes, sans annotation manuelle.

- Validation personne/voiture : **mAP50 38,52 %**, contre **23,73 % pour Y01** sur la même validation. Ce résultat porte sur un seul groupe de validation et ne mesure pas la mobilité.
- **Zéro référence camion en validation** : AP camion `null`, statut `NOT_EVALUATED`. Le surapprentissage à 99,5 % sur huit images est seulement un contrôle d’apprentissage.
- Rejeu de développement : **83 occurrences détectées, 74 estimations de surface, 9 abstentions**, avec un camion sur chacune des 17 images. L’extrait appartient au train ; ces occurrences ne sont pas des objets uniques ni une évaluation indépendante.
- Association optimisée : **15,4 ms médians contre 56,6 à 63,4 ms** dans les contrôles précédents ; sorties conservées exactement. Ne pas attribuer toute la variation du temps complet à cette seule correction.

**Y01 reste par défaut.** Sélection explicite de Y02 :

```powershell
.\.venv-demo\Scripts\python.exe scripts/run_integrated_demo.py --weights outputs/colab/Y02_20261015T134856Z/pilot/weights/best.pt --output outputs/demo_y02_repeat
```

Choisir une sortie neuve. [Dernier rejeu de contrôle Y02](../outputs/reviews/global_20261015/replay_y02/clip.gif) · [Égalité des 153 tableaux et des 17 résultats scientifiques](../outputs/reviews/global_20261015/regression.json) · [Benchmark de l’association](../outputs/yolo/Y02_association_speed/verification.json). Les chronométrages du contrôle de revue ne constituent pas un nouveau benchmark.

## Conclusion sur les preuves disponibles

Les références publiques de mobilité déjà vérifiées couvrent **six dates et 22 boîtes**. Sept boîtes sur deux dates restent sans historique suffisant. Sur les 15 boîtes traitables : **3 avec candidat résiduel, 6 évaluées sans candidat, 2 sans profondeur, 4 sans trajectoire**. Ce bilan mesure le support du diagnostic dans des boîtes partielles du train ; il ne constitue ni un rappel objet ni une mesure des fausses alertes. L’alignement RGB/événements et la présence possible du fond dans les boîtes limitent l’interprétation.

La correction stéréo conservée remplit uniquement les disparités auparavant invalides de la bande gauche de 96 colonnes, sous les contrôles de support et de cohérence habituels. Sur les nouveaux pixels évaluables à une seule date, l’erreur moyenne est **0,851 px**, avec **5,03 % au-delà de 3 px**. Cela ne valide pas les profondeurs de toutes les dates. Le changement de support de profondeur modifie aussi la pose : **550 statuts de points déjà évalués changent** dans le rejeu comparé. Plus de candidats ne signifie pas plus de vrais objets mobiles.

[Contrôles du bord et limites](../outputs/demo_border_20261015/verification.json). Les annotations ne sont pas des entrées du détecteur. Activité, classe YOLO, résidu et mouvement indépendant restent quatre notions distinctes.

## Contrat de cadence vérifié — 15 octobre 2026

Le démonstrateur compare désormais chaque sortie au **pas source existant de 20 ms (50 sorties/s)**. C’est le critère de cadence du rejeu, pas une performance atteinte ni une latence caméra promise. Le statut `cadence_budget` distingue le calcul seul du traitement séquentiel incluant rendu, NPZ et JSON ; le GIF affiche `HORS BUDGET` lorsque le calcul dépasse 20 ms. Les abstentions et la mention de mobilité non confirmée sont conservées.

Même extrait et Y02 explicite : **349,8 ms médians de calcul**, **468,2 ms avec rendu/écritures par image**, **17/17 dépassements**. Initialisation, empreintes, ouverture des lecteurs, console, publication finale du GIF/résumé et affichage du lecteur sont exclus de ce second coût ; le premier appel YOLO est inclus. Ce contrôle n’est pas un nouveau gain de vitesse. Le calcul hors YOLO reste à **311,0 ms médians** : accélérer uniquement YOLO ne suffirait pas à respecter 20 ms.

La simulation FIFO, sans saut d’image et avec file initialement vide, donne **9,23 s de retard final pour le calcul seul**, **11,17 s avec rendu/écritures**, sur les 17 sorties espacées de 320 ms entre la première et la dernière. Elle réutilise les coûts hors ligne mesurés, y compris le premier appel lent, et suppose l’historique disponible. **Ce n’est ni un délai de début de mouvement ni une latence mesurée en direct.** Le délai de début de mouvement reste `null`, faute de référence validée.

**Décision : budget non respecté ; conserver le statut de prototype hors ligne.** Aucun saut d’image, nouvelle cadence, changement de modèle ou seuil n’est introduit pour masquer le coût. **259 tests réussis**, 153 tableaux et résultats scientifiques des 17 images identiques au rejeu de revue ; aperçu inspecté. [Rejeu](../outputs/demo_contract_20261015/clip.gif) · [Mesures et contrat](../outputs/demo_contract_20261015/summary.json) · [Vérification](../outputs/demo_contract_20261015/verification.json).

## Compensation : sensibilité confirmée — 16 octobre 2026

À données, profondeurs, dates et seuils identiques, une permutation fixe de tous les points modifie **567 occurrences de statut sur 16/17 images**. Sur les quatre dates publiques traitables, **12 occurrences changent sur trois dates**, mais les catégories des **15 boîtes restent identiques** : 3 avec candidat, 6 sans candidat observé, 2 sans profondeur, 4 sans trajectoire. Aucun objet manqué n'est récupéré par ce contrôle ; aucune pose alternative n'est validée.

Le paramètre `seed` du solveur était trompeur : le backend classique utilise son propre générateur interne ([source OpenCV 4.14](https://github.com/opencv/opencv/blob/4.14.0/modules/calib3d/src/ptsetreg.cpp#L158)). L'appel global sans effet sur ce tirage est retiré ; `seed=42` reste une métadonnée de compatibilité, toute autre valeur est explicitement refusée. Les **21 modèles par défaut sont reproduits exactement**, ainsi que les associations de référence ; **261 tests passent**.

**Décision : conserver les résidus comme candidats non confirmés.** Le second ajustement coûterait ici 2,55 ms médians sur le rejeu (ajustement seul, pas coût complet d'un filtre), sans gain de qualité établi. Il reste dans le diagnostic existant ; aucune double estimation ni sélection par nombre d'inliers n'est ajoutée au parcours principal. [Preuves et limites](../outputs/focused_truck/pose_order_20261016/summary.json). La sensibilité numérique est démontrée ; distinguer une pose caméra correcte d'un mouvement dominant reste le blocage.

## La suite utile

**Vérification des dates de profondeur — 16 octobre :** les profondeurs historiques de compensation n'ont aucune référence DSEC à date exactement égale : **0/17** dans le rejeu, **0/4** parmi les dates publiques traitables. Les écarts à la référence la plus proche vont de 58 à 40 084 µs en valeur absolue dans le rejeu ; ceux des quatre dates publiques sont +58, −49 968, −20 et +49 995 µs. Les sept boîtes sans historique restent exclues. La référence de disparité à l'image finale ne valide donc pas la profondeur à `t−100 ms`. Aucun arrondi temporel ni calcul d'erreur sur une date voisine n'est effectué. [Dates et empreintes vérifiées](../outputs/focused_truck/pose_order_20261016/depth_reference_dates.json).

**Contrôle exact réalisé — 16 octobre :** profondeur à `36613900994 µs`, suivi jusqu'à `36614000994 µs`, fenêtres causales de 50 ms et fonctions actuelles inchangées. Cette paire est décalée de +58 µs par rapport à la dernière paire du rejeu : ce n'est pas une réévaluation des anciennes profondeurs sauvegardées. Sur **369 points suivis**, 258 ont une profondeur prédite, 103 une référence et **83 les deux**. Sur ces 83 points : **MAE disparité 0,571 px**, **2/83 au-delà de 3 px**, **MAE profondeur 1,720 m**, erreur absolue médiane **0,956 m**, erreur relative médiane **3,73 %**. Couverture des références suivies : **83/103 = 80,58 %** ; 20 références sans prédiction et 175 prédictions sans référence. Les références sont ouvertes après l'inférence et n'entrent pas dans la pose. **264 tests réussis**. [Mesures et provenance](../outputs/focused_truck/depth_exact_20261016/summary.json).

**Effet de profondeur à pose fixe contrôlé — 16 octobre :** les 83 paires restent projetables avec les deux profondeurs. Déplacement des projections : médiane **0,054 px**, moyenne **0,125 px**, maximum **2,247 px**. Les mêmes **74 points** restent à résidu ≤1,5 px et les mêmes **6 points** dépassent 3 px : **aucune transition**. Les projections initiales sont reproduites et les deux calculs vérifiés avec `cv2.projectPoints`, sans nouvel ajustement. **268 tests passent**. [Détail et contrôles](../outputs/focused_truck/depth_projection_20261016/summary.json).

**Décision : clore ce contrôle local de profondeur.** Remplacer uniquement la profondeur ne change pas les catégories sur ce sous-ensemble ; cela ne justifie pas une correction du détecteur ni une baisse du seuil. La pose reste celle ajustée avec les profondeurs prédites, donc son éventuel biais n'est pas corrigé. Les 175 profondeurs prédites sans référence, les erreurs de suivi et la pose caméra restent non validées. Ne pas répéter ce contrôle ni lancer une nouvelle variante par défaut : la prochaine avancée de fiabilité exige une référence indépendante du déplacement ou de la pose, dont il faudra établir la disponibilité et l'alignement avant toute modification du solveur.

La [page officielle DSEC](https://dsec.ifi.uzh.ch/dsec-datasets/download/) consultée le 16 octobre ne liste ni flux optique ni trajectoire caméra directement exploitable dans les entrées `zurich_city_04_b` et `zurich_city_04_e`. Un lot LiDAR/IMU séparé est proposé ; il n'a pas été acquis ni interprété comme une vérité de pose. Aucun fichier de pose, IMU ou flux optique n'a été trouvé dans les dossiers locaux de ces séquences.

**Contrôle EVIMO2 séparé autorisé — bilan du 16 octobre :** sur 60→66, la pose oracle diffère de la référence de 0,139° / 0,642 mm ; trois candidats reposent sur une activité native isolée. Le garde-fou spatial retire ces trois points mais aussi 13 correspondances compatibles, sans validation de conservation du mouvement propre. Sur le contrôle positif choisi avant prédiction (68→74, objet 24 déplacé de 11,29 mm), la sélection globale ne place aucune graine sur l'objet partiellement visible au bord supérieur. Les références sont utilisables pour ce contrôle local, pas pour valider la pose DSEC.

**Répartition spatiale 8×6 testée, non retenue :** plafond inchangé de 400 points, mêmes seuils et deux paires figées. Aucun point cible récupéré : son meilleur coin est 10ᵉ dans sa zone, qui reçoit neuf places. Les suivis passent de 274 à 236 sur 60→66 et de 290 à 246 sur 68→74 ; coût médian du sélecteur seul augmenté de 0,56 et 1,19 ms. Les points communs gardent exactement les mêmes extrémités : le changement porte sur le support choisi. **289 tests passent.** La méthode globale reste par défaut ; la grille et le garde-fou restent expérimentaux. Aucun balayage de grilles, gain de mobilité ou de cadence revendiqué. [Détail et reproduction](43_M14_EVIMO_AUDIT.md#répartition-spatiale-à-budget-constant--16-octobre-2026) · [Comparaison](../outputs/motion/M14_positive_control_20261016/spatial_seeds/comparison.png).

**Décision actualisée : clore cette hypothèse de grille fixe et mettre la branche EVIMO2 en pause.** La suivabilité des trois coins n'est plus la prochaine étape. Les résultats et outils restent conservés comme historique ; appliquer les priorités actives en tête de page. Les annotations manuelles restent sautées.

## Repères de maintenance

- [README : exécuter et préparer le démonstrateur](../README.md).
- [Commandes](16_COMMANDS.md), [cahier des charges](PROJECT_BRIEF.md), [journal complet](19_PROGRESS.md), [revue et organisation](44_PROJECT_MAINTENANCE.md).
- Modifier les sources Markdown, puis exécuter `.\.venv\Scripts\python.exe scripts/sync_markdowns.py`.
- Conserver les données, poids et résultats localement ; `markdowns/` reste un miroir ignoré par Git.
<!-- END ROADMAP SNAPSHOT 20261019 69c98968 -->

</details>
