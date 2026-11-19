# Apprentissages

Lu avant chaque travail par les skills `sdlc` (`challenge`, `spec`, `architect`, `go`) et les agents (planner, implementer, reviewer).
Une ligne par apprentissage, issue d'un fait constaté (finding corrigé, clarification, gate rouge, arbitrage).
Format : `- AAAA-MM-JJ [<feature-id>] constat → règle à appliquer`. Retirer une ligne devenue fausse plutôt que l'empiler.


- 2026-11-19 [architecture] dépendances tierces nécessaires au plugin fdm (build123d/OCP) → elles restent confinées à `plugins/fdm/lib/fdm_tools/` dans un venv sous `${CLAUDE_PLUGIN_DATA}` ; tests et CI restent stdlib et hors ligne (ADR-0002).
- 2026-11-19 [architecture] profils Bambu Studio sous AGPL → jamais redistribués, générés localement par `fdm-profiles` (ADR-0003).
- 2026-11-19 [0001-fdm-plugin] deux corrections en revue finale pour une trace Python sur un `<data>` invalide (fdm-setup, puis fdm-profiles) → toute commande `fdm-*` protège aussi ses écritures disque (mkdir, mkdtemp, write, replace) par `except OSError` vers un message citant le chemin, avec un test « `<data>` est un fichier / non inscriptible » vérifiant l'absence de `Traceback`.
- 2026-11-19 [0001-fdm-plugin] le venv est construit dans un dossier temporaire puis renommé : ses scripts console (`bin/pip`, `bin/activate`) gardent le chemin temporaire → toujours appeler `<data>/venv/bin/python -m …`, jamais un script console du venv.
- 2026-11-19 [0001-fdm-plugin] `${user_config.KEY}` n'est substitué que dans les skills, agents et hooks, pas dans l'environnement des commandes `bin/` → le skill passe options et `${CLAUDE_PLUGIN_DATA}` en arguments explicites.
- 2026-11-19 [0002-fdm-check-run] la règle R3 de `check_arch.py` refuse tout `import fdm_tools` hors de `plugins/fdm/lib/` → tout exemple ou pièce de référence embarqué dans le plugin vit sous `plugins/fdm/lib/fdm_tools/` (ex. `examples/calibration_cube.py`), et le skill le référence à cet endroit.
- 2026-11-19 [0002-fdm-check-run] `fdm_tools` n'est testable en CI que par lecture AST → chaque unité qui touche `fdm_tools` prévoit une vérification manuelle en revue ; elle se fait hors ligne avec un `<data>` temporaire (profils générés par le vrai `fdm-profiles`, `venv` en lien vers un venv local aux versions épinglées), puis suppression du dossier et de `plugins/fdm/lib/fdm_tools/__pycache__/`.
- 2026-11-19 [0002-fdm-check-run] `fdm-run` exécute la pièce par `runpy` : `sys.path[0]` est la racine du projet (pas `parts/`) et une pièce sans `check()` sort en 1, même après `sys.exit(0)` → le skill `fdm:design` doit l'expliquer (imports relatifs à la racine, un `check()` par pièce).
- 2026-11-19 [0003-fdm-slice-skill] le skill passe `${user_config.*}` tel quel, vide par défaut pour les chemins Bambu → toute option de chemin d'une commande `fdm-*` traite une valeur vide comme absente (défaut macOS, sinon erreur demandant l'option).
- 2026-11-19 [0003-fdm-slice-skill] `sdlc-gate start` refuse un arbre modifié hors spec et brief, or le skill `spec` écrit ses arbitrages dans `docs/learnings.md` avant `start` → mettre cette modification de côté (`git stash`) avant `start` et la garder hors des commits du build jusqu'au `ship` (à corriger dans le plugin via `/sdlc:retro`).
- 2026-11-19 [0003-fdm-slice-skill] le reviewer a approuvé sans lire le corps des tests (3 appels d'outils) → la revue finale relit soi-même le code principal et lance les tests de la feature avant de présenter le verdict.
- 2026-11-19 [0003-fdm-slice-skill] `fdm-slice` se vérifie avec le vrai Bambu Studio sans installer le plugin : `<data>` temporaire rempli par `fdm-profiles --data`, copie d'un STL dans un projet temporaire, puis un `machine.json` tronqué pour le cas d'échec ; suppression du dossier ensuite.
