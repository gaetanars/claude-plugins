# Plan : Vérification des pièces fdm (fdm_tools.check, fdm-run, cube de calibration)

Feature : 0002-fdm-check-run · Spec : docs/features/0002-fdm-check-run/spec.md

## Approche
Portage de `~/3d-design/tools/check.py` dans `plugins/fdm/lib/fdm_tools/check.py` en ne changeant que le nécessaire : la constante `A1_BUILD_VOLUME` et la densité PLA en dur (`1.24`) sont remplacées par une fonction privée `_printer()` qui lit `$FDM_DATA/profiles/{machine,filament}.json` et renvoie `(W, D, H)`, nom de machine, densité et type de filament ; `check()` l'appelle en première instruction, avant `mkdir` et les exports ; un registre de module `RESULTS = []` reçoit la liste `issues` de chaque `check()` (append juste avant le `return`). Le reste (`VIEWS`, `render()`, exports aux tolérances 0.01/0.1, contrôles, lignes imprimées) est copié tel quel ; `MIN_WALL`, inutilisé dans l'original, est retiré (aucun contrôle de paroi, cf. Hors périmètre).

`fdm_tools/__init__.py` ne contient que `from fdm_tools.check import check`. L'attribut `fdm_tools.check` désigne donc la fonction et non le module : `run.py` importe le registre par `from fdm_tools.check import RESULTS` (résolu via `sys.modules`) ; `RESULTS` n'est jamais réaffecté, seulement complété par `append`.

`fdm_tools/run.py` : `sys.argv = [PIECE, *ARGS]` ; `runpy.run_path(PIECE, run_name="__main__")` ; toute exception et tout `SystemExit` dont le code n'est ni `None` ni `0` se propage (un `SystemExit(0)` de la pièce poursuit vers l'agrégation, lecture retenue de « SystemExit non nul se propage » de CA-6) ; puis `sys.exit` : 1 avec le message de CA-6 si `RESULTS` est vide, 1 si `any(RESULTS)`, 0 sinon.

