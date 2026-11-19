# ADR-0002: Dépendances Python de fdm dans un venv sous ${CLAUDE_PLUGIN_DATA}

## Statut
Accepté

## Contexte
`fdm-tools` dépend de build123d (OCP, environ 300 Mo de wheels), trimesh, manifold3d, matplotlib et numpy. Le reste du dépôt est en bibliothèque standard et ses tests tournent hors ligne. Claude Code fournit `${CLAUDE_PLUGIN_DATA}`, un stockage persistant propre au plugin.

## Options considérées
1. **Venv géré par le plugin dans `${CLAUDE_PLUGIN_DATA}`** : `bin/fdm-setup` (bibliothèque standard) crée le venv (`python3 -m venv`) et installe un `requirements.txt` épinglé ; outils standard, installation unique par machine, versions reproductibles ; nécessite un Python compatible avec les wheels OCP et une première exécution.
2. **uv + PEP 723** : aucune étape d'installation, mais uv devient un prérequis non standard et le cache est moins prévisible hors ligne.
3. **Venv dans chaque projet utilisateur** : pollution des projets, installation lourde répétée, dérive de versions.

## Décision
Option 1 : outils natifs uniquement, installation unique et versions épinglées sur celles validées (build123d 0.13.0, trimesh 5.2.1, manifold3d 3.5.5, matplotlib 3.11.2, numpy 2.5.5).

## Conséquences
- Toute commande `fdm-*` qui a besoin du venv échoue avec un renvoi vers `fdm-setup` s'il est absent.
- La règle bibliothèque standard uniquement reste valable partout sauf dans `fdm-tools`.
- Les tests du dépôt n'installent ni n'importent build123d ; la chaîne CAO se vérifie en local (pièce de calibration). Rejeté : installer OCP en CI (plusieurs minutes et du réseau à chaque PR).
- Monter une version épinglée se fait par PR avec vérification locale ; un changement de version majeure exige un ADR.
