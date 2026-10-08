"""Utilitaires partagés par les tests de validation de la marketplace (stdlib seule)."""
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(os.environ.get("MARKETPLACE_ROOT", Path(__file__).resolve().parent.parent))
MARKETPLACE_JSON = ROOT / ".claude-plugin" / "marketplace.json"
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def marketplace():
    return load_json(MARKETPLACE_JSON)


def plugins():
    """Plugins à source relative déclarés dans la marketplace : [(nom d'entrée, dossier)]."""
    out = []
    for entry in marketplace().get("plugins", []):
        src = entry.get("source")
        if isinstance(src, str):
            out.append((entry["name"], (ROOT / src).resolve()))
    return out


def plugin_dirs():
    return [d for _, d in plugins()]


def parse_frontmatter(path):
    """Frontmatter plat `clé: valeur`. Toute autre syntaxe lève ValueError avec le chemin."""
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: frontmatter absent (première ligne '---' attendue)")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError(f"{path}: frontmatter non fermé") from None
    data = {}
    for n, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z][\w-]*):[ \t]*(.*)$", line)
        if not m:
            raise ValueError(f"{path}:{n}: syntaxe de frontmatter non supportée (clé: valeur sur une ligne): {line!r}")
        value = m.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[m.group(1)] = value
    return data


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def rel(path):
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)
