# Reader — lecture dans le terminal

Lecteur de texte, Markdown en aperçu et PDF pour macOS et les terminaux Unix, avec
reprise automatique et barre de progression. Python **3.10 ou supérieur** suffit
pour le texte. Pour les PDF, installez Poppler : `brew install poppler`.
L'aperçu visuel facultatif utilise aussi Chafa : `brew install chafa`.

Suivi : [état des fonctionnalités et priorités](ETAT-DES-FONCTIONNALITES.md) ·
[journal des évolutions](EVOLUTIONS.md) ·
[stratégie et catalogue de la bibliothèque de culture générale](STRATEGIE-BIBLIOTHEQUE-CULTURE.md).

## Lancer Reader sans indiquer de fichier

Reader utilise par convention le dossier personnel `~/Lectures`. Créez-le et
configurez-le une fois :

```sh
mkdir -p ~/Lectures
reader --folder ~/Lectures
```

Ensuite, une seule commande suffit :

```sh
reader
```

Reader parcourt ce dossier et ses sous-dossiers, repère les PDF et fichiers
Markdown qui ne figurent pas encore dans l'historique, puis ouvre le sélecteur
général. Les nouveautés portent l'état `nouveau` et sont classées avec les
documents récemment consultés. `↑`/`↓` choisissent et Entrée ouvre ; la reprise
fonctionne ensuite normalement. Le repérage reste léger : le texte d'un PDF
n'est extrait qu'au moment de sa première ouverture. Les fichiers et dossiers
cachés, les liens symboliques et les autres formats sont ignorés.

Ouvrir directement un PDF ou Markdown situé ailleurs crée aussi, dès la première
lecture interactive, une copie privée et atomique dans `~/Lectures` :

```sh
reader ~/Downloads/nouveau-rapport.pdf
```

Reader lit ensuite la copie durable et déplace vers elle toute progression déjà
connue. L'original peut donc être déplacé ou supprimé sans casser la reprise. Un
nom déjà utilisé avec un contenu différent reçoit un court suffixe d'empreinte ;
une copie identique n'est pas dupliquée. `--status` reste une consultation et ne
copie pas le fichier.

`-F` est l'alias court de `--folder`. La configuration est locale : exécutez-la
une fois sur chaque Mac, avec le chemin adapté à cette machine. La commande peut
être répétée sans danger : avec le même chemin, elle relance simplement le
parcours ; avec un autre chemin, elle remplace le dossier actif et sa file de
nouveautés non ouvertes. Elle ne supprime jamais l'historique ni les progressions
existantes. Un fichier supprimé avant sa première ouverture disparaît au prochain
parcours.

Reader mémorise actuellement **un seul dossier actif par machine**. La surveillance
simultanée de plusieurs dossiers (`--folder-add`, `--folder-list` et
`--folder-remove`) reste une amélioration possible, mais n'est pas nécessaire avec
le dossier unique `~/Lectures` retenu pour l'usage courant.

## Bibliothèque de culture générale

Ouvrez le catalogue terminal avec `./reader --catalog`. Les flèches déplacent
la sélection ; Entrée reprend un document présent, `d` télécharge un document
officiel disponible, et `a` affiche la commande pour rattacher un PDF personnel.
Hors terminal interactif, `--catalog` affiche la liste et son état.

```sh
./reader --catalog
./reader --download-library
./reader --download-book bis-aer-2026
./reader --open-book bis-aer-2026 -m w -s 80
./reader --attach-book the-world-haass ~/Downloads/the-world.pdf
./reader --open-book the-world-haass -m w -s 80
```

Les fiches initiales sont dans `reading_catalog.json`. Les PDF téléchargés sont
rangés dans `~/.local/share/reader/library/` (ou `$XDG_DATA_HOME/reader/library/`)
et ne sont pas ajoutés à Git. Les liens locaux et la progression utilisent la
base SQLite Reader ; copier la base **et** le dossier bibliothèque conserve
les téléchargements. Les fichiers rattachés ailleurs gardent un chemin absolu :
sur une autre machine, recopiez-les au même chemin ou rattachez-les à nouveau.
`--download-library` télécharge les sources officielles directement accessibles.
Les sources qui exigent un compte ou refusent l'automatisation restent visibles
dans le catalogue sans faire échouer l'installation. Reader ne contourne pas les
comptes des éditeurs et ne récupère pas les livres commerciaux.

Sept fichiers sont déjà téléchargés ici : manuel OpenStax de finance, rapports
BRI, GIEC, OCDE, Banque mondiale et PNUD, ainsi que l'article arXiv sur Transformer. Le téléchargement
du WEO du FMI a reçu une réponse HTTP 403 depuis cette machine ; son lien
officiel reste dans le catalogue. Le PDF complet de l'AIE demande un compte
gratuit. Les livres de Haass et Drucker restent à acheter, emprunter ou rattacher
depuis un fichier que vous avez obtenu légalement. Damodaran est une référence
payante possible pour une étape ultérieure, pas l'entrée finance du prototype.

