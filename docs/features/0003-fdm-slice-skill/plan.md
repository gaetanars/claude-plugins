# Plan : Découpe fdm-slice, skill fdm:design et version 1.0.0

Feature : 0003-fdm-slice-skill · Spec : docs/features/0003-fdm-slice-skill/spec.md

## Approche
`plugins/fdm/bin/fdm-slice` porte `~/3d-design/tools/slice.sh` en bibliothèque standard, sur le modèle de `plugins/fdm/bin/fdm-profiles` et `fdm-run` :
- `argparse` ;
- `data = args.data or os.environ.get("CLAUDE_PLUGIN_DATA")`, avec le même message d'absence ;
- erreurs par `sys.exit("erreur : …")` ;
- exécutable par défaut sous macOS, erreur hors macOS (comme `fdm-profiles` l. 54-58).

Ni venv ni `fdm_tools`. Déroulé de `main()` :
1. Arguments `--data`, `--bambu-studio`, `stl` (positionnel). Une option inconnue ou un `stl` absent donnent une sortie 2 via argparse.
2. Préconditions, dans l'ordre de CA-4, avant toute écriture et tout lancement :
   - dossier de données ;
   - `P = Path(data) / "profiles"` et `(P / f"{k}.json").is_file()` pour `machine`, `process`, `filament` ;
   - STL : `os.path.isfile(stl)` et `stl.endswith(".stl")` ;
   - exécutable : `exe = args.bambu_studio or (MAC_EXE si sys.platform == "darwin", sinon erreur)`, puis `os.path.isfile(exe) and os.access(exe, os.X_OK)`.
3. `name = os.path.basename(stl)[:-4]` ; `OUT = Path(os.path.abspath(os.path.dirname(stl))) / f"slice_{name}"`.
   - Une `OSError` est interceptée sur chaque opération, avec un message qui cite le chemin : `mkdir(parents=True, exist_ok=True)`, `unlink(missing_ok=True)` de `plate_1.gcode` et de `<name>.3mf`, puis le lancement.
   - Lancement : `subprocess.run([...CA-5...], stdout=PIPE, stderr=STDOUT, text=True, errors="replace")`, sans `cwd`. `errors="replace"` évite une `UnicodeDecodeError` (donc une trace) si la sortie n'est pas en UTF-8.
4. Si `OUT/plate_1.gcode` est absent, quel que soit le code de retour : sur stderr, les 40 dernières lignes qui ne contiennent pas `[trace]`, puis le message d'échec renvoyant vers `fdm-profiles` ; sortie 1.
5. Sinon, lecture du gcode (`errors="replace"`, une `OSError` donne un message et une sortie 1). Pour chacun des trois préfixes, on garde la première ligne qui commence par lui, dans l'ordre du fichier.
   - Temps ou poids manquant : sortie 1, message qui cite le gcode, rien sur stdout.
   - Sinon : les lignes trouvées, puis `Output: <OUT>/<name>.3mf` ; sortie 0.

`plugins/fdm/skills/design/SKILL.md` porte `~/3d-design/.claude/skills/fdm-design/SKILL.md` en français et le rend générique :
- vérification des prérequis en tête (CA-10) ;
- commandes `fdm-*` avec `--data "${CLAUDE_PLUGIN_DATA}"` et les options `${user_config.*}` passées en arguments ;
- ligne « Build volume 256 × 256 × 256 » retirée : le volume vient du profil machine, et `check()` le signale (`exceeds build volume …`) ;
- « (A1, 0.4 nozzle, PLA) » devient « valeurs par défaut pour une buse 0.4 et du PLA » ;
- `tools/flatten_profiles.py` devient `fdm-profiles` ;
- `parts/calibration_cube.py` devient `${CLAUDE_PLUGIN_ROOT}/lib/fdm_tools/examples/calibration_cube.py` ;
- `.venv/bin/python parts/<nom>.py` devient `fdm-run …` ;
- explication de `runpy` (`sys.path[0]` = racine du projet, un `check()` par pièce).

