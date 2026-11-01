# État des fonctionnalités de Reader

Mis à jour le 1 novembre 2026. Ce document décrit l'état livré et l'ordre de
travail actuel ; [EVOLUTIONS.md](EVOLUTIONS.md) conserve les changements datés.
La [feuille de route](FEUILLE-DE-ROUTE.md) détaille les pistes de conception,
dont certaines ne sont pas encore réalisées.

La bibliothèque stratégique est **au stade de la recherche et de la stratégie** ;
elle n'est pas encore une fonction de Reader. Le [plan dédié](STRATEGIE-BIBLIOTHEQUE-CULTURE.md)
documente les domaines, dix sources initiales vérifiées, les conditions d'accès
et les phases proposées. La liste doit être validée avant tout développement.

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
| Voix — prototype validé par l’utilisateur | Ollama/Phonon ou macOS `say`, pause/reprise, progression à la fin de l'audio. `./install.sh --models` précharge Phonon français avant l'ouverture ; téléchargement à la demande disponible en secours. L’utilisateur a testé et validé ; confort d’écoute prolongée et reprise fine restent à évaluer. |
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
8. **Bibliothèque stratégique** : sources et stratégie documentées ; prochaine
   étape, valider le catalogue initial, distinguer fondamentaux et veille, puis
   définir le manifeste local avant d'ajouter une option Bibliothèque au menu.

## Règle de suivi

Pour chaque changement de comportement, mettre à jour le README si nécessaire,
ce tableau et le journal daté. Distinguer une fonction proposée, un prototype,
une validation automatique et un essai réel sur les machines de l'utilisateur.
Une modification locale n'est disponible sur l'autre machine qu'après commit,
push et récupération du dépôt ; ni la bibliothèque ni SQLite ne sont
synchronisées par Git.
