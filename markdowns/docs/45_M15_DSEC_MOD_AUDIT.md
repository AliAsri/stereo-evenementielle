# M15 — Audit DSEC-MOD : annotations acquises, alignement à résoudre

**8 octobre 2026.** Après R01, l'étape M15 prépare une référence publique pour vérifier la détection des objets mobiles sur DSEC, sans annotations manuelles utilisateur. L'acquisition bornée et l'audit du format sont réalisés. **La référence n'est pas encore prête pour noter les sorties événementielles.**

## Ce qui est acquis

Source : dépôt officiel [RENet / DSEC-MOD](https://github.com/ZZY-Zhou/RENet), version figée `0c52e1ed4be6fc7454b4f2d1938511eb010fbf61`. Le fichier `data/DSEC/DSEC-GT.pkl` contient 1 123 535 octets ; son SHA256 est conservé dans [le manifeste](../outputs/motion/M15/acquisition.json). Les fichiers de code amont consultés sont conservés comme texte et n'ont pas été exécutés.

Le cache expose une seule classe, **Moving**, confirmée par [la réponse de l'auteur, issue 17](https://github.com/ZZY-Zhou/RENet/issues/17). Il ne fournit pas les catégories détaillées de DSEC-Detection. Une classe YOLO « car » et une annotation DSEC-MOD « Moving » répondent à deux questions différentes.

L'archive train annoncée à 15 Go mesure 15 990 865 716 octets. L'accès HTTP partiel a permis d'obtenir son index et trois PNG précis de `zurich_city_04_e`, sans télécharger les flux d'événements déjà disponibles localement ni l'archive entière. Les images 1, 134 et 267 ont été choisies avant inspection, au début, au milieu et à la fin de la séquence.

- Index RAR5 : 10 517 en-têtes consultés, CRC des structures vérifiés ; il contient 10 495 RGB et 22 fichiers événements/calibration.
- Trois images 640×480 : 1 347 325 octets lus dans les blocs de fichiers, vérification des en-têtes réels contre l'index puis des tailles et CRC des PNG extraits.
- Deux fichiers d'horodatages RGB DSEC officiels : 3 228 octets chacun.
- Aucune nouvelle dépendance installée ; extraction des trois membres autorisés vers la sortie standard avec `tar.exe`, puis écriture sous des noms locaux fixés.

Les petits RAR reconstruits et les scripts ponctuels de cette acquisition sont conservés dans `outputs/motion/M15/`. Ils sont des preuves de cette opération, pas un téléchargeur RAR général. Le formulaire public Google Drive peut expirer ; l'audit local n'en dépend plus.

## Résultats de l'audit train

| Séquence | Rôle local | Images MOD | Tubes | Boîtes Moving | Dates RGB DSEC |
|---|---|---:|---:|---:|---:|
| `zurich_city_04_e` | train | 267 | 11 | 928 | 269 |
| `zurich_city_04_b` | train | 267 | 13 | 866 | 269 |

Soit **1 794 boîtes sur 534 images**, toutes appartenant au train officiel. Chaque image de ces deux séquences possède au moins une boîte. Le format numérique est `frame, x1, y1, x2, y2`, avec indices commençant à 1. Sur ces deux séquences : coordonnées finies, boîtes de surface positive dans les limites 640×480, indices de frame strictement croissants et aucun trou à l'intérieur des tubes.

Le numéro de tube est seulement l'indice de la liste publiée : il ne devient pas un identifiant universel d'objet. L'audit ne certifie ni l'exhaustivité des annotations ni leur précision au début et à la fin d'un mouvement. Ce sous-ensemble ne fournit pas d'images intégralement négatives permettant à lui seul d'étudier toutes les fausses alertes.

[Rapport machine](../outputs/motion/M15/audit/report.json) · [Export train seulement](../outputs/motion/M15/audit/train_annotations.json) · [Aperçu](../outputs/motion/M15/audit/train_preview.png).

![Images officielles train et annotations Moving](../outputs/motion/M15/audit/train_preview.png)

À gauche : RGB projeté fourni par DSEC-MOD. À droite : les mêmes images avec les annotations publiées. À la première date, les boîtes entourent deux voitures et un camion ; les suivantes montrent notamment les véhicules devant la caméra. **Ce sont des annotations de référence, pas les prédictions de notre détecteur.** Le placement paraît cohérent sur ces trois images, sans prouver un alignement avec les événements ni la mobilité à partir d'une image fixe.

## Deux correspondances encore manquantes

### Numéro de frame vers timestamp

Le cache ne contient pas de timestamps. Les RGB MOD sont nommés `000001.png` à `000267.png`, tandis que les fichiers RGB DSEC contiennent **269 dates** pour chacune de ces séquences. Leurs pas médians sont 49 998 µs (`04_e`) et 50 002 µs (`04_b`).

Sources des dates : [04_e](https://download.ifi.uzh.ch/rpg/DSEC/train/zurich_city_04_e/zurich_city_04_e_image_timestamps.txt) et [04_b](https://download.ifi.uzh.ch/rpg/DSEC/train/zurich_city_04_b/zurich_city_04_b_image_timestamps.txt), reliées depuis [le téléchargement DSEC](https://dsec.ifi.uzh.ch/dsec-datasets/download/).

Un retrait de deux images est une hypothèse, pas une preuve du décalage exact. L'index de l'archive MOD ne contient aucun fichier de timestamps. Aucun calcul `frame × 50 ms` ni appariement automatique « même indice » n'est adopté. L'export conserve `timestamp_us: null` et le statut `NOT_READY_FOR_EVENT_SCORING`.

### Boîte RGB projetée vers événement natif ou rectifié

Le README amont indique une projection RGB vers le champ de vue et la résolution événementiels. Cela ne fixe pas à lui seul la transformation précise vers nos coordonnées natives ou rectifiées. Une résolution commune de 640×480 ne suffit pas. Ne pas superposer directement ces boîtes sur M12 puis compter les correspondances tant que le repère n'est pas vérifié.

## Partitions et réserve de test

Les métadonnées officielles totalisent 11 séquences / 10 495 frames train et 5 séquences / 2 819 frames test. `04_e` et `04_b` sont train dans les deux protocoles ; `thun_00_a`, notre validation locale, est absent de DSEC-MOD.

Le fichier pickle officiel regroupe aussi les annotations test, dont `zurich_city_09_b`. **Leurs octets ont donc été acquis avec le fichier**, ce qui précise la mention historique « non acquis ». Seuls noms, partitions et tailles de séquences ont été consultés côté test. Les tableaux test restent des enveloppes d'octets : aucune matérialisation numérique, inspection de boîtes, export, image ou métrique test. Les événements et images de `09_b` restent non acquis.

Le groupe de trajet `zurich_city_09` apparaît dans les deux splits officiels (`09_e` train, `09_b` test). Notre protocole local conserve sa séparation par groupe : ne pas ajouter `09_e` au réglage tout en revendiquant `09_b` comme groupe indépendant. Aucun split local n'a été changé. Les anciens manifestes restent des snapshots datés.

Les droits de redistribution propres aux annotations MOD ne sont pas établis par les sources consultées ; conserver attribution et provenance, sans présumer qu'une licence du corpus parent couvre ces annotations.

## Code et vérification

- `src/pfe_events/dsec_mod_reference.py` : lecteur spécialisé plafonné à 2 Mio. Les constructeurs NumPy du pickle sont remplacés par des enveloppes inertes ; les globals inconnus sont refusés. Seules les séquences train explicitement sélectionnées sont converties en tableaux. Ce lecteur n'est pas un bac à sable pickle universel.
- `scripts/audit_dsec_mod_sample.py` : vérifie les hashes des acquisitions, prend les séquences locales train, exporte les annotations avec dates inconnues et produit la planche.
- `tests/test_dsec_mod_reference.py` : neuf contrôles couvrant notamment le refus des payloads exécutables, la séparation test, les indices invalides, les dtypes, les limites de taille et l'absence de clipping silencieux.

**Vérification exécutée : 153 tests réussis, syntaxe de 81 fichiers Python et aides de 25 commandes vérifiées.** [Rapport des contrôles](../outputs/checks/M15/report.json) et [journal des tests](../outputs/checks/M15/tests.log). Les sources exécutées sont conservées dans `outputs/motion/M15/sources/`. Aucun algorithme de détection existant ni résultat historique modifié.

Reproduire hors ligne dans un dossier neuf :

```powershell
.\.venv\Scripts\python.exe scripts/audit_dsec_mod_sample.py --output outputs/motion/M15_audit_repeat
.\.venv\Scripts\python.exe scripts/check_project.py --output outputs/checks/M15_repeat
```

## Suite : M16, alignement sur train

1. Comparer les trois RGB MOD acquis à quelques RGB DSEC originaux datés, en documentant projection, indexation et éventuelles images retirées. Vérifier plusieurs dates éloignées, puis confirmer sur `04_b`.
2. Fixer et tester la transformation des boîtes vers le repère du détecteur. Une annotation absente ou une date ambiguë reste inconnue.
3. Ensuite seulement, confronter les candidats géométriques M12/M13 à cette référence, avec règle d'association et support de comparaison définis. Distinguer localisation sur images annotées, erreurs de mobilité et délai de détection ; des labels à environ 20 Hz ne donnent pas un début de mouvement exact à 10 ms.

Aucun score de mobilité réelle, gain de fausses alertes ou délai n'est annoncé dans M15. La compensation du mouvement caméra reste prioritaire ; YOLO, stéréo et XYZ restent dans le périmètre. EVIMO M14 est conservé comme complément.
