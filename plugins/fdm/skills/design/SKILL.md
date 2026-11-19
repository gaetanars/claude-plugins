---
name: design
description: Conception de pièces imprimables en 3D (FDM, imprimante Bambu Lab) avec build123d. À utiliser pour toute demande de conception, modification, vérification ou découpe d'une pièce, boîtier, support, adaptateur, boîte, fixation ou objet à imprimer en 3D.
---

# Conception de pièces FDM

La conception se fait en code (build123d), jamais au jugé : toute affirmation sur les dimensions, l'ajustement ou l'imprimabilité vient d'une vérification, d'un rendu regardé ou d'une découpe.

## Prérequis (à vérifier en premier)

Vérifier la présence de `${CLAUDE_PLUGIN_DATA}/venv/bin/python` et des profils `${CLAUDE_PLUGIN_DATA}/profiles/machine.json`, `process.json` et `filament.json`.
S'il en manque, proposer uniquement la commande correspondante, puis ne rien faire d'autre tant qu'ils manquent :

- venv absent : `fdm-setup --data "${CLAUDE_PLUGIN_DATA}" --python "${user_config.python}"`
- profil absent (à relancer aussi après une mise à jour de Bambu Studio) : `fdm-profiles --data "${CLAUDE_PLUGIN_DATA}" --machine "${user_config.machine}" --process "${user_config.process}" --filament "${user_config.filament}" --profiles-dir "${user_config.bambu_profiles}"`

## Outils

Dans le dossier du projet (`parts/` pour les pièces, `out/` pour les sorties) :

- `fdm-run --data "${CLAUDE_PLUGIN_DATA}" parts/<nom>.py` lance la pièce dans le venv. Elle est exécutée par `runpy` : `sys.path[0]` est la racine du projet (imports relatifs à la racine, pas à `parts/`). Chaque pièce imprimable appelle `check()` ; sans `check()`, la sortie est 1.
- `from fdm_tools import check` puis `check(part, "out/<nom>")` exporte STEP, STL et PNG (`out/<nom>.png`), affiche dimensions, volume, surplombs, puis `OK` ou `ISSUES` (dont le dépassement du volume d'impression de la machine).
- `fdm-slice --data "${CLAUDE_PLUGIN_DATA}" --bambu-studio "${user_config.bambu_studio}" out/<nom>.stl` découpe avec Bambu Studio : temps, poids, et chemin de `out/slice_<nom>/<nom>.3mf`.
- Pièce de référence, à copier pour l'en-tête et l'import : `${CLAUDE_PLUGIN_ROOT}/lib/fdm_tools/examples/calibration_cube.py`.

## Déroulé

1. **Clarifier avant de modéliser.** Fonction, dimensions clés (mesurées au pied à coulisse si la pièce doit s'ajuster), pièces en contact, charges, orientation d'impression, esthétique. Ne poser que les questions qui bloquent ; pour le reste, énoncer les hypothèses avec une valeur par défaut recommandée.
2. **Esquisser l'approche en quelques lignes** : découpage, orientation, évitement des supports, jeux utilisés. Faire valider une conception non triviale.
3. **Écrire `parts/<nom_snake>.py`** :
   - toutes les dimensions en paramètres EN_MAJUSCULES en tête, en mm, commentées ;
   - dimensions dérivées calculées, pas de valeur magique dans la géométrie ;
   - la pièce repose sur Z=0 dans son orientation d'impression (`Align.MIN` sur Z) ;
   - plusieurs pièces : un `check()` par pièce imprimable, plus un contrôle d'interférence d'assemblage avec trimesh/manifold si elles s'emboîtent ;
   - terminer par `check(part, "out/<nom>")`.
4. **Lancer** avec `fdm-run`. Corriger tout `ISSUES` avant d'aller plus loin.
5. **Regarder le rendu** : lire `out/<nom>.png` et vérifier que la forme correspond à l'intention (trous bien placés, détails sur la bonne face, rien d'absent).
6. **Découper** avec `fdm-slice` pour le temps et le poids.
7. **Rendre compte** en français, de façon concise : ce qui a été construit, dimensions clés, orientation, supports ou non, temps et poids, hypothèses, ce qui n'est PAS vérifié. Donner le chemin du `.3mf` à ouvrir dans Bambu Studio.
8. **Itérer** sur les paramètres selon les retours ou les mesures d'une impression d'essai.

## Règles FDM

Valeurs par défaut pour une buse 0.4 et du PLA en couches de 0.2 mm. Le volume d'impression n'est pas listé ici : il vient de la sortie de `check()`.

| Sujet | Valeur par défaut |
|---|---|
| Paroi minimale | 0.8 mm (2 périmètres) ; viser 1.2 à 2 mm pour une paroi structurelle |
| Détail minimal / texte | 0.8 mm de large ; texte en relief ≥ 0.6 mm de haut, police ≥ 5 mm |
| Plancher / plafond | ≥ 0.8 mm (4 couches) |
| Surplomb | ≤ 45° sans support ; chanfreiner plutôt qu'arrondir les faces tournées vers le bas |
| Ponts | ≤ ~20 mm sans support |
| Trous horizontaux | en goutte ou à sommet plat si Ø > 6 mm, ou accepter un léger affaissement |
| Arêtes sur le plateau | chanfrein de 0.4 à 0.6 mm sur les arêtes du bas (pied d'éléphant) ; jamais de congé |
| Compensation des trous | les trous sortent ~0.1 à 0.2 mm trop petits : ajouter 0.2 mm au Ø |
| Jeu, ajustement serré | 0.1 mm par côté |
| Jeu, glissant | 0.2 mm par côté |
| Jeu, libre | 0.3 à 0.4 mm par côté |
| Pièces imprimées en place | jeu ≥ 0.3 mm |
| Vis (taraudage direct dans le PLA) | M3 : trou Ø2.5 ; passage M3 Ø3.4 ; insert chauffé M3 Ø4.0 à 4.2, profondeur 5 à 6 mm |
| Logement d'écrou | M3 hexagonal, 5.5 mm sur plats : poche de 5.8 à 6.0 mm |
| Résistance | les couches sont faibles en Z : orienter pour que les efforts suivent les couches |
| Clips | languette en XY, longueur ≥ 5× l'épaisseur |

Si l'utilisateur fournit des valeurs calibrées par des impressions d'essai, les utiliser à la place de ces valeurs par défaut.

## Conseils build123d

- Le mode builder (`with BuildPart() as p:`) est le style par défaut ; `p.part` est le solide.
- Sélectionner arêtes et faces avec `p.edges().group_by(Axis.Z)[-1]` (haut), `[0]` (bas), `.filter_by(Axis.Z)` (arêtes verticales), `.sort_by(...)`.
- Appliquer `fillet` et `chamfer` après toutes les booléennes qui touchent ces arêtes ; si un congé échoue, réduire le rayon ou passer à un chanfrein.
- `Mode.SUBTRACT` pour trous et poches, `Locations`, `GridLocations` et `PolarLocations` pour les motifs.
- Vérifier les dimensions clés par le calcul (`part.bounding_box()`, `part.volume`) plutôt que de se fier au code.
