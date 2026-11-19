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
Les commandes de vérification sont déclarées dans `.claude/check.json` (`{"check": "<tests + lint + typecheck>", "arch": "<contrôle d'architecture, si une architecture est cadrée>"}`) :
`sdlc-gate verify` les exécute lui-même et refuse la revue tant qu'une est rouge.
L'architecture (`docs/architecture/`, `docs/adr/`) est cadrée par l'humain (`/sdlc:architect`) et jamais modifiée pendant un développement. Le merge est humain.
Le cadrage vit dans `docs/features/<id>/`, les apprentissages dans `docs/learnings.md` (à lire avant tout travail).
Point d'entrée : `/sdlc:go <besoin>`. Règles communes (KISS, TDD en deux commits, commits) : skill `sdlc:conventions`.
