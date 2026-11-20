#!/usr/bin/env python3
"""Plain-Python tests for the T-165 task kit: ready.py, run_logged.py, wait_gate.py, render_queue.py,
review/shot_sheet.py. No network, no Blender, no gh; portable (Linux and Windows)."""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "review"))

import ready  # noqa: E402
import render_queue  # noqa: E402
import run_logged  # noqa: E402
import wait_gate  # noqa: E402

FAILS: list[str] = []


def check(cond, what):
    if not cond:
        FAILS.append(what)
        print(f"FAIL {what}")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def test_ready_line():
    now = dt.datetime(2026, 11, 20, 9, 5, tzinfo=dt.timezone.utc)
    line = ready.ready_line("T-165", "t-165-x", "a" * 40, "e8537d8abc", "docs/x.md",
                            "build 0 · render 0 · tests 2 · ci 0 · wait 0", "$1.20 / ctx 90k", now=now)
    check(line == "2026-11-20T09:05Z | T-165 | READY | t-165-x@aaaaaaa | input e8537d8 | ev docs/x.md | "
                  "ledger: build 0 · render 0 · tests 2 · ci 0 · wait 0 | $1.20 / ctx 90k", f"ready line: {line}")
    try:
        ready.ready_line("T-165", "b", "a" * 40, "b" * 40, "x" * 300, "l", "c", now=now)
        check(False, "ready line over 300 chars must fail")
    except ready.Fail:
        pass


def test_registration():
    reg = 'str(ROOT / "tools/tests/test_a.py")\nadd_executable(plush_tests test_b.cpp)'
    added = ["tools/tests/test_a.py", "tests/test_b.cpp", "tests/test_c.cpp", "pipeline/x/test_new.py",
             "pipeline/x/foo_test.py", "pipeline/x/helper.py", "docs/test_notes.md"]
    check(ready.unregistered_tests(added, reg) == ["tests/test_c.cpp", "pipeline/x/test_new.py",
                                                    "pipeline/x/foo_test.py"], "unregistered tests")
    text = (ROOT / "tools/check_all.py").read_text(encoding="utf-8")
    check("tools/tests/test_task_kit.py" in text, "test_task_kit.py registered in tools/check_all.py")


def test_ready_git(tmp: Path):
    remote, work = tmp / "remote.git", tmp / "work"
    git(tmp, "init", "-q", "--bare", str(remote))
    git(tmp, "init", "-q", "-b", "t-999-x", str(work))
    git(work, "config", "user.email", "t@example.invalid")
    git(work, "config", "user.name", "t")
    git(work, "remote", "add", "origin", str(remote))
    (work / "a.txt").write_text("1\n")
    git(work, "add", "a.txt")
    git(work, "commit", "-q", "-m", "one")
    try:
        ready.check_pushed("t-999-x", work)
        check(False, "unpushed branch must fail")
    except ready.Fail as exc:
        check("push" in str(exc), f"unpushed reason: {exc}")
    git(work, "push", "-q", "origin", "t-999-x")
    check(ready.check_pushed("t-999-x", work) == git(work, "rev-parse", "HEAD"), "pushed at HEAD passes")
    (work / "a.txt").write_text("2\n")
    try:
        ready.check_clean(work)
        check(False, "dirty tree must fail")
    except ready.Fail:
        pass
    git(work, "commit", "-q", "-am", "two")
    check(ready.check_clean(work) == "clean", "clean after commit")
    try:
        ready.check_pushed("t-999-x", work)
        check(False, "HEAD ahead of remote must fail")
    except ready.Fail as exc:
        check("HEAD is" in str(exc), f"ahead reason: {exc}")
    # new-test registration against a base branch
    git(work, "branch", "base", "HEAD")
    (work / "tools").mkdir()
    (work / "tools/check_all.py").write_text("# registry\n")
    (work / "tools/test_new.py").write_text("")
    git(work, "add", ".")
    git(work, "commit", "-q", "-m", "test")
    try:
        ready.check_tests_registered(work, "base")
        check(False, "unregistered new test must fail")
    except ready.Fail as exc:
        check("tools/test_new.py" in str(exc), f"registration reason: {exc}")
    (work / "tools/check_all.py").write_text('# registry\n"tools/test_new.py"\n')
    git(work, "commit", "-q", "-am", "register")
    check("1 new test" in ready.check_tests_registered(work, "base"), "registered test passes")


def test_claims_and_links():
    try:  # repository-state independent: an unknown task always fails with the integrate.py reason
        ready.check_claims("T-0000")
        check(False, "unknown task must fail the claims check")
    except ready.Fail as exc:
        check("no claim" in str(exc), f"claims reason: {exc}")
    check(ready.check_links() == "links ok", "doc links pass")


def test_run_logged(tmp: Path):
    log = tmp / "logs" / "r.log"
    out = io.StringIO()
    code = run_logged.run([sys.executable, "-c", "import sys\nfor i in range(40): print('line', i)\nsys.exit(3)"],
                          log, tail=5, out=out)
    text = out.getvalue().splitlines()
    check(code == 3, "run_logged returns the command's code")
    check(text[:5] == [f"line {i}" for i in range(35, 40)], f"tail: {text[:5]}")
    check(text[-1].startswith("run_logged: exit 3") and str(log) in text[-1], f"summary: {text[-1]}")
    full = log.read_text()
    check("line 0\n" in full and "line 39\n" in full and "[exit 3" in full, "full log kept")
    check(run_logged.run([str(tmp / "no-such-exe")], tmp / "x.log", out=io.StringIO()) == 127, "missing exe")


