# tdd-forge

Livraison autonome en TDD avec Claude Code, pour des dépôts Python et TypeScript sur GitHub.

Tu ne parles qu'au Product Owner. Il cadre, challenge et découpe ; tu valides les critères d'acceptation. Ensuite, la boucle tourne seule : plan, tests rouges, vert, refactor, revue indépendante, apprentissages, PR, merge si la CI est verte.

## Le parcours

```
/tdd-forge:cadrer <besoin>        ← toi + PO (Opus) : vision, challenge, découpage, specs validées
        │  « go »
        ▼
workflow tdd-forge:deliver        ← autonome, une tâche après l'autre
  Préparation   forge.py start          worktree .forge/worktrees/T001, branche forge/T001
  Plan          planner (Opus)          plan.md
  Rouge         test-writer (Sonnet)    tests d'acceptation (1 par AC-n) + unitaires
                forge.py red            échec réel exigé, hors-tests annulés, acceptation verrouillée
  Vert          implementer (Sonnet) ⇄ forge.py green   jusqu'au vert, tests intouchables
  Refactor      implementer ⇄ forge.py green
  Revue         reviewer (Opus) → review-n.json
                test-writer / implementer → dispositions (corrigé · refusé motivé · reporté)
                forge.py dispositions + green, nouveau tour tant qu'il reste du bloquant
  Apprentissage learner (Sonnet)        report.md + .forge/learnings.md
  Livraison     forge.py ship / wait-merge   PR, issues pour les reportés, merge si CI verte
```

## Rôles

| Élément | Modèle | Peut écrire | Rôle |
|---|---|---|---|
| skill `cadrer` | Opus | `PRODUCT.md`, specs | Product Owner, ton seul interlocuteur |
| `planner` | Opus, effort high | `plan.md` | plan de tests et d'implémentation |
| `test-writer` | Sonnet, high | fichiers de test (acceptation verrouillée après le rouge) | tests rouges, tests issus de la revue |
| `implementer` | Sonnet, high | code applicatif uniquement | vert, refactor, corrections de revue |
| `reviewer` | Opus, high | `review-n.json` | revue indépendante après les portes automatiques |
| `runner` | Haiku, low, sans CLAUDE.md | rien | exécute `forge.py`, rien d'autre |
| `learner` | Sonnet, medium | `report.md`, `.forge/learnings.md` | compound engineering |
| `forge.py` | aucun (déterministe) | commits, push, PR, merge | moteur, état, journal, contrôles |

## Les garde-fous, par couche

1. **Hook `guard.py`** (PreToolUse) : chaque agent n'écrit que dans son périmètre ; `git` en écriture et `gh` sont interdits aux agents ; le runner n'exécute que `forge.py`.
2. **Contrôles de `forge.py`** : toute modification de test ou de config par l'implémenteur est annulée et comptée comme violation ; l'empreinte du test d'acceptation est vérifiée à chaque contrôle ; la phase rouge exige un vrai échec.
3. **Portes déterministes** (format, lint, typage, tests, couverture) avant toute revue LLM : elles ne coûtent aucun token.
4. **CI GitHub** qui rejoue les mêmes portes, et protection de `main`.
5. **Merge automatique conditionné** à la CI verte. Sans CI, pas de merge.
6. **Arrêt sur absence de progrès** : deux tours sans amélioration (tests en échec, portes rouges, points bloquants) → PR en brouillon avec le motif, chaîne arrêtée.

## Installation

Prérequis : Claude Code 2.1.271 ou plus, `git`, `gh` authentifié, `python3` 3.9 ou plus, `uv` ou `node`.

1. Pousse ce dossier dans un dépôt GitHub à toi, par exemple `gaetan/tdd-forge`.
2. Dans Claude Code :
   ```
   /plugin marketplace add gaetan/tdd-forge
   /plugin install tdd-forge@tdd-forge
   ```
