"""fdm-run : lanceur avec un faux venv (hors ligne, sans fdm_tools)."""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/fdm/bin/fdm-run"
LIB = (ROOT / "plugins/fdm/lib").resolve()

FAKE = """#!%s
import json, os, sys
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps([sys.argv[0], sys.argv[1:], os.getcwd(), os.environ.get("PYTHONPATH"), os.environ.get("FDM_DATA")]) + "\\n")
print("fake-out")
print("fake-err", file=sys.stderr)
sys.exit(int(os.environ.get("FAKE_RC", "0")))
""" % sys.executable


class Run(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, ignore_errors=True)
        self.project = self.t / "project"
        (self.project / "parts").mkdir(parents=True)
        (self.project / "parts/p.py").write_text("")
        self.log = self.t / "log"
        self.log.touch()
        self.data = self.make_data("data")

    def make_data(self, name, executable=True):
        py = self.t / name / "venv/bin/python"
        py.parent.mkdir(parents=True)
        py.write_text(FAKE)
        py.chmod(0o755 if executable else 0o644)
        return self.t / name

    def run_fdm(self, *args, **extra):
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PLUGIN_DATA", "PYTHONPATH")}
        env.update(FAKE_LOG=str(self.log), **extra)
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=self.project)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def snapshot(self):
        return sorted(str(p) for base in (self.data, self.project) for p in base.rglob("*"))

    def test_no_data_dir(self):
        r = self.run_fdm("parts/p.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("--data", r.stderr)
        self.assertIn("CLAUDE_PLUGIN_DATA", r.stderr)
        self.assertEqual(self.calls(), [])

    def test_data_from_env(self):
        r = self.run_fdm("parts/p.py", CLAUDE_PLUGIN_DATA=str(self.data))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.calls()), 1)

    def test_data_option_overrides_env(self):
        other = self.make_data("other")
        r = self.run_fdm("--data", str(other), "parts/p.py", CLAUDE_PLUGIN_DATA=str(self.data))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.calls()[0][0], str(other / "venv/bin/python"))

    def test_usage_errors(self):
        for args in (("--bogus", "parts/p.py"), (), ("--data",)):
            with self.subTest(args=args):
                self.assertEqual(self.run_fdm(*args, CLAUDE_PLUGIN_DATA=str(self.data)).returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_missing_venv(self):
        shutil.rmtree(self.data / "venv")
        r = self.run_fdm("--data", str(self.data), "parts/p.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("fdm-setup", r.stderr)
        self.assertEqual(self.calls(), [])

    def test_missing_piece(self):
        r = self.run_fdm("--data", str(self.data), "parts/nope.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn("parts/nope.py", r.stderr)
        self.assertEqual(self.calls(), [])

    def test_piece_is_directory(self):
        r = self.run_fdm("--data", str(self.data), "parts")
        self.assertEqual(r.returncode, 1)
        self.assertIn("parts", r.stderr)
        self.assertEqual(self.calls(), [])

    def test_launches_module_in_cwd(self):
        r = self.run_fdm("--data", str(self.data), "parts/p.py", "a", "--data", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        argv0, argv, cwd, _, fdm_data = self.calls()[0]
        self.assertEqual(argv0, str(self.data / "venv/bin/python"))
        self.assertEqual(argv, ["-m", "fdm_tools.run", "parts/p.py", "a", "--data", "x"])
        self.assertEqual(Path(cwd).resolve(), self.project.resolve())
        self.assertEqual(fdm_data, str(self.data))

    def test_pythonpath_without_existing(self):
        self.run_fdm("--data", str(self.data), "parts/p.py")
        self.assertEqual(self.calls()[0][3], str(LIB))

    def test_pythonpath_prepended(self):
        self.run_fdm("--data", str(self.data), "parts/p.py", PYTHONPATH="/x:/y")
        self.assertEqual(self.calls()[0][3], f"{LIB}:/x:/y")

    def test_relays_exit_code(self):
        for rc in (0, 1, 3):
            with self.subTest(rc=rc):
                self.assertEqual(self.run_fdm("--data", str(self.data), "parts/p.py", FAKE_RC=str(rc)).returncode, rc)

    def test_output_not_captured(self):
        r = self.run_fdm("--data", str(self.data), "parts/p.py")
        self.assertIn("fake-out", r.stdout)
        self.assertIn("fake-err", r.stderr)

    def test_writes_nothing(self):
        before = self.snapshot()
        self.run_fdm("--data", str(self.data), "parts/p.py")
        self.assertEqual(self.snapshot(), before)

    def test_imports_stdlib_only(self):
        tree = ast.parse(SCRIPT.read_text())
        roots = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                roots |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module:
                roots.add(n.module.split(".")[0])
        self.assertTrue(roots)
        self.assertLessEqual(roots, set(sys.stdlib_module_names))
        self.assertNotIn("fdm_tools", roots)

    def test_venv_python_not_executable(self):
        data = self.make_data("noexec", executable=False)
        r = self.run_fdm("--data", str(data), "parts/p.py")
        self.assertEqual(r.returncode, 1)
        self.assertIn(str(data / "venv/bin/python"), r.stderr)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
