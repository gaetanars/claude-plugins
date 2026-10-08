import py_compile
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._common import load_json, plugin_dirs, rel


def walk(d, pattern):
    return [p for p in sorted(d.rglob(pattern)) if "node_modules" not in p.parts]


class FilesTest(unittest.TestCase):
    def test_json(self):
        for d in plugin_dirs():
            for p in walk(d, "*.json"):
                with self.subTest(file=rel(p)):
                    load_json(p)

    def test_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            for d in plugin_dirs():
                for i, p in enumerate(walk(d, "*.py")):
                    with self.subTest(file=rel(p)):
                        py_compile.compile(str(p), cfile=str(Path(tmp) / f"{i}.pyc"), doraise=True)

    @unittest.skipUnless(shutil.which("bash"), "bash absent")
    def test_shell(self):
        for d in plugin_dirs():
            for p in walk(d, "*.sh"):
                with self.subTest(file=rel(p)):
                    r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
