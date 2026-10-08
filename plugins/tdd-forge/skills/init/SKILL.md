---
name: init
description: Installe, initialise ou met à jour tdd-forge dans le dépôt courant, quelle que soit la stack — cadrage conjoint PO et architecte (vision, stack, ADR, squelette), adaptateur de résultats, portes, moteur forge.py, conventions, CI GitHub, permissions, protection de branche. À lancer avec /tdd-forge:init, puis après chaque mise à jour du plugin.
disable-model-invocation: true
model: opus
allowed-tools: Read Grep Glob Write Edit AskUserQuestion Skill WebSearch WebFetch Bash(git *) Bash(gh *) Bash(cp *) Bash(mkdir *) Bash(python3 *)
---

# Initialiser tdd-forge

Les fichiers à copier sont dans `assets/`, le contrat d'intégration dans `references/contract.md` (de cette skill). Français, court. Une question à la fois ; les changements en masse se présentent en un bloc numéroté que Gaëtan valide (« ok » ou « ok sauf… »), par `AskUserQuestion` quand les options sont nettes.

## 0. Mode

Détecte le mode et annonce-le en une ligne :

- **neuf** : dépôt sans code (vide, ou seulement README/LICENSE) ;
- **existant** : du code, pas de `.forge/config.json` ;
- **mise à jour** : `.forge/config.json` existe. On écrase `forge.py`, on montre le diff de la config et des fichiers générés, on ne réécrit ni `PRODUCT.md`, ni les conventions, ni la config sans accord.

## 1. Prérequis

Liste en une ligne chacun : `git`, `python3` (3.9 ou plus : outillage du plugin, quelle que soit la stack), `gh auth status`, les outils de la stack, `claude --version` (2.1.271 ou plus : `omitClaudeMd` et les workflows reprenables l'exigent). Remote `origin` sur GitHub (GitLab n'est pas pris en charge). Un prérequis manque : dis comment l'installer et arrête-toi.

## 2. Cadrage à deux voix

Le cadrage se mène à deux rôles : `[PO]` (valeur, périmètre) et `[Architecte]` (comment). Étiquette chaque intervention, une question à la fois. Trois temps :

1. **Vision**, menée par `[PO]` (mode neuf) : modèle `../po/templates/PRODUCT.md`, avec le challenge de `../po/SKILL.md` §3. Propose une rédaction d'une page au plus ; `PRODUCT.md` est écrit après le « ok ». Copie aussi `../po/templates/decisions.md` vers `docs/product/decisions.md`.
2. **Qualités et contraintes**, en conjoint : volumétrie, sécurité et données, déploiement, budget, compétences du client, échéances. Chacun peut challenger le client et l'autre rôle.
3. **Architecture**, menée par `[Architecte]` : charge la skill `tdd-forge:architect` (à défaut, lis `../architect/SKILL.md`) en mode **cadrage** (neuf) ou **rétro-documentation** (existant). Elle produit les ADR, `ARCHITECTURE.md` et, sur dépôt neuf, le *walking skeleton*. Aucune stack n'est exclue : seul compte le contrat de `references/contract.md`.

**Mise à jour** : signale les écarts entre le dépôt et ce qui est consigné, ne réécris rien sans accord ; si `ARCHITECTURE.md` manque, crée-le par rétro-documentation.

## 4. Configuration

Pars de `assets/config.example.json` et compose `.forge/config.json` à partir des outils **déjà présents** : `stack` (libellé informatif), `test_cmd`, `results_path`, `gates`, `test_globs`, `acceptance_globs`, `suppression_markers`. Branche par défaut réelle (`git symbolic-ref refs/remotes/origin/HEAD`).

