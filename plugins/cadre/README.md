# cadre

Cadrage par le contexte et garde-fous légers pour Claude Code (Python, TypeScript, GitHub). Pas d'orchestrateur : une seule session travaille avec le bon contexte, deux hooks tiennent la ligne.

## Installation

```
/plugin marketplace add gaetanars/claude-plugins
/plugin install cadre@gaetanars
```

## Parcours

1. `/cadre:installer` : section `CLAUDE.md`, `.claude/check.json`, CI `check`, `tests/acceptance/`.
2. `/cadre:produit` : écrit `PRODUCT.md`.
3. `/cadre:architecture` : écrit `ARCHITECTURE.md` (ou `adr <sujet>` pour `docs/adr/NNNN-*.md`).
4. `/cadre:spec <besoin>` : challenge, découpage, critères `AC-n` validés par toi, écrits dans `docs/specs/S00x.md`.
5. « implémente `docs/specs/S00x.md` en Plan mode » (obligatoire si frontière, dépendance, schéma ou API publique touchés). Test d'acceptation par AC commité d'abord, micro-cycles TDD, `check` vert, `/code-review`, PR. Tu merges.

## Contrat `.claude/check.json`

```json
{"check": "<commande unique>", "acceptance_dir": "tests/acceptance"}
```

## Hooks

- **PreToolUse** (`acceptance_lock.py`) : éditer un fichier de `acceptance_dir` déjà suivi par git déclenche une demande d'accord (`ask`). Un nouveau fichier reste libre.
- **Stop** (`check_gate.py`) : si l'arbre est modifié depuis le dernier vert, lance `check`. Rouge : exit 2, Claude continue (60 dernières lignes en retour). Après 3 échecs, le hook laisse passer avec un message. L'état est dans `.claude/check-state.json` (ignoré par git).

## Limites

- Si `check` écrit des fichiers non ignorés par git (sorties de couverture, logs), l'empreinte change à chaque fois et il se relance à chaque arrêt : les ignorer.
- Stop ne couvre que l'agent principal : pas les subagents (`SubagentStop`) ni les coéquipiers d'une Agent Team (`TeammateIdle`). Le verrou PreToolUse, lui, s'applique partout.
- Claude Code passe outre après 8 continuations consécutives provoquées par des hooks Stop.
- `MultiEdit` dans le matcher : non confirmé par la doc ; inoffensif si l'outil n'existe pas.
- Exécution de bout en bout non vérifiée en conditions réelles (voir la vérification manuelle dans le plan de migration).
