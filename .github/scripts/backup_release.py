#!/usr/bin/env python3
"""Weekly backup release (plan §8.1 layer 2, T-041), run by .github/workflows/backup.yml after a verified bundle.

On Sundays (UTC), or with --force true: create release backup-<YYYY-MM-DD> with the bundle and its .sha256.
Retention: the 8 newest backup-* releases and the first backup-* release of every month are kept; older weekly
releases lose their release entry and asset. Their backup-<date> tags stay (protected; never deleted).

    python backup_release.py --dir build/backups [--force true|false] [--today YYYY-MM-DD] [--dry-run]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
import subprocess

NAME = re.compile(r"^backup-(\d{4})-(\d{2})-(\d{2})$")


def releases_to_prune(tags: list[str], keep_newest: int = 8) -> list[str]:
    dated = sorted((t for t in tags if NAME.match(t)), reverse=True)
    first_of_month = {}
    for tag in sorted(dated):
        year, month, _day = NAME.match(tag).groups()
        first_of_month.setdefault((year, month), tag)
    keep = set(dated[:keep_newest]) | set(first_of_month.values())
    return [t for t in dated if t not in keep]


def gh(*args, capture=True):
    return subprocess.run(["gh", *args], check=True, text=True, capture_output=capture)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--force", default="false")
    ap.add_argument("--today", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today) if a.today else dt.datetime.now(dt.timezone.utc).date()
    if today.weekday() != 6 and a.force != "true":
        print(f"{today} is not a Sunday; no weekly release")
        return 0
    folder = Path(a.dir)
    bundles = sorted(folder.glob("*.bundle"))
    if len(bundles) != 1:
        raise SystemExit(f"expected one verified bundle in {folder}, found {len(bundles)}")
    report = json.loads((folder / "backup_report.json").read_text(encoding="utf-8"))
    if not report.get("ok") or not report.get("restore", {}).get("ok"):
        raise SystemExit("the bundle did not pass its restore test; no release")
    tag = f"backup-{today.isoformat()}"
    notes = (f"Verified bundle of every branch and tag ({report['branches']} branches, {report['tags']} tags).\n"
             f"SHA-256 {report['sha256']}. Restore test passed ({report['restore']['refs_compared']} refs).\n"
             "Restore: git clone --mirror <bundle> restored.git")
    existing = json.loads(gh("release", "list", "--limit", "200", "--json", "tagName").stdout)
    tags = [r["tagName"] for r in existing]
    if tag in tags:
        print(f"release {tag} already exists")
    elif a.dry_run:
        print(f"DRY-RUN: would create release {tag}")
    else:
        gh("release", "create", tag, str(bundles[0]), f"{bundles[0]}.sha256", "--title", tag, "--notes", notes,
           "--target", "main", capture=False)
        tags.append(tag)
    for old in releases_to_prune(tags):
        if a.dry_run:
            print(f"DRY-RUN: would delete release {old} (tag kept)")
        else:
            gh("release", "delete", old, "--yes", capture=False)  # no --cleanup-tag: backup-* tags stay
            print(f"deleted release {old} (tag kept)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