- **Résultats** : si le lanceur ne produit pas le format neutre, écris l'adaptateur dans `.forge/adapters/` (versionné, jamais dans `.gitignore`) et enchaîne-le dans `test_cmd` en conservant le code de sortie du lanceur.
- **Portes et couverture** : `[Architecte]` les propose (format, lint, typage, sécurité, seuil de couverture éventuel, et une porte d'architecture quand un outil existe pour la stack) ; Gaëtan décide de chacune. Aucun seuil par défaut. Rien n'est affaibli par rapport à l'existant.
- **Mise à jour** : si la config contient `junit_path` ou `acceptance_dir`, migre vers un adaptateur + `results_path` et vers `acceptance_globs`, en montrant le diff.

Présente la configuration, l'adaptateur éventuel et les dépendances de dev à ajouter, attends le « ok ».

## 5. Écriture (après « ok »)

1. `.forge/bin/forge.py` ← `assets/forge.py` (écrase : c'est la mise à jour du moteur).
   `ARCHITECTURE.md` et `docs/architecture/adr/` ← livrables de l'architecte validés (modèles `../architect/templates/`), sans écraser l'existant sans accord.
2. `.forge/config.json` ← la configuration validée (si elle existe : montre le diff, n'écrase qu'avec accord).
3. `.forge/conventions.md` ← `assets/conventions.md` rempli pour le projet à partir des décisions validées (commandes, structure, lien test ↔ `AC-n` avec un exemple, stratégie de test, code, pièges ; les propositions par défaut sont soumises à validation), seulement s'il n'existe pas.
4. `.forge/learnings.md` ← `assets/learnings.md`, seulement s'il n'existe pas.
5. `.gitignore` ← ajoute les lignes de `assets/gitignore.txt` absentes.
6. `.claude/settings.json` ← fusionne `assets/settings.json` (ajoute, ne retire rien) sans autoriser d'avance les lanceurs de la stack : Gaëtan approuve ces commandes au cas par cas.
7. `.github/workflows/forge-gates.yml` ← `assets/forge-gates.yml` dont le bloc `# setup … # endsetup` est remplacé par le setup CI du projet (toolchain, dépendances). Vérifie la dernière version majeure de chaque action.
8. Exclusions : les worktrees vivent dans `.forge/worktrees/`. Vérifie que les outils ne les parcourent pas depuis le checkout principal (`references/contract.md`).
9. `.forge/adapters/` si besoin, dépendances de dev, emplacement des tests d'acceptation couvert par `acceptance_globs` (avec le fichier d'amorce qu'exige la stack).

## 6. Contrôles

1. `python3 .forge/bin/forge.py doctor --plugin-version <version de .claude-plugin/plugin.json du plugin>` : résultats au format neutre lisibles avec au moins un cas, remote GitHub, `gh`, version du moteur. Corrige la config jusqu'au vert ; c'est le contrôle déterministe de ce que tu viens d'écrire.
2. `python3 .forge/bin/forge.py gate` : verte sur `main` avant toute livraison. Sinon, liste les échecs et propose d'en faire la première tâche via `/tdd-forge:po`.

## 7. GitHub (accord explicite, une action à la fois)

1. `gh repo edit --enable-auto-merge --delete-branch-on-merge`.
2. Protection de `main` exigeant le contrôle `gates` :
   `gh api -X PUT repos/{owner}/{repo}/branches/<branche>/protection --input -` avec
   `{"required_status_checks": {"strict": true, "contexts": ["gates"]}, "enforce_admins": true, "required_pull_request_reviews": null, "restrictions": null}`.
   Préviens : `enforce_admins` empêche aussi Gaëtan de pousser directement sur `main`. Sur un dépôt privé, la protection dépend du plan GitHub ; si l'API la refuse, forge.py surveille lui-même la CI et ne merge que si elle est verte.
3. Portes de sécurité, **proposées, jamais imposées** : `osv-scanner` (dépendances) et `gitleaks` (secrets), comme portes supplémentaires de `gates` si Gaëtan les veut.
4. Commit de l'initialisation (architecture et squelette compris) sur une branche `chore/tdd-forge` et PR, que Gaëtan merge lui-même. Les fichiers du système ne passent jamais par le merge automatique. Aucun push sans son accord.

## 8. Suite

Termine par la commande d'usage : `/tdd-forge:po <besoin>`.
