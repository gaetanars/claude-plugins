#!/usr/bin/env python3
"""PreToolUse : demande l'accord avant de modifier un test d'acceptation déjà suivi par git."""
import json
import os
import subprocess
import sys


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)


def main():
    data = json.load(sys.stdin)
    cwd = data.get("cwd") or os.getcwd()
    path = (data.get("tool_input") or {}).get("file_path")
    if not path:
        return
    top = git(cwd, "rev-parse", "--show-toplevel")
    if top.returncode:
        return
    root = os.path.realpath(top.stdout.strip())
    try:
        with open(os.path.join(root, ".claude", "check.json")) as f:
            acceptance = json.load(f)["acceptance_dir"]
    except (OSError, KeyError, ValueError):
        return
    path = os.path.realpath(path if os.path.isabs(path) else os.path.join(cwd, path))
    base = os.path.join(root, acceptance)
    if os.path.commonpath([path, base]) != base:
        return
    if git(root, "ls-files", "--error-unmatch", "--", path).returncode:
        return
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": "test d'acceptation commité : modification soumise à ton accord",
    }}, sys.stdout)


if __name__ == "__main__":
    main()
