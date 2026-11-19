---
schema_version: 3
id: NNNN-slug
title: Titre court
track: standard
status: draft
depends_on: []
---

# Titre court

<!-- track: standard = Contexte, Critères d'acceptation, Décisions de cadrage.
     track: feature = ces trois sections + Périmètre, Hors périmètre, Contraintes (voir ci-dessous).
     status: draft pendant le cadrage ; accepted seulement après l'accord explicite de l'humain. -->

## Contexte
Pourquoi cette unité de travail existe (renvoi vers brief.md s'il existe). Valeur attendue en 2-3 phrases.

## Périmètre
(feature seulement)
- Comportement ou composant inclus.

## Hors périmètre
(feature seulement)
- Ce qui est explicitement exclu (même si voisin).

## Critères d'acceptation
- [ ] CA-1: Comportement observable et testable, formulé sans ambiguïté.

## Contraintes
(feature seulement) Stack, interfaces à respecter, performance, sécurité, compatibilité, zones du code concernées.

## Décisions de cadrage
Chaque question levée pendant le cadrage, avec sa réponse. Aucune question ouverte (`- [ ]`) n'est admise une fois la spec acceptée.

- [x] Q1: Question posée pendant le cadrage → R: Réponse retenue (AAAA-MM-JJ)
