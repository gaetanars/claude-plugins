# tdd-forge

Livraison autonome en TDD avec Claude Code, sur GitHub, **indépendante du langage** : Python, TypeScript/JS, Go, Rust, Java/Kotlin, .NET, Ruby, PHP.

> **Statut : v0.2, expérimental.** Le moteur (`forge.py`) et le hook (`guard.py`) sont couverts par des tests, mais la chaîne n'a pas encore tourné de bout en bout dans Claude Code. Lis [« À vérifier au premier lancement »](#à-vérifier-au-premier-lancement) avant de l'utiliser sur un dépôt qui compte. Il pousse des branches, ouvre des PR et peut les fusionner : essaie-le d'abord sur un dépôt jetable.

Trois commandes :

| Commande | Rôle |
|---|---|
| `/tdd-forge:init` | Installe tout et initialise le PO : entretien de vision, stack, squelette sur dépôt vide, portes, CI, protection de `main`, PR `chore/tdd-forge`. Idempotent : sert aussi à la mise à jour. |
| `/tdd-forge:po <besoin>` | Point d'entrée unique : triage, challenge, découpage, specs, accord, publication de la connaissance produit, lancement de la livraison. |
| `/tdd-forge:retro` | Améliore le système (plugin, conventions du projet, portes) à partir des journaux, revues et consommations. |

Tu ne parles qu'au Product Owner. Il cadre et challenge ; tu donnes ton accord sur les critères d'acceptation. Ensuite la boucle tourne seule : plan, tests rouges, vert, refactor, revue indépendante, apprentissages, PR, merge si la CI est verte.

## Le parcours

```
/tdd-forge:po <besoin>            ← toi + PO (Opus)
  triage      forge.py backlog          bloquées, en cours, CI rouges
  challenge   PRODUCT.md, decisions.md, specs livrées, learnings
  specs       .forge/backlog/T001/spec.md
  accord      AskUserQuestion → forge.py approve   empreinte sha256 de la spec
  publication forge.py publish          PRODUCT.md + docs/product/ par PR séparée
        │  « go »
        ▼
workflow tdd-forge:deliver        ← autonome, une tâche après l'autre
  Préparation   forge.py start          worktree .forge/worktrees/T001, spec figée commitée
  Plan          planner (Opus)          plan.md
  Rouge         test-writer (Sonnet)    tests d'acceptation (un testcase par AC-n) + unitaires
                forge.py red            chaque AC-n a un testcase en échec dans le JUnit
  Vert          implementer (Sonnet) ⇄ forge.py green   chaque AC-n a un testcase au vert
  Refactor      implementer ⇄ forge.py green
  Revue         reviewer (Opus) → review-n.json
                test-writer / implementer → dispositions (corrigé · refusé motivé · reporté)
  Apprentissage learner (Sonnet)        report.md + .forge/learnings.md
  Livraison     forge.py ship / wait-merge   PR, issues pour les reportés, merge si CI verte
```

## Contrat universel de test

Une porte `tests` du `.forge/config.json` exécute les tests, sort en erreur s'ils échouent et écrit un **rapport JUnit XML** (`junit_path`, glob accepté). `forge.py` lit ce rapport : il n'y a aucune branche de code par langage. `skills/init/references/ecosystems.md` donne, par écosystème, le lanceur, l'option JUnit, le format, le lint, le typage, la couverture, la CI, les `test_globs` et les marqueurs de suppression ; `forge.py doctor` valide la config produite. Un écosystème sans JUnit n'est pas pris en charge.

**Traçabilité** : l'identifiant `AC-n` (insensible à la casse : `AC-1`, `ac1`, `AC_01`) figure dans le nom ou la classe du testcase. En rouge, chaque AC doit avoir ≥ 1 testcase en échec ; en vert, ≥ 1 testcase et aucun en échec. Un AC absent est signalé nommément.

## Rôles

