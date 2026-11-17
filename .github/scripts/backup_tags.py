#!/usr/bin/env python3
"""Create durable backup tags backup/<UTC date-time>/<branch> (plan §8.1 layer 1, T-041).

Runs in .github/workflows/backup.yml on every push to main/staging and on every pushed backup request branch
archive/backup-<YYYYmmdd-HHMMSS>-<branch> (cloud sessions cannot push tags; tools/integrate.py pushes the request).
A tip that already has a backup tag for the same branch is not tagged twice. Tags are never moved or deleted.

    python backup_tags.py --ref-name <branch> --sha <sha> [--before <sha>] [--push] [--now YYYYmmdd-HHMMSS]
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess

ZERO = "0" * 40
REQUEST = re.compile(r"^archive/backup-(\d{8}-\d{6})-(.+)$")


def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, text=True, capture_output=True)


def plan(ref_name: str, sha: str, before: str, now: str, existing: dict[str, list[str]]) -> list[tuple[str, str]]:
    """Return [(tag, sha)] to create. `existing` maps sha -> backup tag names pointing at it."""
    match = REQUEST.match(ref_name)
    stamp, branch = (match.group(1), match.group(2)) if match else (now, ref_name)
    wanted = [(f"backup/{stamp}/{branch}", sha)]
    if before and before != ZERO and not match:
        wanted.append((f"backup/{stamp}/{branch}-before", before))
    out = []
    for tag, target in wanted:
        already = [t for t in existing.get(target, []) if t.endswith("/" + tag.split("/", 2)[2])]
        if not already:
            out.append((tag, target))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref-name", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--before", default="")
    ap.add_argument("--now", default="")
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()
    now = a.now or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    git("fetch", "--quiet", "origin", "+refs/tags/backup/*:refs/tags/backup/*", check=False)
    existing: dict[str, list[str]] = {}
    for line in git("for-each-ref", "--format=%(*objectname) %(objectname) %(refname:short)", "refs/tags/backup").stdout.splitlines():
        peeled, obj, name = line.split(" ", 2)  # peeled is empty for lightweight tags
        existing.setdefault(peeled or obj, []).append(name)
    before = a.before
    if before and before != "0" * 40:
        # Only a non-fast-forward push (forbidden by the rulesets) leaves the old tip unreachable; tag it then.
        if git("cat-file", "-e", f"{before}^{{commit}}", check=False).returncode or \
                git("merge-base", "--is-ancestor", before, a.sha, check=False).returncode == 0:
            before = ""
    todo = plan(a.ref_name, a.sha, before, now, existing)
    if not todo:
        print(f"{a.ref_name} {a.sha[:12]} already has a backup tag")
        return 0
    for tag, target in todo:
        git("-c", "user.name=github-actions[bot]", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "tag", "-a", tag, target, "-m", f"Backup of {a.ref_name} at {target} (plan §8.1)")
        print(f"created {tag} -> {target[:12]}")
        if a.push:
            git("push", "origin", f"refs/tags/{tag}")
            print(f"pushed {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
