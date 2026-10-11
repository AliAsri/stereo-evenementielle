# Géométrie stéréo et rectification

## Notation

Dans une caméra pinhole, un point homogène se projette selon `s*[u,v,1]^T = K*[X,Y,Z]^T`. `K` contient `fx,fy,cx,cy`, en pixels pour l'image utilisée. L'extrinsèque `T_RL` transforme un point gauche vers droite. Sa translation est en mètres si la calibration est métrique. La baseline est la distance entre centres optiques ; elle n'est pas une constante à recopier d'un autre dataset.

Pour des points normalisés non déformés, `E=[t]_x R`. Pour les pixels correspondants, `F=K_R^(-T) E K_L^(-1)` et `x_R^T F x_L=0`. Ces relations réduisent la recherche à une ligne épipolaire. La rectification fait correspondre ces lignes à des lignes horizontales ; elle change les intrinsics effectifs.

[Documentation géométrique OpenCV](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html). Les équations sont les conventions de calcul à appliquer et à tester dans ce projet.

## Contrôles DSEC

Choisir la paire événementielle `cam0/cam3`, ses versions rectifiées et `disparity_to_depth.cams_03`. La paire d'images `cam1/cam2` est différente. `T_XY` transforme Y vers X ; `R_rect0` transforme la caméra native gauche vers sa caméra rectifiée. [Convention officielle](https://dsec.ifi.uzh.ch/data-format/).

Composition à vérifier sur le fichier réel : `T_30 = T_32 @ T_21 @ T_10`. La norme de sa translation doit correspondre à la baseline extraite de Q lorsque Q suit la forme rectifiée canonique. Vérifier les rotations : `R.T @ R ≈ I`, `det(R)≈1` ; une transformation inversée peut produire une profondeur de signe erroné tout en donnant une image plausible.

## Rectifier des événements

Lire la table de rectification associée au flux et transformer les coordonnées des événements. Les coordonnées obtenues sont généralement fractionnaires. Pour un premier affichage, arrondir et rejeter les points hors champ ; pour les tenseurs du modèle, suivre exactement l'interpolation de son prétraitement. Ne jamais indexer un tableau avec une coordonnée négative non filtrée : NumPy sélectionnerait depuis la fin.

Une `rectify_map` est un mapping direct **du natif vers le rectifié**. Ce n'est pas automatiquement une carte inverse à passer à `cv2.remap`.

## Changements d'échelle

Une réduction horizontale par `sx` implique `fx'=sx*fx`, `cx'` selon la convention exacte de transformation de pixels et `d'=sx*d`. Une simple multiplication du tableau de disparité sans transformation spatiale ne suffit pas. Pour le MVP, garder la résolution native côté géométrie. Le letterbox propre à YOLO doit être inversé avant tout accès aux ROI natives.

## Vérification avant matching

Superposer les deux représentations rectifiées avec des lignes horizontales ; vérifier manuellement plusieurs contours et mesurer des résidus verticaux sur des correspondances fiables. Une visualisation correcte ne prouve pas seule une synchronisation parfaite. Conserver le contrôle temporel et les tests de calibration séparés.
