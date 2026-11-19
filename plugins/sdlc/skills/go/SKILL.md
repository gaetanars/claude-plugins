---
name: go
description: Point d'entrée du SDLC interactif : trie un besoin (trivial, standard, feature), enchaîne les briques et s'arrête à chaque gate humaine. Remplace plan mode, « apply » et /code-review au quotidien. À invoquer via /sdlc:go <besoin>.
disable-model-invocation: true
---

# Go : de l'idée à la PR, avec toi à chaque gate

Tu orchestres. Tu ne transmets que des **chemins** aux briques et tu ne lis que les sorties JSON de `sdlc-gate` : chaque brique relit ses intrants sur disque.
Tu ne contournes jamais une gate : une gate = arrêt jusqu'à l'accord explicite de l'humain, matérialisé par un statut d'artefact ou un commit.

## 1. Triage
Lis `CLAUDE.md` et `docs/learnings.md`, puis explore juste assez pour trier le besoin `$ARGUMENTS` :
- **trivial** : changement local et évident (typo, config, rename, petit correctif sans ambiguïté) ; ni spec ni plan.
- **standard** : changement borné qui mérite des critères d'acceptation et un plan ; **tout bug** (test de reproduction en première étape).
- **feature** : nouveau comportement, plusieurs unités, ou décision structurante ; exige une architecture acceptée.
Propose le parcours avec une phrase de justification. **Gate : tu attends sa confirmation du parcours.** Besoin vide : demande-le.

## 2. Parcours
- **trivial** : `sdlc-gate start --trivial <slug>` (branche `fix/<slug>`) → modifie dans la session (commits `fix|chore|docs|refactor`, ou `test` rouge puis `feat` si tu ajoutes du comportement) → `/sdlc:review` → `/sdlc:ship`.
- **standard** : `/sdlc:spec` (track standard) → `sdlc-gate start <id>` → `/sdlc:plan` → `/sdlc:build` → `/sdlc:review` → `/sdlc:ship`.
- **feature** : `/sdlc:challenge` → (`/sdlc:architect adr <sujet>` si une entrée « Exige un ADR » est concernée) → `/sdlc:spec` (track feature, découpage en unités) → idem standard.
  Sans architecture acceptée : arrête-toi et propose `/sdlc:architect init`.
Charge chaque brique par son skill (`Skill`), une à la fois, au moment où le parcours y arrive (`go` et `retro` sont les seuls skills réservés à l’invocation explicite). `sdlc-gate start` refuse si la spec n'est pas `accepted` ; son code de sortie ≠ 0 arrête la chaîne (affiche sa sortie).

## 3. Fin d'unité
Après `ship` (PR ouverte ou refusée), résume en 3 lignes (parcours, itérations de revue, apprentissages ajoutés) et propose `/clear` avant la suite (isolation du contexte).
Feature à plusieurs unités : la suivante repart de `spec`.

## Règles
- Pas de push ni de PR hors `/sdlc:ship`, après l'accord explicite. Merge toujours humain.
- Ne code pas toi-même hors parcours trivial : plan, build et review tournent en sous-agents à contexte vierge.
- Tout échec technique non résolu : arrête-toi et rends compte, ne force rien.
