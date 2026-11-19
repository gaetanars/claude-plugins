"""sdlc-init-repo (dry-run `github`, `scaffold`) et sdlc-next-id."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "plugins/sdlc/bin/sdlc-init-repo"
NEXT_ID = ROOT / "plugins/sdlc/bin/sdlc-next-id"


def run(script, *args, cwd=None):
    return subprocess.run([sys.executable, str(script), *args], cwd=cwd, capture_output=True, text=True)


class InitRepo(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, ignore_errors=True)
        subprocess.run(["git", "init", "-q", str(self.t)], check=True)

    def test_next_id(self):
        self.assertEqual(run(NEXT_ID, "Export CSV", cwd=self.t).stdout.strip(), "0001-export-csv")
        (self.t / "docs/features/0007-x").mkdir(parents=True)
        self.assertEqual(run(NEXT_ID, "Été à Paris", cwd=self.t).stdout.strip(), "0008-ete-a-paris")

    def test_next_id_reserves_ids_of_open_feature_branches(self):
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"], cwd=self.t, check=True, env={**__import__("os").environ, **env})
        subprocess.run(["git", "branch", "feat/0003-en-cours"], cwd=self.t, check=True)
        self.assertEqual(run(NEXT_ID, "suite", cwd=self.t).stdout.strip(), "0004-suite")

    def test_github_dry_run_without_labels(self):
        r = run(INIT, "github", "owner/proj", "--ci-context", "build")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("dry-run", r.stdout)
        self.assertNotIn("label", r.stdout)
        self.assertIn("allow_auto_merge=false", r.stdout)  # merge toujours humain
        body = json.loads(r.stdout.split("<<< ")[1].splitlines()[0])
        self.assertEqual(body["required_status_checks"]["contexts"], ["build"])
        self.assertFalse(body["enforce_admins"])
        self.assertNotEqual(run(INIT, "github", "owner/proj", "--automerge").returncode, 0)

    def test_scaffold(self):
        (self.t / "CLAUDE.md").write_text("# p\n")
        s = run(INIT, "scaffold", cwd=self.t)
        self.assertEqual(s.returncode, 0, s.stderr)
        self.assertEqual((self.t / "CLAUDE.md").read_text(), "# p\n")  # CLAUDE.md existant : inchangé
        self.assertTrue((self.t / "docs/adr").is_dir())
        self.assertTrue((self.t / "docs/features/.gitkeep").exists())
        self.assertIn("# Apprentissages", (self.t / "docs/learnings.md").read_text())
        self.assertEqual(json.loads((self.t / ".claude/check.json").read_text()), {"check": "A_RENSEIGNER"})
        self.assertIn("facultatif", s.stdout)
        (self.t / ".claude/check.json").write_text('{"check": "make test"}\n')
        run(INIT, "scaffold", cwd=self.t)
        self.assertEqual(json.loads((self.t / ".claude/check.json").read_text()), {"check": "make test"})


if __name__ == "__main__":
    unittest.main()
