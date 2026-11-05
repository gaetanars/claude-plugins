import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_sdlc_validate_architecture import write_architecture

sys.dont_write_bytecode = True  # pas de __pycache__ dans plugins/*/bin et lib

RUN = Path(__file__).resolve().parents[1] / "plugins/sdlc-factory/bin/sdlc-run"
loader = importlib.machinery.SourceFileLoader("sdlc_run", str(RUN))
spec = importlib.util.spec_from_loader("sdlc_run", loader)
sdlc_run = importlib.util.module_from_spec(spec)
loader.exec_module(sdlc_run)


def load_script(name, path):
    ld = importlib.machinery.SourceFileLoader(name, str(path))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, ld))
    ld.exec_module(mod)
    return mod


sdlc_retro = load_script("sdlc_retro", RUN.with_name("sdlc-retro"))


class Pure(unittest.TestCase):
    def test_parse_block(self):
        body = "texte\n<!-- sdlc:begin -->\nfeature_id: 0007-x\nspec_sha: abc\ndepends_on_issues: 3,4\n<!-- sdlc:end -->\nfin"
        self.assertEqual(sdlc_run.parse_block(body), {"feature_id": "0007-x", "spec_sha": "abc", "depends_on_issues": "3,4"})
        self.assertIsNone(sdlc_run.parse_block("rien"))
        self.assertIsNone(sdlc_run.parse_block(None))

    def test_adjudicate(self):
        f = lambda s: {"severity": s, "file": "a", "line": 1, "issue": "i", "evidence": "e", "suggestion": ""}
        self.assertEqual(sdlc_run.adjudicate({"verdict": "approve", "findings": []}), ("approve", False))
        self.assertEqual(sdlc_run.adjudicate({"verdict": "approve", "findings": [f("minor")]}), ("approve", False))
        # approve interdit s'il reste blocker/major
        self.assertEqual(sdlc_run.adjudicate({"verdict": "approve", "findings": [f("major")]}), ("changes_requested", True))
        self.assertEqual(sdlc_run.adjudicate({"verdict": "approve", "findings": [f("blocker")]}), ("changes_requested", True))
        self.assertEqual(sdlc_run.adjudicate({"verdict": "changes_requested", "findings": [f("minor")]}), ("changes_requested", False))

    def test_collect_findings(self):
        stored = {
            "security": {"verdict": "changes_requested", "summary": "s", "findings": [
                {"severity": "minor", "file": "a", "line": 1, "issue": "m", "evidence": "", "suggestion": ""},
                {"severity": "blocker", "file": "b", "line": 2, "issue": "B", "evidence": "", "suggestion": ""}]},
            "correctness": {"verdict": "approve", "summary": "ok", "findings": []},
            "simplicity": {"verdict": "changes_requested", "summary": "trop complexe", "findings": []},
        }
        got = sdlc_run.collect_findings(stored)
        self.assertEqual([(g["axis"], g["issue"]) for g in got], [("security", "B"), ("simplicity", "trop complexe")])

    def test_next_adr_number(self):
        d = Path(tempfile.mkdtemp())
        self.assertEqual(sdlc_run.next_adr_number(d), 1)
        (d / "docs/adr").mkdir(parents=True)
        (d / "docs/adr/0003-x.md").write_text("x")
        (d / "docs/adr/readme.md").write_text("x")
        self.assertEqual(sdlc_run.next_adr_number(d), 4)

    def test_slugify_and_questions(self):
        self.assertEqual(sdlc_run.slugify("Choix: Simple / Rapide!"), "choix-simple-rapide")
        self.assertEqual(sdlc_run.slugify("!!!"), "decision")
        q = sdlc_run.format_questions([{"question": "Q ?", "why_blocking": "P"}])
        self.assertIn("**Q1.** Q ?", q)

    def test_read_repos(self):
        self.assertEqual(sdlc_run.read_repos(["a/b"]), [("a/b", False)])
        f = Path(tempfile.mkdtemp()) / "repos"
        f.write_text("# c\na/b\nc/d automerge # opt-in\n\n")
        with mock.patch.dict(os.environ, {"SDLC_REPOS_FILE": str(f)}):
            self.assertEqual(sdlc_run.read_repos([]), [("a/b", False), ("c/d", True)])
            f.write_text("a/b merge-moi\n")
            with self.assertRaises(SystemExit):
                sdlc_run.read_repos([])

    def test_load_check(self):
        d = Path(tempfile.mkdtemp())
        with self.assertRaisesRegex(ValueError, "absent"):
            sdlc_run.load_check(d)
        (d / ".claude").mkdir()
        f = d / ".claude" / "check.json"
        for bad in ("pas du json", '{"check": "", "arch": "x"}', '{"check": "A_RENSEIGNER", "arch": "x"}', '{"check": 3, "arch": "x"}',
                    "[]", "{}", '{"check": "make test"}', '{"check": "make test", "arch": "A_RENSEIGNER"}',
                    '{"check": "make test", "arch": " "}'):
            f.write_text(bad)
            with self.assertRaises(ValueError, msg=bad):
                sdlc_run.load_check(d)
        f.write_text('{"check": " make test ", "arch": "make arch"}')
        self.assertEqual(sdlc_run.load_check(d), {"check": "make test", "arch": "make arch"})

    def test_validate_architecture(self):
        d = Path(tempfile.mkdtemp())
        with self.assertRaises(ValueError):
            sdlc_run.validate_architecture(d)
        write_architecture(d)
        sdlc_run.validate_architecture(d)
        write_architecture(d, status="draft")
        with self.assertRaisesRegex(ValueError, "draft"):
            sdlc_run.validate_architecture(d)

    def test_protected_changes(self):
        d = Path(tempfile.mkdtemp())
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(["git", "init", "-q", str(d)], check=True)
        (d / "a.txt").write_text("1")
        subprocess.run([*g, "-C", str(d), "add", "-A"], check=True)
        subprocess.run([*g, "-C", str(d), "commit", "-qm", "1"], check=True)
        before = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        (d / "a.txt").write_text("2")
        subprocess.run([*g, "-C", str(d), "commit", "-qam", "2"], check=True)
        head = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(sdlc_run.protected_changes(d, before, head), [])
        (d / ".claude").mkdir()
        (d / ".claude" / "check.json").write_text("{}")
        (d / "docs" / "architecture").mkdir(parents=True)
        (d / "docs" / "architecture" / "rules.json").write_text("{}")
        subprocess.run([*g, "-C", str(d), "add", "-A"], check=True)
        subprocess.run([*g, "-C", str(d), "commit", "-qm", "3"], check=True)
        head2 = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(sorted(sdlc_run.protected_changes(d, head, head2)),
                         [".claude/check.json", "docs/architecture/rules.json"])

    def test_run_check(self):
        d = Path(tempfile.mkdtemp())
        with mock.patch.dict(os.environ, {"GH_TOKEN": "x", "ANTHROPIC_API_KEY": "y"}):
            r = sdlc_run.run_check(d, 'test -z "$GH_TOKEN$ANTHROPIC_API_KEY" && echo ok')
            self.assertTrue(r["ok"], r)
            r = sdlc_run.run_check(d, "echo boom >&2; exit 3")
        self.assertEqual((r["ok"], r["code"]), (False, 3))
        self.assertIn("boom", r["tail"])
        with mock.patch.object(sdlc_run, "CHECK_TIMEOUT", 1):
            r = sdlc_run.run_check(d, "sleep 5")
        self.assertEqual((r["ok"], r["code"]), (False, 124))


