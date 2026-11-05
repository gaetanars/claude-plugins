import os
import py_compile
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._common import ROOT, git, load_json, plugin_dirs, rel


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

    def test_bin_executables(self):
        """Tout fichier de plugins/*/bin/ a un shebang et le bit exécutable (index git ; système de fichiers s'il n'est pas encore suivi)."""
        for d in plugin_dirs():
            for p in [q for q in sorted((d / "bin").glob("*")) if q.is_file()]:
                with self.subTest(file=rel(p)):
                    first = p.read_text(encoding="utf-8").split("\n", 1)[0]
                    self.assertTrue(first.startswith("#!"), "shebang manquant")
                    staged = git("ls-files", "-s", "--", str(p.relative_to(ROOT))).stdout.split()
                    if staged:
                        self.assertEqual(staged[0], "100755", "bit exécutable absent de l'index git")
                    else:
                        self.assertTrue(os.access(p, os.X_OK), "bit exécutable absent")
                    if "python3" in first:
                        with tempfile.TemporaryDirectory() as tmp:
                            py_compile.compile(str(p), cfile=str(Path(tmp) / "x.pyc"), doraise=True)

    @unittest.skipUnless(shutil.which("bash"), "bash absent")
    def test_shell(self):
        for d in plugin_dirs():
            for p in walk(d, "*.sh"):
                with self.subTest(file=rel(p)):
                    r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
