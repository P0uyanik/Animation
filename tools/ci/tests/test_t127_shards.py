#!/usr/bin/env python3
"""T-127: Blender shard plan, the verdict's shard rules and the before/after command inventory (plain checks)."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import check_all  # noqa: E402

COMBINE = ROOT / ".github/scripts/combine_check_reports.py"


def expect_error(data: dict, text: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "plan.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        try:
            check_all.blender_shard_plan(path)
        except ValueError as exc:
            assert text in str(exc), exc
        else:
            raise AssertionError(f"plan accepted: {data}")


def test_plan() -> None:
    plan = check_all.blender_shard_plan()
    units = [u for v in plan["shards"].values() for u in v]
    assert sorted(units) == sorted(check_all.BLENDER_UNIT_IDS) and len(units) == len(set(units))
    assert 4 <= plan["count"] <= 6, plan["count"]
    all_units = check_all.BLENDER_UNIT_IDS
    expect_error({"count": 2, "shards": {"1": ["nope"]}}, "unknown units")
    expect_error({"count": 2, "shards": {"1": ["boy2"], "2": ["boy2"]}}, "duplicated")
    expect_error({"count": 2, "shards": {"1": [], "2": ["face"]}}, "same shard as charsys")
    expect_error({"count": 1, "shards": {"1": [], "2": []}}, "beyond count")
    with tempfile.TemporaryDirectory() as tmp:  # unassigned units are never dropped: they go to shard 1
        path = Path(tmp) / "plan.json"
        path.write_text(json.dumps({"count": 2, "shards": {"2": ["boy2"]}}), encoding="utf-8")
        got = check_all.blender_shard_plan(path)
        assert got["shards"]["2"] == ["boy2"] and len(got["shards"]["1"]) == len(all_units) - 1
    assert check_all.parse_shard("2/5") == (2, 5)
    for bad in ("0/5", "6/5", "x", ""):
        try:
            check_all.parse_shard(bad)
        except ValueError:
            continue
        raise AssertionError(bad)


def verdict(tmp: Path, shards: dict[int, list[str] | None], count: int, blender: str = "success",
            linux_units: list[str] | None = None) -> tuple[int, str]:
    root = tmp / "reports"
    ok = {"name": "Blender tier", "ok": True, "detail": "x"}
    def write(artifact: str, report: dict) -> None:
        (root / artifact).mkdir(parents=True, exist_ok=True)
        (root / artifact / "check_all.json").write_text(json.dumps({"platform": artifact, "checks": [ok], **report}))
    write("quality-linux", {"blender_units": ["a", "b", "c"] if linux_units is None else linux_units})
    for index, units in shards.items():
        if units is not None:
            write(f"quality-blender-{index}", {"blender_shard": {"index": index, "count": count, "units": units}})
    needs = {job: {"result": "success"} for job in ("plan", "linux")}
    needs["regression"] = {"result": "skipped"}
    needs["blender"] = {"result": blender}
    proc = subprocess.run([sys.executable, str(COMBINE), str(root), str(tmp / "out.txt"), "--needs-json",
                           json.dumps(needs), "--tier", "fast", "--blender-shards", str(count)],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout


def test_verdict() -> None:
    cases = [
        ({1: ["a", "b"], 2: ["c"]}, 2, "success", None, 0, ""),
        ({1: ["a", "b"], 2: None}, 2, "success", None, 1, "no report from quality-blender-2"),
        ({1: ["a", "b"], 2: ["c"]}, 2, "cancelled", None, 1, "job blender cancelled"),
        ({1: ["a", "b"], 2: ["c"]}, 2, "skipped", None, 1, "job blender skipped"),
        ({1: ["a"], 2: ["c"]}, 2, "success", None, 1, "Blender units not run: b"),
        ({1: ["a", "b"], 2: ["b", "c"]}, 2, "success", None, 1, "twice: b"),
        ({}, 0, "skipped", None, 1, "none were planned"),
        ({}, 0, "skipped", [], 0, ""),  # pre-T-127 path: Blender tier in-process, no shards
    ]
    for shards, count, blender, linux_units, code, text in cases:
        with tempfile.TemporaryDirectory() as tmp:
            got, out = verdict(Path(tmp), shards, count, blender, linux_units)
            assert got == code and text in out, (shards, count, blender, got, out)


def test_inventory() -> None:
    revision = "6016b1b"
    have = subprocess.run(["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=ROOT).returncode == 0
    command = [sys.executable, str(ROOT / "tools/ci/blender_inventory.py")]
    if not have:  # no pre-T-127 history in this clone: compare the unsharded path with the shards instead
        command += ["--before", "HEAD"]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    if have:  # T-158: a unit added after T-127 but not listed in added_after_t127 still fails
        data = json.loads(check_all.BLENDER_SHARDS_FILE.read_text(encoding="utf-8"))
        assert data.get("added_after_t127"), "expected listed added units"
        for listed in (data["added_after_t127"][1:], ["nope"]):
            data_unlisted = dict(data, added_after_t127=listed)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "shards.json"
                path.write_text(json.dumps(data_unlisted), encoding="utf-8")
                bad = subprocess.run(command + ["--shards", str(path)], cwd=ROOT, capture_output=True, text=True)
            assert bad.returncode == 1 and "FAIL" in bad.stdout, (listed, bad.stdout + bad.stderr)


if __name__ == "__main__":
    test_plan()
    test_verdict()
    test_inventory()
    print("T-127 shard tests: PASS")
