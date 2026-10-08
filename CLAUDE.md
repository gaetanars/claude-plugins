# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du dépôt

Marketplace Claude Code `gaetanars` (`.claude-plugin/marketplace.json`), un plugin par dossier sous `plugins/`. Plugin actuel : `tdd-forge`. README.md décrit installation, contribution et contrôles de CI.

Remote : `git@github.com:gaetanars/claude-plugins.git` (renommage depuis `tdd-forge` à faire côté GitHub), branche `main`. Langue du code, des prompts et des commits : français (messages au format `feat: …`).

## Règles de marketplace

- Version dans `plugins/<p>/.claude-plugin/plugin.json` uniquement (jamais dans l'entrée marketplace) ; **toute modification d'un plugin impose un bump semver** (contrôlé en CI sur les PR).
- Pas de `CLAUDE.md` dans un dossier de plugin : ce fichier racine porte les consignes de tous les plugins.
- Frontmatter des skills/agents en `clé: valeur` sur une ligne (le lecteur de `tests/_common.py` n'accepte rien d'autre).

## Validation

- `python3 -m unittest discover -s tests -t . -v` (un module par type d'élément ; `BASE_REF=origin/main` active le contrôle de bump). Même commande en CI (`.github/workflows/validate.yml`), qui ajoute `actionlint`.
- `claude plugin validate --strict .` ne valide que la marketplace ; chaque plugin se valide séparément (`claude plugin validate --strict plugins/<p>`), ce que fait `tests/test_cli_validate.py`.

## Plugin tdd-forge

Livraison autonome en TDD sur GitHub, indépendante de la stack : contrat de test = code de sortie + résultats JSON au format neutre (`results_path`), le projet portant lanceur, adaptateur, portes et méthodologie (`.forge/conventions.md`). Le contenu est du Markdown (agents, skills), du JS (workflow), du Python (hooks + moteur) et des assets copiés dans les projets cibles. `plugins/tdd-forge/README.md` décrit le parcours, les rôles et les garde-fous ; le lire avant toute modification structurelle.

- Pas d'exécution de bout en bout vérifiée (voir « À vérifier au premier lancement » dans README.md : options de `agent()`, format de `agent_type` reçu par les hooks, `SubagentStop`, règle de permission `Workflow(tdd-forge:deliver)`). Ne pas présenter ces points comme acquis.
- `forge.py` : `python3 plugins/tdd-forge/skills/init/assets/forge.py version` (sous-commandes : `status start red green tests-update review dispositions mark unblock context ship wait-merge approve backlog publish doctor gate version`).

### Architecture (tout sous `plugins/tdd-forge/`)

Le plugin est un pipeline à trois couches qui communiquent **uniquement par fichiers** (`.forge/backlog/<T>/` dans le projet cible : `spec.md`, `plan.md`, `review-n.json`, `state.json`, `journal.jsonl`) :

1. **Orchestrateur** `workflows/deliver.js` : script de workflow Claude Code, séquentiel par tâche, reprenable. Il ne décide rien lui-même : chaque étape appelle `forge.py status` pour connaître la prochaine étape (`STEPS`), lance l'agent du rôle concerné, puis un contrôle `forge.py`. Boucles rouge / vert / revue avec arrêt sur absence de progrès (`block()` → PR brouillon, chaîne stoppée).
2. **Moteur déterministe** `skills/init/assets/forge.py` (stdlib seule, copié dans `.forge/bin/forge.py` du projet cible par `/tdd-forge:init`) : worktrees `.forge/worktrees/T00x`, état/journal, accord figé (`approve` : empreinte sha256 de la spec), traçabilité `AC-n` dans les résultats de test, portes configurées, annulation des modifications interdites, empreinte du test d'acceptation, commit/push/PR/merge, `publish` (PR de connaissance produit), `doctor` (validation de la config). Toutes ses sorties sont du JSON sur stdout (`emit`) ; le workflow les parse. Config par projet : `.forge/config.json`, composée par `init` depuis `assets/config.example.json` et `skills/init/references/contract.md` (contrat d'intégration, pas du code : aucune branche par stack dans le moteur).
3. **Agents** `agents/*.md` (planner, test-writer, implementer, reviewer, learner, runner) : un fichier par rôle, avec modèle/effort/outils en frontmatter. Le `runner` (Haiku, sans CLAUDE.md, Bash seul) n'existe que pour exécuter `forge.py` sans interprétation.

Garde-fous en profondeur : `scripts/guard.py` (hook PreToolUse, périmètre d'écriture par rôle, ne s'applique qu'aux `agent_type` `tdd-forge:<rôle>` et seulement si `.forge/current` existe) ; `scripts/metrics.py` (hook SubagentStop → `.forge/metrics.jsonl`) ; contrôles de `forge.py` ; CI GitHub (`assets/forge-gates.yml`).

Skills (`skills/`) : `po` (point d'entrée, avec `templates/`), `init` (installation et mise à jour), `retro`, `conventions` (invariants du flux, impose la lecture de `.forge/conventions.md` du projet cible, où vit la méthodologie de test et de code).

Fichiers versionnés du projet cible : `PRODUCT.md`, `docs/product/decisions.md`, `docs/product/specs/T00x.md` (spec figée, commitée par `start` dans la PR de la tâche), `.forge/conventions.md`. Le runtime (`state.json`, journal, revues) reste local.

### Points de cohérence à respecter

- Le contrat JSON de `forge.py` (clés `ok`, `passed`, `blocked`, `approved`, `next`, `pr`, `state`…) est consommé par `deliver.js` : toute modification d'un côté impose de relire l'autre.
- Les périmètres d'écriture/commandes sont définis à deux endroits qui doivent rester alignés : `guard.py` (`ROLES`, `FORGE_READONLY`, `FORGE_PO_ONLY`, `GIT_WRITE`) et les `tools`/instructions de chaque `agents/*.md`.
- `forge.py` est versionné dans `assets/` mais exécuté depuis les projets cibles : une évolution doit passer par une mise à jour de la version (`VERSION`) et par `/tdd-forge:init` côté projet.
- GitHub uniquement (pas de GitLab), tâches séquentielles : limites assumées.
