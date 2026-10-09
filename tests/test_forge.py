import json
import unittest

from tests._forge import ForgeCase


class StatusTest(ForgeCase):
    def test_spec_non_approuvee(self):
        self.spec(approve=False)
        s = self.forge("status", "T001")
        self.assertEqual(s["next"], "invalid")
        self.assertIn("non approuvée", s["reason"])

    def test_spec_modifiee_apres_approbation(self):
        d = self.spec()
        (d / "spec.md").write_text((d / "spec.md").read_text() + "\n- AC-2 — ajout en douce\n")
        s = self.forge("status", "T001")
        self.assertEqual(s["next"], "invalid")
        self.assertIn("modifiée", s["reason"])
        self.assertFalse(self.forge("start", "T001")["ok"])

    def test_dependance_non_livree(self):
        self.spec("T001", approve=False)
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

    def test_start_refuse_spec_non_approuvee(self):
        self.spec(approve=False)
        self.assertFalse(self.forge("start", "T001")["ok"])

    def test_start_commite_la_spec_figee(self):
        d = self.spec()
        self.forge("start", "T001")
        f = self.wt() / "docs/product/specs/T001.md"
        self.assertEqual(f.read_text(), (d / "spec.md").read_text())
        from tests._forge import sh
        self.assertIn("docs(T001): spec", sh(["git", "log", "--oneline"], self.wt()).stdout)
        self.assertEqual(sh(["git", "status", "--porcelain"], self.wt()).stdout, "")


class ApproveTest(ForgeCase):
    def bad(self, text, task="T001"):
        d = self.repo / ".forge/backlog" / task
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.md").write_text(text)
        return self.forge("approve", task)

    def test_approuve_et_enregistre_l_empreinte(self):
        self.spec()
        st = json.loads((self.repo / ".forge/backlog/T001/state.json").read_text())
        self.assertEqual(len(st["approved_hash"]), 64)
        self.assertEqual(self.forge("status", "T001")["next"], "start")

    def test_refus(self):
        self.assertIn("id", self.bad("---\ntitle: x\ndepends_on: []\n---\nAC-1")["error"])
        self.assertIn("title", self.bad("---\nid: T001\ndepends_on: []\n---\nAC-1")["error"])
        self.assertIn("AC", self.bad("---\nid: T001\ntitle: x\ndepends_on: []\n---\nrien")["error"])
        self.assertIn("T009", self.bad("---\nid: T001\ntitle: x\ndepends_on: [T009]\n---\nAC-1")["error"])

    def test_dependance_dans_le_meme_lot(self):
        for t, deps in (("T001", ""), ("T002", "T001")):
            self.spec(t, approve=False, deps=deps)
        self.assertTrue(self.forge("approve", "T001", "T002")["ok"])

    def test_pas_de_reapprobation_apres_lancement(self):
        self.spec()
        self.forge("start", "T001")
        self.assertIn("error", self.forge("approve", "T001"))


class BacklogTest(ForgeCase):
    def test_statuts_et_numerotation(self):
        self.spec("T001")
        self.spec("T002", approve=False)
        self.spec("T003")
        self.forge("start", "T003")
        b = self.forge("backlog")
        st = {t["id"]: t["status"] for t in b["tasks"]}
        self.assertEqual(st, {"T001": "approved", "T002": "draft", "T003": "running"})
        self.assertEqual(b["next_id"], "T004")

    def test_spec_modifiee_redevient_draft(self):
        d = self.spec()
        (d / "spec.md").write_text((d / "spec.md").read_text() + "x")
        t = self.forge("backlog")["tasks"][0]
        self.assertEqual((t["status"], t["spec_modified"]), ("draft", True))


