#!/usr/bin/env python3
"""Safely stage, promote, or revert integration changes using Git only."""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


PROTECTED_BRANCHES = {"main", "staging", "relay-channel", "supervisor-state"}


class IntegrationError(RuntimeError):
    pass


def command_text(command: list[str]) -> str:
    return subprocess.list2cmdline(command) if os.name == "nt" else " ".join(command)


def run(command: list[str], *, cwd: Path, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"+ {command_text(command)}", flush=True)
    proc = subprocess.run(
        command, cwd=cwd, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None,
    )
    if capture:
        if proc.stdout:
            print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        if proc.stderr:
            print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
    if check and proc.returncode:
        raise IntegrationError(f"command failed ({proc.returncode}): {command_text(command)}")
    return proc


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo, check=check)


def git_output(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if check and proc.returncode:
        raise IntegrationError(proc.stderr.strip() or proc.stdout.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def repository_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode:
        raise IntegrationError("run this command inside a Git working tree")
    return Path(proc.stdout.strip()).resolve()


def require_ref(repo: Path, ref: str) -> str:
    value = git_output(repo, "rev-parse", "--verify", ref, check=False)
    if not value:
        raise IntegrationError(f"required ref does not exist: {ref}")
    return value


def fetch(repo: Path, dry_run: bool) -> None:
    if dry_run:
        print("DRY-RUN: would fetch origin")
    else:
        git(repo, "fetch", "origin")


def validate_branch_name(repo: Path, branch: str) -> None:
    if branch.startswith("-") or branch.startswith("origin/"):
        raise IntegrationError("use a branch name without an origin/ prefix")
    proc = subprocess.run(["git", "check-ref-format", "--branch", branch], cwd=repo)
    if proc.returncode:
        raise IntegrationError(f"invalid branch name: {branch}")


def ensure_no_unpushed_wip(repo: Path, branch: str, remote_sha: str) -> None:
    local_ref = f"refs/heads/{branch}"
    local_sha = git_output(repo, "rev-parse", "--verify", local_ref, check=False)
    if local_sha and local_sha != remote_sha:
        ahead = int(git_output(repo, "rev-list", "--count", f"origin/{branch}..{local_ref}"))
        behind = git_output(repo, "rev-list", "--count", f"{local_ref}..origin/{branch}")
        if ahead:
            raise IntegrationError(
                f"local {branch} has unpushed commits (unpushed={ahead}, remote-only={behind})"
            )

    porcelain = git_output(repo, "worktree", "list", "--porcelain")
    current_path: Path | None = None
    for line in porcelain.splitlines() + [""]:
        if line.startswith("worktree "):
            current_path = Path(line[9:])
        elif line == f"branch {local_ref}" and current_path is not None:
            if git_output(current_path, "status", "--porcelain"):
                raise IntegrationError(f"branch {branch} has uncommitted work in {current_path}")
        elif not line:
            current_path = None


def guarded_patterns(repo: Path) -> list[str]:
    path = repo / "tools" / "guarded_paths.txt"
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def path_matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        if not any(char in pattern for char in "*?["):
            return path.startswith(pattern)
        pattern += "*"
    return fnmatch.fnmatchcase(path, pattern) if any(char in pattern for char in "*?[") else path == pattern


def missing_guarded_approvals(repo: Path, base: str, branch: str) -> list[str]:
    changed = git_output(repo, "diff", "--name-only", f"{base}...{branch}").splitlines()
    guarded = sorted(path for path in changed
                     if any(path_matches(path, pattern) for pattern in guarded_patterns(repo)))
    messages = git_output(repo, "log", "--format=%B%x00", f"{base}..{branch}")
    approved: set[str] = set()
    for message in messages.split("\0"):
        approved.update(value.strip().replace("\\", "/")
                        for value in re.findall(r"(?im)^Supervisor-Approved:\s*(\S.*?)\s*$", message))
    return [path for path in guarded if path not in approved]


def temp_parent(repo: Path) -> Path:
    parent = repo / "build" / "integrate-worktrees"
    parent.mkdir(parents=True, exist_ok=True)
    return parent


def remove_worktree(repo: Path, path: Path) -> None:
    git(repo, "worktree", "remove", "--force", str(path), check=False)


def task_id(branch: str) -> str:
    match = re.search(r"(?i)(?:^|/)(t-\d+)", branch)
    return match.group(1).upper() if match else branch


def append_task_log(worktree: Path, task: str, branch: str, commit: str, result: str) -> None:
    log = worktree / "docs" / "process" / "TASK_LOG.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    if not log.exists():
        log.write_text("# Task log\n\n| ID | Task | State | Commit / branch | Notes |\n"
                       "| --- | --- | --- | --- | --- |\n", encoding="utf-8")
    with log.open("a", encoding="utf-8", newline="") as handle:
        handle.write(f"| {task} | Integrated by Supervisor helper | staged | {branch} ({commit[:12]}) | gate {result} |\n")


def check_command(worktree: Path, args: argparse.Namespace, base: str) -> list[str]:
    command = [sys.executable, str(worktree / "tools" / "check_all.py"), "--base", base]
    if args.blender:
        command.extend(["--blender", args.blender])
    if args.build_dir:
        command.extend(["--build-dir", args.build_dir])
    if args.fast:
        command.append("--fast")
    return command


def stage(repo: Path, args: argparse.Namespace) -> None:
    validate_branch_name(repo, args.task_branch)
    if args.task_branch in PROTECTED_BRANCHES:
        raise IntegrationError(f"refusing to stage protected branch {args.task_branch}")
    if args.fast and args.blender:
        raise IntegrationError("--fast and --blender are mutually exclusive")
    fetch(repo, args.dry_run)
    base = "origin/staging"
    branch = f"origin/{args.task_branch}"
    require_ref(repo, base)
    branch_sha = require_ref(repo, branch)
    ensure_no_unpushed_wip(repo, args.task_branch, branch_sha)
    if int(git_output(repo, "rev-list", "--count", f"{base}..{branch}")) < 1:
        raise IntegrationError(f"{branch} is not ahead of {base}")

    missing = missing_guarded_approvals(repo, base, branch)
    if missing:
        print("Guarded paths requiring Supervisor approval trailers:")
        for path in missing:
            print(f"  {path}")
    else:
        print("Guarded paths: all required approval trailers are present")
    if args.dry_run:
        print(f"DRY-RUN: would merge --no-ff {branch}, run the gate, record it, and push HEAD:staging")
        return

    with tempfile.TemporaryDirectory(prefix="stage-", dir=temp_parent(repo)) as raw_temp:
        worktree = Path(raw_temp)
        worktree.rmdir()
        try:
            git(repo, "worktree", "add", "--detach", str(worktree), base)
            merge = git(worktree, "merge", "--no-ff", "--no-edit", branch, check=False)
            if merge.returncode:
                conflicts = git_output(worktree, "diff", "--name-only", "--diff-filter=U").splitlines()
                git(worktree, "merge", "--abort", check=False)
                listing = ", ".join(conflicts) if conflicts else "(Git did not report file names)"
                raise IntegrationError(f"merge conflict; staging was not changed. Conflicting files: {listing}")

            merge_sha = git_output(worktree, "rev-parse", "HEAD")
            gate = run(check_command(worktree, args, base), cwd=worktree, check=False, capture=False)
            if gate.returncode:
                raise IntegrationError("quality gate failed; staging was not changed")
            append_task_log(worktree, task_id(args.task_branch), args.task_branch, merge_sha, "PASS")
            git(worktree, "add", "docs/process/TASK_LOG.md")
            git(worktree, "commit", "-m", f"Log integration of {args.task_branch}",
                "-m", "Gate-Result: PASS", "-m", f"Gate-Commit: {merge_sha}")
            git(worktree, "push", "origin", "HEAD:refs/heads/staging")
            print(f"staged {args.task_branch} at {git_output(worktree, 'rev-parse', 'HEAD')}")
        finally:
            remove_worktree(repo, worktree)


def has_green_record(repo: Path, commit: str) -> bool:
    message = git_output(repo, "show", "-s", "--format=%B", commit)
    return bool(re.search(r"(?im)^Gate-Result:\s*PASS\s*$", message))


def backup_path(directory: Path) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = directory / f"plush-studio-{stamp}.bundle"
    counter = 1
    while candidate.exists():
        candidate = directory / f"plush-studio-{stamp}-{counter}.bundle"
        counter += 1
    return candidate


def prune_patterns(values: list[str]) -> list[str]:
    return [item.strip() for value in values for item in value.split(",") if item.strip()]


def merged_remote_branches(repo: Path) -> list[str]:
    output = git_output(repo, "branch", "-r", "--merged", "origin/main", "--format=%(refname:short)")
    return [remote.strip()[len("origin/"):] for remote in output.splitlines()
            if remote.strip().startswith("origin/") and " -> " not in remote]


def promote(repo: Path, args: argparse.Namespace) -> None:
    fetch(repo, args.dry_run)
    staging = require_ref(repo, "origin/staging")
    main = require_ref(repo, "origin/main")
    if subprocess.run(["git", "merge-base", "--is-ancestor", main, staging], cwd=repo).returncode:
        raise IntegrationError("origin/main cannot be fast-forwarded to origin/staging")

    if has_green_record(repo, staging):
        print(f"green gate record found on origin/staging ({staging})")
    elif args.dry_run:
        print("DRY-RUN: no green record; would re-run tools/check_all.py on origin/staging")
    else:
        with tempfile.TemporaryDirectory(prefix="promote-", dir=temp_parent(repo)) as raw_temp:
            worktree = Path(raw_temp)
            worktree.rmdir()
            try:
                git(repo, "worktree", "add", "--detach", str(worktree), staging)
                gate = run(check_command(worktree, args, "origin/main"), cwd=worktree, check=False, capture=False)
                if gate.returncode:
                    raise IntegrationError("quality gate failed; main was not changed")
            finally:
                remove_worktree(repo, worktree)

    destination = Path(args.backup_dir).expanduser().resolve()
    bundle = backup_path(destination)
    if args.dry_run:
        print(f"DRY-RUN: would create and verify {bundle}")
        print("DRY-RUN: would push origin/staging to main")
        patterns = prune_patterns(args.prune)
        candidates = git_output(
            repo, "branch", "-r", "--merged", "origin/staging", "--format=%(refname:short)"
        ).splitlines()
        for remote in candidates:
            if " -> " in remote:
                continue
            branch = remote.strip()[len("origin/"):] if remote.strip().startswith("origin/") else ""
            if branch and branch not in PROTECTED_BRANCHES and any(
                fnmatch.fnmatchcase(branch, pattern) for pattern in patterns
            ):
                sha = require_ref(repo, f"refs/remotes/origin/{branch}")
                print(f"DRY-RUN: would delete merged branch {branch}: {sha}")
        return

    destination.mkdir(parents=True, exist_ok=True)
    partial = bundle.with_name(f".{bundle.name}.{os.getpid()}.partial")
    try:
        git(repo, "bundle", "create", str(partial), "--all")
        git(repo, "bundle", "verify", str(partial))
        os.replace(partial, bundle)
    finally:
        if partial.exists():
            partial.unlink()
    print(f"verified backup: {bundle}")

    git(repo, "push", "origin", "origin/staging:refs/heads/main")
    git(repo, "fetch", "origin", "main:refs/remotes/origin/main")
    patterns = prune_patterns(args.prune)
    for branch in merged_remote_branches(repo):
        if branch in PROTECTED_BRANCHES or not any(fnmatch.fnmatchcase(branch, pattern) for pattern in patterns):
            continue
        sha = require_ref(repo, f"refs/remotes/origin/{branch}")
        if subprocess.run(["git", "merge-base", "--is-ancestor", sha, "origin/main"], cwd=repo).returncode:
            continue
        subject = git_output(repo, "show", "-s", "--format=%s", sha)
        git(repo, "push", "origin", "--delete", branch)
        print(f"deleted {branch}: {sha} {subject}")
    print(f"promoted origin/staging ({staging}) to main")


def revert_merge(repo: Path, args: argparse.Namespace) -> None:
    fetch(repo, args.dry_run)
    commit = require_ref(repo, args.merge_commit)
    if len(git_output(repo, "show", "-s", "--format=%P", commit).split()) < 2:
        raise IntegrationError(f"{args.merge_commit} is not a merge commit")
    staging = require_ref(repo, "origin/staging")
    if subprocess.run(["git", "merge-base", "--is-ancestor", commit, staging], cwd=repo).returncode:
        raise IntegrationError("merge commit is not contained in origin/staging")
    if args.dry_run:
        print(f"DRY-RUN: would git revert -m 1 {commit} on staging and push without force")
        return

    with tempfile.TemporaryDirectory(prefix="revert-", dir=temp_parent(repo)) as raw_temp:
        worktree = Path(raw_temp)
        worktree.rmdir()
        try:
            git(repo, "worktree", "add", "--detach", str(worktree), staging)
            result = git(worktree, "revert", "-m", "1", commit, check=False)
            if result.returncode:
                git(worktree, "revert", "--abort", check=False)
                raise IntegrationError("revert conflicted; staging was not changed")
            git(worktree, "push", "origin", "HEAD:refs/heads/staging")
            print(f"reverted {commit} on staging at {git_output(worktree, 'rev-parse', 'HEAD')}")
        finally:
            remove_worktree(repo, worktree)


def add_gate_options(target: argparse.ArgumentParser) -> None:
    target.add_argument("--blender", default="", help="pass Blender executable to check_all.py")
    target.add_argument("--build-dir", default="", help="pass build directory to check_all.py")
    target.add_argument("--fast", action="store_true", help="run only the fast gate tier")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    stage_parser = subparsers.add_parser("stage", help="merge a task branch into staging after a green gate")
    stage_parser.add_argument("task_branch")
    add_gate_options(stage_parser)
    stage_parser.add_argument("--dry-run", action="store_true")
    promote_parser = subparsers.add_parser("promote", help="back up, fast-forward main, and safely prune")
    promote_parser.add_argument("--backup-dir", required=True)
    promote_parser.add_argument("--prune", action="append", default=[], metavar="PATTERN",
                                help="branch glob; repeat or comma-separate")
    add_gate_options(promote_parser)
    promote_parser.add_argument("--dry-run", action="store_true")
    revert_parser = subparsers.add_parser("revert", help="revert a merge commit on staging")
    revert_parser.add_argument("merge_commit")
    revert_parser.add_argument("--dry-run", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        repo = repository_root()
        if args.command == "stage":
            stage(repo, args)
        elif args.command == "promote":
            if args.fast and args.blender:
                raise IntegrationError("--fast and --blender are mutually exclusive")
            promote(repo, args)
        else:
            revert_merge(repo, args)
        return 0
    except IntegrationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
