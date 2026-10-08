# Contrat d'intégration projet ↔ tdd-forge

Le plugin porte la cinématique (PO → plan → rouge → vert → refactor → revue → livraison). Le projet porte la technique : lanceur, framework, dossiers, types de tests, couverture, style. Cette page liste ce que `.forge/config.json` doit fournir pour que le moteur (`forge.py`) puisse faire respecter les invariants du flux. Ce n'est pas du code : `forge.py doctor` valide ce qui a été écrit.

## Invariants (portés par le plugin)

1. Rouge d'abord : la commande de test échoue, et chaque `AC-n` a au moins un cas en échec.
2. Vert : la commande passe, toutes les portes passent, et chaque `AC-n` a au moins un cas, sans aucun échec.
3. Les tests d'acceptation sont verrouillés après le rouge (empreinte).
4. Séparation des rôles : le test-writer n'écrit que des tests, l'implementer jamais de tests.
5. Les résultats sont déterministes (sinon la détection d'absence de progrès n'a pas de sens).
6. Les critères d'acceptation sont vérifiables automatiquement.

## Ce que le projet fournit

| Clé | Contenu |
|---|---|
| `test_cmd` | Commande de test. Code de sortie ≠ 0 si un test échoue. Écrit les résultats au format neutre à `results_path` (elle-même, ou enchaînée à un adaptateur). |
| `results_path` | Chemin (glob accepté ; plusieurs fichiers sont concaténés) du JSON de résultats. Par défaut `.forge/out/results.json`. |
| `test_globs` | Motifs des fichiers de test (chemin relatif ou nom de fichier, `fnmatch`). Le rédacteur de tests n'écrit que là ; l'implémenteur n'y écrit jamais. |
| `acceptance_globs` | Motifs (même sémantique) des tests d'acceptation, verrouillés après le rouge. Aucune valeur par défaut. |
| `gates` | Portes libres `{name, cmd, timeout?}` : format, lint, typage, sécurité, couverture… à la discrétion du projet. Une porte au moins porte `"tests": true` : elle exécute les tests et produit les résultats. |
| `suppression_markers` | Textes qui signalent une suppression d'alerte dans le code (liste du projet ; peut être vide). |
| Exclusion de `.forge/` | Les outils du projet (lanceur, formateur, linter) ne doivent pas parcourir `.forge/` depuis le checkout principal : les worktrees y vivent. |
| CI | Le bloc `# setup … # endsetup` de `.github/workflows/forge-gates.yml` installe la toolchain et les dépendances du projet. |

## Format neutre des résultats

```json
{"cases": [{"name": "AC-1 refuse un montant négatif", "failed": true, "acs": ["AC-1"]}]}
```

- `name` (texte) et `failed` (booléen) sont obligatoires. Un JSON invalide ou un cas incomplet rend les résultats inexploitables (rouge refusé, `doctor` en échec).
- `acs` est facultatif : s'il est présent, c'est le lien explicite vers les critères (tags, annotations, markers selon la stack). Sinon, les identifiants `AC-n` (`AC-1`, `AC_1`, `AC 1`, `ac1`, insensible à la casse) sont cherchés dans `name`.
- Un code de sortie ≠ 0 sans aucun cas en échec est un « échec sans test identifiable » (outillage).

## Adaptateur

Quand le lanceur n'écrit pas ce format, la commande de test s'en charge, ou `init` écrit un adaptateur dans `.forge/adapters/` (versionné, protégé : l'implémenteur ne peut pas le modifier) et l'enchaîne dans `test_cmd`, en conservant le code de sortie du lanceur. L'adaptateur est du code du projet, dans le langage de son choix. Exemples **illustratifs** :

Convertir un rapport JUnit XML en format neutre (Python, bibliothèque standard) :

```python
import json, sys, xml.etree.ElementTree as ET
cases = [{"name": f"{tc.get('classname', '')} {tc.get('name', '')}".strip(),
          "failed": any(c.tag in ("failure", "error") for c in tc)}
         for tc in ET.parse(sys.argv[1]).getroot().iter("testcase")]
json.dump({"cases": cases}, open(sys.argv[2], "w"))
```

Lanceur minimal sans aucun framework (`test_cmd` = `sh tests/run.sh`) :

```sh
mkdir -p .forge/out
if sh tests/ac1.sh; then f=false; else f=true; fi
printf '{"cases":[{"name":"AC-1 comportement attendu","failed":%s}]}' "$f" > .forge/out/results.json
[ "$f" = false ]
```

Le nom du cas doit survivre jusqu'aux résultats : si le lanceur ne publie pas l'identifiant, passe par `acs`.

## Limite du flux

Les tests intégrés aux fichiers source (ex. modules de test dans le même fichier que le code) sont incompatibles avec la séparation des rôles par fichiers : le test-writer et l'implementer ne pourraient pas être distingués par chemin. C'est une limite du flux, pas d'un langage.
