#!/usr/bin/env python3
"""T-128 opt-in: run the gate's test sets in parallel in a session. Not used by the gate.

Python: takes EXACTLY the command list of tools/check_all.py:check_python_tests (collected by
patching its runner, never re-listed here) and runs each script as its own process.
C++: shards the doctest binary into N processes by test-case index (--first/--last over the
name-sorted list); the union of shards is the full case list (checked before running).

  python tools/dev/parallel_tests.py py  [-j N] [--serial]
  python tools/dev/parallel_tests.py cpp --bin build/tests/plush_tests [-j N] [--serial]
Prints one line per test/shard: <exit code> <name>, then a sorted summary for diffing.
Revert: delete tools/dev/parallel_tests.py (nothing imports it).
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def gate_python_commands() -> list[list[str]]:
    sys.path.insert(0, str(ROOT / "tools"))  # check_all.py imports its siblings
    spec = importlib.util.spec_from_file_location("check_all", ROOT / "tools/check_all.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_all"] = mod
    spec.loader.exec_module(mod)
    seen: list[list[str]] = []
    mod.run_logged = lambda command, *a, **k: (seen.append(list(command)), (0, 0.0))[1]
    with tempfile.TemporaryDirectory() as tmp:
        mod.check_python_tests(Path(tmp))
    return seen


def doctest_cases(binary: str) -> list[str]:
    out = subprocess.run([binary, "--list-test-cases", "--order-by=name", "--no-version"],
                         capture_output=True, text=True, check=True).stdout
    return [line.strip() for line in out.splitlines()
            if line.strip() and not line.startswith(("[doctest]", "=")) ]


def case_verdicts(log_dir: Path, cases: list[str]) -> dict[str, str]:
    """Per listed case: PASS/FAIL/SKIP. JUnit reports subcases as "case/subcase"; they roll up to the case."""
    import xml.etree.ElementTree as ET
    listed, rank = set(cases), {"PASS": 0, "SKIP": 1, "FAIL": 2}
    verdicts: dict[str, str] = {}
    for xml in log_dir.glob("*.xml"):
        for tc in ET.parse(xml).iter("testcase"):
            name = tc.get("name")
            if name not in listed:
                name = next((c for c in listed if name.startswith(c + "/")), name)
            bad = tc.find("failure") is not None or tc.find("error") is not None
            v = "FAIL" if bad else ("SKIP" if tc.find("skipped") is not None else "PASS")
            if rank[v] >= rank.get(verdicts.get(name, "PASS"), 0):
                verdicts[name] = v
    return verdicts


def run(name: str, command: list[str], log_dir: Path) -> tuple[str, int, float]:
    started = time.monotonic()
    stem = log_dir / name.replace("/", "_").replace(":", "_")
    # Own TMPDIR per job: several tests use fixed names under temp_directory_path()/gettempdir().
    tmp = Path(str(stem) + ".tmp"); tmp.mkdir(exist_ok=True)
    env = dict(os.environ, TMPDIR=str(tmp), TEMP=str(tmp), TMP=str(tmp))
    if command[0] == os.environ.get("_T128_DOCTEST"):
        command = command + ["--reporters=junit", f"--out={stem}.xml"]
    with open(f"{stem}.log", "w") as log:
        code = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env).returncode
    return name, code, time.monotonic() - started


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("suite", choices=["py", "cpp"])
    ap.add_argument("-j", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--serial", action="store_true", help="same jobs, one at a time")
    ap.add_argument("--bin", help="doctest binary (cpp)")
    ap.add_argument("--logs", default=None)
    args = ap.parse_args()
    jobs = 1 if args.serial else args.j
    log_dir = Path(args.logs or tempfile.mkdtemp(prefix="t128-"))
    log_dir.mkdir(parents=True, exist_ok=True)

    if args.suite == "py":
        work = [(str(Path(c[1]).relative_to(ROOT)), c) for c in gate_python_commands()]
    else:
        cases = doctest_cases(args.bin)
        shards = max(1, min(jobs, len(cases)))
        bounds = [(len(cases) * i // shards, len(cases) * (i + 1) // shards) for i in range(shards)]
        assert sum(b - a for a, b in bounds) == len(cases) and bounds[-1][1] == len(cases)
        work = [(f"shard{i}:{a + 1}-{b}", [args.bin, "--order-by=name", f"--first={a + 1}", f"--last={b}"])
                for i, (a, b) in enumerate(bounds)]
        os.environ["_T128_DOCTEST"] = args.bin
        print(f"# {len(cases)} doctest cases in {shards} shard(s)")

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(lambda w: run(w[0], w[1], log_dir), work))
    for name, code, secs in sorted(results):
        print(f"{code} {name} {secs:.1f}s")
    if args.suite == "cpp":  # per-case verdicts from the junit files: the set must equal the listed cases
        verdicts = case_verdicts(log_dir, cases)
        (log_dir / "cases.txt").write_text("".join(f"{v} {k}\n" for k, v in sorted(verdicts.items())))
        missing = sorted(set(cases) - set(verdicts))
        print(f"# cases run={len(verdicts)} listed={len(cases)} missing={len(missing)} "
              f"fail={sum(v == 'FAIL' for v in verdicts.values())} -> {log_dir / 'cases.txt'}")
        if missing:
            results.append(("missing-cases", 1, 0.0))
    failed = [n for n, c, _ in results if c]
    print(f"# jobs={jobs} items={len(results)} failed={len(failed)} wall={time.monotonic() - started:.1f}s logs={log_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
