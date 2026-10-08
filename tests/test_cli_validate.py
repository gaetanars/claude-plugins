import json
import shutil
import subprocess
import unittest

from tests._common import ROOT, plugin_dirs, rel


def validate(path):
    r = subprocess.run(["claude", "plugin", "validate", "--strict", "--json", str(path)],
                       capture_output=True, text=True, cwd=ROOT)
    detail = r.stdout or r.stderr
    try:
        data = json.loads(r.stdout)
        msgs = []
        for part in [data.get("manifest")] + data.get("contents", []):
            for lvl in ("errors", "warnings"):
                for it in (part or {}).get(lvl, []):
                    msgs.append(f"{rel(part['file'])}: {it.get('path')}: {it.get('message')}")
        detail = "\n".join(msgs) or detail
    except (ValueError, KeyError):
        pass
    return r.returncode, detail


@unittest.skipUnless(shutil.which("claude"), "CLI claude absent")
class CliValidateTest(unittest.TestCase):
    def test_marketplace(self):
        code, detail = validate(ROOT)
        self.assertEqual(code, 0, detail)

    def test_plugins(self):
        for d in plugin_dirs():
            with self.subTest(plugin=d.name):
                code, detail = validate(d)
                self.assertEqual(code, 0, detail)


if __name__ == "__main__":
    unittest.main()
