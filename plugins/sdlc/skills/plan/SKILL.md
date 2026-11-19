---
name: plan
description: Brique SDLC : planifie une spec acceptée via le sous-agent planner, écrit plan.md et le commite après accord humain (remplace plan mode). À charger après `sdlc-gate start <id>` dans un parcours /sdlc:go, ou sur /sdlc:plan explicite.
---

# Plan : un plan relu et validé avant la première ligne de code

Prérequis : `sdlc-gate start <id>` a réussi (branche `feat/<id>`, spec commitée). Sinon arrête-toi.

1. **Lance le sous-agent `sdlc:planner`** avec uniquement des chemins : `docs/features/<id>/spec.md`, `brief.md` s'il existe, `CLAUDE.md`, `docs/learnings.md`, `docs/architecture/ARCHITECTURE.md` et `docs/adr/` s'ils existent, gabarit `sdlc-template plan`.
2. **Questions** de sa section `## Questions` :
   - `[structurante]` : tu ne tranches pas ; arrête-toi et renvoie vers `/sdlc:architect adr <sujet>`.
   - `[bloquante]` : pose-la à l'humain, consigne Q/R dans « Clarifications » du plan, relance le planner si la réponse change le plan.
3. **Écris** `docs/features/<id>/plan.md` (sortie du planner, sans la section `## Questions`). Bug : la première étape est le test de reproduction.
4. **Gate humaine** : présente le plan (étapes, couverture des CA, risques) et demande « Tu valides le plan ? ». Modifie-le selon ses retours.
5. Après accord explicite seulement : commit `docs(<id>): plan` (footer `Feature: <id>`). `sdlc-gate verify` exige ce commit avant le premier commit `test`.

Ne code pas. Ne commite rien d'autre.
