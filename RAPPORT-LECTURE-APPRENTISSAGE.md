# Faire évoluer Reader vers une lecture assidue et un apprentissage durable

Compte rendu de recherche et propositions fonctionnelles — 27 octobre 2026.

**Statut : document de recherche et de conception.** Les fonctions proposées
ci-dessous ne sont pas encore implémentées. L'état du logiciel décrit ici
correspond au commit `beb5257`. Ce rapport ne modifie pas le lecteur.

## 1. Objet et orientation

L'objectif est d'étudier comment un lecteur de terminal peut aider une personne
à lire plus régulièrement, mieux comprendre ses lectures et en tirer des
connaissances durables. Trois dimensions doivent être distinguées :

| Dimension | Résultat recherché | Indication observable |
| --- | --- | --- |
| Assiduité | Revenir régulièrement à une lecture choisie | Séances réalisées et reprise facile après une interruption |
| Performance | Comprendre à un rythme adapté au texte | Explication correcte, retour volontaire sur les difficultés |
| Connaissance | Retenir, relier et utiliser les idées | Restitution différée, exemple nouveau et confrontation des sources |

L'orientation proposée est une boucle : **lire → restituer → vérifier → revoir
→ relier à d'autres connaissances**. Reader peut en faciliter les étapes en
conservant son fonctionnement local, son interface de terminal et une lecture
libre accessible à tout moment.

## 2. Méthode et portée de la recherche

Cette synthèse ciblée s'appuie sur huit publications relatives aux habitudes,
au suivi des objectifs, à la lecture, au rappel actif, à l'espacement, à
l'auto-explication et à l'évaluation des sources. Les références sont données
près des constats et réunies dans la bibliographie.

Il ne s'agit pas d'une revue systématique : aucun protocole exhaustif de
recherche, sélection et évaluation du risque de biais n'a été conduit. La
consultation porte sur les résumés scientifiques et présentations des éditeurs,
ainsi que sur le texte intégral lorsqu'il est accessible. Les effets chiffrés
rapportés ne constituent pas des estimations de l'efficacité future de Reader.

Les propositions fonctionnelles sont des adaptations de ces travaux. Une part
importante des résultats concerne des élèves ou étudiants dans des situations
éducatives. Leur transfert vers un adulte lisant seul, vers tous les genres de
livres ou vers une interface de terminal doit être évalué.

## 3. Point de départ : ce que Reader permet déjà

| Fonction existante | Apport possible | Limite actuelle |
| --- | --- | --- |
| Reprise automatique par fichier | Retrouver facilement le passage en cours | Il faut encore fournir le fichier à ouvrir |
| Passages de lignes ou de mots | Choisir la quantité de texte visible | Les limites des passages ne suivent pas nécessairement le sens |
| Avance automatique réglable | Installer un rythme d'affichage | La vitesse choisie ne mesure pas la compréhension |
| Retour au passage précédent et pause | Reconsidérer un passage | Pas de marque-page ni d'annotation durable |
| Aperçu Markdown et extraction PDF | Réunir plusieurs formats dans le terminal | Les références Markdown sont masquées dans l'aperçu |
| Colonne centrée, aide et réglage en direct | Adapter la présentation à son confort | Aucun bénéfice cognitif propre à ce design n'a été démontré |
| Historique SQLite et pourcentage | Retrouver les documents parcourus | Pas de journal de séances ni de mesure d'apprentissage |

La base actuelle conserve le chemin absolu, une empreinte SHA-256 du texte
normalisé, la position, la longueur et la date de sauvegarde. Elle se trouve
par défaut dans `~/.local/state/reader/reading.sqlite3`. Le chemin est la clé
primaire ; un déplacement crée une nouvelle lecture et un texte modifié reprend
au début. Les préférences ne sont pas mémorisées par document.

**La barre mesure une position dans le texte.** Elle ne prouve ni que le passage
a été lu attentivement, ni qu'il a été compris ou retenu. Le temps d'affichage
et la vitesse programmée doivent conserver la même prudence d'interprétation.

## 4. Enseignements de la recherche

### 4.1. Installer un contexte régulier

