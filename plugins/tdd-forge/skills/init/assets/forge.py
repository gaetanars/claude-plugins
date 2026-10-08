#!/usr/bin/env python3
"""forge.py — moteur déterministe de tdd-forge.

Chaque sous-commande écrit UN objet JSON sur stdout. Code de sortie 0 dès que la
commande a pu s'exécuter (le résultat métier est dans le JSON), 1 en cas d'erreur
technique ({"error": ...}). Exception : `gate` sort en 1 si une porte échoue (CI).

Seul ce script commite, pousse, ouvre et merge les PR. Les agents ne le font jamais.
État durable par tâche : .forge/backlog/<T>/state.json + journal.jsonl (reprise sur erreur).
Contrat de test neutre : code de sortie + résultats JSON (`results_path`), quelle que soit la stack du projet.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

VERSION = "0.3.0"
TAIL = 3000
DISPO = {"corrigé": "corrigé", "corrige": "corrigé", "refusé": "refusé", "refuse": "refusé",
         "reporté": "reporté", "reporte": "reporté"}


class ForgeError(Exception):
    pass


# ---------------------------------------------------------------- utilitaires

def emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def run(cmd, cwd, timeout=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), shell=isinstance(cmd, str),
                          capture_output=True, text=True, timeout=timeout)


def git(args, cwd, check=True) -> str:
    p = run(["git", *args], cwd)
    if check and p.returncode != 0:
        raise ForgeError(f"git {' '.join(args)} : {p.stderr.strip()[-1500:]}")
    return p.stdout.strip()


def tail(s: str, n: int = TAIL) -> str:
    s = s or ""
    return s if len(s) <= n else "…" + s[-n:]


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def main_root() -> Path:
    cwd = Path.cwd()
    common = Path(git(["rev-parse", "--git-common-dir"], cwd))
    if not common.is_absolute():
        common = (cwd / common).resolve()
    return common.parent


def read_json(p: Path, default):
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


# ---------------------------------------------------------------- contexte

class Ctx:
    def __init__(self, task: str | None = None):
        self.root = main_root()
        self.task = task
        self.td = self.root / ".forge" / "backlog" / task if task else None
        self.wt = self.root / ".forge" / "worktrees" / task if task else None
        cands = ([self.wt / ".forge" / "config.json"] if task else []) + [self.root / ".forge" / "config.json"]
        for c in cands:
            if c.exists():
                self.cfg = json.loads(c.read_text())
                break
        else:
            raise ForgeError("`.forge/config.json` introuvable : lance /tdd-forge:init")

    def state(self) -> dict:
        return read_json(self.td / "state.json", {})

    def save(self, st: dict) -> None:
        self.td.mkdir(parents=True, exist_ok=True)
        (self.td / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=2))

    def log(self, event: str, **data) -> None:
        self.td.mkdir(parents=True, exist_ok=True)
        with (self.td / "journal.jsonl").open("a") as f:
            f.write(json.dumps({"ts": now(), "task": self.task, "event": event, **data},
                               ensure_ascii=False) + "\n")


def _match(rel: str, globs) -> bool:
    rel = rel.replace(os.sep, "/")
    name = rel.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(name, g) for g in globs or [])


def is_acceptance(rel: str, cfg) -> bool:
    return _match(rel, cfg.get("acceptance_globs"))


def is_test(rel: str, cfg) -> bool:
    return is_acceptance(rel, cfg) or _match(rel, cfg.get("test_globs"))


def is_protected(rel: str) -> bool:
    if rel == ".forge/learnings.md":
        return False
    return rel.startswith((".forge/", ".github/", ".claude/", "docs/product/"))


def changed_paths(wt: Path) -> list[str]:
    p = run(["git", "status", "--porcelain=v1", "-uall", "-z"], wt)
    entries, paths, i = p.stdout.split("\0"), [], 0
    while i < len(entries):
        e = entries[i]
        if e:
            code, path = e[:2], e[3:]
            paths.append(path)
            if code[0] in "RC":
                i += 1  # chemin d'origine du renommage
        i += 1
    return paths


def restore(wt: Path, paths: list[str]) -> None:
    for p in paths:
        if run(["git", "cat-file", "-e", f"HEAD:{p}"], wt).returncode == 0:
            git(["checkout", "HEAD", "--", p], wt)
        else:
            f = wt / p
            if f.is_file():
                f.unlink()


def dirty(wt: Path) -> bool:
    return bool(changed_paths(wt))


def commit(wt: Path, msg: str) -> str:
    git(["add", "-A"], wt)
    git(["commit", "-m", msg], wt)
    return git(["rev-parse", "HEAD"], wt)


def ensure_ignored(base: Path, rel_dir: str) -> None:
    d = base / rel_dir
    d.mkdir(parents=True, exist_ok=True)
    if run(["git", "check-ignore", "-q", f"{rel_dir}/x"], base).returncode != 0:
        (d / ".gitignore").write_text("*\n")


def hash_tree(root: Path, cfg) -> dict:
    """Empreinte des fichiers d'acceptation (suivis ou non ignorés, filtrés par `acceptance_globs`)."""
    files = run(["git", "ls-files", "-co", "--exclude-standard", "-z"], root).stdout.split("\0")
    return {f: hashlib.sha256((root / f).read_bytes()).hexdigest()
            for f in sorted(set(files)) if f and is_acceptance(f, cfg) and (root / f).is_file()}


AC_RE = re.compile(r"(?<![A-Za-z])AC[-_ ]?(\d+)", re.I)


def ac_ids(text: str) -> list[str]:
    """Identifiants AC-n normalisés (AC-1, ac_1, AC 01 → AC-1), triés."""
    return [f"AC-{n}" for n in sorted({int(m) for m in AC_RE.findall(text or "")})]


