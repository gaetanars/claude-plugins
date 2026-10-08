#!/usr/bin/env python3
"""Hook PreToolUse de tdd-forge : chaque agent n'écrit et n'exécute que ce que son rôle autorise.

Ne s'applique qu'aux agents du plugin (agent_type « tdd-forge:<rôle> »). Session principale et
autres agents : aucun effet. Refus = code de sortie 2, motif sur stderr (renvoyé à l'agent).
Filet de sécurité de second niveau : forge.py annule de toute façon les écritures interdites.
"""
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

ROLES = {"planner", "test-writer", "implementer", "reviewer", "runner", "learner"}
GIT_WRITE = re.compile(r"\bgit\s+(push|commit|reset|rebase|checkout|switch|merge|cherry-pick|tag|branch|"
                       r"worktree|clean|restore|stash|am|apply|revert)\b")
FORGE = re.compile(r"python3\s+\.forge/bin/forge\.py\s+(\S+)")
FORGE_READONLY = {"status", "context", "metrics", "version", "backlog", "doctor", "plan-check"}
FORGE_PO_ONLY = {"approve", "publish"}  # accord client et publication : jamais un sous-agent, runner compris
KNOWLEDGE_FILES = ("PRODUCT.md", "ARCHITECTURE.md")  # écrits par le PO / l'architecte, jamais par la livraison
KNOWLEDGE_DIRS = ("docs/product/", "docs/architecture/")


def is_knowledge(rel: str) -> bool:
    return rel in KNOWLEDGE_FILES or rel.startswith(KNOWLEDGE_DIRS)


def deny(reason: str) -> None:
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    try:
        with (proj / ".forge" / "guard.log").open("a") as f:
            f.write(reason.replace("\n", " ") + "\n")
    except OSError:
        pass
    print(f"tdd-forge : {reason}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    data = json.load(sys.stdin)
    agent = data.get("agent_type") or ""
    role = agent.split(":")[-1]
    if "tdd-forge" not in agent or role not in ROLES:
        sys.exit(0)
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".").resolve()
    current = proj / ".forge" / "current"
    if not current.exists():
        sys.exit(0)
    task = current.read_text().strip()
    tool, ti = data.get("tool_name", ""), data.get("tool_input") or {}

    if tool == "Bash":
        cmd = ti.get("command", "")
        subs = FORGE.findall(cmd)
        for sub in subs:
            if sub in FORGE_PO_ONLY:
                deny(f"`forge.py {sub}` est réservé au PO et à Gaëtan : aucun sous-agent ne l'exécute")
        if role == "runner":
            if not cmd.strip().startswith("python3 .forge/bin/forge.py "):
                deny("le runner n'exécute que python3 .forge/bin/forge.py <commande>")
            sys.exit(0)
        if GIT_WRITE.search(cmd) or re.search(r"(^|[\s;&|])gh\s", cmd):
            deny("git en écriture et gh sont réservés à forge.py (commit, push, PR, merge)")
        for sub in subs:
            if sub not in FORGE_READONLY:
                deny(f"`forge.py {sub}` est réservé à l'orchestrateur")
        sys.exit(0)

    path = ti.get("file_path") or ti.get("notebook_path")
    if not path:
        sys.exit(0)
    p = Path(path)
    p = (p if p.is_absolute() else proj / p).resolve()
    td = (proj / ".forge" / "backlog" / task).resolve()
    wt = (proj / ".forge" / "worktrees" / task).resolve()
    cfg_file = wt / ".forge" / "config.json"
    cfg = json.loads(cfg_file.read_text()) if cfg_file.exists() else {}
    locked = json.loads((td / "state.json").read_text()).get("red_sha") if (td / "state.json").exists() else None

    in_td = p.is_relative_to(td)
    rel = str(p.relative_to(wt)).replace(os.sep, "/") if p.is_relative_to(wt) else None
    name = p.name

    def matches(r: str, globs) -> bool:
        return any(fnmatch.fnmatch(r, g) or fnmatch.fnmatch(r.rsplit("/", 1)[-1], g) for g in globs)

    def is_acceptance(r: str) -> bool:
        return matches(r, cfg.get("acceptance_globs", []))

    def is_test(r: str) -> bool:
        return is_acceptance(r) or matches(r, cfg.get("test_globs", []))

    if role == "runner":
        deny("le runner n'écrit aucun fichier")
    if role == "planner":
        if in_td and name == "plan.md":
            sys.exit(0)
        deny(f"le planificateur n'écrit que {td}/plan.md")
    if role == "reviewer":
        if in_td and fnmatch.fnmatch(name, "review-*.json"):
            sys.exit(0)
        deny("le relecteur n'écrit que review-<n>.json dans le dossier de tâche")
    if role == "learner":
        if (in_td and name == "report.md") or rel == ".forge/learnings.md":
            sys.exit(0)
        deny("l'agent d'apprentissage n'écrit que report.md et .forge/learnings.md")
    if role == "test-writer":
        if in_td and fnmatch.fnmatch(name, "dispositions-*-tests.json"):
            sys.exit(0)
        if rel and is_knowledge(rel):
            deny("la connaissance produit et l'architecture (PRODUCT.md, ARCHITECTURE.md, docs/) sont hors de portée du rédacteur de tests")
        if rel and is_test(rel):
            if locked and is_acceptance(rel):
                deny("le test d'acceptation est verrouillé depuis la phase rouge")
            sys.exit(0)
        deny("le rédacteur de tests n'écrit que des fichiers de test du worktree")
    if role == "implementer":
        if in_td and fnmatch.fnmatch(name, "dispositions-*-code.json"):
            sys.exit(0)
        if rel is None:
            deny("hors du worktree de la tâche")
        if is_test(rel):
            deny("l'implémenteur ne modifie jamais les tests : fais passer le code, pas le test")
        if rel.startswith((".forge/", ".github/", ".claude/")) or is_knowledge(rel):
            deny("configuration du système, CI, connaissance produit et architecture hors de portée de l'implémenteur")
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
