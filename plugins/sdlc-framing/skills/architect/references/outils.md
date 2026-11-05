# Outils de contrôle d'architecture : pistes par langage

**Pistes non contraignantes, à vérifier** (existence, version, syntaxe de configuration) avant usage : cette liste vieillit. Le SDLC ne dépend d'aucun outil : seul compte que la commande `arch` retourne 0 quand les règles sont respectées et ≠ 0 sinon.

| Langage | Pistes |
|---|---|
| Python | import-linter (contrats de couches/indépendance), tach |
| TypeScript / JavaScript | dependency-cruiser, eslint-plugin-boundaries |
| Go | go-arch-lint, depguard (golangci-lint) |
| Java / Kotlin | ArchUnit (test JUnit) |
| C# | NetArchTest, ArchUnitNET |
| Rust | cargo-deny (dépendances de crates) ; les frontières de modules internes passent par la structure en crates/workspaces |
| Autre | un script versionné sous `docs/architecture/native/` qui lit `rules.json` et échoue sur toute dépendance interdite |

## Exigences communes
- Configuration et baseline sous `docs/architecture/native/` uniquement ; la commande `arch` les référence par chemin explicite.
- Les modules et dépendances de la configuration reflètent `rules.json` (même découpage, mêmes interdits).
- Commande déterministe, sans réseau à l'exécution, code de sortie fiable.
- Montrer qu'elle mord : une violation volontaire doit la rendre rouge.
