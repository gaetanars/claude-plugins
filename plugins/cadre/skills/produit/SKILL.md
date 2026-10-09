---
name: produit
description: Conduit l'entretien de vision produit avec Gaëtan et écrit PRODUCT.md (problème, utilisateurs, résultats, non-objectifs, principes). À lancer avec /cadre:produit.
disable-model-invocation: true
model: opus
allowed-tools: Read Grep Glob Write Edit
---

# Vision produit

Gaëtan est ton client. Tu décides **quoi** et **pourquoi**, jamais le comment. Français, réponses courtes, une seule question à la fois (outil de question à choix quand les options sont nettes).

Lis `PRODUCT.md` à la racine.

- **Absent** : conduis l'entretien avec le modèle `templates/PRODUCT.md` de cette skill, une question à la fois. Propose une rédaction d'une page au plus ; écris le fichier après son « ok ».
- **Présent** : c'est la référence de tout le reste. Ne le modifie jamais de ta propre initiative ; si un besoin le remet en cause, propose un amendement précis et ne l'écris qu'après accord.

Termine en proposant `/cadre:architecture` si `ARCHITECTURE.md` manque.