def parse_spec(text: str):
    meta = {}
    if text.startswith("---"):
        for line in text.split("---", 2)[1].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    deps = re.findall(r"T\d+", meta.get("depends_on", ""))
    return meta, ac_ids(text), deps


def spec_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def read_spec(ctx: Ctx):
    f = ctx.td / "spec.md"
    if not f.exists():
        raise ForgeError(f"spec introuvable : {f}")
    return parse_spec(f.read_text())


def known_task(root: Path, remote: str, default: str, t: str) -> bool:
    """Tâche connue : spec locale, ou spec livrée dans docs/product/specs (checkout ou branche par défaut)."""
    rel = f"docs/product/specs/{t}.md"
    return ((root / ".forge" / "backlog" / t / "spec.md").exists() or (root / rel).exists()
            or run(["git", "cat-file", "-e", f"{remote}/{default}:{rel}"], root).returncode == 0)


def delivered(ctx: Ctx, t: str) -> bool:
    if Ctx(t).state().get("status") == "done":
        return True
    cfg = ctx.cfg
    return run(["git", "cat-file", "-e", f"{cfg.get('remote', 'origin')}/{cfg.get('default_branch', 'main')}:"
                f"docs/product/specs/{t}.md"], ctx.root).returncode == 0


# ---------------------------------------------------------------- portes

def results_files(wt: Path, cfg) -> list[Path]:
    """`results_path` peut être un glob ; plusieurs fichiers sont concaténés."""
    return sorted(wt.glob(cfg.get("results_path", ".forge/out/results.json")))


def clear_results(wt: Path, cfg) -> None:
    for f in results_files(wt, cfg):
        f.unlink()


def read_results(wt: Path, cfg):
    """Résultats au format neutre `{"cases": [{name, failed, acs?}]}` : (rapport, None), ou (None, raison)
    si absent, illisible ou hors schéma."""
    files = results_files(wt, cfg)
    if not files:
        return None, f"aucun fichier de résultats à {cfg.get('results_path', '.forge/out/results.json')}"
    cases = []
    for p in files:
        try:
            data = json.loads(p.read_text())
        except (OSError, ValueError) as e:
            return None, f"{p.name} : JSON illisible ({e})"
        raw = data.get("cases") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            return None, f"{p.name} : clé `cases` (liste) absente"
        for n, c in enumerate(raw):
            if not isinstance(c, dict) or not isinstance(c.get("name"), str) or not isinstance(c.get("failed"), bool):
                return None, f"{p.name} : cas {n} invalide (`name` texte et `failed` booléen requis)"
            acs = c.get("acs")
            if acs is not None and (not isinstance(acs, list) or not all(isinstance(a, str) for a in acs)):
                return None, f"{p.name} : cas {n} invalide (`acs` doit être une liste de textes)"
            cases.append({"name": c["name"], "failed": c["failed"], "acs": acs})
    return {"cases": cases}, None


def results_counts(report):
    if report is None:
        return None
    cases = report["cases"]
    return {"total": len(cases), "failed": sum(c["failed"] for c in cases)}


def ac_status(acs: list[str], report) -> dict:
    """Pour chaque AC : nombre de cas qui le portent (`acs` explicite, sinon le nom), et combien échouent."""
    per = {a: {"cases": 0, "failing": 0} for a in acs}
    for c in (report or {"cases": []})["cases"]:
        ids = ac_ids(" ".join(c["acs"])) if c.get("acs") is not None else ac_ids(c["name"])
        for a in set(ids):
            if a in per:
                per[a]["cases"] += 1
                per[a]["failing"] += c["failed"]
    return {"no_case": [a for a in acs if per[a]["cases"] == 0],
            "failing": [a for a in acs if per[a]["failing"] > 0],
            "none_failing": [a for a in acs if per[a]["cases"] > 0 and per[a]["failing"] == 0]}


def run_cmd(cmd: str, wt: Path, timeout: int):
    try:
        p = run(cmd, wt, timeout=timeout)
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return False, f"délai dépassé ({timeout} s)"


def run_gates(wt: Path, cfg) -> dict:
    (wt / ".forge" / "out").mkdir(parents=True, exist_ok=True)
    steps = []
    for g in cfg["gates"]:
        if g.get("tests"):
            clear_results(wt, cfg)
        t0 = time.time()
        ok, out = run_cmd(g["cmd"], wt, g.get("timeout", 1500))
        steps.append({"name": g["name"], "ok": ok, "seconds": round(time.time() - t0, 1),
                      "output": "" if ok else tail(out)})
    report, results_error = read_results(wt, cfg)
    return {"passed": all(s["ok"] for s in steps), "steps": steps, "report": report,
            "results_error": results_error, "tests": results_counts(report), "failed_steps": sum(not s["ok"] for s in steps)}


def diff_info(ctx: Ctx, base: str) -> dict:
    """Taille du changement hors tests et marqueurs de suppression ajoutés, fichiers non suivis compris."""
    wt, cfg = ctx.wt, ctx.cfg
    markers = cfg.get("suppression_markers", [])
    lines, sup = 0, []
    for row in git(["diff", "--numstat", base], wt).splitlines():
        a, d, path = row.split("\t", 2)
        if not is_test(path, cfg) and not is_protected(path) and a != "-":
            lines += int(a) + int(d)
    cur = None
    for line in git(["diff", "-U0", base], wt).splitlines():
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("+") and cur and not is_test(cur, cfg) and not is_protected(cur) and any(m in line for m in markers):
            sup.append(f"{cur}: {line[1:].strip()[:160]}")
    untracked = run(["git", "ls-files", "-o", "--exclude-standard", "-z"], wt).stdout.split("\0")
    for f in untracked:
        if not f or is_test(f, cfg) or is_protected(f) or not (wt / f).is_file():
            continue
        content = (wt / f).read_text(errors="ignore").splitlines()
        lines += len(content)
        sup += [f"{f}: {c.strip()[:160]}" for c in content if any(m in c for m in markers)]
    return {"pr_lines": lines, "max_pr_lines": cfg.get("max_pr_lines", 400), "suppressions": sup}


