# Plan : Socle du plugin fdm et installation (venv, profils)

Feature : 0001-fdm-plugin · Spec : docs/features/0001-fdm-plugin/spec.md

## Approche
Trois étapes TDD : métadonnées du plugin, puis `fdm-profiles`, puis `fdm-setup`. Les deux commandes sont des scripts Python en bibliothèque standard (`#!/usr/bin/env python3`, `argparse`, `json`, `hashlib`, `subprocess`, `shutil`, `tempfile`, `pathlib`), sans import tiers ni import de `fdm_tools`.

- Portage de `~/3d-design/tools/flatten_profiles.py` : on garde la fonction récursive `resolve`, le `update` `name`/`from` et la ligne de sortie `"{kind}: {name} ({n} keys)"`. On ajoute :
  - la recherche récursive par nom exact de fichier, sans motif glob (les noms Bambu peuvent contenir des caractères spéciaux) : `[p for p in dir.rglob("*.json") if p.name == f"{name}.json"]` ;
  - la détection d'un nom ambigu et d'un cycle, avec la chaîne parcourue dans le message ;
  - le contrôle « JSON objet » ;
  - le dossier `--profiles-dir`.
  Les trois profils sont résolus en mémoire avant toute écriture. Ensuite seulement, `<data>/profiles/` est créé et chaque `<kind>.json` est écrit dans un `.tmp` voisin puis remplacé par `os.replace`. Une erreur de résolution n'écrit donc rien.
- `fdm-setup` :
  - Il interroge d'abord la version avec `[interp, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"]`, avant toute création sous `<data>`. Il renvoie 1 sur `FileNotFoundError`, `PermissionError`, une sortie illisible ou une version hors de la plage `>=3.11,<3.15`.
  - Il calcule le SHA-256 de `Path(__file__).resolve().parent.parent / "requirements.txt"` et le compare à `<data>/venv/requirements.sha256`. S'ils sont égaux et que `--force` est absent, il sort en 0 avec le message « à jour ».
  - Sinon il construit le venv : `tempfile.mkdtemp(dir=data, prefix="venv.tmp-")`, puis `interp -m venv <tmp>`, puis `<tmp>/bin/python -m pip install -r <requirements>`, puis écriture de `<tmp>/requirements.sha256`.
  - Il bascule ensuite : l'ancien venv est renommé en `venv.old-*`, le temporaire est renommé en `venv`, puis `rmtree` supprime l'ancien. Si le deuxième renommage échoue, l'ancien est restauré.
  - En cas d'échec, `rmtree(tmp)` est lancé et la sortie vaut 1.
- Dossier de données : `args.data or os.environ.get("CLAUDE_PLUGIN_DATA")`, sinon sortie 1 avec un message qui nomme les deux. Ces 3 lignes sont dupliquées dans chaque commande : pas de module partagé (KISS ; R1 n'admet pas d'import local sous `plugins/fdm/bin`).
- Tests hors ligne, sur le modèle de `tests/test_sdlc_init_repo.py` (`subprocess.run([sys.executable, str(script), ...])`) :
  - Faux interpréteur, généré par le test dans un dossier temporaire avec le shebang `#!{sys.executable}`. Il lit `FAKE_PY_VERSION`, `FAKE_VENV_FAIL`, `FAKE_PIP_FAIL` et `FAKE_LOG`. Pour `-m venv DIR`, il crée `DIR/bin/python` comme copie exécutable de lui-même. Pour `-m pip install -r F`, il journalise l'appel puis réussit ou échoue.
  - Fausse arborescence de profils synthétiques, construite par les tests : aucun fichier Bambu.
  - Le test de l'OS passe par `runpy.run_path(script, run_name="__main__")` dans `python -c` après avoir forcé `sys.platform`. La commande lit donc `sys.platform` à l'exécution.
- Choix locaux :
  - messages en français ;
  - les tests s'appuient sur des jetons stables (chemins, versions, noms d'options, noms de profils), pas sur la formulation ;
  - empreinte stockée dans `venv/requirements.sha256` ;
  - JSON écrit avec `indent=2` et un saut de ligne final.
