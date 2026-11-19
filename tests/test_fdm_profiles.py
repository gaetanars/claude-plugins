"""fdm-profiles : aplatissement des profils Bambu Studio (fausse arborescence)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/fdm/bin/fdm-profiles"
MAC_DEFAULT = "/Applications/BambuStudio.app/Contents/Resources/profiles/BBL"


def env():
    return {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_DATA"}


def run(*args, extra_env=None, platform=None):
    e = {**env(), **(extra_env or {})}
    if platform:
        code = "import sys,runpy; sys.platform=%r; sys.argv=%r; runpy.run_path(%r, run_name='__main__')" % (
            platform, [str(SCRIPT), *args], str(SCRIPT))
        cmd = [sys.executable, "-c", code]
    else:
        cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, capture_output=True, text=True, env=e)


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data))


class Profiles(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, ignore_errors=True)
        self.src = self.t / "BBL"
        self.data = self.t / "data"
        self.out = self.data / "profiles"

    def make_tree(self):
        put(self.src / "machine/M.json", {"name": "M", "a": 1, "bed": "x"})
        put(self.src / "process/P.json", {"name": "P", "layer": "0.2"})
        put(self.src / "filament/base/F0.json", {"name": "F0", "t": 200, "k": "base"})
        put(self.src / "filament/mid/F1.json", {"name": "F1", "inherits": "F0", "t": 210, "m": 1})
        put(self.src / "filament/F.json", {"name": "F", "inherits": "F1", "t": 220})

    def go(self, *extra):
        return run("--data", str(self.data), "--profiles-dir", str(self.src),
                   "--machine", "M", "--process", "P", "--filament", "F", *extra)

    def test_flattens_multi_level_inheritance(self):
        self.make_tree()
        r = self.go()
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (self.out / "filament.json").read_text()
        f = json.loads(text)
        self.assertEqual(f, {"name": "F", "t": 220, "k": "base", "m": 1, "from": "system"})
        self.assertIn("\n  ", text)
        self.assertEqual(json.loads((self.out / "machine.json").read_text())["from"], "system")
        self.assertEqual(len(r.stdout.strip().splitlines()), 3)
        self.assertIn("filament: F (5 keys)", r.stdout)

    def test_recursive_search_in_subfolders(self):
        self.make_tree()
        self.assertEqual(self.go().returncode, 0)
        self.assertEqual(json.loads((self.out / "filament.json").read_text())["k"], "base")

    def test_custom_names(self):
        self.make_tree()
        put(self.src / "machine/Other.json", {"x": 1})
        r = run("--data", str(self.data), "--profiles-dir", str(self.src),
                "--machine", "Other", "--process", "P", "--filament", "F")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((self.out / "machine.json").read_text()), {"x": 1, "name": "Other", "from": "system"})

    def test_data_from_env(self):
        self.make_tree()
        r = run("--profiles-dir", str(self.src), "--machine", "M", "--process", "P", "--filament", "F",
                extra_env={"CLAUDE_PLUGIN_DATA": str(self.data)})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.out / "process.json").exists())

    def test_no_data_dir(self):
        self.make_tree()
        before = set(self.t.rglob("*"))
        r = run("--profiles-dir", str(self.src), "--machine", "M", "--process", "P", "--filament", "F")
        self.assertEqual(r.returncode, 1)
        self.assertIn("--data", r.stderr)
        self.assertIn("CLAUDE_PLUGIN_DATA", r.stderr)
        self.assertEqual(set(self.t.rglob("*")), before)

    def test_profile_not_found(self):
        self.make_tree()
        (self.src / "process/P.json").unlink()
        r = self.go()
        self.assertEqual(r.returncode, 1)
        self.assertIn("P", r.stderr)
        self.assertIn(str(self.src / "process"), r.stderr)

    def test_parent_not_found(self):
        self.make_tree()
        put(self.src / "machine/M.json", {"inherits": "Ghost", "a": 1})
        r = self.go()
        self.assertEqual(r.returncode, 1)
        self.assertIn("Ghost", r.stderr)
        self.assertIn(str(self.src / "machine"), r.stderr)

    def test_ambiguous_name(self):
        self.make_tree()
        put(self.src / "machine/a/M.json", {})
        put(self.src / "machine/b/M.json", {})
        r = self.go()
        self.assertEqual(r.returncode, 1)
        self.assertIn(str(self.src / "machine/a/M.json"), r.stderr)
        self.assertIn(str(self.src / "machine/b/M.json"), r.stderr)

    def test_inherits_cycle(self):
        self.make_tree()
        put(self.src / "machine/M.json", {"inherits": "N"})
        put(self.src / "machine/N.json", {"inherits": "M"})
        r = self.go()
        self.assertEqual(r.returncode, 1)
        self.assertRegex(r.stderr, r"M.*N.*M")

    def test_invalid_json(self):
        self.make_tree()
        put(self.src / "machine/M.json", "{not json")
        self.assertEqual(self.go().returncode, 1)

    def test_json_not_object(self):
        self.make_tree()
        put(self.src / "machine/M.json", "[1, 2]")
        self.assertEqual(self.go().returncode, 1)

    def test_atomic_on_error(self):
        self.make_tree()
        put(self.out / "machine.json", '{"old": true}')
        (self.src / "filament/F.json").unlink()
        r = self.go()
        self.assertEqual(r.returncode, 1)
        self.assertEqual((self.out / "machine.json").read_text(), '{"old": true}')
        self.assertEqual([p.name for p in self.out.iterdir()], ["machine.json"])

    def assert_clean_failure(self, r, path):
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn(str(path), r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_data_is_a_file(self):
        self.make_tree()
        self.data.write_text("x")
        self.assert_clean_failure(self.go(), self.data)

    def test_data_beneath_a_file(self):
        self.make_tree()
        blocker = self.t / "blocker"
        blocker.write_text("x")
        self.data = blocker / "y"
        self.assert_clean_failure(self.go(), self.data)

    def test_out_not_writable(self):
        self.make_tree()
        put(self.out / "machine.json", '{"old": true}')
        self.out.chmod(0o500)
        self.addCleanup(self.out.chmod, 0o700)
        if os.access(self.out, os.W_OK):
            self.skipTest("dossier inscriptible malgré chmod (root)")
        self.assert_clean_failure(self.go(), self.out)
        self.assertEqual((self.out / "machine.json").read_text(), '{"old": true}')
        self.assertEqual([p.name for p in self.out.iterdir()], ["machine.json"])

    def test_non_macos_requires_profiles_dir(self):
        for extra in ([], ["--profiles-dir", ""]):
            r = run("--data", str(self.data), *extra, platform="linux")
            self.assertEqual(r.returncode, 1)
            self.assertIn("bambu_profiles", r.stderr)
        self.assertFalse(self.data.exists())

    @unittest.skipIf(Path(MAC_DEFAULT).exists(), "Bambu Studio installé : profils réels non lus")
    def test_macos_default_dir(self):
        r = run("--data", str(self.data), platform="darwin")
        self.assertEqual(r.returncode, 1)
        self.assertIn(MAC_DEFAULT, r.stderr)

    def test_missing_profiles_dir(self):
        r = run("--data", str(self.data), "--profiles-dir", str(self.t / "absent"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("absent", r.stderr)

    def test_usage_errors(self):
        self.assertEqual(run("--bogus").returncode, 2)
        self.assertEqual(run("--data").returncode, 2)


if __name__ == "__main__":
    unittest.main()
