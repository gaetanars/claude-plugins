---
name: installer
description: Installe ou met à jour tdd-forge dans le dépôt courant (Python ou TypeScript) — configuration des portes, moteur forge.py, CI GitHub, permissions, protection de branche. À lancer une fois par dépôt avec /tdd-forge:installer, puis après chaque mise à jour du plugin.
disable-model-invocation: true
allowed-tools: Read Grep Glob Write Edit Bash(git *) Bash(gh auth status) Bash(cp *) Bash(mkdir *) Bash(python3 *) Bash(uv *) Bash(npm *) Bash(npx *)
---

# Installer tdd-forge

Les fichiers à copier sont dans le dossier `assets/` de cette skill. Français, court. Une seule question à la fois ; les changements en masse se présentent en un bloc numéroté que Gaëtan valide (« ok » ou « ok sauf… »).

## 1. Prérequis

Vérifie et rapporte en une liste : `git`, `python3` (3.9 ou plus, requis même pour un dépôt TypeScript), `gh auth status`, `uv` (Python) ou `node`/`npm` (TypeScript), `claude --version` (2.1.271 ou plus : `omitClaudeMd` et les workflows reprenables l'exigent). Remote `origin` sur GitHub. Si un prérequis manque, dis comment l'installer et arrête-toi.

Forge GitLab : pas encore prise en charge par `forge.py` (v0.1). Dis-le et arrête-toi.

## 2. Stack et portes

Détecte la stack (`pyproject.toml` / `uv.lock`, `package.json`). Pars de `assets/config.python.json` ou `assets/config.typescript.json`, puis adapte au dépôt **sans rien affaiblir** :

- garde l'outillage déjà en place (mypy plutôt que pyright, ESLint + typescript-eslint plutôt que Biome, pnpm plutôt que npm) ;
- dépôt neuf : Python → uv, ruff, pyright, pytest, pytest-cov ; TypeScript → Biome 2, `tsc` strict, Vitest et `@vitest/coverage-v8` ;
- branche par défaut réelle (`git symbolic-ref refs/remotes/origin/HEAD`) ;
- couverture : 85 % par défaut, à confirmer.

Présente la configuration finale et les dépendances de dev à ajouter.

## 3. Écriture (après « ok »)

1. `.forge/bin/forge.py` ← `assets/forge.py` (écrase : c'est la mise à jour du moteur).
2. `.forge/config.json` ← la configuration validée (ne l'écrase pas si elle existe : montre le diff).
3. `.forge/learnings.md` ← `assets/learnings.md`, seulement s'il n'existe pas.
4. `.gitignore` ← ajoute les lignes de `assets/gitignore.txt` absentes.
5. `.claude/settings.json` ← fusionne `assets/settings.json` (ajoute les règles manquantes, ne retire rien). Adapte les commandes autorisées à l'outillage retenu.
6. `.github/workflows/forge-gates.yml` ← le modèle de la stack. Vérifie la dernière version majeure de chaque action utilisée et mets-la à jour.
7. Exclusions : les worktrees vivent dans `.forge/worktrees/`. Vérifie que les outils ne les parcourent pas depuis le checkout principal : `testpaths = ["tests"]` pour pytest ; `exclude` étendu à `.forge/**` pour Vitest ; `vcs.useIgnoreFile` pour Biome ; `include` restreint pour `tsconfig.json`. ruff et pyright ignorent déjà `.forge`.
8. Dépendances de dev et dossier `tests/acceptance/` (avec `__init__.py` en Python).

## 4. Ligne de base

Lance `python3 .forge/bin/forge.py gate`. Elle doit être verte sur `main` avant toute livraison : sinon, liste les échecs et propose d'en faire la première tâche via `/tdd-forge:cadrer`.

## 5. GitHub (avec accord explicite, une action à la fois)

1. `gh repo edit --enable-auto-merge --delete-branch-on-merge`.
2. Protection de `main` exigeant le contrôle `gates` :
   `gh api -X PUT repos/{owner}/{repo}/branches/<branche>/protection --input -` avec
   `{"required_status_checks": {"strict": true, "contexts": ["gates"]}, "enforce_admins": true, "required_pull_request_reviews": null, "restrictions": null}`.
   Préviens : `enforce_admins` empêche aussi Gaëtan de pousser directement sur `main`. Sur un dépôt privé, la protection dépend du plan GitHub ; si l'API la refuse, forge.py surveille lui-même la CI et ne merge que si elle est verte.
3. Commit de l'installation sur une branche `chore/tdd-forge` et PR, que Gaëtan merge lui-même. Les fichiers du système ne passent jamais par le merge automatique.

## 6. Suite

Si `PRODUCT.md` manque, propose `/tdd-forge:cadrer` pour l'écrire. Termine par la commande d'usage : `/tdd-forge:cadrer <besoin>`.
