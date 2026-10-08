---
name: conventions
description: Conventions universelles de tdd-forge (TDD, tests par l'interface publique, nommage AC-n, erreurs, simplicité), indépendantes du langage. À charger par les agents de tdd-forge avant d'écrire, tester ou relire du code ; impose la lecture de .forge/conventions.md.
---

# Conventions

**Lecture obligatoire** : `.forge/conventions.md` du projet (stack, commandes, idiomes, pièges). Il prime sur ce qui suit en cas de conflit, comme les conventions déjà visibles dans le dépôt. Adopte les idiomes du langage et de sa version, lus dans les fichiers de config du projet ; n'introduis pas de syntaxe que la version ciblée ne permet pas.

## TDD

- Rouge d'abord : un test qui échoue pour la bonne raison, puis le code le plus simple qui le fait passer, puis le refactor tests au vert.
- Pas de code sans test qui l'exige. Pas de fonctionnalité au-delà de la spec.

## Tests

- Un comportement par test, structure Arrange-Act-Assert, assertions précises (valeur ou erreur attendue, jamais « truthy »).
- Passe par l'interface publique décrite dans le plan ; ne teste jamais les détails internes.
- **Nommage** : chaque test d'acceptation porte son identifiant `AC-n` dans le **nom du testcase** (visible dans le rapport JUnit), pas seulement dans un commentaire. Les autres tests se nomment d'après le comportement et la condition.
- Ne simule que les frontières (réseau, horloge, aléa, système de fichiers, processus externes). Ne simule jamais ce que le projet possède.
- Déterminisme : aucune dépendance à l'ordre d'exécution, à l'heure réelle ou au réseau.

## Code

- Le plus simple qui marche : pas d'abstraction, de dépendance ni de configuration non demandées.
- Erreurs : explicites et typées par le domaine ; jamais avalées en silence ; le contexte d'origine est conservé quand on relance.
- Frontières (horloge, aléa, I/O, réseau) injectées, jamais atteintes en dur depuis la logique métier.
- Pas d'état global caché. Données immuables par défaut.
- Fonctions courtes à responsabilité unique ; noms explicites ; un commentaire explique le pourquoi, jamais le quoi.
- Aucune suppression d'alerte (linter, typage, couverture) sans motif écrit sur la même ligne.
- Entrées externes validées ; aucun secret dans le code ni les tests.
