import unittest

from tests._common import ROOT, SEMVER, load_json, marketplace, plugins, rel

NAME_RE = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"


class MarketplaceTest(unittest.TestCase):
    def test_champs_obligatoires(self):
        m = marketplace()
        self.assertRegex(m.get("name", ""), NAME_RE, "name invalide")
        self.assertNotIn("..", m["name"])
        self.assertTrue(m.get("description", "").strip(), "description manquante")
        self.assertTrue(m.get("owner", {}).get("name"), "owner.name manquant")
        self.assertTrue(m.get("plugins"), "aucun plugin déclaré")

    def test_entrees(self):
        names = [e.get("name") for e in marketplace()["plugins"]]
        self.assertEqual(len(names), len(set(names)), f"noms dupliqués: {names}")
        for e in marketplace()["plugins"]:
            with self.subTest(plugin=e.get("name")):
                self.assertTrue(e.get("name"), "name manquant")
                self.assertTrue(e.get("description", "").strip(), "description manquante")
                self.assertIn("source", e, "source manquante")
                self.assertNotIn("version", e, "version dans l'entrée: elle doit vivre dans plugin.json seulement")

    def test_sources_et_noms(self):
        for name, d in plugins():
            with self.subTest(plugin=name):
                self.assertTrue(d.is_dir(), f"source introuvable: {rel(d)}")
                self.assertEqual(d.parent, (ROOT / "plugins").resolve(), f"{rel(d)} hors de plugins/")
                self.assertEqual(d.name, name, "nom du dossier ≠ nom de l'entrée")
                manifest = d / ".claude-plugin" / "plugin.json"
                self.assertTrue(manifest.is_file(), f"{rel(manifest)} manquant")
                self.assertEqual(load_json(manifest).get("name"), name, f"{rel(manifest)}: name ≠ entrée")

    def test_aucun_plugin_orphelin(self):
        declared = {d.name for _, d in plugins()}
        on_disk = {p.name for p in (ROOT / "plugins").iterdir() if p.is_dir()}
        self.assertEqual(on_disk - declared, set(), "dossiers plugins/ absents de marketplace.json")

    def test_pas_de_claude_md_dans_un_plugin(self):
        for name, d in plugins():
            with self.subTest(plugin=name):
                self.assertFalse((d / "CLAUDE.md").exists(), "CLAUDE.md à la racine d'un plugin (avertissement validate)")


if __name__ == "__main__":
    unittest.main()
