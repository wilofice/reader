# Journal des évolutions

Ce journal commence le 31 octobre 2026. Pour les changements antérieurs,
consulter Git ; l'état consolidé est dans
[ETAT-DES-FONCTIONNALITES.md](ETAT-DES-FONCTIONNALITES.md).

## 3 novembre 2026 — Synchronisation directe

- Adoption locale : la première ouverture interactive d'un PDF ou Markdown
  extérieur le copie atomiquement dans `~/Lectures`, réutilise les copies
  identiques et déplace l'éventuelle progression vers ce chemin durable.
- Documents physiques : la synchronisation SSH copie désormais les PDF et
  Markdown manquants dans `~/Lectures` sur chaque Mac avant de fusionner la
  mémoire. La lecture ne dépend donc plus du chemin original dès qu'une copie
  subsiste sur l'une des deux machines.
- Lancement sans argument : `reader --folder CHEMIN` configure une boîte de
  lecture locale, puis `reader` seul découvre les nouveaux PDF et Markdown et
  ouvre l'historique. Le parcours est récursif, ignore les éléments cachés et
  diffère l'extraction PDF jusqu'à la sélection du document. Validation
  complète : 134 tests réussis, sept tests facultatifs ignorés.
- Configuration initiale appliquée sur les deux Mac avec le dossier personnel
  `~/Lectures`. Un seul dossier est actif par machine ; répéter `--folder` avec
  le même chemin réanalyse, tandis qu'un chemin différent remplace uniquement
  la file des nouveautés et conserve tout l'historique.
- Synchronisation directe : ajout de `reader sync export`, `import` et `ssh`.
  Le format JSON portable fusionne progression, cycles, temps, couverture
  quotidienne et textes collés ; chaque import sauvegarde SQLite auparavant.
  Les documents absents restent en attente par empreinte jusqu'à leur ouverture.
  Aucun paquet supplémentaire n'est requis sur macOS : le transport réutilise
  SSH. Validation complète : 129 tests réussis, sept tests facultatifs ignorés.

## 2 novembre 2026 — Prototype de bibliothèque de lecture

- Reprise depuis l'historique : `reader -H` devient un sélecteur interactif de
  tous les documents mémorisés, classés par consultation récente. Entrée reprend
  le document choisi ; les chemins absents sont signalés. Hors terminal, la
  sortie textuelle historique est conservée pour les scripts. Les horodatages
  ont désormais une précision à la milliseconde pour stabiliser ce classement.
  Validation complète : 125 tests réussis, sept tests visuels facultatifs ignorés.
- Interface de lecture : les rappels personnels longs sont désormais masqués
  par défaut. Seule la devise « Lire, c’est conquérir le monde. » reste visible
  dans l'en-tête lorsque l'espace le permet. La suite complète valide ce rendu
  avec 124 tests réussis et sept tests visuels facultatifs ignorés.
- Sélection vocale automatique : les fiches en anglais utilisent
  `phonon:31m-en`, les autres `phonon:40m-fr`. Une option explicite
  `--speech-model` reste prioritaire ; les fichiers hors catalogue restent en
  français par défaut. `--status` expose le modèle choisi.
- Installation portable : `./install.sh --models` précharge les deux voix
  Phonon sur Apple Silicon ; `--library` télécharge les documents publics et
  `--all` prépare modèles et bibliothèque. Les sources nécessitant un compte ou
  refusant l'automatisation restent référencées sans faire échouer `--all`.
- Validation sur Apple Silicon : `./install.sh --all` a installé les deux voix,
  le modèle pédagogique et les sept PDF publics. Une synthèse anglaise réelle
  avec `phonon:31m-en` a produit 3,84 secondes d'audio valide. La suite complète
  compte 123 tests réussis ; sept tests visuels facultatifs ont été ignorés.
- Correction de la navigation du catalogue : activation explicite des touches
  spéciales, prise en charge des deux séquences terminal courantes pour les
  flèches, et surlignage visible de la ligne active. Vérification réelle dans
  un pseudo-terminal : quatre flèches bas puis Entrée ouvrent le rapport BRI.
  Les touches `j`/`k`, Début et Fin restent aussi disponibles.
- Validation automatisée après correction : 120 tests réussis, dont quatre
  tests propres au sélecteur de bibliothèque ; sept tests facultatifs ignorés
  faute des dépendances OpenCV/PyMuPDF de leurs environnements dédiés.