# ---------------------------------------------------------------- commandes

def cmd_status(ctx: Ctx) -> dict:
    meta, acs, deps = read_spec(ctx)
    st = ctx.state()
    base = {"task": ctx.task, "title": meta.get("title", ""), "review_round": st.get("review_round", 0),
            "pr": st.get("pr_url")}
    if not st.get("approved_hash"):
        return {**base, "next": "invalid", "reason": "spec non approuvée : `forge.py approve` après l'accord de Gaëtan"}
    if spec_hash((ctx.td / "spec.md").read_text()) != st["approved_hash"]:
        return {**base, "next": "invalid", "reason": "spec modifiée depuis son approbation : nouvelle tâche ou nouvel accord"}
    if not acs:
        return {**base, "next": "invalid", "reason": "aucun critère d'acceptation AC-n dans la spec"}
    for d in deps:
        if not delivered(ctx, d):
            return {**base, "next": "invalid", "reason": f"dépendance {d} non livrée"}
    s = st.get("status")
    if s in ("done", "blocked"):
        nxt = s
    elif s in ("shipped", "ci_failed", "ci_absent"):
        nxt = "wait"
    elif not st.get("base_sha") or not ctx.wt.exists():
        nxt = "start"
    elif not (ctx.td / "plan.md").exists():
        nxt = "plan"
    elif not st.get("red_sha"):
        nxt = "red"
    elif not st.get("green"):
        nxt = "green"
    elif not st.get("refactored"):
        nxt = "refactor"
    elif not st.get("review_approved"):
        nxt = "review"
    elif not st.get("learned"):
        nxt = "learn"
    else:
        nxt = "ship"
    return {**base, "next": nxt, "reason": st.get("blocked_reason")}


def cmd_approve(root_ctx: Ctx, tasks: list[str]) -> dict:
    """Fige l'accord client/PO : empreinte sha256 de la spec, relue par `status` avant chaque tâche."""
    cfg, plans = root_ctx.cfg, []
    remote, default = cfg.get("remote", "origin"), cfg.get("default_branch", "main")
    for t in tasks:
        ctx = Ctx(t)
        f = ctx.td / "spec.md"
        if not f.exists():
            raise ForgeError(f"{t} : spec introuvable ({f})")
        text = f.read_text()
        meta, acs, deps = parse_spec(text)
        if meta.get("id") != t:
            raise ForgeError(f"{t} : frontmatter `id` absent ou différent ({meta.get('id')!r})")
        if not meta.get("title"):
            raise ForgeError(f"{t} : frontmatter `title` absent")
        if "depends_on" not in meta:
            raise ForgeError(f"{t} : frontmatter `depends_on` absent (mettre [] sinon)")
        if not acs:
            raise ForgeError(f"{t} : aucun critère d'acceptation AC-n")
        unknown = [d for d in deps if d not in tasks and not known_task(ctx.root, remote, default, d)]
        if unknown:
            raise ForgeError(f"{t} : dépendances inconnues : {', '.join(unknown)}")
        if ctx.state().get("status") not in (None, "approved"):
            raise ForgeError(f"{t} : déjà lancée ({ctx.state().get('status')}) ; un changement est une nouvelle tâche")
        plans.append((ctx, text, acs))
    for ctx, text, _ in plans:
        st = ctx.state()
        st.update(approved_hash=spec_hash(text), approved_at=now(), status=st.get("status") or "approved")
        ctx.save(st)
        ctx.log("approve", hash=st["approved_hash"])
    return {"ok": True, "approved": {c.task: {"acs": a, "hash": c.state()["approved_hash"][:12]} for c, _, a in plans}}


def cmd_backlog(ctx: Ctx) -> dict:
    """Toutes les tâches connues : statut draft|approved|running|blocked|shipped|done."""
    tasks, ids = [], set()
    bdir = ctx.root / ".forge" / "backlog"
    for d in sorted(bdir.glob("T*")) if bdir.exists() else []:
        spec = d / "spec.md"
        if not spec.exists():
            continue
        t = d.name
        ids.add(t)
        text = spec.read_text()
        meta, acs, deps = parse_spec(text)
        st = read_json(d / "state.json", {})
        raw = st.get("status")
        modified = bool(st.get("approved_hash")) and spec_hash(text) != st["approved_hash"]
        if not st.get("approved_hash") or modified:
            status = "draft"
        elif raw in ("blocked", "done"):
            status = raw
        elif raw in ("shipped", "ci_failed", "ci_absent", "closed"):
            status = "shipped"
        elif raw == "running":
            status = "running"
        else:
            status = "approved"
        tasks.append({"id": t, "title": meta.get("title", ""), "status": status, "detail": raw,
                      "depends_on": deps, "acs": acs, "pr": st.get("pr_url"),
                      "reason": st.get("blocked_reason"), "spec_modified": modified})
    delivered_specs = sorted(p.stem for p in (ctx.root / "docs" / "product" / "specs").glob("T*.md")) \
        if (ctx.root / "docs" / "product" / "specs").exists() else []
    used = [int(m.group(1)) for t in ids | set(delivered_specs) if (m := re.fullmatch(r"T(\d+)", t))]
    return {"tasks": tasks, "delivered_specs": delivered_specs, "next_id": f"T{max(used, default=0) + 1:03d}"}


