# État des fonctionnalités de Reader

Mis à jour le 31 octobre 2026. Ce document décrit l'état livré et l'ordre de
travail actuel ; [EVOLUTIONS.md](EVOLUTIONS.md) conserve les changements datés.
La [feuille de route](FEUILLE-DE-ROUTE.md) détaille les pistes de conception,
dont certaines ne sont pas encore réalisées.

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
| Bibliothèque de textes collés | Import nommé, conservation du texte, liste et reprise par le nom. |
| Voix — prototype | Ollama/Phonon ou macOS `say`, pause/reprise, progression à la fin de l'audio. `./install.sh --models` précharge Phonon français avant l'ouverture ; téléchargement à la demande disponible en secours. Chaîne Phonon réelle testée à volume nul ; qualité à l'écoute à évaluer. macOS utilise `afplay` au tempo normal, FFplay pour les autres tempos. |
| Accompagnement — prototype local | Panneau à la demande, contexte/question/indice/résumé/QCM, cache et citations contrôlées. `./install.sh --models` précharge `granite4:latest` ; téléchargement à la demande disponible en secours. Qualité d'un modèle réel encore à évaluer. |

## Priorités confirmées

1. **Textes collés** : première version implémentée ; à essayer sur l'autre Mac.
2. **Voix de lecture** : premier prototype implémenté et chaîne technique Phonon
   vérifiée avec Ollama 0.40.13. Restent comparaison avec Kokoro, confort d'écoute
   prolongée et reprise plus fine. La voix macOS est disponible.
3. **Accompagnement pédagogique** : premier prototype Ollama implémenté ;
   évaluer les réponses d'un vrai modèle, puis fournir un adaptateur payant,
   des références externes vérifiables et un suivi des exercices.
4. **Dictionnaire** : sélectionner un mot ou une expression, définition sourcée
   et vocabulaire personnel. Toujours souhaité, mais passe après voix et panneau.
5. **Statistiques** : historique quotidien, semaines/mois, régularité. Les
   totaux journaliers existent déjà ; leur présentation reste à développer.
6. **Documents complexes** : davantage de tests, tableaux, scans, ordre de
   lecture multicolonne. L'accès à la page originale reste la référence.
7. **Navigation proportionnelle** : pas de 1 %, 0,1 % ou 0,01 % à concevoir.
   **Non implémentée** : afficher le pourcentage actuel n'est pas proposer un
   saut ou une taille de passage en pourcentage.

## Règle de suivi

Pour chaque changement de comportement, mettre à jour le README si nécessaire,
ce tableau et le journal daté. Distinguer une fonction proposée, un prototype,
une validation automatique et un essai réel sur les machines de l'utilisateur.
Une modification locale n'est disponible sur l'autre machine qu'après commit,
push et récupération du dépôt ; ni la bibliothèque ni SQLite ne sont
synchronisées par Git.
