# ADR-0001: Portée du plugin fdm : imprimante Bambu configurable, macOS et Linux

## Statut
Accepté

## Contexte
Les travaux d'origine (`~/3d-design`) sont figés sur une Bambu Lab A1 (buse 0.4, PLA) sous macOS : chemin `/Applications/BambuStudio.app` en dur, script zsh, volume d'impression constant. Le plugin est destiné à être diffusé publiquement.

## Options considérées
1. **A1 et macOS uniquement** : portage direct, minimal ; inutilisable par d'autres, l'élargissement exigerait une révision d'architecture.
2. **Imprimante Bambu configurable, macOS et Linux** : options utilisateur (machine, process, filament ; A1 0.4 PLA par défaut), chemin de Bambu Studio détecté selon l'OS ou surchargé, règles FDM paramétrées par le volume d'impression ; coût modéré.
3. **Abstraction multi-slicers** (Bambu, Orca, PrusaSlicer) : généralité sans utilisateur actuel, contraire à KISS.

## Décision
Option 2 : la diffusion n'a de sens que si tout propriétaire de Bambu peut s'en servir, et l'écart avec l'option 1 se limite à quelques paramètres, sans abstraction.

## Conséquences
- Les constantes d'imprimante (volume, profils) deviennent des options du plugin avec des valeurs par défaut A1.
- Les commandes sont en Python (pas de zsh) pour tourner sous Linux.
- Windows et les autres slicers sont hors périmètre ; les ajouter exige un ADR.
