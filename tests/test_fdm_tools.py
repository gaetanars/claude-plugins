"""fdm_tools : lecture AST des sources, sans jamais importer fdm_tools ni ses dépendances."""
import ast
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "plugins/fdm/lib/fdm_tools"


def parse(name):
    return ast.parse((LIB / name).read_text())


def strings(tree):
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def calls(node):
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
            if name:
                out.append((name, n.lineno, n))
    return out


def func(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def has_string(tree, *needles):
    ss = strings(tree)
    return {n: any(n in s for s in ss) for n in needles}


def handler_names(h):
    t = h.type
    elts = t.elts if isinstance(t, ast.Tuple) else [t]
    return {e.id for e in elts if isinstance(e, ast.Name)}


class CheckSource(unittest.TestCase):
    def setUp(self):
        self.tree = parse("check.py")
        self.check = func(self.tree, "check")

    def test_init_exports_check(self):
        imports = [n for n in parse("__init__.py").body if isinstance(n, ast.ImportFrom)]
        self.assertTrue(any(n.module == "fdm_tools.check" and "check" in [a.name for a in n.names] for n in imports))

    def test_check_signature(self):
        args = self.check.args.args
        self.assertEqual([a.arg for a in args], ["part", "out"])
        self.assertEqual(ast.unparse(args[1].annotation), "str")
        self.assertEqual(ast.unparse(self.check.returns), "trimesh.Trimesh")

    def test_reads_profiles_before_writing(self):
        cs = sorted((line, name) for name, line, _ in calls(self.check))
        self.assertEqual(cs[0][1], "_printer")
        first = cs[0][0]
        for name in ("mkdir", "export_step", "export_stl", "render"):
            lines = [line for line, n in cs if n == name]
            self.assertTrue(lines and min(lines) > first, name)

    def test_profile_fields_and_messages(self):
        found = has_string(self.tree, "FDM_DATA", "machine.json", "filament.json", "printable_area",
                           "printable_height", "filament_density", "filament_type", "fdm-run", "fdm-profiles")
        self.assertTrue(all(found.values()), found)

    def test_profile_errors_are_system_exit(self):
        handlers = [h for n in ast.walk(func(self.tree, "_printer")) if isinstance(n, ast.Try) for h in n.handlers]
        self.assertTrue(any({"OSError", "ValueError"} <= handler_names(h)
                            and any(name == "exit" for name, _, _ in calls(ast.Module(h.body, []))) for h in handlers))

    def test_build_volume_message(self):
        found = has_string(self.tree, "exceeds build volume", "if solid")
        self.assertTrue(all(found.values()), found)
        names = {n.id for n in ast.walk(self.tree) if isinstance(n, ast.Name)}
        self.assertNotIn("A1_BUILD_VOLUME", names)
        consts = [n.value for n in ast.walk(self.tree) if isinstance(n, ast.Constant)]
        self.assertNotIn(1.24, consts)
        self.assertFalse([s for s in strings(self.tree) if "A1" in s or "PLA" in s])

    def test_original_output_kept(self):
        found = has_string(self.tree, "--- ", "size (X×Y×Z): ", "volume: ", "overhangs >45° needing support: ",
                           "files: ", "OK", "ISSUES:", "mesh is not watertight", "inconsistent face winding",
                           "non-positive volume (inverted normals?)", "part does not sit on Z=0")
        self.assertTrue(all(found.values()), found)
        stl = next(c for n, _, c in calls(self.check) if n == "export_stl")
        kw = {k.arg: k.value.value for k in stl.keywords}
        self.assertEqual(kw, {"tolerance": 0.01, "angular_tolerance": 0.1})
        views = next(n.value for n in self.tree.body if isinstance(n, ast.Assign)
                     and any(getattr(t, "id", None) == "VIEWS" for t in n.targets))
        self.assertEqual([k.value for k in views.keys], ["iso", "front", "right", "top"])

    def test_mkdir_oserror_handled(self):
        tries = [n for n in ast.walk(self.check) if isinstance(n, ast.Try)]
        self.assertTrue(any(
            any(name == "mkdir" for name, _, _ in calls(ast.Module(t.body, [])))
            and any("OSError" in handler_names(h) and any(n == "exit" for n, _, _ in calls(ast.Module(h.body, [])))
                    for h in t.handlers)
            for t in tries))

    def test_results_registry(self):
        assigns = [n for n in ast.walk(self.tree) if isinstance(n, (ast.Assign, ast.AugAssign))
                   and any(getattr(t, "id", None) == "RESULTS" for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))]
        self.assertEqual(len(assigns), 1)
        self.assertEqual(ast.unparse(assigns[0]), "RESULTS = []")
        self.assertTrue(any(isinstance(c.func, ast.Attribute) and c.func.attr == "append"
                            and ast.unparse(c.func.value) == "RESULTS" for _, _, c in calls(self.check)))


class RunnerSource(unittest.TestCase):
    def setUp(self):
        self.tree = parse("run.py")

    def test_runs_piece_as_main(self):
        run = next(c for n, _, c in calls(self.tree) if n == "run_path")
        self.assertEqual({k.arg: k.value.value for k in run.keywords}, {"run_name": "__main__"})
        argv = [n.lineno for n in ast.walk(self.tree) if isinstance(n, ast.Assign)
                and any(ast.unparse(t) == "sys.argv" for t in n.targets)]
        self.assertTrue(argv and min(argv) < run.lineno)

    def test_reads_registry(self):
        imports = [n for n in ast.walk(self.tree) if isinstance(n, ast.ImportFrom)]
        self.assertTrue(any(n.module == "fdm_tools.check" and "RESULTS" in [a.name for a in n.names] for n in imports))

    def test_no_check_message(self):
        self.assertTrue(has_string(self.tree, "aucun check() appelé : la pièce n'est pas vérifiée")
                        ["aucun check() appelé : la pièce n'est pas vérifiée"])

    def test_nonzero_system_exit_propagates(self):
        handlers = [h for n in ast.walk(self.tree) if isinstance(n, ast.Try) for h in n.handlers
                    if handler_names(h) == {"SystemExit"}]
        self.assertTrue(any(isinstance(x, ast.Raise) for h in handlers for x in ast.walk(ast.Module(h.body, []))))


class ExampleSource(unittest.TestCase):
    def setUp(self):
        self.tree = parse("examples/calibration_cube.py")

    def test_example_uses_public_api(self):
        imports = [n for n in self.tree.body if isinstance(n, ast.ImportFrom)]
        self.assertTrue(any(n.module == "fdm_tools" and "check" in [a.name for a in n.names] for n in imports))
        cs = [c for n, _, c in calls(self.tree) if n == "check"]
        self.assertTrue(any(len(c.args) == 2 and ast.unparse(c.args[1]) == "'out/calibration_cube'" for c in cs))
        self.assertNotIn("insert", [n for n, _, _ in calls(self.tree)])
        self.assertFalse([s for s in strings(self.tree) if "tools" in s.split("/") or s == "tools"])
        self.assertNotIn("tools", {n.id for n in ast.walk(self.tree) if isinstance(n, ast.Name)})

    def test_example_geometry(self):
        consts = [n.value for n in ast.walk(self.tree) if isinstance(n, ast.Constant)]
        self.assertIn(20.0, consts)
        self.assertIn(5.0, consts)
        chamfer = next(c for n, _, c in calls(self.tree) if n == "chamfer")
        self.assertEqual(chamfer.args[1].value, 1.0)


if __name__ == "__main__":
    unittest.main()
