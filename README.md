# Marketplace Claude Code de gaetanars

Marketplace de plugins [Claude Code](https://code.claude.com), validée en CI à chaque PR.

## Plugin

| Plugin | Version | Description |
|---|---|---|
| `sdlc` | 0.1.0 | SDLC AI-First interactif : `/sdlc:go` (triage), skills `challenge`, `spec`, `architect`, `plan`, `build`, `review`, `ship`, `retro`, `conventions` ; agents `planner`/`implementer`/`reviewer` ; `sdlc-gate` (TDD vérifié, verdict, livraison), validateurs, `sdlc-init-repo`. |

Plugin universel (aucun code propre à un langage ou à un projet) ; tout ce qui concerne un projet vit dans son dépôt (`docs/`, `.claude/check.json`).
Les artefacts sont rédigés en français : les validateurs contrôlent les titres de sections.

## Parcours SDLC

`/sdlc:go <besoin>` trie le besoin, puis chaque brique s'arrête à une **gate humaine** (accord explicite, matérialisé par un statut d'artefact ou un commit). Merge toujours humain.

| Parcours | Chaîne |
|---|---|
| trivial | `sdlc-gate start --trivial <slug>` → modification → `review` → `ship` |
| standard (dont bug) | `spec` → `sdlc-gate start <id>` → `plan` → `build` → `review` → `ship` |
| feature | `challenge` → (`architect adr`) → `spec` → `start` → `plan` → `build` → `review` → `ship` ; architecture acceptée exigée |

| Brique | Rôle | Gate humaine |
|---|---|---|
| `go` | triage, enchaînement | parcours confirmé |
| `challenge` | brief (feature) | brief relu |
| `spec` | `spec.md` v3 | `status: accepted` |
| `architect` | `docs/architecture/`, ADR | acceptation explicite |
| `plan` (agent `planner`) | `plan.md` | plan validé puis commité |
| `build` (agent `implementer`) | commits `test` rouge → `feat`, contrôlés par `sdlc-gate` | — |
| `review` (`sdlc-gate verify` + agent `reviewer`) | verdict JSON (notes git) | ta revue finale |
| `ship` | `docs/learnings.md`, push SSH + PR | « J'ouvre la PR ? » |
| `retro` | améliorations du plugin depuis les `learnings.md` | tu tranches chaque ligne |

Seuls `go` et `retro` sont réservés à l'invocation explicite ; les autres briques sont chargées par `go` au moment où le parcours y arrive (leur `description` le dit), ou lancées à la main.
`sdlc-gate start <id>` exige une spec `accepted`, les `depends_on` mergés sur la branche par défaut, puis fige spec et brief (commit `docs(<id>): spec`) ; `sdlc-next-id` réserve aussi les numéros des branches `feat/*` ouvertes.
Pas d'issue GitHub ni de label. Livrables versionnés dans chaque projet : `docs/architecture/`, `docs/adr/`, `docs/features/<id>/{brief,spec,plan}.md`, `docs/learnings.md`.
Mise en route d'un projet : `sdlc-init-repo scaffold` (renseigner `CLAUDE.md` et `.claude/check.json`), puis `/sdlc:architect init` si tu veux le parcours feature.
Pour un fork, `gh repo set-default` une fois avant `ship`.

## Installation

Dans Claude Code :

```
/plugin marketplace add gaetanars/claude-plugins
/plugin install sdlc@gaetanars
```

Équivalent en ligne de commande : `claude plugin marketplace add gaetanars/claude-plugins` puis `claude plugin install sdlc@gaetanars`.

> **Retrait de `sdlc-contract`, `sdlc-framing`, `sdlc-factory`** : remplacés par `sdlc` (historique git conservé). `claude plugin uninstall <nom>@gaetanars` pour chacun avant d'installer `sdlc`. Les specs v2 existantes ne sont plus acceptées (schema_version 3, `track`, `status: accepted`) ; l'usine Orca est retirée.

> **Retrait de `cadre` et `tdd-forge`** : déjà remplacés ; `claude plugin uninstall cadre@gaetanars` / `tdd-forge@gaetanars` s'ils sont encore installés. La marketplace s'appelait `tdd-forge` : `claude plugin marketplace remove tdd-forge` puis réinstalle avec les commandes ci-dessus.

## Mise à jour

L'auto-update est désactivé par défaut pour une marketplace tierce :

```
claude plugin marketplace update gaetanars
claude plugin update sdlc@gaetanars
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
| `test_sdlc_validate_spec` | `sdlc` | validateur de spec v3 (standard/feature, `status`, brief facultatif, décisions de cadrage) |
| `test_sdlc_init_repo` | `sdlc` | `sdlc-init-repo` (dry-run `github` sans labels, `scaffold`) et `sdlc-next-id` |
| `test_sdlc_validate_architecture` | `sdlc` | format d'architecture v2 : sections, « Exige un ADR », configuration native citée sous `docs/architecture/native/`, ADR, `--require-accepted` |
| `test_sdlc_gate` | `sdlc` | `sdlc-gate` de bout en bout hors ligne (faux `gh` limité à `pr list/create`, dépôts git locaux) : `start` (spec draft, architecture, `--trivial`), TDD, `verify`, `review`, `deliver` |
| job `actionlint` | workflows GitHub | `.github/workflows` et YAML de plugins contenant `jobs:` |

Contraintes : le frontmatter doit rester en `clé: valeur` sur une ligne (lecteur stdlib volontairement minimal). La version du CLI Claude Code est figée dans `validate.yml` (`CLAUDE_CODE_VERSION`) et se met à jour à la main.

## Licence

[MIT](LICENSE).
