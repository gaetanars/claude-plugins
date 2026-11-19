---
schema_version: 3
id: 0002-fdm-check-run
title: Vérification des pièces fdm (fdm_tools.check, fdm-run, cube de calibration)
track: feature
status: accepted
depends_on: [0001-fdm-plugin]
---

# Vérification des pièces fdm (fdm_tools.check, fdm-run, cube de calibration)

## Contexte
Deuxième des trois unités du plugin `fdm` (voir `docs/features/0001-fdm-plugin/brief.md`) ; l'unité 1 (venv par `fdm-setup`, profils aplatis par `fdm-profiles`) est fusionnée. Elle porte `tools/check.py` de `~/3d-design` dans le plugin, sous forme de bibliothèque `fdm_tools`, et ajoute le lanceur `fdm-run` (ADR-0004) qui exécute une pièce du projet de l'utilisateur avec le Python du venv (ADR-0002).
Valeur : toute pièce `parts/<nom>.py` d'un projet quelconque est exportée (STEP, STL), contrôlée contre le volume d'impression de l'imprimante configurée et rendue en PNG, et `fdm-run` sort en code non nul dès qu'un contrôle signale un problème.

## Périmètre
- `plugins/fdm/lib/fdm_tools/__init__.py` : expose `check` (`from fdm_tools import check`).
- `plugins/fdm/lib/fdm_tools/check.py` : portage de `~/3d-design/tools/check.py` (export, contrôles, rendu 4 vues), volume d'impression et densité lus dans les profils aplatis, registre des résultats.
- `plugins/fdm/lib/fdm_tools/run.py` : runner `python -m fdm_tools.run <pièce> [args…]`, agrégation des verdicts en code de sortie.
- `plugins/fdm/lib/fdm_tools/examples/calibration_cube.py` : cube de 20 mm percé de 5 mm, chanfrein supérieur de 1 mm, exporté vers `out/calibration_cube`.
- `plugins/fdm/bin/fdm-run` : lanceur en bibliothèque standard.
- `plugin.json` : version `0.2.0`, description toujours « Préversion », mentionnant la vérification des pièces.
- Tests hors ligne dans `tests/`.

## Hors périmètre
- `fdm-slice`, skill `fdm:design`, README du plugin, version 1.0.0 (unité 3).
- Exécution réelle de build123d, trimesh ou du venv dans les tests et la CI (ADR-0002).
- Nouveaux contrôles (épaisseur minimale de paroi, position dans le plateau, zones exclues) : seuls les contrôles d'origine sont portés.
- `usb_cable_organizer.py` ; toute modification de `~/3d-design`.

