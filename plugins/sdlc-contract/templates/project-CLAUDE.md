# <Nom du projet>

<Une phrase : ce que fait le projet.>

## Stack
- Langage / runtime :
- Frameworks / dépendances clés :

## Commandes
Les agents lisent cette section pour savoir comment vérifier leur travail. Elle est obligatoire.

- Installer : `<commande>`
- Tests : `<commande>`
- Lint / format : `<commande>`
- Lancer : `<commande>`

## Conventions du projet
- Structure des dossiers :
- Style de code, nommage :
- Ce qu'il ne faut jamais faire :

## SDLC
Les commandes de vérification sont déclarées dans `.claude/check.json` (`{"check": "<tests + lint + typecheck>", "arch": "<contrôle d'architecture>"}`) :
l'orchestrateur les exécute lui-même après chaque implémentation et refuse la revue tant que l'une est rouge.
L'architecture (`docs/architecture/`, `docs/adr/`) est cadrée par l'humain et jamais modifiée par les agents.
Le merge est humain par défaut (auto-merge en opt-in par dépôt).
Le cadrage vit dans `docs/features/<id>/`, les décisions dans `docs/adr/`.
Règles communes (KISS, TDD, commits) : voir le skill `sdlc-conventions` du plugin sdlc-contract.
