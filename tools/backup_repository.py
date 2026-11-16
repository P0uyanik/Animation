#!/usr/bin/env python3
"""Create, verify, rotate and optionally restore-test a local git bundle."""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd=ROOT):
    print("+", subprocess.list2cmdline([str(part) for part in command]), flush=True)
    return subprocess.run(command, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--keep", type=int, default=7)
    parser.add_argument("--restore-test", action="store_true")
    args = parser.parse_args()
    if args.keep < 1:
        raise SystemExit("--keep must be at least 1")

    destination = Path(args.destination).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final = destination / f"plush-studio-{stamp}.bundle"
    partial = destination / f".{final.name}.{os.getpid()}.partial"
    if final.exists() or partial.exists():
        raise SystemExit(f"backup target already exists: {final}")

    try:
        run(["git", "bundle", "create", str(partial), "--all"])
        run(["git", "bundle", "verify", str(partial)])
        os.replace(partial, final)
        if args.restore_test:
            with tempfile.TemporaryDirectory(prefix="plush-bundle-restore-") as temp:
                restored = Path(temp) / "restored"
                run(["git", "clone", str(final), str(restored)], cwd=Path(temp))
                run(["git", "fsck", "--full"], cwd=restored)
                run(["git", "rev-parse", "--verify", "HEAD"], cwd=restored)
    finally:
        if partial.exists():
            partial.unlink()

    backups = sorted(destination.glob("plush-studio-*.bundle"), key=lambda path: path.stat().st_mtime, reverse=True)
    for old in backups[args.keep:]:
        old.unlink()
        print(f"rotated {old}")
    print(f"verified backup: {final}")


if __name__ == "__main__":
    main()
