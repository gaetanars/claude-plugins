---
schema_version: 1
status: draft
updated: AAAA-MM-JJ
---

# Architecture : <nom du projet>

## Contexte et objectifs
Ce que fait le système, pour qui, et les qualités visées (fiabilité, performance, sécurité, évolutivité), avec leur priorité.

## Stack
Langage, runtime, frameworks et dépendances structurantes retenus, avec renvoi vers l'ADR qui les justifie.

## Modules
Un module par ligne, nommé comme dans `rules.json` et cité entre accents graves.

- `module-a` : responsabilité unique, ce qu'il expose.
- `module-b` : responsabilité unique, ce qu'il expose.

## Règles de dépendance
Lecture de `rules.json` : un module n'importe que ce que `allowed_dependencies` autorise. Toute autre dépendance est interdite.
Les justifications des choix de frontières renvoient vers les ADR.

## Principes et interdits
- Ce qui est toujours vrai dans ce projet (ex. aucune logique métier dans la couche d'entrée).
- Ce qui est interdit, avec la raison.

## Exige un ADR
Décisions structurantes : l'automate ne les tranche jamais seul, il les remonte.

- Création d'un module ou changement de frontière.
- Nouvelle dépendance runtime majeure.
- Changement de persistance ou d'interface externe.

## Contrôle mécanique
Outil natif : `<outil>`. Configuration : `docs/architecture/native/<fichier>`. Commande : champ `arch` de `.claude/check.json`.
Dépôt existant : la baseline des violations actuelles est figée, aucune nouvelle violation n'est admise.