| Élément | Modèle | Peut écrire | Rôle |
|---|---|---|---|
| skill `po` | Opus | specs, `PRODUCT.md`, `docs/product/` | Product Owner, ton seul interlocuteur |
| `planner` | Opus, medium | `plan.md` | plan de tests et d'implémentation |
| `test-writer` | Sonnet, medium | fichiers de test (acceptation verrouillée après le rouge) | tests rouges, tests issus de la revue |
| `implementer` | Sonnet, medium | code applicatif uniquement | vert, refactor, corrections de revue |
| `reviewer` | Opus, medium | `review-n.json` | revue indépendante après les portes automatiques |
| `runner` | Haiku, low, sans CLAUDE.md | rien | exécute `forge.py`, rien d'autre (un workflow n'a pas d'accès shell) |
| `learner` | Sonnet, low | `report.md`, `.forge/learnings.md` | compound engineering |
| `forge.py` | aucun (déterministe) | commits, push, PR, merge | moteur, état, journal, contrôles |

## Les garde-fous, par couche

1. **Accord figé** : `forge.py approve` enregistre l'empreinte sha256 de la spec ; `status` refuse toute spec non approuvée ou modifiée depuis. `approve` et `publish` sont interdits à tous les sous-agents.
2. **Hook `guard.py`** (PreToolUse) : chaque agent n'écrit que dans son périmètre (`docs/product/` hors de portée de l'implémenteur et du rédacteur de tests) ; `git` en écriture et `gh` sont interdits aux agents ; le runner n'exécute que `forge.py`.
3. **Contrôles de `forge.py`** : toute modification de test ou de config par l'implémenteur est annulée et comptée comme violation ; l'empreinte du test d'acceptation est vérifiée ; la phase rouge exige un échec par AC.
4. **Portes déterministes** (format, lint, typage, tests, couverture) avant toute revue LLM.
5. **CI GitHub** qui rejoue les mêmes portes, et protection de `main`.
6. **Merge automatique conditionné** à la CI verte. Sans CI, pas de merge.
7. **Arrêt sur absence de progrès** : deux tours sans amélioration → PR en brouillon avec le motif, chaîne arrêtée. Le PO trie les blocages en début de session.

## Installation

Prérequis : Claude Code 2.1.271 ou plus, `git`, `gh` authentifié, `python3` 3.9 ou plus (même pour un dépôt Go ou Rust), l'outillage de la stack.

1. Dans Claude Code :
   ```
   /plugin marketplace add gaetanars/claude-plugins
   /plugin install tdd-forge@gaetanars
   ```
2. Dans chaque projet : `/tdd-forge:init`. Sur un dépôt vide il mène l'entretien de vision, propose une stack et crée un squelette minimal avec un test de fumée.

Réglages conseillés dans ton `~/.claude/settings.json` : `"autoContinueAtUsageLimit": true`. Empêche la mise en veille pendant une livraison (macOS : `caffeinate -i`).

## Usage

- **Nouveau besoin** : `/tdd-forge:po <ce que tu veux>`. Réponds au bloc de specs, puis « go ».
- **Suivre** : `/workflows`, ou les PR sur GitHub depuis ton téléphone.
- **Reprendre après une interruption** : relance le workflow avec les mêmes tâches (`/tdd-forge:deliver` avec `{ "tasks": ["T001"] }`). Chaque tâche repart de sa dernière étape validée, même dans une nouvelle session.
- **Après un blocage** : lance `/tdd-forge:po` ; il lit la PR brouillon et le journal, puis te propose de clarifier, de créer une tâche corrective ou de `forge.py unblock T00x`.
- **Mise à jour du plugin** : `/tdd-forge:init` (le moteur est copié dans le projet ; `doctor` signale tout écart de version).
- **Rétro** : `/tdd-forge:retro`, toutes les dix tâches environ.

## Fichiers

