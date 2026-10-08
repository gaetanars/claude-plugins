---
name: conventions
description: Invariants du flux tdd-forge (rouge d'abord, tests d'acceptation verrouillés, séparation des rôles, traçabilité AC-n) et lecture obligatoire de .forge/conventions.md, qui définit la méthodologie de test et de code du projet. À charger par les agents de tdd-forge avant d'écrire, tester ou relire du code.
---

# Conventions

**Lecture obligatoire** : `.forge/conventions.md` du projet, à lire et appliquer, ainsi que l'index d'ADR de `ARCHITECTURE.md` : il définit la méthodologie de test et de code (stratégie de test, style, commandes, pièges). À défaut, ou pour ce qu'il ne couvre pas, suis les conventions visibles dans le dépôt.

## Invariants du flux

- Rouge d'abord : un test qui échoue pour la bonne raison, puis le code le plus simple qui le fait passer, puis le refactor tests au vert. Pas de fonctionnalité au-delà de la spec.
- Chaque critère `AC-n` est lié à au moins un test, de façon visible dans les résultats de test (comme le décrit `.forge/conventions.md`), pas seulement dans un commentaire.
- Les tests d'acceptation sont verrouillés après la phase rouge.
- Le rédacteur de tests n'écrit que des tests ; l'implémenteur n'en écrit ni n'en modifie jamais.
- Une ADR acceptée se respecte et ne change que par une nouvelle ADR, via l'architecte.
- Les résultats sont déterministes : un test qui change d'issue sans changement de code est un défaut.
- Aucune suppression d'alerte sans motif écrit sur la même ligne ; aucun secret dans le code ni les tests.
