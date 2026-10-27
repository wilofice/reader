# Reader — lecture dans le terminal

Lecteur de texte, Markdown en aperçu et PDF pour macOS et les terminaux Unix, avec
reprise automatique et barre de progression. Python **3.10 ou supérieur** suffit
pour le texte. Pour les PDF, installez Poppler : `brew install poppler`.

## Installer sur un autre Mac

Sur un MacBook Air Apple Silicon ou Intel, avec Homebrew disponible :

```sh
brew install python poppler gh
gh auth login
gh repo clone wilofice/reader
cd reader
python3 --version
./reader README.md
```

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

Le [rapport sur la lecture assidue et l'apprentissage durable](RAPPORT-LECTURE-APPRENTISSAGE.md)
réunit les recherches consultées, leurs limites et les fonctions envisagées :
préférences mémorisées, journal de séances, notes, rappel actif, révisions espacées
et liens entre idées. Il décrit un ordre de développement et des critères
d'évaluation. Ces propositions ne sont pas encore implémentées.
