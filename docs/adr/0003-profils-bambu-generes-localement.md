# ADR-0003: Profils Bambu Studio générés localement, jamais redistribués

## Statut
Accepté

## Contexte
La CLI de Bambu Studio ne résout pas l'héritage (`inherits`) des profils : il faut des profils aplatis. Les travaux d'origine embarquaient trois profils A1 aplatis, copiés de Bambu Studio (AGPL-3.0), alors que la marketplace est sous MIT.

## Options considérées
1. **Génération locale** : `fdm-profiles` aplatit, depuis l'installation de Bambu Studio de l'utilisateur, les profils choisis en options, vers `${CLAUDE_PLUGIN_DATA}/profiles/` ; aucun risque de licence, toujours alignés sur la version installée, toute imprimante Bambu couverte ; à régénérer après une mise à jour de Bambu Studio.
2. **Profils A1 embarqués dans le plugin** : risque de licence, A1 seulement, périmés à chaque version de Bambu Studio.

## Décision
Option 1 : elle reprend le mécanisme existant (`flatten_profiles.py`), supprime le risque juridique et tient la portée de l'ADR-0001.

## Conséquences
- Aucun fichier de Bambu Studio n'entre dans le dépôt ; toute redistribution de fichier tiers exige un ADR.
- `fdm-slice` échoue avec un renvoi vers `fdm-profiles` si les profils manquent ou si la découpe échoue après une mise à jour.
