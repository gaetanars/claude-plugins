#!/usr/bin/env python3
"""Mechanical check of docs/architecture/ARCHITECTURE.md dependency rules.

Usage: python3 docs/architecture/native/check_arch.py [repo_root]
Exit 0 when every rule holds, 1 otherwise (one line per violation).
Standard library only, no network, deterministic.
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[3])
STDLIB = set(sys.stdlib_module_names)

# Rule 1: standard library only (plus local test helpers).
STDLIB_ONLY = ["plugins/sdlc", "plugins/fdm/bin", "tests", "docs/architecture/native"]
LOCAL_OK = {"tests"}

# Rule 2: fdm-tools may import stdlib, itself and this allowlist only (new entry = ADR).
FDM_TOOLS = "plugins/fdm/lib/fdm_tools"
FDM_TOOLS_THIRD_PARTY = {"build123d", "trimesh", "manifold3d", "matplotlib", "mpl_toolkits", "numpy"}

# Rule 4: plugins never reference another plugin nor the repository tests.
TESTS_REF = re.compile(r"(\.\./)+tests/|\btests/(_common|sdlc_fakebin)\b")


def python_files(base: Path):
    if not base.exists():
        return
    for path in sorted(base.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.suffix == ".py":
            yield path
        elif path.suffix == "":
            with path.open("rb") as handle:
                if b"python" in handle.readline():
                    yield path


def imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module.split(".")[0]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    errors = []

    for scope in STDLIB_ONLY:
        for path in python_files(ROOT / scope):
            for line, name in imports(path):
                if name not in STDLIB and name not in LOCAL_OK:
                    errors.append(f"{rel(path)}:{line}: R1 stdlib only, imports '{name}'")

    allowed = STDLIB | FDM_TOOLS_THIRD_PARTY | {"fdm_tools"}
    for path in python_files(ROOT / FDM_TOOLS):
        for line, name in imports(path):
            if name not in allowed:
                errors.append(f"{rel(path)}:{line}: R2 fdm-tools imports non-allowlisted '{name}'")

    for path in python_files(ROOT):
        if rel(path).startswith("plugins/fdm/lib/"):
            continue
        for line, name in imports(path):
            if name == "fdm_tools":
                errors.append(f"{rel(path)}:{line}: R3 fdm_tools imported outside plugins/fdm/lib/")

    plugins_dir = ROOT / "plugins"
    plugins = sorted(p.name for p in plugins_dir.iterdir() if p.is_dir()) if plugins_dir.exists() else []
    for plugin in plugins:
        others = [p for p in plugins if p != plugin]
        other_ref = re.compile(r"\bplugins/(" + "|".join(map(re.escape, others)) + r")\b") if others else None
        for path in sorted((plugins_dir / plugin).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                if other_ref and other_ref.search(line):
                    errors.append(f"{rel(path)}:{line_no}: R4 plugin '{plugin}' references another plugin")
                if TESTS_REF.search(line):
                    errors.append(f"{rel(path)}:{line_no}: R4 plugin '{plugin}' references repository tests")

    for error in errors:
        print(error)
    print("arch OK" if not errors else f"arch: {len(errors)} violation(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
