---
name: retro
description: Rétro de tdd-forge. Analyse les livraisons récentes (journaux, revues, consommation, apprentissages [système]) et propose des modifications du plugin, des conventions du projet et des portes, appliquées par PR que Gaëtan valide. À lancer avec /tdd-forge:retro, toutes les dix tâches environ ou quand une livraison a mal tourné.
disable-model-invocation: true
model: opus
allowed-tools: Read Grep Glob Edit AskUserQuestion Bash(python3 .forge/bin/forge.py *) Bash(git log *) Bash(gh pr list *) Bash(gh pr view *)
---

# Rétro du système

La boucle capitalise seule ce qu'elle apprend sur le projet (`.forge/learnings.md`). Cette skill traite l'autre niveau : faire évoluer le système (le plugin tdd-forge, `.forge/conventions.md`, les portes). Rien ne s'applique sans l'accord explicite de Gaëtan.

## 1. Matière

Sur les tâches depuis la dernière rétro (dernière ligne `[système] rétro` de `.forge/learnings.md`, sinon les dix dernières) :

- `python3 .forge/bin/forge.py backlog` pour la liste ; `.forge/backlog/*/journal.jsonl` : tours de correction par phase, blocages et leurs motifs, violations annulées, critères `AC-n` manquants ;
- `review-*.json` et `dispositions-*.json` : remarques récurrentes, taux de refus (un taux élevé signale un relecteur bruyant ou un implémenteur qui résiste à tort) ;
- `python3 .forge/bin/forge.py metrics <T>` : consommation par agent ; repère l'étape la plus chère et celle qui dérive ;
- les entrées `[système]` de `.forge/learnings.md` ;
- l'issue des PR (`gh pr list --author @me --state all`) : CI rouges, PR fermées, reverts.

## 2. Diagnostic

Au plus cinq constats, chacun avec sa preuve chiffrée et sa cause probable. Hiérarchie des remèdes, du plus fiable au moins fiable :

1. une porte déterministe (règle de lint, seuil, contrôle dans `forge.py`, entrée de `gates`) ;
2. une règle dans `.forge/conventions.md` (propre au projet) ou dans la skill `conventions` (universelle) ;
3. une modification du prompt d'un agent ;
4. un changement de modèle ou d'effort.

Une remarque de revue récurrente qu'un outil pourrait détecter devient une règle d'outil, pas une consigne de plus au relecteur.

## 3. Budget du système

Six agents, quatre skills (`init`, `po`, `retro`, `conventions`), un workflow. Ajouter un élément oblige à en retirer un autre ou à justifier pourquoi le budget doit bouger. Un prompt qui s'allonge à chaque rétro est un signal d'alerte : préfère réécrire plus court.

## 4. Proposition

Bloc numéroté : pour chaque changement, le fichier visé, le changement, l'effet attendu et comment on le mesurera à la prochaine rétro. Demande l'accord avec `AskUserQuestion` (« ok », « ok sauf… ») ; texte libre si l'outil n'est pas disponible.

## 5. Application

- **Projet** (`.forge/conventions.md`, `.forge/config.json`, `.forge/learnings.md`) : édite les fichiers dans le checkout principal, puis `python3 .forge/bin/forge.py publish "chore: <résumé>" <fichiers>`. Pour `.forge/config.json` (portes), ajoute `--manual` : la PR reste ouverte, Gaëtan la merge lui-même ; lance ensuite `forge.py doctor`.
- **Plugin** (dépôt du plugin, demande son chemin s'il n'est pas connu) : une branche, les changements validés, la version de `plugin.json` incrémentée, une PR. **Jamais de merge automatique.** Rappelle de relancer `/tdd-forge:init` dans chaque dépôt si `forge.py` a changé.

Termine en ajoutant à `.forge/learnings.md` la ligne `- AAAA-MM-JJ [système] rétro — <n> changements proposés, <m> retenus`, qui sert de point de départ à la rétro suivante (publiée avec le reste).
