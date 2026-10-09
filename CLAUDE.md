# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

Marketplace Claude Code `gaetanars` (`.claude-plugin/marketplace.json`), un plugin par dossier sous `plugins/`. Plugin actuel : `cadre`. README.md décrit installation, contribution et contrôles de CI.

Remote : `git@github.com:gaetanars/claude-plugins.git` (renommage depuis `tdd-forge` à faire côté GitHub), branche `main`. Langue du code, des prompts et des commits : français (messages au format `feat: …`).

## Règles de marketplace

- Version dans `plugins/<p>/.claude-plugin/plugin.json` uniquement (jamais dans l'entrée marketplace) ; **toute modification d'un plugin impose un bump semver** (contrôlé en CI sur les PR).
- Pas de `CLAUDE.md` dans un dossier de plugin : ce fichier racine porte les consignes de tous les plugins.
- Frontmatter des skills/agents en `clé: valeur` sur une ligne (le lecteur de `tests/_common.py` n'accepte rien d'autre).

## Validation

- `python3 -m unittest discover -s tests -t . -v` (un module par type d'élément ; `BASE_REF=origin/main` active le contrôle de bump). Même commande en CI (`.github/workflows/validate.yml`), qui ajoute `actionlint`.
- `claude plugin validate --strict .` ne valide que la marketplace ; chaque plugin se valide séparément (`claude plugin validate --strict plugins/<p>`), ce que fait `tests/test_cli_validate.py`.

## Plugin cadre

Cadrage par le contexte pour dépôts Python/TypeScript. Parcours : `/cadre:installer` → `produit` → `architecture` → `spec` (écrit `docs/specs/S00x.md`) → implémentation en Plan mode, merge humain. `plugins/cadre/README.md` détaille le tout.

- Deux hooks : `scripts/acceptance_lock.py` (PreToolUse, `ask` sur un test d'acceptation déjà suivi par git) et `scripts/check_gate.py` (Stop, lance `check`, exit 2 tant que rouge, 3 essais max).
- Contrat `.claude/check.json` du projet cible : `{"check": "<cmd>", "acceptance_dir": "..."}`, lu par les deux hooks, la CI (`assets/ci-*.yml`) et la skill `installer` : toute évolution impose de relire les quatre.
- Pas d'exécution de bout en bout vérifiée : ne pas la présenter comme acquise.