- Apprentissages appliqués :
  - ADR-0002 : tests et CI restent en bibliothèque standard et hors ligne ; ni pip ni build123d ne sont exécutés.
  - ADR-0003 : les fixtures de profils sont synthétiques ; rien n'est écrit hors de `<data>`.

## Étapes
Chaque étape suit le cycle TDD en deux commits : `test(fdm): ...` (tests seuls, rouges), puis `feat(fdm): ...` (code, sans toucher aux fichiers du commit de tests).

### Étape 1 : Déclaration du plugin fdm (manifeste, marketplace, requirements)
- Tests à écrire d'abord : `tests/test_fdm_plugin.py`, qui lit les fichiers sans rien importer du plugin.
  - `test_marketplace_entry` : entrée `fdm`, `source: ./plugins/fdm`, description commençant par « Préversion », `category: design`, `keywords == ["3d-printing", "fdm", "bambu-lab", "build123d"]`, pas de `version`.
  - `test_manifest_metadata` : `name: fdm`, `version: 0.1.0`, description « Préversion… », `author` égal à celui de `plugins/sdlc/.claude-plugin/plugin.json`, `license: MIT`.
  - `test_user_config` : exactement les clés `machine`, `process`, `filament`, `bambu_studio`, `bambu_profiles`, `python`. Chacune a `type == "string"`, `sensitive is False`, un `title` et une `description` non vides, et les défauts suivants :

    | Clé | Défaut attendu |
    |---|---|
    | `machine` | `Bambu Lab A1 0.4 nozzle` |
    | `process` | `0.20mm Standard @BBL A1` |
    | `filament` | `Generic PLA @BBL A1` |
    | `bambu_studio` | `""` |
    | `bambu_profiles` | `""` |
    | `python` | `python3` |

  - `test_requirements_pinned` : les lignes non vides de `plugins/fdm/requirements.txt` sont exactement les cinq épinglages de la spec.
- Changement :
  - `plugins/fdm/.claude-plugin/plugin.json`, avec `homepage` et `repository` sur le modèle de `sdlc` ;
  - entrée `fdm` après `sdlc` dans `.claude-plugin/marketplace.json` ;
  - `plugins/fdm/requirements.txt`.
- Couvre : CA-1

### Étape 2 : Commande `fdm-profiles`
- Tests à écrire d'abord : `tests/test_fdm_profiles.py`. Les fixtures sont créées dans un dossier temporaire avec `machine/`, `process/` et `filament/`. `CLAUDE_PLUGIN_DATA` est retiré de l'environnement des sous-processus.
  - Cas nominal :
    - `test_flattens_multi_level_inheritance` : 3 niveaux, l'enfant l'emporte, `inherits` est absent, `name` et `from == "system"` sont fixés, sortie 0, une ligne par type avec le nombre de clés, JSON indenté.
    - `test_recursive_search_in_subfolders` : le profil et son parent sont dans des sous-dossiers différents de `filament/`.
    - `test_custom_names` : `--machine`, `--process` et `--filament` sont pris en compte.
  - Dossier de données :
    - `test_data_from_env` : `CLAUDE_PLUGIN_DATA` est utilisé sans `--data`.
    - `test_no_data_dir` : sortie 1, stderr contient `--data` et `CLAUDE_PLUGIN_DATA`, rien n'est créé.
  - Erreurs de résolution :
    - `test_profile_not_found` et `test_parent_not_found` : sortie 1, le nom et le dossier sont cités.
    - `test_ambiguous_name` : sortie 1, les deux chemins sont listés.
    - `test_inherits_cycle` : sortie 1, la chaîne est citée.
    - `test_invalid_json` et `test_json_not_object` : sortie 1.
    - `test_atomic_on_error` : un `<data>/profiles/machine.json` préexistant est inchangé et aucun autre fichier n'est créé quand le filament est introuvable.
  - Dossier des profils :
    - `test_non_macos_requires_profiles_dir` : `sys.platform` est forcé à `linux`, sans option puis avec `--profiles-dir ""`. Sortie 1 et stderr contient `bambu_profiles`.
    - `test_macos_default_dir` : `sys.platform` est forcé à `darwin`. Le test est ignoré si Bambu Studio est installé ; sinon sortie 1 avec le chemin par défaut cité.
    - `test_missing_profiles_dir` : un dossier inexistant donne une sortie 1.
  - `test_usage_errors` : `--bogus` et `--data` sans valeur sortent en 2.
