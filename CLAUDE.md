# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

Marketplace Claude Code `gaetanars` (`.claude-plugin/marketplace.json`), un plugin par dossier sous `plugins/`. Plugins actuels : `sdlc-contract` (poste + serveur), `sdlc-framing` (poste), `sdlc-factory` (serveur). `cadre` a été retiré (historique git conservé). README.md décrit installation, parcours SDLC, contribution et contrôles de CI.

Remote : `git@github.com:gaetanars/claude-plugins.git` (renommage depuis `tdd-forge` à faire côté GitHub), branche `main`. Langue du code, des prompts et des commits : français (messages au format `feat: …`).

## Règles de marketplace

- Version dans `plugins/<p>/.claude-plugin/plugin.json` uniquement (jamais dans l'entrée marketplace) ; **toute modification d'un plugin impose un bump semver** (contrôlé en CI sur les PR).
- Pas de `CLAUDE.md` dans un dossier de plugin : ce fichier racine porte les consignes de tous les plugins.
- Frontmatter des skills/agents en `clé: valeur` sur une ligne (le lecteur de `tests/_common.py` n'accepte rien d'autre).

## Validation

- `python3 -m unittest discover -s tests -t . -v` (un module par type d'élément ; `BASE_REF=origin/main` active le contrôle de bump). Même commande en CI (`.github/workflows/validate.yml`), qui ajoute `actionlint`.
- `claude plugin validate --strict .` ne valide que la marketplace ; chaque plugin se valide séparément (`claude plugin validate --strict plugins/<p>`), ce que fait `tests/test_cli_validate.py`.

## Plugins SDLC

SDLC agentique : cadrage sur poste (`sdlc-framing`), usine sur serveur (`sdlc-factory`, orchestrateur `sdlc-run` en `claude -p`), contrat partagé (`sdlc-contract`). Merge humain par défaut ; auto-merge en opt-in par dépôt (`owner/repo automerge` dans le fichier `repos`, `sdlc-init-repo github --automerge` avec CI requise).

Règles :
- Bibliothèque standard Python uniquement : ni dépendance, ni abstraction non demandée (donc `claude -p`, pas l'Agent SDK).
- `plugins/sdlc-factory/{scripts/guard.py,hooks,bin,lib}` passent par une revue humaine : la rétro ne les touche pas (le hook le refuse, ainsi que `deploy/`, `schemas/`, `plugins/sdlc-*/bin/`, `tests/`, `.claude-plugin/`). `guard.py` échoue en mode fermé.
- Un changement de format de spec incrémente `schema_version` ; validateur, `sdlc-run` et `sdlc-publish` gèrent les versions supportées.
- Un agent ne dépend d'aucun fichier hors de son worktree, sauf via `SDLC_ALLOW_READ`.
- Les appels `claude` utilisent `--setting-sources user` (ignore hooks/env/`.mcp.json` du dépôt cible), `--permission-mode dontAsk`, `--max-turns` par rôle (`ROLES` dans `lib/sdlc_common.py`, mêmes valeurs que le frontmatter) et un sandbox natif obligatoire. `--bare` est écarté : il désactive les hooks du plugin.

Couplages à relire ensemble :
- `.claude/check.json` (`{"check": "<cmd>"}`) : `sdlc-init-repo scaffold` (gabarit `A_RENSEIGNER`), `sdlc-run` (`load_check`, `run_check`, gate), agents `implementer`/`reviewer-*`.
- Bloc d'issue `sdlc:begin` : `sdlc-publish` ↔ `sdlc-run` (`parse_block`).
- `schema_version` : `sdlc-validate-spec`, `sdlc-run` (`SUPPORTED_SCHEMA`), `sdlc-publish`.
- `schemas/verdict.schema.json` (contrat) : reviewers, `adjudicate`, `sdlc-retro`.
- Fichier `repos` : `sdlc-run` (`read_repos`, suffixe `automerge`) et `sdlc-retro` (premier mot seulement).

Les tests SDLC (`tests/test_sdlc_*.py`, faux `gh`/`claude` dans `tests/sdlc_fakebin/`) tournent hors ligne. Pas d'exécution de bout en bout vérifiée (vrai `claude -p`, sandbox réel, GitHub réel, quotas) : ne pas la présenter comme acquise.
