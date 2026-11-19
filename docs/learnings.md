# Apprentissages

Lu avant chaque travail par les skills `sdlc` (`challenge`, `spec`, `architect`, `go`) et les agents (planner, implementer, reviewer).
Une ligne par apprentissage, issue d'un fait constaté (finding corrigé, clarification, gate rouge, arbitrage).
Format : `- AAAA-MM-JJ [<feature-id>] constat → règle à appliquer`. Retirer une ligne devenue fausse plutôt que l'empiler.


- 2026-11-19 [architecture] dépendances tierces nécessaires au plugin fdm (build123d/OCP) → elles restent confinées à `plugins/fdm/lib/fdm_tools/` dans un venv sous `${CLAUDE_PLUGIN_DATA}` ; tests et CI restent stdlib et hors ligne (ADR-0002).
- 2026-11-19 [architecture] profils Bambu Studio sous AGPL → jamais redistribués, générés localement par `fdm-profiles` (ADR-0003).
