#!/usr/bin/env python3
"""Stop : lance la commande check si l'arbre a changé ; bloque (exit 2) tant qu'elle est rouge, 3 essais max."""
import hashlib
import json
import os
import subprocess
import sys

MAX_FAILS = 3


def run(cwd, *args):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def main():
    data = json.load(sys.stdin)
    cwd = data.get("cwd") or os.getcwd()
    top = run(cwd, "git", "rev-parse", "--show-toplevel")
    if top.returncode:
        return 0
    root = top.stdout.strip()
    try:
        with open(os.path.join(root, ".claude", "check.json")) as f:
            check = json.load(f)["check"]
    except (OSError, KeyError, ValueError):
        return 0
    if not run(root, "git", "status", "--porcelain").stdout.strip():
        return 0
    h = hashlib.sha256()
    for out in (run(root, "git", "rev-parse", "HEAD"), run(root, "git", "diff", "HEAD"),
                run(root, "git", "ls-files", "--others", "--exclude-standard")):
        h.update(out.stdout.encode())
    digest = h.hexdigest()
    state_path = os.path.join(root, ".claude", "check-state.json")
    try:
        with open(state_path) as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    if state.get("green") == digest:
        return 0
    res = run(root, "bash", "-c", check)
    if res.returncode == 0:
        state = {"green": digest, "fails": 0}
        code = 0
    else:
        fails = state.get("fails", 0) + 1
        tail = "\n".join((res.stdout + res.stderr).splitlines()[-60:])
        if fails < MAX_FAILS:
            state["fails"] = fails
            print(f"check rouge ({fails}/{MAX_FAILS}) :\n{tail}", file=sys.stderr)
            code = 2
        else:
            state["fails"] = 0
            print(f"portes rouges après {MAX_FAILS} tentatives, intervention humaine.\n{tail}", file=sys.stderr)
            code = 0
    with open(state_path, "w") as f:
        json.dump(state, f)
    return code


if __name__ == "__main__":
    sys.exit(main())
