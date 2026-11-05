---
name: sdlc-conventions
description: Conventions du SDLC personnel : arborescence docs/features, format des specs, ADR, commits, labels, règles de verdict. À consulter pour tout travail dans ce flux.
---

# Conventions du SDLC

## Arborescence (dans chaque projet)

```
docs/features/<id>/        # <id> = NNNN-slug (ex. 0007-export-csv)
  brief.md                 # idéation (poste)          — immuable après publication
  spec.md                  # unité de travail (poste)  — immuable après publication
  ambiguities.md           # questions levées + réponses (le « pourquoi »)
  plan.md                  # plan d'implémentation (planner)
  reviews/<sha7>-<axe>.json  # verdicts, un par axe et par commit relu
  run.json                 # métriques du run (orchestrateur)
docs/adr/NNNN-slug.md      # décisions d'architecture, numérotées globalement
```

Gabarits : `sdlc-template brief|spec|ambiguities|plan|adr|project-CLAUDE`.

## Spec (schema_version: 1)
Frontmatter : `schema_version`, `id`, `title`, `status: ready`, `depends_on: [ids]`.
Sections obligatoires : Contexte, Périmètre, Hors périmètre, Critères d'acceptation, Contraintes.
Critères : `- [ ] CA-n: …` observables et testables. Aucune question ouverte, aucun TODO.
Validation : `sdlc-validate-spec docs/features/<id>`.

## Règle d'immuabilité
Après publication, `brief.md`, `spec.md` et `ambiguities.md` ne sont modifiés que par l'orchestrateur
(ajout d'une clarification dans `ambiguities.md`). Un changement de besoin = nouvelle unité de travail.

## ADR
Une ADR par arbitrage réel (au moins deux options crédibles). Sections : Statut, Contexte,
Options considérées, Décision, Conséquences. Pas d'ADR pour un choix sans alternative.

## Commits
Conventional Commits : `type(scope): sujet` à l'impératif, ≤ 72 caractères.
Types : feat, fix, refactor, test, docs, chore, ci. Footer obligatoire : `Feature: <id>`,
et `Plan-Step: <n>` pour un commit d'implémentation. Un commit = une étape logique du plan.
Pas de `--no-verify`, pas de réécriture d'historique.

## Labels d'issue
`ready` (à traiter) → `in-progress` (verrou) → `in-review` (PR ouverte, en attente de merge ; humain par défaut, auto-merge seulement si le dépôt l'a activé).
`needs-clarification` : l'agent a une question précise (commentaire de l'issue).
`needs-human` : échec ou revues non approuvées après 3 itérations.

## Contrat de vérification
`.claude/check.json` = `{"check": "<commande>"}` (code de sortie 0 = vert). L'implementer la lance avant chaque commit ; l'orchestrateur la relance après lui et ne lance les revues que si elle est verte.

## Verdicts de revue
Trois axes : `correctness`, `security`, `simplicity`. Sortie : verdict `approve` ou `changes_requested`,
liste de findings (severity blocker|major|minor, fichier, ligne, problème, preuve, suggestion).
`approve` est interdit s'il reste un finding blocker ou major. Un finding sans preuve est invalide.
Fichier stocké : verdict + `axis`, `commit`, `iteration`, `reviewed_at`.

## Principes
KISS : la solution la plus simple et éprouvée. Aucune abstraction, dépendance ou option non demandée par la spec.
TDD : test d'abord, constater l'échec, implémenter, constater le succès.
Ne rien inventer : en cas d'ambiguïté, s'arrêter et poser la question, ne pas trancher.
