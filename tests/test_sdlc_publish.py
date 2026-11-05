"""sdlc-publish et sdlc-init-repo contre un faux gh et un dépôt git local."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_sdlc_validate_architecture import write_architecture
from tests.test_sdlc_validate_spec import BRIEF, SPEC

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / "plugins/sdlc-framing/bin/sdlc-publish"
INIT = ROOT / "plugins/sdlc-contract/bin/sdlc-init-repo"
FAKEBIN = Path(__file__).parent / "sdlc_fakebin"
G = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]


def sh(*a, cwd=None):
    r = subprocess.run(a, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"{a}\n{r.stderr}"
    return r.stdout.strip()


def feature(proj, fid, title="Hello", depends="[]", brief=True):
    d = proj / "docs/features" / fid
    d.mkdir(parents=True)
    spec = SPEC.replace("0001-hello", fid).replace("title: Hello", f"title: {title}").replace("depends_on: []", f"depends_on: {depends}")
    (d / "spec.md").write_text(spec)
    if brief:
        (d / "brief.md").write_text(BRIEF.replace("0001-hello", fid))


class Publish(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, ignore_errors=True)
        self.remote = self.t / "remote.git"
        sh("git", "init", "-q", "--bare", "-b", "main", str(self.remote))
        seed = self.t / "seed"
        sh("git", "clone", "-q", str(self.remote), str(seed))
        sh("git", "checkout", "-q", "-b", "main", cwd=seed)
        (seed / "CLAUDE.md").write_text("# p\n")
        write_architecture(seed)
        sh(*G, "add", "-A", cwd=seed)
        sh(*G, "commit", "-q", "-m", "init", cwd=seed)
        sh("git", "push", "-q", "origin", "main", cwd=seed)
        self.proj = self.t / "proj"
        sh("git", "clone", "-q", str(self.remote), str(self.proj))
        sh("git", "config", "user.name", "t", cwd=self.proj)
        sh("git", "config", "user.email", "t@t", cwd=self.proj)
        self.state_path = self.t / "state.json"
        self.state_path.write_text(json.dumps({"issues": {}, "prs": {}}))
        self.env = dict(os.environ, PATH=f"{FAKEBIN}{os.pathsep}{os.environ['PATH']}", FAKE_STATE=str(self.state_path))

    def pub(self, *args):
        return subprocess.run([sys.executable, str(PUBLISH), *args], cwd=self.proj, env=self.env, capture_output=True, text=True)

    def state(self):
        return json.loads(self.state_path.read_text())

    def test_next_id(self):
        self.assertEqual(self.pub("next-id", "Export CSV").stdout.strip(), "0001-export-csv")
        feature(self.proj, "0007-x")
        self.assertEqual(self.pub("next-id", "Été à Paris").stdout.strip(), "0008-ete-a-paris")

    def test_publish_pins_sha_and_labels_last(self):
        feature(self.proj, "0001-hello")
        r = self.pub("publish", "0001-hello")
        self.assertEqual(r.returncode, 0, r.stderr)
        issue = self.state()["issues"]["1"]
        self.assertEqual(issue["title"], "[0001-hello] Hello")
        self.assertEqual(issue["labels"], ["ready"])
        head = sh("git", "--git-dir", str(self.remote), "rev-parse", "main")
        self.assertIn(f"spec_sha: {head}", issue["body"])
        self.assertIn("feature_id: 0001-hello", issue["body"])
        self.assertIn("CA-1", issue["body"])
        self.assertIn("schema_version: 2", issue["body"])
        self.assertIn("brief.md](", issue["body"])
        self.assertIn("docs/features/0001-hello/spec.md",
                      sh("git", "--git-dir", str(self.remote), "ls-tree", "-r", "--name-only", "main"))
        again = self.pub("publish", "0001-hello")
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("déjà publié", again.stderr)

    def test_invalid_spec_publishes_nothing(self):
        feature(self.proj, "0001-hello")
        spec = self.proj / "docs/features/0001-hello/spec.md"
        spec.write_text(spec.read_text() + "- [ ] Q2: question ouverte\n")
        r = self.pub("publish", "0001-hello")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("question ouverte", r.stderr)
        self.assertEqual(self.state()["issues"], {})
        self.assertNotIn("0001-hello", sh("git", "--git-dir", str(self.remote), "ls-tree", "-r", "--name-only", "main"))

    def test_publish_without_brief(self):
        feature(self.proj, "0001-hello", brief=False)
        r = self.pub("publish", "0001-hello")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("brief.md", self.state()["issues"]["1"]["body"])

    def test_dependencies_resolved_in_order(self):
        feature(self.proj, "0001-base", title="Base")
        feature(self.proj, "0002-suite", title="Suite", depends="[0001-base]")
        early = self.pub("publish", "0002-suite")
        self.assertNotEqual(early.returncode, 0)
        self.assertIn("non publiée", early.stderr)
        self.assertEqual(self.state()["issues"], {})
        self.assertEqual(self.pub("publish", "0001-base").returncode, 0)
        r = self.pub("publish", "0002-suite")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("depends_on_issues: 1", self.state()["issues"]["2"]["body"])

    def test_architecture_gate(self):
        feature(self.proj, "0001-hello")
        arch = self.proj / "docs/architecture/ARCHITECTURE.md"
        # modifiée mais non commitée : le serveur lit le dépôt
        arch.write_text(arch.read_text() + "\nAjout.\n")
        r = self.pub("publish", "0001-hello")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("non commités", r.stderr)
        sh("git", "checkout", "--", "docs/architecture", cwd=self.proj)
        # draft
        arch.write_text(arch.read_text().replace("status: accepted", "status: draft"))
        sh(*G, "commit", "-qam", "draft", cwd=self.proj)
        r = self.pub("publish", "0001-hello")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("status draft", r.stderr)
        self.assertIn("/sdlc-framing:architect", r.stderr)
        # absente
        sh("git", "rm", "-rq", "docs/architecture", cwd=self.proj)
        sh(*G, "commit", "-qm", "sans architecture", cwd=self.proj)
        r = self.pub("publish", "0001-hello")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("absent", r.stderr)
        self.assertEqual(self.state()["issues"], {})

    def test_refuses_non_default_branch_and_dry_run(self):
        feature(self.proj, "0001-hello")
        dry = self.pub("publish", "0001-hello", "--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(self.state()["issues"], {})
        sh("git", "checkout", "-q", "-b", "autre", cwd=self.proj)
        r = self.pub("publish", "0001-hello")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("branche par défaut", r.stderr)

    def test_init_repo(self):
        r = subprocess.run([sys.executable, str(INIT), "github", "owner/proj", "--ci-context", "build"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("dry-run", r.stdout)
        for label in ("ready", "in-progress", "in-review", "needs-human"):
            self.assertIn(label, r.stdout)
        self.assertNotIn("needs-clarification", r.stdout)
        self.assertIn("allow_auto_merge=false", r.stdout)  # merge toujours humain
        self.assertIn("PR ouverte, en attente de merge", r.stdout)
        body = json.loads(r.stdout.split("<<< ")[1].splitlines()[0])
        self.assertEqual(body["required_status_checks"]["contexts"], ["build"])
        self.assertFalse(body["enforce_admins"])
        # scaffold
        s = subprocess.run([sys.executable, str(INIT), "scaffold"], cwd=self.proj, capture_output=True, text=True)
        self.assertEqual(s.returncode, 0, s.stderr)
        self.assertTrue((self.proj / "docs/adr").is_dir())
        self.assertEqual((self.proj / "CLAUDE.md").read_text(), "# p\n")  # CLAUDE.md existant : inchangé
        fresh = self.t / "fresh"
        sh("git", "init", "-q", str(fresh))
        s = subprocess.run([sys.executable, str(INIT), "scaffold"], cwd=fresh, capture_output=True, text=True)
        self.assertEqual(s.returncode, 0, s.stderr)
        self.assertIn("## Commandes", (fresh / "CLAUDE.md").read_text())
        self.assertTrue((fresh / "docs/features/.gitkeep").exists())
        self.assertIn("# Apprentissages", (fresh / "docs/learnings.md").read_text())
        self.assertEqual(json.loads((fresh / ".claude/check.json").read_text()), {"check": "A_RENSEIGNER", "arch": "A_RENSEIGNER"})
        self.assertIn("check.json créé", s.stdout)
        self.assertIn("/sdlc-framing:architect init", s.stdout)
        # check.json existant : inchangé
        (fresh / ".claude/check.json").write_text('{"check": "make test"}\n')
        s = subprocess.run([sys.executable, str(INIT), "scaffold"], cwd=fresh, capture_output=True, text=True)
        self.assertEqual(json.loads((fresh / ".claude/check.json").read_text()), {"check": "make test"})

    def test_init_repo_has_no_automerge(self):
        r = subprocess.run([sys.executable, str(INIT), "github", "owner/proj", "--automerge"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
