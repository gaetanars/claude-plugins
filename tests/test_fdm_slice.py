"""fdm-slice : découpe avec un faux Bambu Studio (hors ligne, sans venv ni fdm_tools)."""
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
SCRIPT = ROOT / "plugins/fdm/bin/fdm-slice"
MAC_EXE = "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"

FAKE = """#!%s
import json, os, sys
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps([sys.argv[1:], os.getcwd()]) + "\\n")
for i in range(1, int(os.environ.get("FAKE_LINES", "3")) + 1):
    print("line %%d" %% i)
    print("[trace] t%%d" %% i, file=sys.stderr)
    print("line %%d" %% i, file=sys.stderr)
if "FAKE_GCODE" in os.environ:
    out = sys.argv[sys.argv.index("--outputdir") + 1]
    with open(os.path.join(out, "plate_1.gcode"), "w") as f:
        f.write(os.environ["FAKE_GCODE"])
sys.exit(int(os.environ.get("FAKE_RC", "0")))
""" % sys.executable

GCODE_OK = (
    "; header\n"
    "; total filament weight [g] : 3.1\n"
    "; model printing time: 12m 3s; total estimated time: 15m\n"
    "; total filament length [mm] : 1000\n"
    "; total filament weight [g] : 9\n"
)
LINES_OK = [
    "; total filament weight [g] : 3.1",
    "; model printing time: 12m 3s; total estimated time: 15m",
    "; total filament length [mm] : 1000",
]


def run(*args, platform=None, cwd=None, **env):
    e = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_DATA"}
    e.update(env)
    if platform:
        code = "import sys,runpy; sys.platform=%r; sys.argv=%r; runpy.run_path(%r, run_name='__main__')" % (
            platform, [str(SCRIPT), *args], str(SCRIPT))
        cmd = [sys.executable, "-c", code]
    else:
        cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, capture_output=True, text=True, env=e, cwd=cwd)


