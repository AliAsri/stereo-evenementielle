# Disparité, profondeur et erreurs

## Conversion

Après rectification, définir `d=u_L-u_R`. Dans la forme canonique avec points principaux horizontaux identiques : `Z=fx*B/d`. Plus généralement `Z=fx*B/(d-(cx_L-cx_R))` pour une paire horizontale compatible. La matrice Q fournie évite de supposer cette égalité sans la vérifier : calculer `q=Q@[u,v,d,1]`, puis `[X,Y,Z]=q[:3]/q[3]`. Q doit correspondre à la paire, au repère et à la résolution. [OpenCV, reprojection](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html).

## Unités et invalidité

DSEC code la disparité GT en PNG uint16 : zéro invalide, valeurs valides à diviser par 256. Cette échelle est propre à ce stockage. Les sorties fixes de StereoSGBM sont couramment à diviser par 16 ; une sortie de réseau peut déjà être en pixels. Chaque adaptateur doit exposer son unité et son masque. [Format DSEC](https://dsec.ifi.uzh.ch/data-format/), [StereoSGBM](https://docs.opencv.org/4.x/d2/d85/classcv_1_1StereoSGBM.html).

Ne pas interpréter la GT comme une prédiction du pipeline. La GT sert à un test de décodage, à la supervision et à l'évaluation ; elle n'est jamais un repli pour une profondeur prédite invalide.

## Baseline S01 exécutée

Accumulations gauche/droite sur la même fenêtre de 50 ms → rectification bilinéaire → canal logarithmique total avec échelle commune → SGBM. S01 utilise 96 disparités, blocs 5×5, P1=200/P2=800, unicité 10, suppression de petites composantes et contrôle gauche-droite explicite à 1,5 px. Un support événementiel doit exister dans les blocs des deux vues. Les disparités rejetées restent NaN ; aucun remplissage par la GT ou par un voisin n'est effectué.

Le second matching s'effectue sur les images `(droite, gauche)` retournées horizontalement, puis la carte est retournée à nouveau. Cela permet de vérifier un même déplacement positif `u_L-u_R`, sans utiliser à tort un matcher positif sur la paire inverse non retournée. Un test de texture synthétique décalée de huit pixels contrôle ce signe.

Les fichiers `frame_*.npz` contiennent disparité en pixels, masque, sortie brute Q4, profondeur en mètres, matrice Q et temps de fenêtre. La profondeur est dérivée exclusivement de la disparité prédite. Une vérification après écriture a retrouvé `Z=fx*B/d` sur les 60 fichiers, avec NaN aux pixels invalides. [Protocole complet](21_STEREO_BASELINE.md) et [résultats](13_RESULTS.md).

Le candidat profond remplace uniquement ce bloc, avec son propre prétraitement. Son premier audit mesure forme, signe, résolution et valeurs finies avant toute interprétation qualitative.

## Incertitude utile

Pour le cas canonique, propagation au premier ordre : `sigma_Z ≈ fx*B*sigma_d/d²`. Une petite erreur de disparité devient donc une grande erreur en distance pour les objets lointains. Exemple **analytique fictif** : `fx=500 px`, `B=0,2 m`, `d=10 px` donne `Z=10 m` ; avec `sigma_d=1 px`, `sigma_Z≈1 m`. Ce n'est pas une mesure du dataset.

Plage de distance, seuil minimum de disparité et dispersion acceptable seront figés sur validation. Publier EPE/MAE et Bad1/Bad2/Bad3 en pixels, avec définition exacte ; les scores nommés D1 dans certains benchmarks ont une règle relative/absolue spécifique et ne doivent pas être confondus.