## Lire un texte copié ou collé

Pour importer le presse-papiers et commencer la lecture :

```sh
./reader -c -n "Article sur la mémoire" -m w -s 80
```

Sans `-n`, Reader demande le nom. Sur macOS, le presse-papiers utilise `pbpaste`,
déjà fourni ; Linux utilise `wl-paste`, `xclip` ou `xsel` si disponible.
Pour coller vous-même dans le terminal, sans outil de presse-papiers :

```sh
./reader --paste -n "Mes notes"
```

Collez le contenu, puis appuyez sur Entrée et **Ctrl-D sur une ligne vide**
pour ouvrir le lecteur. Quittez normalement avec `q`. Pour retrouver le texte :

```sh
./reader --library
./reader --open "Mes notes" -m w -s 80
```

La reprise, les cycles et les mots quotidiens fonctionnent comme pour un fichier.
Le contenu est conservé en Markdown dans `texts/` à côté de la base SQLite
(`~/.local/state/reader/texts/` par défaut), et son nom est indexé dans cette base.
Le presse-papiers peut donc changer entre deux sessions. Un nom déjà utilisé
avec le même contenu reprend ce document ; un contenu différent exige un autre
nom. Les noms sont insensibles à la casse ASCII. Les textes restent locaux,
ne sont pas versionnés et ne sont pas synchronisés entre machines.
Avec `-S`, la bibliothèque est créée à côté de la base choisie.
Une sauvegarde doit conserver **la base et le dossier `texts/`** : copier la
base seule ne transporte pas les textes. Les chemins enregistrés sont absolus ;
une copie manuelle doit conserver leur emplacement pour que la reprise fonctionne.

Un flux peut aussi être sauvegardé sans interface :
`cat notes.md | ./reader --paste -n "Mes notes"`, puis `./reader --open "Mes notes"`.

## Voix de lecture — premier prototype

La voix est désactivée par défaut. **`t` ou `T` active/arrête la voix** ; Espace,
`p` et `P` suspendent/reprennent. Elle lit le passage affiché puis avance à la
fin réelle de l'audio. Elle se suspend pendant l'aide, l'aperçu des images ou
la perte de focus du terminal. En quittant au milieu d'un passage, la reprise
relit ce passage ; il n'y a pas encore de position audio mot à mot.

Essai immédiat sur macOS, sans modèle supplémentaire :

```sh
./reader "document.pdf" -m w -s 80 --tts say --speak
```

Pour choisir une voix macOS, listez-les avec `say -v '?'`, puis ajoutez
`--voice NOM`. Pour Phonon, installez et démarrez Ollama **0.40.9+**
compatible avec son API audio :

```sh
ollama --version
./reader "document.pdf" -m w -s 80 --tts ollama --speech-model phonon:40m-fr --speak
```