## Critères d'acceptation
- [ ] CA-1: `python3 -m unittest discover -s tests -t .` passe (dont `test_files` : nouveaux `.py` compilables, `fdm-run` exécutable avec shebang ; `test_cli_validate` ; `test_plugins` avec la version `0.2.0`).
- [ ] CA-2: `python3 docs/architecture/native/check_arch.py` sort en 0 : `fdm-run` n'importe que la bibliothèque standard et n'importe jamais `fdm_tools` ; les fichiers sous `plugins/fdm/lib/fdm_tools/` (exemple compris) n'importent que la bibliothèque standard, `fdm_tools` et la liste blanche.
- [ ] CA-3: `fdm-run [--data DIR] PIECE [ARGS…]` : dossier de données depuis `--data`, sinon `CLAUDE_PLUGIN_DATA` ; absent des deux → sortie 1, message sur stderr nommant `--data` et `CLAUDE_PLUGIN_DATA`. Option inconnue ou `PIECE` manquant → sortie 2 via `argparse`.
- [ ] CA-4: `fdm-run` sort en 1 sans rien lancer, avec un message sur stderr, si `<data>/venv/bin/python` est absent (message renvoyant vers `fdm-setup`) ou si `PIECE` n'est pas un fichier existant (message citant le chemin).
- [ ] CA-5: Sinon `fdm-run` lance `<data>/venv/bin/python -m fdm_tools.run <PIECE> [ARGS…]` dans le répertoire courant inchangé, avec `PYTHONPATH` = `<plugin>/lib` placé devant un éventuel `PYTHONPATH` existant (`<plugin>` résolu depuis l'emplacement de la commande) et `FDM_DATA=<data>` ; stdout et stderr ne sont pas capturés ; `fdm-run` sort avec le code de sortie de ce processus.
- [ ] CA-6: `fdm_tools.run` exécute `PIECE` comme `__main__` (`runpy.run_path`, `sys.argv = [PIECE, ARGS…]`) puis sort en 1 si au moins un `check()` a signalé des problèmes, en 1 avec le message « aucun check() appelé : la pièce n'est pas vérifiée » sur stderr si aucun `check()` n'a été appelé, en 0 sinon ; une exception ou un `SystemExit` non nul de la pièce se propage tel quel.
- [ ] CA-7: `check(part, out)` garde la signature et le retour (maillage trimesh) de l'original ; avant tout export, il lit `$FDM_DATA/profiles/machine.json` et `filament.json`. `FDM_DATA` absent → `SystemExit` avec un message demandant de lancer la pièce par `fdm-run` ; fichier absent, JSON invalide ou champ manquant/illisible (`printable_area`, `printable_height`, `filament_density`, `filament_type`) → `SystemExit` avec un message citant le fichier et renvoyant vers `fdm-profiles`. Aucun fichier n'est écrit dans ces cas.
- [ ] CA-8: Le volume d'impression vaut (largeur, profondeur) de la boîte englobante des points `"XxY"` de `printable_area` et `printable_height` en hauteur ; une pièce dont une dimension dépasse l'axe correspondant est signalée par `exceeds build volume W × D × H mm (<name du profil machine>)`. Le poids estimé utilise `filament_density[0]` et `filament_type[0]` : `(~<g> g <type> if solid)`.
- [ ] CA-9: Les autres contrôles et la sortie de `check()` reprennent l'original à l'identique : export `out.step`, `out.stl` (tolérances 0.01 / 0.1), `out.png` (4 vues), contrôles étanchéité, orientation des faces, volume positif, appui sur Z=0, surface en surplomb > 45°, lignes `--- <nom> ---`, `size`, `volume`, `overhangs`, `files`, puis `OK` ou `ISSUES:` suivi des problèmes. Le dossier parent de `out` est créé ; une `OSError` à sa création donne un `SystemExit` citant le chemin, sans trace Python.
- [ ] CA-10: Les tests ajoutés sont hors ligne, en bibliothèque standard, et n'importent ni `fdm_tools` ni ses dépendances : faux venv (Python factice qui consigne argv, cwd, `PYTHONPATH`, `FDM_DATA` et rend un code de sortie choisi) pour CA-3 à CA-5 ; lecture AST des fichiers de `fdm_tools` pour la présence de `check(part, out)` exporté par `__init__`, du runner et de l'exemple appelant `check(…, "out/calibration_cube")`.
- [ ] CA-11: Vérification manuelle consignée en revue, sur la machine de l'auteur (macOS) avec un venv et des profils réels : `fdm-run plugins/fdm/lib/fdm_tools/examples/calibration_cube.py` depuis un dossier de projet vide affiche `OK`, écrit `out/calibration_cube.{step,stl,png}` et sort en 0 ; une pièce volontairement hors volume affiche `ISSUES:` et sort en 1.

## Contraintes
- Architecture : modules `fdm` (commande `fdm-run`) et `fdm-tools` (`plugins/fdm/lib/fdm_tools/`) ; règles R1 à R4 de `check_arch.py` ; aucune nouvelle dépendance tierce (liste blanche inchangée) ; aucune modification de `docs/architecture/` ni des ADR.
- `fdm-run` : bibliothèque standard, shebang `#!/usr/bin/env python3`, n'écrit rien, n'accède pas au réseau, appelle `<data>/venv/bin/python -m …` (jamais un script console du venv, cf. `docs/learnings.md`). Codes : 0, 1 (message actionnable sur stderr), 2 (usage) ; sinon le code relayé.
- Le registre des résultats est un état de module de `fdm_tools.check` lu par `fdm_tools.run` ; il n'y a ni fichier intermédiaire ni analyse de stdout.
- `fdm_tools` est l'API publique des pièces (ADR-0004) : `from fdm_tools import check` et `check(part, out: str)` sont figés à partir de cette unité.
- Les sorties de `check()` sont relatives au répertoire courant (projet de l'utilisateur) ; rien n'est écrit dans le plugin ni sous `<data>`.
- Compatibilité : macOS vérifié, Linux best effort ; Python du venv ≥ 3.11 et < 3.15.
- Diff visé ≲ 400 lignes.

## Décisions de cadrage
- [x] Q1: Découpage et identifiant ? → R: Unité 2 de la feature (Q7 de `0001-fdm-plugin`), cadrée sous l'identifiant `0002-fdm-check-run`, `depends_on: [0001-fdm-plugin]` ; aucune entrée « Exige un ADR » concernée. (2026-11-19)
- [x] Q2: Comment combiner les verdicts de plusieurs `check()` pour le code de sortie ? → R: Runner `python -m fdm_tools.run <pièce>` lancé par `fdm-run` ; il exécute la pièce par `runpy` et sort en 1 si au moins un `check()` a signalé `ISSUES` ; pas d'analyse de stdout. (2026-11-19)
- [x] Q3: Quelles données des profils `check()` lit-il, et comment les trouve-t-il ? → R: Volume = boîte englobante de `printable_area` + `printable_height` (`machine.json`), densité et type = `filament_density[0]`, `filament_type[0]` (`filament.json`) ; dossier via `FDM_DATA` posé par `fdm-run` ; profils manquants → erreur renvoyant vers `fdm-profiles`. (2026-11-19)
- [x] Q4: Où placer `calibration_cube.py` ? → R: `plugins/fdm/lib/fdm_tools/examples/calibration_cube.py`, dans le module `fdm-tools` (R2 et R3 respectées, pas de révision d'architecture) ; le skill de l'unité 3 le référencera. (2026-11-19)
- [x] Q5: Code de sortie d'une pièce sans aucun `check()` ? → R: 1, avec un message : aucune pièce n'est présentée comme bonne sans contrôle. (2026-11-19)
- [x] Q6: Comment tester sans importer `fdm_tools` ni build123d ? → R: Faux venv pour `fdm-run`, lecture AST des fichiers de `fdm_tools` ; chaîne réelle vérifiée à la main pendant la revue (cube `OK` en sortie 0, cas `ISSUES` en sortie 1). (2026-11-19)
- [x] Q7: Format de sortie de `check()` ? → R: Celui de l'original (lignes en anglais, `OK` / `ISSUES:`), mentions propres à l'A1 rendues génériques (nom de la machine du profil, type de filament) ; messages d'erreur en français comme les autres commandes `fdm-*`. (2026-11-19)
- [x] Q8: Interface de `fdm-run` ? → R: `fdm-run [--data DIR] PIECE [ARGS…]`, mêmes règles que l'unité 1 pour `<data>` ; répertoire courant inchangé ; code de sortie relayé. (2026-11-19)
- [x] Q9: Version du plugin ? → R: `0.2.0`, toujours « Préversion » jusqu'à l'unité 3 (1.0.0). (2026-11-19)
