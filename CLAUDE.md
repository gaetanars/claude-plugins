# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

Marketplace Claude Code `gaetanars` (`.claude-plugin/marketplace.json`), un plugin par dossier sous `plugins/`. Plugins actuels : `sdlc-contract` (poste + serveur), `sdlc-framing` (poste ou session Orca), `sdlc-factory` (serveur Orca). `cadre` a été retiré (historique git conservé). README.md décrit installation, parcours SDLC, contribution et contrôles de CI.

Remote : `git@github.com:gaetanars/claude-plugins.git` (renommage depuis `tdd-forge` à faire côté GitHub), branche `main`. Langue du code, des prompts et des commits : français (messages au format `feat: …`).

## Règles de marketplace

- Version dans `plugins/<p>/.claude-plugin/plugin.json` uniquement (jamais dans l'entrée marketplace) ; **toute modification d'un plugin impose un bump semver** (contrôlé en CI sur les PR).
- Pas de `CLAUDE.md` dans un dossier de plugin : ce fichier racine porte les consignes de tous les plugins.
- Frontmatter des skills/agents en `clé: valeur` sur une ligne (le lecteur de `tests/_common.py` n'accepte rien d'autre).

## Validation

- `python3 -m unittest discover -s tests -t . -v` (un module par type d'élément ; `BASE_REF=origin/main` active le contrôle de bump). Même commande en CI (`.github/workflows/validate.yml`), qui ajoute `actionlint`.
- `claude plugin validate --strict .` ne valide que la marketplace ; chaque plugin se valide séparément (`claude plugin validate --strict plugins/<p>`), ce que fait `tests/test_cli_validate.py`.

## Plugins SDLC

SDLC agentique : cadrage interactif (`sdlc-framing`, en local ou dans une session Orca), usine sur serveur Orca (`sdlc-factory` : automatisation Orca → skill `deliver` → sous-agents + `sdlc-gate`), contrat partagé (`sdlc-contract`). Merge toujours humain, pas d'auto-merge. Amélioration continue : `docs/learnings.md` dans chaque projet (écrit par l'usine et le `po`, relu par tous) ; la rétro sur les plugins est un skill manuel (`/sdlc-framing:retro`).

Règles :
- Bibliothèque standard Python uniquement : ni dépendance, ni abstraction non demandée. Plugins universels : aucun code propre à un langage ou à un projet.
- Le déterministe va dans `sdlc-gate` (choix d'issue, validations, TDD, gates, verdict, push, PR, labels) ; l'enchaînement va dans le skill `deliver`. `plugins/sdlc-factory/bin/sdlc-gate` passe par une revue humaine : le skill `retro` ne le modifie pas.
- `sdlc-gate` n'écrit jamais `.git/config` (protégé par la sandbox de Claude Code) : `--no-track`, push sans `-u`, état dans les notes git (`refs/notes/sdlc-red`, `refs/notes/sdlc-review`).
- Un changement de format de spec ou d'architecture incrémente `schema_version` ; validateurs, `sdlc-gate` et `sdlc-publish` gèrent les versions supportées (v2 uniquement).
- La sécurité du serveur repose sur la sandbox de Claude Code (réglages du serveur, documentés dans `plugins/sdlc-factory/README.md`), l'utilisateur Unix dédié et la relecture humaine des PR ; aucun hook dans les plugins.

Couplages à relire ensemble :
- `.claude/check.json` (`{"check": "<cmd>", "arch": "<cmd>"}`) : `sdlc-init-repo scaffold` (gabarit `A_RENSEIGNER`), `sdlc-gate` (`load_check`, `run_check`, `tests-red`, `verify`), agent `implementer`, skill `architect`.
- Architecture cadrée (`docs/architecture/{ARCHITECTURE.md,native/}`, `docs/adr/`) : `sdlc-validate-architecture` (format de référence), skill `architect` (écrit, seul auteur des ADR), `po` (garde-fou avant découpage), `sdlc-publish` (exige accepté + commité), `sdlc-gate` (`start` valide, `verify` protège les chemins), agents `planner` (remonte les décisions « Exige un ADR ») et `reviewer`. Aucun fichier de configuration native hors `docs/architecture/native/`.
- Bloc d'issue `sdlc:begin` : `sdlc-publish` ↔ `sdlc-gate` (`parse_block`).
- `schema_version` : `sdlc-validate-spec`, `sdlc-validate-architecture`, `sdlc-gate` (`SUPPORTED_SCHEMA`), `sdlc-publish`.
- `schemas/verdict.schema.json` (contrat) : agent `reviewer`, `sdlc-gate` (`check_verdict`, `adjudicate`, corps de PR).
- Convention TDD en deux commits (`test` rouge puis `feat`) : `sdlc-conventions`, gabarit `plan.md`, agents `planner` et `implementer`, `sdlc-gate` (`tdd_errors`).
- `docs/learnings.md` : gabarit `learnings.md`, `sdlc-init-repo scaffold`, skills `challenger`/`po`/`architect`/`retro`/`deliver`, agents, `sdlc-gate deliver` (seul fichier modifiable après la revue avec `plan.md`).

Les tests SDLC (`tests/test_sdlc_*.py`, faux `gh` dans `tests/sdlc_fakebin/`) tournent hors ligne. Vérifié sur le serveur : essai Orca (skill depuis le prompt, worktree neuf, signature, push SSH et `gh` en sandbox). Pas de run complet de `/sdlc-factory:deliver` vérifié : ne pas le présenter comme acquis.
