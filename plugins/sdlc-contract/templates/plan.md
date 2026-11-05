# Plan : <titre de la feature>

Feature : <id> · Spec : docs/features/<id>/spec.md

## Approche
Résumé de la solution retenue en quelques phrases. Renvoi vers les ADR concernés.

## Étapes
Chaque étape est petite, vérifiable, et se termine par un commit.

### Étape 1 : <intitulé>
- Test(s) à écrire d'abord : <description>
- Changement : <fichiers / fonctions>
- Couvre : CA-1
- Vérification : <commande>

## Couverture des critères d'acceptation
| CA | Étape(s) | Test(s) |
|----|----------|---------|
| CA-1 | 1 | test_xxx |

## Conformité à l'architecture
Modules touchés (noms de `docs/architecture/rules.json`), règles de dépendance concernées, ADR existantes appliquées.
Aucune décision structurante nouvelle : sinon elle est remontée en ambiguïté, pas tranchée ici.

## Risques et points de vigilance
Ce qui peut mal tourner, comment le détecter.

## Hors plan
Ce qui est volontairement non traité (cohérent avec « Hors périmètre » de la spec).