def cmd_start(ctx: Ctx) -> dict:
    s = cmd_status(ctx)
    if s["next"] in ("invalid", "done", "blocked"):
        return {"ok": False, "reason": s.get("reason") or s["next"]}
    cfg, root, st = ctx.cfg, ctx.root, ctx.state()
    ensure_ignored(root, ".forge/worktrees")
    ensure_ignored(root, ".forge/backlog")
    branch, remote, default = f"forge/{ctx.task}", cfg.get("remote", "origin"), cfg.get("default_branch", "main")
    if run(["git", "remote", "get-url", remote], root).returncode == 0:
        git(["fetch", remote, default], root)
        base_ref = f"{remote}/{default}"
    else:
        base_ref = default
    if not ctx.wt.exists():
        if run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], root).returncode == 0:
            git(["worktree", "add", str(ctx.wt), branch], root)
        else:
            git(["worktree", "add", "-b", branch, str(ctx.wt), base_ref], root)
    base_sha = st.get("base_sha") or git(["merge-base", base_ref, branch], root)
    ensure_ignored(ctx.wt, ".forge/out")
    spec_rel = f"docs/product/specs/{ctx.task}.md"
    if not (ctx.wt / spec_rel).exists():
        (ctx.wt / spec_rel).parent.mkdir(parents=True, exist_ok=True)
        (ctx.wt / spec_rel).write_text((ctx.td / "spec.md").read_text())
        commit(ctx.wt, f"docs({ctx.task}): spec")
    (root / ".forge" / "current").write_text(ctx.task)
    st.update(base_sha=base_sha, branch=branch, status="running", started=st.get("started") or now())
    ctx.save(st)
    ctx.log("start", base=base_sha, branch=branch)
    return {"ok": True, "worktree": str(ctx.wt.relative_to(root)), "base_sha": base_sha}


def _stall(ctx: Ctx, st: dict, key: str, progressed: bool) -> bool:
    st[key] = 0 if progressed else st.get(key, 0) + 1
    return st[key] >= ctx.cfg.get("stall_rounds", 2)


def _block(ctx: Ctx, st: dict, reason: str) -> None:
    st.update(status="blocked", blocked_reason=reason)
    ctx.log("blocked", reason=reason)


def cmd_red(ctx: Ctx) -> dict:
    cfg, wt, st = ctx.cfg, ctx.wt, ctx.state()
    _, acs, _ = read_spec(ctx)
    changes = changed_paths(wt)
    non_test = [p for p in changes if not is_test(p, cfg)]
    if non_test:
        restore(wt, non_test)
    tests = [p for p in changes if is_test(p, cfg)]
    acc = [p for p in tests if is_acceptance(p, cfg)]
    problems = []
    if non_test:
        problems.append(f"fichiers hors tests annulés : {', '.join(non_test)}")
    if not acc:
        problems.append(f"aucun test d'acceptation parmi acceptance_globs ({', '.join(cfg.get('acceptance_globs', []))})")
    (wt / ".forge" / "out").mkdir(parents=True, exist_ok=True)
    clear_results(wt, cfg)
    ok, out = run_cmd(cfg["test_cmd"], wt, cfg.get("test_timeout", 1500))
    report, results_error = read_results(wt, cfg)
    counts = results_counts(report)
    ac = ac_status(acs, report)
    if ok:
        problems.append("les tests passent déjà : ils ne prouvent rien, la phase rouge exige un échec")
    elif report is None:
        problems.append(f"résultats de test inexploitables : {results_error}")
    elif counts["failed"] == 0:
        problems.append("échec sans test en échec identifiable dans les résultats (outillage ?)")
    else:
        if ac["no_case"]:
            problems.append(f"critères sans cas de test (l'identifiant AC-n doit figurer dans le nom du cas ou dans `acs`) : {', '.join(ac['no_case'])}")
        if ac["none_failing"]:
            problems.append(f"critères dont aucun test n'échoue : {', '.join(ac['none_failing'])}")
    if problems:
        sig = hashlib.sha256("|".join(problems).encode()).hexdigest()
        blocked = _stall(ctx, st, "stall_red", sig != st.get("red_sig"))
        st["red_sig"] = sig
        if blocked:
            _block(ctx, st, "phase rouge sans progrès")
        ctx.save(st)
        ctx.log("red_refused", problems=problems)
        return {"ok": False, "problems": problems, "tests": counts, "output": tail(out), "blocked": blocked,
                "ac_missing": ac["no_case"] + ac["none_failing"], "ac_failing": ac["failing"]}
    meta, _, _ = read_spec(ctx)
    sha = commit(wt, f"test({ctx.task}): phase rouge — {meta.get('title', '')}")
    st.update(red_sha=sha, tests_baseline=sha, acceptance_hash=hash_tree(wt, cfg), stall_red=0)
    ctx.save(st)
    ctx.log("red", sha=sha, failing=counts)
    return {"ok": True, "red_sha": sha, "tests": counts, "ac_failing": ac["failing"]}