class RetroCollect(unittest.TestCase):
    def test_collect_reads_default_branch_and_feat_branches(self):
        t = Path(tempfile.mkdtemp())
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]

        def sh(*a, cwd=None):
            r = subprocess.run(a, cwd=cwd, capture_output=True, text=True)
            assert r.returncode == 0, f"{a}\n{r.stderr}"

        def run_files(root, fid, outcome, ended, summary="x"):
            d = root / "docs" / "features" / fid
            (d / "reviews").mkdir(parents=True, exist_ok=True)
            (d / "run.json").write_text(json.dumps({"feature": fid, "outcome": outcome, "ended_at": ended, "iterations": [1],
                                                    "cost_usd_total": 1.5, "duration_s": 3}))
            (d / "reviews" / "abc1234-security.json").write_text(json.dumps({
                "axis": "security", "iteration": 1, "findings": [{"severity": "major", "file": "a.py", "issue": summary}]}))

        remote = t / "remote.git"
        sh("git", "init", "-q", "--bare", "-b", "main", str(remote))
        seed = t / "seed"
        sh("git", "clone", "-q", str(remote), str(seed))
        sh("git", "checkout", "-q", "-b", "main", cwd=seed)
        run_files(seed, "0001-merged", "approved", "2026-02-01T00:00:00")
        run_files(seed, "0003-old", "approved", "2025-01-01T00:00:00")
        sh(*g, "add", "-A", cwd=seed)
        sh(*g, "commit", "-q", "-m", "init", cwd=seed)
        sh("git", "push", "-q", "origin", "main", cwd=seed)
        # run en échec, jamais fusionné : seulement sur sa branche
        sh("git", "checkout", "-q", "-b", "feat/0002-failed", cwd=seed)
        run_files(seed, "0002-failed", "needs-human", "2026-02-02T00:00:00", "secret en clair")
        # même feature sur main (ancien) et sur la branche (plus récent) : le plus récent l'emporte
        run_files(seed, "0001-merged", "needs-human", "2026-02-03T00:00:00")
        sh(*g, "add", "-A", cwd=seed)
        sh(*g, "commit", "-q", "-m", "run", cwd=seed)
        sh("git", "push", "-q", "origin", "feat/0002-failed", cwd=seed)
        work = t / "work"
        (work / "repos").mkdir(parents=True)
        sh("git", "clone", "-q", str(remote), str(work / "repos" / "o__r"))

        with mock.patch.object(sdlc_retro, "WORKDIR", work):
            runs = sdlc_retro.collect(["o/r"], "2026-01-01")
        by = {r["feature"]: r for r in runs}
        self.assertEqual(sorted(by), ["0001-merged", "0002-failed"])  # 0003-old filtré par `since`
        self.assertEqual(by["0002-failed"]["outcome"], "needs-human")
        self.assertEqual(by["0002-failed"]["findings"][0]["issue"], "secret en clair")
        self.assertEqual(by["0001-merged"]["outcome"], "needs-human")  # dédoublonné, le plus récent
        self.assertEqual(len(runs), 2)
        self.assertEqual(by["0002-failed"]["gates_failed"], 0)

    def test_gates_failed(self):
        data = {"iterations": [{"check": {"ok": False}, "arch": {"ok": True}}, {"check": {"ok": True}, "arch": {"ok": False}},
                               {"check": {"ok": True}, "arch": {"ok": True}}, 1]}
        self.assertEqual(sdlc_retro.gates_failed(data), 2)
        self.assertEqual(sdlc_retro.gates_failed({}), 0)


if __name__ == "__main__":
    unittest.main()
