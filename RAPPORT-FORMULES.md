# Repérage enrichi des formules PDF

## Livraison

Le repérage enrichi combine les indices typographiques du PDF et un modèle
visuel DocLayout-YOLO préentraîné. Il signale la présence probable de formules,
sans les transcrire ni les expliquer. Les images et tracés Poppler sont conservés.

L'installation est facultative : `./install.sh --layout`. Ensuite, la lecture
prépare les pages en arrière-plan, avec priorité au passage affiché. La commande
`./reader "document.pdf" --prepare` remplit le cache avant la lecture, sans ouvrir
SQLite. Fermer le lecteur arrête son processus ; les pages terminées sont
conservées pour la reprise. Le README décrit les modes et les limites.

## Évaluation sur Russell et Norvig

Document : quatrième édition globale, 1 166 pages physiques ; même empreinte
que dans [l'audit précédent](RAPPORT-AUDIT-AIMA.md).

Une première sélection de 50 pages comprend les 24 pages déjà contrôlées,
des pages riches en symboles et des pages réparties dans le livre. Le parcours
a ensuite été étendu aux **1 166 pages**, toutes préparées sans erreur.

| Indice de formules par page | Pages |
|---|---:|
| Typographie seule ou avec le modèle | 381 |
| Modèle seul ou avec la typographie | 377 |
| Union des deux méthodes | 443 |
| Avec formule probable, sans ancien indice images/tracés | 230 |

Ces nombres sont des **signalements**, pas des annotations de référence ni une
mesure de précision. Les 230 pages supplémentaires demanderaient un contrôle
indépendant pour déterminer le nombre de vrais gains et de fausses alertes.

## Contrôles concrets

- Pages **293 et 633** : formules désormais repérées, alors que l'ancien audit
  ne donnait aucun indice structurel. Les cadres proposés ont été inspectés.
- Pages **245 et 410** : expressions repérées par le modèle et la typographie.
- Pages **47 et 587** : contrôles de texte courant, sans alerte de formules.
- Une copie rasterisée de la page 293 simule un scan sans texte sélectionnable :
  **3 zones** repérées par le modèle, aucune par la typographie. Ce test établit
  une capacité sur cet exemple, sans garantir tous les scans.
- Des affectations de pseudocode sont parfois retenues par la typographie,
  notamment page 196. Les zones restent qualifiées de probables et ne doivent
  pas être prises pour un nombre exact d'équations.

Les rendus annotés de contrôle sont locaux, dans `output/pdf/formula-eval/`,
exclus de Git. La lecture interactive sur la page 293 a confirmé l'indicateur,
la conservation de position et la restauration du terminal.

## Coût observé

Machine : macOS 26.2 ARM64, accélération Apple MPS, PyMuPDF 1.26.7,
DocLayout-YOLO 0.0.4, PyTorch 2.14.1, rendu maximal 1536 pixels et entrée
modèle de 1024 pixels. L'environnement optionnel occupe environ **1,2 Go**,
auxquels s'ajoutent le modèle de 40,7 Mo et le cache.

La préparation complémentaire du livre a pris **182,10 secondes**, après
constitution partielle du cache pendant les essais. Ce n'est donc pas un temps
à froid des 1 166 pages. La médiane des durées de page conservées est d'environ
**0,142 seconde**, avec des initialisations et vérifications distinctes.

Un essai CPU séparé sur les pages 47, 293 et 633 a également réussi : aucune
alerte sur 47, sept zones sur 293 et deux sur 633. Les durées observées étaient
d'environ 0,70 à 0,95 seconde par page, hors chargement initial du modèle.
Ces mesures ne constituent pas une garantie pour une autre machine ou un autre PDF.

## Validation et provenance

Les **74 tests** passent dans l'environnement enrichi. Ils couvrent notamment
le cache, les polices et indices mathématiques, les pages tournées, la priorité
au passage, le retour au CPU, l'arrêt du processus et l'absence de création de
mémoire pendant `--prepare`.

Le checkpoint est lié à une révision et une empreinte SHA-256 vérifiées avant
chargement. La préparation bloque les connexions réseau Python et les
installations automatiques du SDK ; seul le téléchargement explicite du modèle
pendant l'installation utilise le réseau.

Sources techniques : [extraction PyMuPDF](https://pymupdf.readthedocs.io/en/latest/textpage.html),
[DocLayout-YOLO officiel](https://github.com/opendatalab/DocLayout-YOLO),
[checkpoint](https://huggingface.co/juliozhao/DocLayout-YOLO-DocStructBench).