class RedTest(ForgeCase):
    def setUp(self):
        super().setUp()
        self.spec()
        self.forge("start", "T001")
        (self.repo / ".forge/backlog/T001/plan.md").write_text("plan")

    def test_rouge_valide(self):
        self.write("tests/acceptance/test_a.py", "# AC-1\n")
        self.set_results(("test_ac_1", True))
        r = self.forge("red", "T001")
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.forge("status", "T001")["next"], "green")

    def test_tests_deja_verts_refuses(self):
        self.write("tests/acceptance/test_a.py", "# AC-1\n")
        self.set_results(("test_ac_1", False))
        r = self.forge("red", "T001")
        self.assertFalse(r["ok"])
        self.assertTrue(any("passent déjà" in p for p in r["problems"]))

    def test_fichier_hors_tests_annule(self):
        self.write("tests/acceptance/test_a.py", "# AC-1\n")
        src = self.write("src/app.py")
        self.set_results(("test_ac_1", True))
        r = self.forge("red", "T001")
        self.assertFalse(r["ok"])
        self.assertFalse(src.exists())

    def test_aucun_test_acceptation(self):
        self.write("tests/unit/test_u.py")
        self.set_results(("test_u", True))
        r = self.forge("red", "T001")
        self.assertTrue(any("acceptation" in p for p in r["problems"]))

    def test_ac_sans_test(self):
        self.write("tests/acceptance/test_a.py", "# rien\n")
        self.set_results(("test_x", True))
        r = self.forge("red", "T001")
        self.assertTrue(any("AC-1" in p for p in r["problems"]))

    def test_ac_sans_testcase_nomme(self):
        self.write("tests/acceptance/test_a.py", "# AC-1 dans le fichier seulement\n")
        self.set_results(("test_quelque_chose", True))
        r = self.forge("red", "T001")
        self.assertFalse(r["ok"])
        self.assertEqual(r["ac_missing"], ["AC-1"])
        self.assertTrue(any("AC-1" in p for p in r["problems"]))

    def test_ac_identifiants_normalises(self):
        for name in ("test_AC_01_x", "AC-1 comportement", "ac1"):
            self.set_results((name, True))
            self.write("tests/acceptance/test_a.py", f"# {name}\n")
            self.assertTrue(self.forge("red", "T001")["ok"], name)
            self.forge("unblock", "T001")
            from tests._forge import sh
            sh(["git", "reset", "-q", "--hard", "HEAD~1"], self.wt())
            st = self.repo / ".forge/backlog/T001/state.json"
            d = json.loads(st.read_text())
            d.pop("red_sha")
            st.write_text(json.dumps(d))

    def test_ac_dont_aucun_test_n_echoue(self):
        d = self.repo / ".forge/backlog/T001/spec.md"
        d.write_text(d.read_text() + "- AC-2 — autre\n")
        self.forge("approve", "T001")
        self.write("tests/acceptance/test_a.py", "# AC-1 AC-2\n")
        self.set_results(("test_ac_1", True), ("test_ac_2", False))
        r = self.forge("red", "T001")
        self.assertFalse(r["ok"])
        self.assertEqual(r["ac_missing"], ["AC-2"])

    def test_absence_de_progres_bloque(self):
        self.write("tests/acceptance/test_a.py", "# AC-1\n")
        self.set_results(("test_ac_1", False))
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
        self.set_results(("test_ac_1", False))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertTrue(r["passed"], r)
        self.assertEqual(self.forge("status", "T001")["next"], "refactor")

    def test_modif_architecture_annulee_au_vert(self):
        self.write("src/app.py", "x = 1\n")
        self.write("ARCHITECTURE.md", "# détourné\n")
        self.write("docs/architecture/adr/0001-x.md", "# détourné\n")
        self.write("PRODUCT.md", "# détourné\n")
        self.set_results(("test_ac_1", False))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(r["passed"], r)
        for rel in ("ARCHITECTURE.md", "docs/architecture/adr/0001-x.md", "PRODUCT.md"):
            self.assertFalse((self.wt() / rel).exists(), rel)

    def test_ac_sans_testcase_au_vert(self):
        self.set_results(("test_autre", False))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(r["passed"])
        self.assertEqual(r["ac_missing"], ["AC-1"])

    def test_rouge_encore(self):
        self.set_results(("test_ac_1", True))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(r["passed"])
        self.assertFalse(r["blocked"])

    def test_modification_de_test_annulee(self):
        t = self.write("tests/unit/test_new.py")
        self.set_results(("test_ac_1", False))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(r["passed"])
        self.assertTrue(r["violations"])
        self.assertFalse(t.exists())

    def test_acceptation_modifiee(self):
        self.write("tests/acceptance/test_a.py", "# AC-1 truqué\n")
        self.set_results(("test_ac_1", False))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(r["passed"])
        self.assertTrue(r["violations"])
        self.assertEqual((self.wt() / "tests/acceptance/test_a.py").read_text(), "# AC-1\n")

    def test_config_protegee_annulee(self):
        f = self.write(".github/workflows/x.yml")
        self.set_results(("test_ac_1", False))
        self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(f.exists())

    def test_absence_de_progres_puis_unblock(self):
        self.set_results(("test_ac_1", True))
        self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(self.forge("green", "T001", "--phase", "impl")["blocked"])
        self.assertTrue(self.forge("green", "T001", "--phase", "impl")["blocked"])
        self.assertEqual(self.forge("status", "T001")["next"], "blocked")
        self.assertEqual(self.forge("unblock", "T001")["next"], "green")

    def test_marqueur_de_suppression_signale(self):
        self.write("src/app.py", "x = 1  # noqa\n")
        self.set_results(("test_ac_1", False))
        r = self.forge("green", "T001", "--phase", "impl")
        self.assertTrue(r["suppressions"])


