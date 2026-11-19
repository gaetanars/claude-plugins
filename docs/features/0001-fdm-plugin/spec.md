---
schema_version: 3
id: 0001-fdm-plugin
title: Socle du plugin fdm et installation (venv, profils)
track: feature
status: accepted
depends_on: []
---

# Socle du plugin fdm et installation (venv, profils)

## Contexte
Première des trois unités du plugin `fdm` (voir `brief.md`) : elle crée le plugin dans la marketplace et les deux commandes d'installation dont dépendent les unités suivantes (vérification des pièces, puis découpe et skill). Architecture : ADR-0001 (Bambu configurable, macOS et Linux), ADR-0002 (venv sous `${CLAUDE_PLUGIN_DATA}`), ADR-0003 (profils générés localement).
Valeur : sur une machine où Bambu Studio est installé, `fdm-setup` puis `fdm-profiles` préparent un environnement CAO reproductible et des profils aplatis, sans rien écrire dans le projet de l'utilisateur ni redistribuer de fichier tiers.

## Périmètre
- `plugins/fdm/.claude-plugin/plugin.json` : `name: fdm`, `version: 0.1.0`, description commençant par « Préversion », `author` identique à `plugins/sdlc/.claude-plugin/plugin.json`, `license: MIT`, `userConfig` à six options (voir Contraintes).
- Entrée `fdm` dans `.claude-plugin/marketplace.json` : `source: ./plugins/fdm`, description commençant par « Préversion », `category: design`, `keywords: ["3d-printing", "fdm", "bambu-lab", "build123d"]`, sans `version`.
- `plugins/fdm/requirements.txt` : exactement les cinq dépendances directes épinglées `build123d==0.13.0`, `trimesh==5.2.1`, `manifold3d==3.5.5`, `matplotlib==3.11.2`, `numpy==2.5.5`.
- `plugins/fdm/bin/fdm-setup` : crée ou met à jour le venv `<data>/venv`.
- `plugins/fdm/bin/fdm-profiles` : aplatit trois profils Bambu Studio dans `<data>/profiles/`.
- Tests hors ligne de ces deux commandes dans `tests/`.

## Hors périmètre
- `fdm_tools`, `fdm-run`, exemple de calibration (unité 2) ; `fdm-slice`, skill `fdm:design`, README du plugin, version 1.0.0 (unité 3).
- Détection automatique de Bambu Studio sous Linux ; Windows ; autres slicers.
- Exécution réelle de pip ou de Bambu Studio dans les tests et la CI.
- Toute modification de `~/3d-design`.

