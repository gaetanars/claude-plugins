# ADR-0004: Pièces dans le projet utilisateur, outils dans le plugin, lanceur fdm-run

## Statut
Accepté

## Contexte
Les pièces d'origine faisaient `sys.path.insert` puis `from tools.check import check`, ce qui supposait les outils rangés à côté des pièces. Dans un plugin, les outils vivent sous `${CLAUDE_PLUGIN_ROOT}` et les pièces appartiennent à l'utilisateur.

## Options considérées
1. **Lanceur** : l'utilisateur écrit `parts/<nom>.py` dans son projet ; `fdm-run parts/<nom>.py` l'exécute avec le Python du venv en ajoutant `plugins/fdm/lib` au `PYTHONPATH` (`from fdm_tools import check`), sorties dans `out/` du projet ; `fdm-slice` découpe. Une pièce ne se lance pas avec un `python` nu.
2. **Copie des outils dans le projet utilisateur** : chaque projet a sa copie, privée des correctifs.

## Décision
Option 1 : le plugin reste l'unique source des outils, le projet utilisateur ne contient que ses pièces et leurs sorties.

## Conséquences
- Les commandes `bin/` sont en bibliothèque standard et n'importent jamais `fdm_tools` : elles lancent le venv en sous-processus.
- `fdm_tools` est l'API publique des pièces : la casser impose un bump majeur du plugin.
- Changer l'emplacement des pièces ou des sorties exige un ADR.
