---
schema_version: 2
status: draft
updated: AAAA-MM-JJ
---

# Architecture : <nom du projet>

## Contexte et objectifs
Ce que fait le système, pour qui, et les qualités visées (fiabilité, performance, sécurité, évolutivité), avec leur priorité.

## Stack
Langage, runtime, frameworks et dépendances structurantes retenus, avec renvoi vers l'ADR qui les justifie.

## Modules
Un module par ligne, cité entre accents graves, avec ses chemins.

- `module-a` (`src/module_a/`) : responsabilité unique, ce qu'il expose.
- `module-b` (`src/module_b/`) : responsabilité unique, ce qu'il expose.

## Règles de dépendance
Pour chaque module, les modules qu'il peut importer (ex. `module-b` → `module-a`). Toute autre dépendance est interdite.
L'outil natif applique exactement ces règles ; les justifications des frontières renvoient vers les ADR.

## Principes et interdits
- Ce qui est toujours vrai dans ce projet (ex. aucune logique métier dans la couche d'entrée).
- Ce qui est interdit, avec la raison.

## Exige un ADR
Décisions structurantes : l'automate ne les tranche jamais seul, il les remonte.

- Création d'un module ou changement de frontière.
- Nouvelle dépendance runtime majeure.
- Changement de persistance ou d'interface externe.

## Contrôle mécanique
Outil natif : `<outil>`. Configuration : `docs/architecture/native/<fichier>` (seul emplacement admis : il est protégé contre les agents).
Commande : champ `arch` de `.claude/check.json`.
Dépôt existant : la baseline des violations actuelles est figée, aucune nouvelle violation n'est admise.
