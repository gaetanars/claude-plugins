# Écosystèmes pris en charge

Référence pour composer `.forge/config.json`, la CI et la liste de commandes autorisées. Ce n'est pas du code : `forge.py doctor` valide la configuration produite, quel que soit le langage.

**Contrat universel** : une porte `tests` (marquée `"tests": true`) qui écrit un rapport JUnit XML à `junit_path` (un glob est accepté quand l'outil écrit un fichier par classe) et sort en erreur si un test échoue. Le nom du testcase (ou sa classe) porte l'identifiant `AC-n`. Un écosystème sans JUnit n'est pas pris en charge.

Les outils déjà présents dans le dépôt priment sur ce tableau. Dépôt neuf : prends la ligne « par défaut ». Vérifie les versions courantes des outils et des actions CI avant de les figer.

| Écosystème | Tests + JUnit (`test_cmd`) | Format | Lint | Typage | Couverture (porte `tests`) | Setup CI |
|---|---|---|---|---|---|---|
| **Python** | `uv run pytest -q -p no:cacheprovider --junitxml=.forge/out/junit.xml` | `uv run ruff format --check .` | `uv run ruff check .` | `uv run pyright` (ou mypy) | `… --cov --cov-fail-under=85` (pytest-cov) | `astral-sh/setup-uv`, `uv sync --locked` |
| **TypeScript / JS** | `npx vitest run --reporter=junit --outputFile.junit=.forge/out/junit.xml` | `npx biome format .` (ou prettier `--check`) | `npx biome lint .` (ou ESLint) | `npx tsc --noEmit` (strict) | `--coverage` + `coverage.thresholds` dans la config Vitest (`@vitest/coverage-v8`) | `actions/setup-node`, `npm ci` (ou pnpm/yarn) |
| **Go** | `gotestsum --junitfile .forge/out/junit.xml -- ./...` | `test -z "$(gofmt -l .)"` | `golangci-lint run` | `go vet ./...` (le compilateur type déjà) | `-coverprofile` + contrôle du seuil par script | `actions/setup-go`, `go mod download` |
| **Rust** | `cargo nextest run --profile ci` ; `junit_path` = `target/nextest/ci/junit.xml` (profil `[profile.ci.junit] path = "junit.xml"` dans `.config/nextest.toml`) | `cargo fmt --check` | `cargo clippy --all-targets -- -D warnings` | compilateur | `cargo llvm-cov nextest --fail-under-lines 85` | `dtolnay/rust-toolchain`, `taiki-e/install-action` (nextest, llvm-cov) |
| **Java / Kotlin** | Maven : `mvn -q test` ; `junit_path` = `target/surefire-reports/TEST-*.xml`. Gradle : `./gradlew test` ; `build/test-results/test/TEST-*.xml` | Spotless `check` / ktlint | Checkstyle, PMD, detekt | compilateur | JaCoCo avec règle de seuil | `actions/setup-java`, cache Maven/Gradle |
| **.NET** | `dotnet test --logger "junit;LogFilePath=$PWD/.forge/out/junit.xml"` (paquet `JunitXml.TestLogger`) | `dotnet format --verify-no-changes` | analyseurs + `-warnaserror` | compilateur | coverlet avec seuil | `actions/setup-dotnet` |
| **Ruby** | `bundle exec rspec --format progress --format RspecJunitFormatter --out .forge/out/junit.xml` (gem `rspec_junit_formatter`) | `bundle exec rubocop` | RuboCop | Sorbet (`srb tc`) optionnel | SimpleCov `minimum_coverage` | `ruby/setup-ruby` (`bundler-cache: true`) |
| **PHP** | `vendor/bin/phpunit --log-junit .forge/out/junit.xml` | `vendor/bin/pint --test` (ou php-cs-fixer `--dry-run`) | PHPStan | PHPStan (niveau élevé) | pcov/Xdebug + contrôle du seuil par script | `shivammathur/setup-php`, `composer install` |

## Pour chaque ligne, renseigne aussi

| Écosystème | `test_globs` | `suppression_markers` | Exclure `.forge/` des outils |
|---|---|---|---|
| Python | `tests/*`, `test_*.py`, `*_test.py`, `conftest.py` | `# type: ignore`, `# noqa`, `# pyright: ignore`, `pragma: no cover` | `testpaths = ["tests"]` (pytest) |
| TypeScript / JS | `tests/*`, `*.test.ts`, `*.spec.ts` (+ `.tsx`, `.js`) | `@ts-ignore`, `@ts-expect-error`, `eslint-disable`, `biome-ignore`, `v8 ignore` | `exclude: ['.forge/**']` (Vitest), `vcs.useIgnoreFile` (Biome), `include` de `tsconfig.json` |
| Go | `*_test.go` | `//nolint`, `// nolint` | rien : Go ignore les dossiers commençant par `.` |
| Rust | `tests/*`, `tests.rs` | `#[allow(`, `#[expect(`, `LLVM_COV_EXCL` | rien (le worktree est hors du workspace Cargo ; sinon `exclude` du workspace) |
| Java / Kotlin | `src/test/*` | `@SuppressWarnings`, `@Suppress`, `NOSONAR` | le worktree ne fait pas partie du build du checkout principal |
| .NET | `*Tests/*`, `*Tests.cs`, `tests/*` | `#pragma warning disable`, `[SuppressMessage`, `[ExcludeFromCodeCoverage]` | `<DefaultItemExcludes>` : `.forge/**` |
| Ruby | `spec/*`, `*_spec.rb` | `# rubocop:disable`, `# :nocov:`, `# typed: ignore` | `.rubocop.yml` : `AllCops/Exclude` `.forge/**/*` |
| PHP | `tests/*`, `*Test.php` | `@phpstan-ignore`, `@codeCoverageIgnore`, `phpcs:ignore` | `phpunit.xml` : `testsuite` limité à `tests` ; `exclude` PHPStan |

`acceptance_dir` : `tests/acceptance` partout, sauf convention locale contraire (Go : un sous-dossier de paquet `acceptance/` ; Java : `src/test/java/.../acceptance`). Il doit correspondre à `test_globs`.

## Nommer les tests avec l'identifiant AC-n

`forge.py` reconnaît `AC-1`, `AC_1`, `AC 1`, `ac1` (insensible à la casse) dans le nom ou la classe du testcase JUnit. Il faut un identifiant qui survit au rapport : Python `test_ac1_…`, Go `TestAC1_…`, JS `it('AC-1 …')`, Rust `fn ac1_…`, JUnit `void ac1_…()`, RSpec `it 'AC-1 …'`.

## Dépôt vide : squelette minimal

Outillage + un test de fumée qui passe (un seul testcase, `smoke`), pour que `doctor` et `gate` soient verts avant la première tâche. Pas d'architecture : la première tâche la décide.
