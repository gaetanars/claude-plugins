---
name: retro
description: Rétrospective manuelle du SDLC : lit les apprentissages (docs/learnings.md) de dépôts projets et propose les plus petites améliorations des plugins de la marketplace, preuves à l'appui. À lancer dans le dépôt marketplace via /sdlc-framing:retro <chemin-projet>...
disable-model-invocation: true
model: opus
allowed-tools: Read Grep Glob Edit Write Bash
---

# Rétro : améliorer les outils universels à partir des faits des projets

Tu travailles dans le dépôt marketplace. Les arguments sont des chemins de dépôts projets locaux.
Tu ne modifies rien sans l'accord de l'utilisateur.

## Entrées
Pour chaque projet : `docs/learnings.md`, et au besoin `docs/features/*/plan.md` (clarifications du run) et l'historique git
(`git -C <projet> log --oneline`). Les verdicts de revue et métriques sont dans les PR (`gh pr view` si l'utilisateur le demande).

## Méthode
1. Ne garde que ce qui relève de l'outil universel : un apprentissage propre à un projet reste dans son `docs/learnings.md`.
2. Cherche les **motifs récurrents** (au moins 2 occurrences, idéalement dans 2 projets) : même question posée à l'usine,
   même finding, même gate rouge, même correction de cadrage.
3. Pour chaque motif, trace la cause dans un fichier précis (skill, agent, gabarit, conventions) et propose **la plus petite modification**
   qui la traite. Préfère retirer ou reformuler une règle inutile plutôt qu'en ajouter.
4. Présente un tableau « motif → preuves (projet, feature, ligne d'apprentissage) → modification » ; l'utilisateur tranche ligne par ligne.
5. Après accord : applique, incrémente le **patch** de `version` dans `plugins/<plugin>/.claude-plugin/plugin.json` de chaque plugin modifié,
   lance `python3 -m unittest discover -s tests -t . -v`. Ne commite et ne pousse que sur demande.

## Interdits
- Pas de règle sans preuve, pas de modification cosmétique. Si rien ne mérite changement, dis-le.
- `plugins/sdlc-factory/bin/sdlc-gate` et `plugins/sdlc-factory/deploy/` relèvent d'une revue humaine dédiée : signale le besoin, ne les modifie pas ici.
- N'affaiblis jamais un contrôle, le plafond d'itérations ni l'exigence de preuve des findings.