class ReviewTest(ForgeCase):
    def setUp(self):
        super().setUp()
        self.spec()
        self.to_red()
        self.set_results(("test_ac_1", False))
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


class PublishTest(ForgeCase):
    def test_publie_sans_toucher_la_branche_courante(self):
        from tests._forge import sh
        (self.repo / "PRODUCT.md").write_text("# Produit\n")
        (self.repo / "docs/product").mkdir(parents=True)
        (self.repo / "docs/product/decisions.md").write_text("- décision\n")
        r = self.forge("publish", "docs: vision", "PRODUCT.md", "docs/product")
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(r["merge"], "github")
        self.assertIn("pr merge", self.ghlog.read_text())
        branches = sh(["git", "branch", "--list", "product/*"], self.origin).stdout
        self.assertTrue(branches.strip())
        shown = sh(["git", "show", f"{branches.split()[-1]}:docs/product/decisions.md"], self.origin).stdout
        self.assertEqual(shown, "- décision\n")
        # checkout principal remis à HEAD, plus de worktree ni de branche locale temporaires
        self.assertEqual(sh(["git", "status", "--porcelain"], self.repo).stdout, "")
        self.assertFalse((self.repo / "PRODUCT.md").exists())
        self.assertEqual(sh(["git", "branch", "--list", "product/*"], self.repo).stdout, "")

    def test_manual_ne_merge_pas(self):
        (self.repo / ".forge/conventions.md").write_text("# c\n")
        r = self.forge("publish", "chore: conventions", ".forge/conventions.md", "--manual")
        self.assertEqual(r["merge"], "manual")
        self.assertNotIn("pr merge", self.ghlog.read_text())

    def test_chemin_non_publiable(self):
        (self.repo / "src.py").write_text("x")
        self.assertIn("error", self.forge("publish", "m", "src.py"))
        self.assertIn("error", self.forge("publish", "m", "../x"))

    def test_publie_architecture(self):
        (self.repo / "ARCHITECTURE.md").write_text("# Architecture\n")
        (self.repo / "docs/architecture/adr").mkdir(parents=True)
        (self.repo / "docs/architecture/adr/0001-x.md").write_text("# ADR\n")
        r = self.forge("publish", "docs: architecture", "ARCHITECTURE.md", "docs/architecture")
        self.assertTrue(r.get("ok"), r)
        self.assertIn("docs/architecture/adr/0001-x.md", r["files"])

    def test_rien_a_publier(self):
        r = self.forge("publish", "m", ".forge/config.json")
        self.assertTrue(r["noop"])


class ResultsTest(ForgeCase):
    def setup_cfg(self, **changes):
        cfg = json.loads((self.repo / ".forge/config.json").read_text())
        cfg.update(changes)
        (self.repo / ".forge/config.json").write_text(json.dumps(cfg))
        from tests._forge import sh
        sh(["git", "commit", "-qam", "cfg"], self.repo)
        sh(["git", "push", "-q"], self.repo)
        self.spec()
        self.forge("start", "T001")
        return cfg

    def test_results_path_glob_plusieurs_fichiers(self):
        script = self.tmp / "multi.py"
        script.write_text("import json, pathlib\nd = pathlib.Path('.forge/out/reports'); d.mkdir(parents=True, exist_ok=True)\n"
                          "(d / 'r-a.json').write_text(json.dumps({'cases': [{'name': 'AC-1 a', 'failed': True}]}))\n"
                          "(d / 'r-b.json').write_text(json.dumps({'cases': [{'name': 'b', 'failed': False}]}))\n"
                          "raise SystemExit(1)\n")
        self.setup_cfg(results_path=".forge/out/reports/r-*.json", test_cmd=f"python3 {script}")
        self.write("tests/acceptance/test_a.py")
        r = self.forge("red", "T001")
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["tests"], {"total": 2, "failed": 1})

    def test_acs_explicite_prioritaire_sur_le_nom(self):
        self.setup_cfg()
        self.write("tests/acceptance/test_a.py")
        self.set_results(("test_ac_1", True, ["AC-2"]))
        r = self.forge("red", "T001")
        self.assertFalse(r["ok"])
        self.assertEqual(r["ac_missing"], ["AC-1"])

    def test_acs_explicite_sans_id_dans_le_nom(self):
        self.setup_cfg()
        self.write("tests/acceptance/test_a.py")
        self.set_results(("refuse un montant négatif", True, ["AC-1"]))
        self.assertTrue(self.forge("red", "T001")["ok"])

    def test_json_invalide_refuse_le_rouge(self):
        self.setup_cfg()
        self.write("tests/acceptance/test_a.py")
        self.set_results_raw("pas du json")
        r = self.forge("red", "T001")
        self.assertFalse(r["ok"])
        self.assertTrue(any("inexploitables" in p for p in r["problems"]), r)

    def test_schema_incomplet_refuse_le_rouge(self):
        self.setup_cfg()
        self.write("tests/acceptance/test_a.py")
        self.set_results_raw(json.dumps({"cases": [{"name": "AC-1 a"}]}))
        r = self.forge("red", "T001")
        self.assertFalse(r["ok"])
        self.assertTrue(any("inexploitables" in p for p in r["problems"]), r)

    def test_acceptance_globs_plusieurs_motifs(self):
        self.setup_cfg(acceptance_globs=["tests/acceptance/*", "features/*.feature"],
                       test_globs=["tests/*", "features/*"])
        self.write("features/a.feature")
        self.set_results(("AC-1 a", True))
        r = self.forge("red", "T001")
        self.assertTrue(r["ok"], r)
        self.write("features/a.feature", "truqué\n")
        self.set_results(("AC-1 a", False))
        g = self.forge("green", "T001", "--phase", "impl")
        self.assertFalse(g["passed"])
        self.assertTrue(any("features/a.feature" in v for v in g["violations"]), g)
        self.assertNotEqual((self.wt() / "features/a.feature").read_text(), "truqué\n")

    def test_aucun_test_d_acceptation_selon_les_motifs(self):
        self.setup_cfg(acceptance_globs=["features/*.feature"], test_globs=["tests/*", "features/*"])
        self.write("tests/unit/test_u.py")
        self.set_results(("AC-1 a", True))
        r = self.forge("red", "T001")
        self.assertFalse(r["ok"])
        self.assertTrue(any("aucun test d'acceptation" in p for p in r["problems"]), r)


