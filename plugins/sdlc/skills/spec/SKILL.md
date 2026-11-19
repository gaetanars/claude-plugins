---
name: spec
description: Brique SDLC : écrit et fait accepter la spec d'une unité de travail (standard ou feature), lève les ambiguïtés, status accepted après l'accord humain. À charger quand le parcours choisi dans /sdlc:go arrive à l'étape spec, ou sur /sdlc:spec explicite ; pas pour un changement trivial.
---

# Spec : cadrer une unité de travail

Tu transformes un besoin (ou un brief) en une spec que des agents réaliseront **sans jamais avoir à deviner**.
Tu ne décides rien à la place de l'utilisateur ; tu proposes avec une recommandation, il tranche.
Le résultat est `docs/features/<id>/spec.md` (schema_version 3), commité plus tard par `sdlc-gate start`. Pas d'issue GitHub.

## Parcours
- `track: standard` : un changement borné (dont un bug : le CA 1 est « le cas reproduit ne se produit plus », test de reproduction en première étape du plan). Sections : Contexte, Critères d'acceptation, Décisions de cadrage.
- `track: feature` : les 6 sections (Périmètre, Hors périmètre, Contraintes en plus). **Exige une architecture acceptée** : lance `sdlc-validate-architecture --require-accepted docs/architecture` ; absente, invalide ou `draft` → **arrête-toi** et renvoie vers `/sdlc:architect init`.

## Déroulé
1. **Lis** `docs/features/<id>/brief.md` s'il existe (sinon pars du besoin exposé), `CLAUDE.md`, `docs/learnings.md`, le code concerné ; en feature aussi `docs/architecture/ARCHITECTURE.md` et `docs/adr/`.
   Les apprentissages disent ce qui a déjà été demandé ou corrigé : tranche ces points maintenant.
2. **Découpe** (feature) en unités : résultat observable et testable, PR relisible (≲ 400 lignes de diff), un seul « pourquoi », `depends_on` sans cycle.
   Confronte chaque unité à la liste « Exige un ADR » de `ARCHITECTURE.md` : décision structurante non couverte par une ADR acceptée → **arrête cette unité**, renvoie vers `/sdlc:architect adr <sujet>` (ou `revise`).
   Présente le découpage et fais-le valider. Une spec = une unité ; les suivantes se cadrent après la livraison de la première.
3. **Lève TOUTES les ambiguïtés avant d'écrire** : nominal, erreurs, limites et volumes, données et formats, interfaces, sécurité, performance, compatibilité, architecture, tests attendus.
   Questions par salves de 3 maximum, consignées dans « Décisions de cadrage » (`- [x] Qn: question → R: réponse (date)`). Aucune supposition silencieuse : sans réponse, propose un défaut et fais-le confirmer.
4. **Écris** la spec d'après `sdlc-template spec` (identifiant : `sdlc-next-id <slug>`), en `status: draft`, `track` et `schema_version: 3`. Critères `CA-n` observables et testables.
5. **Valide** : `sdlc-validate-spec docs/features/<id>` ; corrige jusqu'à `OK`.
6. **Gate humaine** : « Tu valides la spec ? ». Après son accord explicite seulement : `status: accepted`, puis relance le validateur. Ne commite pas : `sdlc-gate start <id>` s'en charge.

## Règles
- Jamais `status: accepted` sans accord explicite dans la session.
- Après `sdlc-gate start`, spec et brief sont figés (la vérification refuse toute modification) : un changement de besoin = nouvelle unité.
- Un arbitrage qui vaudra pour la suite reste dans « Décisions de cadrage » : `ship` le reporte dans `docs/learnings.md`. Ne modifie pas `docs/learnings.md` ici (`sdlc-gate start` refuse tout fichier modifié hors spec et brief).
- Tout ce que `plan` ou `build` pourrait demander et qu'on peut trancher maintenant doit l'être maintenant.
- Ne code pas.
