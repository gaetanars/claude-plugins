# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

Marketplace + plugin Claude Code (`tdd-forge`, v0.1.0) : livraison autonome en TDD pour dépôts Python/TypeScript sur GitHub. Ce dépôt ne contient **pas** d'application : il n'y a ni build, ni lint, ni suite de tests. Le contenu est du Markdown (agents, skills), du JS (workflow), du Python (hooks + moteur) et des assets copiés dans les projets cibles. README.md (français) décrit le parcours, les rôles et les garde-fous ; le lire avant toute modification structurelle.

Le dossier racine contient aussi les fichiers d'un dépôt git nu (`HEAD`, `objects/`, `hooks/`, `refs/`…) à côté de l'arbre de travail : ce sont des artefacts du dépôt, pas du code du plugin. Remote : `git@github.com:gaetanars/tdd-forge.git`, branche `main`. Langue du code, des prompts et des commits : français (messages au format `feat: …`).

## Validation

- Seule vérification outillée : `claude plugin validate plugins/tdd-forge`.
- Pas d'exécution de bout en bout vérifiée (voir « À vérifier au premier lancement » dans README.md : options de `agent()`, format de `agent_type` reçu par les hooks, `SubagentStop`, règle de permission `Workflow(tdd-forge:deliver)`). Ne pas présenter ces points comme acquis.
- `forge.py` : `python3 plugins/tdd-forge/skills/installer/assets/forge.py version` (sous-commandes : `status start red green tests-update review dispositions mark unblock context ship wait-merge version`).

## Architecture (tout sous `plugins/tdd-forge/`)

Le plugin est un pipeline à trois couches qui communiquent **uniquement par fichiers** (`.forge/backlog/<T>/` dans le projet cible : `spec.md`, `plan.md`, `review-n.json`, `state.json`, `journal.jsonl`) :

1. **Orchestrateur** `workflows/deliver.js` : script de workflow Claude Code, séquentiel par tâche, reprenable. Il ne décide rien lui-même : chaque étape appelle `forge.py status` pour connaître la prochaine étape (`STEPS`), lance l'agent du rôle concerné, puis un contrôle `forge.py`. Boucles rouge / vert / revue avec arrêt sur absence de progrès (`block()` → PR brouillon, chaîne stoppée).
2. **Moteur déterministe** `skills/installer/assets/forge.py` (stdlib seule, copié dans `.forge/bin/forge.py` du projet cible par `/tdd-forge:installer`) : worktrees `.forge/worktrees/T00x`, état/journal, exécution des portes configurées, annulation des modifications interdites, empreinte du test d'acceptation, commit/push/PR/merge. Toutes ses sorties sont du JSON sur stdout (`emit`) ; le workflow les parse. Config par projet : `assets/config.{python,typescript}.json`.
3. **Agents** `agents/*.md` (planner, test-writer, implementer, reviewer, learner, runner) : un fichier par rôle, avec modèle/effort/outils en frontmatter. Le `runner` (Haiku, sans CLAUDE.md, Bash seul) n'existe que pour exécuter `forge.py` sans interprétation.

Garde-fous en profondeur : `scripts/guard.py` (hook PreToolUse, périmètre d'écriture par rôle, ne s'applique qu'aux `agent_type` `tdd-forge:<rôle>` et seulement si `.forge/current` existe) ; `scripts/metrics.py` (hook SubagentStop → `.forge/metrics.jsonl`) ; contrôles de `forge.py` ; CI GitHub (`assets/forge-gates-*.yml`).

Skills (`skills/`) : `cadrer` (PO, avec `templates/PRODUCT.md` et `spec.md`), `installer`, `ameliorer` (rétro), `conventions-python` / `conventions-typescript` (chargées à la demande).

## Points de cohérence à respecter

- Le contrat JSON de `forge.py` (clés `ok`, `passed`, `blocked`, `approved`, `next`, `pr`, `state`…) est consommé par `deliver.js` : toute modification d'un côté impose de relire l'autre.
- Les périmètres d'écriture/commandes sont définis à deux endroits qui doivent rester alignés : `guard.py` (`ROLES`, `FORGE_READONLY`, `GIT_WRITE`) et les `tools`/instructions de chaque `agents/*.md`.
- `forge.py` est versionné dans `assets/` mais exécuté depuis les projets cibles : une évolution doit passer par une mise à jour de la version (`VERSION`) et par `/tdd-forge:installer` côté projet.
- GitHub uniquement (pas de GitLab), tâches séquentielles : limites assumées en v0.1.
