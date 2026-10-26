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

```sh
# Passages de 10 lignes affichées, avec avance manuelle
./reader "notes.txt" -m l -s 10

# Lots de 80 mots
./reader "notes.txt" -m w -s 80

# Lots automatiques à 220 mots par minute
./reader "notes.txt" -m w -s 80 -a -w 220

# Défilement ligne par ligne, démarrant automatiquement
./reader "notes.txt" -m s -w 180
```

Les modes courts `l`, `w`, `s` correspondent à `lines`, `words`, `scroll`.
Toutes les anciennes formes restent acceptées, par exemple
`--mode words --size 80`. La lettre `w` après `-m` choisit le mode mots ;
l'option `-w 220` règle la vitesse.

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

Les passages tiennent dans la fenêtre : le nombre demandé est un maximum.
Pendant la lecture, `[` réduit le passage et `]` l'augmente : d'une ligne en
mode `lines` ou `scroll`, de dix mots en mode `words`, avec un minimum de un.
La valeur apparaît sous le titre. La position courante reste inchangée ; le
délai automatique est recalculé pour le nouveau passage. Ces réglages valent
pour la session ; utilisez `--size` pour choisir la taille au démarrage.

Les longues lignes sont repliées sans perdre de texte. Le mode `scroll` déplace
la fenêtre d'une ligne à la fois ; chaque délai dépend du nombre de mots de
cette ligne. Les autres modes automatiques calculent le délai sur le passage
affiché. Le rythme reste approximatif, avec un délai minimal de 0,25 seconde.

## Touches

| Touche | Action |
| --- | --- |
| `n`, Entrée, flèche droite/bas | Avancer |
| `b`, flèche gauche/haut | Revenir et suspendre l'avance automatique |
| Espace | Suspendre l'automatique ; avancer en lecture manuelle |
| `a` | Activer ou suspendre l'automatique |
| `+`, `-` | Modifier la vitesse de 25 mots/minute |
| `[`, `]` | Réduire / augmenter le nombre de lignes ou de mots affichés |
| `g` | Revenir au début |
| `q`, Échap | Sauvegarder et quitter |

Le retour retrouve les passages visités pendant la session. Après réouverture,
il recalcule le passage précédent selon la taille actuelle du terminal.

## Lisibilité et aperçu Markdown

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
le défilement, la fin de lecture et la restauration du terminal. Un test extrait
aussi un vrai PDF si Poppler est disponible ; sinon ce test est ignoré.
