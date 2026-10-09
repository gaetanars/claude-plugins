---
name: installer
description: Installe cadre dans le dépôt courant (Python ou TypeScript) — section CLAUDE.md, commande check unique (.claude/check.json), CI GitHub, dossier des tests d'acceptation. À lancer une fois par dépôt avec /cadre:installer.
disable-model-invocation: true
allowed-tools: Read Grep Glob Write Edit Bash(git *) Bash(mkdir *) Bash(python3 *) Bash(uv *) Bash(npm *) Bash(npx *) Bash(jq *)
---

# Installer cadre

Les fichiers à copier sont dans le dossier `assets/` de cette skill. Français, court. Une seule question à la fois ; les changements en masse se présentent en un bloc numéroté que Gaëtan valide (« ok » ou « ok sauf… »).

## 1. Prérequis

Vérifie et rapporte en une liste : `git`, `python3` (3.9 ou plus : les hooks l'exigent, même pour un dépôt TypeScript), `uv` (Python) ou `node`/`npm` (TypeScript). Le dépôt doit être un dépôt git. Si un prérequis manque, dis comment l'installer et arrête-toi.

## 2. Stack et commande check

Détecte la stack (`pyproject.toml` / `uv.lock`, `package.json`). Pars de `assets/check.python.json` ou `assets/check.typescript.json`, puis adapte au dépôt **sans rien affaiblir** :

- garde l'outillage déjà en place (mypy plutôt que pyright, ESLint + typescript-eslint plutôt que Biome, pnpm plutôt que npm) ;
- dépôt neuf : Python → uv, ruff, pyright, pytest, pytest-cov ; TypeScript → Biome 2, `tsc` strict, Vitest et `@vitest/coverage-v8` ;
- couverture : 85 % par défaut, à confirmer.

`check` est une commande unique, ses étapes enchaînées par `&&`. Présente la configuration finale et les dépendances de dev à ajouter.

## 3. Écriture (après « ok »)

1. `.claude/check.json` ← `{"check": "<commande>", "acceptance_dir": "tests/acceptance"}` (si le fichier existe, montre le diff).
2. `CLAUDE.md` du projet ← ajoute la section de `assets/claude-md.md` (absente seulement).
3. `.github/workflows/check.yml` ← `assets/ci-<stack>.yml`, adapté à l'outillage retenu. Le job s'appelle `check`. Vérifie la dernière version majeure de chaque action utilisée et mets-la à jour.
4. `tests/acceptance/` (avec `__init__.py` en Python).
5. `.gitignore` ← ajoute les lignes de `assets/gitignore.txt` absentes.
6. Dépendances de dev.

## 4. Ligne de base

Lance la commande `check`. Elle doit être verte avant toute livraison : sinon, liste les échecs et propose d'en faire la première spec via `/cadre:spec`.

## 5. Suite

Suggère (sans l'appliquer) la protection de `main` exigeant le contrôle `check`. Si `PRODUCT.md` ou `ARCHITECTURE.md` manquent, propose `/cadre:produit` et `/cadre:architecture`.
