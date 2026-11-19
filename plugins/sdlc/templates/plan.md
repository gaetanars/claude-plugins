# Plan : <titre de la feature>

Feature : <id> · Spec : docs/features/<id>/spec.md

## Approche
Résumé de la solution retenue en quelques phrases. Choix locaux (sans alternative structurante) et ADR existantes appliquées.

## Étapes
Chaque étape suit le cycle TDD en deux commits : `test(...)` (tests seuls, rouges), puis `feat(...)` (code, sans toucher aux fichiers du commit de tests).

### Étape 1 : <intitulé>
- Tests à écrire d'abord : <fichiers, cas>
- Changement : <fichiers / fonctions>
- Couvre : CA-1

## Couverture des critères d'acceptation
| CA | Étape(s) | Test(s) |
|----|----------|---------|
| CA-1 | 1 | test_xxx |

## Conformité à l'architecture
Modules touchés (noms de `docs/architecture/ARCHITECTURE.md`), règles de dépendance concernées, ADR existantes appliquées.
Aucune décision de la liste « Exige un ADR » : sinon elle est remontée à l'humain, pas tranchée ici.

## Risques et points de vigilance
Ce qui peut mal tourner, comment le détecter.

## Hors plan
Ce qui est volontairement non traité (cohérent avec « Hors périmètre » de la spec).

## Clarifications
Questions posées à l'humain pendant le run et réponses obtenues (la spec publiée reste inchangée).
