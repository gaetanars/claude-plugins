---
name: build
description: Brique SDLC : implémente le plan commité en TDD vérifié via le sous-agent implementer (test rouge puis feat, contrôlés par sdlc-gate). À charger quand plan.md est commité sur feat/<id> dans un parcours /sdlc:go, ou sur /sdlc:build explicite.
---

# Build : TDD vérifié

Prérequis : `plan.md` commité (`docs(<id>): plan`) sur `feat/<id>`. Sinon renvoie vers `/sdlc:plan`.
Tu ne crois pas l'implémenteur sur parole : seules les sorties de `sdlc-gate` font foi. Tu ne codes pas toi-même.

1. **Lance `sdlc:implementer`** avec les chemins de la spec, du plan et l'id. Il applique le cycle par étape : commit `test` → `sdlc-gate tests-red` (rouge constaté) → commit `feat` → `sdlc-gate verify`.
2. S'il rend une question bloquante : pose-la à l'humain, consigne Q/R dans « Clarifications » du plan (commit `docs(<id>): plan` : un commit `docs` entre `test` et `feat` est toléré par `sdlc-gate`), relance-le.
3. **Vérifie toi-même** : `sdlc-gate verify`. Rouge : relance l'implémenteur avec la sortie complète comme finding `blocker`.
4. Vert : enchaîne sur `/sdlc:review`. Pas de gate humaine ici : le contrôle est mécanique, ta revue vient après.

Corrections après revue : relance l'implémenteur avec les findings `blocker` et `major` (un finding de comportement = d'abord un test rouge), puis reprends en 3.
