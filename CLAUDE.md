# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

Marketplace Claude Code `gaetanars` (`.claude-plugin/marketplace.json`), un plugin par dossier sous `plugins/`. Plugin actuel : `sdlc` (SDLC AI-First interactif). `sdlc-contract`, `sdlc-framing`, `sdlc-factory` (usine Orca) et `cadre` ont été retirés (historique git conservé ; Orca pourra être réintroduit). README.md décrit installation, parcours SDLC, contribution et contrôles de CI.

Remote : `git@github.com:gaetanars/claude-plugins.git` (renommage depuis `tdd-forge` à faire côté GitHub), branche `main`. Langue du code, des prompts et des commits : français (messages au format `feat: …`).

## Règles de marketplace

- Version dans `plugins/<p>/.claude-plugin/plugin.json` uniquement (jamais dans l'entrée marketplace) ; **toute modification d'un plugin impose un bump semver** (contrôlé en CI sur les PR).
- Pas de `CLAUDE.md` dans un dossier de plugin : ce fichier racine porte les consignes de tous les plugins.
- Frontmatter des skills/agents en `clé: valeur` sur une ligne (le lecteur de `tests/_common.py` n'accepte rien d'autre).

## Validation

- `python3 -m unittest discover -s tests -t . -v` (un module par type d'élément ; `BASE_REF=origin/main` active le contrôle de bump). Même commande en CI (`.github/workflows/validate.yml`), qui ajoute `actionlint`.
- `claude plugin validate --strict .` ne valide que la marketplace ; chaque plugin se valide séparément (`claude plugin validate --strict plugins/<p>`), ce que fait `tests/test_cli_validate.py`.
- Architecture (`docs/architecture/ARCHITECTURE.md`, ADR dans `docs/adr/`) : `python3 docs/architecture/native/check_arch.py` (bibliothèque standard, rien à installer ; champ `arch` de `.claude/check.json`). La modifier passe par `/sdlc:architect revise`.

## Plugin SDLC

Interactif : `/sdlc:go <besoin>` trie en trivial / standard / feature, enchaîne les briques (`challenge`, `spec`, `architect`, `plan`, `build`, `review`, `ship`, `retro`, `conventions`, chacune invocable seule ; `disable-model-invocation: true` seulement sur `go` et `retro`, les autres briques doivent rester chargeables par `go` via l'outil `Skill`, leur `description` dit à quel moment) et s'arrête à chaque gate humaine (statut d'artefact ou commit ; **aucun hook**). Pas d'issue GitHub ni de label : la spec acceptée et commitée est l'unité de travail. Merge toujours humain ; push SSH + PR seulement après l'accord explicite en session. Amélioration continue : `docs/learnings.md` dans chaque projet (écrit par `ship`, `spec`, `architect`, relu par toutes les briques) ; rétro manuelle `/sdlc:retro`.

Règles :
- Bibliothèque standard Python uniquement : ni dépendance, ni abstraction non demandée. Plugin universel : aucun code propre à un langage ou à un projet.
- Le déterministe va dans `sdlc-gate` (démarrage, validations, TDD, verify, verdict, push, PR) ; l'enchaînement va dans les skills. `plugins/sdlc/bin/sdlc-gate` passe par une revue humaine : le skill `retro` ne le modifie pas.
- `sdlc-gate` n'écrit jamais `.git/config` (protégé par la sandbox de Claude Code) : `--no-track`, push sans `-u`, état dans les notes git (`refs/notes/sdlc-red`, `refs/notes/sdlc-review`) et la branche (`feat/<id>`, `fix/<slug>`).
- Un changement de format de spec incrémente `schema_version` (v3 uniquement, `SUPPORTED_SCHEMA`) ; l'architecture a son propre `schema_version` (v2).

Couplages à relire ensemble :
- `.claude/check.json` (`{"check": "<cmd>", "arch": "<cmd>"}`, `arch` facultatif mais obligatoire si l'architecture est acceptée) : `sdlc-init-repo scaffold` (gabarit `A_RENSEIGNER`), `sdlc-gate` (`load_check`, `run_check`, `tests-red`, `verify`), agent `implementer`, skill `architect`.
- Architecture cadrée (`docs/architecture/{ARCHITECTURE.md,native/}`, `docs/adr/`) : `sdlc-validate-architecture`, skill `architect` (seul auteur des ADR), `spec` (garde-fou feature), `sdlc-gate` (`start` exige l'acceptation en feature, `verify` protège les chemins), agents `planner` et `reviewer`. Aucun fichier de configuration native hors `docs/architecture/native/`.
- Spec v3 (`track`, `status`) : `sdlc-validate-spec`, `sdlc-gate` (`start`, `verify`, `deliver`), skills `spec`/`go`/`plan`, gabarit `spec.md`, `conventions`.
- `schemas/verdict.schema.json` : agent `reviewer`, `sdlc-gate` (`check_verdict`, `adjudicate`, corps de PR).
- Convention TDD en deux commits et `plan.md` avant le premier `test` : `conventions`, gabarit `plan.md`, agents `planner`/`implementer`, `sdlc-gate` (`tdd_errors`, `verify`).
- `docs/learnings.md` : gabarit `learnings.md`, `sdlc-init-repo scaffold`, skills `challenge`/`spec`/`architect`/`ship`/`retro`/`go`, agents, `sdlc-gate deliver` (seul fichier modifiable après la revue avec `plan.md`).

Les tests SDLC (`tests/test_sdlc_*.py`, faux `gh` dans `tests/sdlc_fakebin/`, limité à `pr list/create`) tournent hors ligne. Aucun run interactif complet de `/sdlc:go` n'est vérifié : ne pas le présenter comme acquis.
