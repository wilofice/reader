# État des fonctionnalités de Reader

Mis à jour le 2 novembre 2026. Ce document décrit l'état livré et l'ordre de
travail actuel ; [EVOLUTIONS.md](EVOLUTIONS.md) conserve les changements datés.
La [feuille de route](FEUILLE-DE-ROUTE.md) détaille les pistes de conception,
dont certaines ne sont pas encore réalisées.

La bibliothèque stratégique dispose maintenant d'un **prototype terminal** :
catalogue de 11 fiches, recherche des sources, téléchargement des fichiers
officiels accessibles, rattachement de documents personnels et reprise avec la
progression SQLite habituelle. Les ouvrages commerciaux ne sont pas distribués.
Voir les commandes dans le [README](README.md) et l'analyse dans le
[plan dédié](STRATEGIE-BIBLIOTHEQUE-CULTURE.md). L'équilibre et la qualité du
catalogue restent à évaluer avec l'utilisateur.

## Disponible

| Fonction | État et limites |
| --- | --- |
| Texte, Markdown et PDF | Aperçu Markdown ; extraction PDF avec Poppler. |
| Lecture manuelle et automatique | Passages en mots ou lignes, défilement, vitesse et taille réglables. |
| Reprise et relectures | Position SQLite, cycles de lecture ; terminer avant de commencer le cycle suivant. |
| Interface et ZEN | Progression, nombre total de mots, rappels personnels, affichage épuré facultatif. |
| Images | Pages PDF et images Markdown locales ; iTerm2 ou Quick Look sur macOS. |
| Repérage des contenus complexes | Indices par page, formules via moteur optionnel ; détection imparfaite, sans explication des figures. |
| Préparation PDF | Cache enrichi avec `--prepare`, après `./install.sh --layout`. |
| Temps et focus | Temps actif, estimation restante, chrono/minuteur sur demande, minimum et défaut de cinq minutes. |
| Objectif quotidien | Mots validés sauvegardés par date ; objectif de 15 000 mots par défaut. Pas encore de tableau de bord historique. |
| Télécommande | Navigation par Page suivante/précédente, en plus des flèches. |
| Navigation proportionnelle | `1`/`2`/`3` activent des segments de 1 %/0,1 %/0,01 % du nombre de mots. `h`/`l` sont des alias des commandes de passage précédent/suivant ; la progression quotidienne reste comptée normalement. |
| Bibliothèque de textes collés | Import nommé, conservation du texte, liste et reprise par le nom. |
| Bibliothèque stratégique | Catalogue terminal de 11 sources, navigation par flèches ou `j`/`k`, téléchargement officiel, rattachement PDF local et progression par édition. `./install.sh --library` installe les documents accessibles et `--all` prépare modèles et bibliothèque. Sept documents téléchargés localement ; FMI en HTTP 403 et rapport AIE soumis à compte. |
| Voix — prototype validé par l’utilisateur | Ollama/Phonon ou macOS `say`, pause/reprise, progression à la fin de l'audio. Les livres du catalogue choisissent automatiquement Phonon anglais ou français selon leur fiche. `./install.sh --models` précharge les deux voix ; téléchargement à la demande disponible en secours. La voix française est validée ; voix anglaise, confort prolongé et reprise fine restent à évaluer. |
| Accompagnement — prototype local en évaluation | Panneau à la demande, contexte/question/indice/résumé/QCM, cache et citations contrôlées. `./install.sh --models` précharge `granite4:latest` ; l’utilisateur évalue la qualité des résultats. |

## Priorités confirmées

1. **Textes collés** : bibliothèque nommée implémentée ; bibliothèque et mémoire
   restent propres à chaque machine.
2. **Voix de lecture** : l’utilisateur a testé et validé le prototype. Restent
   comparaison avec Kokoro, confort d'écoute prolongée et reprise plus fine.
3. **Accompagnement pédagogique** : prototype disponible ; l’utilisateur évalue
   encore la qualité. Ensuite : sources vérifiables, adaptateur payant éventuel
   et suivi des exercices.
4. **Navigation proportionnelle** : segments de lecture proportionnels livrés
   avant le dictionnaire. Restent les essais sur PDF et formules extraites sans
   délimiteurs explicites.
5. **Dictionnaire** : prochain chantier à cadrer avant codage : sélection au
   clavier, définitions sourcées et vocabulaire personnel local.
6. **Statistiques** : historique quotidien, semaines/mois, régularité. Les
   totaux journaliers existent déjà ; leur présentation reste à développer.
7. **Documents complexes** : davantage de tests sur tableaux, scans et lecture
   multicolonne. L'accès à la page originale reste la référence.
8. **Bibliothèque stratégique** : prototype initial livré ; prochaine étape,
   essayer les lectures et les accès locaux, puis réévaluer la couverture, les
   perspectives et l'ordre du catalogue avant de l'élargir.

## Règle de suivi

Pour chaque changement de comportement, mettre à jour le README si nécessaire,
ce tableau et le journal daté. Distinguer une fonction proposée, un prototype,
une validation automatique et un essai réel sur les machines de l'utilisateur.
Une modification locale n'est disponible sur l'autre machine qu'après commit,
push et récupération du dépôt ; ni la bibliothèque ni SQLite ne sont
synchronisées par Git.