`bin/fdm-run` reprend la structure de `plugins/fdm/bin/fdm-setup` et `fdm-profiles` (`argparse`, `data = args.data or os.environ.get("CLAUDE_PLUGIN_DATA")`, même message d'absence, `sys.exit("erreur : …")`). Arguments : `--data`, `piece`, `args` avec `nargs=argparse.REMAINDER` (après `PIECE`, `--data x` va à la pièce ; une option inconnue avant `PIECE` donne la sortie 2). Lancement : `subprocess.run([<data>/venv/bin/python, "-m", "fdm_tools.run", piece, *args], env=…)` sans capture, puis `sys.exit(r.returncode)`. `PYTHONPATH = os.pathsep.join([lib] + ([old] if old else []))`, sans entrée vide (qui ajouterait le répertoire courant) ; `lib = Path(__file__).resolve().parent.parent / "lib"`.

Apprentissages appliqués (`docs/learnings.md`) :
- 2026-11-19 « toujours `<data>/venv/bin/python -m …` » : `fdm-run` n'appelle aucun script console du venv.
- 2026-11-19 « toute commande `fdm-*` protège ses écritures disque par `except OSError` » : `fdm-run` n'écrit rien ; sa seule opération système (lancement du sous-processus) est protégée par `except OSError` (Python du venv non exécutable) avec un message citant le chemin. Dans `check()`, le `mkdir` du dossier parent est protégé (CA-9).
- 2026-11-19 [architecture] « tests et CI stdlib et hors ligne » : faux venv et lecture AST, aucun import de `fdm_tools`.
- 2026-11-19 « `${user_config.*}` absent de l'environnement de `bin/` » : `fdm-run` ne dépend que de `--data`/`CLAUDE_PLUGIN_DATA` ; le skill (unité 3) passera `--data`.

Choix locaux, sans alternative structurante :
- Message de dépassement : `exceeds build volume {w:g} × {d:g} × {h:g} mm ({name})`, `name = machine.get("name", "?")` (non exigé par CA-7 ; `fdm-profiles` l'écrit toujours).
- Erreurs de profil interceptées : `OSError`, `ValueError` (JSON invalide, `float`, liste vide), `KeyError`, `TypeError`, `IndexError`, `AttributeError` → `erreur : profil illisible <chemin> (<détail>), relancer fdm-profiles`.
- `FDM_DATA` absent → `erreur : FDM_DATA absent, lancer la pièce avec fdm-run`.
- Code de retour négatif (signal) relayé tel quel par `sys.exit`.
- Messages de commit en anglais, comme l'historique récent et les préférences globales.

## Étapes
Chaque étape suit le cycle TDD en deux commits : `test(...)` (tests seuls, rouges), puis `feat(...)` (code, sans toucher aux fichiers du commit de tests). `plan.md` est commité (`docs(0002-fdm-check-run): plan`) avant le premier commit `test`.

### Étape 1 : lanceur `fdm-run`
- **Tests à écrire d'abord** : `tests/test_fdm_run.py` (nouveau, sur le modèle de `tests/test_fdm_setup.py`). Faux `<data>/venv/bin/python` (shebang `sys.executable`) qui ajoute une ligne JSON à `FAKE_LOG` (`argv[0]`, `argv[1:]`, `os.getcwd()`, `PYTHONPATH`, `FDM_DATA`), imprime `fake-out` sur stdout et `fake-err` sur stderr, sort avec `int(os.environ.get("FAKE_RC", "0"))`. Environnement hérité sans `CLAUDE_PLUGIN_DATA` ni `PYTHONPATH` ; projet = dossier temporaire avec `parts/p.py`, `cwd` du sous-processus ; `FAKE_LOG` hors du projet et de `<data>`. Cas :
  - `test_no_data_dir` : sortie 1, stderr contient `--data` et `CLAUDE_PLUGIN_DATA`, journal vide.
  - `test_data_from_env` : `CLAUDE_PLUGIN_DATA` seul → 0, faux Python appelé.
  - `test_data_option_overrides_env` : `--data A` avec `CLAUDE_PLUGIN_DATA=B` → Python de A appelé.
  - `test_usage_errors` : `--bogus parts/p.py` → 2 ; sans argument → 2 ; `--data` sans valeur → 2.
  - `test_missing_venv` : sortie 1, `fdm-setup` dans stderr, journal vide.
  - `test_missing_piece` : sortie 1, chemin de la pièce dans stderr, journal vide.
  - `test_piece_is_directory` : idem `test_missing_piece`.
  - `test_launches_module_in_cwd` : `argv[0] == str(Path(data) / "venv/bin/python")` ; `argv[1:] == ["-m", "fdm_tools.run", "parts/p.py", "a", "--data", "x"]` (chemin relatif conservé) ; cwd = projet (comparé après `resolve()`) ; `FDM_DATA == <data>`.
  - `test_pythonpath_without_existing` : `PYTHONPATH == str((ROOT/"plugins/fdm/lib").resolve())`, sans séparateur final.
  - `test_pythonpath_prepended` : `PYTHONPATH=/x:/y` → `<lib>:/x:/y`.
  - `test_relays_exit_code` : `FAKE_RC` 0, 1, 3 → mêmes codes.
  - `test_output_not_captured` : `fake-out` dans `r.stdout`, `fake-err` dans `r.stderr`.
  - `test_writes_nothing` : ensemble des fichiers de `<data>` et du projet identique avant/après.
  - `test_imports_stdlib_only` : lecture AST de `plugins/fdm/bin/fdm-run` ; chaque racine d'import dans `sys.stdlib_module_names`, aucune `fdm_tools`.
  - `test_venv_python_not_executable` : faux Python sans bit exécutable → sortie 1, chemin dans stderr, pas de `Traceback`.
- **Changement** : `plugins/fdm/bin/fdm-run` (nouveau, `#!/usr/bin/env python3`, mode 100755 dans l'index git).
- **Commits** : `test(fdm): cover fdm-run launcher` puis `feat(fdm): add fdm-run launcher`.
- **Couvre** : CA-1 (bin exécutable), CA-2 (volet `fdm-run`), CA-3, CA-4, CA-5, CA-10 (faux venv).

### Étape 2 : `fdm_tools.check` et `__init__`
- **Tests à écrire d'abord** : `tests/test_fdm_tools.py` (nouveau), classe `CheckSource`, lecture par `ast.parse` uniquement. Utilitaires : `strings(tree)` (toutes les constantes `str`, y compris les parties d'f-string) ; `calls(node)` (noms appelés `Name.id`/`Attribute.attr` avec ligne). Cas :
  - `test_init_exports_check` : `__init__.py` contient `ImportFrom(module="fdm_tools.check")` avec le nom `check`.
  - `test_check_signature` : `def check(part, out: str)` (2 arguments, annotation `str` sur `out`), retour annoté `trimesh.Trimesh`.
  - `test_reads_profiles_before_writing` : le premier appel dans `check` est `_printer`, à une ligne antérieure à `mkdir`, `export_step`, `export_stl`, `render`.
  - `test_profile_fields_and_messages` : chaînes contenant `FDM_DATA`, `machine.json`, `filament.json`, `printable_area`, `printable_height`, `filament_density`, `filament_type`, `fdm-run`, `fdm-profiles`.
  - `test_profile_errors_are_system_exit` : dans `_printer`, au moins un `except` capturant `OSError` et `ValueError` dont le corps appelle `sys.exit`.
  - `test_build_volume_message` : chaînes contenant `exceeds build volume` et `if solid` ; aucun identifiant `A1_BUILD_VOLUME`, aucune constante `1.24`, aucune chaîne contenant `A1` ni `PLA`.
  - `test_original_output_kept` : chaînes `--- `, `size (X×Y×Z): `, `volume: `, `overhangs >45° needing support: `, `files: `, `OK`, `ISSUES:`, `mesh is not watertight`, `inconsistent face winding`, `non-positive volume (inverted normals?)`, `part does not sit on Z=0` ; appel `export_stl` avec les mots-clés `tolerance=0.01` et `angular_tolerance=0.1` ; `VIEWS` aux clés `iso`, `front`, `right`, `top`.
  - `test_mkdir_oserror_handled` : un `Try` dont le corps appelle `mkdir` et dont un handler capture `OSError` et appelle `sys.exit`.
  - `test_results_registry` : affectation de module `RESULTS = []` ; `check` appelle `RESULTS.append` ; aucune autre affectation de `RESULTS`.
- **Changement** : `plugins/fdm/lib/fdm_tools/__init__.py` (nouveau) ; `plugins/fdm/lib/fdm_tools/check.py` (nouveau : portage, `_printer()`, `RESULTS`, `mkdir` protégé, docstring `from fdm_tools import check`).
- **Commits** : `test(fdm): cover fdm_tools.check source` puis `feat(fdm): port check to fdm_tools with profile-driven build volume`.
- **Couvre** : CA-1 (`test_files.test_python`), CA-2 (commande `arch`, R2), CA-7, CA-8, CA-9, CA-10 (AST).

### Étape 3 : runner `fdm_tools.run` et cube de calibration
- **Tests à écrire d'abord** : `tests/test_fdm_tools.py`, classes `RunnerSource` et `ExampleSource` :
  - `test_runs_piece_as_main` : appel `runpy.run_path` avec `run_name="__main__"`, précédé d'une affectation de `sys.argv`.
  - `test_reads_registry` : `ImportFrom(module="fdm_tools.check")` avec le nom `RESULTS`.
  - `test_no_check_message` : chaîne contenant `aucun check() appelé : la pièce n'est pas vérifiée`.
  - `test_nonzero_system_exit_propagates` : un handler `except SystemExit` contenant un `raise`.
  - `test_example_uses_public_api` : `examples/calibration_cube.py` contient `from fdm_tools import check` et un appel `check(…, "out/calibration_cube")` ; aucun appel `sys.path.insert`, aucune référence à `tools`.
  - `test_example_geometry` : constantes `20.0`, `5.0` et appel `chamfer` avec `1.0`.
- **Changement** : `plugins/fdm/lib/fdm_tools/run.py` (nouveau) ; `plugins/fdm/lib/fdm_tools/examples/calibration_cube.py` (nouveau, sans `__init__.py` : l'original sans `sys.path.insert`, avec `from fdm_tools import check`).
- **Commits** : `test(fdm): cover fdm_tools.run and calibration example` puis `feat(fdm): add piece runner and calibration cube example`.
- **Couvre** : CA-2 (R2, R3), CA-6, CA-10.

### Étape 4 : manifeste 0.2.0
- **Tests à écrire d'abord** : `tests/test_fdm_plugin.py::test_manifest_metadata` : `"0.1.0"` → `"0.2.0"` et `assertIn("vérification", m["description"])`.
- **Changement** : `plugins/fdm/.claude-plugin/plugin.json` : version `0.2.0`, description « Préversion : … (installation de l'environnement CAO et des profils, vérification des pièces) ».
- **Commits** : `test(fdm): expect manifest 0.2.0` puis `feat(fdm): bump fdm to 0.2.0`.
- **Couvre** : CA-1 (`test_plugins`, `test_cli_validate`, contrôle de bump avec `BASE_REF`).

### Vérification manuelle (revue, CA-11)
Sur macOS, avec un venv créé par `fdm-setup` et des profils réels générés par `fdm-profiles`, depuis un dossier vide `$T` :
1. `<repo>/plugins/fdm/bin/fdm-run --data <data> <repo>/plugins/fdm/lib/fdm_tools/examples/calibration_cube.py` → `OK`, pas de `exceeds`, `$T/out/calibration_cube.{step,stl,png}` présents, code 0.
2. Pièce `$T/parts/too_big.py` (`Box(300, 10, 10, align=(…, Align.MIN))`, `check(…, "out/too_big")`) → `ISSUES:` et `exceeds build volume 256 × 256 × 256 mm (Bambu Lab A1 0.4 nozzle)`, code 1.
3. Pièce sans `check()` → code 1 et message de CA-6.
Relevé (commandes, sorties, codes) consigné en revue.

## Couverture des critères d'acceptation
| CA | Étape(s) | Test(s) |
|----|----------|---------|
| CA-1 | 1, 2, 3, 4 | `test_files.FilesTest.test_bin_executables`, `test_files.FilesTest.test_python`, `test_cli_validate`, `test_plugins.PluginManifestTest.test_version_semver`, `test_fdm_plugin.FdmPlugin.test_manifest_metadata` |
| CA-2 | 1, 2, 3 | `test_fdm_run.Run.test_imports_stdlib_only` ; commande `arch` (`check_arch.py`, R1 à R4) lancée par `sdlc-gate verify` |
| CA-3 | 1 | `test_no_data_dir`, `test_data_from_env`, `test_data_option_overrides_env`, `test_usage_errors` |
| CA-4 | 1 | `test_missing_venv`, `test_missing_piece`, `test_piece_is_directory` |
| CA-5 | 1 | `test_launches_module_in_cwd`, `test_pythonpath_without_existing`, `test_pythonpath_prepended`, `test_relays_exit_code`, `test_output_not_captured`, `test_writes_nothing`, `test_venv_python_not_executable` |
| CA-6 | 3 | `RunnerSource.*` ; vérification manuelle (points 2 et 3) |
| CA-7 | 2 | `CheckSource.test_check_signature`, `test_reads_profiles_before_writing`, `test_profile_fields_and_messages`, `test_profile_errors_are_system_exit` |
| CA-8 | 2 | `CheckSource.test_build_volume_message`, `test_profile_fields_and_messages` ; vérification manuelle (point 2) |
| CA-9 | 2 | `CheckSource.test_original_output_kept`, `test_mkdir_oserror_handled`, `test_results_registry` ; vérification manuelle (point 1) |
| CA-10 | 1, 2, 3 | `test_fdm_run.py` (faux venv) ; `test_fdm_tools.py` (AST seul, aucun import de `fdm_tools`) |
| CA-11 | revue | vérification manuelle consignée (points 1 et 2) |

## Conformité à l'architecture
- Modules touchés : `fdm` (`plugins/fdm/bin/fdm-run`, `plugin.json`) ; `fdm-tools` (`plugins/fdm/lib/fdm_tools/` : `__init__.py`, `check.py`, `run.py`, `examples/calibration_cube.py`) ; `tests` (`test_fdm_run.py`, `test_fdm_tools.py`, `test_fdm_plugin.py`).
- Règles de dépendance : `fdm` → `fdm-tools` uniquement en sous-processus (`<data>/venv/bin/python -m fdm_tools.run`) ; `fdm-run` en bibliothèque standard (R1), sans `fdm_tools` (R3). `fdm-tools` : bibliothèque standard (`json`, `os`, `sys`, `runpy`, `pathlib`), `fdm_tools` et liste blanche (R2). `tests` → `fdm`/`fdm-tools` en lecture de fichiers et en sous-processus de `fdm-run` avec faux venv, sans import de `fdm_tools` ; les tests ne lancent pas `check_arch.py` (dépendance `tests` → `docs/architecture/native` non autorisée), CA-2 repose sur la commande `arch`. R4 : aucune référence à `plugins/sdlc` ni à `tests/` dans `plugins/fdm`.
- ADR appliquées : 0001 (volume issu du profil machine configurable, pas d'A1 en dur), 0002 (Python du venv sous `<data>`, pas de build123d en CI), 0003 (profils lus dans `<data>/profiles`, jamais embarqués), 0004 (lanceur, `PYTHONPATH` sur `plugins/fdm/lib`, sorties dans le projet, API `from fdm_tools import check` figée), 0005 (`check_arch.py`).
- Aucune entrée « Exige un ADR » : pas de nouveau module (`examples/` est dans `fdm-tools`), pas de nouvelle dépendance, emplacements inchangés ; `docs/architecture/` et `docs/adr/` non modifiés.

## Risques et points de vigilance
- Masquage du sous-module : `from fdm_tools.check import check` dans `__init__` remplace l'attribut `fdm_tools.check` par la fonction. `run.py` doit importer `RESULTS` par `from fdm_tools.check import RESULTS`, jamais `fdm_tools.check.RESULTS`. Si `RESULTS` est réaffecté au lieu d'être complété, le runner lit une liste vide et sort toujours en 1 (couvert par `test_results_registry` et la vérification manuelle point 1).
- Tests AST de portée limitée : ils vérifient la structure, pas le comportement réel de `check()` (lecture des profils, calcul du volume) ni l'agrégation de `run.py`. Une erreur de logique (min/max de la boîte, `[0]` des listes) ne se voit qu'à la vérification manuelle : la revue relit `_printer()` contre un `machine.json` réel (`printable_area` = liste de `"XxY"`, `printable_height` = chaîne).
- Exports non protégés : `export_step`/`export_stl`/`savefig` vers un dossier existant non inscriptible peuvent produire une trace Python ; la spec ne protège que le `mkdir` (CA-9).
- Bytecode : Python peut écrire `__pycache__/` sous `plugins/fdm/lib/fdm_tools/` dans le cache du plugin installé ; la contrainte « rien n'est écrit dans le plugin » vise les sorties de `check()`. Laissé tel quel.
- Exécution par `runpy` : `sys.path[0]` est le répertoire courant (racine du projet), pas `parts/` ; une pièce qui importe un module voisin échouera. Hors spec, à documenter dans le skill (unité 3).
- `fdm-run` doit être ajouté en 100755, sinon `test_bin_executables` échoue.
- Taille : environ 200 lignes de code et 230 de tests, proche de la cible de 400 ; garder des tests compacts avec des utilitaires AST partagés.

## Hors plan
- `fdm-slice`, skill `fdm:design`, README du plugin, version 1.0.0 (unité 3).
- Nouveaux contrôles (paroi minimale, position sur le plateau, zones exclues).
- Exécution de build123d, trimesh ou d'un vrai venv dans les tests et la CI.
- Ajout du dossier de la pièce à `sys.path`, `PYTHONDONTWRITEBYTECODE`, protection `OSError` des exports.
- `usb_cable_organizer.py`, toute modification de `~/3d-design`, de `docs/architecture/` ou des ADR.

## Clarifications
Aucune pendant la planification.
