---
name: conventions-python
description: Conventions Python pour écrire, tester et relire du code Python à l'état de l'art. À charger via cadre sur une stack Python.
---

# Conventions Python

Les conventions déjà présentes dans le dépôt priment. Lis `pyproject.toml` pour la version de Python ciblée et les outils, et n'utilise que la syntaxe qu'elle autorise.

## Code

- Typage complet des signatures publiques, propre en mode strict. Syntaxe moderne : `X | None`, génériques natifs (`list[str]`), `type` pour les alias si la version le permet.
- Données : `@dataclass(frozen=True, slots=True)` par défaut ; `Enum`/`StrEnum` plutôt que des chaînes magiques ; `Protocol` pour les dépendances injectées.
- Erreurs : exceptions métier dédiées, jamais de `except:` nu ni de `except Exception` silencieux ; relance avec `raise … from e`.
- Ressources : gestionnaires de contexte ; `pathlib` plutôt que `os.path` ; `logging` plutôt que `print`.
- Pas d'argument par défaut mutable, pas d'état global caché. Horloge, aléa, réseau et système de fichiers passent par des dépendances injectables.
- Fonctions courtes, une responsabilité ; nommage explicite ; pas de commentaire qui paraphrase le code.
- Dépendances gérées avec `uv` uniquement ; aucune nouvelle sans nécessité.

## Tests (pytest)

- Un comportement par test, nommé `test_<comportement>_<condition>` ; Arrange-Act-Assert.
- Tester par l'interface publique ; ne simuler que les frontières (réseau, horloge, aléa). Ne jamais simuler ce que le projet possède.
- `pytest.mark.parametrize` pour les variations ; `tmp_path` et `monkeypatch` plutôt que des fichiers ou variables réels.
- Assertions précises (`pytest.raises(ErreurMetier, match=...)`), jamais `assert result` seul.
- Déterminisme : aucune dépendance à l'ordre d'exécution ni à l'heure réelle.