```
PRODUCT.md                       vision produit (amendée avec ton accord)          versionné
docs/product/decisions.md        journal des décisions client/PO                   versionné
docs/product/specs/T001.md       spec figée, commitée dans la PR de sa tâche       versionné
.forge/config.json               portes et paramètres                              versionné
.forge/conventions.md            conventions du projet (généré par init)           versionné
.forge/bin/forge.py              moteur                                            versionné
.forge/learnings.md              apprentissages, mis à jour par chaque PR          versionné
.github/workflows/forge-gates.yml
.forge/backlog/T001/             spec en cours, plan, revues, state.json, journal  local
.forge/worktrees/T001/           copie de travail isolée                           local, supprimée après merge
.forge/metrics.jsonl, guard.log  consommation et refus du hook                     local
```

Les capacités livrées = les specs présentes sur `main`. Les agents échangent exclusivement par fichiers ; `state.json` et `journal.jsonl` constituent la trace de chaque étape et permettent la reprise.

## Consommation

Mesurée, avec des plafonds de tours (pas de plafond de tokens). Le hook `metrics.py` relève l'usage de chaque agent à sa sortie ; chaque PR affiche le total par agent ; la rétro repère les étapes qui dérivent. Leviers : runner sur Haiku sans CLAUDE.md, outils restreints par rôle, skill `conventions` chargée à la demande, portes déterministes avant la revue, revue unique sur Opus, effort medium par défaut, plafonds de tours dans `deliver.js` (5 corrections vertes par phase, 3 tours de revue).

## À vérifier au premier lancement

Ces points reposent sur la documentation de Claude Code, pas sur une exécution réelle de bout en bout :

- **Option `agentType` de `agent()`** dans le workflow (avec `schema` et `label`) : lance `/workflow-authoring` et compare avec `workflows/deliver.js`.
- **`agent_type` reçu par les hooks** pour un agent lancé par un workflow : attendu `tdd-forge:<rôle>` (confirmé par la doc pour un agent de plugin, pas pour un agent de workflow). Si `.forge/guard.log` reste vide alors qu'un agent sort de son périmètre, c'est ce format qui diffère.
- **`SubagentStop` sur les agents de workflow** : `.forge/metrics.jsonl` doit se remplir pendant une livraison.
- **Forme de la règle `Workflow(tdd-forge:deliver)`** dans les permissions : si une demande d'autorisation apparaît au lancement, accepte « always ».
- **Lancement du workflow depuis la skill `po`** : sinon, le PO donne la commande `/tdd-forge:deliver`.
- **`AskUserQuestion` dans une skill** (`po`, `init`, `retro`) : sinon, l'accord se demande en texte (« ok » / « ok sauf n »), sans changer le parcours.
- `claude plugin validate --strict plugins/tdd-forge` avant la première installation.

Fais une première livraison sur une tâche minuscule, en restant devant l'écran. Un dépôt jetable Python et un Go prouvent le multi-langage.

## Contribuer

Voir le [README de la marketplace](../../README.md#contribuer). Les points de cohérence (contrat JSON `forge.py` ⇄ `deliver.js`, périmètres de `guard.py` ⇄ `agents/*.md`) sont décrits dans le `CLAUDE.md` racine. Toute modification du plugin impose d'incrémenter `version` dans `.claude-plugin/plugin.json`. Les tests (`tests/test_forge.py`, `tests/test_guard.py`) tournent avec la commande de validation de la marketplace.

## Limites

- **GitHub uniquement.** GitLab n'est pas codé dans `forge.py`.
- **Tâches séquentielles** : pas de parallélisme, pour éviter les conflits entre branches auto-mergées.
- **JUnit obligatoire** : un écosystème sans rapport JUnit n'est pas pris en charge. Les tests unitaires placés dans les fichiers source (Rust `#[cfg(test)]`) ne sont pas reconnus comme tests par `test_globs` : préfère `tests/`.
- **Contournement par le shell** : un agent qui modifierait un test via Bash n'est pas bloqué au moment même, mais la modification est annulée au contrôle suivant.
- **Relecteur de la même famille de modèles** que l'implémenteur : les portes déterministes et la CI restent le vrai filet.

## Licence

[MIT](LICENSE).
