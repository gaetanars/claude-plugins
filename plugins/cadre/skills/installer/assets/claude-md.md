## Cadre de travail (plugin cadre)

Références : `PRODUCT.md` (vision), `ARCHITECTURE.md` (frontières), `docs/adr/` (décisions), `docs/specs/` (specs validées).

### Définition de « fini »

1. Un test d'acceptation par `AC-n` de la spec, sous `acceptance_dir` (`.claude/check.json`), écrit et commité d'abord, rouge pour la bonne raison.
2. Puis des micro-cycles TDD (test unitaire → code → refactor) : les tests unitaires évoluent avec le design.
3. La commande `check` de `.claude/check.json` est verte.
4. `/code-review` est passé.
5. La PR référence la spec. L'humain merge.

### Interdits

- Modifier un test d'acceptation commité sans accord explicite.
- Supprimer une alerte (lint, types, couverture) sans motif sur la même ligne.
- Ajouter une dépendance ou franchir une frontière non prévue par `ARCHITECTURE.md` sans ADR.

### Conventions

Charger la skill `cadre:conventions-<stack>` (python ou typescript) avant d'écrire du code.
