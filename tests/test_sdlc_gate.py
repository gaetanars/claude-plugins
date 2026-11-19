"""sdlc-gate de bout en bout, hors ligne : faux gh, dépôt distant local, clone de travail."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_sdlc_validate_architecture import write_architecture
from tests.test_sdlc_validate_spec import SPEC, STANDARD

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "plugins/sdlc/bin/sdlc-gate"
FAKEBIN = Path(__file__).parent / "sdlc_fakebin"
FID = "0001-hello"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
RUN_TESTS = 'for t in tests/test_*.sh; do [ -e "$t" ] || continue; sh "$t" || exit 1; done\n'
APPROVE = {"verdict": "approve", "summary": "conforme à la spec", "findings": []}
MAJOR = {"axis": "correctness", "severity": "major", "file": "hello.txt", "line": 1,
         "issue": "cas vide non traité", "evidence": "aucun test du cas vide", "suggestion": "ajouter un test"}


def sh(*a, cwd=None, env=None):
    r = subprocess.run([str(x) for x in a], cwd=cwd, capture_output=True, text=True, env=env)
    assert r.returncode == 0, f"{a}\n{r.stderr}"
    return r.stdout.strip()


class Gate(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, ignore_errors=True)
        self.env = dict(os.environ, **IDENT, PATH=f"{FAKEBIN}{os.pathsep}{os.environ['PATH']}",
                        FAKE_STATE=str(self.t / "state.json"))
        Path(self.env["FAKE_STATE"]).write_text(json.dumps({"prs": {}}))
        self.remote = self.t / "remote.git"
        sh("git", "init", "-q", "--bare", "-b", "main", self.remote)
        self.seed = self.t / "seed"
        sh("git", "clone", "-q", self.remote, self.seed)
        sh("git", "checkout", "-q", "-b", "main", cwd=self.seed)
        self.write(self.seed, {"CLAUDE.md": "# p\n", ".claude/check.json": json.dumps({"check": "sh tests/run.sh"}),
                               "tests/run.sh": RUN_TESTS})
        self.push_seed("init")
        self.wt = self.t / "wt"
        sh("git", "clone", "-q", self.remote, self.wt)

    # ------------------------------------------------------------ aides
    def write(self, root, files):
        for path, content in files.items():
            p = Path(root) / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    def push_seed(self, msg):
        sh("git", "add", "-A", cwd=self.seed, env=self.env)
        sh("git", "commit", "-q", "-m", msg, cwd=self.seed, env=self.env)
        sh("git", "push", "-q", "origin", "main", cwd=self.seed)

    def sync(self):
        sh("git", "fetch", "-q", "origin", cwd=self.wt)
        sh("git", "rebase", "-q", "origin/main", cwd=self.wt, env=self.env)

    def with_arch(self, status="accepted", arch_cmd="true"):
        write_architecture(self.seed, status=status)
        self.write(self.seed, {".claude/check.json": json.dumps({"check": "sh tests/run.sh", "arch": arch_cmd})})
        self.push_seed("architecture")
        self.sync()

    def spec(self, text=SPEC):
        self.write(self.wt, {f"docs/features/{FID}/spec.md": text})

    def gate(self, *args, stdin=None):
        return subprocess.run([sys.executable, str(GATE), *args], cwd=self.wt, env=self.env, input=stdin,
                              capture_output=True, text=True)

    def commit(self, msg, files, footer=True):
        self.write(self.wt, files)
        sh("git", "add", "-A", cwd=self.wt, env=self.env)
        sh("git", "commit", "-q", "-m", msg, *(["-m", f"Feature: {FID}"] if footer else []), cwd=self.wt, env=self.env)

    def started(self, text=SPEC):
        self.spec(text)
        r = self.gate("start", FID)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def trivial(self):
        r = self.gate("start", "--trivial", "typo")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def plan(self):
        self.commit(f"docs({FID}): plan", {f"docs/features/{FID}/plan.md": "# Plan\n"})

    def tdd_step(self, msg="hello"):
        self.commit(f"test(hello): {msg}", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        r = self.gate("tests-red")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.commit("feat(hello): ajoute hello.txt", {"hello.txt": "hello\n"})

    def review(self, verdict):
        return self.gate("review", stdin=json.dumps(verdict))

    def branch(self):
        return sh("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=self.wt)

    def refuses(self, *args, fragment):
        r = self.gate(*args)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(fragment, r.stderr)

    # ------------------------------------------------------------ start
    def test_start_feature_commits_spec(self):
        self.with_arch()
        out = self.started()
        self.assertEqual((out["track"], out["id"], out["branch"], out["resumed"], out["architecture"]),
                         ("feature", FID, f"feat/{FID}", False, True))
        self.assertEqual(self.branch(), f"feat/{FID}")
        self.assertEqual(sh("git", "log", "-1", "--format=%s", cwd=self.wt), f"docs({FID}): spec")
        self.assertEqual(sh("git", "status", "--porcelain", cwd=self.wt), "")
        again = self.gate("start", FID)  # reprise
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertTrue(json.loads(again.stdout)["resumed"])

    def test_start_standard_without_architecture(self):
        out = self.started(STANDARD)
        self.assertEqual((out["track"], out["architecture"]), ("standard", False))

    def test_start_refuses_draft_spec(self):
        self.spec(SPEC.replace("status: accepted", "status: draft"))
        self.refuses("start", FID, fragment="acceptée par l'humain")
        self.assertNotEqual(self.branch(), f"feat/{FID}")

    def test_start_feature_requires_accepted_architecture(self):
        self.spec()
        self.refuses("start", FID, fragment="architecture acceptée exigée")
        self.with_arch(status="draft")
        self.refuses("start", FID, fragment="status draft")

    def test_start_refuses_invalid_spec_and_dirty_tree(self):
        self.refuses("start", "0001-nope", fragment="spec.md absent")
        self.spec(SPEC + "- [ ] Q2: question ouverte\n")
        self.refuses("start", FID, fragment="question ouverte")
        self.write(self.wt, {"brouillon.txt": "x"})
        self.spec()
        self.refuses("start", FID, fragment="non propre")

    def test_start_refuses_placeholder_check_and_required_arch(self):
        self.write(self.seed, {".claude/check.json": '{"check": "A_RENSEIGNER"}'})
        self.push_seed("gabarit")
        self.sync()
        self.spec(STANDARD)
        self.refuses("start", FID, fragment="encore au gabarit")
        self.write(self.seed, {".claude/check.json": '{"check": "sh tests/run.sh"}'})
        write_architecture(self.seed)  # architecture acceptée sans `arch` : exigé
        self.push_seed("architecture sans arch")
        self.sync()
        self.refuses("start", FID, fragment='"arch"')

    def test_start_refuses_when_behind_origin(self):
        self.write(self.seed, {"autre.txt": "x"})
        self.push_seed("en avance")
        self.spec(STANDARD)
        self.refuses("start", FID, fragment="pas à jour")

    def test_start_accepts_edited_tracked_spec(self):
        self.write(self.seed, {f"docs/features/{FID}/spec.md": STANDARD.replace("status: accepted", "status: draft")})
        self.push_seed("spec brouillon")
        self.sync()
        self.spec(STANDARD)  # modification non indexée d'un fichier suivi : première ligne de `status` = " M …"
        self.assertEqual(self.gate("start", FID).returncode, 0)

    def test_start_refuses_changed_spec_on_resume(self):
        self.started(STANDARD)
        self.spec(STANDARD.replace("Corriger le contenu", "Réécrire le contenu"))
        self.refuses("start", FID, fragment="spec figée")
        self.assertEqual(sh("git", "log", "--format=%s", cwd=self.wt).count(f"docs({FID}): spec"), 1)

    def test_start_marks_spec_already_on_default_branch(self):
        self.write(self.seed, {f"docs/features/{FID}/spec.md": STANDARD})
        self.push_seed("spec sur main")
        self.sync()
        self.started(STANDARD)
        self.assertEqual(sh("git", "log", "-1", "--format=%s", cwd=self.wt), f"docs({FID}): spec")
        self.plan()
        self.tdd_step()
        r = self.gate("verify")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_spec_commit_independent_of_grep_config(self):
        self.env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="grep.patternType", GIT_CONFIG_VALUE_0="extended")
        self.started(STANDARD)
        self.plan()
        self.tdd_step()
        r = self.gate("verify")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_start_requires_merged_dependencies(self):
        dep = STANDARD.replace("depends_on: []", "depends_on: [0000-base]")
        self.spec(dep)
        self.refuses("start", FID, fragment="0000-base")
        self.write(self.seed, {"docs/features/0000-base/spec.md": "x\n"})
        self.push_seed("base mergée")
        self.sync()
        r = self.gate("start", FID)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_start_trivial(self):
        out = self.trivial()
        self.assertEqual((out["track"], out["branch"]), ("trivial", "fix/typo"))
        self.assertEqual(self.branch(), "fix/typo")
        self.refuses("start", "--trivial", "Pas Un Slug", fragment="invalide")

    # ------------------------------------------------------------ TDD
    def test_tests_red_refuses_green_or_non_test_commit(self):
        self.trivial()
        self.commit("feat(hello): sans test", {"hello.txt": "hello\n"})
        self.refuses("tests-red", fragment="n'est pas un commit test")
        self.commit("test(hello): test déjà vert", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        self.refuses("tests-red", fragment="`check` est vert")

    def test_verify_accepts_tdd_cycle(self):
        self.started(STANDARD)
        self.plan()
        self.tdd_step()
        r = self.gate("verify")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_verify_refuses_feat_without_red_or_without_test(self):
        self.started(STANDARD)
        self.plan()
        self.commit("feat(hello): ajoute hello.txt", {"hello.txt": "hello\n"})
        self.refuses("verify", fragment="non précédé d'un commit test")
        self.commit("test(hello): sans rouge constaté", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        self.commit("feat(hello): encore", {"hello.txt": "hello\n\n"})
        self.refuses("verify", fragment="sans rouge constaté")

    def test_verify_refuses_feat_touching_its_tests(self):
        self.started(STANDARD)
        self.plan()
        self.commit("test(hello): exige hello", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        self.assertEqual(self.gate("tests-red").returncode, 0)
        self.commit("feat(hello): affaiblit le test", {"hello.txt": "x\n", "tests/test_hello.sh": "true\n"})
        self.refuses("verify", fragment="modifie des fichiers du commit de tests")

    def test_verify_tolerates_docs_commit_between_test_and_feat(self):
        self.started(STANDARD)
        self.plan()
        self.commit("test(hello): exige hello", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        self.assertEqual(self.gate("tests-red").returncode, 0)
        self.commit(f"docs({FID}): plan", {f"docs/features/{FID}/plan.md": "# Plan\n\n## Clarifications\nQ/R\n"})
        self.commit("feat(hello): ajoute hello.txt", {"hello.txt": "hello\n"})
        r = self.gate("verify")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_verify_requires_plan_before_tests(self):
        self.started(STANDARD)
        self.refuses("verify", fragment="plan.md non commité")
        self.commit("test(hello): exige hello", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        self.assertEqual(self.gate("tests-red").returncode, 0)
        self.plan()
        self.commit("feat(hello): ajoute hello.txt", {"hello.txt": "hello\n"})
        self.refuses("verify", fragment="commité après le premier commit test")

    def test_verify_refuses_protected_paths_and_modified_spec(self):
        self.with_arch()
        self.started()
        self.plan()
        self.commit("chore: touche le protégé", {"docs/architecture/ARCHITECTURE.md": "x\n", ".github/w.yml": "x\n",
                                                 f"docs/features/{FID}/spec.md": "x\n"})
        r = self.gate("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("chemin protégé modifié : docs/architecture/ARCHITECTURE.md", r.stderr)
        self.assertIn("chemin protégé modifié : .github/w.yml", r.stderr)
        self.assertIn(f"chemin protégé modifié : docs/features/{FID}/spec.md", r.stderr)

    def test_verify_red_check_dirty_tree_and_arch(self):
        self.trivial()
        self.commit("test(hello): exige hello", {"tests/test_hello.sh": 'test "$(cat hello.txt)" = hello\n'})
        self.refuses("verify", fragment="check rouge")
        (self.wt / "brouillon.txt").write_text("x")
        self.refuses("verify", fragment="non propre")
        sh("git", "clean", "-fdq", cwd=self.wt)
        self.with_arch(arch_cmd="false")
        self.refuses("verify", fragment="arch rouge")

    def test_verify_arch_optional_without_architecture(self):
        self.trivial()
        self.commit("docs: note", {"NOTE.md": "x\n"}, footer=False)
        r = self.gate("verify")
        self.assertEqual(r.returncode, 0, r.stderr)

    # ------------------------------------------------------------ revue
    def test_review_requalifies_and_caps_iterations(self):
        self.started(STANDARD)
        self.plan()
        self.tdd_step()
        r = self.review({"verdict": "approve", "summary": "ok", "findings": [MAJOR]})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertTrue(json.loads(r.stdout)["adjusted"])
        for i in (2, 3):
            self.commit(f"fix(hello): correction {i}", {"hello.txt": f"hello {i}\n"})
            r = self.review({"verdict": "changes_requested", "summary": f"toujours faux {i}", "findings": [MAJOR]})
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("l'humain tranche", r.stderr)

    def test_review_rejects_invalid_verdict(self):
        self.trivial()
        r = self.review({"verdict": "approve", "summary": "ok", "findings": [{"severity": "minor", "issue": "x"}]})
        self.assertEqual(r.returncode, 1)
        self.assertIn("finding invalide", r.stderr)
        sans_ligne = {k: v for k, v in MAJOR.items() if k not in ("file", "line")}
        r = self.review({"verdict": "changes_requested", "summary": "x", "findings": [sans_ligne]})
        self.assertEqual(r.returncode, 1)
        self.assertIn("finding invalide", r.stderr)

    # ------------------------------------------------------------ livraison
    def test_deliver_feature(self):
        self.started(STANDARD)
        self.plan()
        self.tdd_step()
        self.assertEqual(self.review(APPROVE).returncode, 0)
        self.commit(f"docs({FID}): apprentissages", {"docs/learnings.md": "- 2026-11-05 [0001-hello] x → y\n"})
        r = self.gate("deliver")
        self.assertEqual(r.returncode, 0, r.stderr)
        pr = json.loads(Path(self.env["FAKE_STATE"]).read_text())["prs"]["1"]
        self.assertEqual((pr["head"], pr["base"], pr["title"]), (f"feat/{FID}", "main", "Hello"))
        self.assertNotIn("Closes", pr["body"])
        self.assertIn("| correctness | 0 | 0 | 0 |", pr["body"])
        self.assertEqual(sh("git", "--git-dir", self.remote, "rev-parse", f"feat/{FID}"), sh("git", "rev-parse", "HEAD", cwd=self.wt))
        again = self.gate("deliver")  # idempotent : pas de seconde PR
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(len(json.loads(Path(self.env["FAKE_STATE"]).read_text())["prs"]), 1)

    def test_deliver_trivial(self):
        self.trivial()
        self.commit("fix: corrige la coquille", {"README.md": "ok\n"}, footer=False)
        self.assertEqual(self.review(APPROVE).returncode, 0)
        r = self.gate("deliver")
        self.assertEqual(r.returncode, 0, r.stderr)
        pr = json.loads(Path(self.env["FAKE_STATE"]).read_text())["prs"]["1"]
        self.assertEqual((pr["head"], pr["title"]), ("fix/typo", "fix: corrige la coquille"))

    def test_deliver_requires_approved_review_of_last_code(self):
        self.trivial()
        self.commit("fix: a", {"a.txt": "a\n"}, footer=False)
        self.refuses("deliver", fragment="aucun verdict")
        self.assertEqual(self.review(APPROVE).returncode, 0)
        self.commit("fix: après la revue", {"a.txt": "b\n"}, footer=False)
        self.refuses("deliver", fragment="postérieurs à la revue")
        self.assertEqual(json.loads(Path(self.env["FAKE_STATE"]).read_text())["prs"], {})


if __name__ == "__main__":
    unittest.main()
