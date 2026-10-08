import json
import unittest

from tests._forge import ForgeCase, junit


class StatusTest(ForgeCase):
    def test_spec_non_validee(self):
        self.spec(validated=False)
        s = self.forge("status", "T001")
        self.assertEqual(s["next"], "invalid")

    def test_sans_ac(self):
        self.spec(acs=())
        self.assertEqual(self.forge("status", "T001")["next"], "invalid")

    def test_dependance_non_livree(self):
        self.spec("T002", deps="T001")
        s = self.forge("status", "T002")
        self.assertEqual(s["next"], "invalid")
        self.assertIn("T001", s["reason"])

    def test_spec_valide_demarre(self):
        self.spec()
        self.assertEqual(self.forge("status", "T001")["next"], "start")

    def test_config_absente(self):
        self.spec()
        (self.repo / ".forge" / "config.json").unlink()
        self.assertIn("error", self.forge("status", "T001"))


class StartTest(ForgeCase):
    def test_start_cree_le_worktree(self):
        self.spec()
        r = self.forge("start", "T001")
        self.assertTrue(r["ok"])
        self.assertTrue(self.wt().is_dir())
        self.assertEqual((self.repo / ".forge" / "current").read_text(), "T001")
        self.assertEqual(self.forge("status", "T001")["next"], "plan")

    def test_start_refuse_spec_invalide(self):
        self.spec(validated=False)
        self.assertFalse(self.forge("start", "T001")["ok"])


class RedTest(ForgeCase):
    def setUp(self):
        super().setUp()
        self.spec()
        self.forge("start", "T001")
        (self.repo / ".forge/backlog/T001/plan.md").write_text("plan")

    def test_rouge_valide(self):
        self.write("tests/acceptance/test_a.py", "# AC-1\n")
        self.set_junit(("test_ac_1", True))
        r = self.forge("red", "T001")
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.forge("status", "T001")["next"], "green")

    def test_tests_deja_verts_refuses(self):
        self.write("tests/acceptance/test_a.py", "# AC-1\n")
        self.set_junit(("test_ac_1", False))
        r = self.forge("red", "T001")
        self.assertFalse(r["ok"])
        self.assertTrue(any("passent déjà" in p for p in r["problems"]))

    def test_fichier_hors_tests_annule(self):
        self.write("tests/acceptance/test_a.py", "# AC-1\n")
        src = self.write("src/app.py")
        self.set_junit(("test_ac_1", True))
        r = self.forge("red", "T001")
        self.assertFalse(r["ok"])
        self.assertFalse(src.exists())

    def test_aucun_test_acceptation(self):
        self.write("tests/unit/test_u.py")
        self.set_junit(("test_u", True))
        r = self.forge("red", "T001")
        self.assertTrue(any("acceptation" in p for p in r["problems"]))

    def test_ac_sans_test(self):
        self.write("tests/acceptance/test_a.py", "# rien\n")
        self.set_junit(("test_x", True))
        r = self.forge("red", "T001")
        self.assertTrue(any("AC-1" in p for p in r["problems"]))

    def test_absence_de_progres_bloque(self):
        self.write("tests/acceptance/test_a.py", "# AC-1\n")
        self.set_junit(("test_ac_1", False))
        # le premier tour ne compte pas : le blocage vient au deuxième tour identique
        self.assertFalse(self.forge("red", "T001")["blocked"])
        self.assertFalse(self.forge("red", "T001")["blocked"])
        self.assertTrue(self.forge("red", "T001")["blocked"])
        self.assertEqual(self.forge("status", "T001")["next"], "blocked")


