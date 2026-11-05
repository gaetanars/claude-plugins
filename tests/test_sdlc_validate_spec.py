import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VALIDATOR = Path(__file__).resolve().parents[1] / "plugins/sdlc-contract/bin/sdlc-validate-spec"

SPEC = """---
schema_version: 1
id: 0001-hello
title: Hello
status: ready
depends_on: []
---

# Hello

## Contexte
Ajouter un fichier hello.txt pour valider le flux de bout en bout.

## Périmètre
- Créer hello.txt avec une ligne de contenu.

## Hors périmètre
- Toute autre fonctionnalité.

## Critères d'acceptation
- [ ] CA-1: Le fichier hello.txt existe à la racine et contient au moins une ligne.

## Contraintes
Aucune dépendance externe, fichier texte brut.
"""
BRIEF = """---
schema_version: 1
id: 0001-hello
title: Hello
---

# Brief : Hello

## Problème
Valider le flux de bout en bout du SDLC sur un cas minimal.

## Valeur
Confiance dans l'automate avant usage réel.
"""
AMB = """---
schema_version: 1
id: 0001-hello
---

# Ambiguïtés levées

- [x] Q1: Quel contenu ? → R: Une ligne libre (2026-11-04)
"""


def make(spec=SPEC, brief=BRIEF, amb=AMB, name="0001-hello"):
    d = Path(tempfile.mkdtemp()) / name
    d.mkdir()
    for f, t in (("spec.md", spec), ("brief.md", brief), ("ambiguities.md", amb)):
        if t is not None:
            (d / f).write_text(t, encoding="utf-8")
    return d


def check(d):
    r = subprocess.run([sys.executable, str(VALIDATOR), str(d)], capture_output=True, text=True)
    return r.returncode, r.stderr + r.stdout


class ValidateSpec(unittest.TestCase):
    def test_valid(self):
        code, out = check(make())
        self.assertEqual(code, 0, out)

    def test_open_question_blocks(self):
        code, out = check(make(amb=AMB + "- [ ] Q2: Format ?\n"))
        self.assertEqual(code, 1)
        self.assertIn("question ouverte", out)

    def test_missing_file(self):
        code, out = check(make(brief=None))
        self.assertEqual(code, 1)
        self.assertIn("brief.md manquant", out)

    def test_unsupported_schema_version(self):
        code, out = check(make(spec=SPEC.replace("schema_version: 1", "schema_version: 9")))
        self.assertEqual(code, 1)
        self.assertIn("non supporté", out)

    def test_id_must_match_folder(self):
        code, out = check(make(name="0002-other"))
        self.assertEqual(code, 1)
        self.assertIn("≠ nom du dossier", out)

    def test_vague_criterion(self):
        code, out = check(make(spec=SPEC.replace("Le fichier hello.txt existe à la racine et contient au moins une ligne.", "ça marche")))
        self.assertEqual(code, 1)
        self.assertIn("trop vague", out)

    def test_no_criteria(self):
        code, out = check(make(spec=SPEC.replace("- [ ] CA-1:", "- CA-1:")))
        self.assertEqual(code, 1)
        self.assertIn("aucun critère", out)

    def test_placeholder_marker(self):
        code, out = check(make(spec=SPEC.replace("Aucune dépendance externe", "TODO préciser la dépendance")))
        self.assertEqual(code, 1)
        self.assertIn("incomplétude", out)

    def test_status_must_be_ready(self):
        code, out = check(make(spec=SPEC.replace("status: ready", "status: draft")))
        self.assertEqual(code, 1)

    def test_out_of_scope_needs_a_bullet(self):
        code, out = check(make(spec=SPEC.replace("- Toute autre fonctionnalité.", "Rien.")))
        self.assertEqual(code, 1)
        self.assertIn("Hors périmètre", out)

    def test_depends_on_format(self):
        code, _ = check(make(spec=SPEC.replace("depends_on: []", "depends_on: [0002-base]")))
        self.assertEqual(code, 0)
        code, out = check(make(spec=SPEC.replace("depends_on: []", "depends_on: 0002-base")))
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