class Slice(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, ignore_errors=True)
        self.data = self.t / "data"
        for k in ("machine", "process", "filament"):
            (self.data / "profiles").mkdir(parents=True, exist_ok=True)
            (self.data / "profiles" / f"{k}.json").write_text("{}")
        self.project = self.t / "project"
        (self.project / "out").mkdir(parents=True)
        (self.project / "out/p.stl").write_text("solid")
        self.out = self.project / "out/slice_p"
        self.bs = self.t / "bs"
        self.bs.write_text(FAKE)
        self.bs.chmod(0o755)
        self.log = self.t / "log"
        self.log.touch()

    def go(self, *args, data=True, **env):
        pre = ["--data", str(self.data)] if data else []
        env.setdefault("FAKE_LOG", str(self.log))
        return run(*pre, "--bambu-studio", str(self.bs), *args, cwd=self.project, **env)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def snapshot(self):
        snap = {}
        for base in (self.data, self.project):
            for p in base.rglob("*"):
                if p.is_file():
                    snap[str(p)] = (p.read_bytes(), p.stat().st_mtime_ns)
        return snap

    def test_data_from_env(self):
        r = run("--bambu-studio", str(self.bs), "out/p.stl", cwd=self.project,
                CLAUDE_PLUGIN_DATA=str(self.data), FAKE_LOG=str(self.log), FAKE_GCODE=GCODE_OK)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.calls()), 1)

    def test_data_option_overrides_env(self):
        other = self.t / "other"
        r = run("--data", str(self.data), "--bambu-studio", str(self.bs), "out/p.stl", cwd=self.project,
                CLAUDE_PLUGIN_DATA=str(other), FAKE_LOG=str(self.log), FAKE_GCODE=GCODE_OK)
        self.assertEqual(r.returncode, 0, r.stderr)
        argv = self.calls()[0][0]
        self.assertIn(str(self.data / "profiles/machine.json"), argv[argv.index("--load-settings") + 1])

    def test_usage_errors(self):
        for args in (["--bogus", "out/p.stl"], [], ["--data", str(self.data)]):
            with self.subTest(args=args):
                r = run(*args, cwd=self.project, FAKE_LOG=str(self.log))
                self.assertEqual(r.returncode, 2)
                self.assertEqual(self.calls(), [])

    def test_command_line(self):
        r = self.go("out/p.stl", FAKE_GCODE=GCODE_OK)
        self.assertEqual(r.returncode, 0, r.stderr)
        (argv, cwd), = self.calls()
        p = self.data / "profiles"
        self.assertEqual(Path(argv[argv.index("--outputdir") + 1]).resolve(), self.out.resolve())
        self.assertEqual(Path(cwd).resolve(), self.project.resolve())
        argv[argv.index("--outputdir") + 1] = "<OUT>"
        self.assertEqual(argv, [
            "--debug", "1",
            "--load-settings", f"{p}/machine.json;{p}/process.json",
            "--load-filaments", f"{p}/filament.json",
            "--arrange", "1", "--orient", "0", "--slice", "0",
            "--export-3mf", "p.3mf", "--outputdir", "<OUT>", "out/p.stl"])

    def test_success_output(self):
        r = self.go("out/p.stl", FAKE_GCODE=GCODE_OK)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[:3], LINES_OK)
        self.assertEqual(len(lines), 4)
        self.assertEqual(Path(lines[3][len("Output: "):]).resolve(), (self.out / "p.3mf").resolve())
        self.assertTrue(lines[3].startswith("Output: "))
        self.assertNotIn("line ", r.stdout)
        self.assertNotIn("line ", r.stderr)

    def test_length_optional(self):
        g = "\n".join(LINES_OK[:2]) + "\n"
        r = self.go("out/p.stl", FAKE_GCODE=g)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_missing_time_or_weight(self):
        gcode = self.out / "plate_1.gcode"
        for name, lines in (("temps", [LINES_OK[0], LINES_OK[2]]), ("poids", LINES_OK[1:])):
            with self.subTest(manque=name):
                r = self.go("out/p.stl", FAKE_GCODE="\n".join(lines) + "\n")
                self.assertEqual(r.returncode, 1)
                self.assertIn(str(gcode), r.stderr)
                self.assertEqual(r.stdout, "")

    def test_failure_tail(self):
        for rc in ("0", "3"):
            with self.subTest(rc=rc):
                r = self.go("out/p.stl", FAKE_LINES="60", FAKE_RC=rc)
                self.assertEqual(r.returncode, 1)
                self.assertIn("line 21", r.stderr)
                self.assertIn("line 60", r.stderr)
                self.assertNotIn("line 20\n", r.stderr)
                self.assertNotIn("[trace]", r.stderr)
                self.assertIn("fdm-profiles", r.stderr)

    def test_stale_outputs_removed(self):
        self.out.mkdir()
        (self.out / "plate_1.gcode").write_text(GCODE_OK)
        (self.out / "p.3mf").write_text("old")
        (self.out / "keep.txt").write_text("keep")
        r = self.go("out/p.stl")
        self.assertEqual(r.returncode, 1)
        self.assertFalse((self.out / "plate_1.gcode").exists())
        self.assertFalse((self.out / "p.3mf").exists())
        self.assertTrue((self.out / "keep.txt").exists())

    def test_writes_only_in_out(self):
        before = self.snapshot()
        r = self.go("out/p.stl", FAKE_GCODE=GCODE_OK)
        self.assertEqual(r.returncode, 0, r.stderr)
        after = self.snapshot()
        changed = {k for k in after if before.get(k) != after[k]}
        self.assertTrue(changed)
        for k in changed:
            self.assertTrue(Path(k).is_relative_to(self.out), k)

    def assert_clean_failure(self, r, *texts, launched=False):
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        for t in texts:
            self.assertIn(t, r.stderr)
        if not launched:
            self.assertEqual(self.calls(), [])

    def test_no_data_dir(self):
        r = self.go("out/p.stl", data=False)
        self.assert_clean_failure(r, "--data", "CLAUDE_PLUGIN_DATA")

    def test_missing_profile(self):
        for k in ("machine", "process", "filament"):
            with self.subTest(profil=k):
                f = self.data / "profiles" / f"{k}.json"
                f.unlink()
                self.assert_clean_failure(self.go("out/p.stl"), str(f), "fdm-profiles")
                f.write_text("{}")

    def test_bad_stl(self):
        (self.project / "out/d.stl").mkdir()
        (self.project / "out/p.txt").write_text("solid")
        for stl in ("out/none.stl", "out/d.stl", "out/p.txt"):
            with self.subTest(stl=stl):
                self.assert_clean_failure(self.go(stl), stl)

    def test_exe_not_executable(self):
        plain = self.t / "plain"
        plain.write_text("x")
        plain.chmod(0o644)
        for exe in (plain, self.t / "absent"):
            with self.subTest(exe=exe.name):
                r = run("--data", str(self.data), "--bambu-studio", str(exe), "out/p.stl",
                        cwd=self.project, FAKE_LOG=str(self.log))
                self.assert_clean_failure(r, str(exe), "bambu_studio")

    def test_non_macos_requires_exe(self):
        for extra in ([], ["--bambu-studio", ""]):
            with self.subTest(extra=extra):
                r = run("--data", str(self.data), *extra, "out/p.stl", platform="linux",
                        cwd=self.project, FAKE_LOG=str(self.log))
                self.assert_clean_failure(r, "bambu_studio", "--bambu-studio")

    @unittest.skipIf(os.path.exists(MAC_EXE), "vrai Bambu Studio présent")
    def test_macos_default_exe(self):
        r = run("--data", str(self.data), "--bambu-studio", "", "out/p.stl", platform="darwin",
                cwd=self.project, FAKE_LOG=str(self.log))
        self.assert_clean_failure(r, MAC_EXE)

    def test_out_is_a_file(self):
        self.out.write_text("file")
        self.assert_clean_failure(self.go("out/p.stl"), str(self.out))

    @unittest.skipIf(os.geteuid() == 0, "root ignore les permissions")
    def test_out_not_writable(self):
        self.out.mkdir()
        (self.out / "plate_1.gcode").write_text(GCODE_OK)
        self.out.chmod(0o500)
        self.addCleanup(self.out.chmod, 0o700)
        r = self.go("out/p.stl")
        self.assert_clean_failure(r, str(self.out))
        self.assertTrue((self.out / "plate_1.gcode").exists())

    @unittest.skipIf(os.geteuid() == 0, "root ignore les permissions")
    def test_data_not_writable(self):
        for d in (self.data / "profiles", self.data):
            d.chmod(0o500)
            self.addCleanup(d.chmod, 0o700)
        r = self.go("out/p.stl", FAKE_GCODE=GCODE_OK)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_launch_oserror(self):
        bad = self.t / "bad"
        bad.write_bytes(b"\x00\x01\x02\x03binary")
        bad.chmod(0o755)
        r = run("--data", str(self.data), "--bambu-studio", str(bad), "out/p.stl",
                cwd=self.project, FAKE_LOG=str(self.log))
        self.assert_clean_failure(r, str(bad))


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


if __name__ == "__main__":
    unittest.main()
