# tdd-forge

Livraison autonome en TDD avec Claude Code, sur GitHub, **indépendante de la stack** : le plugin porte le flux, le projet porte la technique (lanceur, framework, dossiers, types de tests, couverture, style).

> **Statut : v0.4, expérimental.** Le moteur (`forge.py`) et le hook (`guard.py`) sont couverts par des tests, mais la chaîne n'a pas encore tourné de bout en bout dans Claude Code. Lis [« À vérifier au premier lancement »](#à-vérifier-au-premier-lancement) avant de l'utiliser sur un dépôt qui compte. Il pousse des branches, ouvre des PR et peut les fusionner : essaie-le d'abord sur un dépôt jetable.

Quatre commandes :

| Commande | Rôle |
|---|---|
| `/tdd-forge:init` | Installe tout et mène le cadrage à deux voix (PO et architecte) : vision, qualités, stack, ADR, *walking skeleton* sur dépôt neuf ou rétro-documentation sur dépôt existant, portes, CI, protection de `main`, PR `chore/tdd-forge`. Idempotent : sert aussi à la mise à jour. |
| `/tdd-forge:po <besoin>` | Point d'entrée unique : triage, challenge, découpage, specs, accord, publication de la connaissance produit, lancement de la livraison. |
| `/tdd-forge:architect <sujet>` | Fait évoluer l'architecture : nouvelle ADR qui en remplace une autre (jamais de réécriture), publiée par PR. Le code à changer passe ensuite par le PO. |
| `/tdd-forge:retro` | Améliore le système (plugin, conventions du projet, portes) à partir des journaux, revues et consommations. |

Tu parles au Product Owner (le quoi) et, pour le comment d'ensemble, à l'architecte, que le PO consulte quand un besoin touche l'architecture. Le PO cadre et challenge ; tu donnes ton accord sur les critères d'acceptation. Ensuite la boucle tourne seule : plan, tests rouges, vert, refactor, revue indépendante, apprentissages, PR, merge si la CI est verte.

## Le parcours

```
/tdd-forge:po <besoin>            ← toi + PO (Opus)
  triage      forge.py backlog          bloquées, en cours, CI rouges
  challenge   PRODUCT.md, ARCHITECTURE.md (ADR), decisions.md, specs livrées, learnings
              impact d'architecture → consultation de l'architecte (Opus), ADR proposée
  specs       .forge/backlog/T001/spec.md
  accord      AskUserQuestion → forge.py approve   empreinte sha256 de la spec
  publication forge.py publish          PRODUCT.md, docs/product/, ARCHITECTURE.md, docs/architecture/ par PR séparée
        │  « go »
        ▼
workflow tdd-forge:deliver        ← autonome, une tâche après l'autre
  Préparation   forge.py start          worktree .forge/worktrees/T001, spec figée commitée
  Plan          planner (Opus)          plan.md (suit les ADR ; ÉCART-ADR ou DÉPASSEMENT → forge.py plan-check)
  Rouge         test-writer (Sonnet)    tests d'acceptation (un cas par AC-n) + autres tests du plan
                forge.py red            chaque AC-n a un cas en échec dans les résultats
  Vert          implementer (Sonnet) ⇄ forge.py green   chaque AC-n a un cas au vert
  Refactor      implementer ⇄ forge.py green
  Revue         reviewer (Opus) → review-n.json
                test-writer / implementer → dispositions (corrigé · refusé motivé · reporté)
  Apprentissage learner (Sonnet)        report.md + .forge/learnings.md
  Livraison     forge.py ship / wait-merge   PR, issues pour les reportés, merge si CI verte
```

## Contrat universel de test
Le plugin ne présuppose ni langage, ni lanceur, ni framework. Il exige seulement :

- une commande de test (`test_cmd`) dont le code de sortie reflète le résultat ;
- des **résultats au format neutre** à `results_path` (glob accepté, fichiers concaténés) :
  `{"cases": [{"name": "AC-1 refuse un montant négatif", "failed": true, "acs": ["AC-1"]}]}` ;
- des portes libres (`gates`), dont une marquée `"tests": true`, et les motifs `test_globs` et `acceptance_globs`.

