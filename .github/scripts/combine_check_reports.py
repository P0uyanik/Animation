#!/usr/bin/env python3
"""Combine the quality-gate reports of one CI run into <= 10 lines and decide the verdict (T-041).

    python combine_check_reports.py <downloaded-artifacts> <summary.txt>
        [--needs-json '<toJSON(needs)>'] [--tier fast|full] [--characters '["a","b"]'] [--windows true|false]

Reports are check_all.json files (tools/check_all.py, tools/regression/run.py --gate-report, trial-merge conflicts).
Checks with the same name are merged into one line. With --needs-json the run also FAILS when a required job did not
succeed or a required report is missing: the linux gate always, one regression report per character on the full
tier, the windows report when the windows job ran. Exit 1 on any FAIL (the required "Gate verdict" check).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def label_for(path: Path, root: Path, report: dict) -> str:
    try:
        artifact = path.relative_to(root).parts[0]
    except (ValueError, IndexError):
        artifact = path.parent.name
    return f"{report.get('platform') or artifact}:{artifact}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--needs-json", default="")
    parser.add_argument("--tier", default="")
    parser.add_argument("--characters", default="[]")
    parser.add_argument("--windows", default="false")
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
        if args.tier not in {"fast", "full"}:
            problems.append(f"tier not decided ({args.tier or 'plan failed'})")

    order: list[str] = []
    grouped: dict[str, list[tuple[str, dict]]] = {}
    for path, report in reports:
        label = label_for(path, args.root, report)
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
    if args.tier:
        lines.insert(0, f"Tier: {args.tier}")
    if len(lines) > 11:  # tier header + at most 10 check lines
        raise SystemExit(f"combined summary has {len(lines)} lines (maximum 10 checks)")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if any(line.startswith("FAIL") for line in lines) else 0


if __name__ == "__main__":
    raise SystemExit(main())
