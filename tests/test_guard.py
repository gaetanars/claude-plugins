import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._forge import GUARD


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        (self.tmp / ".forge" / "backlog" / "T001").mkdir(parents=True)
        (self.tmp / ".forge" / "worktrees" / "T001" / ".forge").mkdir(parents=True)
        (self.tmp / ".forge" / "current").write_text("T001")
        (self.tmp / ".forge" / "worktrees" / "T001" / ".forge" / "config.json").write_text(
            json.dumps({"acceptance_dir": "tests/acceptance", "test_globs": ["tests/*"]}))

    def call(self, role, tool, **ti):
        data = {"agent_type": f"tdd-forge:{role}" if role else "", "tool_name": tool, "tool_input": ti}
        p = subprocess.run(["python3", str(GUARD)], input=json.dumps(data), capture_output=True, text=True,
                           env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.tmp)})
        return p.returncode

    def wt(self, rel):
        return str(self.tmp / ".forge" / "worktrees" / "T001" / rel)

    def td(self, name):
        return str(self.tmp / ".forge" / "backlog" / "T001" / name)

    def lock(self):
        (self.tmp / ".forge" / "backlog" / "T001" / "state.json").write_text('{"red_sha": "abc"}')

    def test_hors_plugin_ou_sans_tache(self):
        self.assertEqual(self.call("", "Write", file_path=self.wt("src/a.py")), 0)
        self.assertEqual(self.call("autre", "Bash", command="git push"), 0)
        (self.tmp / ".forge" / "current").unlink()
        self.assertEqual(self.call("implementer", "Write", file_path=self.wt("tests/a.py")), 0)

    def test_planner(self):
        self.assertEqual(self.call("planner", "Write", file_path=self.td("plan.md")), 0)
        self.assertEqual(self.call("planner", "Write", file_path=self.wt("src/a.py")), 2)

    def test_reviewer(self):
        self.assertEqual(self.call("reviewer", "Write", file_path=self.td("review-1.json")), 0)
        self.assertEqual(self.call("reviewer", "Write", file_path=self.wt("src/a.py")), 2)

    def test_learner(self):
        self.assertEqual(self.call("learner", "Write", file_path=self.td("report.md")), 0)
        self.assertEqual(self.call("learner", "Write", file_path=self.wt(".forge/learnings.md")), 0)
        self.assertEqual(self.call("learner", "Write", file_path=self.wt("src/a.py")), 2)

    def test_test_writer(self):
        self.assertEqual(self.call("test-writer", "Write", file_path=self.wt("tests/unit/a.py")), 0)
        self.assertEqual(self.call("test-writer", "Write", file_path=self.wt("src/a.py")), 2)
        self.assertEqual(self.call("test-writer", "Write", file_path=self.td("dispositions-1-tests.json")), 0)
        self.assertEqual(self.call("test-writer", "Write", file_path=self.td("dispositions-1-code.json")), 2)

    def test_acceptation_verrouillee_apres_rouge(self):
        self.assertEqual(self.call("test-writer", "Write", file_path=self.wt("tests/acceptance/a.py")), 0)
        self.lock()
        self.assertEqual(self.call("test-writer", "Write", file_path=self.wt("tests/acceptance/a.py")), 2)
        self.assertEqual(self.call("test-writer", "Write", file_path=self.wt("tests/unit/a.py")), 0)

    def test_implementer(self):
        self.assertEqual(self.call("implementer", "Write", file_path=self.wt("src/a.py")), 0)
        self.assertEqual(self.call("implementer", "Write", file_path=self.wt("tests/a.py")), 2)
        self.assertEqual(self.call("implementer", "Write", file_path=self.wt(".github/w.yml")), 2)
        self.assertEqual(self.call("implementer", "Write", file_path=str(self.tmp / "src/a.py")), 2)
        self.assertEqual(self.call("implementer", "Write", file_path=self.td("dispositions-1-code.json")), 0)

    def test_git_et_gh(self):
        for cmd in ("git commit -m x", "git push", "gh pr merge 1", "cd x && git checkout main"):
            self.assertEqual(self.call("implementer", "Bash", command=cmd), 2, cmd)
        self.assertEqual(self.call("implementer", "Bash", command="git diff HEAD"), 0)

    def test_forge_lecture_seule(self):
        self.assertEqual(self.call("planner", "Bash", command="python3 .forge/bin/forge.py context T001"), 0)
        for sub in ("ship T001", "red T001", "unblock T001"):
            self.assertEqual(self.call("planner", "Bash", command=f"python3 .forge/bin/forge.py {sub}"), 2, sub)

    def test_approve_et_publish_interdits_a_tous(self):
        for role in ("planner", "implementer", "runner", "learner"):
            for sub in ("approve T001", 'publish "m" PRODUCT.md'):
                self.assertEqual(self.call(role, "Bash", command=f"python3 .forge/bin/forge.py {sub}"), 2, (role, sub))
        self.assertEqual(self.call("planner", "Bash",
                                   command="python3 .forge/bin/forge.py status T001 && python3 .forge/bin/forge.py approve T001"), 2)

    def test_backlog_et_doctor_en_lecture(self):
        for sub in ("backlog", "doctor"):
            self.assertEqual(self.call("planner", "Bash", command=f"python3 .forge/bin/forge.py {sub}"), 0)

    def test_docs_produit_hors_de_portee(self):
        self.assertEqual(self.call("implementer", "Write", file_path=self.wt("docs/product/decisions.md")), 2)
        self.assertEqual(self.call("test-writer", "Write", file_path=self.wt("docs/product/specs/T001.md")), 2)
        self.assertEqual(self.call("learner", "Write", file_path=self.wt("docs/product/decisions.md")), 2)

    def test_runner(self):
        self.assertEqual(self.call("runner", "Bash", command="python3 .forge/bin/forge.py ship T001"), 0)
        self.assertEqual(self.call("runner", "Bash", command="ls"), 2)
        self.assertEqual(self.call("runner", "Write", file_path=self.wt("a")), 2)


if __name__ == "__main__":
    unittest.main()
