import unittest

from tests._common import parse_frontmatter, plugin_dirs, rel


def files():
    out = []
    for d in plugin_dirs():
        out += [(p, p.parent.name) for p in sorted(d.glob("skills/*/SKILL.md"))]
        out += [(p, p.stem) for p in sorted(d.glob("commands/*.md"))]
    return out


class SkillsTest(unittest.TestCase):
    def test_frontmatter(self):
        for path, expected in files():
            with self.subTest(file=rel(path)):
                fm = parse_frontmatter(path)
                self.assertTrue(fm.get("description", "").strip(), "description vide")
                self.assertLessEqual(len(fm["description"]), 1536, "description > 1536 caractères")
                if "name" in fm:
                    self.assertEqual(fm["name"], expected, "name ≠ nom du dossier/fichier")
                    self.assertRegex(fm["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$", "name non kebab-case")


if __name__ == "__main__":
    unittest.main()