def cmd_green(ctx: Ctx, phase: str) -> dict:
    cfg, wt, st = ctx.cfg, ctx.wt, ctx.state()
    violations = []
    bad = [p for p in changed_paths(wt) if is_test(p, cfg) or is_protected(p)]
    if bad:
        restore(wt, bad)
        violations.append(f"modifications interdites annulées (tests ou config) : {', '.join(bad)}")
    if hash_tree(wt, cfg) != st.get("acceptance_hash"):
        violations.append("le test d'acceptation verrouillé a changé")
    g = run_gates(wt, cfg)
    info = diff_info(ctx, st["base_sha"])
    failed_tests = g["tests"]["failed"] if g["tests"] else None
    _, acs, _ = read_spec(ctx)
    ac = ac_status(acs, g["report"])
    if g["passed"]:
        if g["report"] is None:
            violations.append(f"résultats de test inexploitables : {g['results_error']}")
        if ac["no_case"]:
            violations.append(f"critères sans cas de test dans les résultats : {', '.join(ac['no_case'])}")
        if ac["failing"]:
            violations.append(f"critères avec un test en échec : {', '.join(ac['failing'])}")
    if g["passed"] and not violations:
        if dirty(wt):
            prefix = {"impl": "feat", "refactor": "refactor", "review": "fix"}[phase]
            commit(wt, f"{prefix}({ctx.task}): {phase}")
        if phase == "impl":
            st["green"] = True
        if phase == "refactor":
            st["refactored"] = True
        st.setdefault("progress", {})[phase] = None
        st[f"stall_{phase}"] = 0
        ctx.save(st)
        ctx.log("green", phase=phase, tests=g["tests"], pr_lines=info["pr_lines"])
        return {"passed": True, "tests": g["tests"], **info}
    prev = st.setdefault("progress", {}).get(phase)
    cur = {"failed_steps": g["failed_steps"], "failed_tests": failed_tests}
    progressed = prev is None or cur["failed_steps"] < prev["failed_steps"] or (
        failed_tests is not None and prev.get("failed_tests") is not None and failed_tests < prev["failed_tests"])
    blocked = _stall(ctx, st, f"stall_{phase}", progressed)
    st["progress"][phase] = cur
    if blocked:
        _block(ctx, st, f"phase {phase} sans progrès sur {cfg.get('stall_rounds', 2)} tours")
    ctx.save(st)
    ctx.log("not_green", phase=phase, **cur, violations=violations)
    return {"passed": False, "blocked": blocked, "violations": violations, "tests": g["tests"],
            "failed": [s for s in g["steps"] if not s["ok"]], "ac_missing": ac["no_case"],
            "ac_failing": ac["failing"], **info}


def cmd_tests_update(ctx: Ctx) -> dict:
    cfg, wt, st = ctx.cfg, ctx.wt, ctx.state()
    changes = changed_paths(wt)
    problems = []
    non_test = [p for p in changes if not is_test(p, cfg)]
    acc = [p for p in changes if is_acceptance(p, cfg)]
    if non_test or acc:
        restore(wt, non_test + acc)
        problems.append(f"modifications annulées (hors tests ou acceptation verrouillée) : {', '.join(non_test + acc)}")
    sha = None
    if dirty(wt):
        sha = commit(wt, f"test({ctx.task}): tests issus de la revue")
        st["tests_baseline"] = sha
        ctx.save(st)
    ctx.log("tests_update", sha=sha, problems=problems)
    return {"ok": True, "committed": bool(sha), "problems": problems}


def _review_items(ctx: Ctx, rnd: int):
    data = read_json(ctx.td / f"review-{rnd}.json", None)
    if data is None:
        raise ForgeError(f"review-{rnd}.json absent ou illisible")
    items = data.get("items", [])
    for i in items:
        if not {"id", "severity", "target"} <= i.keys() or i["severity"] not in ("bloquant", "mineur") \
                or i["target"] not in ("code", "tests"):
            raise ForgeError(f"élément de revue mal formé : {json.dumps(i, ensure_ascii=False)[:300]}")
    return items


def cmd_review(ctx: Ctx, rnd: int) -> dict:
    st = ctx.state()
    items = _review_items(ctx, rnd)
    blocking = sum(i["severity"] == "bloquant" for i in items)
    prev = st.get("review_blocking_prev")
    blocked = _stall(ctx, st, "stall_review", prev is None or blocking == 0 or blocking < prev)
    st.update(review_round=rnd, review_blocking_prev=blocking)
    approved = not items
    if approved:
        st["review_approved"] = True
    if blocked:
        _block(ctx, st, "revue sans progrès sur les points bloquants")
    ctx.save(st)
    ctx.log("review", round=rnd, blocking=blocking, items=len(items))
    return {"ok": True, "approved": approved, "blocked": blocked, "blocking": blocking,
            "minor": len(items) - blocking,
            "items_code": sum(i["target"] == "code" for i in items),
            "items_tests": sum(i["target"] == "tests" for i in items)}


def cmd_dispositions(ctx: Ctx, rnd: int) -> dict:
    st = ctx.state()
    items = _review_items(ctx, rnd)
    disp = {}
    for target in ("code", "tests"):
        for d in read_json(ctx.td / f"dispositions-{rnd}-{target}.json", []):
            disp[d.get("id")] = d
    missing = {"code": [], "tests": []}
    invalid = {"code": [], "tests": []}
    for i in items:
        d = disp.get(i["id"])
        if d is None:
            missing[i["target"]].append(i["id"])
            continue
        status = DISPO.get(str(d.get("status", "")).lower())
        if status is None or (status != "corrigé" and not d.get("reason")):
            invalid[i["target"]].append(i["id"])
        else:
            d["status"] = status
    ok = not any(missing.values()) and not any(invalid.values())
    if ok:
        deferred = st.setdefault("deferred", {})
        for i in items:
            d = disp[i["id"]]
            if d["status"] == "reporté":
                deferred[i["id"]] = {"title": d.get("issue_title") or i.get("summary", i["id"]),
                                     "reason": d.get("reason", ""), "detail": i.get("detail", "")}
        counts = {s: sum(disp[i["id"]]["status"] == s for i in items) for s in ("corrigé", "refusé", "reporté")}
        st.setdefault("dispositions", {})[str(rnd)] = counts
        if not any(i["severity"] == "bloquant" for i in items):
            st["review_approved"] = True
        ctx.save(st)
    ctx.log("dispositions", round=rnd, ok=ok, missing=missing, invalid=invalid)
    return {"ok": ok, "missing": missing, "invalid": invalid}


def cmd_mark(ctx: Ctx, key: str) -> dict:
    st = ctx.state()
    st[key] = True
    ctx.save(st)
    ctx.log("mark", key=key)
    return {"ok": True}


