---
name: init
description: Installe, initialise ou met à jour tdd-forge dans le dépôt courant, quel que soit le langage (Python, TypeScript/JS, Go, Rust, Java/Kotlin, .NET, Ruby, PHP) — entretien de vision sur dépôt neuf, stack, squelette, portes, moteur forge.py, conventions, CI GitHub, permissions, protection de branche. À lancer avec /tdd-forge:init, puis après chaque mise à jour du plugin.
disable-model-invocation: true
model: opus
allowed-tools: Read Grep Glob Write Edit AskUserQuestion Bash(git *) Bash(gh *) Bash(cp *) Bash(mkdir *) Bash(python3 *) Bash(uv *) Bash(npm *) Bash(npx *) Bash(go *) Bash(cargo *) Bash(dotnet *) Bash(bundle *) Bash(composer *) Bash(mvn *) Bash(gradle *) Bash(./gradlew *)
---

# Initialiser tdd-forge

Les fichiers à copier sont dans `assets/`, la référence des écosystèmes dans `references/ecosystems.md` (de cette skill). Français, court. Une question à la fois ; les changements en masse se présentent en un bloc numéroté que Gaëtan valide (« ok » ou « ok sauf… »), par `AskUserQuestion` quand les options sont nettes.

## 0. Mode

Détecte le mode et annonce-le en une ligne :

- **neuf** : dépôt sans code (vide, ou seulement README/LICENSE) ;
- **existant** : du code, pas de `.forge/config.json` ;
- **mise à jour** : `.forge/config.json` existe. On écrase `forge.py`, on montre le diff de la config et des fichiers générés, on ne réécrit ni `PRODUCT.md`, ni les conventions, ni la config sans accord.

## 1. Prérequis

Liste en une ligne chacun : `git`, `python3` (3.9 ou plus, requis quel que soit le langage), `gh auth status`, les outils de la stack, `claude --version` (2.1.271 ou plus : `omitClaudeMd` et les workflows reprenables l'exigent). Remote `origin` sur GitHub (GitLab n'est pas pris en charge). Un prérequis manque : dis comment l'installer et arrête-toi.

## 2. Vision (mode neuf)

Conduis l'entretien de vision avec le modèle `../po/templates/PRODUCT.md`, une question à la fois. Propose une rédaction d'une page au plus ; `PRODUCT.md` est écrit après son « ok ». Copie aussi `../po/templates/decisions.md` vers `docs/product/decisions.md`.

## 3. Stack

- **Existant / mise à jour** : détecte-la (fichiers de config, lanceur de test en place) et garde l'outillage déjà là.
- **Neuf** : propose une stack adaptée à la vision, avec une justification d'une ligne, parmi les écosystèmes de `references/ecosystems.md` ; Gaëtan tranche. Crée le **squelette minimal** : outillage (gestionnaire de dépendances, formateur, linter, typage, couverture) et **un test de fumée** qui passe. Rien d'autre : la première tâche décide de l'architecture.

Un écosystème sans rapport JUnit n'est pas pris en charge : dis-le.

## 4. Configuration

Pars de `assets/config.example.json` et compose `.forge/config.json` pour la stack avec `references/ecosystems.md` : `stack` (libellé informatif), `test_cmd`, `junit_path`, `gates` (format, lint, typage, tests avec couverture ; la porte tests porte `"tests": true`), `test_globs`, `acceptance_dir`, `suppression_markers`. **Sans rien affaiblir** : garde l'outillage en place, couverture à 85 % par défaut (à confirmer), branche par défaut réelle (`git symbolic-ref refs/remotes/origin/HEAD`).

Présente la configuration et les dépendances de dev à ajouter, attends le « ok ».

## 5. Écriture (après « ok »)

1. `.forge/bin/forge.py` ← `assets/forge.py` (écrase : c'est la mise à jour du moteur).
2. `.forge/config.json` ← la configuration validée (si elle existe : montre le diff, n'écrase qu'avec accord).
3. `.forge/conventions.md` ← `assets/conventions.md` rempli pour la stack (commandes, structure, nommage `AC-n` avec un exemple du langage, idiomes, pièges), seulement s'il n'existe pas.
4. `.forge/learnings.md` ← `assets/learnings.md`, seulement s'il n'existe pas.
5. `.gitignore` ← ajoute les lignes de `assets/gitignore.txt` absentes.
6. `.claude/settings.json` ← fusionne `assets/settings.json` (ajoute, ne retire rien) et ajoute les commandes de la stack retenue (`Bash(<lanceur> *)`).
7. `.github/workflows/forge-gates.yml` ← `assets/forge-gates.yml` dont le bloc `# setup … # endsetup` est remplacé par le setup CI de la stack (toolchain, dépendances). Vérifie la dernière version majeure de chaque action.
8. Exclusions : les worktrees vivent dans `.forge/worktrees/`. Vérifie que les outils ne les parcourent pas depuis le checkout principal (colonne « Exclure `.forge/` » de la référence).
9. Dépendances de dev, dossier `acceptance_dir` (avec le fichier d'amorce qu'exige la stack).

## 6. Contrôles

1. `python3 .forge/bin/forge.py doctor --plugin-version <version de .claude-plugin/plugin.json du plugin>` : JUnit lisible avec au moins un testcase, remote GitHub, `gh`, version du moteur. Corrige la config jusqu'au vert ; c'est le contrôle déterministe de ce que tu viens d'écrire.
2. `python3 .forge/bin/forge.py gate` : verte sur `main` avant toute livraison. Sinon, liste les échecs et propose d'en faire la première tâche via `/tdd-forge:po`.

## 7. GitHub (accord explicite, une action à la fois)

1. `gh repo edit --enable-auto-merge --delete-branch-on-merge`.
2. Protection de `main` exigeant le contrôle `gates` :
   `gh api -X PUT repos/{owner}/{repo}/branches/<branche>/protection --input -` avec
   `{"required_status_checks": {"strict": true, "contexts": ["gates"]}, "enforce_admins": true, "required_pull_request_reviews": null, "restrictions": null}`.
   Préviens : `enforce_admins` empêche aussi Gaëtan de pousser directement sur `main`. Sur un dépôt privé, la protection dépend du plan GitHub ; si l'API la refuse, forge.py surveille lui-même la CI et ne merge que si elle est verte.
3. Portes de sécurité, **proposées, jamais imposées** : `osv-scanner` (dépendances) et `gitleaks` (secrets), comme portes supplémentaires de `gates` si Gaëtan les veut.
4. Commit de l'initialisation sur une branche `chore/tdd-forge` et PR, que Gaëtan merge lui-même. Les fichiers du système ne passent jamais par le merge automatique. Aucun push sans son accord.

## 8. Suite

Termine par la commande d'usage : `/tdd-forge:po <besoin>`.
