#!/usr/bin/env python3
"""Combine OS-specific check_all JSON reports into one <=10-line summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    reports = []
    for path in sorted(args.root.rglob("check_all.json")):
        try:
            reports.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError) as exc:
            reports.append((path, {"platform": path.parent.name, "checks": [{"name": "Report", "ok": False, "detail": str(exc)}]}))
    if not reports:
        lines = ["FAIL Report: no quality-gate artifacts were downloaded"]
    else:
        order: list[str] = []
        grouped: dict[str, list[tuple[str, dict]]] = {}
        for path, report in reports:
            platform = str(report.get("platform") or path.parent.parent.name)
            phase = "branch" if "branch" in path.parts else "trial" if "trial" in path.parts else "report"
            label = f"{platform}/{phase}"
            for check in report.get("checks", []):
                name = str(check.get("name", "unnamed"))
                if name not in grouped:
                    order.append(name)
                    grouped[name] = []
                grouped[name].append((label, check))
        lines = []
        for name in order:
            failures = [(platform, check) for platform, check in grouped[name] if not check.get("ok", False)]
            if not failures:
                detail = ""
                if name == "Merge status":
                    detail = ": clean"
                lines.append(f"PASS {name}{detail}")
                continue
            details = []
            for platform, check in failures:
                detail = str(check.get("detail") or "failed").replace("\n", " ")
                details.append(f"{platform}: {detail}")
            lines.append(f"FAIL {name}: {'; '.join(details)}")
    if len(lines) > 10:
        raise SystemExit(f"combined summary has {len(lines)} lines (maximum 10)")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