- Ajout d'un catalogue terminal de onze lectures, avec progression par édition,
  liens d'acquisition, statut d'accès et téléchargement depuis des URL PDF
  officielles. `./reader --catalog` liste ou ouvre le sélecteur interactif ;
  `--download-library`, `--download-book ID`, `--open-book ID` et
  `--attach-book ID CHEMIN` couvrent acquisition, rattachement et lecture.
- Sept PDF ont été téléchargés dans `~/.local/share/reader/library/`, hors Git :
  manuel de finance OpenStax 2e (2026), BRI AER 2026, résumé GIEC AR6, OCDE
  2023, Banque mondiale WDR 2026, article Transformer sur arXiv et PNUD HDR
  2025. Reader retrouve leurs positions via
  la mémoire SQLite habituelle.
- L'AIE demande la création d'un compte gratuit pour télécharger le WEO complet ;
  Reader conserve son lien sans contourner cette étape. Le téléchargement du
  WEO FMI a répondu HTTP 403 sur cette machine. Ces fiches restent ouvrables par
  source officielle ou rattachement d'un document local.
- La recherche n'a trouvé aucun téléchargement complet gratuit autorisé pour
  *The World* ou *The Effective Executive*. Le premier est référencé pour la
  localisation en bibliothèque ; le second dispose d'un aperçu éditeur et peut
  se trouver à l'emprunt selon les bibliothèques. Les copies détenues par
  l'utilisateur peuvent être rattachées ; aucune copie non autorisée n'a été
  récupérée. La source finance a été remplacée par le manuel libre OpenStax ;
  Damodaran reste une référence avancée possible, mais commerciale.

## 1 novembre 2026 — Stratégie de bibliothèque de lecture

- Structuration de l'objectif : constituer une culture générale et stratégique
  pour des responsabilités de direction, avec des rayons internationaux,
  techniques, financiers, énergétiques, juridiques, sociaux et managériaux.
- Recherche et première sélection de dix sources institutionnelles, académiques
  et éditoriales ; accès gratuit, achat/emprunt, licences et limites sont
  distingués dans [STRATEGIE-BIBLIOTHEQUE-CULTURE.md](STRATEGIE-BIBLIOTHEQUE-CULTURE.md).
- Le document formalise les phases de validation, rétention, catalogue local,
  prototype terminal et évaluation. La bibliothèque elle-même n'est pas
  implémentée ; aucune œuvre n'est ajoutée ou téléchargée dans le dépôt.

## 1 novembre 2026 — Navigation proportionnelle

- `1`, `2` et `3` choisissent des segments de lecture de 1 %, 0,1 % ou 0,01 %
  du nombre total de mots. `h`/`l` avancent ou reviennent comme `b`/`n` et les
  flèches ; chaque passage affiché est compté normalement à la validation.
- Les formules Markdown explicitement délimitées restent dans le même segment.
  Les PDF et équations sans délimiteurs restent à évaluer sur documents réels.

## 1 novembre 2026 — Préparation Ollama avant Reader

- `./install.sh --models` installe l'application Ollama officielle si nécessaire,
  démarre le serveur et télécharge à l'avance le modèle texte `granite4:latest`
  ainsi que la voix française `phonon:40m-fr` sur Apple Silicon. La commande
  affiche la progression `ollama pull`; elle convient avant le premier lancement
  de Reader. L'installation à la demande dans Reader reste comme solution de
  secours pour un modèle choisi plus tard.
- Sur Mac Intel, le modèle texte est préchargé ; Phonon est omis et la voix
  macOS `say` reste disponible.

## 31 octobre 2026

- Suivi : création d'un état consolidé et de ce journal ; priorité donnée à la
  voix, puis à l'accompagnement pédagogique après la bibliothèque de textes.
- Bibliothèque : import depuis le presse-papiers (`-c`) ou collage (`--paste`),
  nom avec `-n`, liste avec `--library`, reprise avec `--open NOM`.
  Les textes sont conservés localement à côté de la base ; un nom existant avec
  un contenu différent est refusé. Une réimportation identique conserve la reprise.
- Rappel personnel : ajout du sticky note et d'au moins un mot à noter, dans
  les variantes complète et abrégées du rappel.
