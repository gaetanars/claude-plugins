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
`sdlc-gate verify` les exécute lui-même et refuse la revue tant que l'une est rouge.
L'architecture (`docs/architecture/`, `docs/adr/`) est cadrée par l'humain et jamais modifiée par l'usine. Le merge est humain.
Le cadrage vit dans `docs/features/<id>/`, les apprentissages dans `docs/learnings.md` (à lire avant tout travail).
Règles communes (KISS, TDD en deux commits, commits) : voir le skill `sdlc-conventions` du plugin sdlc-contract.
