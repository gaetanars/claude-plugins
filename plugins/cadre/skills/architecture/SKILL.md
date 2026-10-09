---
name: architecture
description: Écrit ARCHITECTURE.md (modules, frontières, dépendances, choix structurants) par entretien après analyse de l'existant, ou un ADR dans docs/adr/. À lancer avec /cadre:architecture, ou /cadre:architecture adr <sujet>.
disable-model-invocation: true
model: opus
allowed-tools: Read Grep Glob Write Edit Agent
---

# Architecture

Français, court, une seule question à la fois. Rien n'est écrit sans l'accord de Gaëtan.

## Mode initial (ARCHITECTURE.md absent)

1. Lis `PRODUCT.md`. Délègue l'analyse de l'existant (modules, flux, dépendances) au sous-agent Explore pour garder ce contexte léger.
2. Présente ce que tu as observé, puis mène l'entretien sur ce qui n'est pas évident dans le code : frontières voulues, dépendances admises ou interdites, choix structurants.
3. Propose `ARCHITECTURE.md` d'une page au plus, sur le modèle `templates/ARCHITECTURE.md`, avec la section « Exige un ADR ». Écris-le après son « ok ».

## Mode ADR (`adr <sujet>`, ou décision qui l'exige)

Écris `docs/adr/NNNN-<titre-kebab>.md` (numéro à la suite des existants) sur le modèle `templates/adr.md` : Contexte / Décision / Conséquences / Statut. Si la décision change `ARCHITECTURE.md`, propose l'amendement correspondant.
