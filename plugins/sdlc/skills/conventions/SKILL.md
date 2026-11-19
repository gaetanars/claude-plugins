---
name: conventions
description: Conventions du SDLC interactif (parcours et gates, spec v3, branches, commits TDD, check.json, verdict, apprentissages). À consulter dès qu'une brique SDLC doit vérifier un format ou une règle ; pas à charger pour un travail hors SDLC.
---

# Conventions du SDLC

## Parcours et gates
`/sdlc:go <besoin>` trie en **trivial** / **standard** / **feature** (un bug = standard, test de reproduction en première étape). Chaque brique s'invoque aussi seule.
Une **gate humaine** = arrêt jusqu'à ton accord explicite, matérialisé par un statut d'artefact ou un commit : confirmation du parcours, brief relu, spec `accepted`, architecture acceptée, plan commité, revue finale, accord de PR. Aucun hook.
Pas d'issue GitHub, pas de label : la spec acceptée et commitée est l'unité de travail. Merge toujours humain.

## Arborescence (dans chaque projet)
```
docs/features/<id>/        # <id> = NNNN-slug (ex. 0007-export-csv)
  brief.md                 # idéation (feature), facultatif
  spec.md                  # unité de travail (standard, feature)
  plan.md                  # plan d'implémentation et clarifications
docs/architecture/         # ARCHITECTURE.md + native/ (configuration de l'outil de contrôle)
docs/adr/NNNN-slug.md      # décisions d'architecture, numérotées globalement
docs/learnings.md          # apprentissages du projet, relus avant chaque travail
```
Artefacts toujours dans le dépôt du projet, y compris tiers. Gabarits : `sdlc-template brief|spec|plan|adr|architecture|learnings|project-CLAUDE`. Artefacts en français (titres contrôlés par les validateurs).

## Spec (schema_version: 3)
Frontmatter : `schema_version`, `id`, `title`, `track: standard|feature`, `status: draft|accepted`, `depends_on: [ids]`.
Sections : standard = Contexte, Critères d'acceptation, Décisions de cadrage ; feature = + Périmètre, Hors périmètre, Contraintes.
Critères : `- [ ] CA-n: …` observables et testables. Décisions : `- [x] Qn: … → R: … (date)`, aucune question ouverte, aucun TODO.
Validation : `sdlc-validate-spec docs/features/<id>`. `sdlc-gate start <id>` exige `accepted`, commite spec et brief (`docs(<id>): spec`) ; ils sont ensuite figés.

## Branches
`feat/<id>` (standard, feature), `fix/<slug>` (trivial). `sdlc-gate` déduit le contexte de la branche. Push SSH, sans `-u` ; jamais d'écriture de `.git/config`.

## Commits et TDD
Conventional Commits : `type(scope): sujet` à l'impératif, ≤ 72 caractères, footer `Feature: <id>` (standard, feature).
Chaque étape du plan = deux commits : `test(...)` seul (`sdlc-gate tests-red` constate le rouge), puis `feat(...)` sans modifier un fichier du commit `test` précédent.
`fix`, `refactor`, `docs`, `chore` sont permis seuls. Standard/feature : `plan.md` est commité avant le premier commit `test`. Trivial : ni spec ni plan.
Pas de `--no-verify`, pas de réécriture d'historique. État TDD et verdicts : notes git `refs/notes/sdlc-red`, `refs/notes/sdlc-review`.

## Contrat de vérification
`.claude/check.json` = `{"check": "<commande>", "arch": "<commande>"}` (code 0 = vert). `check` obligatoire : tests, lint, typecheck. `arch` : contrôle d'architecture par l'outil natif ; facultatif, **obligatoire dès que `docs/architecture/` est accepté**.
`sdlc-gate verify` les exécute lui-même.

## Architecture
Cadrée avec `/sdlc:architect`, versionnée, jamais modifiée pendant un développement : `docs/architecture/ARCHITECTURE.md`, `docs/architecture/native/`, `docs/adr/`. Validation : `sdlc-validate-architecture --require-accepted docs/architecture`.
Exigée pour le parcours feature seulement. Une décision de la liste « Exige un ADR » non couverte par une ADR acceptée n'est jamais tranchée par un agent : retour à `architect adr`.
Chemins protégés (contrôlés par `verify`) : `docs/architecture/`, `docs/adr/`, `.claude/`, `.github/`, spec et brief figés.

## Apprentissages
`docs/learnings.md` : une ligne par apprentissage, `- AAAA-MM-JJ [<id>] constat → règle à appliquer`. Écrit par `ship` (faits du run et corrections de ta revue finale), `spec` et `architect` (arbitrages) ; lu par toutes les briques.
Une règle devenue fausse est retirée, pas contredite. `/sdlc:retro` remonte les motifs récurrents vers le plugin.

## Verdict de revue
Un relecteur, trois axes : `correctness`, `security`, `simplicity`. Sortie : `approve` ou `changes_requested`, findings (axis, severity blocker|major|minor, file, line, issue, evidence, suggestion) ; schéma `schemas/verdict.schema.json`.
`approve` est requalifié en `changes_requested` s'il reste un blocker ou major. Un finding sans preuve est invalide. Plafond d'itérations : stop, l'humain tranche.

## Principes
KISS : la solution la plus simple et éprouvée. Aucune abstraction, dépendance ou option non demandée par la spec. Ne rien inventer : en cas d'ambiguïté, poser la question.