Pour préparer les modèles **avant d'ouvrir Reader**, lancez `./install.sh --models`.
Cette étape installe et démarre Ollama si nécessaire, puis précharge
`granite4:latest` et, sur Apple Silicon, `phonon:40m-fr` et `phonon:31m-en`.
Reader peut aussi télécharger à la demande un modèle absent. Il faut
une connexion Internet et assez d'espace disque durant la préparation. Les
modèles ne sont pas inclus dans Git.
Pour un livre ouvert avec `--open-book` ou depuis `--catalog`, Reader sélectionne
automatiquement `phonon:31m-en` lorsque sa fiche indique l'anglais et
`phonon:40m-fr` sinon. Un fichier ouvert directement conserve le français par
défaut, car il n'a pas de métadonnée de langue. `--speech-model NOM` force un
autre choix. `--status` indique le modèle retenu.
`--voice default` utilise la voix du modèle ; `ollama show NOM_DU_MODELE`
indique les voix disponibles. Reader ne met pas à jour les modèles déjà installés.
La variante française 40M est sous CC BY-NC 4.0 ; l'anglais 31M sous Apache 2.0.
Les paquets audio Ollama actuels nécessitent Apple Silicon.
[Modèles et licences](https://ollama.com/library/phonon).

Au tempo normal, macOS utilise son lecteur natif `afplay`, même si FFplay est
installé. FFplay est utilisé pour changer le tempo et pour les autres systèmes.
Pour modifier le tempo sans changer la hauteur de la voix :

```sh
brew install ffmpeg
./reader --open "Mes notes" --speak --audio-rate 1.2
```

Pendant la voix, `+`/`-` règlent le tempo entre ×0,5 et ×2 et relisent le passage
courant. Ce multiplicateur n'est pas une promesse de mots/minute. `-w` conserve
son rôle pour l'avance automatique silencieuse et règle le débit initial de
`say` ; l'API Phonon n'accepte pas de vitesse native.
[API audio Ollama](https://docs.ollama.com/capabilities/speech).

Ce prototype prépare **un passage à la fois**, dans un répertoire temporaire
supprimé à la fermeture ; il n'exporte pas de livre audio ni de cache durable.
La préparation n'est pas comptée comme de l'écoute. Une erreur met la lecture
en pause sans valider le passage. `a` revient à l'avance automatique silencieuse.
Le temps restant audio n'est pas encore estimé ; l'écran l'indique explicitement.
Les formules et tableaux sont lus comme du texte, sans interprétation spéciale.
La génération Phonon et la lecture native ont été vérifiées avec Ollama 0.40.13
sur cette machine : audio non silencieux, pause/reprise et fin de lecture
(test du lecteur à volume nul). Cela ne constitue pas une évaluation de la
qualité vocale ou de la fatigue à l'écoute. La synthèse macOS a aussi été vérifiée.
Si FFplay signale une bibliothèque Homebrew manquante, utilisez le tempo ×1,
ou réparez son installation avec `brew reinstall ffmpeg` pour les autres tempos.

## Accompagnement pédagogique — premier prototype local

Le modèle texte par défaut est `granite4:latest` et sera téléchargé au premier
usage du panneau si nécessaire. Vous pouvez en choisir un autre avec
`--llm-model NOM` :

```sh
./reader "document.pdf" --companion
```

Le premier appel à une aide (`1` à `5`) déclenche le téléchargement si le
modèle sélectionné n'est pas encore présent. Pour utiliser un autre modèle :
`./reader "document.pdf" --companion --llm-model NOM_DU_MODELE`.

`--companion` ouvre le panneau au démarrage ; **`e`** l'ouvre ou le ferme ensuite.
L'ouverture par `e` met la lecture en pause ; Espace permet de reprendre.
Aucune génération n'est automatique :

| Touche, panneau ouvert | Aide demandée |
| --- | --- |
| `1` | Contexte du passage |
| `2` | Question ouverte ; `R` révèle une réponse possible |
| `3` | Indice pour réfléchir |
| `4` | Résumé |
| `5` | QCM ; répondre avec `A`, `B`, `C` ou `D` avant correction |
| `{` / `}` | Défiler dans la réponse |

Une demande suspend la lecture pour laisser réfléchir. Le panneau occupe la
colonne droite à partir de 110 colonnes ; dans une fenêtre étroite, il remplace
temporairement le texte et suspend sa progression. ZEN masque le panneau.
Le changement de passage annule la demande précédente et efface sa réponse.

Le serveur reçoit le texte affiché du passage, limité à 8 000 caractères,
avec des instructions pédagogiques ; aucun PDF complet ni image n'est envoyé.
`--ollama-url` configure le serveur utilisé par la voix et l'accompagnement
(défaut : `http://127.0.0.1:11434`). Le nom du modèle est affiché dans le panneau.
Le repère de page/ligne vient de Reader ; la citation d'appui doit exister dans
le passage. Reader tolère les différences typographiques sans conséquence
(espaces, retours à la ligne, apostrophes et tirets), puis affiche la citation
exacte du document. Une citation absente ou ambiguë entraîne le refus de la
réponse. Cela ne garantit pas la justesse du contenu généré, marqué « IA ·
à vérifier ». La lecture ne dépend pas de la disponibilité du serveur.
Si le modèle reformule sa citation, Reader lui demande automatiquement une
correction une seule fois ; une citation toujours introuvable reste refusée.

Les réponses sont conservées sous `~/.cache/reader/enrichment-v1/`, ou sous
`$XDG_CACHE_HOME/reader/enrichment-v1/`. Supprimer ce cache ne supprime pas la
progression. Les QCM ne sont pas encore un historique d'apprentissage ; les
mots proposés ne constituent pas encore un dictionnaire personnel.
Le fournisseur payant et la sélection d'un mot restent à développer. Un essai
local avec `granite4:latest` a vérifié les échanges ; la qualité pédagogique sur
des documents variés reste à évaluer. Aucun service payant n'est appelé.

## Installer sur un autre Mac

Depuis le dépôt cloné, installez les dépendances puis préparez Ollama et ses modèles :

```sh
./install.sh --all
```

Le script vérifie Python **3.10+** avec `curses` et SQLite, Poppler (`pdftotext`,
`pdftoppm`, `pdfimages`, `pdftocairo`) et Chafa. Il installe les éléments manquants via Homebrew et
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
iTerm2 et GitHub CLI restent facultatifs. `./install.sh --models` installe
l'application Ollama officielle par Homebrew, démarre son serveur local et
télécharge le modèle pédagogique et les voix française et anglaise avant le
lancement de Reader. `./install.sh --library` télécharge seulement les documents
publics du catalogue ; `./install.sh --all` enchaîne modèles et bibliothèque.
Les téléchargements peuvent prendre du temps et utiliser plusieurs Go.
L'installation automatique de l'application Ollama requiert macOS 14 ou plus
récent ; si Ollama est déjà installé, le script réutilise son exécutable.

### Premier clonage

Sur un MacBook Air Apple Silicon ou Intel, avec Homebrew disponible :

```sh
brew install gh
gh auth login
gh repo clone wilofice/reader
cd reader
git switch main
./install.sh --all
./reader README.md
```

Les fonctionnalités et commandes documentées sont disponibles sur la branche `main`.
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
Le titre en haut indique le total des mots du document, par exemple
`notes.md · 12 450 mots`. Le comptage utilise le texte lisible (aperçu Markdown
ou texte extrait du PDF), comme le suivi quotidien. Un titre trop long est
raccourci pour garder le total visible, y compris avec le chrono.
Pour rendre la commande accessible depuis tous les dossiers, vous pouvez créer
un lien vers cet exécutable dans un répertoire de votre `PATH`.

### Devise dans l'en-tête

« Lire, c’est conquérir le monde. » est la seule devise affichée dans l'en-tête,
juste avant la séparation avec le contenu. Les rappels personnels longs sont
masqués par défaut afin de laisser davantage de place au passage lu. Sur les
fenêtres très petites et en mode ZEN, la devise est également masquée. Le
terminal conserve sa taille de caractères ; la devise utilise un style atténué.

## Modes de lecture

### Lecture ZEN

```sh
./reader "notes.md" -z
./reader "notes.md" -z -m w -s 80 -a -w 240
```

La touche `z` active ou quitte le mode ZEN : le contenu reste visible,
sans en-tête, citation ni barre de progression. La position et le temps continuent
à être sauvegardés. Le compteur quotidien reste discret en bas à droite ; un
focus activé explicitement et un indice visuel peuvent apparaître au-dessus
du texte. Les commandes habituelles restent actives ; `?` affiche
temporairement l'aide et `i` la référence du passage, puis Échap revient à la
lecture. L'aide et la consultation de référence suspendent le défilement et le
comptage du temps. Quitter ZEN conserve la position, avec adaptation du passage
à la nouvelle surface d'affichage.

### Focus : chrono ou minuteur

Le focus est **désactivé à l'ouverture**. Appuyez sur `f`, puis choisissez
`c` pour un chrono (temps écoulé) ou `m` pour un minuteur (temps restant).
Entrée démarre ; Échap annule. Dans ce menu, `j` / `k` règlent le minuteur
par pas de 5 minutes : **minimum et durée par défaut de 5 minutes**.
L'ancien réglage de 25 minutes est ramené une fois à 5 minutes lors de la mise
à jour ; les durées choisies ensuite restent mémorisées.
Démarrer une séance reprend une lecture mise en pause. Si le document est
terminé, revenez avec `b` ou commencez une nouvelle lecture avec `N`, puis `f`.

Le temps apparaît en grands chiffres **minutes:secondes**, en haut à droite :
`01:25` signifie 1 minute et 25 secondes. Les minutes continuent au-delà de 59
(par exemple `75:00`). Sur un terminal petit, il passe en affichage compact.
Les chiffres évoluent chaque seconde : un minuteur de 5 minutes commence à
`05:00`, puis passe à `04:59`. Le symbole `▶` indique une séance active.
`f` arrête le focus ; Espace, `p` et `P` suspendent ou reprennent la
lecture et le focus. L'aide, les menus, la veille et la perte de focus du terminal
ne sont pas comptés. La consultation d'une figure compte tant que son aperçu
intégré reste actif ; passer dans une fenêtre Quick Look suspend le compteur.
À zéro, le minuteur reste visible avec
« FOCUS TERMINÉ » et une sonnerie terminal unique, si elle est prise en charge.
La lecture peut continuer ; `f` ferme le minuteur terminé.

Le focus conserve le rythme de lecture choisi, manuel ou automatique. Le mode
et la durée sont mémorisés, mais **aucune séance ne redémarre automatiquement**.
Pour présélectionner une durée sans démarrer :

```sh
./reader "document.pdf" --focus-minutes 15
```

### Objectif quotidien de mots

Le coin inférieur droit affiche `xxx/15000 mots`, tous documents confondus.
Le compteur augmente **quand un passage est validé** en avançant, en manuel
comme en automatique. Afficher un passage, ouvrir l'aide ou revenir en arrière
n'ajoute aucun mot. Repasser sur une zone déjà validée dans le même cycle et
le même jour ne la recompte pas. Une nouvelle relecture avec `N`, après avoir
terminé le document, contribue de nouveau à l'objectif.

Le suivi utilise le texte lisible (sans compter la ponctuation seule), avec
les mêmes repères pour le Markdown brut et son aperçu. Il estime les mots
parcourus ; il ne mesure pas les mouvements des yeux. Les anciens temps de
lecture ne sont pas convertis rétroactivement en mots.

Le jour suit la date locale de la machine. À minuit, le compteur affiché passe
au nouveau jour ; les totaux antérieurs restent dans SQLite. Un passage est
attribué au jour de sa validation. L'objectif est réglable et mémorisé :

```sh
./reader --daily                     # consulter le total du jour
./reader --goal 15000 --daily        # changer l'objectif sans ouvrir de document
./reader "notes.md" --goal 12000     # régler l'objectif puis lire
```

`--status` expose également `daily_date`, `daily_words` et `daily_goal`.
**15 000 mots correspondent à environ 30 à 60 pages** en supposant 250 à 500 mots
par page, ou 75 minutes à 200 mots/minute, hors pauses et prise de notes.
C'est un objectif quotidien conséquent ; un ouvrage technique peut demander
nettement plus de temps à volume égal.

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

### Navigation proportionnelle

Appuyez sur `1`, `2` ou `3` (panneau IA fermé) pour lire en segments de
**1 %**, **0,1 %** ou **0,01 %** du nombre total de mots du document. Le plus
petit segment est d'un mot ; s'il dépasse la place à l'écran, il se lit par
plusieurs pages du terminal. `l`, comme `n` ou la flèche droite, valide le texte
affiché et avance ; `h`, comme `b` ou la flèche gauche, revient au passage
précédent. Ainsi les mots lus sont comptés normalement dans l'objectif
quotidien. Les formules Markdown explicitement délimitées restent dans le même
segment, même si une formule longue peut occuper plusieurs écrans. Les PDF sans
structure de formule reconnue continuent de s'appuyer sur l'extraction texte et
les références de page.

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
| `-F` | `--folder` | Mémoriser le dossier des documents à lire |
| `-H` | `--history` | Sélectionner un document de l'historique |
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
| `n`, Entrée, flèche droite/bas, Page suivante | Avancer |
| `b`, flèche gauche/haut, Page précédente | Revenir et suspendre l'avance automatique |
| Espace, `p`, `P` | Pause / reprise dans tous les modes de lecture, y compris le focus et le comptage du temps ; n'avance pas en manuel |
| `f` | Choisir un chrono ou un minuteur ; arrêter le focus s'il est déjà affiché |
| `a` | Activer ou suspendre l'automatique |
| `+`, `-` | Modifier la vitesse de 25 mots/minute |
| `j`, `k` | Réduire / augmenter le nombre de lignes ou de mots affichés |
| `?` | Ouvrir / fermer l'aide, avec suspension de l'avance automatique |
| `g` | Revenir au début |
| `N` (majuscule) | Commencer une nouvelle lecture après avoir terminé |
| `z` | Activer / quitter ZEN |
| `i` | Consulter la référence de page PDF ou de ligne source |
| `v` | Consulter les pages PDF signalées ou les images Markdown locales du passage |
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
Temps cumulé : 00h 12min · Reste ≈ 00h 08min auto
```

Les durées de lecture cumulées et restantes contiennent uniquement les **heures et minutes**
(le chrono et le minuteur de focus restent en minutes:secondes). Le temps
écoulé est arrondi à la minute inférieure ; le temps restant est arrondi à la
minute supérieure. Le stockage et le JSON conservent les secondes pour le
calibrage et la précision du minuteur. Le compteur se cumule entre les ouvertures du même fichier.
Il compte le temps pendant lequel le texte est disponible à la lecture, en
manuel comme en automatique. Il s'arrête pendant une pause, dans l'aide, quand
la fenêtre est trop petite pour afficher le texte, lorsque le terminal perd le
focus et après la fin du document. L'avance automatique est également suspendue
en arrière-plan ; elle retrouve le délai restant au retour.
Les longues suspensions du processus entre deux mises à jour sont ignorées.

Les terminaux compatibles signalent les changements de focus par le
[protocole xterm 1004](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html).
Avant réception d'événements de focus, iTerm2 et Terminal.app sur macOS local
disposent aussi d'un contrôle natif de l'application au premier plan, vérifié au
plus une fois par seconde. Dès qu'ils sont reçus, les événements du terminal
font foi : une identité d'application héritée ou périmée ne doit pas les contredire.
Ce complément ne nécessite ni AppleScript ni permission d'accessibilité ; il
ne distingue pas les onglets d'une même application, contrairement aux événements
de focus du terminal. Sur un terminal ou un multiplexeur qui ne transmet pas ces
événements, la détection peut être partielle ; `p` reste disponible.

**Ne pas toucher au clavier reste compatible avec la lecture** : le temps compte
tant que le terminal est actif. Appuyez sur `p` si vous vous interrompez en le
laissant au premier plan. Ce compteur reste une estimation, sans mesure de
l'attention ni de la compréhension.
Espace, `p` et `P` suspendent ou reprennent la lecture. Pour avancer en manuel,
utilisez `n`, Entrée ou les flèches. `n` avance et reprend aussi la lecture.

La boucle d'affichage attend normalement jusqu'à une seconde entre deux mises
à jour, au lieu de dix réveils par seconde. Une touche ou un événement de focus
la réveille immédiatement ; l'attente est raccourcie pour respecter la vitesse
automatique et pendant une analyse visuelle en cours.

| Mode | Calcul de l'estimation |
| --- | --- |
| Automatique (`-a` ou `-m s`) | Nombre de mots restant à afficher, divisé par la vitesse `-w` ; le délai du passage courant diminue pendant son affichage |
| Manuel | Rythme observé sur les passages avancés avec `n`, Entrée ou les flèches, et le temps actif passé sur ces passages |
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
Les images gardent leur texte alternatif (ou le libellé « Image ») dans le texte ;
`v` permet de consulter les images locales du passage.
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

**L'aperçu affiche la page originale entière, sans interprétation des objets.**
La touche `v` rend sa mise en page avec Poppler, puis l'affiche dans le mode
adapté : figures, tableaux et formules restent à leur emplacement.
Si plusieurs pages du passage ont déjà des indices visuels, `v` ouvre un menu :
`↑/↓` (ou `j/k`) pour choisir, Entrée pour ouvrir, Échap pour annuler.
Avec une seule page signalée, l'ouverture est directe ; sans indice disponible,
l'aperçu commence à la première page du passage. Les résultats en cours d'analyse
apparaîtront lors du retour à la lecture. Vous pouvez consulter la page suivante
dans l'aperçu intégré sans avancer votre position de lecture.

#### Indicateur de contenu visuel

L'organisation prévue pour la suite est décrite dans [ARCHITECTURE.md](ARCHITECTURE.md).

Sans appuyer sur `v`, un message en gras, au-dessus du texte, signale les indices trouvés sur les
pages du passage affiché, par exemple : `Image repérée · p. PDF 20 · v voir`.
Il reste visible en haut en ZEN, sans réafficher les compteurs. Sa ligne est
réservée : l'apparition d'un indice ne décale pas le passage pendant la lecture.

- **Image repérée** : image intégrée assez grande pour dépasser les filtres
  de taille ; les petites icônes et masques sont ignorés.
- **Tracés visuels probables** : plusieurs traits ou formes vectorielles,
  pouvant appartenir à un schéma, un graphe ou un tableau.
- **Référence Figure 3-2** : mention dans le texte de cette page ; ce n'est
  pas la preuve que la figure y apparaît. `v` ouvre la page de la mention.

L'analyse locale utilise `pdfimages` et un export SVG `pdftocairo`, en
arrière-plan : pages affichées et une page d'avance, sans parcourir tout le
livre. Elle ne nécessite ni modèle, ni GPU, ni appel payant. Les résultats sont
mis en cache dans `~/.cache/reader/visuals-v1/<empreinte PDF>/` (ou sous
`$XDG_CACHE_HOME/reader/visuals-v1/`). L'empreinte porte sur le fichier complet.
La touche `i` donne les indices et les éventuelles erreurs. Une analyse
indisponible est distinguée d'une analyse sans indice ; `v` reste utilisable.

Ce repérage est **heuristique, à l'échelle de la page** : il ne localise pas
l'objet dans le passage, ne distingue pas fiablement tableau, formule et figure,
et peut signaler des décorations. Il peut manquer les petites images ou un
tableau sans bordures. Les caractères définis comme glyphes SVG sont exclus du
comptage des tracés. L'absence d'indicateur ne garantit pas l'absence d'objet.
Pour désactiver l'analyse : `./reader "document.pdf" --no-visual-hints`.

#### Repérage des formules PDF (facultatif)

Installez le moteur enrichi une seule fois sur chaque Mac :

```sh
./install.sh --layout
./reader "document.pdf"
```

L'installation crée `.venv-layout`, installe les dépendances de
`requirements-layout.txt` et télécharge le modèle DocLayout-YOLO (~41 Mo).
L'environnement complet occupait environ 1,2 Go sur la machine de test Apple
Silicon. Le lecteur simple conserve ses dépendances habituelles.
Sous Linux, installez les dépendances de base puis lancez `./install-layout.sh`.
Le moteur optionnel utilise Python 3.10 à 3.13 ; l'installateur macOS peut
installer Python 3.12 si nécessaire. La pile testée utilise macOS 14+ sur ARM64.

Après installation, les PDF sont préparés en arrière-plan : pages visibles
prioritaires, puis document entier. La lecture peut commencer immédiatement.
Le bandeau peut afficher `Formule(s) probable(s) · p. PDF 293 · v voir` ; `i`
indique la méthode et les éventuels échecs. `v` ouvre toujours la page originale.

Pour préparer le document avant lecture, sans ouvrir la base de progression :

```sh
./reader "document.pdf" --prepare
./reader "document.pdf" --formulas off    # garder seulement images et tracés
./reader "document.pdf" --formulas text   # typographie, sans charger le modèle
./reader "document.pdf" --formulas model  # modèle visuel seul
```

`--formulas auto`, par défaut, active la combinaison typographie + modèle
lorsque l'installation est prête. Sans moteur installé, la lecture habituelle
reste disponible. Le téléchargement est réservé à l'installation ; la
préparation désactive les connexions réseau Python du moteur. Le modèle est
lié à une révision et une empreinte SHA-256 vérifiées. Aucun service payant
n'est utilisé. CUDA ou le GPU Apple sont sélectionnés lorsqu'ils sont disponibles,
avec retour au CPU si une opération accélérée échoue.

Les résultats sont conservés sous
`~/.cache/reader/formulas-v1/<méthode-modèle>/<empreinte PDF>/`, ou sous
`$XDG_CACHE_HOME/reader/`. Fermer le lecteur arrête son calcul ; rouvrir reprend
les pages manquantes. Les préparations simultanées d'un même cache partagent
un verrou. Effacer ce cache ne supprime pas la progression SQLite.

Le repérage reste probabiliste : il peut manquer des expressions inline ou
confondre des affectations de pseudocode avec des formules. Les zones ne sont
pas un comptage exact des équations. Le moteur visuel peut traiter une page
scannée ; **la lecture du texte d'un PDF entièrement scanné nécessite toujours
un OCR préalable**. Cette version ne transcrit ni n'explique les formules, et
ne traite pas les expressions LaTeX des Markdown.
Le [compte rendu du repérage des formules](RAPPORT-FORMULES.md) donne les cas
contrôlés, les signalements sur le livre entier et les coûts observés.

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

La référence de page localise le passage courant ; l'indicateur visuel donne
séparément les indices trouvés. Le numéro physique commence à 1 et peut différer du numéro
imprimé dans le livre. Les pages sans texte entre deux pages restent comptées.
Les PDF entièrement scannés nécessitent toujours un OCR préalable.

`-p` expose `pdf_page` et `pdf_pages` pour un PDF, sinon `null`. Ces champs
concernent le début du passage sauvegardé, indépendamment de la taille de fenêtre.
Les tableaux et formules ne font pas l'objet d'une conversion sémantique.

### Images Markdown locales

Les images référencées dans le passage affiché sont signalées au-dessus du texte.
`v` ouvre directement une image unique ou propose un choix s'il y en a plusieurs.
Le même mode `--preview auto` sélectionne iTerm2, Quick Look ou les symboles.
Échap / `v` revient exactement au passage ; le défilement automatique attend la
fermeture. Le choix n'ajoute pas de temps de lecture ; la consultation de l'image
est comptée comme pour un aperçu PDF.

```markdown
![Architecture](images/architecture.png)
![Tableau](<images/tableau des mesures.jpg>)
![Schéma][schema]

[schema]: images/schema.png
```

Les chemins relatifs sont résolus depuis le dossier du Markdown, pas depuis
le terminal. Les images inline, les références Markdown et les balises HTML
`<img src="…">` simples sont prises en charge ; les exemples dans les blocs de
code sont ignorés. Les images distantes ne sont pas téléchargées.
Formats : PNG, JPEG, GIF, WebP, BMP et TIFF (selon le moteur installé). Les GIF
sont affichés sans animation dans l'aperçu intégré. Les SVG et les extensions
Markdown complexes restent hors de cette première version. Un fichier manquant
produit un message et laisse revenir à la lecture. L'aperçu intégré ajuste
l'image au terminal ; le zoom et le déplacement restent propres à l'aperçu PDF.

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

Dans un terminal, `reader -H` ouvre un sélecteur trié par dernière consultation :
utilisez `↑`/`↓` (ou `j`/`k`), puis Entrée pour reprendre le document choisi à
sa position mémorisée. Le chemin complet, la progression et le temps de lecture
sont affichés. Un fichier déplacé ou supprimé porte le symbole `⚠` et ne peut
pas être ouvert. Dans un script ou avec une redirection, `--history` conserve sa
sortie texte afin de rester exploitable en ligne de commande.

La mémoire identifie les documents par leur chemin absolu. Un fichier déplacé
est considéré comme nouveau ; un contenu modifié reprend au début pour éviter
une position incorrecte. Utilisez une seule session par document : la dernière
sauvegarde prévaut. Les PDF sont extraits avec `pdftotext -layout` ; leurs positions
concernent le texte extrait, pas les pages. Un PDF scanné nécessite un OCR préalable.

### Synchroniser deux Mac sans cloud

Fermez les sessions de lecture sur les deux machines, puis lancez depuis l'une
d'elles :

```sh
reader sync ssh genereux@192.168.1.18
```

La commande copie aussi dans `~/Lectures` les PDF et Markdown absents de chaque
Mac, récupère l'état distant, le fusionne localement, puis renvoie l'état
consolidé. Chaque import crée d'abord une sauvegarde cohérente dans
`~/.local/state/reader/backups/`. Aucun serveur tiers n'est utilisé et les bases
SQLite ne sont jamais partagées directement sur le réseau.

La fusion associe les documents par empreinte de contenu : elle conserve la
position la plus avancée, les cycles terminés, le temps cumulé le plus élevé et
l'union des mots quotidiens déjà couverts. Les textes collés et les fichiers de
lecture sont transportés. Leur copie dans `~/Lectures` rend la reprise
indépendante du chemin original. Si un original est supprimé sur un Mac, la copie
de l'autre peut le rétablir lors de la synchronisation suivante. Si toutes les
copies physiques sont supprimées, seule la progression peut être conservée.
Utilisez Reader sur une seule machine à la fois et synchronisez avant de changer
de Mac.

Pour transporter manuellement un paquet, par exemple sur une clé USB :

```sh
reader sync export ~/Desktop/reader-sync.json
reader sync import ~/Desktop/reader-sync.json
```

Le paquet contient les chemins et les textes collés : il est créé avec des
permissions privées, mais doit rester confidentiel. Consultez toutes les
commandes avec `reader sync --help`.

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

### Comparer automatiquement les détecteurs sur un PDF

Un outil **expérimental, séparé de la lecture** compare le repérage structurel
Poppler et une méthode OpenCV sur toutes les pages, sans toucher à SQLite.
OpenCV masque les mots sélectionnables puis cherche des zones d'encre restantes.
Il ne comprend pas les figures et peut manquer des formules masquées avec le
texte. Les lignes sont aussi mesurées par morphologie
([méthode OpenCV](https://docs.opencv.org/4.13.0/dd/dd7/tutorial_morph_lines_detection.html)).

```sh
python3 -m venv .venv-audit
.venv-audit/bin/python -m pip install -r requirements-audit.txt
.venv-audit/bin/python audit_visuals.py "document.pdf" --sample 16
```

Poppler reste nécessaire. Aucune dépendance du lecteur n'est ajoutée par défaut.
Les résultats se trouvent dans `output/pdf/visual-audit/<empreinte PDF>/` :
`summary.md`, inventaires JSON/CSV et `review.html`. La galerie locale mélange
des désaccords et des accords positifs/négatifs ; elle permet d'exporter des
annotations Oui/Non/Incertain. Ces choix ne sont pas enregistrés automatiquement :
exportez-les avant de fermer la page. Les pages sont numérotées physiquement.

Les analyses réussies sont conservées pour reprendre après interruption ; les
erreurs sont retentées. `--output chemin` change le dossier de résultats.
Les temps sauvegardés peuvent provenir d'une passe antérieure. Aucun fichier
n'est envoyé sur le réseau. Les rendus personnels et l'environnement d'audit
sont exclus de Git.

Un désaccord **ne prouve pas un oubli**. Seul un contrôle visuel peut établir
une référence ; sans annotations indépendantes, cet outil ne calcule ni précision
ni rappel globaux. Ses résultats ne changent pas le détecteur de `reader`.
Le [premier compte rendu Poppler / OpenCV](RAPPORT-DETECTION-VISUELLE.md)
présente l'essai sur 269 pages et le contrôle visuel d'un échantillon.
L'[audit du livre de Russell et Norvig](RAPPORT-AUDIT-AIMA.md) couvre 1 166 pages
et documente notamment les formules manquées et la correction de l'import XML.

La [feuille de route des documents enrichis](FEUILLE-DE-ROUTE.md) organise les
demandes de mode ZEN, relectures complètes, images, graphes, tableaux, formules,
pas de progression, colonne LLM et voix de lecture. Elle précise les priorités,
les dépendances et les limites des solutions envisagées. Le mode ZEN, les cycles
et un aperçu visuel des pages PDF et des images Markdown locales sont désormais
disponibles ; les autres enrichissements restent à développer.

Le [rapport sur la lecture assidue et l'apprentissage durable](RAPPORT-LECTURE-APPRENTISSAGE.md)
réunit les recherches consultées, leurs limites et les fonctions envisagées :
préférences mémorisées, journal de séances, notes, rappel actif, révisions espacées
et liens entre idées. Il décrit un ordre de développement et des critères
d'évaluation. Ces propositions ne sont pas encore implémentées.