3. Dans chaque projet : `/tdd-forge:installer`. Il configure les portes, copie `forge.py`, écrit la CI et les permissions, vérifie la ligne de base et propose la protection de `main`.

Réglages conseillés dans ton `~/.claude/settings.json` : `"autoContinueAtUsageLimit": true`. Empêche la mise en veille pendant une livraison (macOS : `caffeinate -i` dans un terminal).

## Usage

- **Nouveau besoin** : `/tdd-forge:cadrer <ce que tu veux>`. Valide le bloc de specs, puis « go ».
- **Suivre** : `/workflows`, ou les PR sur GitHub depuis ton téléphone.
- **Reprendre après une interruption** : relance le workflow avec les mêmes tâches (`/tdd-forge:deliver` avec `{ "tasks": ["T001"] }`). Chaque tâche repart de sa dernière étape validée, même dans une nouvelle session.
- **Après un blocage** : lis la PR brouillon et `.forge/backlog/T00x/journal.jsonl`. Clarifie, ou crée une nouvelle tâche via le PO. Puis `python3 .forge/bin/forge.py unblock T00x` et relance.
- **Rétro du système** : `/tdd-forge:ameliorer`, toutes les dix tâches environ.

## Fichiers

```
PRODUCT.md                       vision produit, à toi (le PO propose, tu valides)
.forge/config.json               portes et paramètres            versionné
.forge/bin/forge.py              moteur                          versionné
.forge/learnings.md              apprentissages du projet        versionné, mis à jour par chaque PR
.forge/backlog/T001/             spec, plan, revues, dispositions, state.json, journal.jsonl   local
.forge/worktrees/T001/           copie de travail isolée         local, supprimée après merge
.forge/metrics.jsonl             tokens par agent et par tâche   local
.github/workflows/forge-gates.yml
```

Les agents échangent exclusivement par ces fichiers. `state.json` et `journal.jsonl` constituent la trace de chaque étape, et permettent la reprise.

## Consommation

Mesurée, sans plafond. Le hook `metrics.py` relève l'usage de chaque agent à sa sortie ; chaque PR affiche le total par agent ; la rétro repère les étapes qui dérivent. Leviers en place : runner sur Haiku sans CLAUDE.md, outils restreints par rôle, skills de conventions chargées à la demande, portes déterministes avant la revue, revue unique sur Opus.

## À vérifier au premier lancement

Ces points reposent sur la documentation de Claude Code, pas sur une exécution réelle de bout en bout :

- **Options de `agent()`** dans le workflow (`agentType`, `schema`, `label`) : lance `/workflow-authoring` et compare avec `workflows/deliver.js`.
- **Format de `agent_type`** reçu par les hooks (attendu : `tdd-forge:implementer`) : si `.forge/guard.log` reste vide alors qu'un agent sort de son périmètre, c'est ce format qui diffère.
- **`SubagentStop` sur les agents de workflow** : `.forge/metrics.jsonl` doit se remplir pendant une livraison.
- **Nom de la règle `Workflow(tdd-forge:deliver)`** dans les permissions : si une demande d'autorisation apparaît au lancement, accepte « always ».
- `claude plugin validate plugins/tdd-forge` avant la première installation.

Fais une première livraison sur une tâche minuscule, en restant devant l'écran.

## Limites de la v0.1

- **GitHub uniquement.** GitLab (`glab`, MR, auto-merge) n'est pas encore codé dans `forge.py`.
- **Tâches séquentielles** : pas de parallélisme, pour éviter les conflits entre branches auto-mergées.
- **Specs non versionnées** : `.forge/backlog/` reste local ; la PR conserve le rapport.
- **Contournement par le shell** : un agent qui modifierait un test via Bash n'est pas bloqué au moment même, mais la modification est annulée au contrôle suivant.
- **Relecteur de la même famille de modèles** que l'implémenteur : les portes déterministes et la CI restent le vrai filet.
