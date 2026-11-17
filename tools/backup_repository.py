#!/usr/bin/env python3
"""Create, verify, checksum, rotate and restore-test a git bundle of every branch and tag (plan §8.1, T-041).

    python tools/backup_repository.py --destination <dir> [--remote <url>] [--keep 7] [--restore-test]
        [--git-config key=value ...] [--report <json>] [--github-output <file>]

Without --remote the local repository's refs are bundled (legacy local use). With --remote, a bare snapshot of the
remote's refs/heads/* and refs/tags/* is fetched first (pull-request refs are not backed up), so the bundle holds
exactly the remote's branches and tags. Steps: git bundle create --all, git bundle verify, <bundle>.sha256.
--restore-test: clone the bundle into an empty bare repository, git fsck --full, require every branch and tag SHA
to equal the snapshot (the remote at backup time; refs that moved on the remote since are listed as information),
and check out main into <destination>/restore/main for the fast-tier run (see .github/workflows/backup.yml).
Exit 1 if anything fails.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd=ROOT, capture=False, config=()):
    command = [str(part) for part in command]
    if command[0] == "git":
        command = ["git", *[x for item in config for x in ("-c", item)], *command[1:]]
    shown = [part if "extraheader" not in part else "http.extraheader=***" for part in command]
    print("+", subprocess.list2cmdline(shown), flush=True)
    return subprocess.run(command, cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None)


def refs_of(git_dir: Path) -> dict[str, str]:
    out = run(["git", "--git-dir", git_dir, "for-each-ref", "--format=%(objectname) %(refname)",
               "refs/heads", "refs/tags"], capture=True).stdout
    return dict(reversed(line.split(" ", 1)) for line in out.splitlines() if line.strip())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--remote", default="", help="back up this remote's branches and tags (default: local refs)")
    parser.add_argument("--keep", type=int, default=7)
    parser.add_argument("--restore-test", action="store_true")
    parser.add_argument("--git-config", action="append", default=[], help="extra 'git -c' settings (e.g. auth)")
    parser.add_argument("--report", default="")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args(argv)
    if args.keep < 1:
        raise SystemExit("--keep must be at least 1")

    destination = Path(args.destination).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final = destination / f"plush-studio-{stamp}.bundle"
    partial = destination / f".{final.name}.{os.getpid()}.partial"
    if final.exists() or partial.exists():
        raise SystemExit(f"backup target already exists: {final}")
    report = {"schema": "plush-studio.backup/1", "created_utc": stamp, "remote": bool(args.remote), "ok": False}

    try:
        if args.remote:
            snapshot = destination / "snapshot.git"
            if snapshot.exists():
                shutil.rmtree(snapshot)
            run(["git", "init", "--bare", "--quiet", snapshot])
            run(["git", "--git-dir", snapshot, "fetch", "--quiet", "--no-tags", args.remote,
                 "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*"], config=args.git_config)
            source = snapshot
        else:
            source = Path(run(["git", "rev-parse", "--absolute-git-dir"], capture=True).stdout.strip())
        expected = refs_of(source)
        if not any(name.startswith("refs/heads/") for name in expected):
            raise SystemExit("no branches to back up")
        run(["git", "--git-dir", source, "bundle", "create", partial, "--all"])
        run(["git", "bundle", "verify", partial])
        os.replace(partial, final)
        checksum = sha256_file(final)
        Path(f"{final}.sha256").write_text(f"{checksum}  {final.name}\n", encoding="utf-8")
        (destination / "refs.txt").write_text("".join(f"{sha} {name}\n" for name, sha in sorted(expected.items())),
                                              encoding="utf-8")
        report.update(bundle=final.name, sha256=checksum, bytes=final.stat().st_size,
                      branches=sum(n.startswith("refs/heads/") for n in expected),
                      tags=sum(n.startswith("refs/tags/") for n in expected))

        if args.restore_test:
            restore = destination / "restore"
            if restore.exists():
                shutil.rmtree(restore)
            restored = restore / "restored.git"
            run(["git", "clone", "--quiet", "--mirror", final, restored])
            run(["git", "--git-dir", restored, "fsck", "--full", "--no-progress"])
            actual = refs_of(restored)
            mismatches = sorted(name for name in set(expected) | set(actual) if expected.get(name) != actual.get(name))
            moved = []
            if args.remote:
                live = run(["git", "ls-remote", "--heads", "--tags", args.remote], capture=True,
                           config=args.git_config).stdout
                live_refs = {name: sha for sha, name in (line.split("\t", 1) for line in live.splitlines() if "\t" in line)
                             if not name.endswith("^{}")}
                moved = sorted(name for name in set(expected) | set(live_refs) if expected.get(name) != live_refs.get(name))
            worktree = ""
            if "refs/heads/main" in actual:
                worktree_path = restore / "main"
                run(["git", "clone", "--quiet", "--branch", "main", restored, worktree_path])
                worktree = worktree_path.as_posix()
            report["restore"] = {"ok": not mismatches, "refs_compared": len(expected), "mismatches": mismatches,
                                 "moved_on_remote_since_snapshot": moved, "worktree": worktree}
            print(f"restore test: {len(expected)} refs compared, {len(mismatches)} mismatch(es); "
                  f"{len(moved)} ref(s) moved on the remote since the snapshot")
            if mismatches:
                raise SystemExit("restore test FAILED: " + ", ".join(mismatches[:10]))
    finally:
        if partial.exists():
            partial.unlink()

    backups = sorted(destination.glob("plush-studio-*.bundle"), key=lambda path: path.stat().st_mtime, reverse=True)
    for old in backups[args.keep:]:
        old.unlink()
        Path(f"{old}.sha256").unlink(missing_ok=True)
        print(f"rotated {old}")
    report["ok"] = True
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"bundle={final.name}\n")
    print(f"verified backup: {final} sha256 {report['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
