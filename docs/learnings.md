# Apprentissages

Lu avant chaque travail par les skills `sdlc` (`challenge`, `spec`, `architect`, `go`) et les agents (planner, implementer, reviewer).
Une ligne par apprentissage, issue d'un fait constaté (finding corrigé, clarification, gate rouge, arbitrage).
Format : `- AAAA-MM-JJ [<feature-id>] constat → règle à appliquer`. Retirer une ligne devenue fausse plutôt que l'empiler.


- 2026-11-19 [architecture] dépendances tierces nécessaires au plugin fdm (build123d/OCP) → elles restent confinées à `plugins/fdm/lib/fdm_tools/` dans un venv sous `${CLAUDE_PLUGIN_DATA}` ; tests et CI restent stdlib et hors ligne (ADR-0002).
- 2026-11-19 [architecture] profils Bambu Studio sous AGPL → jamais redistribués, générés localement par `fdm-profiles` (ADR-0003).
- 2026-11-19 [0001-fdm-plugin] deux corrections en revue finale pour une trace Python sur un `<data>` invalide (fdm-setup, puis fdm-profiles) → toute commande `fdm-*` protège aussi ses écritures disque (mkdir, mkdtemp, write, replace) par `except OSError` vers un message citant le chemin, avec un test « `<data>` est un fichier / non inscriptible » vérifiant l'absence de `Traceback`.
- 2026-11-19 [0001-fdm-plugin] le venv est construit dans un dossier temporaire puis renommé : ses scripts console (`bin/pip`, `bin/activate`) gardent le chemin temporaire → toujours appeler `<data>/venv/bin/python -m …`, jamais un script console du venv.
- 2026-11-19 [0001-fdm-plugin] `${user_config.KEY}` n'est substitué que dans les skills, agents et hooks, pas dans l'environnement des commandes `bin/` → le skill passe options et `${CLAUDE_PLUGIN_DATA}` en arguments explicites.
