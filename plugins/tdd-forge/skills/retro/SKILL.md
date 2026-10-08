---
name: ameliorer
description: Rétro de tdd-forge. Analyse les livraisons récentes (journaux, revues, consommation, apprentissages [système]) et propose des modifications du plugin lui-même, appliquées par PR que Gaëtan valide. À lancer avec /tdd-forge:ameliorer, toutes les dix tâches environ ou quand une livraison a mal tourné.
disable-model-invocation: true
model: opus
allowed-tools: Read Grep Glob Edit Bash(python3 .forge/bin/forge.py *) Bash(git log *) Bash(gh pr list *) Bash(gh pr view *)
---

# Rétro du système

La boucle capitalise seule ce qu'elle apprend sur le projet (`.forge/learnings.md`). Cette skill traite l'autre niveau : faire évoluer tdd-forge lui-même. Rien ne s'applique sans l'accord explicite de Gaëtan.

## 1. Matière

Sur les tâches depuis la dernière rétro (dernière ligne `[système] rétro` de `.forge/learnings.md`, sinon les dix dernières) :

- `.forge/backlog/*/journal.jsonl` : tours de correction par phase, blocages et leurs motifs, violations annulées ;
- `review-*.json` et `dispositions-*.json` : remarques récurrentes, taux de refus (un taux élevé signale un relecteur bruyant ou un implémenteur qui résiste à tort) ;
- `python3 .forge/bin/forge.py metrics <T>` : consommation par agent ; repère l'étape la plus chère et celle qui dérive ;
- les entrées `[système]` de `.forge/learnings.md` ;
- l'issue des PR (`gh pr list --author @me --state all`) : CI rouges, PR fermées, reverts.

## 2. Diagnostic

Au plus cinq constats, chacun avec sa preuve chiffrée et sa cause probable. Hiérarchie des remèdes, du plus fiable au moins fiable :

1. une porte déterministe (règle de lint, seuil, contrôle dans `forge.py`) ;
2. une règle dans une skill de conventions ;
3. une modification du prompt d'un agent ;
4. un changement de modèle ou d'effort.

Une remarque de revue récurrente qu'un outil pourrait détecter devient une règle d'outil, pas une consigne de plus au relecteur.

## 3. Budget du système

Six agents, cinq skills, un workflow. Ajouter un élément oblige à en retirer un autre ou à justifier pourquoi le budget doit bouger. Un prompt qui s'allonge à chaque rétro est un signal d'alerte : préfère réécrire plus court.

## 4. Proposition

Bloc numéroté : pour chaque changement, le fichier du plugin visé, le changement, l'effet attendu et comment on le mesurera à la prochaine rétro. Gaëtan répond « ok » ou « ok sauf… ».

## 5. Application

Dans le dépôt du plugin (demande son chemin s'il n'est pas connu) : une branche, les changements validés, la version de `plugin.json` incrémentée, une PR. **Jamais de merge automatique** : Gaëtan relit et merge. Rappelle ensuite de relancer `/tdd-forge:installer` dans chaque dépôt si `forge.py` a changé.

Termine en ajoutant à `.forge/learnings.md` la ligne `- AAAA-MM-JJ [système] rétro — <n> changements proposés, <m> retenus`, qui sert de point de départ à la rétro suivante.
