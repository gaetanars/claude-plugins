# fdm

Conception de pièces imprimables en FDM pour imprimantes Bambu Lab, modélisées en [build123d](https://github.com/gumyr/build123d) : le skill `/fdm:design` écrit la pièce, la vérifie (`check()`), produit un rendu PNG et la découpe avec Bambu Studio (temps, poids, `.3mf`).

## Prérequis

- Bambu Studio installé (sa CLI sert à la découpe, ses profils système à `fdm-profiles`).
- Python 3.11 à 3.14 (option `python`).
- Accès réseau et environ 300 Mo de disque au premier `fdm-setup` (venv avec build123d, trimesh, manifold3d, matplotlib, numpy).

## Installation

```
/plugin marketplace add gaetanars/claude-plugins
/plugin install fdm@gaetanars
```

## Mise en route

Une fois par machine, les commandes `fdm-setup` puis `fdm-profiles` (le skill `/fdm:design` les propose s'il manque le venv ou un profil) :

- `fdm-setup` crée le venv sous `${CLAUDE_PLUGIN_DATA}/venv` ;
- `fdm-profiles` aplatit les profils machine, process et filament de Bambu Studio sous `${CLAUDE_PLUGIN_DATA}/profiles`. À relancer après une mise à jour de Bambu Studio.

## Usage

`/fdm:design <besoin>` dans un dossier de projet : les pièces vont dans `parts/<nom>.py`, les sorties (STEP, STL, PNG, découpe dans `out/slice_<nom>/`) dans `out/`. Une pièce de référence est fournie : `lib/fdm_tools/examples/calibration_cube.py`.

## Options (`userConfig`)

| Option | Défaut | Rôle |
|---|---|---|
| `machine` | `Bambu Lab A1 0.4 nozzle` | profil machine Bambu Studio |
| `process` | `0.20mm Standard @BBL A1` | profil de process |
| `filament` | `Generic PLA @BBL A1` | profil de filament |
| `bambu_studio` | vide | exécutable Bambu Studio ; vide = chemin macOS standard |
| `bambu_profiles` | vide | dossier `profiles/BBL` de Bambu Studio ; vide = chemin macOS standard |
| `python` | `python3` | interpréteur Python 3.11 à 3.14 du venv |

## Plateformes

macOS : vérifié. Linux : non vérifié ; les options `bambu_studio` et `bambu_profiles` y sont obligatoires. Windows : non pris en charge.
