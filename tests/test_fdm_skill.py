"""Skill fdm:design : cohérence avec les commandes et l'exemple du plugin (hors ligne)."""
import re
import unittest
from pathlib import Path

from tests._common import parse_frontmatter

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/fdm"
SKILL = PLUGIN / "skills/design/SKILL.md"
DATA = '--data "${CLAUDE_PLUGIN_DATA}"'
COMMANDS = {
    "fdm-setup": 'fdm-setup --data "${CLAUDE_PLUGIN_DATA}" --python "${user_config.python}"',
    "fdm-profiles": 'fdm-profiles --data "${CLAUDE_PLUGIN_DATA}" --machine "${user_config.machine}" '
                    '--process "${user_config.process}" --filament "${user_config.filament}" '
                    '--profiles-dir "${user_config.bambu_profiles}"',
    "fdm-run": 'fdm-run --data "${CLAUDE_PLUGIN_DATA}" parts/<nom>.py',
    "fdm-slice": 'fdm-slice --data "${CLAUDE_PLUGIN_DATA}" --bambu-studio "${user_config.bambu_studio}" out/<nom>.stl',
}


def snippets(text):
    """Extraits de code : spans en accent grave et lignes des blocs clôturés."""
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif fenced:
            out.append(line)
        else:
            out += re.findall(r"`([^`]+)`", line)
    return out


class Skill(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_frontmatter(self):
        fm = parse_frontmatter(SKILL)
        self.assertEqual(fm["name"], "design")
        self.assertNotIn("disable-model-invocation", fm)
        for word in ("conception", "modification", "vérification", "découpe", "3D"):
            self.assertIn(word, fm["description"])

    def test_commands_exist(self):
        names = set(re.findall(r"\bfdm-[a-z]+\b", self.text))
        self.assertTrue(names)
        for n in names:
            self.assertTrue((PLUGIN / "bin" / n).is_file(), n)

    def test_invocations_pass_data(self):
        seen = set()
        for snip in snippets(self.text):
            for m in re.finditer(r"\b(fdm-(?:setup|profiles|run|slice))\s+\S", snip):
                seen.add(m.group(1))
                with self.subTest(snippet=snip):
                    self.assertIn(DATA, snip)
        self.assertEqual(seen, set(COMMANDS))

    def test_exact_commands(self):
        for name, cmd in COMMANDS.items():
            with self.subTest(cmd=name):
                self.assertIn(cmd, self.text)

    def test_plugin_root_paths_exist(self):
        paths = [p.rstrip(".,)") for p in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)", self.text)]
        self.assertIn("lib/fdm_tools/examples/calibration_cube.py", paths)
        for p in paths:
            self.assertTrue((PLUGIN / p).exists(), p)

    def test_prerequisites_and_runpy(self):
        for s in ("${CLAUDE_PLUGIN_DATA}/venv/bin/python", "machine.json", "process.json", "filament.json",
                  "sys.path[0]", "from fdm_tools import check", "check()"):
            self.assertIn(s, self.text)

    def test_generic_rules(self):
        for s in ("0.4", "PLA", "out/<nom>.png", ".3mf"):
            self.assertIn(s, self.text)
        for s in ("256", "A1"):
            self.assertNotIn(s, self.text)


if __name__ == "__main__":
    unittest.main()
