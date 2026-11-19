---
name: review
description: Brique SDLC : revue indépendante de la branche (sdlc-gate verify, sous-agent reviewer, verdict, puis revue finale humaine ; remplace /code-review). À charger quand l'implémentation d'un parcours /sdlc:go est terminée, ou sur /sdlc:review explicite.
---

# Review : vérifier, faire relire, trancher

1. **Vérifier** : `sdlc-gate verify`. Rouge : arrête-toi et renvoie vers `/sdlc:build` (ou corrige, en trivial) avec la sortie.
2. **Relire** : lance `sdlc:reviewer` (contexte vierge) avec les chemins de la spec et du plan (sauf trivial : l'intention du changement et les messages de commit) et la commande de diff
   `git diff origin/<branche par défaut>...HEAD -- . ':(exclude)docs/features'`.
   Transmets sa sortie JSON telle quelle à `sdlc-gate review` par heredoc (aucun fichier dans le dépôt) :
   `sdlc-gate review <<'SDLC_VERDICT'` … `SDLC_VERDICT`.
   - code 0 : approuvé → étape 3 ;
   - code 2 : corrections demandées → `/sdlc:build` (ou correction directe en trivial) avec les findings `blocker` et `major`, puis reprends en 1 ;
   - code 3 : plafond d'itérations (`SDLC_MAX_ITER`, 3 par défaut) : **stop**, présente les findings et laisse l'humain trancher ;
   - code 1 : verdict invalide → redemande au reviewer un JSON conforme.
3. **Ta revue finale (gate humaine)** : présente le verdict, les findings restants et un résumé du diff ; demande « OK, ou des corrections ? ».
   - Corrections de sa part : traite-les (via `/sdlc:build` ou directement en trivial), relance depuis 1 ; **note chacune** : elle alimentera `docs/learnings.md` au `ship`.
   - OK explicite : passe à `/sdlc:ship`.
