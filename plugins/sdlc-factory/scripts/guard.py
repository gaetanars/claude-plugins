#!/usr/bin/env python3
"""Garde-fou PreToolUse du SDLC (déterministe, indépendant du modèle).

Actif seulement si SDLC_WORKTREE est défini (posé par sdlc-run / sdlc-retro) : hors de ce cadre
(session interactive, poste) le hook ne fait rien. Code de sortie 2 = action refusée.
Échoue en mode fermé : toute exception (entrée illisible, bug) refuse l'action.

Variables : SDLC_WORKTREE (racine d'écriture), SDLC_ROLE (planner|implementer|reviewer|retro),
SDLC_ALLOW_READ (racines de lecture supplémentaires, séparées par ':').

Limites connues : un shell peut encore écrire hors worktree par des moyens indirects (mv, cp, tee…)
ou lire ce que l'utilisateur Unix peut lire. Le vrai périmètre est l'utilisateur Unix dédié.
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path


def deny(msg):
    print(f"[sdlc-guard] refusé : {msg}", file=sys.stderr)
    sys.exit(2)


WT_ENV = os.environ.get("SDLC_WORKTREE")
if not WT_ENV:
    sys.exit(0)

WT = Path(WT_ENV).resolve()
ROLE = os.environ.get("SDLC_ROLE", "implementer")
READ_ROOTS = [WT] + [Path(p).resolve() for p in os.environ.get("SDLC_ALLOW_READ", "").split(os.pathsep) if p]

PROTECTED = {
    "implementer": [r"^\.git(/|$)", r"^\.github/", r"^\.claude/", r"^docs/features/", r"^docs/adr/", r"^docs/architecture/"],
    # La rétro ne touche ni au garde-fou, ni à l'orchestrateur, ni à ses bibliothèques, ni aux tests, ni à la marketplace.
    # plugins/*/.claude-plugin/plugin.json reste modifiable (bump de version exigé par la CI).
    "retro": [r"^\.git(/|$)", r"^\.github/", r"^tests/", r"^\.claude-plugin/",
              r"^plugins/sdlc-factory/(scripts|hooks|bin|lib|deploy|schemas)/", r"^plugins/sdlc-[^/]+/bin/"],
}

BLOCKED_BASH = [
    (r"\bsudo\b|(^|[;&|]\s*)su\s", "élévation de privilèges"),
    (r"\bgit\s+(-C\s+\S+\s+)?push\b", "git push est réservé à l'orchestrateur"),
    (r"\bgit\s+(-C\s+\S+\s+)?(reset\s+--hard|clean|rebase|remote|config|worktree|gc|filter-branch|update-ref|reflog\s+expire)\b",
     "commande git destructive ou de configuration"),
    (r"\bgit\s+branch\s+(-[dDmM]\b|--delete|--move)", "suppression/renommage de branche"),
    (r"\bgit\s+checkout\s+(-f\b|--force)", "checkout forcé"),
    (r"--no-verify|--no-gpg-sign", "contournement des hooks git"),
    (r"(^|[\s;&|(])gh(\s|$)", "gh est interdit à l'agent"),
    (r"\b(curl|wget|ncat|ssh|scp|rsync|telnet)\b", "accès réseau direct interdit"),
    (r"(^|[;&|]\s*)(printenv|env)\s*($|[;&|])|/proc/\S*environ", "lecture de l'environnement"),
    (r"\.config/gh|/\.ssh\b|~/\.ssh|\$HOME/\.ssh|\.netrc|\.aws/|\.claude/\.credentials|\.claude\.json", "accès aux secrets"),
    (r"\b(mkfs|shutdown|reboot|systemctl|crontab|chroot)\b|\bdd\s+if=", "commande système"),
    (r">\s*/(etc|usr|bin|sbin|home|root|var|opt)/|>>?\s*~", "écriture hors worktree"),
]

READONLY_GIT = re.compile(r"^\s*git\s+(diff|log|show|status|blame|ls-files|grep|rev-parse|rev-list)\b[^;&|`$<>\n]*$")


def inside(p: Path, root: Path) -> bool:
    return p == root or root in p.parents


def resolve(p: str, cwd: str) -> Path:
    q = Path(os.path.expanduser(p))
    if not q.is_absolute():
        q = Path(cwd) / q
    return Path(os.path.normpath(q))


def glob_prefix(pattern: str) -> str:
    m = re.search(r"[*?\[{]", pattern)
    return pattern[: m.start()] if m else pattern


def check_read(ti, cwd):
    cands = [ti.get("file_path"), ti.get("path")]
    pat = ti.get("pattern")
    # Glob : le motif peut être absolu ; Grep : « pattern » est une regex, on ne le traite pas.
    if ti.get("_tool") == "Glob" and pat:
        cands.append(glob_prefix(pat) if (pat.startswith(("/", "~")) or ".." in pat) else None)
    if ti.get("glob"):
        g = ti["glob"]
        cands.append(glob_prefix(g) if (g.startswith(("/", "~")) or ".." in g) else None)
    for c in cands:
        if not c:
            continue
        p = resolve(c, cwd)
        if not any(inside(p, r) for r in READ_ROOTS):
            deny(f"lecture hors périmètre : {p}")


def check_write(path, cwd):
    if not path:
        deny("chemin d'écriture manquant")
    p = resolve(path, cwd)
    if not inside(p, WT):
        deny(f"écriture hors du worktree : {p}")
    rel = p.relative_to(WT).as_posix() if p != WT else "."
    for pat in PROTECTED.get(ROLE, PROTECTED["implementer"]):
        if re.search(pat, rel):
            deny(f"chemin protégé pour le rôle {ROLE} : {rel}")


def check_rm(cmd, cwd):
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        deny("commande illisible")
    in_rm = False
    for t in toks:
        if t in (";", "&&", "||", "|", "&", "(", ")"):
            in_rm = False
            continue
        if not in_rm:
            in_rm = Path(t).name == "rm"
            continue
        if t.startswith("-"):
            continue
        if re.search(r"[$`]", t):
            deny("rm avec expansion non vérifiable")
        p = resolve(t, cwd)
        if p == WT or not inside(p, WT):
            deny(f"rm hors périmètre : {p}")
        if p.relative_to(WT).parts[:1] == (".git",):
            deny("rm dans .git")


def check_bash(cmd, cwd):
    if ROLE == "planner":
        deny("pas de shell pour le planner")
    if ROLE == "reviewer":
        if not READONLY_GIT.match(cmd) or "--output" in cmd:
            deny("revue en lecture seule : seules les commandes git de lecture sont permises")
        return
    for pat, why in BLOCKED_BASH:
        if re.search(pat, cmd):
            deny(why)
    check_rm(cmd, cwd)


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    ti = dict(data.get("tool_input") or {})
    cwd = data.get("cwd") or str(WT)
    ti["_tool"] = tool
    if tool == "Bash":
        check_bash(ti.get("command", ""), cwd)
    elif tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        if ROLE in ("reviewer", "planner"):
            deny(f"écriture interdite pour le rôle {ROLE}")
        check_write(ti.get("file_path") or ti.get("notebook_path") or "", cwd)
    elif tool in ("Read", "Grep", "Glob"):
        check_read(ti, cwd)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001 — mode fermé : une panne du garde-fou ne laisse jamais passer l'action
        deny(f"erreur interne du garde-fou ({type(e).__name__}: {e})")