- Clarification : les pas de navigation en pourcentage restent à implémenter.
- Voix, premier prototype : `t`, `--speak`, adaptateurs Ollama et macOS `say`,
  pause/reprise du processus audio, tempo FFplay et synchronisation au passage.
  La préparation ne valide aucun mot et n'est pas du temps d'écoute ; une
  réouverture relit le passage interrompu. Un seul passage temporaire est préparé.
- Accompagnement, premier prototype : `e`, panneau latéral ou vue étroite,
  demandes explicites de contexte/question/indice/résumé/QCM via Ollama,
  corrections masquées avant réponse, cache, référence source et annulation
  lorsque le passage change. ZEN masque le panneau. Pas d'API payante à ce stade.
- Validation des prototypes : synthèse macOS réelle sans diffusion sonore ;
  API audio et génération pédagogique testées avec des serveurs simulés.
  Ollama local 0.33.3 ne permet pas encore l'essai Phonon (minimum documenté 0.40.9).
  Ne pas confondre ces vérifications avec une comparaison des voix ou une
  validation de la qualité pédagogique d'un vrai modèle.
- Essai complémentaire avec `granite4:latest`, déjà installé : contexte reçu ;
  un premier QCM a été refusé pour structure invalide et un autre produisait
  un résumé au lieu d'une question. Le schéma et les contrôles ont été renforcés.
  Une question comparative ensuite produite n'était pas suffisamment justifiée
  par le passage ; les consignes ont été resserrées. La justesse sémantique reste
  à évaluer et n'est pas garantie par la validation JSON ou une citation présente.
  Cet essai ne suffit pas à qualifier la pédagogie du modèle sur des livres.
- Ancrage des réponses IA : les différences inoffensives d'espaces,
  d'apostrophes et de tirets sont rapprochées du texte exact du document. Une
  citation reformulée déclenche une seule demande de correction au modèle ; une
  citation toujours absente est refusée afin de ne pas masquer une hallucination.
- Installation Ollama : les modèles vocal et texte absents sont maintenant
  téléchargés à la première utilisation via l'API du serveur configuré ; une
  progression s'affiche dans l'interface. Le panneau choisit `granite4:latest`
  par défaut. Ollama doit rester installé et démarré, avec Internet et espace
  disque disponibles lors du premier téléchargement sur chaque serveur.
- Vérifications : 111 tests exécutés, aucun échec, sept ignorés ; contrôles ciblés
  répétés après les ajustements de la voix et du schéma pédagogique. Le collage
  et la réouverture nommée ont été vérifiés dans un pseudo-terminal réel.

### Correction de l'activation de la voix

- Diagnostic réel après mise à jour : Ollama 0.40.13 fonctionnait, mais
  `phonon:40m-fr` était absent (HTTP 404). Téléchargement du modèle français
  effectué sur cette machine (~126 Mo).
- `t` et `T` activent/arrêtent désormais la voix. Un modèle absent indique
  directement `ollama pull NOM_DU_MODELE`. L'en-tête signale l'échec et `i`
  permet de lire le message complet.
- Un second blocage a été reproduit : FFplay ne démarrait plus, faute de
  `libjxl.0.11.dylib`. Au tempo ×1, macOS utilise désormais `afplay` en priorité.
  Les tempos différents nécessitent toujours un FFplay fonctionnel ; une erreur
  de bibliothèque indique comment revenir à ×1 ou réparer FFmpeg.
- Test Phonon réel : environ trois secondes pour générer sept secondes d'audio
  au premier essai, signal non silencieux, lecture native à volume nul,
  pause/reprise et fin de lecture validées. Cette mesure ponctuelle sur le Mac
  de développement n'est ni un benchmark MacBook Air ni un jugement de qualité vocale.
- Tests ciblés : sept vérifications audio, dont les deux casses de `t`, le
  modèle manquant, la préférence pour le lecteur natif et le message FFplay.
- Non-régression : 115 tests exécutés, aucun échec, sept ignorés.

## Derniers correctifs déjà publiés

- `f793592` : Page suivante/précédente pour les télécommandes de présentation.
- `334bfbe` : dépendance `huggingface-hub` explicitement installée pour DocLayout-YOLO.
- `8159333` : durée par défaut du minuteur ramenée à cinq minutes.
