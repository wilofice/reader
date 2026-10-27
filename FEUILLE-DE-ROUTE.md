# Reader : documents enrichis, relectures et lecture ZEN

Compte rendu des demandes du 27 octobre 2026. **Première livraison : ZEN,
cycles de lecture, références et aperçu visuel de page PDF** ; les autres fonctions restent
des propositions à développer. L'aperçu affiche la page entière avec Poppler et
Chafa (centré dans iTerm2), ou dans Quick Look sur macOS ; il ne détecte ni
n'interprète les objets complexes. La sélection automatique est documentée
dans le README. Ce document complète le
[rapport sur l'apprentissage](RAPPORT-LECTURE-APPRENTISSAGE.md).

## 1. Intentions retenues

Lire les documents dans leur intégralité depuis le terminal, y compris les
images, graphiques, tableaux et formules. Disposer d'une lecture épurée ou
accompagnée d'enrichissements, sans déléguer systématiquement sa réflexion.
Conserver chaque lecture complète d'un même document, puis ajouter la voix
dans un deuxième temps.

L'utilisateur accepte un prétraitement consommant CPU/GPU et des services
payants si la qualité le justifie. La configuration exacte du Dell G15 et du
MacBook Air reste à relever avant le choix des modèles et les benchmarks.
Aucune disponibilité de GPU, quantité de mémoire ou performance n'est supposée.

## 2. Priorisation proposée

| Ordre | Chantier | Résultat attendu | Dépendance principale |
| --- | --- | --- | --- |
| 1 | Mode ZEN | Un texte lisible, sans encombrement ni sollicitations | Interface actuelle |
| 2 | Cycles de lecture | Terminer une lecture avant d'ouvrir la suivante, avec historique | Migration de la mémoire SQLite |
| 3 | Document structuré et cache | Conserver blocs, images, sources et ordre de lecture |
| 4 | Images, graphes, tableaux, formules | Lire et inspecter les contenus complexes sans application externe |
| 5 | Passages proportionnels et navigation | Avancer finement sans découper les objets complexes |
| 6 | Colonne d'accompagnement LLM | Contexte, indices, vocabulaire, questions et QCM à la demande |
| 7 | Voix de lecture | Audio synchronisé et piloté depuis le terminal |

Les chantiers 3 et 4 sont le principal investissement technique. Le prototype
visuel doit commencer tôt sur un petit corpus représentatif, avant de figer
le moteur de rendu. Les chantiers 1 et 2 peuvent apporter une amélioration
rapide sans attendre ce moteur. Aucun délai de livraison n'est fixé ici.

## 3. Voir des images dans un terminal : oui, sous conditions

Le protocole graphique Kitty permet d'afficher des images, de choisir leur
position et de les redimensionner. Il faut détecter les capacités du terminal,
et tester le transport utilisé, notamment sous SSH ou avec un multiplexeur.
[Spécification Kitty](https://sw.kovidgoyal.net/kitty/graphics-protocol/).

iTerm2 documente son propre protocole d'images et le support du protocole Kitty.
C'est une option possible sur macOS. Le choix d'un terminal compatible est une
condition du rendu fidèle, distincte de la puissance CPU/GPU de la machine.
[Documentation iTerm2](https://iterm2.com/documentation-images.html).

Chafa propose des rendus Kitty, iTerm2, Sixel et des mosaïques Unicode.
Une mosaïque constitue un recours de compatibilité, mais ne suffit pas pour
lire de petites légendes scientifiques ou une formule complexe.
[Documentation Chafa](https://hpjansson.org/chafa/).

**Proposition :** un mode d'affichage automatique détectant le protocole,
avec sélection manuelle possible. Afficher clairement une incompatibilité au
lieu de prétendre restituer fidèlement une figure en caractères approximatifs.
Les images doivent rester agrandissables dans le terminal, avec déplacement
dans l'image et retour au passage exact.

Le rendu actuel avec `curses` ne gère pas encore cette couche graphique. Il
faudra coordonner l'effacement du texte, les placements d'images, le changement
de taille, la fermeture de vues et le tampon alternatif. Le choix entre une
extension du moteur actuel et un autre moteur TUI sera décidé après prototype,
sans réécriture générale préalable imposée.

## 4. Préparer le document une fois, le lire plusieurs fois

Le texte issu de `pdftotext` reste utile comme solution légère, mais ne peut
plus constituer la représentation unique d'un document complexe.

Représentation proposée : une suite de blocs typés comprenant texte, titre,
liste, code, image, graphique, tableau, formule et référence. Chaque bloc garde
un identifiant, l'ordre de lecture et sa provenance : page et rectangle pour
un PDF, emplacement dans le source pour un Markdown.

Conserver simultanément :

- Le contenu structuré utile à la recherche, à la voix et aux questions.
- Un rendu visuel fidèle des objets qui peuvent être mal extraits.
- Les liens entre le texte, la légende, les appels de figures et les sources.
- La version du document, de l'extracteur et des paramètres de traitement.

Pour les PDF, distinguer images intégrées et dessins vectoriels : un graphe
n'est pas nécessairement une image récupérable par extraction. PyMuPDF expose
le rendu des pages et de zones, les images et les dessins ; il constitue une
piste à évaluer, y compris ses conditions de licence avant intégration.
[API PyMuPDF](https://pymupdf.readthedocs.io/en/latest/page.html).

Docling constitue une autre piste pour obtenir une représentation structurée
de documents. Son adéquation aux ouvrages réels devra être comparée à d'autres
extracteurs sur notre corpus, sans présumer une extraction parfaite.
[Projet Docling](https://github.com/docling-project/docling).

Le cache doit être réutilisable, exportable et invalidé selon le contenu et les
versions de traitement. Le prétraitement peut s'effectuer sur la machine la
plus adaptée, puis le paquet préparé être transféré à l'autre. Le lecteur doit
rester réactif pendant une préparation en tâche de fond. Les annotations et
cycles de lecture restent distincts de ce cache régénérable.

## 5. Traitement des contenus complexes

| Objet | Affichage principal proposé | Accès complémentaire |
| --- | --- | --- |
| Image Markdown | Image locale référencée, avec légende et texte alternatif | Agrandissement dans le terminal |
| Figure ou graphe PDF | Rendu de la zone source, légende associée | Zoom et consultation de la page complète |
| Tableau simple | Grille lisible avec en-têtes | Défilement horizontal et vue par ligne |
| Tableau complexe | Rendu fidèle, avec extraction structurée si exploitable | Détail des cellules et retour au visuel |
| Formule Markdown | Rendu graphique de l'expression mathématique | Source LaTeX et explication facultative |
| Formule PDF | Zone source fidèle ; expression extraite si possible | Zoom et vérification de l'extraction |
| Graphe Markdown déclaré en code | Rendu par un moteur adapté au langage reconnu | Source du graphe, sinon signalement explicite |

Les cellules fusionnées, unités, exposants, notes, signes et légendes sont des
informations à conserver. Une transcription ou une description LLM complète
le visuel ; elle ne le remplace pas silencieusement. Une extraction incertaine
doit rester vérifiable dans la zone source, sans devoir lancer un autre lecteur.

Les tableaux, formules et figures doivent être des blocs consultables sans
chronomètre imposé. Suspendre l'avance automatique lors de leur inspection et
laisser l'utilisateur confirmer la suite. Leur durée de lecture ne se déduit
pas correctement d'un simple nombre de mots.

## 6. Avancer de 1 %, 0,1 % ou 0,01 %

**Ambiguïté à résoudre :** pourcentage de document affiché par passage, saut de
navigation, ou les deux. Cette demande n'est pas assimilée à une vitesse :

| Réglage | Question à laquelle il répond |
| --- | --- |
| Taille d'un passage | Quelle quantité afficher à chaque étape ? |
| Pas de navigation | De combien avancer ou reculer sur demande ? |
| Vitesse automatique | Combien de temps laisser avant d'avancer ? |

Exemple sur 100 000 mots : 1 % correspond à 1 000 mots, 0,1 % à 100 mots et
0,01 % à 10 mots. Une fenêtre ne pouvant pas contenir un tel passage doit le
présenter sur plusieurs écrans, sans masquer ni sauter le reste.

Le texte courant pourrait utiliser un pourcentage des mots, avec minimum d'une
unité et rapprochement d'une limite de phrase. Les objets complexes resteraient
indivisibles. Il faut définir explicitement le dénominateur pour un document
mêlant texte et objets ; il ne sera pas présenté comme une part du temps ou de
la difficulté. La progression actuelle repose sur des caractères : elle ne
doit pas être changée silencieusement.

Si ces valeurs désignent des variations de vitesse, les distinguer comme une
troisième option éventuelle. Une précision numérique de 0,01 % ne garantit
aucune précision équivalente du rythme réel. Les formules demandent surtout
une pause et un contrôle manuel du passage.

## 7. Colonne d'accompagnement et LLM

Disposition proposée sur fenêtre suffisamment large : environ deux tiers pour
le document et un tiers pour l'accompagnement. Ce rapport est réglable. Sur
petite fenêtre, utiliser un panneau basculable plutôt que comprimer le texte.
Le mode ZEN masque entièrement cette colonne.

Ordre de divulgation proposé : contexte court, indice ou question, tentative
personnelle, puis explication ou résumé sur demande. Les QCM révèlent leur
correction après réponse, avec justification et passage source. Les mots à
retenir sont suggérés en petit nombre et validés par le lecteur.

Prévoir aussi les références, définitions et liens entre idées. Un résumé
complet ne doit pas apparaître systématiquement avant la réflexion. Toute
production est distinguée du texte de l'auteur et rattachée à un passage.
Ne pas inventer de références externes : les liens proposés doivent être
vérifiables et leur consultation distincte du document original.

Prévoir des adaptateurs séparés pour un modèle local et une API payante. Ollama
documente des sorties structurées, utilisables aussi avec certains modèles de
vision : c'est une piste pour les questions et descriptions, pas une garantie
d'exactitude pédagogique. [Documentation Ollama](https://registry.ollama.com/blog/structured-outputs).

La génération doit être asynchrone et ses résultats mis en cache. Une réponse
tardive ne doit pas s'afficher comme si elle concernait le nouveau passage.
Prévoir annulation, nouvelle tentative et erreurs sans bloquer la lecture.
Le contexte effectivement transmis, le fournisseur et les dépenses doivent
être visibles dans les réglages ; aucun service payant n'est encore appelé.

## 8. Relectures complètes et historique

Introduire un **cycle de lecture**, distinct d'une ouverture du programme.
Un cycle possède une position, une date de début, un temps cumulé et un état.

Règle demandée : un seul cycle en cours par document. Fermer puis rouvrir le
lecteur reprend ce cycle. Une nouvelle lecture ne commence qu'après la
validation de fin du cycle précédent. Revenir au début pendant un cycle est
une navigation interne, et ne crée pas une relecture supplémentaire.

Le raccourci `g` et l'option `--restart` doivent respecter cette distinction.
La fin d'un document rend une action « commencer la prochaine lecture »
disponible, sans démarrage automatique. Un saut à la fin ne constitue pas à
lui seul une validation de lecture complète. Cette règle de suivi ne prétend
pas prouver que chaque passage a été compris.

Conserver deux compteurs non ambigus :

- **Lectures terminées** : tous les cycles achevés, y compris le premier.
- **Relectures terminées** : lectures terminées moins une, avec minimum zéro.

Exemple : après une première lecture achevée, afficher « 1 lecture terminée,
0 relecture terminée ». Pendant le cycle suivant, afficher « Lecture 2 en
cours ». À sa fin : « 2 lectures terminées, 1 relecture terminée ».

Garder le temps par cycle et le temps total du document. Les durées déjà
enregistrées avant cette fonction restent identifiées comme cumul historique,
sans inventer leur répartition. De même, ne pas fabriquer plusieurs cycles à
partir d'une ancienne position ou de sauvegardes répétées. La migration devra
prévoir le cas d'un document déjà à 100 %.

Un changement de contenu doit produire une version identifiable et conserver
l'historique, avec une décision explicite de reprise ou de nouvelle version.
Le déplacement d'un fichier ne doit pas fusionner deux lectures par simple
égalité d'empreinte ; l'identité stable prévue dans le précédent rapport
devient importante pour ce chantier.

## 9. Mode ZEN

Un basculement réversible masque en-tête, citation, pourcentage, compteurs,
raccourcis permanents et colonne LLM. Le document reste centré, avec son confort
de lecture réglable. Les tableaux, images et formules nécessaires restent
consultables : ZEN signifie moins d'interface, pas moins de contenu.

Les commandes de pause, reprise, retour, aide et sortie restent disponibles.
L'aide apparaît temporairement et revient au même état. La position et le
temps continuent à être sauvegardés selon les règles actuelles ; les pauses
explicites et l'aide restent exclues du comptage. Aucun enrichissement ne doit
apparaître spontanément en ZEN.

## 10. Voix de lecture : deuxième temps

Commencer par une voix française, la pause, la reprise, le choix de vitesse et
le retour à un passage. La voix doit suivre les blocs du document structuré.
Sur macOS, la commande système `say` fournit déjà synthèse vocale et réglage de
débit ; ce comportement a été vérifié dans le manuel local `man say`.
Le moteur pour l'autre machine sera choisi selon son système et sa configuration.

Une voix plus naturelle, locale ou payante, pourra utiliser un adaptateur
supplémentaire avec cache audio. L'affichage doit suivre la lecture effective
de l'audio, pas un minuteur indépendant. Un premier alignement au bloc est
plus simple qu'une promesse de surlignage précis mot à mot.

Définir séparément la prononciation des formules, le parcours des tableaux,
la lecture des légendes et celle des références. Les descriptions d'images
générées sont signalées comme telles. Le temps consacré n'est compté qu'une
fois lorsque voix et texte sont actifs ensemble. Distinguer progression de
lecture et progression de génération d'un fichier audio.

## 11. Prototypes et critères de validation

Constituer un corpus avec images Markdown locales, graphique vectoriel PDF,
document scanné, mise en page multicolonne, formule avec indices et exposants,
tableau à cellules fusionnées et document long. Conserver les fichiers de test
dont l'utilisation est autorisée et les résultats attendus.

Vérifier le même contenu sur les deux machines : qualité d'extraction, ordre,
absence de perte d'objets, zoom lisible, mise en cache et reprise. Mesurer la
durée de préparation, la mémoire et la fluidité ; sélectionner ensuite les
modèles et profils de traitement. Les sorties structurées doivent toujours
permettre de retrouver le contenu source.

Tester aussi les petites fenêtres, les redimensionnements, la disparition des
images à la fermeture d'une vue, le panneau LLM lent ou indisponible, la pause
audio, le passage en ZEN et les migrations de mémoire. Les relectures doivent
avoir des tests dédiés empêchant un nouveau cycle avant la fin du précédent.

Les commandes disponibles de la première livraison sont documentées dans le
README. Les autres options et raccourcis seront définis à leur implémentation.