- Changement : `plugins/fdm/bin/fdm-profiles` (mode 100755), avec les fonctions `find_profile(kind_dir, name)`, `resolve(kind_dir, name, chain)` et `main()`. Les erreurs passent par une exception locale convertie en message stderr et sortie 1 dans `main`.
- Couvre : CA-1, CA-2, CA-3, CA-8, CA-9, CA-10, CA-11, CA-12

### Étape 3 : Commande `fdm-setup`
- Tests à écrire d'abord : `tests/test_fdm_setup.py`, avec le faux interpréteur décrit dans « Approche » et `CLAUDE_PLUGIN_DATA` retiré de l'environnement.
  - Dossier de données :
    - `test_no_data_dir` : sortie 1, les deux noms sont cités, rien n'est créé.
    - `test_data_from_env` : `CLAUDE_PLUGIN_DATA` est utilisé sans `--data`.
  - Interpréteur :
    - `test_rejects_python_out_of_range` : avec 3.10 et 3.15, sortie 1, stderr cite la version trouvée et la plage, et `<data>` n'existe pas.
    - `test_accepts_bounds` : 3.11 et 3.14 sont acceptés.
    - `test_python_not_found` et `test_python_not_executable` : sortie 1.
    - `test_default_python_from_path` : le faux interpréteur est nommé `python3` et placé en tête de `PATH`, sans `--python`.
  - Construction : `test_creates_venv`.
    - sortie 0, stdout contient `<data>/venv` ;
    - le journal contient `venv <tmp>`, avec `<tmp>` sous `<data>` et différent de `venv`, puis `pip install -r <plugin>/requirements.txt` ;
    - `venv/requirements.sha256` vaut le SHA-256 du fichier du plugin ;
    - aucun `venv.tmp-*` ne reste.
  - Idempotence et reconstruction :
    - `test_idempotent` : un second lancement donne un journal vide et une sortie 0.
    - `test_rebuild_on_hash_change` : l'empreinte enregistrée est altérée, le venv est reconstruit.
    - `test_force_rebuilds` : `--force` reconstruit.
  - Échecs :
    - `test_pip_failure_without_venv` : sortie 1, pas de `venv` ni de `venv.tmp-*`.
    - `test_pip_failure_keeps_previous_venv` : avec `--force` et un fichier témoin dans l'ancien venv, l'ancien venv est intact.
    - `test_venv_creation_failure` : sortie 1, nettoyage effectué.
  - `test_usage_errors` : `--bogus` et `--python` sans valeur sortent en 2.
- Changement : `plugins/fdm/bin/fdm-setup` (mode 100755), avec les fonctions `python_version(interp)`, `requirements_hash()`, `build_venv(interp, data, digest)` et `main()`.
- Couvre : CA-1, CA-2, CA-3, CA-4, CA-5, CA-6, CA-7, CA-11, CA-12

## Couverture des critères d'acceptation
| CA | Étape(s) | Test(s) |
|----|----------|---------|
| CA-1 | 1, 2, 3 | test_fdm_plugin (4 tests), test_marketplace, test_plugins.test_version_semver, test_files.test_bin_executables, test_cli_validate.test_plugins |
| CA-2 | 2, 3 | commande `arch` (`check_arch.py`, R1 et R4), lancée par `sdlc-gate verify` |
| CA-3 | 2, 3 | test_fdm_profiles.test_no_data_dir, test_fdm_profiles.test_data_from_env, test_fdm_setup.test_no_data_dir, test_fdm_setup.test_data_from_env |
| CA-4 | 3 | test_rejects_python_out_of_range, test_accepts_bounds, test_python_not_found, test_python_not_executable, test_default_python_from_path |
| CA-5 | 3 | test_creates_venv |
| CA-6 | 3 | test_idempotent, test_rebuild_on_hash_change, test_force_rebuilds |
| CA-7 | 3 | test_pip_failure_without_venv, test_pip_failure_keeps_previous_venv, test_venv_creation_failure |
| CA-8 | 2 | test_flattens_multi_level_inheritance, test_recursive_search_in_subfolders, test_custom_names |
| CA-9 | 2 | test_profile_not_found, test_parent_not_found, test_ambiguous_name, test_inherits_cycle, test_invalid_json, test_json_not_object, test_atomic_on_error |
| CA-10 | 2 | test_non_macos_requires_profiles_dir, test_macos_default_dir, test_missing_profiles_dir |
| CA-11 | 2, 3 | test_fdm_profiles.test_usage_errors, test_fdm_setup.test_usage_errors |
| CA-12 | 2, 3 | tests_fdm_profiles et tests_fdm_setup (faux interpréteur, fausse arborescence, aucun réseau) |

