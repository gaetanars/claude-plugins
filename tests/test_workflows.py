import re
import shutil
import subprocess
import unittest

from tests._common import plugin_dirs, rel

WRAP = """
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8').replace(/^export const meta/m, 'const meta');
new (Object.getPrototypeOf(async function () {}).constructor)(src);
"""


@unittest.skipUnless(shutil.which("node"), "node absent")
class WorkflowsTest(unittest.TestCase):
    def test_workflows(self):
        for d in plugin_dirs():
            for path in sorted(d.glob("workflows/*.js")):
                with self.subTest(file=rel(path)):
                    src = path.read_text(encoding="utf-8")
                    m = re.search(r"^export const meta = \{(.*?)^\}", src, re.S | re.M)
                    self.assertIsNotNone(m, "bloc 'export const meta = {…}' absent")
                    name = re.search(r"\bname:\s*'([^']+)'", m.group(1))
                    self.assertIsNotNone(name, "meta.name absent")
                    self.assertEqual(name.group(1), path.stem, "meta.name ≠ nom du fichier")
                    self.assertRegex(m.group(1), r"\bdescription:\s*'[^']+'", "meta.description vide")
                    r = subprocess.run(["node", "-e", WRAP, str(path)], capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, f"syntaxe invalide:\n{r.stderr}")


if __name__ == "__main__":
    unittest.main()
