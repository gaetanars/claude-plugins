# Marketplace Claude Code de gaetanars

Marketplace de plugins [Claude Code](https://code.claude.com), validée en CI à chaque PR.

## Plugins

| Plugin | Où l'installer | Version | Description |
|---|---|---|---|
| `sdlc-contract` | poste et serveur | 0.3.0 | Contrat partagé : gabarits brief/spec/plan/ADR/architecture/apprentissages, schéma de verdict, conventions, contrat `.claude/check.json`, `sdlc-validate-spec`, `sdlc-validate-architecture`, `sdlc-init-repo`. |
| `sdlc-framing` | poste (ou session Orca) | 0.3.0 | Skills `challenger` (idéation), `architect` (architecture), `po` (cadrage), `retro` (amélioration des outils), `sdlc-publish` (spec → issue GitHub). Dépend de `sdlc-contract`. |
| [`sdlc-factory`](plugins/sdlc-factory/README.md) | serveur Orca | 0.3.0 | Skill `deliver`, agents `planner`/`implementer`/`reviewer`, `sdlc-gate` (TDD vérifié, gates, livraison en PR). Dépend de `sdlc-contract`. |

Les plugins sont universels (aucun code propre à un langage ou à un projet) ; tout ce qui concerne un projet vit dans son dépôt.
Les artefacts sont rédigés en français : les validateurs contrôlent les titres de sections.

## Parcours SDLC

Tu interviens en idéation, architecture et cadrage, en local ou dans une session Orca ; l'usine fait ensuite plan → TDD → revue → PR
sans toi, sauf question ou escalade. **Le merge est toujours humain.**

```
CADRAGE (toi + skills)                               USINE (serveur Orca, automatisation horaire par dépôt)
/sdlc-framing:architect → docs/architecture/ + ADR   precheck `sdlc-gate next` : une issue ready, aucune in-progress
   une fois par projet ; `adr <sujet>` / `revise`    /sdlc-factory:deliver dans un worktree neuf
/sdlc-framing:challenger → brief.md (facultatif)       sdlc-gate start   → in-progress, feat/<id>, cadrage validé
/sdlc-framing:po → spec.md (Q/R dans la spec)          planner           → plan.md ; question → posée dans la session
   refuse sans architecture acceptée                   implementer       → commit test (rouge constaté) → commit feat
sdlc-publish publish <id> → push main + issue ready    sdlc-gate verify  → check + arch, chemins protégés, TDD
                                                       reviewer          → verdict JSON (3 axes) ; 3 refus → needs-human
                                                       docs/learnings.md → apprentissages du run
                                                       sdlc-gate deliver → push, PR « Closes #n », in-review → TU FUSIONNES
/sdlc-framing:retro <projets> (manuel) → améliorations des plugins à partir des docs/learnings.md des projets
```

Livrables versionnés dans chaque projet, relus à chaque étape suivante :

| Livrable | Écrit par | Lu par |
|---|---|---|
| `docs/architecture/ARCHITECTURE.md`, `native/`, `docs/adr/` | `architect` (toi) | `challenger`, `po`, planner, implementer, reviewer, `sdlc-gate` |
| `docs/features/<id>/brief.md` (facultatif), `spec.md` | `challenger`, `po` | planner, implementer, reviewer, `sdlc-gate` |
| `docs/features/<id>/plan.md` | usine | implementer, reviewer, toi (PR) |
| `docs/learnings.md` | usine, `po` | tous les skills et agents ; `retro` |

Installation poste : `/plugin install sdlc-framing@gaetanars` (`sdlc-contract` suit en dépendance), puis dans un projet `sdlc-init-repo scaffold`
(renseigner `CLAUDE.md` et `.claude/check.json`), puis `/sdlc-framing:architect init`. Serveur : [`plugins/sdlc-factory/README.md`](plugins/sdlc-factory/README.md).

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
tests/                            validation des éléments et tests SDLC (unittest, stdlib) ; sdlc_fakebin/ = faux gh
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
| `test_sdlc_validate_spec`, `test_sdlc_publish` | `sdlc-contract`, `sdlc-framing` | validateur de spec v2 (brief facultatif, décisions de cadrage), publication, `sdlc-init-repo` (labels, protection, scaffold) contre un faux `gh` |
| `test_sdlc_validate_architecture` | `sdlc-contract` | format d'architecture v2 : sections, « Exige un ADR », configuration native citée sous `docs/architecture/native/`, ADR, `--require-accepted` |
| `test_sdlc_gate` | `sdlc-factory` | `sdlc-gate` de bout en bout hors ligne (faux `gh`, dépôts git locaux, worktree simulant Orca) : `next`, `start` et escalades, TDD, `verify`, `review`, `deliver`, `escalate` |
| job `actionlint` | workflows GitHub | `.github/workflows` et YAML de plugins contenant `jobs:` |

Contraintes : le frontmatter doit rester en `clé: valeur` sur une ligne (lecteur stdlib volontairement minimal). La version du CLI Claude Code est figée dans `validate.yml` (`CLAUDE_CODE_VERSION`) et se met à jour à la main.

## Licence

[MIT](LICENSE).