def test_wait_gate(tmp: Path):
    state = tmp / "gh_state.json"
    fake = tmp / "fake_gh.py"
    fake.write_text(
        "import json, sys\n"
        f"p = {str(state)!r}\n"
        "s = json.load(open(p))\n"
        "s['calls'] += 1\n"
        "json.dump(s, open(p, 'w'))\n"
        "if s.get('fail'):\n    sys.stderr.write('HTTP 404\\n'); sys.exit(1)\n"
        "done = s['calls'] >= 2\n"
        "print(json.dumps({'status': 'completed' if done else 'in_progress', 'url': 'u',\n"
        "  'conclusion': s['conclusion'] if done else None, 'jobs': s['jobs']}))\n")
    gh = [sys.executable, str(fake)]
    state.write_text(json.dumps({"calls": 0, "conclusion": "success", "jobs": [{"name": "a", "conclusion": "success"}]}))
    check(wait_gate.wait(gh, "7", interval=0) == (0, "GREEN run 7 u"), "green after polling")
    state.write_text(json.dumps({"calls": 0, "conclusion": "failure", "jobs": [
        {"name": "lint", "conclusion": "success"}, {"name": "blender 2/5", "conclusion": "failure"}]}))
    check(wait_gate.wait(gh, "8", interval=0) == (1, "RED run 8 failure: blender 2/5 u"), "red names the job")
    state.write_text(json.dumps({"calls": 0, "fail": True}))
    code, line = wait_gate.wait(gh, "9", interval=0)
    check(code == 2 and "HTTP 404" in line, f"gh error: {line}")
    state.write_text(json.dumps({"calls": -100, "conclusion": "success", "jobs": []}))
    code, line = wait_gate.wait(gh, "10", interval=0.01, timeout=0)
    check(code == 2 and line.startswith("TIMEOUT"), f"timeout: {line}")


def test_render_queue(tmp: Path):
    lock = tmp / "render.lock"
    with render_queue.render_lock("a", lock, quiet=True):
        check(lock.is_file(), "lock file exists while held")
        child = subprocess.run([sys.executable, str(ROOT / "tools/render_queue.py"), "run", "--lock", str(lock),
                                "--timeout", "0.5", "--poll", "0.1", "--", sys.executable, "-c", "print(1)"],
                               capture_output=True, text=True)
        check(child.returncode == 3, f"second holder times out (exit {child.returncode})")
    check(not lock.exists(), "lock released")
    # a lock left by a dead process on this host is stale and taken over
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    lock.write_text(json.dumps({"pid": dead.pid, "host": render_queue.socket.gethostname(), "label": "old"}))
    with render_queue.render_lock("b", lock, timeout=1, quiet=True):
        check(json.loads(lock.read_text())["label"] == "b", "stale lock taken over")
    child = subprocess.run([sys.executable, str(ROOT / "tools/render_queue.py"), "run", "--lock", str(lock), "--",
                            sys.executable, "-c", "import sys; sys.exit(4)"], capture_output=True, text=True)
    check(child.returncode == 4 and not lock.exists(), "run passes the exit code and releases")


def test_shot_sheet(tmp: Path):
    try:
        from PIL import Image
    except ImportError:
        print("SKIP shot_sheet (no PIL)")
        return
    import shot_sheet
    for col, color in (("before", (200, 40, 40)), ("after", (40, 200, 40))):
        (tmp / col).mkdir()
        for f in (1, 24):
            Image.new("RGB", (1920, 1080), color).save(tmp / col / f"frame_{f:04d}.png")
    spec = {"title": "T-165 test", "frames": [1, 24],
            "columns": [{"label": "before", "dir": "before"}, {"label": "after", "dir": "after"}],
            "crops": [{"label": "face", "box": [0.4, 0.1, 0.6, 0.4]}, {"label": "px", "box": [0, 0, 100, 50]}],
            "out": "out/sheet.jpg",
            "render": [{"cmd": [sys.executable, "-c", "print('render')"]}]}
    (tmp / "s.json").write_text(json.dumps(spec))
    code = shot_sheet.main([str(tmp / "s.json"), "--lock", str(tmp / "q.lock")])
    check(code == 0, "shot_sheet builds")
    out = tmp / "out" / "sheet.jpg"
    with Image.open(out) as im:
        check(max(im.size) <= 2048, f"sheet within 2048 px: {im.size}")
        check(im.size[0] > im.size[1], "6 tiles per row are wider than 2 rows")
    rec = json.loads((tmp / "out" / "sheet.jpg.json").read_text())
    check(len(rec["inputs"]) == 4 and not rec["missing"], "record lists 4 inputs")
    check(shot_sheet.crop_box([0.5, 0.5, 1, 1], 100, 50) == (50, 25, 100, 50), "fraction crop")
    check(shot_sheet.crop_box([10, 5, 500, 500], 100, 50) == (10, 5, 100, 50), "pixel crop clamped")
    spec["frames"] = [1, 48]
    spec.pop("render")
    (tmp / "s2.json").write_text(json.dumps(spec))
    check(shot_sheet.main([str(tmp / "s2.json")]) == 1, "missing frame exits 1")
    (tmp / "bad.json").write_text(json.dumps({"columns": [], "frames": []}))
    check(shot_sheet.main([str(tmp / "bad.json")]) == 2, "invalid spec exits 2")


def main() -> int:
    started = time.monotonic()
    test_ready_line()
    test_registration()
    test_claims_and_links()
    for fn in (test_ready_git, test_run_logged, test_wait_gate, test_render_queue, test_shot_sheet):
        with tempfile.TemporaryDirectory() as d:
            fn(Path(d))
    print(f"test_task_kit: {'FAIL ' + str(len(FAILS)) if FAILS else 'PASS'} ({time.monotonic() - started:.1f} s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
