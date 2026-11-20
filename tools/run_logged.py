#!/usr/bin/env python3
"""Run a command, keep its full log, print only the tail and the log path (T-165).

    python3 tools/run_logged.py [--log PATH] [--tail N] [--name NAME] -- <command...>

The full stdout+stderr goes to --log (default: <tempdir>/plush-logs/<name>-<UTC>.log), so a failure can be read
later without re-running the command. Prints the last N lines (default 15), then one summary line:
`run_logged: exit <code> · <seconds> s · log <path>`. Exits with the command's exit code. Opt-in tool."""
from __future__ import annotations

import argparse
import collections
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def default_log(name: str) -> Path:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return Path(tempfile.gettempdir()) / "plush-logs" / f"{name}-{stamp}-{os.getpid()}.log"


def run(command: list[str], log: Path, tail: int = 15, out=None) -> int:
    out = out or sys.stdout
    log.parent.mkdir(parents=True, exist_ok=True)
    last: collections.deque[str] = collections.deque(maxlen=max(tail, 0))
    started = time.monotonic()
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        f.write("$ " + subprocess.list2cmdline(command) + "\n")
        f.flush()
        try:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                    encoding="utf-8", errors="replace")
        except OSError as exc:
            f.write(f"cannot start: {exc}\n")
            print(f"run_logged: cannot start {command[0]}: {exc} · log {log}", file=out)
            return 127
        assert proc.stdout is not None
        for line in proc.stdout:
            f.write(line)
            last.append(line.rstrip("\n"))
        code = proc.wait()
        seconds = time.monotonic() - started
        f.write(f"[exit {code} after {seconds:.1f} s]\n")
    for line in last:
        print(line, file=out)
    print(f"run_logged: exit {code} · {seconds:.1f} s · log {log}", file=out, flush=True)
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", default="")
    parser.add_argument("--tail", type=int, default=15)
    parser.add_argument("--name", default="")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("needs a command after --")
    name = args.name or Path(command[0]).stem or "run"
    return run(command, Path(args.log) if args.log else default_log(name), args.tail)


if __name__ == "__main__":
    sys.exit(main())