## Conformité à l'architecture
- Modules touchés : `marketplace` (entrée `fdm`, par chemin source), `fdm` (`plugins/fdm/` hors `lib/`) et `tests`. `fdm-tools`, `sdlc` et `ci` ne sont pas touchés.
- Règles de dépendance :
  - `fdm` ne dépend d'aucun module dans cette unité.
  - `tests` lit les fichiers et lance des sous-processus, ce qui est autorisé.
  - R1 : les bins `fdm-*` n'importent que la bibliothèque standard.
  - R4 : aucune référence à `plugins/sdlc` ni aux tests du dépôt dans `plugins/fdm/`.
- ADR appliquées :
  - ADR-0001 : macOS par défaut, Linux par option.
  - ADR-0002 : venv sous `<data>/venv`, versions épinglées, tests hors ligne.
  - ADR-0003 : profils aplatis localement, aucun fichier Bambu dans le dépôt.
  - ADR-0005 : `check_arch.py` est utilisé tel quel.
- Principes : rien n'est écrit hors de `<data>` ; aucune version dans l'entrée marketplace ; pas de `CLAUDE.md` dans `plugins/fdm` ; le nouveau plugin démarre en `0.1.0`, donc le contrôle de bump est sans objet.
- Aucune décision de la liste « Exige un ADR » : la création du plugin `fdm` et sa frontière sont couvertes par l'architecture acceptée.

## Risques et points de vigilance
- **Venv renommé après création.** Les scripts console du venv (`bin/pip`, `bin/activate`) gardent le chemin du dossier temporaire. Seuls `bin/python` et `python -m ...` restent fiables : les unités 2 et 3 devront toujours appeler `<data>/venv/bin/python -m ...`. À vérifier lors de l'installation réelle pendant la revue.
- **`CLAUDE_PLUGIN_DATA` hérité de l'environnement.** Les tests doivent le retirer de l'`env` des sous-processus.
- **Test du défaut macOS.** Il est ignoré si Bambu Studio est installé, pour ne pas lire de vrais profils. Il ne s'exécute réellement que sur la CI Linux.
- **Faux interpréteur.** La forme réelle de la requête de version n'est vérifiée que par l'installation manuelle en revue.
- **Taille du diff.** Environ 450 lignes, au-dessus de la cible de 400 : il faut garder des tests compacts, avec des helpers `run()`, `make_tree()` et `fake_python()`.
- **Bit exécutable.** Il est obligatoire dans l'index git : `git add --chmod=+x` si nécessaire.

## Hors plan
- `fdm_tools`, `fdm-run`, exemple de calibration (unité 2) ; `fdm-slice`, skill `fdm:design`, README du plugin, passage en 1.0.0 (unité 3).
- Mise à jour du `README.md` racine, de la description globale de `marketplace.json` et du `CLAUDE.md` racine (« Plugin actuel : sdlc ») : à traiter dans l'unité 3.
- Lecture de `userConfig` par les commandes : c'est le skill de l'unité 3 qui passera les options en arguments.
- Détection de Bambu Studio sous Linux, Windows, autres slicers ; exécution réelle de pip ou de Bambu Studio en test ou en CI ; toute modification de `~/3d-design`.

## Clarifications
Aucune.
