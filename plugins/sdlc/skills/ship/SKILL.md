---
name: ship
description: Brique SDLC : capitalise les apprentissages dans docs/learnings.md puis, sur accord explicite, pousse en SSH et ouvre la PR (merge humain). À charger quand la revue finale est approuvée dans un parcours /sdlc:go, ou sur /sdlc:ship explicite.
---

# Ship : apprendre, puis livrer sur accord

Prérequis : verdict `approve` enregistré (`/sdlc:review`) et ta revue finale faite. Tu ne modifies pas le code ici.

1. **Apprentissages** : si le run a appris quelque chose de réutilisable (finding corrigé qui se reproduira, correction demandée à la revue finale, clarification qui aurait dû être cadrée, gate rouge récurrent, arbitrage des « Décisions de cadrage » de la spec valable pour la suite),
   ajoute une ligne par fait à `docs/learnings.md` (`- AAAA-MM-JJ [<id ou slug>] constat → règle à appliquer`) ; retire une ligne devenue fausse. Rien de réutilisable : n'ajoute rien.
   Commit `docs(<id ou slug>): apprentissages`. Seuls `learnings.md` et `plan.md` peuvent changer après le verdict.
2. **Gate humaine** : récapitule (branche, commits, verdict, apprentissages) et demande « J'ouvre la PR ? ». **Sans accord explicite : arrête-toi** (la branche reste locale, rien n'est poussé).
3. Accord obtenu : `sdlc-gate deliver` (vérifie le verdict et `verify`, `git push` SSH de la branche, `gh pr create`). Pour un fork : `gh repo set-default` une fois au préalable.
   Échec : affiche la cause, ne contourne rien.
4. Donne l'URL de la PR. **Le merge est toujours humain.**
