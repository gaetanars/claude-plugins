#!/usr/bin/env python3
"""Hook SubagentStop de tdd-forge : additionne l'usage de la transcription d'un agent du plugin
et l'ajoute à .forge/metrics.jsonl (une ligne par lancement). Ne bloque jamais (sortie 0)."""
import json
import os
import sys
import time
from pathlib import Path


def main() -> None:
    try:
        data = json.load(sys.stdin)
        agent = data.get("agent_type") or ""
        if "tdd-forge" not in agent:
            return
        proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
        current = proj / ".forge" / "current"
        transcript = data.get("agent_transcript_path")
        if not current.exists() or not transcript or not Path(transcript).exists():
            return
        seen, tot = set(), {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
        model = None
        for line in Path(transcript).read_text(errors="ignore").splitlines():
            try:
                msg = json.loads(line).get("message") or {}
            except json.JSONDecodeError:
                continue
            u = msg.get("usage")
            if not u:
                continue
            mid = msg.get("id")
            if mid in seen:  # un même message peut occuper plusieurs lignes
                continue
            seen.add(mid)
            model = msg.get("model") or model
            tot["input"] += u.get("input_tokens", 0)
            tot["output"] += u.get("output_tokens", 0)
            tot["cache_read"] += u.get("cache_read_input_tokens", 0)
            tot["cache_write"] += u.get("cache_creation_input_tokens", 0)
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "task": current.read_text().strip(),
               "agent": agent.split(":")[-1], "model": model, **tot}
        with (proj / ".forge" / "metrics.jsonl").open("a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:  # la mesure ne doit jamais casser la boucle
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