class GreenTest(ForgeCase):
    def setUp(self):
        super().setUp()
        self.spec()
        self.to_red()

    def test_vert(self):
        self.write("src/app.py", "x = 1\n")
        self.set_junit(("test_ac_1", False))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertTrue(r["passed"], r)
        self.assertEqual(self.forge("status", "T001")["next"], "refactor")

    def test_rouge_encore(self):
        self.set_junit(("test_ac_1", True))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(r["passed"])
        self.assertFalse(r["blocked"])

    def test_modification_de_test_annulee(self):
        t = self.write("tests/unit/test_new.py")
        self.set_junit(("test_ac_1", False))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(r["passed"])
        self.assertTrue(r["violations"])
        self.assertFalse(t.exists())

    def test_acceptation_modifiee(self):
        self.write("tests/acceptance/test_a.py", "# AC-1 truqué\n")
        self.set_junit(("test_ac_1", False))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(r["passed"])
        self.assertTrue(r["violations"])
        self.assertEqual((self.wt() / "tests/acceptance/test_a.py").read_text(), "# AC-1\n")

    def test_config_protegee_annulee(self):
        f = self.write(".github/workflows/x.yml")
        self.set_junit(("test_ac_1", False))
        self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(f.exists())

    def test_absence_de_progres_puis_unblock(self):
        self.set_junit(("test_ac_1", True))
        self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(self.forge("green", "T001", "--phase", "impl")["blocked"])
        self.assertTrue(self.forge("green", "T001", "--phase", "impl")["blocked"])
        self.assertEqual(self.forge("status", "T001")["next"], "blocked")
        self.assertEqual(self.forge("unblock", "T001")["next"], "green")

    def test_marqueur_de_suppression_signale(self):
        self.write("src/app.py", "x = 1  # noqa\n")
        self.set_junit(("test_ac_1", False))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertTrue(r["suppressions"])


class ReviewTest(ForgeCase):
    def setUp(self):
        super().setUp()
        self.spec()
        self.to_red()
        self.set_junit(("test_ac_1", False))
        self.forge("green", "T001", "--phase", "impl")
        self.td = self.repo / ".forge/backlog/T001"

    def review(self, rnd, items):
        (self.td / f"review-{rnd}.json").write_text(json.dumps({"items": items}))

    def item(self, i, sev="bloquant", target="code"):
        return {"id": i, "severity": sev, "target": target, "summary": "s"}

    def test_approbation(self):
        self.review(1, [])
        r = self.forge("review", "T001", 1)
        self.assertTrue(r["approved"])

    def test_changements(self):
        self.review(1, [self.item("R1-1"), self.item("R1-2", "mineur", "tests")])
        r = self.forge("review", "T001", 1)
        self.assertFalse(r["approved"])
        self.assertEqual((r["blocking"], r["minor"], r["items_code"], r["items_tests"]), (1, 1, 1, 1))

    def test_element_mal_forme(self):
        self.review(1, [{"id": "R1-1"}])
        self.assertIn("error", self.forge("review", "T001", 1))

    def test_dispositions(self):
        self.review(1, [self.item("R1-1"), self.item("R1-2", "mineur", "tests")])
        self.forge("review", "T001", 1)
        (self.td / "dispositions-1-code.json").write_text(json.dumps([{"id": "R1-1", "status": "corrigé"}]))
        r = self.forge("dispositions", "T001", 1)
        self.assertFalse(r["ok"])
        self.assertEqual(r["missing"]["tests"], ["R1-2"])
        (self.td / "dispositions-1-tests.json").write_text(
            json.dumps([{"id": "R1-2", "status": "reporté", "reason": "hors périmètre", "issue_title": "t"}]))
        self.assertTrue(self.forge("dispositions", "T001", 1)["ok"])

    def test_refus_sans_motif(self):
        self.review(1, [self.item("R1-1")])
        (self.td / "dispositions-1-code.json").write_text(json.dumps([{"id": "R1-1", "status": "refusé"}]))
        self.assertEqual(self.forge("dispositions", "T001", 1)["invalid"]["code"], ["R1-1"])


class ShipTest(ForgeCase):
    def test_ship_pousse_et_ouvre_la_pr(self):
        self.spec()
        self.to_red()
        self.write("src/app.py")
        self.set_junit(("test_ac_1", False))
        self.assertTrue(self.forge("green", "T001", "--phase", "impl")["passed"])
        r = self.forge("ship", "T001")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["pr"], "https://github.com/x/y/pull/1")
        refs = self.ghlog.read_text()
        self.assertIn("pr create", refs)
        self.assertIn("pr merge", refs)
        from tests._forge import sh
        self.assertIn("forge/T001", sh(["git", "branch", "--list"], self.origin).stdout)
        self.assertEqual(self.forge("status", "T001")["next"], "wait")

    def test_ship_bloque_en_brouillon(self):
        self.spec()
        self.forge("start", "T001")
        r = self.forge("ship", "T001", "--blocked", "motif")
        self.assertEqual(r["status"], "blocked")
        self.assertIn("--draft", self.ghlog.read_text())
        self.assertNotIn("pr merge", self.ghlog.read_text())


if __name__ == "__main__":
    unittest.main()
