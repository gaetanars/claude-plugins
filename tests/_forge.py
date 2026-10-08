"""Banc d'essai de forge.py : dépôt git temporaire, remote nu local, `gh` factice, JUnit contrôlé."""
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._common import ROOT

PLUGIN = ROOT / "plugins" / "tdd-forge"
FORGE = PLUGIN / "skills" / "installer" / "assets" / "forge.py"
GUARD = PLUGIN / "scripts" / "guard.py"

FAKE_TESTS = """\
import os, shutil, sys
from pathlib import Path
Path('.forge/out').mkdir(parents=True, exist_ok=True)
src = Path(os.environ['FAKE_JUNIT'])
shutil.copy(src, '.forge/out/junit.xml')
sys.exit(1 if '<failure' in src.read_text() else 0)
"""

FAKE_GH = """\
#!/usr/bin/env python3
import os, sys
with open(os.environ['GH_LOG'], 'a') as f:
    f.write(' '.join(sys.argv[1:]) + '\\n')
a = sys.argv[1:3]
if a == ['pr', 'view']:
    sys.exit(1)
if a == ['pr', 'create']:
    print('https://github.com/x/y/pull/1')
if a == ['issue', 'create']:
    print('https://github.com/x/y/issues/9')
"""


def junit(*cases):
    """cases : (nom, échec ?) → contenu JUnit."""
    body = "".join(f'<testcase classname="t" name="{n}">{"<failure message=\"ko\"/>" if bad else ""}</testcase>'
                   for n, bad in cases)
    return f'<testsuites><testsuite name="s">{body}</testsuite></testsuites>'


def sh(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **kw)


class ForgeCase(unittest.TestCase):
    CONFIG = {
        "version": 1, "stack": "test", "default_branch": "main", "remote": "origin",
        "test_globs": ["tests/*"], "acceptance_dir": "tests/acceptance",
        "junit_path": ".forge/out/junit.xml", "suppression_markers": ["# noqa"],
        "max_pr_lines": 400, "stall_rounds": 2, "merge_method": "squash",
    }

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.repo, self.origin, bindir = self.tmp / "repo", self.tmp / "origin.git", self.tmp / "bin"
        for d in (self.repo, bindir):
            d.mkdir()
        sh(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], self.tmp)
        sh(["git", "init", "-q", "-b", "main"], self.repo)
        for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
            sh(["git", "config", k, v], self.repo)
        self.fake = self.tmp / "fake_tests.py"
        self.fake.write_text(FAKE_TESTS)
        cmd = f"python3 {self.fake}"
        cfg = {**self.CONFIG, "test_cmd": cmd, "gates": [{"name": "tests", "cmd": cmd, "tests": True}]}
        (self.repo / ".forge").mkdir()
        (self.repo / ".forge" / "config.json").write_text(json.dumps(cfg))
        (self.repo / ".gitignore").write_text(".forge/worktrees/\n.forge/backlog/\n.forge/out/\n.forge/current\n")
        (self.repo / "README.md").write_text("x\n")
        sh(["git", "add", "-A"], self.repo)
        sh(["git", "commit", "-qm", "init"], self.repo)
        sh(["git", "remote", "add", "origin", str(self.origin)], self.repo)
        sh(["git", "push", "-q", "-u", "origin", "main"], self.repo)
        gh = bindir / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.ghlog = self.tmp / "gh.log"
        self.env = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "GH_LOG": str(self.ghlog)}
        self.set_junit()

    def set_junit(self, *cases):
        f = self.tmp / "junit.xml"
        f.write_text(junit(*cases))
        self.env["FAKE_JUNIT"] = str(f)

    def spec(self, task="T001", acs=("AC-1",), extra="", validated=True, deps=""):
        d = self.repo / ".forge" / "backlog" / task
        d.mkdir(parents=True, exist_ok=True)
        crit = "\n".join(f"- {a} — critère" for a in acs)
        (d / "spec.md").write_text(
            f"---\nid: {task}\ntitle: Titre {task}\nvalidated: {str(validated).lower()}\n"
            f"depends_on: [{deps}]\n---\n\n## Critères d'acceptation\n\n{crit}\n{extra}")
        return d

    def forge(self, *args, cwd=None):
        p = subprocess.run(["python3", str(FORGE), *map(str, args)], cwd=cwd or self.repo,
                           capture_output=True, text=True, env=self.env)
        try:
            return json.loads(p.stdout)
        except json.JSONDecodeError:
            self.fail(f"sortie non JSON ({p.returncode}) : {p.stdout!r} {p.stderr!r}")

    def wt(self, task="T001"):
        return self.repo / ".forge" / "worktrees" / task

    def write(self, rel, text="x\n", task="T001"):
        f = self.wt(task) / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
        return f

    def to_red(self, task="T001"):
        """Amène la tâche à la phase rouge validée."""
        self.assertTrue(self.forge("start", task)["ok"])
        (self.repo / ".forge" / "backlog" / task / "plan.md").write_text("plan")
        self.write("tests/acceptance/test_a.py", "# AC-1\n", task)
        self.set_junit(("test_ac_1", True))
        r = self.forge("red", task)
        self.assertTrue(r["ok"], r)
