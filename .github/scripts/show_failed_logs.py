#!/usr/bin/env python3
"""Print the last lines of every failing check's log from check_all.json / regression reports (CI job log only).

    python show_failed_logs.py <folder> [--lines 40]
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("folder", type=Path)
ap.add_argument("--lines", type=int, default=40)
a = ap.parse_args()
root = Path.cwd()
seen = set()
for report in sorted(a.folder.rglob("check_all.json")):
    data = json.loads(report.read_text(encoding="utf-8"))
    for check in data.get("checks", []):
        for item in [check, *check.get("subchecks", [])]:
            log = item.get("log") or ""
            if item.get("ok", True) or not log or log in seen:
                continue
            seen.add(log)
            path = Path(log) if Path(log).is_absolute() else root / log
            print(f"::group::FAILED {item.get('name')}: {log}")
            try:
                print("\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-a.lines:]))
            except OSError as exc:
                print(f"(log unreadable: {exc})")
            print("::endgroup::")
for log in sorted(a.folder.rglob("regression.log")):
    text = log.read_text(encoding="utf-8", errors="replace").splitlines()
    if any("Traceback" in line or "Error" in line for line in text):
        print(f"::group::{log}")
        print("\n".join(text[-a.lines:]))
        print("::endgroup::")
