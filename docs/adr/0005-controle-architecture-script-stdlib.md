# ADR-0005: Contrôle d'architecture par un script en bibliothèque standard

## Statut
Accepté

## Contexte
Les modules du dépôt ne s'importent presque pas entre eux : les dépendances passent par des chemins (marketplace, tests, références entre plugins) et par des politiques d'imports (bibliothèque standard uniquement, liste blanche de `fdm-tools`). Le dépôt n'a aucune dépendance de développement.

## Options considérées
1. **import-linter** : outil éprouvé pour les contrats entre paquets Python, mais il ne couvre ni les références par chemin ni la politique bibliothèque standard, et il ajoute une dépendance au dépôt.
2. **Script en bibliothèque standard** sous `docs/architecture/native/check_arch.py` : analyse des imports avec `ast`, recherche de références de chemins ; encode exactement les règles d'`ARCHITECTURE.md`, déterministe, sans réseau ni dépendance.

## Décision
Option 2 : c'est la seule qui couvre les quatre règles sans ajouter de dépendance.

## Conséquences
- Le script est protégé (`docs/architecture/native/`) : le modifier passe par `/sdlc:architect revise`.
- La liste blanche de `fdm-tools` y est codée : l'étendre exige un ADR.
- `ci → tests` n'est pas contrôlé par le script : un seul workflow, déjà couvert par `tests/test_workflows.py`.