## Critères d'acceptation
- [ ] CA-1: `python3 -m unittest discover -s tests -t .` passe, y compris `test_marketplace` (entrée `fdm` déclarée, nom du dossier = nom de l'entrée = `name` du manifeste), `test_plugins` (version semver, description, auteur, licence), `test_files` (bins exécutables avec shebang) et `test_cli_validate` (`claude plugin validate --strict plugins/fdm` sans erreur).
- [ ] CA-2: `python3 docs/architecture/native/check_arch.py` sort en 0 : `fdm-setup` et `fdm-profiles` n'importent que la bibliothèque standard et ne référencent ni `plugins/sdlc` ni les tests du dépôt.
- [ ] CA-3: Le dossier de données vient de `--data <dir>`, sinon de la variable d'environnement `CLAUDE_PLUGIN_DATA` ; si aucun des deux n'est fourni, la commande sort en 1 avec un message sur stderr nommant `--data` et `CLAUDE_PLUGIN_DATA`, sans rien créer.
- [ ] CA-4: `fdm-setup --python <interp>` refuse en sortie 1, avant toute création de fichier sous `<data>`, un interpréteur dont la version est hors de la plage ≥ 3.11 et < 3.15, avec un message citant la version trouvée et la plage acceptée ; un interpréteur introuvable ou non exécutable donne aussi une sortie 1 avec message. `--python` vaut `python3` par défaut.
- [ ] CA-5: Avec un interpréteur valide et sans venv existant, `fdm-setup` crée le venv dans un dossier temporaire sous `<data>`, y installe `requirements.txt` du plugin avec le pip du venv, enregistre l'empreinte SHA-256 de `requirements.txt` dans le venv, puis renomme le dossier en `<data>/venv` ; sortie 0 et message indiquant le chemin du venv.
- [ ] CA-6: Si le venv existe et que son empreinte enregistrée est égale à celle du `requirements.txt` courant, `fdm-setup` ne lance ni création de venv ni pip, sort en 0 et l'indique ; si l'empreinte diffère ou si `--force` est passé, le venv est reconstruit selon CA-5 et remplace l'ancien seulement en cas de succès.
- [ ] CA-7: Si la création du venv ou l'installation pip échoue, `fdm-setup` sort en 1 avec un message sur stderr, supprime le dossier temporaire et laisse `<data>/venv` dans son état antérieur (absent ou intact).
- [ ] CA-8: `fdm-profiles` résout `--machine`, `--process` et `--filament` (défauts : `Bambu Lab A1 0.4 nozzle`, `0.20mm Standard @BBL A1`, `Generic PLA @BBL A1`) dans `<profiles-dir>/{machine,process,filament}/` en cherchant `<nom>.json` récursivement, suit la chaîne `inherits` sur tous ses niveaux (chaque parent cherché de la même façon dans le même type), fusionne du plus ancien ancêtre au profil demandé (l'enfant l'emporte), retire `inherits`, fixe `name` au nom demandé et `from` à `system`, et écrit `<data>/profiles/{machine,process,filament}.json` (JSON indenté) ; sortie 0 et une ligne par profil (type, nom, nombre de clés).
- [ ] CA-9: `fdm-profiles` sort en 1, sans modifier `<data>/profiles/`, quand un profil ou un parent est introuvable (message citant le nom et le dossier parcouru), quand un nom correspond à plusieurs fichiers (message listant les chemins), quand la chaîne `inherits` boucle (message citant la chaîne), ou quand un fichier n'est pas un JSON objet valide ; les trois fichiers de sortie sont écrits ensemble ou pas du tout.
- [ ] CA-10: `--profiles-dir` vaut par défaut `/Applications/BambuStudio.app/Contents/Resources/profiles/BBL` sur macOS ; sur un autre OS sans `--profiles-dir`, ou avec une valeur vide, `fdm-profiles` sort en 1 en demandant de renseigner l'option `bambu_profiles` ; un dossier inexistant donne une sortie 1 avec message.
- [ ] CA-11: Un usage incorrect (option inconnue, argument manquant) sort en 2 via `argparse`, pour les deux commandes.
- [ ] CA-12: Les tests ajoutés sont hors ligne et en bibliothèque standard : faux interpréteur (version, création de venv, idempotence, `--force`, échec pip avec état antérieur conservé) et fausse arborescence de profils (héritage multi-niveaux, recherche récursive, introuvable, ambigu, cycle, JSON invalide, atomicité).

## Contraintes
- Architecture : modules `fdm` et `marketplace` uniquement ; règles R1 et R4 de `check_arch.py` ; aucune dépendance tierce hors `requirements.txt` (consommé par pip dans le venv, jamais importé par les commandes).
- `userConfig` de `plugin.json` : six options `type: string`, `sensitive: false`, chacune avec `title` et `description` : `machine` (défaut `Bambu Lab A1 0.4 nozzle`), `process` (défaut `0.20mm Standard @BBL A1`), `filament` (défaut `Generic PLA @BBL A1`), `bambu_studio` (exécutable Bambu Studio, défaut vide = chemin macOS standard, obligatoire sous Linux), `bambu_profiles` (dossier `profiles/BBL`, défaut vide = chemin macOS standard, obligatoire sous Linux), `python` (défaut `python3`). Les commandes ne lisent pas ces options elles-mêmes : le skill (unité 3) les passe en arguments, car `${user_config.KEY}` n'est substitué que dans le contenu des skills et les hooks.
- Arguments : `fdm-setup [--data DIR] [--python INTERP] [--force]` ; `fdm-profiles [--data DIR] [--profiles-dir DIR] [--machine NOM] [--process NOM] [--filament NOM]`. Une valeur vide passée par le skill pour `--profiles-dir` équivaut à l'absence d'option.
- `requirements.txt` est lu depuis le dossier du plugin, résolu à partir de l'emplacement de la commande (pas depuis `CLAUDE_PLUGIN_ROOT`).
- Codes de sortie : 0 succès, 1 erreur d'exécution (message actionnable sur stderr), 2 usage incorrect. Seul pip accède au réseau.
- Rien n'est écrit hors de `<data>` ; aucun fichier n'est écrit dans le projet de l'utilisateur.
- Compatibilité : macOS et Linux ; Python 3 de la bibliothèque standard pour les commandes elles-mêmes (shebang `#!/usr/bin/env python3`).
- Diff visé ≲ 400 lignes.

## Décisions de cadrage
- [x] Q1: Comment les commandes `bin/` reçoivent-elles le dossier de données et les options ? → R: Arguments explicites passés par le skill (`--data "${CLAUDE_PLUGIN_DATA}"`, options en arguments) ; repli sur la variable d'environnement `CLAUDE_PLUGIN_DATA`, sinon erreur. Constaté sur Claude Code 2.1.328 : `${user_config.KEY}` n'est substitué que dans les skills, agents et hooks. (2026-11-19)
- [x] Q2: Quelles options `userConfig` ? → R: `machine`, `process`, `filament`, `bambu_studio`, `bambu_profiles`, `python`, toutes `string` non sensibles ; chemins Bambu vides = défauts macOS, obligatoires sous Linux (pas de détection automatique). Schéma `type`/`title`/`description`/`default`/`sensitive` vérifié avec `claude plugin validate`. (2026-11-19)
- [x] Q3: Épinglage et comportement de `fdm-setup` ? → R: Cinq dépendances directes épinglées exactement (pas de gel complet, qui casserait Linux ARM via `lib3mf`/`py-lib3mf`) ; Python ≥ 3.11 et < 3.15 d'après le `Requires-Python` de build123d 0.13.0 et cadquery-ocp 8.0.1 ; idempotent par empreinte de `requirements.txt`, `--force` pour reconstruire. (2026-11-19)
- [x] Q4: Comment `fdm-profiles` trouve-t-il un profil ? → R: Recherche récursive de `<nom>.json` sous le dossier du type (150 profils filament sont dans des sous-dossiers dans Bambu Studio installé) ; introuvable, ambigu ou cycle = erreur. (2026-11-19)
- [x] Q5: Comportement en cas d'échec ? → R: Atomique : venv construit dans un dossier temporaire sous `<data>` puis renommé ; les trois profils écrits ensemble ou pas du tout ; sorties 0/1/2. (2026-11-19)
- [x] Q6: Version, métadonnées et tests ? → R: `0.1.0` « Préversion » jusqu'à l'unité 3 (1.0.0) ; catégorie `design` ; pas de README propre au plugin dans cette unité (le README racine satisfait `claude plugin validate --strict`) ; tests hors ligne avec faux interpréteur et fausse arborescence de profils ; installation réelle vérifiée à la main pendant la revue. (2026-11-19)
- [x] Q7: Découpage de la feature ? → R: 1) socle et installation (cette spec) ; 2) `fdm_tools.check` + `fdm-run` + exemple ; 3) `fdm-slice` + skill + README + 1.0.0. Chaque merge publie une préversion 0.x (le test d'orphelin impose l'entrée marketplace dès l'unité 1). (2026-11-19)
