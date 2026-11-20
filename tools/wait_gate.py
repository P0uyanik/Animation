#!/usr/bin/env python3
"""Wait on ONE GitHub Actions run and print one line: GREEN, or RED with the failing job(s) (T-165).

    python3 tools/wait_gate.py <run-id> [--repo OWNER/NAME] [--interval S] [--timeout S] [--gh GH]

Polls `gh run view <id> --json status,conclusion,jobs,url` until the run completes (default every 60 s), then prints
`GREEN run <id> <url>` (exit 0) or `RED run <id> <conclusion>: <failed job>[, ...] <url>` (exit 1). Errors and the
timeout exit 2. Run it once in the background instead of send_later check-ins; it never posts anything. Opt-in."""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time

OK = {"success", "skipped", "neutral"}


def view(gh: list[str], run_id: str, repo: str) -> dict:
    cmd = gh + ["run", "view", run_id, "--json", "status,conclusion,jobs,url"]
    if repo:
        cmd += ["--repo", repo]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["gh failed"])
    return json.loads(proc.stdout)


def verdict(run_id: str, data: dict) -> tuple[int, str]:
    url = data.get("url", "")
    conclusion = data.get("conclusion") or ""
    failed = [j.get("name", "?") for j in data.get("jobs", []) if (j.get("conclusion") or "") not in OK]
    if conclusion == "success" and not failed:
        return 0, f"GREEN run {run_id} {url}".strip()
    jobs = ", ".join(failed[:5]) + (f" (+{len(failed) - 5})" if len(failed) > 5 else "") if failed else "no job named"
    return 1, f"RED run {run_id} {conclusion or 'unknown'}: {jobs} {url}".strip()


def wait(gh: list[str], run_id: str, repo: str = "", interval: float = 60, timeout: float | None = None) -> tuple[int, str]:
    started = time.monotonic()
    while True:
        try:
            data = view(gh, run_id, repo)
        except (RuntimeError, ValueError, OSError) as exc:
            return 2, f"ERROR run {run_id}: {exc}"
        if data.get("status") == "completed":
            return verdict(run_id, data)
        if timeout is not None and time.monotonic() - started >= timeout:
            return 2, f"TIMEOUT run {run_id} still {data.get('status', '?')} after {timeout:.0f} s"
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_id")
    parser.add_argument("--repo", default="")
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--gh", default="gh", help="gh executable (may include arguments)")
    args = parser.parse_args(argv)
    code, line = wait(shlex.split(args.gh, posix=(sys.platform != "win32")), args.run_id, args.repo,
                      args.interval, args.timeout)
    print(line, flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
