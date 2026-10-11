# Événements et conventions du projet

## Mesure physique

Une caméra événementielle compare localement la luminance logarithmique à une référence. Un changement de magnitude suffisante déclenche un événement `e=(x,y,t,p)`. `p` indique une hausse ou une baisse ; ce n'est pas une intensité absolue. Les seuils et le bruit varient entre pixels et capteurs. Le flux est asynchrone, sans obligation de produire un événement pour chaque pixel à chaque instant. [Gallego et al., Event-based Vision: A Survey](https://arxiv.org/abs/1904.08405).

Conséquences pour notre développement : un pixel sans événement n'est pas nécessairement noir, vide ou invalide physiquement ; il peut simplement être stable. L'absence d'événements ne signifie pas absence d'objet. Le mouvement de la caméra fait apparaître des événements sur des objets statiques, et un scintillement lumineux peut en générer sans déplacement.

## Contrat interne proposé

- `x`, `y` : indices entiers du capteur natif, origine en haut à gauche, x colonne et y ligne.
- `t_us` : microsecondes entières dans l'horloge commune de la séquence ; ne pas convertir les temps absolus en float32.
- `p` : convention canonique 0/1 pour le stockage ; conversion signée explicite `2*p-1` si nécessaire, après conversion en type signé.
- Fenêtre causale : `[t_end-delta, t_end)` ; jamais d'événement après la date de décision.
- Gauche et droite partagent **les mêmes bornes**, pas le même nombre d'événements.
- La sortie doit indiquer `native_left`, `native_right`, `rectified_left` ou `rectified_right` ; les types de coordonnées ne sont pas interchangeables.

## Particularités DSEC vérifiées

Le HDF5 contient `events/x,y,t,p`, `ms_to_idx` et `t_offset`. Les temps sont en µs ; ajouter l'offset propre au fichier pour rejoindre l'horloge des autres modalités. `ms_to_idx` accélère l'accès. Les événements sont non rectifiés ; la table `rectify_map[y,x]` donne leurs coordonnées rectifiées. La compression utilise Blosc/ZSTD, d'où l'import de `hdf5plugin` avant lecture. [Format officiel](https://dsec.ifi.uzh.ch/data-format/).

## Inspection avant filtrage

Vérifier longueur égale des quatre tableaux, types entiers, ordre temporel non décroissant, bornes de pixels, polarités autorisées, premier/dernier temps et chevauchement stéréo. Compter événements/s, proportion de polarités et activité spatiale. Le nombre brut avant/après toute transformation doit être conservé pour diagnostiquer une perte.

Le premier lecteur doit lire une tranche HDF5, sans charger toute la séquence. Une recherche binaire sur les timestamps constitue une référence simple pour vérifier plus tard le chemin accéléré par `ms_to_idx`. Cette référence n'est pas annoncée optimale en débit.

## Filtrage prévu

Commencer sans filtre afin de disposer d'un témoin. Tester ensuite suppression de pixels anormalement actifs et filtre de voisinage spatio-temporel, avec paramètres inscrits dans la configuration. Ne pas utiliser d'événements futurs pour confirmer un événement passé dans une expérience de latence causale. Un filtre peut effacer les contours fins des piétons ; contrôler l'effet sur détection et stéréo, pas seulement la propreté visuelle.
