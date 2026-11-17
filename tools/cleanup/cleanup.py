#!/usr/bin/env python3
"""Branch cleanup runner (T-048): gathers git facts, applies tools/cleanup/select.py, deletes, logs, restores.

Used by .github/workflows/cleanup.yml and by the tests (against local bare repositories). See
docs/process/CLEANUP.md.

    cleanup.py hash --request REQUEST.json
    cleanup.py runs-to-verify --request REQUEST.json --dry-run-log DRY_RUN_LOG.jsonl
    cleanup.py run --repo . --request REQUEST.json --task-log TASK_LOG.md --backup-runs runs.json \
        --dry-run-log DRY_RUN_LOG.jsonl --verified-runs verified.json --cleanup-log CLEANUP_LOG.md \
        --summary summary.md --run-id 123 [--allow-delete]
    cleanup.py restore --repo . --cleanup-log CLEANUP_LOG.md --branch NAME
"""

from __future__ import annotations

import os
import sys

# tools/cleanup/select.py shadows the standard-library module ``select`` that ``subprocess`` imports, so this
# directory must never be on sys.path. Remove it before anything else is imported and load select.py by path.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]

import argparse  # noqa: E402
import datetime as dt  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import subprocess  # noqa: E402


def load_select():
    name = "plush_cleanup_select"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, "select.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sel = load_select()


# --------------------------------------------------------------------------------------------------------------
# git helpers

def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed ({result.returncode}): {result.stderr.strip()}")
    return result


def fetch(repo: Path, remote: str) -> None:
    git(repo, "fetch", "--prune", "--force", "--no-tags", remote,
        f"+refs/heads/*:refs/remotes/{remote}/*", "+refs/tags/backup/*:refs/tags/backup/*")


def gather_facts(repo: Path, remote: str, names, main_ref: str) -> dict:
    """Facts for each requested branch. Invalid names are never passed to git."""
    facts = {}
    for name in names:
        if sel.invalid_name_reason(name):
            facts[name] = sel.BranchFacts(name, exists=False)
            continue
        ref = f"refs/remotes/{remote}/{name}"
        result = git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
        if result.returncode != 0:
            facts[name] = sel.BranchFacts(name, exists=False)
            continue
        sha = result.stdout.strip()
        merged = git(repo, "merge-base", "--is-ancestor", sha, main_ref, check=False).returncode == 0
        refs = git(repo, "for-each-ref", "--format=%(refname)", "--contains", sha,
                   "refs/tags/backup/", f"refs/remotes/{remote}/archive/").stdout.split()
        backups = tuple(sorted(
            r.removeprefix("refs/tags/") if r.startswith("refs/tags/") else "branch " + r.split("/", 3)[3]
            for r in refs
            if r.startswith("refs/tags/backup/") or r.startswith(f"refs/remotes/{remote}/archive/backup-")
        ))
        facts[name] = sel.BranchFacts(name, exists=True, sha=sha, merged=merged, backup_refs=backups)
    return facts


def remote_sha(repo: Path, remote: str, branch: str) -> str | None:
    out = git(repo, "ls-remote", "--heads", remote, f"refs/heads/{branch}").stdout.split()
    return out[0] if out else None


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


# --------------------------------------------------------------------------------------------------------------
# File helpers

def read_text(path: str | None) -> str:
    if not path or not os.path.exists(path):
        return ""
    return Path(path).read_text(encoding="utf-8")


