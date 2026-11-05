---
name: sdlc-conventions
description: Conventions du SDLC personnel : arborescence docs/features, format des specs, apprentissages, ADR, commits TDD, labels, règles de verdict. À consulter pour tout travail dans ce flux.
---

# Conventions du SDLC

## Arborescence (dans chaque projet)

```
docs/features/<id>/        # <id> = NNNN-slug (ex. 0007-export-csv)
  brief.md                 # idéation (poste), facultatif — immuable après publication
  spec.md                  # unité de travail (poste)     — immuable après publication
  plan.md                  # plan d'implémentation et clarifications du run (usine)
docs/architecture/         # ARCHITECTURE.md + native/ (configuration de l'outil de contrôle)
docs/adr/NNNN-slug.md      # décisions d'architecture, numérotées globalement, écrites par l'humain
docs/learnings.md          # apprentissages du projet, relus avant chaque travail
```

Gabarits : `sdlc-template brief|spec|plan|adr|architecture|learnings|project-CLAUDE`.
Les artefacts sont rédigés en français (titres de sections contrôlés par les validateurs).

## Spec (schema_version: 2)
Frontmatter : `schema_version`, `id`, `title`, `status: ready`, `depends_on: [ids]`.
Sections obligatoires : Contexte, Périmètre, Hors périmètre, Critères d'acceptation, Contraintes, Décisions de cadrage.
Critères : `- [ ] CA-n: …` observables et testables. Décisions : `- [x] Qn: … → R: … (date)`, aucune question ouverte, aucun TODO.
Brief facultatif : pour un petit changement, le `po` part directement de l'idée.
Validation : `sdlc-validate-spec docs/features/<id>`.

## Immuabilité
Après publication, `brief.md` et `spec.md` ne changent plus (contrôlé à la livraison). Un changement de besoin = nouvelle unité.
Une question posée pendant le run et sa réponse vont dans la section « Clarifications » de `plan.md`.

## Apprentissages
`docs/learnings.md` : une ligne par apprentissage, `- AAAA-MM-JJ [<id>] constat → règle à appliquer`.
Écrit par l'usine à la livraison (finding corrigé, clarification, gate rouge) et par le cadrage quand un arbitrage vaut pour la suite.
Lu par `challenger`, `po`, `architect`, planner, implementer et reviewer. Une règle devenue fausse est retirée, pas contredite.

## ADR
Une ADR par arbitrage réel (au moins deux options crédibles), écrite par l'humain via `/sdlc-framing:architect`.
Sections : Statut, Contexte, Options considérées, Décision, Conséquences. Statut `Accepté`, `Proposé`, `Déprécié` ou `Remplacé par NNNN` (jamais de réécriture).

## Commits et TDD
Conventional Commits : `type(scope): sujet` à l'impératif, ≤ 72 caractères, footer `Feature: <id>`.
Chaque étape du plan = deux commits :
1. `test(...)` : uniquement les tests de l'étape ; `sdlc-gate tests-red` constate qu'ils échouent.
2. `feat(...)` : le code qui les fait passer, sans modifier aucun fichier du commit `test` qui le précède.
`fix`, `refactor`, `docs`, `chore` sont permis seuls (corrections de revue). Pas de `--no-verify`, pas de réécriture d'historique.

## Labels d'issue
`ready` (à traiter) → `in-progress` (une seule à la fois par dépôt) → `in-review` (PR ouverte, merge humain).
`needs-human` : échec, décision structurante à cadrer, ou revues non approuvées après 3 itérations (commentaire de l'issue).
Les questions de l'agent se posent dans sa session Orca ; l'issue reste `in-progress` pendant l'attente.

## Contrat de vérification
`.claude/check.json` = `{"check": "<commande>", "arch": "<commande>"}` (code de sortie 0 = vert). `check` : tests, lint, typecheck. `arch` : contrôle des règles d'architecture par l'outil natif du langage.
`sdlc-gate verify` les exécute lui-même ; la revue n'a lieu que si les deux sont verts.

## Architecture
Cadrée avec `/sdlc-framing:architect`, versionnée dans le dépôt, jamais modifiée par l'usine :
- `docs/architecture/ARCHITECTURE.md` : objectifs, stack, modules, règles de dépendance, principes, liste « Exige un ADR », contrôle mécanique.
- `docs/architecture/native/` : configuration (et baseline) de l'outil natif, seul emplacement admis.
Validation : `sdlc-validate-architecture --require-accepted docs/architecture`.
Une décision de la liste « Exige un ADR » non couverte par une ADR acceptée n'est jamais tranchée par un agent : `needs-human`.
Chemins protégés à la livraison : `docs/architecture/`, `docs/adr/`, `.claude/`, `.github/`, `brief.md` et `spec.md` de la feature.

## Verdict de revue
Un relecteur, trois axes : `correctness`, `security`, `simplicity`. Sortie : `approve` ou `changes_requested`,
findings (axis, severity blocker|major|minor, file, line, issue, evidence, suggestion) ; schéma `schemas/verdict.schema.json`.
`approve` est requalifié en `changes_requested` s'il reste un finding blocker ou major. Un finding sans preuve est invalide.

## Principes
KISS : la solution la plus simple et éprouvée. Aucune abstraction, dépendance ou option non demandée par la spec.
Ne rien inventer : en cas d'ambiguïté, poser la question, ne pas trancher.
