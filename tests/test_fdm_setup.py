"""fdm-setup : venv sous <data>, avec un faux interpréteur (hors ligne, sans pip)."""
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/fdm/bin/fdm-setup"
REQ = ROOT / "plugins/fdm/requirements.txt"

FAKE = """#!%s
import os, shutil, sys
a = sys.argv[1:]
log = lambda s: open(os.environ["FAKE_LOG"], "a").write(s + "\\n")
if a[:1] == ["-c"]:
    v = os.environ.get("FAKE_PY_VERSION", "3.12")
    print(v)
elif a[:2] == ["-m", "venv"]:
    if os.environ.get("FAKE_VENV_FAIL"):
        sys.exit(1)
    log("venv " + a[2])
    os.makedirs(a[2] + "/bin")
    shutil.copy(__file__, a[2] + "/bin/python")
    os.chmod(a[2] + "/bin/python", 0o755)
elif a[:3] == ["-m", "pip", "install"]:
    log("pip " + " ".join(a[2:]))
    if os.environ.get("FAKE_PIP_FAIL"):
        sys.exit(1)
else:
    sys.exit(3)
""" % sys.executable


class Setup(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, ignore_errors=True)
        self.data = self.t / "data"
        self.log = self.t / "log"
        self.log.touch()
        self.py = self.fake_python(self.t / "bin" / "python-fake")

    def fake_python(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(FAKE)
        path.chmod(0o755)
        return path

    def run_setup(self, *args, **extra):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_DATA"}
        env.update(FAKE_LOG=str(self.log), **extra)
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)

    def setup(self, *extra, **env):
        return self.run_setup("--data", str(self.data), "--python", str(self.py), *extra, **env)

    def calls(self):
        return self.log.read_text().splitlines()

    def leftovers(self):
        return [p.name for p in self.data.iterdir() if p.name != "venv"] if self.data.exists() else []

    def test_no_data_dir(self):
        r = self.run_setup("--python", str(self.py))
        self.assertEqual(r.returncode, 1)
        self.assertIn("--data", r.stderr)
        self.assertIn("CLAUDE_PLUGIN_DATA", r.stderr)
        self.assertFalse(self.data.exists())

    def test_data_from_env(self):
        r = self.run_setup("--python", str(self.py), CLAUDE_PLUGIN_DATA=str(self.data))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.data / "venv").is_dir())

    def test_rejects_python_out_of_range(self):
        for v in ("3.10", "3.15"):
            r = self.setup(FAKE_PY_VERSION=v)
            self.assertEqual(r.returncode, 1)
            self.assertIn(v, r.stderr)
            self.assertIn("3.11", r.stderr)
            self.assertIn("3.15", r.stderr)
            self.assertFalse(self.data.exists())

    def test_accepts_bounds(self):
        for v in ("3.11", "3.14"):
            shutil.rmtree(self.data, ignore_errors=True)
            self.assertEqual(self.setup(FAKE_PY_VERSION=v).returncode, 0)

    def test_python_not_found(self):
        r = self.run_setup("--data", str(self.data), "--python", str(self.t / "absent"))
        self.assertEqual(r.returncode, 1)
        self.assertTrue(r.stderr)
        self.assertFalse(self.data.exists())

    def test_python_not_executable(self):
        self.py.chmod(stat.S_IRUSR | stat.S_IWUSR)
        r = self.setup()
        self.assertEqual(r.returncode, 1)
        self.assertTrue(r.stderr)
        self.assertFalse(self.data.exists())

    def test_default_python_from_path(self):
        self.fake_python(self.t / "path" / "python3")
        r = self.run_setup("--data", str(self.data), PATH=str(self.t / "path") + os.pathsep + os.environ["PATH"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.calls()), 2)

    def test_creates_venv(self):
        r = self.setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(str(self.data / "venv"), r.stdout)
        venv_call, pip_call = self.calls()
        tmp = Path(venv_call.split(" ", 1)[1])
        self.assertEqual(tmp.parent, self.data)
        self.assertNotEqual(tmp, self.data / "venv")
        self.assertEqual(pip_call, f"pip install -r {REQ}")
        digest = hashlib.sha256(REQ.read_bytes()).hexdigest()
        self.assertEqual((self.data / "venv/requirements.sha256").read_text().strip(), digest)
        self.assertEqual(self.leftovers(), [])

    def test_idempotent(self):
        self.setup()
        self.log.write_text("")
        r = self.setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.calls(), [])

    def test_rebuild_on_hash_change(self):
        self.setup()
        self.log.write_text("")
        (self.data / "venv/requirements.sha256").write_text("0" * 64)
        self.assertEqual(self.setup().returncode, 0)
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual((self.data / "venv/requirements.sha256").read_text().strip(), hashlib.sha256(REQ.read_bytes()).hexdigest())

    def test_force_rebuilds(self):
        self.setup()
        (self.data / "venv/witness").touch()
        self.log.write_text("")
        self.assertEqual(self.setup("--force").returncode, 0)
        self.assertEqual(len(self.calls()), 2)
        self.assertFalse((self.data / "venv/witness").exists())
        self.assertEqual(self.leftovers(), [])

    def test_pip_failure_without_venv(self):
        r = self.setup(FAKE_PIP_FAIL="1")
        self.assertEqual(r.returncode, 1)
        self.assertTrue(r.stderr)
        self.assertFalse((self.data / "venv").exists())
        self.assertEqual(self.leftovers(), [])

    def test_pip_failure_keeps_previous_venv(self):
        self.setup()
        (self.data / "venv/witness").touch()
        r = self.setup("--force", FAKE_PIP_FAIL="1")
        self.assertEqual(r.returncode, 1)
        self.assertTrue((self.data / "venv/witness").exists())
        self.assertEqual(self.leftovers(), [])

    def test_venv_creation_failure(self):
        r = self.setup(FAKE_VENV_FAIL="1")
        self.assertEqual(r.returncode, 1)
        self.assertTrue(r.stderr)
        self.assertFalse((self.data / "venv").exists())
        self.assertEqual(self.leftovers(), [])

    def test_usage_errors(self):
        self.assertEqual(self.run_setup("--bogus").returncode, 2)
        self.assertEqual(self.run_setup("--python").returncode, 2)


if __name__ == "__main__":
    unittest.main()
