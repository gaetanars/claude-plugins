"""Briques communes de sdlc-run et sdlc-retro (bibliothèque standard uniquement)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# lib/ -> sdlc-factory -> plugins -> racine du dépôt marketplace
SDLC_HOME = Path(os.environ.get("SDLC_HOME") or Path(__file__).resolve().parents[3])
CONTRACT = SDLC_HOME / "plugins" / "sdlc-contract"
FACTORY = SDLC_HOME / "plugins" / "sdlc-factory"
SCHEMAS = FACTORY / "schemas"
WORKDIR = Path(os.environ.get("SDLC_WORKDIR") or Path.home() / "sdlc-work")
CALL_TIMEOUT = int(os.environ.get("SDLC_CALL_TIMEOUT", "3600"))
BUDGET = os.environ.get("SDLC_BUDGET_USD", "")  # plafond par appel ; vide = aucun
SECRET_VARS = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
CHECK_SECRET_VARS = SECRET_VARS + ("ANTHROPIC_API_KEY",)  # `check` n'en a pas besoin
ALLOWED_DOMAINS = [d.strip() for d in os.environ.get(
    "SDLC_ALLOWED_DOMAINS", "pypi.org,files.pythonhosted.org,registry.npmjs.org").split(",") if d.strip()]

# Lecture seule des relecteurs : motifs natifs de permission (le hook guard.py reste en défense en profondeur).
REVIEWER_TOOLS = "Read,Grep,Glob," + ",".join(
    f"Bash(git {c} *)" for c in ("diff", "log", "show", "status", "blame", "grep", "ls-files", "rev-parse"))

# rôle -> (agent, rôle du garde-fou, outils pré-approuvés, max_turns : mêmes valeurs que le frontmatter de l'agent)
ROLES = {
    "planner": ("planner", "planner", "Read,Grep,Glob", 40),
    "implementer": ("implementer", "implementer", "Read,Edit,Write,Grep,Glob,Bash", 150),
    "reviewer-correctness": ("reviewer-correctness", "reviewer", REVIEWER_TOOLS, 40),
    "reviewer-security": ("reviewer-security", "reviewer", REVIEWER_TOOLS, 40),
    "reviewer-simplicity": ("reviewer-simplicity", "reviewer", REVIEWER_TOOLS, 40),
    "retro": ("retro", "retro", "Read,Grep,Glob,Edit,Write", 60),
}


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


def sh(*args, cwd=None, input=None, check=True, env=None, timeout=None):
    r = subprocess.run([str(a) for a in args], cwd=cwd, input=input, capture_output=True, text=True,
                       env=env, timeout=timeout)
    if check and r.returncode:
        cmd = " ".join(str(a) for a in args)[:200]
        raise RuntimeError(f"{cmd} → code {r.returncode}\n{(r.stderr or r.stdout).strip()[:2000]}")
    return r.stdout.strip()


def gh(*args, **kw):
    return sh("gh", *args, **kw)


def ghjson(*args):
    return json.loads(gh(*args) or "null")


def git(wt, *args, **kw):
    return sh("git", "-C", str(wt), *args, **kw)


def sandbox_settings(cwd):
    """Réglages `--settings` : sandbox natif obligatoire (échec si indisponible), écriture limitée au worktree et au
    .git du clone de base (nécessaire à `git commit` dans un worktree), réseau limité aux domaines autorisés.
    Le sandbox ne couvre que les commandes Bash : les écritures de fichiers restent filtrées par guard.py."""
    allow_write = [str(cwd)]
    gitfile = Path(cwd) / ".git"
    if gitfile.is_file():  # worktree : « gitdir: <base>/.git/worktrees/<id> »
        gd = gitfile.read_text(encoding="utf-8").strip().removeprefix("gitdir:").strip()
        allow_write.append(str(Path(gd).parents[1]))
    return {"sandbox": {"enabled": True, "failIfUnavailable": True, "allowUnsandboxedCommands": False,
                        "filesystem": {"allowWrite": allow_write},
                        "network": {"allowedDomains": ALLOWED_DOMAINS}}}


def call_claude(role, prompt, cwd, calls, schema=None, phase="", allow_read=()):
    """Lance `claude -p` sous l'identité d'un agent du plugin sdlc-factory.

    Avec `schema` : retourne structured_output (dict). Sinon : retourne le texte final.
    Un appel invalide est retenté une fois ; au second échec : RuntimeError.
    """
    agent, guard_role, tools, max_turns = ROLES[role]
    # --setting-sources user : ni hooks, ni env, ni .mcp.json du dépôt cible (ses CLAUDE.md restent lus comme fichiers).
    cmd = ["claude", "-p", "--agent", f"sdlc-factory:{agent}",
           "--plugin-dir", str(CONTRACT), "--plugin-dir", str(FACTORY),
           "--output-format", "json", "--allowedTools", tools, "--permission-mode", "dontAsk",
           "--setting-sources", "user", "--settings", json.dumps(sandbox_settings(cwd)),
           "--max-turns", str(max_turns), "--no-session-persistence"]
    if schema:
        cmd += ["--json-schema", json.dumps(json.loads(Path(schema).read_text(encoding="utf-8")))]
    if BUDGET:
        cmd += ["--max-budget-usd", BUDGET]
    env = {k: v for k, v in os.environ.items() if k not in SECRET_VARS}  # l'agent ne voit jamais le jeton GitHub
    env.update(SDLC_WORKTREE=str(cwd), SDLC_ROLE=guard_role,
               SDLC_ALLOW_READ=os.pathsep.join([str(SDLC_HOME), *map(str, allow_read)]))
    last = ""
    for attempt in (1, 2):
        t0 = time.time()
        r = subprocess.run(cmd, input=prompt, cwd=cwd, env=env, capture_output=True, text=True, timeout=CALL_TIMEOUT)
        try:
            out = json.loads(r.stdout)
        except ValueError:
            out = {}
        calls.append({"phase": phase, "role": role, "attempt": attempt,
                      "cost_usd": out.get("total_cost_usd") or 0, "turns": out.get("num_turns"),
                      "subtype": out.get("subtype"), "permission_denials": len(out.get("permission_denials") or []),
                      "duration_s": round(time.time() - t0)})
        structured = out.get("structured_output")
        ok = r.returncode == 0 and not out.get("is_error") and (isinstance(structured, dict) if schema else True)
        if ok:
            return structured if schema else (out.get("result") or "")
        last = (out.get("result") or r.stderr or r.stdout or "")[:800]
        log(f"appel {role} invalide (tentative {attempt}) : {last[:200]}")
    raise RuntimeError(f"appel {role} en échec après 2 tentatives : {last}")