def cmd_unblock(ctx: Ctx) -> dict:
    """Reprise manuelle après un blocage : Gaëtan a corrigé ou clarifié, la boucle repart de l'étape en cours."""
    st = ctx.state()
    st.update(status="running", blocked_reason=None, progress={})
    for k in [k for k in st if k.startswith("stall_")]:
        st[k] = 0
    st.pop("review_blocking_prev", None)
    ctx.save(st)
    ctx.log("unblock")
    return {"ok": True, "next": cmd_status(ctx)["next"]}


def cmd_context(ctx: Ctx) -> dict:
    st = ctx.state()
    return {"task": ctx.task, "base_sha": st.get("base_sha"), "worktree": str(ctx.wt.relative_to(ctx.root)),
            "acceptance_globs": ctx.cfg.get("acceptance_globs", []), "test_cmd": ctx.cfg["test_cmd"],
            "results_path": ctx.cfg.get("results_path", ".forge/out/results.json"),
            "gates": [g["name"] for g in ctx.cfg.get("gates", [])],
            "stack": ctx.cfg.get("stack"), "review_round": st.get("review_round", 0),
            **(diff_info(ctx, st["base_sha"]) if st.get("base_sha") else {})}


def metrics(ctx: Ctx) -> dict:
    per = {}
    f = ctx.root / ".forge" / "metrics.jsonl"
    if f.exists():
        for line in f.read_text().splitlines():
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            if m.get("task") != ctx.task:
                continue
            a = per.setdefault(m["agent"], {"runs": 0, "input": 0, "output": 0, "cache_read": 0, "cache_write": 0})
            a["runs"] += 1
            for k in ("input", "output", "cache_read", "cache_write"):
                a[k] += m.get(k, 0)
    total = {k: sum(a[k] for a in per.values()) for k in ("input", "output", "cache_read", "cache_write")}
    return {"per_agent": per, "total": total}


def _gh(args, cwd) -> subprocess.CompletedProcess:
    return run(["gh", *args], cwd)


def _body(ctx: Ctx, st: dict, blocked: str | None, issues: list[str]) -> str:
    meta, acs, _ = read_spec(ctx)
    report = ctx.td / "report.md"
    parts = [report.read_text() if report.exists() else f"## {ctx.task} — {meta.get('title', '')}\n"]
    if blocked:
        parts.insert(0, f"> ⛔ **Tâche bloquée** : {blocked}. PR en brouillon, pas de merge automatique.\n")
    disp = st.get("dispositions", {})
    if disp:
        rows = "\n".join(f"| {r} | {c['corrigé']} | {c['refusé']} | {c['reporté']} |" for r, c in sorted(disp.items()))
        parts.append(f"## Revue\n\n| Tour | Corrigés | Refusés | Reportés |\n|---|---|---|---|\n{rows}\n")
    if issues:
        parts.append("## Points reportés\n\n" + "\n".join(f"- {u}" for u in issues) + "\n")
    m = metrics(ctx)
    if m["per_agent"]:
        rows = "\n".join(f"| {a} | {v['runs']} | {v['input']:,} | {v['output']:,} | {v['cache_read']:,} |"
                         for a, v in sorted(m["per_agent"].items()))
        t = m["total"]
        parts.append("## Consommation\n\n| Agent | Lancements | Entrée | Sortie | Cache lu |\n|---|---|---|---|---|\n"
                     f"{rows}\n| **Total** | | {t['input']:,} | {t['output']:,} | {t['cache_read']:,} |\n")
    parts.append(f"---\n_Généré par tdd-forge {VERSION}. Merge automatique si la CI est verte._")
    return "\n".join(parts)


def cmd_ship(ctx: Ctx, blocked: str | None) -> dict:
    cfg, wt, root, st = ctx.cfg, ctx.wt, ctx.root, ctx.state()
    remote, default, branch = cfg.get("remote", "origin"), cfg.get("default_branch", "main"), f"forge/{ctx.task}"
    if not blocked:
        bad = [p for p in changed_paths(wt) if is_test(p, cfg) or is_protected(p)]
        if bad:
            restore(wt, bad)
        g = run_gates(wt, cfg)
        if not g["passed"]:
            return {"ok": False, "reason": "contrôle final rouge", "failed": [s for s in g["steps"] if not s["ok"]]}
    if dirty(wt):
        commit(wt, f"wip({ctx.task}): travail interrompu" if blocked else f"docs({ctx.task}): apprentissages")
    if _gh(["auth", "status"], root).returncode != 0:
        raise ForgeError("gh non authentifié : lance `gh auth login`")
    git(["push", "-u", remote, branch], wt)
    issues = st.setdefault("issues", {})
    for rid, d in st.get("deferred", {}).items():
        if rid not in issues:
            body = f"Reporté pendant la revue de {ctx.task} ({rid}).\n\n{d['detail']}\n\nMotif : {d['reason']}"
            p = _gh(["issue", "create", "--title", d["title"], "--body", body], wt)
            if p.returncode == 0:
                issues[rid] = p.stdout.strip()
    meta, _, _ = read_spec(ctx)
    body_file = ctx.td / "pr-body.md"
    body_file.write_text(_body(ctx, st, blocked, list(issues.values())))
    view = _gh(["pr", "view", branch, "--json", "url"], wt)
    if view.returncode == 0:
        url = json.loads(view.stdout)["url"]
        _gh(["pr", "edit", url, "--body-file", str(body_file)], wt)
    else:
        args = ["pr", "create", "--base", default, "--head", branch,
                "--title", f"{ctx.task} — {meta.get('title', '')}", "--body-file", str(body_file)]
        p = _gh(args + (["--draft"] if blocked else []), wt)
        if p.returncode != 0:
            raise ForgeError(f"création de PR impossible : {p.stderr.strip()[-800:]}")
        url = p.stdout.strip().splitlines()[-1]
    st["pr_url"] = url
    if blocked:
        _block(ctx, st, blocked)
        ctx.save(st)
        return {"ok": True, "pr": url, "status": "blocked"}
    method = cfg.get("merge_method", "squash")
    auto = _gh(["pr", "merge", url, "--auto", f"--{method}", "--delete-branch"], wt)
    st.update(status="shipped", merge_mode="github" if auto.returncode == 0 else "watch", shipped_epoch=time.time())
    ctx.save(st)
    ctx.log("shipped", pr=url, merge_mode=st["merge_mode"])
    return {"ok": True, "pr": url, "merge_mode": st["merge_mode"]}


