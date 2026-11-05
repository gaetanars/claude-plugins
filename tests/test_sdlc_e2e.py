"""Bout en bout hors ligne : sdlc-run contre un faux gh (état JSON), un faux claude (scénarios) et un dépôt git local."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_sdlc_validate_architecture import write_architecture

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "plugins/sdlc-factory/bin/sdlc-run"
FAKEBIN = Path(__file__).parent / "sdlc_fakebin"
REPO = "owner/proj"
CHECK = "test -f hello.txt && ! grep -q BAD hello.txt"  # vert dès que l'implementer a écrit hello.txt sans marqueur BAD
ARCH = "! grep -q FORBIDDEN hello.txt"  # « règle d'architecture » factice
FID = "0001-hello"

SPEC = f"""---
schema_version: 1
id: {FID}
title: Hello
status: ready
depends_on: []
---

# Hello

## Contexte
Ajouter un fichier hello.txt pour valider le flux de bout en bout.

## Périmètre
- Créer hello.txt avec une ligne de contenu.

## Hors périmètre
- Toute autre fonctionnalité.

## Critères d'acceptation
- [ ] CA-1: Le fichier hello.txt existe à la racine et contient au moins une ligne.

## Contraintes
Aucune dépendance externe, fichier texte brut.
"""
BRIEF = f"""---
schema_version: 1
id: {FID}
title: Hello
---

# Brief : Hello

## Problème
Valider le flux de bout en bout du SDLC sur un cas minimal.

## Valeur
Confiance dans l'automate avant usage réel.
"""
AMB = f"""---
schema_version: 1
id: {FID}
---

# Ambiguïtés levées