def read_json(path: str | None):
    if not path or not os.path.exists(path):
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def append(path: str, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


# --------------------------------------------------------------------------------------------------------------
# Commands

def cmd_hash(args) -> int:
    print(sel.request_hash(sel.parse_request(read_text(args.request))))
    return 0


def cmd_runs_to_verify(args) -> int:
    hash_ = sel.request_hash(sel.parse_request(read_text(args.request)))
    for run_id in sel.runs_to_verify(hash_, sel.parse_dry_run_log(read_text(args.dry_run_log))):
        print(run_id)
    return 0


def backup_runs_from(path: str | None):
    """``--backup-runs``: GitHub API response (object with workflow_runs, or a plain list). Missing/unreadable
    file means the lookup failed; an empty list means backup.yml never ran. Both refuse deletion."""
    data = read_json(path)
    if isinstance(data, dict) and isinstance(data.get("workflow_runs"), list):
        return data["workflow_runs"]
    if isinstance(data, list):
        return data
    return None


def cmd_run(args) -> int:
    repo = Path(args.repo).resolve()
    summary_notes: list[str] = []
    try:
        request = sel.parse_request(read_text(args.request))
    except sel.RequestError as error:
        append(args.summary, f"## Branch cleanup — request rejected\n\n{error}\n\nNothing was considered.\n")
        print(f"request rejected: {error}", file=sys.stderr)
        return 2
    hash_ = sel.request_hash(request)
    fetch(repo, args.remote)
    main_ref = f"refs/remotes/{args.remote}/main"
    git(repo, "rev-parse", "--verify", f"{main_ref}^{{commit}}")
    facts = gather_facts(repo, args.remote, request.branches, main_ref)

    approval = None
    if request.mode == "delete":
        records = sel.parse_dry_run_log(read_text(args.dry_run_log))
        verified = read_json(args.verified_runs) or {}
        approval = sel.dry_run_approval(hash_, records, verified if isinstance(verified, dict) else {})
        summary_notes.append(f"dry run: {approval.reason}")
    backup_runs = backup_runs_from(args.backup_runs)
    summary_notes.append(f"backup: {sel.backup_run_status(backup_runs)[1]}")
    decisions = sel.decide(request, facts, read_text(args.task_log), backup_runs, approval)

    now = utc_now()
    date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    failures = 0
    if request.mode == "dry-run":
        append(args.dry_run_log, json.dumps(sel.dry_run_record(request, args.run_id, date, decisions),
                                            sort_keys=True) + "\n")
        summary_notes.append("dry run recorded; nothing was deleted")
    elif not args.allow_delete:
        summary_notes.append("deletion disabled (--allow-delete not given); nothing was deleted")
    else:
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        final = []
        for decision in decisions:
            if decision.action != sel.ACTION_DELETE:
                final.append(decision)
                continue
            ok, why = delete_branch(repo, args.remote, decision.branch, decision.sha, stamp)
            if ok:
                if not os.path.exists(args.cleanup_log) or not read_text(args.cleanup_log).strip():
                    Path(args.cleanup_log).parent.mkdir(parents=True, exist_ok=True)
                    Path(args.cleanup_log).write_text(sel.CLEANUP_LOG_HEADER, encoding="utf-8", newline="\n")
                append(args.cleanup_log, sel.cleanup_log_line(date, decision.branch, decision.sha, hash_) + "\n")
                final.append(sel.Decision(decision.branch, decision.sha, "deleted", f"{decision.reason}; {why}"))
            else:
                failures += 1
                final.append(sel.Decision(decision.branch, decision.sha, "delete-failed", why))
        decisions = final
    append(args.summary, sel.summary_markdown(request, hash_, decisions, summary_notes))
    if args.decisions_json:
        Path(args.decisions_json).write_text(json.dumps(
            {"request_hash": hash_, "mode": request.mode,
             "decisions": [d.__dict__ for d in decisions]}, indent=2) + "\n", encoding="utf-8")
    for d in decisions:
        print(f"{d.action:13} {d.branch} {(d.sha or '-')[:12]} {d.reason}")
    return 1 if failures else 0


def delete_branch(repo: Path, remote: str, branch: str, sha: str, stamp: str) -> tuple[bool, str]:
    """Pin the tip with a fresh backup tag, then delete only if the remote branch is still at ``sha``."""
    tag = f"refs/tags/backup/{stamp}/{branch}"
    result = git(repo, "push", remote, f"{sha}:{tag}", check=False)
    if result.returncode != 0:
        return False, f"backup tag push failed, branch kept: {result.stderr.strip()[-200:]}"
    result = git(repo, "push", f"--force-with-lease=refs/heads/{branch}:{sha}", remote, f":refs/heads/{branch}",
                 check=False)
    if result.returncode != 0:
        return False, f"delete refused (branch moved or push failed), branch kept: {result.stderr.strip()[-200:]}"
    if remote_sha(repo, remote, branch) is not None:
        return False, "branch still present after delete"
    return True, f"deleted; pinned by tag {tag.removeprefix('refs/tags/')}"


def cmd_restore(args) -> int:
    repo = Path(args.repo).resolve()
    entries = [e for e in sel.parse_cleanup_log(read_text(args.cleanup_log)) if e["branch"] == args.branch]
    if args.sha:
        entries = [e for e in entries if e["sha"] == args.sha]
    if not entries:
        print(f"no CLEANUP_LOG entry for {args.branch}", file=sys.stderr)
        return 2
    entry = entries[-1]
    current = remote_sha(repo, args.remote, args.branch)
    if current is not None:
        print(f"refusing: {args.branch} already exists on {args.remote} at {current}", file=sys.stderr)
        return 2
    command = sel.restore_command(entry, args.remote)
    print("+", " ".join(command))
    git(repo, *command[1:])
    restored = remote_sha(repo, args.remote, args.branch)
    if restored != entry["sha"]:
        print(f"restore mismatch: expected {entry['sha']}, remote has {restored}", file=sys.stderr)
        return 1
    print(f"restored {args.branch} at {restored}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("hash")
    p.add_argument("--request", required=True)
    p.set_defaults(func=cmd_hash)

    p = sub.add_parser("runs-to-verify")
    p.add_argument("--request", required=True)
    p.add_argument("--dry-run-log", required=True)
    p.set_defaults(func=cmd_runs_to_verify)

    p = sub.add_parser("run")
    p.add_argument("--repo", default=".")
    p.add_argument("--remote", default="origin")
    p.add_argument("--request", required=True)
    p.add_argument("--task-log", required=True)
    p.add_argument("--backup-runs", required=True)
    p.add_argument("--dry-run-log", required=True)
    p.add_argument("--verified-runs")
    p.add_argument("--cleanup-log", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--decisions-json")
    p.add_argument("--allow-delete", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("restore")
    p.add_argument("--repo", default=".")
    p.add_argument("--remote", default="origin")
    p.add_argument("--cleanup-log", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--sha")
    p.set_defaults(func=cmd_restore)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