def _finalize(ctx: Ctx, st: dict) -> None:
    root, remote = ctx.root, ctx.cfg.get("remote", "origin")
    run(["git", "worktree", "remove", "--force", str(ctx.wt)], root)
    run(["git", "branch", "-D", f"forge/{ctx.task}"], root)
    run(["git", "fetch", remote, "--prune"], root)
    cur = root / ".forge" / "current"
    if cur.exists() and cur.read_text().strip() == ctx.task:
        cur.unlink()
    st.update(status="done", merged=now())
    ctx.save(st)
    ctx.log("merged", pr=st.get("pr_url"))


def cmd_wait_merge(ctx: Ctx, max_seconds: int) -> dict:
    st = ctx.state()
    url, root = st.get("pr_url"), ctx.root
    if not url:
        raise ForgeError("aucune PR enregistrée pour cette tâche")
    deadline = time.time() + max_seconds
    while True:
        v = _gh(["pr", "view", url, "--json", "state"], root)
        state = json.loads(v.stdout).get("state") if v.returncode == 0 else None
        if state == "MERGED":
            _finalize(ctx, st)
            return {"state": "merged", "pr": url}
        if state == "CLOSED":
            st["status"] = "closed"
            ctx.save(st)
            return {"state": "closed", "pr": url}
        c = _gh(["pr", "checks", url, "--json", "name,bucket"], root)
        checks = json.loads(c.stdout) if c.stdout.strip().startswith("[") else []
        if not checks and time.time() - st.get("shipped_epoch", 0) > 180:
            st["status"] = "ci_absent"
            ctx.save(st)
            ctx.log("ci_absent", pr=url)
            return {"state": "ci_absent", "pr": url, "reason": "aucune CI : pas de merge sans CI verte"}
        if any(x.get("bucket") in ("fail", "cancel") for x in checks):
            st["status"] = "ci_failed"
            ctx.save(st)
            ctx.log("ci_failed", pr=url)
            return {"state": "ci_failed", "pr": url, "reason": "CI rouge : PR laissée ouverte"}
        if checks and all(x.get("bucket") in ("pass", "skipping") for x in checks) and st.get("merge_mode") == "watch":
            m = _gh(["pr", "merge", url, f"--{ctx.cfg.get('merge_method', 'squash')}", "--delete-branch"], root)
            if m.returncode != 0:
                return {"state": "merge_failed", "pr": url, "reason": tail(m.stderr, 800)}
        if time.time() > deadline:
            return {"state": "pending", "pr": url}
        time.sleep(30)


PUBLISHABLE = ("PRODUCT.md", "docs/product/", ".forge/conventions.md", ".forge/learnings.md", ".forge/config.json")


def cmd_publish(ctx: Ctx, message: str, paths: list[str], manual: bool) -> dict:
    """Publie des fichiers du checkout principal (vision, décisions, conventions…) par une PR issue de la
    branche par défaut, sans toucher à la branche courante. Merge auto si CI verte, sauf --manual."""
    cfg, root = ctx.cfg, ctx.root
    remote, default = cfg.get("remote", "origin"), cfg.get("default_branch", "main")
    files = []
    for p in paths:
        rel = os.path.normpath(p).replace(os.sep, "/")
        if rel.startswith(("..", "/")) or not any(
                rel == a or (a.endswith("/") and (rel + "/").startswith(a)) for a in PUBLISHABLE):
            raise ForgeError(f"{p} : chemin non publiable (autorisés : {', '.join(PUBLISHABLE)})")
        src = root / rel
        if src.is_dir():
            files += [str(f.relative_to(root)) for f in sorted(src.rglob("*")) if f.is_file()]
        elif src.is_file():
            files.append(rel)
        else:
            raise ForgeError(f"{p} : introuvable dans le checkout principal")
    if not files:
        raise ForgeError("aucun fichier à publier")
    if _gh(["auth", "status"], root).returncode != 0:
        raise ForgeError("gh non authentifié : lance `gh auth login`")
    stamp = time.strftime("%Y%m%d%H%M%S")
    branch, wt = f"product/{stamp}", root / ".forge" / "worktrees" / f"_publish-{stamp}"
    ensure_ignored(root, ".forge/worktrees")
    git(["fetch", remote, default], root)
    git(["worktree", "add", "-b", branch, str(wt), f"{remote}/{default}"], root)
    try:
        for f in files:
            (wt / f).parent.mkdir(parents=True, exist_ok=True)
            (wt / f).write_bytes((root / f).read_bytes())
        git(["add", "--", *files], wt)
        if run(["git", "diff", "--cached", "--quiet"], wt).returncode == 0:
            return {"ok": True, "noop": True, "reason": f"déjà identique à {remote}/{default}"}
        git(["commit", "-m", message], wt)
        git(["push", "-u", remote, branch], wt)
        body = "Connaissance produit publiée par tdd-forge :\n\n" + "\n".join(f"- `{f}`" for f in files)
        p = _gh(["pr", "create", "--base", default, "--head", branch, "--title", message, "--body", body], wt)
        if p.returncode != 0:
            raise ForgeError(f"création de PR impossible : {p.stderr.strip()[-800:]}")
        url = p.stdout.strip().splitlines()[-1]
        merge = "manual"
        if not manual:
            m = _gh(["pr", "merge", url, "--auto", f"--{cfg.get('merge_method', 'squash')}", "--delete-branch"], wt)
            merge = "github" if m.returncode == 0 else "manual"
        # le contenu est dans la PR : on remet le checkout principal à l'état de HEAD pour que le pull ne conflicte pas
        restore(root, [f for f in files if f in changed_paths(root)])
        return {"ok": True, "pr": url, "merge": merge, "files": files}
    finally:
        run(["git", "worktree", "remove", "--force", str(wt)], root)
        run(["git", "branch", "-D", branch], root)


