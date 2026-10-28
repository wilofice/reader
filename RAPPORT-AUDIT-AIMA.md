# Audit du livre Artificial Intelligence: A Modern Approach

## Conclusion

L'audit complet fonctionne sur les **1 166 pages** de la quatrième édition
globale de Russell et Norvig. Aucun échec de page après correction de l'import
XML. Cette méthode OpenCV ne justifie pas de remplacer le détecteur Poppler :
ses deux alertes supplémentaires correspondent aux bandeaux décoratifs des
annexes. Des formules restent manquées par les deux méthodes.

Le lecteur conserve donc son fonctionnement actuel. Le prochain axe utile
est le repérage des formules, en complément des images et tracés.

## Protocole et résultats du 28 octobre 2026

Document téléchargé depuis la bibliothèque de l'université d'État d'Erevan.
SHA-256 : `ca4fca8dd88929646e06f584ae5ce4d84c8272de0f4c3b8abd55118b80152cfa`.
Même protocole que le [premier audit](RAPPORT-DETECTION-VISUELLE.md) :
analyse structurelle Poppler et OpenCV 5.0.0 sur rendu maximal de 1600 pixels,
CPU, un fil OpenCV, macOS 26.2 ARM64. Aucun modèle spécialisé n'a été évalué.

| Signalement structurel par page | Nombre |
|---|---:|
| Poppler et OpenCV | 335 |
| Poppler seul | 139 |
| OpenCV seul | 2 |
| Aucun des deux | 690 |
| Erreurs de page | 0 |

Poppler signale donc 474 pages, OpenCV 337. Ces nombres ne mesurent pas la
qualité : une décoration peut déclencher une alerte et une absence d'alerte
peut masquer des formules. Les simples mentions textuelles de figures ne sont
pas comptées comme détections structurelles.

La passe mesurée a pris **523,54 secondes**, environ 8 min 44 s, hors extraction
initiale et galerie : 100,63 s pour Poppler, 422,29 s pour le rendu puis OpenCV.
Ce sont des temps locaux observés, avec d'autres vérifications en parallèle ;
ils ne constituent pas un benchmark matériel ni un temps OpenCV isolé.

## Défaut d'extraction découvert et corrigé

Le premier lancement échouait sur le XML produit par `pdftotext -bbox`.
Certaines polices mathématiques génèrent des caractères de contrôle interdits
dans XML 1.0. L'import exclut désormais uniquement ces caractères, en gardant
les rectangles de tous les mots. **277 caractères** ont été exclus dans cet
export ; le nombre est consigné dans le manifeste et le résumé générés.

Le PDF original reste intact. Cela rend l'export exploitable, sans reconstituer
les symboles perdus. Un test reproduit le défaut et vérifie que le rectangle
du mot est conservé. Les **61 tests** de la suite passent.

## Contrôle visuel et exemples conservés

L'assistant a examiné 24 pages sélectionnées entre accords et désaccords, puis
3 pages ciblées pour leur richesse en symboles : 245, 293 et 410. Des vues
détaillées complètent les planches de contrôle. Les annotations restent
séparées des résultats automatiques, avec des cas marqués incertains.

- **1074 et 1081**, seules alertes OpenCV supplémentaires : les rectangles
  détectés entourent les bandeaux des annexes, pas les formules ou la grammaire
  présentes plus bas. Il faut distinguer une page contenant du contenu utile
  d'une localisation pertinente de ce contenu.
- **293 et 633** : formules affichées visibles, mais aucune alerte structurelle
  des deux méthodes. Ce sont des omissions confirmées sur ces exemples.
- **245, 410, 440, 463 et 784** : formules visibles, Poppler les signale,
  cette méthode OpenCV ne les signale pas.
- **56, 182, 452, 782, 912, 943 et 978** : exemples de tableau, échiquier,
  graphes, schémas ou photographies signalés par les deux méthodes.
- **403** : une alerte Poppler correspond à une mise en titre décorative,
  sans figure utile relevée au contrôle.

Les 690 pages sans signal ne sont donc **pas** 690 pages sans contenu complexe.
L'échantillon n'est pas une annotation exhaustive du livre : aucune précision
ni aucun rappel global ne sont annoncés.

## Prochaine expérience

Conserver le repérage des images intégrées et compléter l'index avec un
détecteur de formules. Tester d'abord des indices de symboles, de police et de
mise en page sur les exemples conservés, sans masquer toutes les expressions
mathématiques comme le fait ce prototype OpenCV. Comparer ensuite, si nécessaire,
un modèle de mise en page spécialisé sur les mêmes cas, sans explication des
figures ni service obligatoire.

Inventaires, galerie locale, annotations et rendus sont dans
`output/pdf/visual-audit/<empreinte>/`, exclus de Git. La progression SQLite
n'est jamais ouverte par l'audit. L'environnement OpenCV reste facultatif.
