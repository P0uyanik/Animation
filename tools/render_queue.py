#!/usr/bin/env python3
"""One-render-at-a-time queue (T-165): a lock file that heavy render jobs take before they start.

    python3 tools/render_queue.py run [--lock PATH] [--timeout S] -- <command...>   wait for the lock, run, release
    python3 tools/render_queue.py status [--lock PATH]                             who holds the lock, if anyone

In Python:  with render_queue.render_lock(label="shot_sheet"): ...

Two renders at once starve each other (T-162). The lock is a file created with O_EXCL that holds the owner's pid,
host, label and start time. A lock whose pid is gone (same host) is stale and is taken over. Default path:
$PLUSH_RENDER_LOCK, else <tempdir>/plush-render.lock (one per machine). Opt-in: nothing in the gate uses it."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def default_lock() -> Path:
    env = os.environ.get("PLUSH_RENDER_LOCK", "")
    return Path(env) if env else Path(tempfile.gettempdir()) / "plush-render.lock"


def read_lock(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {}  # being written or unreadable: treat as held


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in out.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def is_stale(info: dict | None) -> bool:
    if not info:
        return False
    return info.get("host") == socket.gethostname() and not pid_alive(int(info.get("pid", 0)))


def try_acquire(path: Path, label: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if is_stale(read_lock(path)):
            with contextlib.suppress(FileNotFoundError):
                path.unlink()
            return try_acquire(path, label)
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "host": socket.gethostname(), "label": label,
                   "since": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, f)
    return True


def release(path: Path) -> None:
    info = read_lock(path)
    if info and info.get("pid") == os.getpid() and info.get("host") == socket.gethostname():
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


@contextlib.contextmanager
def render_lock(label: str = "render", lock: Path | None = None, timeout: float | None = None,
                poll: float = 2.0, quiet: bool = False):
    """Block until this process holds the render lock; release it on exit. TimeoutError after `timeout` s."""
    path = Path(lock) if lock else default_lock()
    started, told = time.monotonic(), False
    while not try_acquire(path, label):
        if not quiet and not told:
            info = read_lock(path) or {}
            print(f"render_queue: waiting for {info.get('label', '?')} (pid {info.get('pid', '?')}) - {path}",
                  file=sys.stderr, flush=True)
            told = True
        if timeout is not None and time.monotonic() - started >= timeout:
            raise TimeoutError(f"render lock {path} still held after {timeout:.0f} s")
        time.sleep(poll)
    try:
        yield path
    finally:
        release(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run a command while holding the lock")
    run.add_argument("--lock", default="")
    run.add_argument("--timeout", type=float, default=None)
    run.add_argument("--label", default="")
    run.add_argument("--poll", type=float, default=2.0)
    run.add_argument("command", nargs=argparse.REMAINDER)
    status = sub.add_parser("status", help="print the current holder")
    status.add_argument("--lock", default="")
    args = parser.parse_args(argv)
    lock = Path(args.lock) if args.lock else default_lock()
    if args.cmd == "status":
        info = read_lock(lock)
        print("free" if info is None else ("stale " if is_stale(info) else "held ") + json.dumps(info))
        return 0
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("run needs a command after --")
    try:
        with render_lock(args.label or os.path.basename(command[0]), lock, args.timeout, args.poll):
            return subprocess.run(command).returncode
    except TimeoutError as exc:
        print(f"render_queue: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
