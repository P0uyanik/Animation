#!/usr/bin/env python3
"""Combine the quality-gate reports of one CI run into <= 10 lines and decide the verdict (T-041).

    python combine_check_reports.py <downloaded-artifacts> <summary.txt>
        [--needs-json '<toJSON(needs)>'] [--tier fast|full] [--characters '["a","b"]'] [--windows true|false]

Reports are check_all.json files (tools/check_all.py, tools/regression/run.py --gate-report, trial-merge conflicts).
Checks with the same name are merged into one line. With --needs-json the run also FAILS when a required job did not
succeed or a required report is missing: the linux gate always (the linux renderer job was removed in T-142), one regression report per character on the full
tier, the windows report when the windows job ran. With --blender-shards N (T-127) the job "blender" must have
succeeded and every shard report quality-blender-1..N must be present, name its own shard, and the shards' units must
be exactly the linux report's Blender unit list (each unit once): a missing, cancelled, skipped or partial shard is FAIL.
Exit 1 on any FAIL (the required "Gate verdict" check).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def label_for(path: Path, root: Path, report: dict) -> str:
    try:
        artifact = path.relative_to(root).parts[0]
    except (ValueError, IndexError):
        artifact = path.parent.name
    return f"{report.get('platform') or artifact}:{artifact}"


def blender_shard_problems(reports: list, root: Path, needs: dict, count: int) -> list[str]:
    by_artifact = {path.relative_to(root).parts[0]: report for path, report in reports}
    expected = (by_artifact.get("quality-linux") or {}).get("blender_units") or []
    if count <= 0:
        return ["linux gate delegated the Blender tier to shard jobs, but none were planned"] if expected else []
    problems: list[str] = []
    result = needs.get("blender", {}).get("result", "missing")
    if result != "success":
        problems.append(f"job blender {result}")
    if not expected:
        problems.append("linux report lists no Blender units for the shards")
    ran: list[str] = []
    for index in range(1, count + 1):
        report = by_artifact.get(f"quality-blender-{index}")
        if report is None:
            problems.append(f"no report from quality-blender-{index}")
            continue
        shard = report.get("blender_shard") or {}
        if shard.get("index") != index or shard.get("count") != count:
            problems.append(f"quality-blender-{index} reports shard {shard.get('index')}/{shard.get('count')}")
        ran.extend(shard.get("units") or [])
    missing = sorted(set(expected) - set(ran))
    extra = sorted(set(ran) - set(expected))
    twice = sorted({unit for unit in ran if ran.count(unit) > 1})
    if missing:
        problems.append("Blender units not run: " + ", ".join(missing))
    if extra or twice:
        problems.append("Blender units unexpected or twice: " + ", ".join(extra + twice))
    return problems


def durations_markdown(root: Path, limit: int = 25) -> str:
    """T-127 (combine_check_reports.py --durations <root>): the slowest commands of every report (check_all.json "durations") as a Markdown table."""
    rows = []
    for path in sorted(root.rglob("check_all.json")) if root.is_dir() else []:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        job = path.relative_to(root).parts[0]
        rows += [(float(item.get("seconds", 0)), job, item) for item in report.get("durations", [])]
    rows.sort(key=lambda row: -row[0])
    total = sum(row[0] for row in rows)
    lines = [f"\n**Per-test durations** ({len(rows)} commands, {total / 60:.1f} min in total; slowest {limit}):\n",
             "| seconds | job | command | exit |", "|---:|---|---|---:|"]
    lines += [f"| {seconds:.1f} | {job} | {item.get('script')} ({item.get('log')}) | {item.get('exit')} |"
              for seconds, job, item in rows[:limit]]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--durations":
        print(durations_markdown(Path(sys.argv[2])))
        return 0
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--needs-json", default="")
    parser.add_argument("--tier", default="")
    parser.add_argument("--characters", default="[]")
    parser.add_argument("--windows", default="false",
                        help="true: the windows job ran and is required; informational: it ran, reported but not required")
    parser.add_argument("--blender-shards", type=int, default=0,
                        help="T-127: number of Blender shard jobs that ran instead of the in-process Blender tier")
    args = parser.parse_args()

    reports = []
    for path in sorted(args.root.rglob("check_all.json")) if args.root.is_dir() else []:
        try:
            reports.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError) as exc:
            reports.append((path, {"platform": path.parent.name,
                                   "checks": [{"name": "Report", "ok": False, "detail": str(exc)}]}))

    problems: list[str] = []
    if args.needs_json:
        needs = json.loads(args.needs_json)
        required = {"plan": True, "linux": True, "regression": args.tier == "full", "windows": args.windows == "true"}
        for job, must in required.items():
            result = needs.get(job, {}).get("result", "missing")
            if must and result != "success":
                problems.append(f"job {job} {result}")
        artifacts = {path.relative_to(args.root).parts[0] for path, _ in reports}
        expected = ["quality-linux"]
        if args.tier == "full":
            expected += [f"regression-{c}" for c in json.loads(args.characters or "[]")]
        if args.windows == "true":
            expected.append("quality-windows")
        problems += [f"no report from {name}" for name in expected if name not in artifacts]
        problems += blender_shard_problems(reports, args.root, needs, args.blender_shards)
        if args.tier not in {"fast", "full"}:
            problems.append(f"tier not decided ({args.tier or 'plan failed'})")

    order: list[str] = []
    grouped: dict[str, list[tuple[str, dict]]] = {}
    info: list[str] = []
    for path, report in reports:
        label = label_for(path, args.root, report)
        if args.windows == "informational" and path.relative_to(args.root).parts[0] == "quality-windows":
            failed = [str(c.get("name")) for c in report.get("checks", []) if not c.get("ok", False)]
            info.append("INFO windows (not required yet): " + (f"FAIL {', '.join(failed)}" if failed else "all PASS"))
            continue
        for check in report.get("checks", []):
            name = str(check.get("name", "unnamed"))
            if name not in grouped:
                order.append(name)
                grouped[name] = []
            grouped[name].append((label, check))
    lines = []
    for name in order:
        failures = [(label, check) for label, check in grouped[name] if not check.get("ok", False)]
        if not failures:
            detail = ""
            if name in {"Merge status", "Blender tier", "Write-set"}:
                values = []
                for _label, check in grouped[name]:
                    value = str(check.get("detail") or "").replace("\n", " ")
                    if value and value not in values:
                        values.append(value)
                if values:
                    detail = ": " + " | ".join(values)
            lines.append(f"PASS {name}{detail}")
            continue
        details = [f"{label}: {str(check.get('detail') or 'failed').replace(chr(10), ' ')}" for label, check in failures]
        lines.append(f"FAIL {name}: {'; '.join(details)}")
    if not reports:
        problems.append("no quality-gate reports were downloaded")
    if problems:
        lines.append("FAIL CI jobs: " + "; ".join(problems))
    checks = len(lines)
    if checks > 10:
        raise SystemExit(f"combined summary has {checks} check lines (maximum 10)")
    if args.tier:
        lines.insert(0, f"Tier: {args.tier}")
    if args.windows == "informational" and not info:
        info.append("INFO windows (not required yet): no report")
    lines.extend(info)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if any(line.startswith("FAIL") for line in lines) else 0


if __name__ == "__main__":
    raise SystemExit(main())