class PlanCheckTest(ForgeCase):
    def check(self, text):
        d = self.spec()
        (d / "plan.md").write_text(text)
        return self.forge("plan-check", "T001")

    def test_plan_normal(self):
        r = self.check("# Plan\n\n1. Compréhension\n")
        self.assertEqual((r["ok"], r["blocked"]), (True, False))

    def test_depassement(self):
        r = self.check("DÉPASSEMENT\nredécouper en deux\n")
        self.assertTrue(r["blocked"])
        self.assertIn("DÉPASSEMENT", r["reason"])

    def test_ecart_adr(self):
        r = self.check("ÉCART-ADR 0003 : la tâche exige un second service\n")
        self.assertTrue(r["blocked"])
        self.assertIn("0003", r["reason"])

    def test_sans_plan(self):
        self.spec()
        self.assertFalse(self.forge("plan-check", "T001")["blocked"])

    def test_unblock_retire_le_plan_d_arret(self):
        self.check("ÉCART-ADR 0003 : motif\n")
        self.forge("start", "T001")
        self.assertTrue(self.forge("unblock", "T001")["ok"])
        self.assertEqual(self.forge("status", "T001")["next"], "plan")


class DoctorTest(ForgeCase):
    def checks(self):
        r = self.forge("doctor", "--plugin-version", "0.4.0")
        return r, {c["name"]: c["ok"] for c in r["checks"]}

    def test_remote_github_requis(self):
        self.set_results(("t", False))
        r, c = self.checks()
        self.assertTrue(c["results"] and c["config"] and c["gh"] and c["version"])
        self.assertFalse(c["remote"])  # remote local de test
        self.assertFalse(r["ok"])

    def test_results_vide(self):
        self.set_results()
        self.assertFalse(self.checks()[1]["results"])

    def test_results_json_invalide(self):
        self.set_results_raw("{")
        self.assertFalse(self.checks()[1]["results"])

    def test_sans_results_path_ni_acceptance_globs(self):
        cfg = json.loads((self.repo / ".forge/config.json").read_text())
        for k in ("results_path", "acceptance_globs"):
            cfg.pop(k)
        (self.repo / ".forge/config.json").write_text(json.dumps(cfg))
        self.set_results(("t", False))
        r = self.forge("doctor")
        c = {x["name"]: x for x in r["checks"]}
        self.assertFalse(c["config"]["ok"])
        self.assertIn("acceptance_globs", c["config"]["detail"])
        self.assertFalse(c["results"]["ok"])
        self.assertIn("/tdd-forge:init", c["results"]["detail"])

    def test_architecture_requise(self):
        self.set_results(("t", False))
        self.assertFalse(self.checks()[1]["architecture"])
        (self.repo / "ARCHITECTURE.md").write_text("# Architecture\n")
        self.assertTrue(self.checks()[1]["architecture"])

    def test_version_differente(self):
        r = self.forge("doctor", "--plugin-version", "9.9.9")
        self.assertFalse({c["name"]: c["ok"] for c in r["checks"]}["version"])


class ShipTest(ForgeCase):
    def test_ship_pousse_et_ouvre_la_pr(self):
        self.spec()
        self.to_red()
        self.write("src/app.py")
        self.set_results(("test_ac_1", False))
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