Si le lanceur n'écrit pas ce format, la commande de test s'en charge ou `init` écrit un **adaptateur du projet** dans `.forge/adapters/` (versionné, protégé). `skills/init/references/contract.md` décrit le contrat complet ; `forge.py doctor` valide la config produite. Tout le *comment* (types de tests, granularité, couverture, style) est défini dans `.forge/conventions.md` du projet.

**Traçabilité** : `acs` (explicite) ou, à défaut, l'identifiant `AC-n` dans le nom du cas (insensible à la casse : `AC-1`, `ac1`, `AC_01`). En rouge, chaque AC doit avoir ≥ 1 cas en échec ; en vert, ≥ 1 cas et aucun en échec. Un AC absent est signalé nommément.

`python3` est l'outillage du *plugin* (moteur et hooks), pas un choix imposé au projet.

## Rôles

| Élément | Modèle | Peut écrire | Rôle |
|---|---|---|---|
| skill `po` | Opus | specs, `PRODUCT.md`, `docs/product/` | Product Owner : quoi et pourquoi |
| skill `architect` | Opus | `ARCHITECTURE.md`, `docs/architecture/adr/`, squelette | Architecte : stack, structure, outillage de test, ADR, portes d'architecture ; dialogue avec toi, donc dans la conversation |
| `planner` | Opus, medium | `plan.md` | planificateur technique : plan de tests et d'implémentation, dans le cadre des ADR |
| `test-writer` | Sonnet, medium | fichiers de test (acceptation verrouillée après le rouge) | tests rouges, tests issus de la revue |
| `implementer` | Sonnet, medium | code applicatif uniquement | vert, refactor, corrections de revue |
| `reviewer` | Opus, medium | `review-n.json` | revue indépendante après les portes automatiques |
| `runner` | Haiku, low, sans CLAUDE.md | rien | exécute `forge.py`, rien d'autre (un workflow n'a pas d'accès shell) |
| `learner` | Sonnet, low | `report.md`, `.forge/learnings.md` | compound engineering |
| `forge.py` | aucun (déterministe) | commits, push, PR, merge | moteur, état, journal, contrôles |

## Les garde-fous, par couche

1. **Accord figé** : `forge.py approve` enregistre l'empreinte sha256 de la spec ; `status` refuse toute spec non approuvée ou modifiée depuis. `approve` et `publish` sont interdits à tous les sous-agents.
2. **Hook `guard.py`** (PreToolUse) : chaque agent n'écrit que dans son périmètre (`PRODUCT.md`, `ARCHITECTURE.md`, `docs/product/` et `docs/architecture/` hors de portée de l'implémenteur et du rédacteur de tests) ; `git` en écriture et `gh` sont interdits aux agents ; le runner n'exécute que `forge.py`.
3. **Contrôles de `forge.py`** : toute modification de test ou de config par l'implémenteur est annulée et comptée comme violation ; l'empreinte du test d'acceptation est vérifiée ; la phase rouge exige un échec par AC.
4. **ADR** : le planificateur suit les ADR acceptées et signale `ÉCART-ADR NNNN` sinon ; `forge.py plan-check` (lecture seule) arrête alors la tâche, comme un `DÉPASSEMENT` ; le relecteur traite une violation d'ADR comme `bloquant`. Une ADR acceptée ne change que par une nouvelle ADR.
5. **Portes du projet** (déterministes) avant toute revue LLM.
6. **CI GitHub** qui rejoue les mêmes portes, et protection de `main`.
7. **Merge automatique conditionné** à la CI verte. Sans CI, pas de merge.
8. **Arrêt sur absence de progrès** : deux tours sans amélioration → PR en brouillon avec le motif, chaîne arrêtée. Le PO trie les blocages en début de session.

## Installation

Prérequis : Claude Code 2.1.271 ou plus, `git`, `gh` authentifié, `python3` 3.9 ou plus (outillage du plugin, quelle que soit la stack du projet), l'outillage de la stack.

1. Dans Claude Code :
   ```
   /plugin marketplace add gaetanars/claude-plugins
   /plugin install tdd-forge@gaetanars
   ```
