#!/usr/bin/env python3
"""Cast check (T-062): animation evaluations use the current approved character versions.

    python3 tools/check_cast.py [--base <ref>] [--json <path>]

Checked shots:
- every shot in content/scenes/eval/ (the shared evaluation shots), and
- every docs/evaluation/**/shot*.scene.json that is new on this branch (added since the merge base with --base;
  default origin/staging, else origin/main, else main; without a base only the evaluation shots are checked).

Each cast entry must be {"character_id": <id>, "version": "current"} (resolved by pipeline/production/run_shot.py
from docs/evaluation/characters/fidelity_baseline.json), or an explicit source (version_dir, or spec + overrides)
that resolves to the same version as "current". An explicit source of any other version FAILS unless the entry
carries a non-empty "legacy_reason" (for example a frozen regression comparison that needs the old version).
Evaluation shots additionally must use "current" itself, so they never fall behind a newly approved version.

Exempt (documented in docs/process/GATE.md): the engine's unit-test packages under tests/data (frozen; they are
packages, not shots), and shots that already existed before this check (episodes/, older docs/evaluation evidence),
which are historical records of what was rendered at the time.

Also reports, for information, characters with a current version that no evaluation shot casts yet.
Exit 0 when every checked shot passes, 1 otherwise."""
from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = "content/scenes/eval"
NEW_SHOT_GLOB = "docs/evaluation/**/shot*.scene.json"


def load_run_shot():
    spec = importlib.util.spec_from_file_location("run_shot", ROOT / "pipeline" / "production" / "run_shot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)


def choose_base(explicit: str) -> str:
    for ref in ([explicit] if explicit else ["origin/staging", "origin/main", "main"]):
        if git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode == 0:
            return ref
    return ""


def new_evaluation_shots(base: str) -> list[str]:
    if not base:
        return []
    common = git("merge-base", base, "HEAD").stdout.strip() or base
    out = git("diff", "--name-only", "--diff-filter=A", "-z", common, "--").stdout
    added = {p for p in out.split("\0") if p}
    # untracked files count as new, too (a local run before the commit)
    added |= {p for p in git("ls-files", "--others", "--exclude-standard", "-z", "docs/evaluation").stdout.split("\0") if p}
    return sorted(p for p in added if matches(p, NEW_SHOT_GLOB))


def matches(path: str, pattern: str) -> bool:
    """'**/' may be empty (docs/evaluation/x/shot.scene.json and docs/evaluation/a/b/shot.scene.json both match)."""
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, pattern.replace("**/", ""))


def evaluation_shots(root: Path = ROOT) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in (root / EVAL_DIR).rglob("*.scene.json")
                  if "build" not in p.relative_to(root / EVAL_DIR).parts)


def explicit_version(src: dict, root: Path) -> tuple[str, str]:
    """(character id, version) of an explicit cast source."""
    if "version_dir" in src:
        manifest = json.loads((root / src["version_dir"] / "manifest.json").read_text(encoding="utf-8"))
        return manifest["character_id"], manifest["version"]
    spec = json.loads((root / src["spec"]).read_text(encoding="utf-8"))
    version = spec.get("metadata", {}).get("spec_version", "")
    for item in src.get("overrides", []):
        data = json.loads((root / item).read_text(encoding="utf-8")).get("override", {})
        version = data.get("metadata", {}).get("spec_version", version)
    return spec["identity"]["id"], version or "unversioned"


def check_shot(path: str, require_current: bool, run_shot, root: Path = ROOT) -> dict:
    """Problems of one shot's cast (an empty list = pass) and the character ids it casts."""
    problems, cast_ids = [], []
    try:
        shot = json.loads((root / path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"shot": path, "problems": [f"unreadable: {exc}"], "characters": []}
    cast = (shot.get("production") or {}).get("cast") or {}
    if not cast:
        problems.append("no production.cast")
    for name, src in sorted(cast.items()):
        if not isinstance(src, dict):
            problems.append(f"{name}: cast entry is not an object")
            continue
        legacy = isinstance(src.get("legacy_reason"), str) and src["legacy_reason"].strip()
        try:
            if src.get("version") == "current":
                cid = src.get("character_id")
                run_shot.current_source(cid, str(root))  # must resolve
                cast_ids.append(cid)
                continue
            cid, version = explicit_version(src, root)
            cast_ids.append(cid)
            current = run_shot.current_source(cid, str(root))["resolved"]["version"]
        except (SystemExit, OSError, KeyError, ValueError) as exc:
            problems.append(f"{name}: cast does not resolve ({exc})")
            continue
        if legacy:
            continue
        if version != current:
            problems.append(f"{name}: pins {cid} {version}, current is {current} "
                            f"(use {{\"character_id\": \"{cid}\", \"version\": \"current\"}} or add \"legacy_reason\")")
        elif require_current:
            problems.append(f"{name}: evaluation shots use {{\"character_id\": \"{cid}\", \"version\": \"current\"}}, "
                            f"not an explicit source (it would fall behind the next approved version)")
    return {"shot": path, "problems": problems, "characters": sorted(set(cast_ids))}


def run(base: str, root: Path = ROOT) -> dict:
    run_shot = load_run_shot()
    eval_shots = evaluation_shots(root)
    results = [check_shot(p, True, run_shot, root) for p in eval_shots]
    results += [check_shot(p, False, run_shot, root) for p in new_evaluation_shots(base) if p not in eval_shots]
    baseline = json.loads((root / run_shot.FIDELITY_BASELINE).read_text(encoding="utf-8"))
    cast_in_eval = {c for r in results if r["shot"] in eval_shots for c in r["characters"]}
    not_cast = sorted(set(baseline.get("characters", {})) - cast_in_eval)
    problems = [f"{r['shot']}: {p}" for r in results for p in r["problems"]]
    if not eval_shots:
        problems.append(f"no evaluation shots in {EVAL_DIR}")
    return {"pass": not problems, "base": base, "checked": [r["shot"] for r in results], "problems": problems,
            "current_characters_not_in_evaluation_shots": not_cast, "results": results}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    report = run(choose_base(a.base))
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"cast check: {'PASS' if report['pass'] else 'FAIL'}: {len(report['checked'])} shot(s) checked "
          f"(base {report['base'] or 'none'})")
    for problem in report["problems"]:
        print(f"  FAIL {problem}")
    if report["current_characters_not_in_evaluation_shots"]:
        print("  info: current characters not cast in any evaluation shot yet: "
              + ", ".join(report["current_characters_not_in_evaluation_shots"]))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
