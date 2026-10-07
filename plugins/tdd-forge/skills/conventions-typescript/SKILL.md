---
name: conventions-typescript
description: Conventions TypeScript de tdd-forge pour écrire, tester et relire du code TypeScript à l'état de l'art. À charger par les agents de tdd-forge sur une stack TypeScript.
---

# Conventions TypeScript

Les conventions déjà présentes dans le dépôt priment. Lis `package.json` et `tsconfig.json` pour les versions et les options, et respecte-les.

## Code

- `strict` actif, ainsi que `noUncheckedIndexedAccess` et `exactOptionalPropertyTypes` si le projet les active. ESM, imports Node avec le préfixe `node:`.
- Jamais `any` : `unknown` puis rétrécissement. Pas d'assertion de type (`as`) pour faire taire le compilateur.
- Unions discriminées pour les états ; `switch` exhaustif avec un cas `never` ; `readonly` et `as const` par défaut.
- Valider les données à la frontière (entrées HTTP, fichiers, variables d'environnement) avec la bibliothèque déjà utilisée par le projet (Zod, Valibot…) ; au cœur du code, les types suffisent.
- Erreurs : classes d'erreur dédiées, ou un type `Result` si le projet l'utilise déjà ; ne pas mélanger les deux styles.
- Asynchrone : aucune promesse flottante ; `Promise.all` pour le parallélisme indépendant ; `AbortSignal` pour l'annulation.
- Exports nommés ; modules courts, une responsabilité ; horloge, aléa et réseau injectables.

## Tests (Vitest)

- `describe` par unité, `it` par comportement, formulé comme une phrase ; Arrange-Act-Assert.
- Tester par l'interface publique ; ne simuler que les frontières. `vi.useFakeTimers()` pour le temps.
- Assertions précises (`toEqual`, `toThrow(ErreurMetier)`) ; instantanés seulement pour des sorties stables et lisibles.
- Déterminisme : pas d'ordre implicite entre tests, pas de réseau réel.