def cmd_doctor(ctx: Ctx, plugin_version: str | None) -> dict:
    """Contrôle déterministe d'une config écrite par un LLM, quelle que soit la stack."""
    cfg, root, checks = ctx.cfg, ctx.root, []

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    missing = [k for k in ("test_cmd", "gates", "results_path", "acceptance_globs", "test_globs") if not cfg.get(k)]
    check("config", not missing, f"clés manquantes : {', '.join(missing)}" if missing else "clés requises présentes")
    if "test_cmd" in cfg:
        (root / ".forge" / "out").mkdir(parents=True, exist_ok=True)
        clear_results(root, cfg)
        ok, out = run_cmd(cfg["test_cmd"], root, cfg.get("test_timeout", 1500))
        if not cfg.get("results_path"):
            check("results", False, "`results_path` absent : les résultats doivent être au format neutre "
                  "(voir references/contract.md) ; lance /tdd-forge:init pour écrire l'adaptateur du projet")
        else:
            rep, err = read_results(root, cfg)
            n = len(rep["cases"]) if rep else 0
            check("results", n >= 1, f"{n} cas de test dans {cfg['results_path']}" if n else
                  f"résultats inexploitables ({err}) ; code de sortie {'0' if ok else '≠0'} : {tail(out, 600)}")
        if not any(g.get("tests") for g in cfg.get("gates", [])):
            check("gates", False, "aucune porte marquée `\"tests\": true` : la traçabilité AC-n n'a pas de résultats")
    url = run(["git", "remote", "get-url", cfg.get("remote", "origin")], root)
    check("remote", url.returncode == 0 and "github.com" in url.stdout, url.stdout.strip() or "remote absent")
    check("gh", _gh(["auth", "status"], root).returncode == 0, "gh authentifié")
    if plugin_version:
        check("version", plugin_version == VERSION, f"moteur {VERSION}, plugin {plugin_version}"
              + ("" if plugin_version == VERSION else " : relance /tdd-forge:init pour mettre à jour"))
    return {"ok": all(c["ok"] for c in checks), "checks": checks}


def cmd_gate() -> int:
    top = Path(git(["rev-parse", "--show-toplevel"], Path.cwd()))
    cfg = json.loads((top / ".forge" / "config.json").read_text())
    g = run_gates(top, cfg)
    g.pop("report", None)
    emit(g)
    return 0 if g["passed"] else 1


# ---------------------------------------------------------------- entrée

def main() -> int:
    ap = argparse.ArgumentParser(prog="forge.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("status", "start", "red", "tests-update", "context", "metrics", "unblock"):
        sub.add_parser(name).add_argument("task")
    p = sub.add_parser("green")
    p.add_argument("task")
    p.add_argument("--phase", choices=["impl", "refactor", "review"], required=True)
    for name in ("review", "dispositions"):
        p = sub.add_parser(name)
        p.add_argument("task")
        p.add_argument("round", type=int)
    p = sub.add_parser("mark")
    p.add_argument("task")
    p.add_argument("key", choices=["learned"])
    p = sub.add_parser("ship")
    p.add_argument("task")
    p.add_argument("--blocked")
    p = sub.add_parser("wait-merge")
    p.add_argument("task")
    p.add_argument("--max-seconds", type=int, default=1500)
    p = sub.add_parser("approve")
    p.add_argument("tasks", nargs="+")
    p = sub.add_parser("publish")
    p.add_argument("message")
    p.add_argument("paths", nargs="+")
    p.add_argument("--manual", action="store_true", help="PR laissée ouverte, sans merge automatique")
    p = sub.add_parser("doctor")
    p.add_argument("--plugin-version")
    sub.add_parser("backlog")
    sub.add_parser("gate")
    sub.add_parser("version")
    a = ap.parse_args()
    try:
        if a.cmd == "gate":
            return cmd_gate()
        if a.cmd == "version":
            emit({"version": VERSION})
            return 0
        if a.cmd in ("approve", "publish", "doctor", "backlog"):
            ctx = Ctx()
            emit({"approve": lambda: cmd_approve(ctx, a.tasks), "backlog": lambda: cmd_backlog(ctx),
                  "publish": lambda: cmd_publish(ctx, a.message, a.paths, a.manual),
                  "doctor": lambda: cmd_doctor(ctx, a.plugin_version)}[a.cmd]())
            return 0
        ctx = Ctx(a.task)
        res = {
            "status": lambda: cmd_status(ctx),
            "start": lambda: cmd_start(ctx),
            "red": lambda: cmd_red(ctx),
            "green": lambda: cmd_green(ctx, a.phase),
            "tests-update": lambda: cmd_tests_update(ctx),
            "review": lambda: cmd_review(ctx, a.round),
            "dispositions": lambda: cmd_dispositions(ctx, a.round),
            "mark": lambda: cmd_mark(ctx, a.key),
            "context": lambda: cmd_context(ctx),
            "unblock": lambda: cmd_unblock(ctx),
            "metrics": lambda: metrics(ctx),
            "ship": lambda: cmd_ship(ctx, a.blocked),
            "wait-merge": lambda: cmd_wait_merge(ctx, a.max_seconds),
        }[a.cmd]()
        emit(res)
        return 0
    except ForgeError as e:
        emit({"error": str(e)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