2. Dans chaque projet : `/tdd-forge:init`. Sur un dépôt neuf, le PO mène l'entretien de vision, puis l'architecte propose la stack avec options, contradicteur et ADR (tu tranches) et pose un *walking skeleton* de bout en bout ; sur un dépôt existant il documente l'architecture sans rien restructurer.

Réglages conseillés dans ton `~/.claude/settings.json` : `"autoContinueAtUsageLimit": true`. Empêche la mise en veille pendant une livraison (macOS : `caffeinate -i`).

## Usage

- **Faire évoluer l'architecture** : `/tdd-forge:architect <sujet>`.
- **Nouveau besoin** : `/tdd-forge:po <ce que tu veux>`. Réponds au bloc de specs, puis « go ».
- **Suivre** : `/workflows`, ou les PR sur GitHub depuis ton téléphone.
- **Reprendre après une interruption** : relance le workflow avec les mêmes tâches (`/tdd-forge:deliver` avec `{ "tasks": ["T001"] }`). Chaque tâche repart de sa dernière étape validée, même dans une nouvelle session.
- **Après un blocage** : lance `/tdd-forge:po` ; il lit la PR brouillon et le journal, puis te propose de clarifier, de créer une tâche corrective ou de `forge.py unblock T00x`.
- **Mise à jour du plugin** : `/tdd-forge:init` (le moteur est copié dans le projet ; `doctor` signale tout écart de version).
- **Rétro** : `/tdd-forge:retro`, toutes les dix tâches environ.

## Fichiers

```
PRODUCT.md                       vision produit (amendée avec ton accord)          versionné
ARCHITECTURE.md                  qualités, stack, structure, index des ADR         versionné
docs/architecture/adr/           ADR (alternatives rejetées, réexamen, règle)      versionné
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
- **Chargement d'une skill par une autre** (`Skill` depuis `init` et `po` vers `architect`) et `allowed-tools` effectifs de ces skills. À défaut, `init` et `po` lisent `../architect/SKILL.md`, comme ils lisent déjà `../po/templates`.
- **ADR publiée après le démarrage d'une tâche** : le worktree part de l'état de `main` à `start` ; après un `ÉCART-ADR`, vérifie que l'ADR remplaçante figure dans le worktree (sinon redémarre la tâche sur une base à jour).
- **`AskUserQuestion` dans une skill** (`po`, `init`, `architect`, `retro`) : sinon, l'accord se demande en texte (« ok » / « ok sauf n »), sans changer le parcours.
- `claude plugin validate --strict plugins/tdd-forge` avant la première installation.

Fais une première livraison sur une tâche minuscule, en restant devant l'écran. Un dépôt jetable avec un simple script qui écrit `results.json` prouve qu'aucune techno n'est présupposée.

## Contribuer

Voir le [README de la marketplace](../../README.md#contribuer). Les points de cohérence (contrat JSON `forge.py` ⇄ `deliver.js`, périmètres de `guard.py` ⇄ `agents/*.md`) sont décrits dans le `CLAUDE.md` racine. Toute modification du plugin impose d'incrémenter `version` dans `.claude-plugin/plugin.json`. Les tests (`tests/test_forge.py`, `tests/test_guard.py`) tournent avec la commande de validation de la marketplace.

## Limites

- **GitHub uniquement.** GitLab n'est pas codé dans `forge.py`.
- **Tâches séquentielles** : pas de parallélisme, pour éviter les conflits entre branches auto-mergées.
- **Tests intégrés aux fichiers source** (ex. Rust `#[cfg(test)]`) : incompatibles avec la séparation des rôles par fichiers. C'est une limite du flux, pas d'un langage.
- **Moteur et hooks en Python** : outillage du plugin, sans contrainte sur le projet.
- **Contournement par le shell** : un agent qui modifierait un test via Bash n'est pas bloqué au moment même, mais la modification est annulée au contrôle suivant.
- **Relecteur de la même famille de modèles** que l'implémenteur : les portes déterministes et la CI restent le vrai filet.

## Licence

[MIT](LICENSE).
