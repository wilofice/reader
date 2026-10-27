# Reader — lecture dans le terminal

Lecteur de texte, Markdown en aperçu et PDF pour macOS et les terminaux Unix, avec
reprise automatique et barre de progression. Python **3.10 ou supérieur** suffit
pour le texte. Pour les PDF, installez Poppler : `brew install poppler`.
L'aperçu visuel facultatif utilise aussi Chafa : `brew install chafa`.

## Installer sur un autre Mac

Depuis le dépôt cloné, installez les dépendances avec une seule commande :

```sh
./install.sh
```

Le script vérifie Python **3.10+** avec `curses` et SQLite, Poppler (`pdftotext`
et `pdftoppm`) et Chafa. Il installe les éléments manquants via Homebrew et
ne lance aucune installation si tout fonctionne déjà. Si Homebrew est absent,
il lance son [installateur officiel](https://docs.brew.sh/Installation), qui peut
demander confirmation, les outils de développement Apple et un mot de passe
administrateur. Une connexion Internet est nécessaire pour installer.

Pour vérifier seulement, sans installation ni accès réseau :

```sh
./install.sh --check
```

Cette vérification utilise le `PATH` du terminal courant et renvoie un code
non nul si une dépendance manque. Le script ne modifie ni le profil du shell,
ni les documents, ni la progression. S'il trouve ou installe Homebrew hors de
votre `PATH`, il affiche une ligne `export PATH=...` à exécuter dans ce terminal.
Suivez les indications de Homebrew pour rendre ce réglage permanent si besoin.
Les dépendances indirectes installées ou mises à jour sont gérées par Homebrew.
iTerm2, GitHub CLI et les modèles LLM ne font pas partie des dépendances installées.

### Premier clonage

Sur un MacBook Air Apple Silicon ou Intel, avec Homebrew disponible :

```sh
brew install gh
gh auth login
gh repo clone wilofice/reader
cd reader
git switch codex/next-iteration
./install.sh
./reader README.md
```

La commande d'installation est actuellement sur la branche `codex/next-iteration`.
Le dépôt est privé : authentifiez-vous avec un compte qui y a accès. Si Git et
votre accès GitHub sont déjà configurés, vous pouvez aussi utiliser
`git clone git@github.com:wilofice/reader.git`. Poppler est facultatif si vous ne
lisez pas de PDF. Aucune installation `pip`, compilation ou configuration de
base de données n'est nécessaire. Le droit d'exécution de `reader` est conservé
par Git. Utilisez une fenêtre Terminal ou iTerm avec une police Unicode.

Pour les mises à jour, lancez `git pull --ff-only` dans le dossier du projet.
Le lecteur fonctionne localement, sans connexion réseau après installation.

La mémoire de lecture reste propre à chaque machine : **cloner le dépôt ne
transfère pas les progressions**. Pour les récupérer, fermez les lecteurs sur
les deux machines, copiez la base `reading.sqlite3` depuis son emplacement
indiqué plus bas, puis placez-la au même emplacement sur l'autre Mac. Les
documents doivent garder les mêmes chemins absolus et le même texte pour
retrouver leurs positions ; sinon une nouvelle lecture commencera. Copier une
base existante remplace l'historique de destination : gardez-en une sauvegarde.

## Démarrer

Depuis ce dossier :

```sh
./reader "J'ai besoin de reprendre le travail que j'ai comme.md"
./reader "document.pdf"
```

Rouvrez le même fichier avec la même commande pour retrouver votre passage.
Pour rendre la commande accessible depuis tous les dossiers, vous pouvez créer
un lien vers cet exécutable dans un répertoire de votre `PATH`.

## Modes de lecture

### Lecture ZEN

```sh
./reader "notes.md" -z
./reader "notes.md" -z -m w -s 80 -a -w 240
```

La touche `z` active ou quitte le mode ZEN : seul le contenu reste visible,
sans en-tête, citation, barre ni compteurs. La position et le temps continuent
à être sauvegardés. Les commandes habituelles restent actives ; `?` affiche
temporairement l'aide et `i` la référence du passage, puis Échap revient à la
lecture. L'aide et la consultation de référence suspendent le défilement et le
comptage du temps. Quitter ZEN conserve la position, avec adaptation du passage
à la nouvelle surface d'affichage.

### Choisir le passage et le rythme

Pour se concentrer sur un passage isolé, utilisez le **mode mots avec avance
automatique** :

```sh
./reader "notes.txt" -m w -s 80 -a -w 240
```

Cette commande affiche jusqu'à **80 mots à la fois**, puis remplace le passage
par le suivant après environ **20 secondes** à 240 mots/minute.

| Mode | Texte affiché | Avance |
| --- | --- | --- |
| `-m l` (`lines`) | Un passage de lignes ; 15 par défaut | Passage suivant avec `n`, ou automatiquement avec `-a` |
| `-m w` (`words`) | Un lot de mots ; 120 par défaut | Lot suivant avec `n`, ou automatiquement avec `-a` |
| `-m s` (`scroll`) | Une fenêtre de lignes ; 15 par défaut | Automatique dès le démarrage, une ligne à la fois |

Le mode `s` conserve donc du contexte à l'écran : il décale une fenêtre de texte.
Le mode `w -a` renouvelle le passage entier et convient mieux pour isoler ce
qu'on lit. Pour isoler une seule ligne en automatique, utilisez `-m s -s 1`.

```sh
# Une seule ligne à la fois, avec avance manuelle
./reader "notes.txt" -m l -s 1

# Passages de 10 lignes, avec avance manuelle
./reader "notes.txt" -m l -s 10

# Lots de 80 mots, avec avance manuelle
./reader "notes.txt" -m w -s 80

# Une seule ligne à la fois, avec avance automatique
./reader "notes.txt" -m s -s 1 -w 240

# Fenêtre de 15 lignes défilant une ligne à la fois
./reader "notes.txt" -m s -w 180
```

**`-s` règle la quantité de texte affichée**, en lignes pour `l` et `s`, en mots
pour `w`. Les lignes longues sont repliées selon la largeur du terminal. Les
passages tiennent dans la fenêtre : le nombre demandé est un maximum, et un
lot de 80 mots peut être plus court si l'écran ne peut pas tout afficher.

Pendant la lecture, `j` réduit le passage et `k` l'augmente : d'une ligne en
mode `l` ou `s`, de dix mots en mode `w`, avec un minimum de un. La valeur
apparaît sous le titre. La position courante reste inchangée ; le délai
automatique est recalculé pour le nouveau passage. Ces réglages valent pour la
session ; utilisez `-s` pour choisir la taille au démarrage.

## Régler la vitesse automatique

**`-w` règle la vitesse dans tous les modes automatiques**, y compris `-m w -a`.
Sans `-w`, la vitesse est de **200 mots/minute**. Dans les modes manuels `l`
et `w`, le lecteur attend votre action : `-w` seul n'active pas l'automatique.

La lettre `w` après `-m` choisit le **mode mots** ; l'option `-w 240` choisit
la **vitesse**. Par exemple :

```sh
# Même taille de passage, rythme plus lent : environ 40 secondes pour 80 mots
./reader "notes.txt" -m w -s 80 -a -w 120

# Même taille de passage, rythme plus rapide : environ 20 secondes pour 80 mots
./reader "notes.txt" -m w -s 80 -a -w 240
```

Pour raisonner en mots par seconde, multipliez par 60 :

| Rythme souhaité | Valeur à passer |
| --- | --- |
| 1 mot/seconde | `-w 60` |
| 2 mots/seconde | `-w 120` |
| 3 mots/seconde | `-w 180` |
| 4 mots/seconde | `-w 240` |
| 5 mots/seconde | `-w 300` |

Le délai vaut `nombre de mots × 60 / vitesse`. En mode `l -a` ou `w -a`, il
dépend du passage réellement affiché ; en mode `s`, de la première ligne qui
va quitter la fenêtre. Le rythme reste approximatif, avec un délai minimal
de 0,25 seconde. Une ligne ou un lot de plusieurs mots n'est donc pas remplacé
à chaque mot. Pendant la lecture, `+` et `-` ajustent la vitesse, et `a` active
ou suspend l'avance automatique.

## Options courtes et longues

Toutes les anciennes formes restent acceptées. Par exemple,
`--mode words --size 80 --auto --wpm 240` équivaut à `-m w -s 80 -a -w 240`.

| Option courte | Option longue | Fonction |
| --- | --- | --- |
| `-m` | `--mode` | Mode de lecture |
| `-s` | `--size` | Taille du passage |
| `-a` | `--auto` | Avance automatique |
| `-w` | `--wpm` | Vitesse en mots/minute |
| `-r` | `--restart` | Reprendre au début |
| `-e` | `--encoding` | Encodage du texte |
| `-R` | `--raw` | Source Markdown |
| `-S` | `--state` | Chemin de la base |
| `-H` | `--history` | Historique |
| `-p` | `--status` | Progression en JSON |
| `-h` | `--help` | Aide |
| `-z` | `--zen` | Démarrer en lecture épurée |
| — | `--graphics` | Format de l'aperçu PDF via Chafa |
| — | `--preview` | Mode d'aperçu PDF : `auto`, `iterm2` ou `quicklook` (alias de `--graphics`) |
| — | `--new-reading` | Commencer le cycle suivant après la fin du précédent |
| — | `--readings` | Afficher les cycles du document et leurs durées |

## Touches

| Touche | Action |
| --- | --- |
| `n`, Entrée, flèche droite/bas | Avancer |
| `b`, flèche gauche/haut | Revenir et suspendre l'avance automatique |
| Espace | Pause / reprise en automatique ; avancer en manuel, ou reprendre si en pause |
| `p` | Mettre en pause / reprendre dans tous les modes, y compris le comptage du temps |
| `a` | Activer ou suspendre l'automatique |
| `+`, `-` | Modifier la vitesse de 25 mots/minute |
| `j`, `k` | Réduire / augmenter le nombre de lignes ou de mots affichés |
| `?` | Ouvrir / fermer l'aide, avec suspension de l'avance automatique |
| `g` | Revenir au début |
| `N` (majuscule) | Commencer une nouvelle lecture après avoir terminé |
| `z` | Activer / quitter ZEN |
| `i` | Consulter la référence de page PDF ou de ligne source |
| `v` | Ouvrir la page PDF comme image dans le terminal |
| `q`, Échap | Sauvegarder et quitter |

Le retour retrouve les passages visités pendant la session. Après réouverture,
il recalcule le passage précédent selon la taille actuelle du terminal.
Les touches `[` et `]` (crochets ouvrant et fermant) restent aussi acceptées
pour réduire et augmenter le passage. Elles désignent des touches à presser,
pas des éléments décoratifs de l'interface.

Dans l'aide, les flèches haut/bas permettent de défiler si nécessaire ; `?` ou
Échap revient à la lecture, et `q` quitte le lecteur. Si l'avance automatique
était active, elle reprend avec un nouveau délai complet à la fermeture de l'aide.

## Temps consacré et estimation du temps restant

Une ligne au-dessus de la barre de progression affiche le **temps cumulé sur ce
document** et le **temps restant estimé**, par exemple :

```text
Temps cumulé : 12:34 · Reste ≈ 08:20 auto
```

Les durées sont au format `minutes:secondes`, puis `heures:minutes:secondes`
au-delà d'une heure. Le compteur se cumule entre les ouvertures du même fichier.
Il compte le temps pendant lequel le texte est disponible à la lecture, en
manuel comme en automatique. Il s'arrête pendant une pause, dans l'aide, quand
la fenêtre est trop petite pour afficher le texte et après la fin du document.
Les longues suspensions du processus entre deux mises à jour sont ignorées.

**Appuyez sur `p` lorsque vous interrompez votre lecture**, même en manuel.
Le programme ne sait pas si vous regardez encore le terminal : une fenêtre
laissée ouverte sans pause peut donc continuer à compter. Ce compteur est une
estimation du temps consacré, sans mesure de l'attention ni de la compréhension.
Espace reprend une lecture en pause ; `n` avance et reprend aussi la lecture.

| Mode | Calcul de l'estimation |
| --- | --- |
| Automatique (`-a` ou `-m s`) | Nombre de mots restant à afficher, divisé par la vitesse `-w` ; le délai du passage courant diminue pendant son affichage |
| Manuel | Rythme observé sur les passages avancés avec `n`, Entrée, les flèches ou Espace, et le temps actif passé sur ces passages |
| Manuel sans observations suffisantes | Affichage « calibrage », sans durée inventée à partir de la vitesse automatique |

En manuel, le calibrage demande au moins **20 mots et 10 secondes cumulés sur
des passages terminés**. Le rythme observé apparaît alors dans l'en-tête et
sert à estimer la durée restante. Le temps passé sur le passage encore ouvert
ne devient un échantillon qu'à son avancement : l'estimation manuelle est donc
mise à jour par passage, et non par un compte à rebours artificiel.

Les passages sautés en moins de 0,2 seconde ne servent pas au calibrage.
Un retour en arrière, un changement de taille ou de fenêtre, ou un changement
entre manuel et automatique écarte l'échantillon en cours pour éviter de
mélanger des mesures incompatibles. Les échantillons suivants peuvent de nouveau
être utilisés. Le temps total consacré reste compté même sans échantillon valide.
Une navigation rapide ou une interruption non déclarée peut encore fausser le
rythme observé : la durée affichée reste approximative.

Les mots sont comptés dans le texte effectivement proposé à la lecture, donc
dans l'aperçu pour un fichier Markdown. Les futures pauses, les relectures et
les changements de vitesse ne peuvent pas être prédits. Le délai minimal de
0,25 seconde et les passages sans mots peuvent aussi allonger l'automatique,
particulièrement à grande vitesse ou avec des passages très courts.

Le temps est sauvegardé à chaque déplacement, à la fermeture normale et environ
toutes les cinq secondes. Une fermeture forcée peut perdre les dernières
secondes non sauvegardées. Les anciennes bases sont mises à niveau en conservant
les positions ; les temps commencent à zéro car les anciennes lectures ne
contenaient aucune mesure de durée.

`--restart` remet la position au début mais conserve le temps cumulé. Une
modification du texte conserve aussi ce cumul, tout en remettant la position
et le calibrage à zéro. Un changement entre source Markdown et aperçu remet
le calibrage à zéro, sans effacer le temps consacré. Le cumul reste attaché au
chemin du document, avec les limites de déplacement décrites plus bas.

```sh
# Voir le temps cumulé dans l'historique
./reader -H

# Statistiques et estimation fondée sur les observations manuelles
./reader "notes.txt" -p

# Estimation fondée sur un rythme automatique de 240 mots/minute
./reader "notes.txt" -p -a -w 240
```

Le JSON de `-p` contient `reading_seconds`, `remaining_words`,
`estimated_remaining_seconds`, `estimated_wpm` et `estimate_basis`. Ce dernier
vaut `configured_speed` en automatique, `observed_manual_speed` après calibrage,
`calibrating` avant calibrage, ou `complete` à la fin. Une estimation indisponible
vaut `null`. Les statistiques ne font pas avancer la lecture.

## Lisibilité et aperçu Markdown

Le contenu est présenté dans une colonne centrée, limitée à 76 colonnes de
largeur, avec une séparation sous l'en-tête et une barre de progression sur
presque toute la fenêtre. Le mode, la vitesse et l'état de lecture sont indiqués
en haut. L'aide complète est accessible avec `?` pour garder le bas de l'écran
discret. Les petits terminaux utilisent une présentation compacte.

La devise « Lire, c’est conquérir le monde. » accompagne discrètement l'en-tête.
Choisie pour Reader, elle n'est attribuée à aucun auteur. Elle apparaît lorsque
l'en-tête dispose d'assez de place, sans empiéter sur le contenu ni les
informations de lecture.

Une couleur cyan souligne les indications et la progression, sans changer la
couleur de fond du terminal. Pour désactiver les couleurs :

```sh
NO_COLOR=1 ./reader "notes.txt"
```

La **taille des caractères** se règle dans votre application de terminal :
utilisez son menu de zoom ou ses préférences de police. Sur Terminal et iTerm
pour Mac, le raccourci habituel pour agrandir est `⌘ +`. Le lecteur s'adapte
à la nouvelle largeur sans changer votre position. `--size` règle la quantité
de texte, pas la police.

Les fichiers `.md`, `.markdown` et `.mdown` s'ouvrent automatiquement en aperçu
textuel : titres sans `#`, texte sans délimiteurs de gras/italique, libellés des
liens, listes avec puces et blocs de code conservés. Les références de notes,
leurs définitions et le HTML décoratif ou explicitement masqué sont retirés.
Les images ne sont pas affichées ; leur texte alternatif est conservé s'il existe.
Les tableaux restent textuels. Ce rendu couvre le Markdown courant, sans
reproduire toute la mise en page d'un navigateur ni les extensions complexes.

Pour consulter exceptionnellement le source :

```sh
./reader "notes.md" --raw
```

Les positions restent liées au texte source pour conserver les lectures déjà
mémorisées. Lors d'un changement entre source et aperçu, la reprise dans une
ligne transformée peut être légèrement décalée.

## Mémoire et progression

### Lectures complètes et relectures

Une ouverture du programme n'est pas une nouvelle lecture. Un **cycle** reste
en cours entre les sessions jusqu'à la fin du document. Avancer après le dernier
passage (ou attendre son délai en automatique) termine le cycle une seule fois.
La touche `N`, à la fin, commence le suivant. Elle est refusée avant la fin.

```sh
./reader "notes.md" --readings
./reader "notes.md" --new-reading
```

`--new-reading` nécessite un terminal interactif et un cycle précédent terminé.
Le nouveau cycle repart au début ; le temps total du document est conservé et
une nouvelle durée de cycle commence. Après deux cycles terminés, le bilan
compte **2 lectures terminées, dont 1 relecture**. Le numéro du cycle est visible
dans l'en-tête ; `i`, `--readings` et `-p` permettent de consulter le bilan.

`g` et `--restart` reviennent au début **du même cycle** : ils ne créent pas de
relecture et n'effacent pas les cycles terminés. Revoir des passages d'un cycle
déjà terminé n'augmente pas son compteur ; ce temps supplémentaire reste dans
le cumul général, sans modifier sa durée figée à la fin. Les cycles sont
distingués par chemin et empreinte du texte ; les compteurs concernent la version
actuelle du texte. Les anciennes versions restent conservées dans la base.

La migration conserve les positions et durées existantes. Le temps antérieur au
suivi des cycles n'est pas attribué artificiellement à une lecture. Une ancienne
position à 100 % est importée comme une fin historique unique, sans dates de
début/fin inventées. Le JSON de `-p` expose `reading_number`,
`completed_readings` et `completed_rereadings`.

### Pages PDF et aperçu visuel des contenus complexes

Pour les PDF, Reader conserve maintenant les limites des pages transmises par
`pdftotext`. Le bas de l'écran indique la page physique ou l'intervalle de pages
du passage affiché. La touche `i` fournit la référence et le chemin du document,
sans perdre la position. Dans un Markdown ou un texte, elle indique la ligne
du source, y compris en aperçu Markdown.

**Ce prototype affiche la page originale entière, sans reconnaissance des objets.**
La touche `v` rend sa mise en page avec Poppler, puis l'affiche dans le mode
adapté : figures, tableaux et formules restent à leur emplacement.
Si le passage couvre plusieurs pages, l'aperçu commence à la première ; vous
pouvez consulter la suivante sans avancer votre position de lecture.

```sh
brew install poppler chafa
./reader "document.pdf"
```

Le mode par défaut `--preview auto` identifie le terminal à l'exécution à partir
de ses variables d'environnement, notamment `TERM_PROGRAM` :

| Environnement reconnu | Aperçu choisi |
| --- | --- |
| iTerm2 (`iTerm.app`) | Image intégrée centrée horizontalement, via Chafa |
| Terminal.app (`Apple_Terminal`), sur macOS local | Fenêtre Quick Look avec l'image de la page courante |
| Kitty, Ghostty ou WezTerm reconnus | Image intégrée via le protocole Kitty |
| Terminal inconnu ou environnement masqué par un multiplexeur | Symboles, avec avertissement de qualité |

Ce mécanisme ne garantit pas d'identifier tous les terminaux : les variables
peuvent être absentes ou héritées, particulièrement à distance. L'ouverture
automatique de Quick Look est désactivée en contexte SSH et sous multiplexeur.
Vous pouvez toujours forcer votre choix :

```sh
./reader "document.pdf" --preview iterm2
./reader "document.pdf" --preview quicklook
```

Le mode Quick Look nécessite macOS, Poppler et l'outil système `qlmanage`, sans
Chafa. Il ouvre **l'image de la page concernée**, pas le PDF à parcourir de
nouveau. Fermez la fenêtre pour revenir au même passage ; depuis le terminal,
`v`, Échap ou `q` ferment aussi l'aperçu lancé par Reader. Quick Look gère ses
propres commandes graphiques : les raccourcis du tableau ci-dessous concernent
uniquement l'aperçu intégré. Pour consulter une autre page en Quick Look,
revenez au lecteur et naviguez dans le texte. Le temps d'ouverture est compté
comme temps d'inspection ; fermez la fenêtre si vous interrompez la consultation.

**Dans l'aperçu intégré iTerm2 ou les autres formats Chafa :**

| Touche dans l'aperçu | Action |
| --- | --- |
| `+`, `-` | Zoomer / dézoomer, jusqu'à ×4 |
| Flèches | Déplacer la zone agrandie |
| `0` | Revenir à la page entière |
| `n`, `b` | Page suivante / précédente, sans modifier la lecture |
| `p` | Suspendre / reprendre le compteur d'inspection |
| `v`, Échap ou `q` | Fermer l'aperçu et retrouver le passage exact |

L'automatique est suspendu pendant l'aperçu et reprend avec un nouveau délai
à sa fermeture. Le temps d'inspection est ajouté au temps consacré au document,
y compris si la lecture du texte était en pause avant l'ouverture ; `p` dans
l'aperçu permet de l'interrompre. Le temps de calcul et de préparation de l'image
est exclu. L'inspection ne calibre pas le rythme de lecture du texte,
ne termine aucun cycle et ne fait pas progresser le pourcentage.

Sur un terminal reconnu comme compatible, le mode automatique sélectionne un
format d'image. Sinon il utilise explicitement le mode **symboles**, approximation
qui peut rendre les petits détails illisibles. La sélection repose sur les
variables d'environnement, sans interrogation du terminal ; sous un multiplexeur,
elle reste conservative. Un terminal compatible et correctement configuré est
nécessaire pour voir les images en pixels. Les formats pris en charge sont
décrits dans le [manuel de Chafa](https://hpjansson.org/chafa/man/).

Pour choisir le protocole explicitement si la détection ne convient pas :

```sh
./reader "document.pdf" --graphics iterm
./reader "document.pdf" --graphics kitty
./reader "document.pdf" --graphics sixels
./reader "document.pdf" --graphics symbols
```

Le format graphique forcé doit être pris en charge par le terminal. Les transferts via
SSH et les multiplexeurs demandent une vérification de la configuration.
Les protocoles Kitty et iTerm ont été testés à l'encodage ; leur affichage réel
dans chaque terminal doit encore être validé sur les machines d'utilisation.

La première image de chaque page est conservée sous
`~/.cache/reader/pdf/`, ou `$XDG_CACHE_HOME/reader/pdf/`. Le cache utilise
l'empreinte du **fichier PDF complet**, incluant ses images ; les recadrages de
zoom sont temporaires. Il est régénérable, sans lien avec la base de progression,
et peut être supprimé après fermeture du lecteur. Un rendu ou un appel à Chafa
dépassant 30 secondes retourne une erreur et laisse la lecture en pause.
Ce prototype prépare la page de manière synchrone : une touche de retour est
traitée à la fin de la préparation. Aucun OCR ni LLM n'est appelé.

La page indiquée localise le passage courant ; elle n'atteste pas qu'un objet
complexe s'y trouve. Le numéro physique commence à 1 et peut différer du numéro
imprimé dans le livre. Les pages sans texte entre deux pages restent comptées.
Les PDF entièrement scannés nécessitent toujours un OCR préalable.

`-p` expose `pdf_page` et `pdf_pages` pour un PDF, sinon `null`. Ces champs
concernent le début du passage sauvegardé, indépendamment de la taille de fenêtre.
Le rendu reste limité aux pages PDF : pas d'images Markdown ni de conversion
sémantique des tableaux ou formules pour le moment.

### Stockage et reprise

La position est enregistrée à chaque déplacement dans
`~/.local/state/reader/reading.sqlite3`, ou sous `$XDG_STATE_HOME/reader/`
si cette variable est définie. Aucun service ni connexion réseau n'est utilisé.
La base contient les chemins, empreintes et positions, sans copie du texte.

La barre mesure la proportion de caractères précédant le passage courant.
Quitter conserve le début de ce passage : vous pourrez le finir à la prochaine
session. Avancez après le dernier passage pour marquer **100 %** ; en automatique,
le lecteur attend son délai de lecture avant de terminer.

```sh
./reader --history
./reader "notes.txt" --status
./reader "notes.txt" --restart
./reader "notes.txt" --state "/chemin/memoire.sqlite3"
./reader "ancien.txt" --encoding latin-1
```

La mémoire identifie les documents par leur chemin absolu. Un fichier déplacé
est considéré comme nouveau ; un contenu modifié reprend au début pour éviter
une position incorrecte. Utilisez une seule session par document : la dernière
sauvegarde prévaut. Les PDF sont extraits avec `pdftotext -layout` ; leurs positions
concernent le texte extrait, pas les pages. Un PDF scanné nécessite un OCR préalable.

## Vérification

```sh
python3 -m unittest discover -s tests -v
```

Les tests vérifient les positions persistantes, les changements de documents,
le découpage sans perte, le rendu Markdown et l'extraction PDF simulée. Les tests
en pseudo-terminal vérifient les touches, le changement de taille, la reprise,
la pause pendant l'aide, l'affichage compact, le défilement, la fin de lecture
et la restauration du terminal. Ils couvrent aussi la migration des anciennes
bases, le temps cumulé, les pauses et les estimations automatiques et manuelles.
Un test extrait
aussi un vrai PDF si Poppler est disponible ; sinon ce test est ignoré.

## Recherche et évolutions proposées

La [feuille de route des documents enrichis](FEUILLE-DE-ROUTE.md) organise les
demandes de mode ZEN, relectures complètes, images, graphes, tableaux, formules,
pas de progression, colonne LLM et voix de lecture. Elle précise les priorités,
les dépendances et les limites des solutions envisagées. Le mode ZEN, les cycles
et un aperçu visuel des pages PDF sont désormais disponibles ; les images
Markdown et les autres enrichissements restent à développer.

Le [rapport sur la lecture assidue et l'apprentissage durable](RAPPORT-LECTURE-APPRENTISSAGE.md)
réunit les recherches consultées, leurs limites et les fonctions envisagées :
préférences mémorisées, journal de séances, notes, rappel actif, révisions espacées
et liens entre idées. Il décrit un ordre de développement et des critères
d'évaluation. Ces propositions ne sont pas encore implémentées.
