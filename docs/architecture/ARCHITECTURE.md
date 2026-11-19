---
schema_version: 2
status: accepted
updated: 2026-11-19
---

# Architecture : marketplace Claude Code gaetanars

## Contexte et objectifs
Marketplace Claude Code publique qui diffuse des plugins indépendants : `sdlc` (SDLC AI-First interactif) et `fdm` (conception de pièces imprimables en FDM pour imprimantes Bambu Lab, modélisées en build123d).
Qualités visées, par priorité :
1. Fiabilité vérifiable : chaque plugin est validé hors ligne en CI ; toute affirmation de `fdm` sur une pièce vient d'un contrôle, d'un rendu ou d'une découpe.
2. Portabilité : `fdm` fonctionne sur macOS et Linux, pour toute imprimante Bambu configurable (ADR-0001).
3. Simplicité : bibliothèque standard partout sauf dans `fdm-tools`, aucune abstraction spéculative.
4. Conformité de licence : la marketplace (MIT) ne redistribue aucun fichier tiers (ADR-0003).

## Stack
- Plugins Claude Code (skills, agents, `bin/`), distribués par `.claude-plugin/marketplace.json`, versionnés en semver par plugin.
- Python 3, bibliothèque standard uniquement pour `sdlc`, les commandes `plugins/fdm/bin/`, `tests` et le contrôle d'architecture.
- `fdm-tools` : build123d, trimesh, manifold3d, matplotlib, numpy, aux versions épinglées dans un venv installé par `fdm-setup` sous `${CLAUDE_PLUGIN_DATA}` (ADR-0002).
- Bambu Studio installé chez l'utilisateur : découpe en CLI et source des profils, aplatis localement (ADR-0003).
- Validation : unittest hors ligne, `claude plugin validate --strict`, actionlint en CI.

## Modules
- `marketplace` (`.claude-plugin/`) : catalogue des plugins, sans version.
- `sdlc` (`plugins/sdlc/`) : plugin SDLC interactif (skills, agents, `bin/sdlc-*`, gabarits, schémas).
- `fdm` (`plugins/fdm/`, hors `plugins/fdm/lib/`) : plugin de conception FDM ; skill `fdm:design`, commandes `bin/fdm-setup`, `bin/fdm-profiles`, `bin/fdm-run`, `bin/fdm-slice` (ADR-0004).
- `fdm-tools` (`plugins/fdm/lib/fdm_tools/`) : bibliothèque CAO importée par les pièces de l'utilisateur (`check`, rendu, règles d'imprimante) ; seul module autorisé à importer des dépendances tierces.
- `tests` (`tests/`) : validation hors ligne du dépôt, un module par type d'élément.
- `ci` (`.github/`) : workflow qui lance `tests` et actionlint, Dependabot.

## Règles de dépendance
- `marketplace` → `sdlc`, `fdm` (par chemin source uniquement).
- `sdlc` → aucun module.
- `fdm` → `fdm-tools`, uniquement en sous-processus via le Python du venv : les commandes `bin/` n'importent jamais `fdm_tools`.
- `fdm-tools` → aucun module ; imports limités à la bibliothèque standard, `fdm_tools` et la liste blanche (`build123d`, `trimesh`, `manifold3d`, `matplotlib`, `mpl_toolkits`, `numpy`).
- `tests` → `marketplace`, `sdlc`, `fdm`, `fdm-tools` en lecture de fichiers seulement, jamais par import de `fdm_tools`.
- `ci` → `tests`.
Toute autre dépendance est interdite : aucun module ne dépend de `tests` ni de `ci`, aucun plugin ne référence un autre plugin (ADR-0005).

## Principes et interdits
- Chaque plugin est autonome : il ne lit que `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}` et le projet de l'utilisateur ; jamais de chemin vers un autre plugin ni vers `tests/` du dépôt.
- Les pièces et leurs sorties (`parts/`, `out/`) vivent dans le projet de l'utilisateur ; le plugin ne copie jamais ses outils dans ce projet (ADR-0004).
- Les tests du dépôt n'installent ni n'importent build123d : la chaîne CAO se vérifie en local (pièce de calibration), pas en CI (ADR-0002).
- Erreurs : chaque commande `fdm-*` sort en code non nul avec un message actionnable (venv absent → `fdm-setup`, Bambu Studio introuvable, profils manquants → `fdm-profiles`) ; un `check` en `ISSUES` sort aussi en code non nul.
- Sécurité : `fdm-run` exécute le code des pièces de l'utilisateur dans son projet, sans privilège ; seul `fdm-setup` accède au réseau (pip, versions épinglées). Aucun secret manipulé.
- Interdit : redistribuer des profils ou fichiers de Bambu Studio (AGPL) ; installer des dépendances dans le Python global ou le projet de l'utilisateur ; `CLAUDE.md` dans un dossier de plugin ; version dans l'entrée marketplace.
- Toute modification d'un plugin impose un bump semver de son `plugin.json`.

## Exige un ADR
Décisions structurantes : l'automate ne les tranche jamais seul, il les remonte.

- Création d'un module ou d'un plugin, ou changement de frontière entre modules.
- Nouvelle dépendance tierce dans `fdm-tools` (extension de la liste blanche) ou changement de version majeure d'une dépendance épinglée.
- Support d'un autre slicer que Bambu Studio ou d'un autre OS (Windows).
- Changement d'emplacement du venv, des profils ou des sorties des pièces.
- Redistribution de tout fichier tiers dans la marketplace.
- Dérogation à la règle bibliothèque standard uniquement hors `fdm-tools`.
- Exécution de `fdm-tools` en CI (installation d'OCP).

## Contrôle mécanique
Outil natif : script Python en bibliothèque standard (aucun outil existant ne couvre des dépendances par chemins et par politique d'imports ; ADR-0005). Configuration : `docs/architecture/native/check_arch.py` (seul emplacement admis : il est protégé contre les agents).
Règles appliquées : R1 bibliothèque standard uniquement (`plugins/sdlc`, `plugins/fdm/bin`, `tests`, `docs/architecture/native`) ; R2 liste blanche d'imports de `fdm-tools` ; R3 `fdm_tools` importé uniquement dans `plugins/fdm/lib/` ; R4 isolation des plugins (aucune référence à un autre plugin ni aux tests du dépôt).
Commande : champ `arch` de `.claude/check.json`.
Dépôt existant : aucune violation au cadrage (2026-11-19), donc aucune baseline ; aucune nouvelle violation n'est admise.
