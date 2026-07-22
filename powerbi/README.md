# Power BI

- `wattwatch_theme.json` : theme visuel (couleurs, cartes arrondies), a importer via Affichage -> Themes -> Parcourir les themes.
- `senegal_concessions.geojson` : contours des 45 departements du Senegal (source [GADM](https://gadm.org), niveau administratif 2, licence gratuite pour usage non commercial), avec un attribut `concession` ajoute a chaque departement (SENELEC/ERA/LLK/DPSL/SCL) selon la zone de concession electrique correspondante. A importer dans le visuel Carte de formes (Shape Map), champ de correspondance = `concession`.

Limite a garder en tete : les zones de concession rurale (ERA/LLK/DPSL/SCL) ne sont pas des decoupages administratifs officiels, elles recoupent approximativement des departements entiers (Kaffrine/Tambacounda/Kedougou pour ERA, etc.). SENELEC n'est pas non plus cantonne aux 35 departements restants : il coexiste avec les concessions rurales dans les memes zones (villes vs campagne). La carte est une approximation utile pour la visualisation, pas une frontiere juridique exacte.
