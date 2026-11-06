---
name: deliver
description: Usine SDLC : prend la prochaine issue ready du dépôt, planifie, implémente en TDD vérifié, fait relire puis ouvre la PR (merge humain). Lancé par une automatisation Orca via /sdlc-factory:deliver.
disable-model-invocation: true
model: opus
allowed-tools: Read Grep Glob Write Edit Bash Agent
---

# Deliver : de l'issue `ready` à la PR

Tu orchestres. Les sous-agents `sdlc-factory:planner`, `sdlc-factory:implementer` et `sdlc-factory:reviewer` font le travail ;
`sdlc-gate` fait les contrôles et la livraison. **Tu ne codes pas toi-même, tu ne pousses pas, tu n'appelles pas `gh`.**
Tu ne crois aucun sous-agent sur parole : seules les sorties de `sdlc-gate` font foi.

## Déroulé
1. **Démarrer** : `sdlc-gate start`. Code ≠ 0 : affiche sa sortie et **arrête-toi** (rien à traiter, ou issue déjà escaladée).
   Le JSON donne l'issue, la feature, les chemins de la spec, du brief et du plan, `resumed`.
2. **Contexte** : lis la spec, le brief s'il existe, `CLAUDE.md`, `docs/learnings.md`, `docs/architecture/ARCHITECTURE.md`.
3. **Plan** (si `plan.md` n'existe pas déjà sur la branche) : lance `planner` avec les chemins. Puis :
   - question `[structurante]` → `sdlc-gate escalate "<décision> : à cadrer avec /sdlc-framing:architect adr"` et arrête-toi ;
   - question `[bloquante]` → pose-la à l'humain **dans cette session**, attends sa réponse, consigne Q/R dans la section « Clarifications » du plan,
     relance `planner` si la réponse change le plan ;
   - écris `docs/features/<id>/plan.md`, commit `docs(<id>): plan` (footer `Feature: <id>`).
4. **Implémenter** : lance `implementer` avec la spec, le plan et l'id. S'il rend une question bloquante : même traitement qu'en 3.
5. **Vérifier toi-même** : `sdlc-gate verify`. Rouge : relance `implementer` avec la sortie complète de `verify` comme finding `blocker`.
6. **Relire** : lance `reviewer` (contexte vierge) avec l'id, la spec, le plan et la commande de diff
   `git diff origin/<branche par défaut>...HEAD -- . ':(exclude)docs/features'`.
   Transmets sa sortie JSON telle quelle sur l'entrée standard, par heredoc (aucun fichier dans le dépôt) :
   `sdlc-gate review <<'SDLC_VERDICT'` … `SDLC_VERDICT`.
   - code 0 : approuvé → étape 7 ;
   - code 2 : relance `implementer` avec les findings `blocker` et `major`, puis reprends en 5 ;
   - code 3 : plafond d'itérations atteint, l'issue est en `needs-human` : arrête-toi ;
   - code 1 : verdict invalide → redemande au `reviewer` un JSON conforme.
7. **Apprentissages** : si le run a appris quelque chose de réutilisable (finding corrigé qui se reproduira, clarification qui aurait dû être cadrée,
   gate rouge récurrent), ajoute une ligne par fait à `docs/learnings.md` (`- AAAA-MM-JJ [<id>] constat → règle à appliquer`),
   commit `docs(<id>): apprentissages`. Rien de réutilisable : n'ajoute rien.
8. **Livrer** : `sdlc-gate deliver` (push de `feat/<id>`, PR, issue `in-review`). Échec : corrige la cause si elle est dans ton périmètre, sinon `sdlc-gate escalate`.

## Règles
- Ne modifie jamais `docs/architecture/`, `docs/adr/`, `.claude/`, `.github/`, ni la spec ou le brief : `sdlc-gate` refuse la livraison.
- Une décision de la liste « Exige un ADR » n'est jamais tranchée ici : `sdlc-gate escalate`.
- Tout échec technique que tu ne sais pas résoudre : `sdlc-gate escalate "<cause précise>"`, puis arrête-toi.
- Termine par un compte rendu court : issue, résultat (PR, needs-human, question en attente), itérations.
