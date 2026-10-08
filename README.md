# Marketplace Claude Code de gaetanars

Marketplace de plugins [Claude Code](https://code.claude.com), validée en CI à chaque PR.

## Plugins

| Plugin | Version | Description |
|---|---|---|
| [`tdd-forge`](plugins/tdd-forge/README.md) | 0.1.1 | Livraison autonome en TDD (Python, TypeScript, GitHub) : PO, plan, tests rouges, vert, refactor, revue, PR et merge si CI verte. Expérimental. |

## Installation

Dans Claude Code :

```
/plugin marketplace add gaetanars/claude-plugins
/plugin install tdd-forge@gaetanars
```

Équivalent en ligne de commande : `claude plugin marketplace add gaetanars/claude-plugins` puis `claude plugin install tdd-forge@gaetanars`.

> **Migration** : la marketplace s'appelait `tdd-forge` (dépôt `gaetanars/tdd-forge`). Retire l'ancienne (`claude plugin marketplace remove tdd-forge`) puis réinstalle avec les commandes ci-dessus.

## Mise à jour

L'auto-update est désactivé par défaut pour une marketplace tierce :

```
claude plugin marketplace update gaetanars
claude plugin update tdd-forge@gaetanars
```

## Structure

```
.claude-plugin/marketplace.json   catalogue (nom, propriétaire, plugins)
plugins/<plugin>/                 un dossier par plugin
  .claude-plugin/plugin.json      manifeste, seule source de la version
  skills/ agents/ commands/ hooks/ workflows/ …
tests/                            validation des éléments (unittest, stdlib)
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
| `test_files` | fichiers du plugin | JSON valides, Python compilable, shell valide (`bash -n`) |
| job `actionlint` | workflows GitHub | `.github/workflows` et YAML de plugins contenant `jobs:` |

Contraintes : le frontmatter doit rester en `clé: valeur` sur une ligne (lecteur stdlib volontairement minimal). La version du CLI Claude Code est figée dans `validate.yml` (`CLAUDE_CODE_VERSION`) et se met à jour à la main.

## Licence

[MIT](LICENSE).