Apprentissages appliqués (`docs/learnings.md`) :
- Tests stdlib et hors ligne : faux Bambu Studio en script Python, aucun import de `fdm_tools`, jamais le vrai Bambu Studio. Le test du défaut macOS est sauté si le vrai exécutable existe.
- `except OSError` sur toute écriture disque, avec des tests « `OUT` est un fichier », « `OUT` non inscriptible » et « `<data>` non inscriptible », sans `Traceback`.
- `${user_config.*}` absent de l'environnement de `bin/` : le skill passe tout en arguments explicites.
- Exemple sous `lib/fdm_tools/examples/` : le skill le cite, un test vérifie qu'il existe.
- `runpy` : expliqué dans le skill, vérifié par un test.
- Une valeur vide vaut absence : `args.bambu_studio or …`, testé avec `--bambu-studio ""`.

Choix locaux, sans alternative structurante :
- Extension `.stl` en minuscules uniquement : `check()` exporte en `.stl`, et un `.STL` est refusé avec le message de CA-4.
- `<P>` et `<STL>` sont passés tels quels (répertoire courant inchangé, comme l'original) ; `OUT` est absolu.
- Messages en français, préfixés par `erreur : ` :
  - `profil absent : <chemin>, lancer fdm-profiles`
  - `STL introuvable ou sans extension .stl : <stl>`
  - `exécutable Bambu Studio introuvable ou non exécutable : <exe>, renseigner l'option bambu_studio (--bambu-studio)`
  - `exécutable Bambu Studio requis hors macOS, renseigner l'option bambu_studio (--bambu-studio)`
  - `création de <OUT> impossible : <e>`, `suppression de <f> impossible : <e>`, `lancement de <exe> impossible : <e>`, `lecture de <gcode> impossible : <e>`
  - `découpe échouée (<gcode> absent) ; après une mise à jour de Bambu Studio, relancer fdm-profiles`
  - `temps ou poids absent de <gcode>`
- Valeurs calibrées : le skill dit de les utiliser à la place des valeurs par défaut, sans « mettre à jour ce tableau » (le plugin installé n'est pas modifiable par l'utilisateur).
- README racine : « ## Plugin » devient « ## Plugins », et `claude plugin update fdm@gaetanars` est ajouté à « Mise à jour ».

## Étapes
Chaque étape suit le cycle TDD en deux commits : `test(...)` (tests seuls, rouges), puis `feat(...)` (code, sans toucher aux fichiers du commit de tests). `plan.md` est commité (`docs(0003-fdm-slice-skill): plan`) avant le premier commit `test`.

### Étape 1 : `fdm-slice`, découpe nominale
- Tests à écrire d'abord : `tests/test_fdm_slice.py` (nouveau), sur le modèle de `tests/test_fdm_run.py` et `tests/test_fdm_profiles.py`.
  - Utilitaire `run(*args, platform=None, **env)`, repris de `tests/test_fdm_profiles.py` (forçage de `sys.platform` par `runpy`) ; environnement hérité sans `CLAUDE_PLUGIN_DATA`, `cwd` = dossier projet temporaire.
  - Faux Bambu Studio `self.t/bs` (shebang `sys.executable`, mode 755). Il :
    - ajoute `[argv[1:], os.getcwd()]` en JSON à `FAKE_LOG` ;
    - écrit sur stdout et stderr les lignes `line 1` à `line <FAKE_LINES>`, entrecoupées de lignes `[trace] t<i>` ;
    - si `FAKE_GCODE` est défini, écrit son contenu dans `<--outputdir>/plate_1.gcode` ;
    - sort avec le code `FAKE_RC`.
  - `setUp` :
    - `<data>/profiles/{machine,process,filament}.json` ;
    - `<data>` sans `venv/`, ce qui prouve que le venv n'est pas utilisé ;
    - projet `project/out/p.stl` ;
    - `FAKE_LOG` hors du projet et de `<data>`.
  - `GCODE_OK`, dans cet ordre :
    - une ligne quelconque ;
    - `; total filament weight [g] : 3.1` ;
    - `; model printing time: 12m 3s; total estimated time: 15m` ;
    - `; total filament length [mm] : 1000` ;
    - un doublon `; total filament weight [g] : 9`.
  - `test_data_from_env` : avec `CLAUDE_PLUGIN_DATA` seul, sortie 0 et un appel.
  - `test_data_option_overrides_env` : `--data A` avec `CLAUDE_PLUGIN_DATA=B` (B sans profils) donne une sortie 0, et `--load-settings` cite les chemins de A.
  - `test_usage_errors` : `--bogus out/p.stl`, aucun argument, `--data` seul : sortie 2, journal vide.
  - `test_command_line` :
    - argv exactement égal à la liste de CA-5 ;
    - `out/p.stl` relatif conservé, `p.3mf` ;
    - `--outputdir` = `<projet>/out/slice_p` ;
    - cwd = projet ;
    - chemins comparés après `resolve()`.
  - `test_success_output` : stdout = exactement les lignes poids, temps et longueur (premières occurrences, ordre du fichier), puis `Output: <OUT>/p.3mf` ; sortie 0 ; `line ` absent de stdout et de stderr.
  - `test_length_optional` : sans la ligne de longueur, sortie 0.
  - `test_missing_time_or_weight` : sous-tests sans temps, puis sans poids ; sortie 1, chemin du gcode dans stderr, stdout vide.
  - `test_failure_tail` :
    - `FAKE_LINES=60`, pas de gcode, `FAKE_RC` à 0 puis à 3 ;
    - sortie 1 ;
    - stderr contient `line 21` à `line 60`, mais ni `line 20` ni `[trace]` ;
    - stderr contient `fdm-profiles`.
  - `test_stale_outputs_removed` :
    - `OUT/plate_1.gcode` (contenu valide), `OUT/p.3mf` et `OUT/keep.txt` préexistants ; le faux n'écrit rien ;
    - sortie 1 ;
    - `plate_1.gcode` et `p.3mf` absents, `keep.txt` présent.
  - `test_writes_only_in_out` : d'après un instantané de `<data>` et du projet, tous les fichiers créés ou modifiés sont sous `OUT`.
  - `test_imports_stdlib_only` : lecture AST, comme `test_fdm_run.py`.
- Changement : `plugins/fdm/bin/fdm-slice` (nouveau, `#!/usr/bin/env python3`, 100755 dans l'index git).
  - Inclus : arguments, données, exécutable (`--bambu-studio` ou `MAC_EXE`), `OUT`, suppression des anciens fichiers, lancement, analyse du résultat.
  - Pas encore : les préconditions de CA-4 ni les `except OSError`.
- Commits : `test(fdm): cover fdm-slice nominal slicing` puis `feat(fdm): add fdm-slice command`.
- Couvre : CA-1 (`test_bin_executables`), CA-2, CA-3 (données, usage, sans venv), CA-5, CA-6, CA-7, CA-8.

### Étape 2 : `fdm-slice`, préconditions et erreurs système
- Tests à écrire d'abord : `tests/test_fdm_slice.py`, avec l'utilitaire `assert_clean_failure(r, text)` (sortie 1, `text` dans stderr, pas de `Traceback`, journal vide si rien n'a été lancé).
  - `test_no_data_dir` : sortie 1, `--data` et `CLAUDE_PLUGIN_DATA` dans stderr.
  - `test_missing_profile` : sous-tests pour chacun des trois profils ; stderr cite le chemin et `fdm-profiles`.
  - `test_bad_stl` : STL inexistant, dossier nommé `d.stl`, fichier `p.txt` ; chemin cité.
  - `test_exe_not_executable` : `--bambu-studio` vers un fichier non exécutable, puis vers un chemin absent ; stderr cite le chemin et `bambu_studio`.
  - `test_non_macos_requires_exe` : `platform="linux"`, sans option puis avec `--bambu-studio ""` ; stderr cite `bambu_studio` et `--bambu-studio`.
  - `test_macos_default_exe` : sauté si `MAC_EXE` existe ; `platform="darwin"`, `--bambu-studio ""` ; stderr cite `MAC_EXE`.
  - `test_out_is_a_file` : `project/out/slice_p` est un fichier ; chemin cité.
  - `test_out_not_writable` : `OUT` en `0o500` avec un `plate_1.gcode` périmé (sauté sous root) ; `OUT` cité, gcode conservé.
  - `test_data_not_writable` : `<data>` et `profiles/` en `0o500` (sauté sous root) ; sortie 0, pas de `Traceback`.
  - `test_launch_oserror` : `--bambu-studio` vers un fichier exécutable sans shebang, au contenu binaire (`ENOEXEC`) ; sortie 1, chemin cité, pas de `Traceback`.
- Changement : `plugins/fdm/bin/fdm-slice`.
  - Avant `mkdir` : préconditions de CA-3 et CA-4, et cas « hors macOS sans valeur ».
  - `try/except OSError` autour de `mkdir`, `unlink`, `subprocess.run` et de la lecture du gcode.
- Commits : `test(fdm): cover fdm-slice preconditions and disk errors` puis `feat(fdm): validate fdm-slice inputs and handle OS errors`.
- Couvre : CA-3, CA-4, CA-5 (`OSError`), CA-8.

### Étape 3 : skill `fdm:design`
- Tests à écrire d'abord : `tests/test_fdm_skill.py` (nouveau). Il lit `plugins/fdm/skills/design/SKILL.md` avec `tests._common.parse_frontmatter`.
  - `test_frontmatter` : `name == "design"`, pas de `disable-model-invocation` ; la description contient `conception`, `modification`, `vérification`, `découpe` et `3D`.
  - `test_commands_exist` : tout nom trouvé par `\bfdm-[a-z]+\b` est un fichier de `plugins/fdm/bin/`.
  - `test_invocations_pass_data` :
    - toute invocation de `fdm-setup`, `fdm-profiles`, `fdm-run` ou `fdm-slice` suivie d'un argument, dans un extrait de code (span en accent grave ou ligne de bloc), contient `--data "${CLAUDE_PLUGIN_DATA}"` ;
    - chacune des quatre commandes est invoquée au moins une fois.
  - `test_exact_commands` : les quatre commandes de CA-10 figurent mot pour mot.
  - `test_plugin_root_paths_exist` : tout chemin `${CLAUDE_PLUGIN_ROOT}/<chemin>` cité existe sous `plugins/fdm/`, dont `…/lib/fdm_tools/examples/calibration_cube.py`.
  - `test_prerequisites_and_runpy` : le skill contient `${CLAUDE_PLUGIN_DATA}/venv/bin/python`, `machine.json`, `process.json`, `filament.json`, `sys.path[0]`, `from fdm_tools import check` et `check()`.
  - `test_generic_rules` : le skill contient `0.4`, `PLA`, `out/<nom>.png` et `.3mf`, mais ni `256` ni `A1`.
- Changement : `plugins/fdm/skills/design/SKILL.md` (nouveau, en français, environ 90 lignes).
  - Frontmatter `name: design` et `description:` sur une ligne.
  - Sections :
    - Prérequis (arrêt tant qu'ils manquent) ;
    - Outils ;
    - Déroulé (les 8 étapes d'origine) ;
    - Règles FDM (valeurs par défaut, sans volume d'impression) ;
    - Conseils build123d.
- Commits : `test(fdm): cover design skill consistency` puis `feat(fdm): add fdm:design skill`.
- Couvre : CA-1 (`test_skills`, `test_cli_validate`), CA-9, CA-10, CA-11.

### Étape 4 : documentation et version 1.0.0
- Tests à écrire d'abord : `tests/test_fdm_plugin.py`.
  - `test_marketplace_entry` : `assertNotIn("Préversion", …)` et `assertIn("découpe", …)`.
  - `test_manifest_metadata` : version `"1.0.0"`, pas de `Préversion`, `vérification` et `découpe` dans la description.
  - `test_plugin_readme` (nouveau) : `plugins/fdm/README.md` contient :
    - `Bambu Studio`, `3.11`, `3.14`, `300 Mo` ;
    - `/plugin install fdm@gaetanars`, `fdm-setup`, `fdm-profiles` ;
    - `/fdm:design`, `parts/`, `out/` ;
    - les six clés `userConfig` (lues dans `plugin.json`) ;
    - `non vérifié`.
  - `test_root_readme` (nouveau) : le README racine contient une ligne qui commence par `` | `fdm` | 1.0.0 | `` et `/plugin install fdm@gaetanars`.
- Changement :
  - `plugins/fdm/.claude-plugin/plugin.json` : version `1.0.0`, description sans « Préversion » qui mentionne vérification, rendu et découpe.
  - `.claude-plugin/marketplace.json` : description de l'entrée `fdm` sans « Préversion », avec la découpe.
  - `plugins/fdm/README.md` (nouveau).
  - `README.md` : ligne `fdm` dans la table, `/plugin install fdm@gaetanars`, `claude plugin update fdm@gaetanars`.
- Commits : `test(fdm): expect release 1.0.0 and documentation` puis `feat(fdm): release fdm 1.0.0 with documentation`.
- Couvre : CA-1 (`test_plugins`, `test_fdm_plugin`, `test_cli_validate`, bump avec `BASE_REF`), CA-12.

### Vérification manuelle (revue, CA-13)
Sur macOS, avec le plugin installé depuis le clone local de la branche, et `fdm-setup` et `fdm-profiles` réels, dans un dossier de projet vide `$T` :
1. `/fdm:design` sur le cube de calibration :
   - `fdm-run` affiche `OK` et sort en 0 ;
   - le skill lit `out/calibration_cube.png` ;
   - `fdm-slice` affiche le temps, le poids et `Output: …/out/slice_calibration_cube/calibration_cube.3mf`, et sort en 0.
2. `fdm-slice --data <copie de data avec un machine.json invalide> out/calibration_cube.stl` : sortie 1, dernières lignes de Bambu Studio, renvoi vers `fdm-profiles`.
3. Suppression de `$T` et de la copie de `<data>`.

Le relevé (commandes, sorties, codes de sortie) est consigné en revue.

## Couverture des critères d'acceptation
| CA | Étape(s) | Test(s) |
|----|----------|---------|
| CA-1 | 1, 3, 4 | `test_files` (`test_bin_executables`, `test_python`), `test_skills`, `test_cli_validate`, `test_plugins`, `test_fdm_plugin` (`test_manifest_metadata`, `test_marketplace_entry`) |
| CA-2 | 1 | `test_fdm_slice.test_imports_stdlib_only` ; commande `arch` (`check_arch.py`) via `sdlc-gate verify` |
| CA-3 | 1, 2 | `test_data_from_env`, `test_data_option_overrides_env`, `test_usage_errors`, `test_no_data_dir` ; `<data>` sans venv |
| CA-4 | 2 | `test_missing_profile`, `test_bad_stl`, `test_exe_not_executable`, `test_non_macos_requires_exe`, `test_macos_default_exe` |
| CA-5 | 1, 2 | `test_command_line`, `test_stale_outputs_removed`, `test_out_is_a_file`, `test_out_not_writable`, `test_launch_oserror` |
| CA-6 | 1 | `test_failure_tail`, `test_stale_outputs_removed` |
| CA-7 | 1 | `test_success_output`, `test_length_optional`, `test_missing_time_or_weight` |
| CA-8 | 1, 2 | `tests/test_fdm_slice.py` (faux Bambu Studio), dont `test_stale_outputs_removed`, `test_data_not_writable`, `test_out_not_writable`, `test_out_is_a_file` |
| CA-9 | 3 | `test_fdm_skill.test_frontmatter`, `test_generic_rules` ; relecture en revue |
| CA-10 | 3 | `test_exact_commands`, `test_prerequisites_and_runpy`, `test_plugin_root_paths_exist` |
| CA-11 | 3 | `test_commands_exist`, `test_invocations_pass_data`, `test_plugin_root_paths_exist` |
| CA-12 | 4 | `test_plugin_readme`, `test_root_readme` |
| CA-13 | revue | vérification manuelle consignée |

## Conformité à l'architecture
- Modules touchés :
  - `fdm` : `bin/fdm-slice`, `skills/design/SKILL.md`, `README.md`, `plugin.json` ;
  - `marketplace` : description de l'entrée `fdm`, sans version ;
  - `tests` ;
  - `README.md` racine.
  - `fdm-tools` reste inchangé.
- Dépendances :
  - `fdm-slice` n'importe que la bibliothèque standard (R1) et n'importe ni n'appelle `fdm_tools` (R3) ;
  - le skill ne référence que `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}` et le projet (R4) ;
  - les tests lisent des fichiers et lancent `fdm-slice` avec un faux Bambu Studio, sans importer `fdm_tools`.
- ADR appliquées :
  - 0001 : exécutable configurable, défaut macOS, Linux best effort ;
  - 0002 : pas de CAO en CI, pas de venv pour `fdm-slice` ;
  - 0003 : profils lus dans `<data>/profiles`, renvoi vers `fdm-profiles` ;
  - 0004 : sorties sous `out/slice_<nom>/` du projet, `fdm-run`, API `from fdm_tools import check` inchangée ;
  - 0005 : `check_arch.py`.
- Aucune décision de la liste « Exige un ADR » : `fdm-slice` est déjà prévue dans le module `fdm` ; ni dépendance ni emplacement nouveaux ; `docs/architecture/` et `docs/adr/` restent inchangés.

## Risques et points de vigilance
- Lancement accidentel du vrai Bambu Studio : tous les tests nominaux passent `--bambu-studio <faux>`, et le seul test du défaut macOS est sauté si le vrai exécutable existe.
- Fin de la sortie capturée : `[trace]` est filtré avant de prendre les 40 dernières lignes ; `test_failure_tail` fixe les bornes (`line 21` à `line 60`).
- Chemins macOS `/var` et `/private/var` : comparer `OUT` et cwd après `resolve()`.
- `test_commands_exist` : le skill doit écrire `fdm_tools` (module) et `fdm:design`, jamais `fdm-tools` ni `fdm-design`.
- `test_invocations_pass_data` ne voit que les extraits de code. Une commande nommée en prose est une mention ; la revue vérifie que chaque instruction d'exécution donne la commande complète.
- Tests de permissions : sautés sous root.
- Taille : environ 560 lignes, au-delà de la cible de 400. L'essentiel vient des tests imposés par CA-8 ; les tests restent compacts (sous-tests, utilitaires partagés), et le skill ne répète pas le README.
- Format réel des lignes gcode de Bambu Studio : seul le préfixe compte, à confirmer à la vérification manuelle.
- `fdm-slice` doit être ajouté en 100755.
- Bump : 1.0.0 n'arrive qu'à l'étape 4, donc le contrôle `BASE_REF` n'est vert qu'après cette étape.

## Hors plan
- Modifier `fdm-setup`, `fdm-profiles`, `fdm-run`, `fdm_tools` ou `requirements.txt`.
- Délai maximal de découpe, détection de Bambu Studio sous Linux, Windows, autres slicers, `.STL` en majuscules.
- Hook de démarrage, `usb_cable_organizer.py`, toute modification de `~/3d-design`.
- `CLAUDE.md` racine (« Plugin actuel : `sdlc` ») et tableau « Ce que la CI contrôle » du README : à proposer séparément.
- `docs/architecture/`, ADR.

## Clarifications
Aucune pendant la planification.
