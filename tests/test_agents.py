import unittest

from tests._common import parse_frontmatter, plugin_dirs, rel

IGNORES = ("hooks", "mcpServers", "permissionMode", "initialPrompt")


class AgentsTest(unittest.TestCase):
    def test_frontmatter(self):
        for d in plugin_dirs():
            for path in sorted(d.glob("agents/*.md")):
                with self.subTest(file=rel(path)):
                    fm = parse_frontmatter(path)
                    self.assertEqual(fm.get("name"), path.stem, "name ≠ nom du fichier")
                    self.assertNotIn(":", fm["name"])
                    self.assertTrue(fm.get("description", "").strip(), "description vide")
                    for k in IGNORES:
                        self.assertNotIn(k, fm, f"champ '{k}' ignoré pour un agent de plugin")


if __name__ == "__main__":
    unittest.main()
