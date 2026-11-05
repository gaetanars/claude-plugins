import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VALIDATOR = Path(__file__).resolve().parents[1] / "plugins/sdlc-contract/bin/sdlc-validate-architecture"

ARCH_MD = """---
schema_version: 1
status: {status}
updated: 2026-11-05
---

# Architecture : proj

## Contexte et objectifs
Petit service ; fiabilité et simplicité d'abord.

## Stack
Langage unique, aucune dépendance runtime majeure.

## Modules
- `domain` : règles métier, aucune dépendance sortante.
- `app` : cas d'usage, orchestre le domaine.

## Règles de dépendance
`app` peut importer `domain`, rien d'autre n'est autorisé.

## Principes et interdits
- Aucune logique métier dans `app`.

## Exige un ADR
- Création d'un module ou changement de frontière.

## Contrôle mécanique
Outil natif : `archtool`. Configuration : docs/architecture/native/archtool.cfg.
"""

RULES = {
    "schema_version": 1,
    "modules": [{"name": "domain", "paths": ["src/domain/**"]}, {"name": "app", "paths": ["src/app/**"]}],
    "allowed_dependencies": {"domain": [], "app": ["domain"]},
    "native": {"tool": "archtool", "config": "docs/architecture/native/archtool.cfg"},
}


def write_architecture(root, status="accepted", rules=None, md=None):
    """Crée un cadrage d'architecture valide sous <root>/docs/architecture (fixture partagée avec les autres tests SDLC)."""
    a = Path(root) / "docs" / "architecture"
    (a / "native").mkdir(parents=True, exist_ok=True)
    (a / "ARCHITECTURE.md").write_text(md if md is not None else ARCH_MD.format(status=status), encoding="utf-8")
    (a / "rules.json").write_text(json.dumps(rules if rules is not None else RULES, indent=2), encoding="utf-8")
    (a / "native" / "archtool.cfg").write_text("# config native\n", encoding="utf-8")
    return a


def validate(root, *flags):
    return subprocess.run([sys.executable, str(VALIDATOR), *flags, str(Path(root) / "docs" / "architecture")],
                          capture_output=True, text=True)


class ValidateArchitecture(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        write_architecture(self.root)

    def rules(self, **patch):
        r = json.loads(json.dumps(RULES))
        r.update(patch)
        write_architecture(self.root, rules=r)

    def fails(self, fragment, *flags):
        r = validate(self.root, *flags)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(fragment, r.stderr)

    def test_valid(self):
        r = validate(self.root, "--require-accepted")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_absent_directory(self):
        r = validate(Path(tempfile.mkdtemp()))
        self.assertEqual(r.returncode, 1)
        self.assertIn("/sdlc-framing:architect", r.stderr)

    def test_usage(self):
        self.assertEqual(subprocess.run([sys.executable, str(VALIDATOR)], capture_output=True, text=True).returncode, 2)

    def test_draft_refused_only_when_required(self):
        write_architecture(self.root, status="draft")
        self.assertEqual(validate(self.root).returncode, 0)
        self.fails("status draft", "--require-accepted")

    def test_frontmatter_errors(self):
        md = ARCH_MD.format(status="accepted")
        write_architecture(self.root, md=md.replace("schema_version: 1", "schema_version: 9"))
        self.fails("schema_version")
        write_architecture(self.root, md=md.replace("status: accepted", "status: ok"))
        self.fails("status doit être")
        write_architecture(self.root, md=md.replace("2026-11-05", "hier"))
        self.fails("updated")
        write_architecture(self.root, md=md.split("---\n", 2)[2])
        self.fails("frontmatter absent")

    def test_missing_or_empty_section(self):
        md = ARCH_MD.format(status="accepted")
        write_architecture(self.root, md=md.replace("## Stack\nLangage unique, aucune dépendance runtime majeure.\n\n", ""))
        self.fails("section « Stack » manquante")
        write_architecture(self.root, md=md.replace("- Création d'un module ou changement de frontière.", "rien"))
        self.fails("« Exige un ADR » doit lister")

    def test_placeholder(self):
        write_architecture(self.root, md=ARCH_MD.format(status="accepted").replace("Petit service", "TODO service"))
        self.fails("marqueur d'incomplétude")

    def test_rules_errors(self):
        self.rules(modules=[{"name": "domain", "paths": ["a"]}, {"name": "domain", "paths": ["b"]}])
        self.fails("module dupliqué")
        self.rules(modules=[{"name": "domain", "paths": []}, {"name": "app", "paths": ["a"]}])
        self.fails("paths doit être")
        self.rules(allowed_dependencies={"domain": [], "app": ["ghost"]})
        self.fails("module inconnu 'ghost'")
        self.rules(allowed_dependencies={"domain": []})
        self.fails("sans entrée pour 'app'")
        self.rules(allowed_dependencies={"domain": ["domain"], "app": []})
        self.fails("dépend de lui-même")
        self.rules(allowed_dependencies={"domain": ["app"], "app": ["domain"]})
        self.fails("cycle")
        self.rules(schema_version=2)
        self.fails("schema_version")

    def test_native_errors(self):
        for native, fragment in (({"tool": "", "config": "docs/architecture/native/archtool.cfg"}, "native.tool"),
                                 ({"tool": "archtool", "config": "pyproject.toml"}, "doit être sous docs/architecture/native/"),
                                 ({"tool": "archtool", "config": "docs/architecture/native/../../x"}, "doit être sous"),
                                 ({"tool": "archtool", "config": "docs/architecture/native/absent.cfg"}, "introuvable"),
                                 ({"tool": "archtool", "config": "docs/architecture/native/archtool.cfg",
                                   "baseline": "docs/architecture/native/baseline.txt"}, "baseline")):
            self.rules(native=native)
            self.fails(fragment)
        (self.root / "docs/architecture/native/baseline.txt").write_text("x")
        self.rules(native={"tool": "archtool", "config": "docs/architecture/native/archtool.cfg",
                           "baseline": "docs/architecture/native/baseline.txt"})
        self.assertEqual(validate(self.root).returncode, 0)

    def test_prose_and_rules_must_agree(self):
        self.rules(modules=RULES["modules"] + [{"name": "infra", "paths": ["src/infra/**"]}],
                   allowed_dependencies={"domain": [], "app": ["domain"], "infra": []})
        self.fails("module `infra` (rules.json) absent")
        md = ARCH_MD.format(status="accepted").replace("`archtool`", "autre").replace("archtool.cfg", "x.cfg")
        write_architecture(self.root, md=md)
        self.fails("ne mentionne pas l'outil")

    def test_adr_consistency(self):
        adr = self.root / "docs" / "adr"
        adr.mkdir(parents=True)
        (adr / "0001-a.md").write_text("# ADR-0001: a\n\n## Statut\nAccepté\n")
        (adr / "0002-b.md").write_text("# ADR-0002: b\n\n## Statut\nRemplacé par 0003\n")
        self.fails("n'existe pas")
        (adr / "0003-c.md").write_text("# ADR-0003: c\n\n## Statut\nAccepté\n")
        self.assertEqual(validate(self.root).returncode, 0)
        (adr / "0003-d.md").write_text("# ADR-0003: d\n\n## Statut\nAccepté\n")
        self.fails("dupliqué")
        (adr / "0003-d.md").unlink()
        (adr / "0003-c.md").write_text("# ADR-0003: c\n\n## Statut\nPeut-être\n")
        self.fails("Statut invalide")


if __name__ == "__main__":
    unittest.main()
