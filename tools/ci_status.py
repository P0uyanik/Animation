#!/usr/bin/env python3
"""CI status and "already verified" lookups for the GitHub workflows (T-086).

    python tools/ci_status.py status [--branch main] [--exclude NAME] [--summary FILE] [--json FILE]
        Lists the latest result of EVERY workflow in the repository on <branch> (default main): the newest run and the
        newest decisive result (newest completed run that was not cancelled or skipped), so a red workflow cannot
        hide behind a cancelled or still-running one. Workflows that never ran on <branch> are listed too, with the
        branch they last ran on. Exit 1 if any workflow's newest decisive result on <branch> is a failure.

    python tools/ci_status.py verified --sha SHA --branches 'integration/*,staging' [--require-full-for CHARS_JSON]
        [--wait-minutes N] [--workflow checks.yml] [--github-output FILE]
        Does a successful quality-gate run for exactly this commit exist on one of the given branches? Used by the
        plan job on staging/main pushes (docs/process/GATE.md §5.1). Prints and writes:
          mode=verified  run_id=<id> run_branch=<branch>  a successful run with every required job green;
          mode=failed    run_id=<id> ...                  the newest finished run for this commit failed;
          mode=run                                        no finished run for this commit: run the full gate here.
        With --wait-minutes, queued/in-progress runs for the commit are waited for (polled once a minute).
        With --require-full-for, the run must contain a successful "regression <character>" job for each character.

Authentication: GITHUB_TOKEN or GH_TOKEN (Actions: the job token with `actions: read`); without a token the
`gh` CLI is used if present. Repository: GITHUB_REPOSITORY or --repo owner/name.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

REQUIRED_JOBS = ("Plan (tier)", "linux gate", "linux renderer", "Gate verdict")
FAILED = {"failure", "timed_out", "startup_failure", "action_required"}
NOT_DECISIVE = {"cancelled", "skipped", "neutral", "stale", None, ""}


class Api:
    def __init__(self, repo: str):
        self.repo = repo
        self.base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
        self.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

    def get(self, endpoint: str, **params):
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        rel = f"repos/{self.repo}/{endpoint}" + (f"?{query}" if query else "")
        if not self.token and shutil.which("gh"):
            out = subprocess.run(["gh", "api", "-X", "GET", rel], capture_output=True, text=True, check=True)
            return json.loads(out.stdout)
        request = urllib.request.Request(f"{self.base}/{rel}", headers={
            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {self.token}"} if self.token else {})})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))


def repo_name(arg: str) -> str:
    repo = arg or os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        return repo
    url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    tail = url.rstrip("/").removesuffix(".git").split("github.com")[-1].lstrip(":/")
    if "/" in tail:
        return "/".join(tail.split("/")[-2:])
    raise SystemExit("repository unknown: pass --repo owner/name or set GITHUB_REPOSITORY")


def age(stamp: str) -> str:
    if not stamp:
        return "?"
    then = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    minutes = int((dt.datetime.now(dt.timezone.utc) - then).total_seconds() // 60)
    return f"{minutes} min ago" if minutes < 120 else f"{minutes // 60} h ago" if minutes < 2880 else f"{minutes // 1440} d ago"


def describe(run: dict | None) -> str:
    if not run:
        return "-"
    state = run.get("conclusion") or run.get("status")
    return f"{state} ({run.get('event')}, {run.get('head_sha', '')[:7]}, {age(run.get('created_at', ''))}, run {run.get('id')})"


# ---------------------------------------------------------------- status

def workflow_status(api: Api, branch: str, exclude: set[str]) -> list[dict]:
    rows = []
    workflows = api.get("actions/workflows", per_page=100).get("workflows", [])
    for workflow in sorted(workflows, key=lambda w: w.get("name", "")):
        name = workflow.get("name", "")
        runs = api.get(f"actions/workflows/{workflow['id']}/runs", branch=branch, per_page=30).get("workflow_runs", [])
        latest = runs[0] if runs else None
        decisive = next((r for r in runs if r.get("status") == "completed" and r.get("conclusion") not in NOT_DECISIVE),
                        None)
        row = {"workflow": name, "path": workflow.get("path"), "state": workflow.get("state"),
               "latest": describe(latest), "latest_url": (latest or {}).get("html_url", ""),
               "decisive": describe(decisive), "decisive_conclusion": (decisive or {}).get("conclusion", ""),
               "excluded": name in exclude}
        if decisive and decisive.get("conclusion") in FAILED and decisive.get("name") == workflow.get("path"):
            # A run named after the file and without jobs is GitHub rejecting the workflow file at that commit. Once
            # the file changed on the branch after it, the error is stale (the workflow may never run on the branch).
            changed = api.get("commits", sha=branch, path=workflow.get("path"), per_page=1)
            last = changed[0]["commit"]["committer"]["date"] if changed else ""
            if last and last > decisive.get("created_at", ""):
                row["decisive_conclusion"] = "stale"
                row["note"] = (f"workflow-file error at {decisive.get('head_sha', '')[:7]} is stale: "
                               f"{workflow.get('path')} changed on {branch} since ({last})")
        if not runs:
            other = api.get(f"actions/workflows/{workflow['id']}/runs", per_page=1).get("workflow_runs", [])
            row["note"] = (f"no run on {branch}; last run on {other[0].get('head_branch')}: {describe(other[0])}"
                           if other else f"no run on {branch} (never ran)")
        elif decisive is None:
            row["note"] = f"no decisive result in the last {len(runs)} runs on {branch} (all cancelled/skipped/running)"
        rows.append(row)
    return rows


def verdict_of(row: dict) -> str:
    if row.get("excluded"):
        return "INFO"
    if row["decisive_conclusion"] in FAILED:
        return "FAIL"
    if row["decisive_conclusion"] == "success":
        return "PASS"
    return "WARN"


def cmd_status(args) -> int:
    api = Api(repo_name(args.repo))
    rows = workflow_status(api, args.branch, set(args.exclude or []))
    lines = [f"Latest result of every workflow on {args.branch} ({api.repo}, "
             f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC)"]
    for row in rows:
        row["verdict"] = verdict_of(row)
        text = f"{row['verdict']:4} {row['workflow']}: decisive {row['decisive']}; newest {row['latest']}"
        if row.get("note"):
            text += f"; {row['note']}"
        lines.append(text)
    print("\n".join(lines))
    if args.summary:
        table = ["| | Workflow | Newest decisive result | Newest run | Note |", "| --- | --- | --- | --- | --- |"]
        for row in rows:
            link = f"[{row['latest']}]({row['latest_url']})" if row["latest_url"] else row["latest"]
            table.append(f"| {row['verdict']} | {row['workflow']} | {row['decisive']} | {link} | {row.get('note', '')} |")
        with open(args.summary, "a", encoding="utf-8") as out:
            out.write(f"### {lines[0]}\n\n" + "\n".join(table) + "\n")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 1 if any(row["verdict"] == "FAIL" for row in rows) else 0


# ---------------------------------------------------------------- verified

def matches(branch: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(branch, pattern) for pattern in patterns)


def run_problems(api: Api, run: dict, characters: list[str]) -> list[str]:
    """Why a successful run does not count as verification of the full gate (empty list: it counts)."""
    jobs = api.get(f"actions/runs/{run['id']}/jobs", per_page=100, filter="latest").get("jobs", [])
    result = {job.get("name"): job.get("conclusion") for job in jobs}
    problems = [f"job {name} {result.get(name, 'missing')}" for name in REQUIRED_JOBS if result.get(name) != "success"]
    problems += [f"job regression {c} {result.get(f'regression {c}', 'missing')}" for c in characters
                 if result.get(f"regression {c}") != "success"]
    return problems


def find_verification(api: Api, workflow: str, sha: str, branches: list[str], characters: list[str],
                      self_id: str) -> tuple[str, dict | None, str]:
    runs = api.get(f"actions/workflows/{workflow}/runs", head_sha=sha, per_page=50).get("workflow_runs", [])
    runs = [r for r in runs if str(r.get("id")) != self_id and r.get("event") in {"push", "workflow_dispatch"}
            and matches(r.get("head_branch") or "", branches)]
    notes = []
    for run in runs:  # newest first
        if run.get("status") == "completed" and run.get("conclusion") == "success":
            problems = run_problems(api, run, characters)
            if not problems:
                return "verified", run, f"run {run['id']} on {run['head_branch']} passed"
            notes.append(f"run {run['id']} on {run['head_branch']} passed but does not cover the gate: "
                         + ", ".join(problems))
    pending = [r for r in runs if r.get("status") != "completed"]
    if pending:
        return "pending", pending[0], f"run {pending[0]['id']} on {pending[0]['head_branch']} is {pending[0]['status']}"
    failed = [r for r in runs if r.get("status") == "completed" and r.get("conclusion") in FAILED]
    if failed:
        run = failed[0]
        return "failed", run, f"run {run['id']} on {run['head_branch']} for this commit {run['conclusion']}"
    return "run", None, "; ".join(notes) or f"no gate run for {sha[:7]} on {', '.join(branches)}"


def cmd_verified(args) -> int:
    api = Api(repo_name(args.repo))
    branches = [b.strip() for b in args.branches.split(",") if b.strip()]
    characters = json.loads(args.require_full_for) if args.require_full_for else []
    deadline = time.monotonic() + args.wait_minutes * 60
    self_id = os.environ.get("GITHUB_RUN_ID", "")
    while True:
        mode, run, detail = find_verification(api, args.workflow, args.sha, branches, characters, self_id)
        if mode != "pending":
            break
        if time.monotonic() >= deadline:
            mode, detail = "run", f"gave up waiting after {args.wait_minutes} min: {detail}"
            run = None
            break
        print(f"waiting: {detail}", flush=True)
        time.sleep(args.poll_seconds)
    out = {"mode": mode, "run_id": str((run or {}).get("id", "")), "run_branch": (run or {}).get("head_branch", ""),
           "run_url": (run or {}).get("html_url", ""), "detail": detail}
    print(json.dumps(out))
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as fh:
            for key, value in out.items():
                fh.write(f"{key}={value}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default="", help="owner/name (default: GITHUB_REPOSITORY or the origin remote)")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="latest result of every workflow on a branch")
    status.add_argument("--branch", default="main")
    status.add_argument("--exclude", action="append", help="workflow name listed as INFO only (e.g. this status job)")
    status.add_argument("--summary", default="", help="append a Markdown table (e.g. $GITHUB_STEP_SUMMARY)")
    status.add_argument("--json", default="")
    status.set_defaults(func=cmd_status)
    verified = sub.add_parser("verified", help="is there a successful gate run for this commit?")
    verified.add_argument("--sha", required=True)
    verified.add_argument("--branches", required=True, help="comma-separated branch globs, e.g. 'integration/*,staging'")
    verified.add_argument("--workflow", default="checks.yml")
    verified.add_argument("--require-full-for", default="", help="JSON list of characters whose regression job must pass")
    verified.add_argument("--wait-minutes", type=float, default=0)
    verified.add_argument("--poll-seconds", type=float, default=60)
    verified.add_argument("--github-output", default="")
    verified.set_defaults(func=cmd_verified)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
