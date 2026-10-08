# Conventions du projet

Lues par tous les agents de tdd-forge avant d'agir, en complément de la skill `tdd-forge:conventions`.
Versionné ; enrichi par la rétro (`/tdd-forge:retro`). Court : une règle, un fait vérifiable par ligne.
C'est ici que vit la méthodologie du projet : le plugin ne porte que le flux. Les valeurs ci-dessous sont des propositions à adapter et valider à l'init.

## Stack

- Langage et version :
- Gestionnaire de dépendances :
- Structure (sources, tests, acceptation) :

## Commandes

- Tests :
- Portes (format, lint, typage, sécurité…) :
- Couverture (seuil décidé avec le PO, ou aucun) :

## Résultats de test et liens AC

- Lanceur et format natif des résultats :
- Adaptateur (`.forge/adapters/`) ou commande qui produit `results_path` :
- Comment ce projet lie un test à un critère `AC-n` (dans le nom du cas, par tag, ou par `acs` dans l'adaptateur), avec un exemple :
- Où vivent les tests d'acceptation (`acceptance_globs`) :

## Stratégie de test

- Types de tests (acceptation, unitaires, intégration…) et quand les utiliser : *proposition : acceptation par critère, plus des tests unitaires pour la logique non triviale.*
- Granularité : *proposition : un comportement par test, structure Arrange-Act-Assert, assertions précises.*
- Doublures : *proposition : ne simuler que les frontières (réseau, horloge, aléa, système de fichiers, processus externes).*
- Déterminisme : *proposition : aucune dépendance à l'ordre d'exécution, à l'heure réelle ou au réseau.*
- Couverture :

## Code

- Style et idiomes : *proposition : le plus simple qui marche, fonctions courtes, noms explicites, commentaire pour le pourquoi.*
- Erreurs : *proposition : explicites, typées par le domaine, jamais avalées.*
- Frontières : *proposition : horloge, aléa, I/O et réseau injectés.*
- Suppressions d'alertes : *proposition : aucune sans motif écrit sur la même ligne.*

## Pièges connus

- 
