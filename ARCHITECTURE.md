# Architecture de Reader : prochaine étape

## Objectif

Signaler l'existence d'un contenu visuel et permettre de le consulter, puis
reprendre exactement la lecture. L'explication automatique des figures ne fait
pas partie du besoin. Conserver un fonctionnement local, dans le terminal,
avec Quick Look comme solution macOS complémentaire.

## Base actuelle

- `reader` : extraction du texte, position, passages, interface `curses`,
  rythme de lecture et mémoire SQLite.
- `visual_hints.py` : analyse structurelle Poppler en arrière-plan, indices
  par page et cache identifié par l'empreinte du PDF complet.
- `pdf_preview.py` : rendu de la page, zoom et affichage iTerm2 ou Quick Look.
- `formula_index.py` : lecture du cache et gestion d'un processus de préparation
  indépendant de `curses`, avec priorité aux pages affichées.
- `layout_worker.py` : typographie PyMuPDF et modèle local DocLayout-YOLO dans
  `.venv-layout` ; cache versionné défini par `formula_cache.py`.
- `reading_habits.py` : séance de focus liée au temps de lecture actif et
  couverture des mots par jour/document/cycle dans SQLite ; les intervalles
  validés évitent le double comptage après un retour ou une réouverture.
- `focus_ui.py` : choix explicite du chrono ou du minuteur, sans activation
  automatique ni changement du rythme de lecture.

Le repérage est indépendant de la taille des passages. L'interface associe les
pages couvertes par le texte affiché à leurs indices. Une mention textuelle
n'est pas assimilée à une figure détectée.

## Organisation cible, par petites étapes

1. **Document** : produire un texte avec ses positions et références source.
   PDF et Markdown utilisent des adaptateurs distincts. Préserver les offsets
   actuels pour ne pas perdre les positions sauvegardées.
2. **Index visuel** : fournir une liste d'indices par page ou emplacement
   Markdown, avec type d'indice, origine et état d'analyse. Un rectangle reste
   facultatif ; ne pas inventer une localisation précise.
3. **Session de lecture** : gérer position, passage, vitesse, temps et cycles
   sans dépendre du terminal ni d'un détecteur particulier.
4. **Interface et aperçu** : afficher les indices, proposer leur consultation
   et revenir au passage. L'interface ne lance pas directement les extracteurs.
5. **Persistance** : SQLite conserve la lecture ; le cache versionné conserve
   les données dérivées. Effacer le cache ne doit jamais effacer la progression.

Un détecteur OpenCV ou un modèle spécialisé pourrait compléter l'index visuel
ultérieurement, sans changer la session de lecture. Aucun LLM n'est nécessaire
pour signaler la présence d'un objet.

## Lot livré et prochaine étape

L'indice reste en haut. Un menu permet de choisir parmi les pages déjà signalées
du passage avant d'ouvrir l'aperçu. Les images Markdown locales sont consultables
avec les mêmes moteurs d'affichage. `reading_media.py` extrait leurs références
et fournit le menu commun ; les fichiers distants ne sont pas téléchargés.

Le moteur enrichi est désormais facultatif. Il prépare les pages progressivement,
conserve leurs références et se termine à la fermeture du lecteur. Le mode
`--prepare` remplit le même cache sans ouvrir SQLite. Les modèles, environnements
et rendus ne sont pas versionnés. La validation couvre des pages de formules
manquées auparavant et une page rasterisée pour simuler un scan ; l'amélioration
du rappel et des fausses alertes sur d'autres documents reste à évaluer.

La voix et les enrichissements pédagogiques viendront ensuite comme services
optionnels de la session ; ils ne doivent pas conditionner la lecture simple.
