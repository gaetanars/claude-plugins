# Marketplace Claude Code de gaetanars

Marketplace de plugins [Claude Code](https://code.claude.com), validée en CI à chaque PR.

## Plugins

| Plugin | Où l'installer | Version | Description |
|---|---|---|---|
| `sdlc-contract` | poste et serveur | 0.1.0 | Contrat partagé : gabarits brief/spec/plan/ADR, schéma de verdict, conventions, contrat `.claude/check.json`, `sdlc-validate-spec`, `sdlc-init-repo`. |
| `sdlc-framing` | poste | 0.1.0 | Skills `challenger` (idéation) et `po` (cadrage), `sdlc-publish` (spec → issue GitHub). Dépend de `sdlc-contract`. |
| [`sdlc-factory`](plugins/sdlc-factory/README.md) | serveur | 0.1.0 | Agents planner/implementer/reviewers/retro, orchestrateur `sdlc-run`, `sdlc-retro`, garde-fous, unités systemd. Dépend de `sdlc-contract`. Expérimental. |

## Parcours SDLC

Tu n'interviens qu'en idéation et cadrage (poste) ; un automate (serveur) fait plan → implémentation → check → 3 revues → PR. **Le merge est humain par défaut.**

```
POSTE (toi)                                         SERVEUR (automate)
/sdlc-framing:challenger  → brief.md
/sdlc-framing:po          → spec.md + ambiguities.md
sdlc-publish publish <id> → push main + issue [<id>] + label `ready` EN DERNIER
                                                    sdlc-run (timer) : issue `ready`, dépendances fermées
                                                    ├─ setup : `needs-human` si .claude/check.json absent ou au gabarit
                                                    ├─ planner (Opus)       → plan.md + ADR
                                                    ├─ implementer (Sonnet) → commits TDD
                                                    ├─ check (lancé par l'orchestrateur, sans jeton) : rouge → retour à l'implementer
                                                    ├─ 3 reviewers en parallèle (contexte vierge) → verdicts JSON liés au SHA
                                                    ├─ rejet : corrige ; 3 itérations max (check rouge compris), sinon `needs-human`
                                                    └─ push, PR, statut `sdlc/verdicts`, label `in-review` → TU FUSIONNES
                                                       (opt-in par dépôt : `owner/repo automerge` → auto-merge GitHub armé)
                                                    ambiguïté → `needs-clarification` ; tu réponds, tu remets `ready`
sdlc-retro (hebdo) → PR sur CE dépôt : améliorations des prompts/skills/gabarits, preuves à l'appui, runs en échec inclus
```

Installation poste : `/plugin install sdlc-framing@gaetanars` (`sdlc-contract` suit en dépendance), puis dans un projet `sdlc-init-repo scaffold` (renseigner `CLAUDE.md` et `.claude/check.json`). Installation serveur et garde-fous : [`plugins/sdlc-factory/README.md`](plugins/sdlc-factory/README.md).

## Installation

Dans Claude Code :

```
/plugin marketplace add gaetanars/claude-plugins
/plugin install sdlc-framing@gaetanars
```

Équivalent en ligne de commande : `claude plugin marketplace add gaetanars/claude-plugins` puis `claude plugin install sdlc-framing@gaetanars`.

> **Retrait de `cadre`** : le plugin est remplacé par les plugins SDLC (historique git conservé). `claude plugin uninstall cadre@gaetanars` avant d'installer `sdlc-framing`. Le contrat `.claude/check.json` est repris sans `acceptance_dir`.

> **Retrait de `tdd-forge`** : déjà remplacé (historique git conservé) ; `claude plugin uninstall tdd-forge@gaetanars` s'il est encore installé.

> **Migration** : la marketplace s'appelait `tdd-forge` (dépôt `gaetanars/tdd-forge`). Retire l'ancienne (`claude plugin marketplace remove tdd-forge`) puis réinstalle avec les commandes ci-dessus.

## Mise à jour

L'auto-update est désactivé par défaut pour une marketplace tierce :

```
claude plugin marketplace update gaetanars
claude plugin update sdlc-framing@gaetanars
```

## Structure

```
.claude-plugin/marketplace.json   catalogue (nom, propriétaire, plugins)
plugins/<plugin>/                 un dossier par plugin
  .claude-plugin/plugin.json      manifeste, seule source de la version
  skills/ agents/ commands/ hooks/ workflows/ …
tests/                            validation des éléments et tests SDLC (unittest, stdlib) ; sdlc_fakebin/ = faux gh/claude
.github/workflows/validate.yml    CI
```

## Contribuer

Ajouter ou modifier un plugin :

1. Créer `plugins/<nom>/` avec `.claude-plugin/plugin.json` (`name` = nom du dossier, `version` semver `X.Y.Z`, `description`, `author`, `license`).
2. Déclarer le plugin dans `.claude-plugin/marketplace.json` (`name`, `source: "./plugins/<nom>"`, `description`). Pas de `version` dans l'entrée.
3. **Incrémenter `version` dans `plugin.json` à chaque PR qui touche le plugin** : sans cela, `claude plugin update` ne propose rien aux utilisateurs.
4. Ne pas placer de `CLAUDE.md` dans un plugin (avertissement de `validate`).

### Validation locale

Prérequis : `python3` 3.9+, `node`, CLI `claude` (la CI utilise la version figée dans `validate.yml`).

```
python3 -m unittest discover -s tests -t . -v
BASE_REF=origin/main python3 -m unittest tests.test_plugins -v   # contrôle du bump de version
```

### Ce que la CI contrôle

Les plugins sont découverts depuis `marketplace.json` : un nouveau plugin est couvert sans modifier les tests.

| Test | Élément | Contrôle |
|---|---|---|
| `test_cli_validate` | marketplace, chaque plugin | `claude plugin validate --strict` (exit 0) |
| `test_marketplace` | `marketplace.json` | champs requis, noms uniques, sources existantes, nom entrée = `plugin.json` = dossier, aucun plugin orphelin, pas de `version` dans l'entrée, pas de `CLAUDE.md` dans un plugin |
| `test_plugins` | `plugin.json` | `version` semver, `description`, `author`, `license` ; sur PR, version strictement supérieure à celle de la base si le plugin est modifié |
| `test_skills` | `skills/*/SKILL.md`, `commands/*.md` | frontmatter, `name` = dossier (kebab-case), `description` non vide ≤ 1536 caractères |
| `test_agents` | `agents/*.md` | `name` = fichier, `description` non vide, aucun champ ignoré pour un agent de plugin (`hooks`, `mcpServers`, `permissionMode`, `initialPrompt`) |
| `test_hooks` | `hooks/hooks.json` | clé `hooks`, tout script `${CLAUDE_PLUGIN_ROOT}/…` existe |
| `test_workflows` | `workflows/*.js` | bloc `meta` (`name` = fichier, `description`), syntaxe valide via `node` |
| `test_files` | fichiers du plugin | JSON valides, Python compilable, shell valide (`bash -n`), `plugins/*/bin/` : shebang + bit exécutable (index git) |
| `test_sdlc_validate_spec`, `test_sdlc_publish` | `sdlc-contract`, `sdlc-framing` | validateur de spec, publication, `sdlc-init-repo` (`--automerge`, scaffold `check.json`) contre un faux `gh` |
| `test_sdlc_guard`, `test_sdlc_run_unit` | `sdlc-factory` | garde-fou (mode fermé, périmètre de la rétro), fonctions pures de `sdlc-run`/`sdlc-retro` (`collect`, `load_check`, `read_repos`) |
| `test_sdlc_e2e` | `sdlc-factory` | `sdlc-run` de bout en bout hors ligne (faux `gh`/`claude`, dépôt git local) : gate check, merge humain/opt-in automerge, argv de `claude` |
| job `actionlint` | workflows GitHub | `.github/workflows` et YAML de plugins contenant `jobs:` |

Contraintes : le frontmatter doit rester en `clé: valeur` sur une ligne (lecteur stdlib volontairement minimal). La version du CLI Claude Code est figée dans `validate.yml` (`CLAUDE_CODE_VERSION`) et se met à jour à la main.

## Licence

[MIT](LICENSE).
