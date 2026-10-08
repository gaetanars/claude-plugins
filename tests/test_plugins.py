import os
import unittest

from tests._common import SEMVER, ROOT, git, load_json, plugins, rel

BASE_REF = os.environ.get("BASE_REF")


def parse(v):
    return tuple(int(x) for x in v.split("."))


class PluginManifestTest(unittest.TestCase):
    def test_version_semver(self):
        for name, d in plugins():
            with self.subTest(plugin=name):
                m = load_json(d / ".claude-plugin" / "plugin.json")
                self.assertRegex(m.get("version", ""), SEMVER, f"{rel(d)}/.claude-plugin/plugin.json: version X.Y.Z requise")
                self.assertTrue(m.get("description", "").strip(), "description manquante")
                self.assertTrue(m.get("author", {}).get("name"), "author.name manquant")
                self.assertTrue(m.get("license"), "license manquante")

    @unittest.skipUnless(BASE_REF, "BASE_REF non défini")
    def test_bump_de_version(self):
        for name, d in plugins():
            with self.subTest(plugin=name):
                diff = git("diff", "--name-only", f"{BASE_REF}...HEAD", "--", str(d.relative_to(ROOT)))
                self.assertEqual(diff.returncode, 0, diff.stderr)
                if not diff.stdout.strip():
                    continue
                manifest = str((d / ".claude-plugin" / "plugin.json").relative_to(ROOT))
                old = git("show", f"{BASE_REF}:{manifest}")
                if old.returncode != 0:
                    continue  # plugin nouveau
                import json
                old_v = json.loads(old.stdout).get("version", "0.0.0")
                new_v = load_json(d / ".claude-plugin" / "plugin.json")["version"]
                self.assertGreater(parse(new_v), parse(old_v),
                                   f"{name}: fichiers modifiés depuis {BASE_REF} mais version {old_v} → {new_v} non incrémentée")


if __name__ == "__main__":
    unittest.main()