Lally et ses collègues ont suivi des personnes répétant une activité quotidienne
dans un contexte stable. Le développement de l'automaticité variait fortement
selon les participants ; manquer une occasion ne compromettait pas matériellement
le processus observé. Les activités étudiées n'étaient pas des séances de lecture.
Cette étude soutient l'intérêt d'un contexte régulier, sans établir de durée
universelle pour devenir lecteur assidu. [Lally et al., 2010](https://onlinelibrary.wiley.com/doi/10.1002/ejsp.674)

**Application proposée :** choisir un rendez-vous lié à une activité existante,
par exemple quelques minutes après le café, et retrouver immédiatement son
document. Une interruption ne devrait pas effacer les progrès présentés par
l'outil. Une série de jours consécutifs peut être informative, mais ne devrait
pas devenir l'unique représentation de la régularité.

### 4.2. Rendre les progrès observables

Harkin et ses collègues ont réuni 138 études expérimentales, soit 19 951
participants. Les interventions encourageant le suivi des progrès favorisaient
en moyenne l'atteinte des objectifs. Les domaines étaient variés ; ce résultat
ne valide pas un tableau de bord particulier pour la lecture. [Harkin et al., 2016](https://pubmed.ncbi.nlm.nih.gov/26479070/)

**Application proposée :** un objectif personnel et un bilan hebdomadaire
compréhensible : séances réalisées, lectures poursuivies, temps de session
estimé. Le bilan doit distinguer un lecteur ouvert d'une activité effectivement
confirmée par l'utilisateur. Aucune surveillance de l'attention n'est nécessaire.

### 4.3. Adapter la vitesse à la compréhension

La synthèse de Rayner et ses collègues décrit un compromis entre vitesse et
compréhension. Elle souligne que les retours en arrière peuvent soutenir la
compréhension et que les compétences linguistiques, notamment le vocabulaire,
contribuent à une lecture efficace. Une forte augmentation de vitesse ne
garantit pas le maintien d'une compréhension approfondie. [Rayner et al., 2016](https://journals.sagepub.com/doi/10.1177/1529100615623267)

**Application proposée :** garder la pause et le retour faciles, distinguer
survol et étude approfondie, et laisser l'utilisateur ralentir selon le texte.
Le mode par passages répond à sa préférence de concentration. Le choix de
80 mots, le découpage par phrases et les pauses en fin de paragraphe restent
des paramètres de conception à tester, sans taille optimale établie ici.

### 4.4. Restituer avant de consulter la réponse

La revue de Dunlosky et ses collègues attribue une forte utilité aux tests
d'entraînement et à la pratique distribuée. Elle attribue une utilité plus
limitée à certaines pratiques courantes comme le surlignage ou la relecture
lorsqu'elles sont considérées comme techniques générales d'apprentissage.
Cela ne signifie pas qu'un surlignage ou une relecture soit toujours inutile.
[Dunlosky et al., 2013](https://www.psychologicalscience.org/publications/journals/pspi/learning-techniques.html)

La méta-analyse de Yang et ses collègues porte sur 222 études et 48 478 élèves
ou étudiants. Les interrogations améliorent en moyenne les résultats scolaires ;
l'ampleur du bénéfice varie notamment avec le retour correctif, les répétitions
et le contexte. [Yang et al., 2021](https://pubmed.ncbi.nlm.nih.gov/33683913/)

**Application proposée :** masquer temporairement une section, demander une
restitution, puis permettre une comparaison avec le passage source. L'utilisateur
doit produire une réponse avant de révéler le texte. Une note copiée dans un
carnet ne remplace pas cette activité.

### 4.5. Revoir à distance

Cepeda et ses collègues ont synthétisé 317 expériences sur la pratique distribuée.
Leur analyse relie l'espacement utile à l'horizon de rétention : l'intervalle
favorable dépend aussi du moment auquel on souhaite encore se souvenir.
Elle ne définit pas un calendrier unique applicable à toutes les lectures.
[Cepeda et al., 2006](https://pubmed.ncbi.nlm.nih.gov/16719566/)

**Application proposée :** conserver quelques questions et les reproposer à
distance, avec rappel avant révélation du passage. Un calendrier initial au
lendemain, quelques jours après et la semaine suivante serait un point de départ
ajustable. Le nombre de révisions doit rester compatible avec le temps disponible.

### 4.6. Expliquer et construire des liens

La méta-analyse de Bisra et ses collègues rassemble 64 rapports de recherche.
Elle observe un bénéfice moyen des invitations à produire ses propres
explications, dans diverses conditions d'apprentissage. Ce résultat ne prouve
pas que toute consigne libre ou toute note améliore automatiquement la lecture.
[Bisra et al., 2018](https://link.springer.com/article/10.1007/s10648-018-9434-x)

**Application proposée :** demander ponctuellement une explication, un exemple
ou une relation avec une lecture antérieure. Les questions devraient porter
sur le sens : « Pourquoi ? », « Dans quel cas ? », « À quelle idée cela se
relie-t-il ? ». Elles doivent pouvoir être ignorées, notamment en lecture de loisir.

### 4.7. Examiner les sources

Breakstone et ses collègues ont étudié un enseignement en ligne de la lecture
latérale : quitter une source inconnue pour consulter des informations externes
sur sa crédibilité. Les étudiants ont amélioré leurs évaluations entre le
prétest et le post-test. Ce dispositif pédagogique ne démontre pas l'effet
d'une simple commande de consultation dans Reader. [Breakstone et al., 2021](https://misinforeview.hks.harvard.edu/article/lateral-reading-college-students-learn-to-critically-evaluate-internet-sources-in-an-online-course/)

**Application proposée :** rendre les références accessibles, conserver l'auteur,
la date et la provenance quand ils sont connus, puis faciliter la comparaison
entre plusieurs textes. Un nom prestigieux, une belle présentation ou un nombre
de références ne devraient pas être convertis en score automatique de vérité.

## 5. Fonctions proposées et critères d'acceptation

Toutes les fonctions de cette section sont **à développer**. Les priorités
expriment un ordre de réalisation proposé, pas une décision d'implémentation.

### F01 — Reprendre le dernier document

**Priorité 1.** Ouvrir la dernière lecture lorsque la commande ne reçoit aucun
fichier ; proposer une bibliothèque si cette lecture n'est plus disponible.

Critères d'acceptation : retrouver le passage sauvegardé, signaler un fichier
absent sans perdre son historique, permettre de choisir un autre document et
garder les commandes explicites actuelles valables.

### F02 — Mémoriser les préférences

**Priorité 1.** Conserver par document le mode, la taille du passage et la vitesse.
Une préférence générale pourrait servir de valeur initiale.

Ordre proposé : option explicitement fournie en ligne de commande, préférence
du document, puis valeur générale. Un changement en cours de session doit
pouvoir être retrouvé à la prochaine ouverture. La taille de police reste
réglée dans le terminal.

### F03 — Objectif personnel et journal de séances

**Priorité 1.** Permettre un objectif simple, par exemple dix minutes, et un bilan
hebdomadaire. Le seuil reste choisi par l'utilisateur.

Critères d'acceptation : distinguer lecture et pause, nommer les durées comme
estimations, permettre de corriger une séance oubliée ouverte, conserver les
semaines précédentes après un jour manqué et rendre l'objectif désactivable.

### F04 — Notes, difficultés et marque-pages

**Priorité 2.** Attacher une note à un passage : idée importante, question, mot
inconnu, difficulté ou exemple personnel. Retrouver ce passage depuis la note.

Chaque annotation doit garder le document, son contexte et une empreinte de
version. Si le texte change, signaler l'ancrage à vérifier plutôt que rattacher
silencieusement une note au mauvais extrait. Un export Markdown doit permettre
de relire ses notes sans Reader.

### F05 — Restitution avec texte masqué

**Priorité 2.** À une limite choisie par le lecteur, proposer de restituer une
idée avant de retrouver le texte. Commencer avec quelques consignes génériques
et des questions rédigées par l'utilisateur, sans dépendance à une IA.

Exemple d'écran proposé, non encore disponible :

```text
Qu'avez-vous retenu de cette section ?

Idée principale :
Exemple personnel :
Point à vérifier :

Après votre réponse : retrouver le passage et corriger votre note.
```

Critères d'acceptation : pause du défilement pendant l'exercice, sauvegarde du
brouillon, révélation volontaire du passage, possibilité de compléter la réponse
et retour à la lecture sans déplacement involontaire. Une auto-évaluation doit
être présentée comme telle, sans score de maîtrise déduit du seul ressenti.

### F06 — Passages suivant la structure du texte

**Priorité 2, expérimentation.** Proposer des passages par phrases ou paragraphes,
ainsi que des pauses aux changements de section. Garder le découpage actuel
par mots ou lignes disponible.

Le découpage doit tenir compte des abréviations, listes, blocs de code et titres.
Un paragraphe trop long doit rester consultable sur plusieurs écrans. La qualité
de la segmentation des PDF dépendra aussi de l'extraction : colonnes et césures
peuvent perturber la structure. Comparer ce mode aux lots fixes avant d'en faire
un réglage recommandé.

### F07 — Révisions espacées

**Priorité 3.** Créer une file locale de questions à revoir, liée aux notes et
aux passages sources. Chaque révision commence par une tentative de rappel.

Critères d'acceptation : consulter les échéances, reporter ou retirer une question,
révéler la source après réponse, consigner la tentative et limiter la charge
quotidienne. Les premiers intervalles seront des réglages pratiques ajustables,
avec leur caractère expérimental expliqué.

### F08 — Références et contexte accessibles

**Priorité 2.** Garder un aperçu épuré et permettre d'afficher sur demande les
références, liens et informations de provenance associés au passage.

Le mode source `-R` existe déjà ; une consultation contextualisée serait plus
directe. Les liens ne doivent pas être perdus lors de l'export d'une note. La
consultation d'une ressource distante doit rester une action explicite, sans
connexion requise pour la lecture ordinaire.

### F09 — Relier les idées et organiser un parcours

**Priorité 4.** Relier une note à une autre avec une relation explicite : complète,
illustre, contredit ou applique. Une fiche d'idée peut contenir une explication,
un exemple, une limite, une question ouverte et sa source.

Un parcours thématique pourrait organiser des lectures introductives puis plus
approfondies, avec comparaison de points de vue. Ces relations sont des aides à
la réflexion choisies par le lecteur ; leur nombre ne mesure pas son expertise.

### F10 — Bilan distinguant activité et apprentissage

**Priorité 3.** Présenter séparément les documents parcourus, les séances et les
tentatives de restitution. Conserver la barre actuelle comme repère de position.

Critères d'acceptation : aucun passage affiché n'est automatiquement déclaré
compris ; les réponses évaluées, les auto-évaluations et les notes restent
identifiables. L'outil ne déduit pas un niveau de connaissance général d'un
pourcentage de document ou d'un temps d'affichage.

## 6. Parcours quotidien proposé

Exemple de séance de quinze minutes, à adapter à l'envie et au texte :

| Moment | Activité | Fonction concernée |
| --- | --- | --- |
| Deux premières minutes | Retrouver une idée de la séance précédente, puis vérifier | F05, F07 |
| Dix minutes suivantes | Lire à son rythme, marquer une difficulté si nécessaire | Fonctions actuelles, F04, F06 |
| Trois dernières minutes | Expliquer une idée, donner un exemple et choisir ce qui mérite une révision | F04, F05, F09 |

Cette répartition constitue une proposition pratique, pas un dosage optimal
validé. Une séance plus courte doit rester utile. Pour un roman ou une lecture
de détente, toutes les sollicitations pédagogiques pourront être désactivées.

Une fiche de fin de séance pourrait répondre à quatre questions :

1. Quelle idée puis-je expliquer sans relire ?
2. Quel exemple montre que je l'ai comprise ?
3. Qu'est-ce qui reste confus ou mérite vérification ?
4. Où retrouver la source et quand revoir cette idée ?

## 7. Principes d'interface et de données

### Une lecture qui garde la priorité

Préserver la colonne centrée, le fond du terminal, l'aide accessible et les
raccourcis existants. Les nouvelles sollicitations doivent être facultatives
et placées à des limites choisies, sans interrompre chaque petit passage.
L'utilisateur doit pouvoir consulter, annoter ou réfléchir aussi longtemps
qu'il le souhaite, puis revenir exactement à sa lecture.

Les durées de concentration, les couleurs et le découpage sont des réglages de
confort. Leur présentation ne doit pas promettre un entraînement cognitif dont
l'efficacité spécifique n'a pas été mesurée.

### Une mémoire locale extensible

SQLite peut rester le support principal. Un schéma futur pourrait ajouter :

| Donnée proposée | Contenu |
| --- | --- |
| Préférences | Mode, quantité affichée, vitesse et choix de lecture libre |
| Séances | Début, fin, pauses connues et correction éventuelle |
| Annotations | Note, type, extrait, ancrage et version du texte |
| Questions | Consigne, éléments de réponse et passage de référence |
| Révisions | Échéance, tentative, résultat déclaré et prochain rendez-vous |
| Liens entre idées | Notes concernées et relation choisie |

Une migration doit préserver les positions existantes. La création du journal
ne doit pas inventer des séances à partir des anciennes dates de sauvegarde.
Les notes personnelles et les bases restent exclues de Git par défaut.

### Portabilité entre machines

Le chemin absolu actuel limite la reprise après déplacement. Avant d'ajouter une
synchronisation, définir comment identifier un document et ses versions. Un
identifiant interne stable, associé à des chemins et à des empreintes, pourrait
faciliter une importation future. Deux copies identiques peuvent toutefois
représenter deux lectures différentes : leur fusion ne doit pas être implicite.

Prévoir un export lisible et une sauvegarde restaurable avant une synchronisation
complexe. Le clonage du code Git continuera à être distinct du transfert de la
mémoire personnelle. Ces évolutions de stockage sont des propositions techniques,
sans bénéfice pédagogique directement établi.

### Place éventuelle de l'IA

Le premier ensemble de fonctions peut fonctionner hors ligne sans IA. Une aide
ultérieure pourrait suggérer des questions ou des liens, à partir d'un passage
explicitement sélectionné. Les suggestions devraient conserver leur source et
rester modifiables. Une question générée ou une correction automatique peut être
erronée ; elle ne doit pas devenir une preuve de maîtrise ni remplacer la
vérification du texte. Aucun envoi de documents n'est nécessaire au socle proposé.

## 8. Ordre de développement recommandé

| Étape | Livrable | Condition pour poursuivre |
| --- | --- | --- |
| 1 — Retour facile | F01, F02, F03 : reprise, préférences, objectif et séances | La lecture démarre simplement et les sauvegardes existantes sont préservées |
| 2 — Lecture active | F04, F05, F08 ; essai distinct de F06 | Les notes sont retrouvables et les exercices ne gênent pas la lecture libre |
| 3 — Entretien | F07, F10 : révisions et bilan | Le rappel différé peut être observé sans charge de révision excessive |
| 4 — Connaissances reliées | F09 : liens et parcours | Les relations aident effectivement à expliquer ou comparer des idées |

Le premier objectif produit serait donc : **retrouver sa lecture sans effort,
garder une idée et pouvoir la retrouver avec sa source**. Les fonctions de
révision dépendront ensuite de cette base. Aucun calendrier de livraison n'est
fixé par ce rapport.

## 9. Comment évaluer les bénéfices

Commencer par une expérimentation personnelle limitée, par exemple une semaine
d'observation du lecteur actuel puis trois semaines avec quelques fonctions
ajoutées progressivement. Ce calendrier est une organisation pratique ; une
comparaison avant/après sur une seule personne ne permet pas d'attribuer avec
certitude les changements au logiciel.

| Dimension | Mesure proposée | Limite à garder visible |
| --- | --- | --- |
| Régularité | Séances réalisées par rapport à l'objectif personnel | Dépend aussi des contraintes de vie et de l'intérêt du texte |
| Facilité de reprise | Difficultés signalées et étapes nécessaires pour relire | Une durée de démarrage faible ne mesure pas l'engagement |
| Compréhension | Explication et exemple évalués à l'aide du passage | Les questions doivent être pertinentes et les critères explicites |
| Rétention | Restitution après un délai fixé à l'avance | Reposer la même question entraîne aussi cette réponse particulière |
| Réutilisation | Application à une situation ou une question nouvelle | Une réussite locale ne prouve pas une expertise générale |
| Confort | Fatigue, gêne ou plaisir déclarés ; usage des pauses | Ces observations subjectives sont utiles sans être des tests cognitifs |

Pour comparer les modes d'affichage, choisir des textes de difficulté comparable,
équilibrer autant que possible leur ordre et consacrer un temps similaire aux
conditions. Examiner compréhension et restitution différée autant que vitesse.
Un essai sur davantage de personnes demanderait un protocole plus structuré.

Des critères d'acceptation techniques compléteront ces observations : sauvegarde
fiable, restauration après interruption, respect des préférences explicites,
ancrage correct des notes, migrations sans perte, export et fonctionnement dans
les petits terminaux. Les tests actuels du logiciel ne constituent pas une
validation pédagogique des futures fonctions.

## 10. Points de vigilance et questions ouvertes

- **Charge d'usage :** combien de notes ou questions le lecteur souhaite-t-il
  réellement produire sans perdre l'envie de lire ?
- **Nature des textes :** distinguer lecture de loisir, découverte d'un sujet,
  documentation technique et apprentissage approfondi.
- **Découpage :** tester les paragraphes et les lots fixes ; aucun nombre de mots
  idéal n'a été établi par cette recherche.
- **Mesure :** garder distincts position, affichage, attention déclarée,
  compréhension et rappel différé.
- **Qualité des questions :** vérifier leurs réponses dans la source et inclure
  parfois un exemple ou une inférence, au-delà de la restitution littérale.
- **Révisions :** éviter qu'une accumulation de cartes rende le retour au lecteur
  décourageant ; laisser choisir ce qui mérite d'être conservé.
- **Accès aux sources :** préserver une présentation sobre tout en rendant les
  preuves, références et désaccords consultables.
- **Évolution de la mémoire :** décider du comportement lors du déplacement ou
  de la modification d'un fichier avant de généraliser les annotations.

La recherche soutient plusieurs mécanismes d'apprentissage. La combinaison
proposée, son interface et ses réglages demeurent des hypothèses de produit à
éprouver auprès de l'utilisateur.

## 11. Bibliographie

Les liens renvoient aux publications, à leurs notices scientifiques ou à la
présentation de la revue éditrice. Consultation : 27 octobre 2026.

1. Lally, P., van Jaarsveld, C. H. M., Potts, H. W. W. et Wardle, J. (2010).
   [How are habits formed: Modelling habit formation in the real world](https://onlinelibrary.wiley.com/doi/10.1002/ejsp.674).
   *European Journal of Social Psychology*. DOI : `10.1002/ejsp.674`.
2. Harkin, B. et al. (2016).
   [Does monitoring goal progress promote goal attainment? A meta-analysis of the experimental evidence](https://pubmed.ncbi.nlm.nih.gov/26479070/).
   *Psychological Bulletin*. DOI : `10.1037/bul0000025`.
3. Rayner, K., Schotter, E. R., Masson, M. E. J., Potter, M. C. et Treiman, R. (2016).
   [So Much to Read, So Little Time: How Do We Read, and Can Speed Reading Help?](https://journals.sagepub.com/doi/10.1177/1529100615623267).
   *Psychological Science in the Public Interest*. DOI : `10.1177/1529100615623267`.
4. Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J. et Willingham, D. T. (2013).
   [Improving Students' Learning With Effective Learning Techniques: Promising Directions From Cognitive and Educational Psychology](https://www.psychologicalscience.org/publications/journals/pspi/learning-techniques.html).
   *Psychological Science in the Public Interest*. DOI : `10.1177/1529100612453266`.
5. Yang, C., Luo, L., Vadillo, M. A., Yu, R. et Shanks, D. R. (2021).
   [Testing (quizzing) boosts classroom learning: A systematic and meta-analytic review](https://pubmed.ncbi.nlm.nih.gov/33683913/).
   *Psychological Bulletin*. DOI : `10.1037/bul0000309`.
6. Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T. et Rohrer, D. (2006).
   [Distributed practice in verbal recall tasks: A review and quantitative synthesis](https://pubmed.ncbi.nlm.nih.gov/16719566/).
   *Psychological Bulletin*. DOI : `10.1037/0033-2909.132.3.354`.
7. Bisra, K., Liu, Q., Nesbit, J. C., Salimi, F. et Winne, P. H. (2018).
   [Inducing Self-Explanation: a Meta-Analysis](https://link.springer.com/article/10.1007/s10648-018-9434-x).
   *Educational Psychology Review*. DOI : `10.1007/s10648-018-9434-x`.
8. Breakstone, J., Smith, M., Connors, P., Ortega, T., Kerr, D. et Wineburg, S. (2021).
   [Lateral reading: College students learn to critically evaluate internet sources in an online course](https://misinforeview.hks.harvard.edu/article/lateral-reading-college-students-learn-to-critically-evaluate-internet-sources-in-an-online-course/).
   *Harvard Kennedy School Misinformation Review*.
