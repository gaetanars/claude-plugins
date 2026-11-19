---
schema_version: 3
id: 0001-fdm-plugin
title: Plugin fdm de conception de pièces imprimables
---

# Brief : Plugin fdm de conception de pièces imprimables

## Problème
La méthode de conception FDM (skill `fdm-design`, `tools/check.py`, `tools/slice.sh`, `tools/flatten_profiles.py`) vit dans un seul projet local, `~/3d-design`, hors git, figée sur une Bambu Lab A1 sous macOS (chemins, volume d'impression et profils en dur). Elle n'est réutilisable ni dans un autre projet ni par un autre propriétaire de Bambu ; le seul contournement est de copier le dossier, copie qui ne reçoit plus les correctifs.

## Valeur
Un plugin `fdm` installable depuis la marketplace `gaetanars` rend la méthode disponible dans tout projet, pour toute imprimante Bambu configurable (ADR-0001), avec une source unique des outils (ADR-0004).
Critère de succès : sur une machine propre (macOS), installer le plugin, lancer `fdm-setup` puis `fdm-profiles`, et `/fdm:design` produit le cube de calibration avec `OK`, un rendu PNG et une découpe donnant temps et poids, sans autre intervention.
Décisions issues de l'idéation :
- Le volume d'impression est lu dans le profil machine aplati (`printable_area`, `printable_height`) : une seule source de vérité ; `check` échoue avec un renvoi vers `fdm-profiles` si les profils manquent.
- `fdm-setup` crée le venv avec `python3` du PATH, surchargeable par une option, et refuse explicitement une version de Python hors de la plage supportée par les wheels OCP.
- `/fdm:design` vérifie d'abord la présence du venv et des profils et, s'ils manquent, propose `fdm-setup` / `fdm-profiles` et rien d'autre ; aucun hook de démarrage de session.
- `calibration_cube.py` est embarqué comme exemple de référence du skill.

## Non-objectifs
- Linux vérifié : Linux est pris en charge en best effort (chemin de Bambu Studio surchargeable par option, sans détection automatique), signalé « non vérifié » dans le README.
- Windows, autres slicers (Orca, PrusaSlicer), autres imprimantes que Bambu.
- Exécuter la chaîne CAO en CI (ADR-0002) : vérification locale par la pièce de calibration.
- Diffuser `usb_cable_organizer.py` (pièce personnelle).
- Modifier `~/3d-design` dans cette feature : la suppression de `tools/` et du skill local est une étape manuelle post-livraison (dossier hors git, donc irréversible), faite avec accord explicite une fois le critère de succès vérifié avec le plugin installé.

## Pistes écartées
- Ne rien construire et garder le skill de projet : pas de réutilisation ni de diffusion.
- Modèle de dépôt à copier par projet : copies divergentes, privées des correctifs (ADR-0004).
- Option de volume d'impression saisie à la main : risque d'incohérence avec le profil machine.
- Hook de démarrage de session pour vérifier l'installation : bruit dans tous les projets non 3D.
- uv/PEP 723, venv par projet, profils embarqués, abstraction multi-slicers : écartés par les ADR 0001 à 0003.

## Risques et inconnues
- Plage de versions de Python supportée par les wheels OCP (cadquery-ocp) pour build123d 0.13.0 : à vérifier pendant la spec.
- Comportement de la CLI Bambu Studio sous Linux (AppImage, Flatpak) : inconnu, non vérifiable faute de banc.
- Mécanisme d'options utilisateur des plugins (`userConfig`, `CLAUDE_PLUGIN_OPTION_*`) et disponibilité de `${CLAUDE_PLUGIN_DATA}` dans `bin/` et les skills : présents dans Claude Code 2.1.328, syntaxe à vérifier pendant la spec.
- Changement de comportement : `check` sortait toujours en succès ; `fdm-run` sortira en code non nul si un `check` signale `ISSUES` (pièces multi-parties : agrégation à préciser en spec).
- Évolution des profils Bambu Studio après mise à jour : régénération par `fdm-profiles`, signalée par `fdm-slice` en cas d'échec.
- Taille du venv (OCP, environ 300 Mo) et accès réseau requis au premier `fdm-setup`.
- Découpage probable en unités : (1) socle du plugin et `fdm-tools` + `fdm-setup`/`fdm-run` ; (2) `fdm-profiles` et `fdm-slice` ; (3) skill `fdm:design`, entrée marketplace, README. Aucune décision structurante nouvelle hors ADR 0001 à 0005 identifiée.
