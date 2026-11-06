"""sdlc-gate de bout en bout, hors ligne : faux gh, dépôt distant local, worktree simulant celui d'Orca."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_sdlc_validate_architecture import write_architecture
from tests.test_sdlc_validate_spec import SPEC

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "plugins/sdlc-factory/bin/sdlc-gate"
FAKEBIN = Path(__file__).parent / "sdlc_fakebin"
FID = "0001-hello"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
RUN_TESTS = 'for t in tests/test_*.sh; do [ -e "$t" ] || continue; sh "$t" || exit 1; done\n'
APPROVE = {"verdict": "approve", "summary": "conforme à la spec", "findings": []}


def sh(*a, cwd=None, env=None):
    r = subprocess.run([str(x) for x in a], cwd=cwd, capture_output=True, text=True, env=env)
    assert r.returncode == 0, f"{a}\n{r.stderr}"
    return r.stdout.strip()


def block(sha, deps="", schema="2"):
    return (f"Résumé\n\n<!-- sdlc:begin -->\nfeature_id: {FID}\nspec_path: docs/features/{FID}/spec.md\n"
            f"spec_sha: {sha}\nschema_version: {schema}\ndepends_on_issues: {deps}\n<!-- sdlc:end -->\n")


class Gate(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, ignore_errors=True)
        self.env = dict(os.environ, **IDENT, PATH=f"{FAKEBIN}{os.pathsep}{os.environ['PATH']}",
                        FAKE_STATE=str(self.t / "state.json"))
        self.remote = self.t / "remote.git"
        sh("git", "init", "-q", "--bare", "-b", "main", self.remote)
        self.seed = self.t / "seed"
        sh("git", "clone", "-q", self.remote, self.seed)
        sh("git", "checkout", "-q", "-b", "main", cwd=self.seed)
        write_architecture(self.seed)
        self.write(self.seed, {
            "CLAUDE.md": "# p\n",
            ".claude/check.json": json.dumps({"check": "sh tests/run.sh", "arch": "true"}),
            "tests/run.sh": RUN_TESTS,
            f"docs/features/{FID}/spec.md": SPEC,
        })
        self.sha = self.push_seed("cadrage")
        self.state = {"issues": {"1": {"title": f"[{FID}] Hello", "body": block(self.sha), "labels": ["ready"],
                                       "state": "OPEN", "comments": []}}, "prs": {}}
        self.save()
        base = self.t / "base"
        sh("git", "clone", "-q", self.remote, base)
        self.wt = self.t / "wt"
        sh("git", "-C", base, "worktree", "add", "-q", "-b", "orca/run-1", self.wt, "origin/main")

    # ------------------------------------------------------------ aides
    def write(self, root, files):
        for path, content in files.items():
            p = Path(root) / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    def push_seed(self, msg):
        sh("git", "add", "-A", cwd=self.seed, env=self.env)
        sh("git", "commit", "-q", "-m", msg, cwd=self.seed, env=self.env)
        sh("git", "push", "-q", "origin", "main", cwd=self.seed, env=self.env)
        return sh("git", "rev-parse", "HEAD", cwd=self.seed)

    def save(self):
        Path(self.env["FAKE_STATE"]).write_text(json.dumps(self.state))

    def load(self):
        self.state = json.loads(Path(self.env["FAKE_STATE"]).read_text())
        return self.state

    def gate(self, *args, stdin=None):
        return subprocess.run([sys.executable, str(GATE), *args], cwd=self.wt, env=self.env, input=stdin,
                              capture_output=True, text=True)

    def commit(self, msg, files):
        self.write(self.wt, files)
        sh("git", "add", "-A", cwd=self.wt, env=self.env)
        sh("git", "commit", "-q", "-m", msg, "-m", f"Feature: {FID}", cwd=self.wt, env=self.env)

    def labels(self, n="1"):
        return self.load()["issues"][n]["labels"]

    def started(self):
        r = self.gate("start")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def tdd_step(self):
        self.commit("test(hello): hello.txt contient hello", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        r = self.gate("tests-red")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.commit("feat(hello): ajoute hello.txt", {"hello.txt": "hello\n"})

    def review(self, verdict):
        return self.gate("review", stdin=json.dumps(verdict))

    # ------------------------------------------------------------ next
    def test_next(self):
        self.assertEqual(self.gate("next", "--repo", "owner/proj").returncode, 0)
        self.state["issues"]["1"]["body"] = block(self.sha, deps="2")
        self.state["issues"]["2"] = {"title": "[0000-base] Base", "body": "", "labels": [], "state": "OPEN", "comments": []}
        self.save()
        self.assertEqual(self.gate("next", "--repo", "owner/proj").returncode, 1)  # dépendance ouverte
        self.state["issues"]["2"]["state"] = "CLOSED"
        self.save()
        self.assertEqual(self.gate("next", "--repo", "owner/proj").returncode, 0)
        self.state["issues"]["2"]["labels"] = ["in-progress"]
        self.state["issues"]["2"]["state"] = "OPEN"
        self.save()
        self.assertEqual(self.gate("next", "--repo", "owner/proj").returncode, 1)  # une seule issue à la fois

    # ------------------------------------------------------------ start
    def test_start(self):
        out = self.started()
        self.assertEqual((out["issue"], out["feature"], out["branch"]), (1, FID, f"feat/{FID}"))
        self.assertFalse(out["resumed"])
        self.assertEqual(sh("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=self.wt), f"feat/{FID}")
        self.assertEqual(self.labels(), ["in-progress"])
        self.assertEqual(self.gate("start").returncode, 1)  # déjà une issue in-progress

    def test_start_nothing_to_do(self):
        self.state["issues"]["1"]["labels"] = []
        self.save()
        r = self.gate("start")
        self.assertEqual(r.returncode, 1)
        self.assertIn("rien à traiter", r.stdout)

    def escalated(self, fragment):
        r = self.gate("start")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.labels(), ["needs-human"])
        self.assertIn(fragment, self.state["issues"]["1"]["comments"][-1]["body"])

    def test_start_escalates_on_invalid_block(self):
        self.state["issues"]["1"]["body"] = "pas de bloc"
        self.save()
        self.escalated("sdlc:begin")

    def test_start_escalates_on_old_schema(self):
        self.state["issues"]["1"]["body"] = block(self.sha, schema="1")
        self.save()
        self.escalated("schema_version")

    def test_start_escalates_when_spec_changed_after_publication(self):
        self.write(self.seed, {f"docs/features/{FID}/spec.md": SPEC.replace("Hello", "Hello modifié")})
        self.push_seed("spec modifiée")
        self.escalated("a changé depuis sa publication")

    def test_start_escalates_on_draft_architecture(self):
        arch = self.seed / "docs/architecture/ARCHITECTURE.md"
        arch.write_text(arch.read_text().replace("status: accepted", "status: draft"))
        self.push_seed("draft")
        self.escalated("status draft")

    def test_start_escalates_on_placeholder_check(self):
        self.write(self.seed, {".claude/check.json": '{"check": "A_RENSEIGNER", "arch": "true"}'})
        self.push_seed("gabarit")
        self.escalated("encore au gabarit")

    # ------------------------------------------------------------ TDD
    def test_tests_red_refuses_green_or_non_test_commit(self):
        self.started()
        self.commit("feat(hello): sans test", {"hello.txt": "hello\n"})
        r = self.gate("tests-red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("n'est pas un commit test", r.stderr)
        self.commit("test(hello): test déjà vert", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        r = self.gate("tests-red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("`check` est vert", r.stderr)

    def test_verify_accepts_tdd_cycle(self):
        self.started()
        self.tdd_step()
        r = self.gate("verify")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_verify_refuses_feat_without_red_test(self):
        self.started()
        self.commit("test(hello): test sans rouge constaté", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        self.commit("feat(hello): ajoute hello.txt", {"hello.txt": "hello\n"})
        r = self.gate("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("sans rouge constaté", r.stderr)

    def test_verify_refuses_feat_not_preceded_by_test(self):
        self.started()
        self.commit("feat(hello): ajoute hello.txt", {"hello.txt": "hello\n"})
        r = self.gate("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("non précédé d'un commit test", r.stderr)

    def test_verify_refuses_feat_touching_its_tests(self):
        self.started()
        self.commit("test(hello): exige hello", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        self.assertEqual(self.gate("tests-red").returncode, 0)
        self.commit("feat(hello): affaiblit le test", {"hello.txt": "x\n", "tests/test_hello.sh": "true\n"})
        r = self.gate("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("modifie des fichiers du commit de tests", r.stderr)

    def test_verify_refuses_protected_paths_and_red_check(self):
        self.started()
        self.commit("chore: touche l'architecture", {"docs/architecture/ARCHITECTURE.md": "x\n",
                                                     f"docs/features/{FID}/spec.md": "x\n"})
        self.commit("test(hello): exige hello", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        r = self.gate("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("chemin protégé modifié : docs/architecture/ARCHITECTURE.md", r.stderr)
        self.assertIn(f"chemin protégé modifié : docs/features/{FID}/spec.md", r.stderr)
        self.assertIn("check rouge", r.stderr)

    def test_verify_refuses_dirty_tree(self):
        self.started()
        (self.wt / "brouillon.txt").write_text("x")
        r = self.gate("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("non propre", r.stderr)

    # ------------------------------------------------------------ revue
    def test_review_requalifies_and_caps_iterations(self):
        self.started()
        self.tdd_step()
        major = {"axis": "correctness", "severity": "major", "file": "hello.txt", "line": 1,
                 "issue": "cas vide non traité", "evidence": "aucun test du cas vide", "suggestion": "ajouter un test"}
        r = self.review({"verdict": "approve", "summary": "ok", "findings": [major]})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertTrue(json.loads(r.stdout)["adjusted"])
        for i in (2, 3):
            self.commit(f"fix(hello): correction {i}", {"hello.txt": f"hello {i}\n"})
            r = self.review({"verdict": "changes_requested", "summary": f"toujours faux {i}", "findings": [major]})
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("needs-human", self.labels())
        self.assertIn(f"feat/{FID}", sh("git", "--git-dir", self.remote, "branch", "--list", f"feat/{FID}"))

    def test_review_rejects_invalid_verdict(self):
        self.started()
        r = self.review({"verdict": "approve", "summary": "ok", "findings": [{"severity": "minor", "issue": "x"}]})
        self.assertEqual(r.returncode, 1)
        self.assertIn("finding invalide", r.stderr)

    # ------------------------------------------------------------ livraison
    def test_deliver_happy_path(self):
        self.started()
        self.commit(f"docs({FID}): plan", {f"docs/features/{FID}/plan.md": "# Plan\n"})
        self.tdd_step()
        self.assertEqual(self.review(APPROVE).returncode, 0)
        self.commit(f"docs({FID}): apprentissages", {"docs/learnings.md": "- 2026-11-05 [0001-hello] x → y\n"})
        r = self.gate("deliver")
        self.assertEqual(r.returncode, 0, r.stderr)
        st = self.load()
        pr = st["prs"]["1"]
        self.assertEqual(pr["head"], f"feat/{FID}")
        self.assertIn("Closes #1", pr["body"])
        self.assertIn("| correctness | 0 | 0 | 0 |", pr["body"])
        self.assertEqual(st["issues"]["1"]["labels"], ["in-review"])
        head = sh("git", "rev-parse", "HEAD", cwd=self.wt)
        self.assertEqual(sh("git", "--git-dir", self.remote, "rev-parse", f"feat/{FID}"), head)

    def test_deliver_requires_approved_review_of_last_code(self):
        self.started()
        self.tdd_step()
        r = self.gate("deliver")
        self.assertEqual(r.returncode, 1)
        self.assertIn("aucun verdict", r.stderr)
        self.assertEqual(self.review(APPROVE).returncode, 0)
        self.commit("fix(hello): après la revue", {"hello.txt": "hello\n\n"})
        r = self.gate("deliver")
        self.assertEqual(r.returncode, 1)
        self.assertIn("postérieurs à la revue", r.stderr)
        self.assertEqual(self.load()["prs"], {})

    def test_escalate(self):
        self.started()
        self.commit(f"docs({FID}): plan", {f"docs/features/{FID}/plan.md": "# Plan\n"})
        r = self.gate("escalate", "décision structurante : nouvelle base de données")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.labels(), ["needs-human"])
        self.assertIn("nouvelle base de données", self.state["issues"]["1"]["comments"][-1]["body"])
        self.assertTrue(sh("git", "--git-dir", self.remote, "branch", "--list", f"feat/{FID}"))


if __name__ == "__main__":
    unittest.main()
