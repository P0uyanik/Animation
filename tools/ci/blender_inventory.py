#!/usr/bin/env python3
"""T-127 proof (a): the Blender tier runs the exact same commands before and after sharding.

    python tools/ci/blender_inventory.py [--before <git rev>] [--out <json>]

Dry run, no Blender: tools/check_all.py's run_logged is replaced by a recorder (every command "succeeds" and every
file "exists", so each command that can run is listed). The pre-T-127 check_blender (from --before) runs once on one
runner; the new one runs once per shard of tools/ci/blender_shards.json. Paths are normalised (<ROOT>, <OUT>, ...).
Exit 1 unless the two command lists are the same multiset, the shards are disjoint and their union is every unit.
Both the full tier (CI: --full --regression-external) and the fast tier (no changed character) are compared.
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))


def load(source: str, name: str):
    path = Path(tempfile.mkdtemp(prefix="t127-")) / f"{name}.py"  # sibling imports resolve through sys.path
    path.write_text(source.replace("Path(__file__).resolve().parents[1]", repr(str(ROOT)).join(("Path(", ")"))),
                    encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def record(module, tier: str, units=None) -> list[str]:
    commands: list[str] = []
    out = Path(tempfile.gettempdir()) / "t127-inventory"
    blender = str(out / "blender")
    engine = out / "plush-render"

    def fake_run(command, log_path, *, append=False, env=None):
        text = " ".join(str(part) for part in command)
        for value, token in ((str(out), "<OUT>"), (str(ROOT), "<ROOT>"), (sys.executable, "<PY>")):
            text = text.replace(value, token)
        commands.append(f"{text}  > {Path(log_path).name}")
        return 0, 0.0

    tier_info = {"tier": tier, "full_paths": []}
    kwargs = {} if units is None else {"units": units}
    with mock.patch.object(module, "run_logged", fake_run), \
         mock.patch.object(Path, "is_file", lambda self: True), \
         mock.patch.object(Path, "write_text", lambda self, *a, **k: 0), \
         mock.patch.object(module.tempfile, "mkdtemp", lambda **k: str(out)), \
         mock.patch.object(module.shutil, "copy2", lambda *a, **k: None), \
         mock.patch.object(module.shutil, "rmtree", lambda *a, **k: None), \
         mock.patch.object(module.shutil, "which", lambda name: name):
        module.check_blender(blender, out, out / "logs", True, set(), tier_info, "origin/main", "",
                             "linux regression jobs" if tier == "full" else "", "", engine, **kwargs)
    return commands


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", default="6016b1b", help="pre-T-127 revision of tools/check_all.py")
    parser.add_argument("--out", default="", help="write the inventory JSON here")
    args = parser.parse_args()
    before = load(subprocess.run(["git", "show", f"{args.before}:tools/check_all.py"], cwd=ROOT, check=True,
                                 capture_output=True, text=True).stdout, "check_all_before")
    after = load((ROOT / "tools/check_all.py").read_text(encoding="utf-8"), "check_all_after")
    plan = after.blender_shard_plan()
    assigned = [unit for units in plan["shards"].values() for unit in units]
    problems = []
    if sorted(assigned) != sorted(after.BLENDER_UNIT_IDS) or len(set(assigned)) != len(assigned):
        problems.append("shards are not a partition of the units")
    report = {"before": args.before, "plan": plan, "tiers": {}}
    for tier in ("full", "fast"):
        old = record(before, tier)
        single = record(after, tier)
        shards = {k: record(after, tier, units) for k, units in plan["shards"].items()}
        new = [command for k in plan["shards"] for command in shards[k]]
        same = collections.Counter(old) == collections.Counter(new)
        if not same:
            problems.append(f"{tier}: sharded commands differ from the pre-T-127 commands")
        if old != single:
            problems.append(f"{tier}: unsharded (fallback) commands or their order differ from the pre-T-127 path")
        report["tiers"][tier] = {"before": old, "after_unsharded_identical": old == single,
                                 "after_shards": shards, "same_multiset": same,
                                 "count_before": len(old), "count_after": len(new)}
        print(f"{tier}: {len(old)} commands before, {len(new)} after in {plan['count']} shards; "
              f"same set and arguments: {same}; fallback identical incl. order: {old == single}")
    report["problems"] = problems
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for problem in problems:
        print("FAIL " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
