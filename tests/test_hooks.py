import re
import unittest

from tests._common import load_json, plugin_dirs, rel

REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s\"']+)")


def commands(node):
    if isinstance(node, dict):
        if isinstance(node.get("command"), str):
            yield node["command"]
        for v in node.values():
            yield from commands(v)
    elif isinstance(node, list):
        for v in node:
            yield from commands(v)


class HooksTest(unittest.TestCase):
    def test_hooks_json(self):
        for d in plugin_dirs():
            path = d / "hooks" / "hooks.json"
            if not path.exists():
                continue
            with self.subTest(file=rel(path)):
                data = load_json(path)
                self.assertIsInstance(data.get("hooks"), dict, "clé 'hooks' (objet) obligatoire")
                for cmd in commands(data):
                    for ref in REF.findall(cmd):
                        self.assertTrue((d / ref).is_file(), f"script absent: {ref}")


if __name__ == "__main__":
    unittest.main()
