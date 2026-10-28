# Premier audit automatique des contenus visuels

## Conclusion

L'inventaire et la comparaison sont automatisables sur un document entier.
Le premier essai ne justifie pas de remplacer le repérage Poppler par cette
méthode OpenCV : elle élimine certaines fausses alertes, mais manque aussi de
vrais contenus. Le lecteur conserve son détecteur actuel.

## Essai du 28 octobre 2026

Document local : *System Design Interview*, Alex Xu, 269 pages physiques.
Empreinte SHA-256 : `1556d7a7cbcc1ec82dacfad4ffde2d39674fef27f34e00a7b7aa483878d5e821`.
Environnement : macOS 26.2 ARM64, OpenCV 5.0.0, CPU, un fil OpenCV,
rendu maximal de 1600 pixels. Aucun modèle téléchargé, aucun appel d'API.

| Pages signalées | Nombre |
|---|---:|
| Par les deux méthodes | 166 |
| Par Poppler uniquement | 31 |
| Par OpenCV uniquement | 0 |
| Par aucune des deux | 72 |
| Erreurs d'analyse | 0 |

Une passe locale a pris 58,54 secondes, hors extraction initiale et galerie :
11,33 secondes pour l'analyse structurelle et 47,10 secondes pour le rendu
des pages suivi d'OpenCV. Ce sont des temps observés sur cette machine, pas une
comparaison universelle ni un temps d'inférence OpenCV isolé.

## Méthodes comparées

Poppler inventorie les images intégrées et les tracés SVG, selon les filtres
actuels de Reader. Une simple mention « Figure » n'est pas comptée comme une
détection structurelle dans cet audit.

OpenCV reçoit une page rendue, masque les rectangles des mots sélectionnables,
puis examine les composantes d'encre restantes. Il mesure aussi les lignes
horizontales et verticales par morphologie. Les zones candidates ne sont pas
des classes « tableau », « formule » ou « figure ».
Sources : [morphologie](https://docs.opencv.org/4.13.0/dd/dd7/tutorial_morph_lines_detection.html),
[contours](https://docs.opencv.org/4.13.0/d4/d73/tutorial_py_contours_begin.html).

## Contrôle visuel de 16 pages

Un échantillon reproductible mélange accords et désaccords. L'assistant a
examiné la planche des 16 pages et des vues détaillées des pages 33, 222, 245
et 254. Les annotations sont conservées séparément des détections.

- Pages 6, 67, 112, 173 et 235 : schémas visibles, signalés par les deux méthodes.
- Pages 222 et 245 : tableau et capture d'écran visibles, signalés par Poppler,
  manqués par cette méthode OpenCV.
- Pages 2, 33, 86 et 109 : mentions légales ou bibliographies avec liens
  soulignés ; fausses alertes structurelles Poppler dans cet échantillon.
- Pages 50, 69, 120, 221 et 254 : texte courant, aucun objet visuel relevé
  lors de ce contrôle, aucune détection structurelle.

Cet échantillon est orienté vers les désaccords. Il ne permet pas d'annoncer une
précision ou un rappel sur les 269 pages. En particulier, une absence de
détection n'est pas une annotation négative automatique.

## Suite recommandée

Conserver le signal des images intégrées : le filtrer par OpenCV ferait perdre
les pages 222 et 245. Examiner plutôt les tracés qui correspondent aux liens
soulignés pour réduire les fausses alertes, sans supprimer les vrais graphes.
Ajouter ensuite des exemples indépendants : formules, tableaux sans bordures,
pages scannées et autres mises en page. Aucun YOLO n'a été évalué à ce stade.

L'outil `audit_visuals.py` produit inventaires JSON/CSV, galerie locale et export
d'annotations, avec reprise après interruption. Les rendus et données du livre
restent dans `output/pdf/`, exclu de Git ; la mémoire de lecture n'est jamais
ouverte. Le README donne les commandes pour un autre document.
