"""Déclaration du plugin fdm : manifeste, entrée marketplace, requirements."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/fdm"


def load(path):
    return json.loads(Path(path).read_text())


class FdmPlugin(unittest.TestCase):
    def test_marketplace_entry(self):
        entries = [p for p in load(ROOT / ".claude-plugin/marketplace.json")["plugins"] if p["name"] == "fdm"]
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(e["source"], "./plugins/fdm")
        self.assertNotIn("Préversion", e["description"])
        self.assertIn("découpe", e["description"])
        self.assertEqual(e["category"], "design")
        self.assertEqual(e["keywords"], ["3d-printing", "fdm", "bambu-lab", "build123d"])
        self.assertNotIn("version", e)

    def test_manifest_metadata(self):
        m = load(PLUGIN / ".claude-plugin/plugin.json")
        self.assertEqual(m["name"], "fdm")
        self.assertEqual(m["version"], "1.0.0")
        self.assertNotIn("Préversion", m["description"])
        self.assertIn("vérification", m["description"])
        self.assertIn("découpe", m["description"])
        self.assertEqual(m["author"], load(ROOT / "plugins/sdlc/.claude-plugin/plugin.json")["author"])
        self.assertEqual(m["license"], "MIT")

    def test_user_config(self):
        cfg = load(PLUGIN / ".claude-plugin/plugin.json")["userConfig"]
        defaults = {
            "machine": "Bambu Lab A1 0.4 nozzle",
            "process": "0.20mm Standard @BBL A1",
            "filament": "Generic PLA @BBL A1",
            "bambu_studio": "",
            "bambu_profiles": "",
            "python": "python3",
        }
        self.assertEqual(set(cfg), set(defaults))
        for key, default in defaults.items():
            self.assertEqual(cfg[key]["type"], "string", key)
            self.assertIs(cfg[key]["sensitive"], False, key)
            self.assertTrue(cfg[key]["title"], key)
            self.assertTrue(cfg[key]["description"], key)
            self.assertEqual(cfg[key]["default"], default, key)

    def test_plugin_readme(self):
        text = (PLUGIN / "README.md").read_text(encoding="utf-8")
        keys = load(PLUGIN / ".claude-plugin/plugin.json")["userConfig"]
        self.assertEqual(len(keys), 6)
        for s in ("Bambu Studio", "3.11", "3.14", "300 Mo", "/plugin install fdm@gaetanars", "fdm-setup",
                  "fdm-profiles", "/fdm:design", "parts/", "out/", "non vérifié", *keys):
            self.assertIn(s, text)

    def test_root_readme(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue(any(l.startswith("| `fdm` | 1.0.0 |") for l in text.splitlines()))
        self.assertIn("/plugin install fdm@gaetanars", text)

    def test_requirements_pinned(self):
        lines = [l.strip() for l in (PLUGIN / "requirements.txt").read_text().splitlines() if l.strip()]
        self.assertEqual(lines, ["build123d==0.13.0", "trimesh==5.2.1", "manifold3d==3.5.5", "matplotlib==3.11.2", "numpy==2.5.5"])


if __name__ == "__main__":
    unittest.main()