- [x] Q1: Quel contenu ? → R: Une ligne libre (2026-11-04)
"""


def sh(*a, cwd=None, env=None):
    r = subprocess.run(a, cwd=cwd, env=env, capture_output=True, text=True)
    assert r.returncode == 0, f"{a}\n{r.stderr}"
    return r.stdout.strip()


class E2E(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, ignore_errors=True)
        self.remote = self.t / "remote.git"
        sh("git", "init", "-q", "--bare", "-b", "main", str(self.remote))
        seed = self.t / "seed"
        sh("git", "clone", "-q", str(self.remote), str(seed))
        sh("git", "checkout", "-q", "-b", "main", cwd=seed)
        fdir = seed / "docs" / "features" / FID
        fdir.mkdir(parents=True)
        (seed / "CLAUDE.md").write_text("# proj\n## Commandes\n- Tests : `true`\n")
        (seed / ".claude").mkdir()
        (seed / ".claude" / "check.json").write_text(json.dumps({"check": CHECK, "arch": ARCH}))
        write_architecture(seed)
        for n, t in (("spec", SPEC), ("brief", BRIEF), ("ambiguities", AMB)):
            (fdir / f"{n}.md").write_text(t, encoding="utf-8")
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        sh(*g, "add", "-A", cwd=seed)
        sh(*g, "commit", "-q", "-m", "init", cwd=seed)
        sh("git", "push", "-q", "origin", "main", cwd=seed)
        self.sha = sh("git", "rev-parse", "HEAD", cwd=seed)

        body = (f"## Résumé\nx\n<!-- sdlc:begin -->\nfeature_id: {FID}\nspec_path: docs/features/{FID}/spec.md\n"
                f"spec_sha: {self.sha}\nschema_version: 1\ndepends_on_issues: \n<!-- sdlc:end -->\n")
        self.state_path = self.t / "state.json"
        self.state_path.write_text(json.dumps({"issues": {"1": {"title": f"[{FID}] Hello", "body": body, "labels": ["ready"],
                                                                "state": "OPEN", "comments": []}}, "prs": {}, "statuses": []}))
        self.cdir = self.t / "claude"
        self.cdir.mkdir()
        (self.t / "repos").write_text(REPO + "\n")
        self.scenario("approve_all")
        self.env = dict(os.environ, PATH=f"{FAKEBIN}{os.pathsep}{os.environ['PATH']}", FAKE_STATE=str(self.state_path),
                        FAKE_REMOTE=str(self.remote), FAKE_CLAUDE_DIR=str(self.cdir), SDLC_WORKDIR=str(self.t / "work"),
                        SDLC_REPOS_FILE=str(self.t / "repos"), PYTHONDONTWRITEBYTECODE="1", GH_TOKEN="topsecret", SDLC_HOME=str(ROOT))

    # -- helpers
    def scenario(self, s):
        (self.cdir / "scenario").write_text(s)

    def run_sdlc(self, *extra, **env):
        return subprocess.run([sys.executable, str(RUN), *extra], env={**self.env, **env}, capture_output=True, text=True)

    def state(self):
        return json.loads(self.state_path.read_text())

    def calls(self, agent=None):
        p = self.cdir / "calls.jsonl"
        rows = [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        return [r for r in rows if agent is None or r["agent"] == agent]

    def branch_files(self):
        return sh("git", "--git-dir", str(self.remote), "ls-tree", "-r", "--name-only", f"feat/{FID}").splitlines()

    def branch_file(self, path):
        return sh("git", "--git-dir", str(self.remote), "show", f"feat/{FID}:{path}")

    def run_json(self):
        return json.loads(self.branch_file(f"docs/features/{FID}/run.json"))

    def push_seed(self, mutate):
        """Applique `mutate(seed)` puis pousse sur la branche par défaut du dépôt distant."""
        seed = self.t / "seed"
        mutate(seed)
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        sh(*g, "add", "-A", cwd=seed)
        sh(*g, "commit", "-q", "-m", "maj", cwd=seed)
        sh("git", "push", "-q", "origin", "main", cwd=seed)

    def push_check(self, cmd, arch=ARCH):
        """Remplace (ou supprime si cmd est None) .claude/check.json."""
        def mutate(seed):
            f = seed / ".claude" / "check.json"
            if cmd is None:
                f.unlink()
            else:
                f.write_text(json.dumps({k: v for k, v in (("check", cmd), ("arch", arch)) if v is not None}))
        self.push_seed(mutate)

    # -- scénarios
    def test_happy_path(self):
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 0, r.stderr)
        st = self.state()
        self.assertEqual(st["issues"]["1"]["labels"], ["in-review"])
        pr = st["prs"]["1"]
        self.assertIn("Closes #1", pr["body"])
        self.assertFalse(pr["automerge"], "merge humain par défaut")
        self.assertIn("merge humain", pr["body"])
        self.assertIn("à fusionner", st["issues"]["1"]["comments"][-1]["body"])
        self.assertEqual(pr["head"], f"feat/{FID}")
        self.assertEqual(len(st["statuses"]), 1)
        self.assertIn("context=sdlc/verdicts", st["statuses"][0]["fields"])
        self.assertIn("state=success", st["statuses"][0]["fields"])

        files = self.branch_files()
        base = f"docs/features/{FID}"
        for f in ("plan.md", "run.json", "spec.md", "brief.md", "ambiguities.md"):
            self.assertIn(f"{base}/{f}", files)
        self.assertIn("docs/adr/0001-choix-simple.md", files)
        self.assertIn("hello.txt", files)
        self.assertEqual(len([f for f in files if f.startswith(f"{base}/reviews/")]), 3)
        rj = self.run_json()
        self.assertEqual(rj["outcome"], "approved")
        self.assertEqual(len(rj["iterations"]), 1)
        self.assertTrue(rj["iterations"][0]["check"]["ok"])
        self.assertGreater(rj["cost_usd_total"], 0)
        self.assertEqual(rj["calls"][0]["subtype"], "success")
        self.assertEqual(rj["calls"][0]["permission_denials"], 0)

        # traçabilité des commits
        log = sh("git", "--git-dir", str(self.remote), "log", "--format=%B", f"feat/{FID}")
        self.assertIn(f"Feature: {FID}", log)

        # appels d'agents : bons noms, plugins, schéma, rôles, jamais de jeton
        self.assertEqual([c["agent"] for c in self.calls()][:2], ["planner", "implementer"])
        self.assertEqual(len(self.calls("reviewer-correctness")) + len(self.calls("reviewer-security"))
                         + len(self.calls("reviewer-simplicity")), 3)
        for c in self.calls():
            self.assertFalse(c["has_gh_token"], "le jeton GitHub ne doit jamais atteindre l'agent")
            self.assertEqual(c["argv"].count("--plugin-dir"), 2)
            self.assertIn("--json-schema", c["argv"])
            argv = c["argv"]
            self.assertEqual(argv[argv.index("--setting-sources") + 1], "user")
            self.assertEqual(argv[argv.index("--permission-mode") + 1], "dontAsk")
            self.assertGreater(int(argv[argv.index("--max-turns") + 1]), 0)
            sb = json.loads(argv[argv.index("--settings") + 1])["sandbox"]
            self.assertTrue(sb["enabled"] and sb["failIfUnavailable"])
            self.assertFalse(sb["allowUnsandboxedCommands"])
            self.assertIn("pypi.org", sb["network"]["allowedDomains"])
            self.assertIn(c["worktree"], sb["filesystem"]["allowWrite"])
            self.assertEqual(Path(c["cwd"]).resolve(), Path(c["worktree"]).resolve())
        roles = {c["agent"]: c["role"] for c in self.calls()}
        self.assertEqual(roles["planner"], "planner")
        self.assertEqual(roles["reviewer-security"], "reviewer")
        impl = self.calls("implementer")[0]["argv"]
        self.assertEqual(impl[impl.index("--allowedTools") + 1], "Read,Edit,Write,Grep,Glob,Bash")
        rev = self.calls("reviewer-security")[0]["argv"]
        tools = rev[rev.index("--allowedTools") + 1]
        self.assertIn("Bash(git diff *)", tools)
        self.assertNotIn("Bash,", tools + ",")
        # le .git du clone de base est inscriptible (git commit dans un worktree)
        sb = json.loads(impl[impl.index("--settings") + 1])["sandbox"]
        self.assertTrue(any(w.endswith("owner__proj/.git") for w in sb["filesystem"]["allowWrite"]), sb["filesystem"])
        self.assertIn("Check exécuté par l'orchestrateur", self.calls("reviewer-security")[0]["prompt"])

    def test_reject_once_then_fix(self):
        self.scenario("reject_once")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 0, r.stderr)
        rj = self.run_json()
        self.assertEqual(len(rj["iterations"]), 2)
        self.assertEqual(rj["iterations"][0]["verdicts"]["security"], "changes_requested")
        self.assertEqual(rj["iterations"][1]["verdicts"]["security"], "approve")
        self.assertEqual(len(self.calls("implementer")), 2)
        self.assertIn("secret en clair", self.calls("implementer")[1]["prompt"])  # les findings sont transmis
        self.assertNotIn("secret en clair", self.calls("implementer")[0]["prompt"])
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["in-review"])
        self.assertEqual(len([f for f in self.branch_files() if "/reviews/" in f]), 6)  # 2 commits relus x 3 axes

    def test_escalates_after_three_iterations(self):
        self.scenario("always_reject")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        st = self.state()
        self.assertEqual(st["issues"]["1"]["labels"], ["needs-human"])
        self.assertEqual(st["prs"], {})
        self.assertIn("3 itérations", st["issues"]["1"]["comments"][-1]["body"])
        self.assertEqual(len(self.calls("implementer")), 3)
        rj = self.run_json()
        self.assertEqual(rj["outcome"], "needs-human")
        self.assertEqual(len(rj["iterations"]), 3)

    def test_approve_with_major_finding_is_requalified(self):
        self.scenario("liar")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 0, r.stderr)
        rj = self.run_json()
        self.assertEqual(rj["iterations"][0]["verdicts"]["simplicity"], "changes_requested")
        recs = [json.loads(self.branch_file(f)) for f in self.branch_files() if f.endswith("-simplicity.json")]
        first = next(r for r in recs if r["iteration"] == 1)
        self.assertTrue(first["adjusted"])
        self.assertEqual(first["verdict_declared"], "approve")
        self.assertEqual(first["verdict"], "changes_requested")
        second = next(r for r in recs if r["iteration"] == 2)
        self.assertFalse(second["adjusted"])

    def test_clarification_roundtrip(self):
        self.scenario("ambiguity")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        st = self.state()
        self.assertEqual(st["issues"]["1"]["labels"], ["needs-clarification"])
        self.assertIn("sdlc:clarification", st["issues"]["1"]["comments"][-1]["body"])
        self.assertIn("Quel format de sortie ?", st["issues"]["1"]["comments"][-1]["body"])
        self.assertEqual(self.calls("implementer"), [])

        # l'humain répond et remet `ready`
        st["issues"]["1"]["comments"].append({"id": "IC_h1", "body": "Format : JSON.", "author": {"login": "gaetan"}})
        st["issues"]["1"]["labels"] = ["ready"]
        self.state_path.write_text(json.dumps(st))
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["in-review"])
        amb = self.branch_file(f"docs/features/{FID}/ambiguities.md")
        self.assertIn("Format : JSON.", amb)
        self.assertEqual(amb.count("IC_h1"), 1)
        self.assertEqual(len(self.calls("planner")), 2)

    def test_clarification_without_answer_stays_blocked(self):
        self.scenario("ambiguity")
        self.run_sdlc()
        st = self.state()
        st["issues"]["1"]["labels"] = ["ready"]  # remis `ready` sans réponse
        self.state_path.write_text(json.dumps(st))
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["needs-clarification"])
        self.assertEqual(len(self.calls("planner")), 1)

    def test_unclosed_dependency_is_skipped(self):
        st = self.state()
        st["issues"]["1"]["body"] = st["issues"]["1"]["body"].replace("depends_on_issues: \n", "depends_on_issues: 2\n")
        st["issues"]["2"] = {"title": "dep", "body": "", "labels": [], "state": "OPEN", "comments": []}
        self.state_path.write_text(json.dumps(st))
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["ready"])
        self.assertEqual(self.calls(), [])
        st = self.state()
        st["issues"]["2"]["state"] = "CLOSED"
        self.state_path.write_text(json.dumps(st))
        self.assertEqual(self.run_sdlc().returncode, 0)
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["in-review"])

    def test_dry_run_changes_nothing(self):
        r = self.run_sdlc("--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["feature"], FID)
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["ready"])
        self.assertEqual(self.calls(), [])

    def test_automerge_opt_in_via_repos_file(self):
        (self.t / "repos").write_text(f"# dépôts\n{REPO} automerge  # opt-in\n")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 0, r.stderr)
        st = self.state()
        self.assertTrue(st["prs"]["1"]["automerge"])
        self.assertIn("auto-merge armé", st["issues"]["1"]["comments"][-1]["body"])
        self.assertEqual(st["issues"]["1"]["labels"], ["in-review"])

    def test_repo_flag_never_automerges(self):
        r = self.run_sdlc("--repo", REPO)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.state()["prs"]["1"]["automerge"])

    def test_invalid_repos_line_is_refused(self):
        (self.t / "repos").write_text(f"{REPO} automerge extra\n")
        r = self.run_sdlc()
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_check_red_then_green(self):
        self.scenario("check_red_then_green")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 0, r.stderr)
        rj = self.run_json()
        self.assertEqual(len(rj["iterations"]), 2)
        self.assertFalse(rj["iterations"][0]["check"]["ok"])
        self.assertEqual(rj["iterations"][0]["verdicts"], {})
        self.assertTrue(rj["iterations"][1]["check"]["ok"])
        # aucune revue sur l'itération rouge ; la sortie du check est transmise comme finding
        self.assertEqual(len(self.calls("reviewer-security")), 1)
        second = self.calls("implementer")[1]["prompt"]
        self.assertIn('"axis": "check"', second)
        self.assertIn("est rouge", second)
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["in-review"])

    def test_check_always_red_escalates_without_review(self):
        self.push_check("false")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        st = self.state()
        self.assertEqual(st["issues"]["1"]["labels"], ["needs-human"])
        self.assertIn("Gate toujours rouge", st["issues"]["1"]["comments"][-1]["body"])
        self.assertEqual(self.calls("reviewer-security"), [])
        self.assertEqual(len(self.calls("implementer")), 3)  # compte dans MAX_ITER
        self.assertEqual(st["prs"], {})

    def test_arch_red_then_green(self):
        self.scenario("arch_red_then_green")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 0, r.stderr)
        rj = self.run_json()
        self.assertEqual(len(rj["iterations"]), 2)
        self.assertTrue(rj["iterations"][0]["check"]["ok"])
        self.assertFalse(rj["iterations"][0]["arch"]["ok"])
        self.assertEqual(rj["iterations"][0]["verdicts"], {})
        self.assertTrue(rj["iterations"][1]["arch"]["ok"])
        self.assertEqual(len(self.calls("reviewer-security")), 1)  # aucune revue sur l'itération rouge
        second = self.calls("implementer")[1]["prompt"]
        self.assertIn('"axis": "arch"', second)
        self.assertNotIn('"axis": "check"', second)
        self.assertIn("Contrôle d'architecture", self.calls("reviewer-security")[0]["prompt"])
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["in-review"])

    def test_both_gates_red_reported_together(self):
        self.push_check("false", arch="false")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        self.assertIn("Gate toujours rouge", self.state()["issues"]["1"]["comments"][-1]["body"])
        p = self.calls("implementer")[1]["prompt"]
        self.assertIn('"axis": "check"', p)
        self.assertIn('"axis": "arch"', p)

    def test_architecture_absent_escalates(self):
        self.push_seed(lambda seed: shutil.rmtree(seed / "docs" / "architecture"))
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        st = self.state()
        self.assertEqual(st["issues"]["1"]["labels"], ["needs-human"])
        self.assertIn("/sdlc-framing:architect", st["issues"]["1"]["comments"][-1]["body"])
        self.assertEqual(self.calls(), [])

    def test_architecture_draft_escalates(self):
        def draft(seed):
            f = seed / "docs" / "architecture" / "ARCHITECTURE.md"
            f.write_text(f.read_text().replace("status: accepted", "status: draft"))
        self.push_seed(draft)
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["needs-human"])
        self.assertIn("status draft", self.state()["issues"]["1"]["comments"][-1]["body"])
        self.assertEqual(self.calls(), [])

    def test_missing_arch_command_escalates(self):
        self.push_check(CHECK, arch=None)
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["needs-human"])
        self.assertIn('"arch"', self.state()["issues"]["1"]["comments"][-1]["body"])
        self.assertEqual(self.calls(), [])

    def test_implementer_touching_architecture_escalates(self):
        self.scenario("touch_arch")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        st = self.state()
        self.assertEqual(st["issues"]["1"]["labels"], ["needs-human"])
        self.assertIn("fichiers verrouillés", st["issues"]["1"]["comments"][-1]["body"])
        self.assertIn("docs/architecture/ARCHITECTURE.md", st["issues"]["1"]["comments"][-1]["body"])
        self.assertEqual(self.calls("reviewer-security"), [])
        self.assertEqual(st["prs"], {})

    def test_planner_contract_escalates_structuring_decisions(self):
        agent = (ROOT / "plugins/sdlc-factory/agents/planner.md").read_text()
        self.assertIn("Exige un ADR", agent)  # le planner remonte les décisions structurantes au lieu de les trancher

    def test_check_runs_without_secrets(self):
        self.push_check('test -z "$GH_TOKEN" && test -z "$ANTHROPIC_API_KEY" && test -f hello.txt')
        r = self.run_sdlc(ANTHROPIC_API_KEY="sk-secret")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.run_json()["iterations"][0]["check"]["ok"])

    def test_missing_check_escalates(self):
        self.push_check(None)
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        st = self.state()
        self.assertEqual(st["issues"]["1"]["labels"], ["needs-human"])
        self.assertIn(".claude/check.json est absent", st["issues"]["1"]["comments"][-1]["body"])
        self.assertEqual(self.calls(), [])

    def test_placeholder_check_escalates(self):
        self.push_check("A_RENSEIGNER")
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["needs-human"])
        self.assertEqual(self.calls(), [])

    def test_automerge_failure_escalates_but_keeps_pr(self):
        (self.t / "repos").write_text(f"{REPO} automerge\n")
        r = self.run_sdlc(FAKE_AUTOMERGE_FAIL="1")
        self.assertEqual(r.returncode, 1)
        st = self.state()
        self.assertEqual(st["issues"]["1"]["labels"], ["needs-human"])
        self.assertEqual(len(st["prs"]), 1)
        self.assertIn("auto-merge", st["issues"]["1"]["comments"][-1]["body"])

    def test_invalid_spec_is_refused(self):
        seed = self.t / "seed"
        spec = seed / "docs/features" / FID / "spec.md"
        spec.write_text(SPEC.replace("Aucune dépendance externe", "TODO dépendances"))
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        sh(*g, "commit", "-qam", "spec cassée", cwd=seed)
        sh("git", "push", "-q", "origin", "main", cwd=seed)
        st = self.state()
        st["issues"]["1"]["body"] = st["issues"]["1"]["body"].replace(self.sha, sh("git", "rev-parse", "HEAD", cwd=seed))
        self.state_path.write_text(json.dumps(st))
        r = self.run_sdlc()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.state()["issues"]["1"]["labels"], ["needs-human"])
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
