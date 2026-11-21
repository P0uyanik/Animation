#!/usr/bin/env python3
"""READY preflight (T-165): run the mechanical checks a Supervisor would send back, then print ONE READY line.

    python3 tools/ready.py --task T-NNN --input <SHA> --evidence <path> \
        --ledger "build N · render N · tests N · ci N · wait N" --cost "$X / ctx Yk" [--note "..."]

Checks, in order (the first failure stops it with a short reason and exit 1):
  clean     no uncommitted tracked changes (READY describes a commit, not a working tree)
  pushed    origin/<branch> on the remote is exactly HEAD (`git ls-remote`)
  claims    `tools/integrate.py claims --check T-NNN`
  write-set the gate's own rule (tools/check_all.py check_write_set)
  tests     every test file the branch adds is registered in a TESTS manifest (T-182) or tests/CMakeLists.txt
  links     `tools/check_doc_links.py`
On success it prints the relay line (<= 300 chars) and exits 0:
  `<UTC> | T-NNN | READY | <branch>@<sha> | input <sha> | ev <path> | ledger: ... | <cost>[ | note]`
It never sends anything: the caller sends that line once, to its Supervisor. `--cost` comes from the caller's own
get_session usage. Opt-in tool; the gate does not run it."""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_LINE = 300
REGISTRIES = ("tools/check_all.py", "tests/CMakeLists.txt")


class Fail(Exception):
    pass


def git(*args: str, root: Path = ROOT) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        raise Fail(f"git {' '.join(args[:2])}: {(proc.stderr or proc.stdout).strip()[:120]}")
    return proc.stdout.strip()


def check_clean(root: Path = ROOT) -> str:
    dirty = [line[3:] for line in git("status", "--porcelain", "--untracked-files=no", root=root).splitlines() if line]
    if dirty:
        raise Fail(f"uncommitted changes: {', '.join(dirty[:3])}")
    return "clean"


def check_pushed(branch: str, root: Path = ROOT, remote: str = "origin") -> str:
    head = git("rev-parse", "HEAD", root=root)
    out = git("ls-remote", remote, f"refs/heads/{branch}", root=root)
    remote_sha = out.split()[0] if out else ""
    if not remote_sha:
        raise Fail(f"{branch} is not on {remote}: push it first")
    if remote_sha != head:
        raise Fail(f"{remote}/{branch} is {remote_sha[:7]}, HEAD is {head[:7]}: push first")
    return head


def check_claims(task: str, root: Path = ROOT) -> str:
    proc = subprocess.run([sys.executable, str(root / "tools/integrate.py"), "claims", "--check", task],
                          cwd=root, capture_output=True, text=True)
    last = (proc.stdout.strip().splitlines() or [proc.stderr.strip()])[-1]
    if proc.returncode != 0:
        raise Fail(last[:160])
    return last


def check_write_set(task: str) -> str:
    sys.path.insert(0, str(ROOT / "tools"))
    import check_all  # the gate's own rule and base
    result = check_all.check_write_set(task, check_all.choose_base(""))
    if not result.ok:
        raise Fail(f"write-set: {result.detail}"[:200])
    return result.detail


def is_test_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if path.endswith(".py"):
        return name.startswith("test_") or name.endswith("_test.py")
    return path.startswith("tests/") and path.endswith(".cpp") and name.startswith("test_")


def unregistered_tests(added: list[str], registry_text: str) -> list[str]:
    """Added test files whose repository path (Python) or file name (C++ under tests/) no registry mentions."""
    missing = []
    for path in added:
        if not is_test_file(path):
            continue
        key = path.rsplit("/", 1)[-1] if path.endswith(".cpp") else path
        if key not in registry_text:
            missing.append(path)
    return missing


def manifest_paths(root: Path) -> list[str]:
    """Repository paths listed in the TESTS manifests under ``root`` (T-182; the gate checks the rest)."""
    sys.path.insert(0, str(ROOT / "tools"))
    import check_all
    paths = []
    for manifest in sorted(p for p in check_all.repo_files(root) if p.rsplit("/", 1)[-1] == check_all.TEST_MANIFEST_NAME):
        entries, _ = check_all.parse_manifest_text(manifest, (root / manifest).read_text(encoding="utf-8"))
        paths += [e.path for e in entries]
    return paths


def check_tests_registered(root: Path = ROOT, base: str = "origin/main") -> str:
    common = git("merge-base", base, "HEAD", root=root)
    added = [p for p in git("diff", "--name-only", "--diff-filter=A", common, "HEAD", root=root).splitlines() if p]
    text = "\n".join((root / r).read_text(encoding="utf-8") for r in REGISTRIES if (root / r).is_file())
    text += "\n" + "\n".join(manifest_paths(root))
    missing = unregistered_tests(added, text)
    if missing:
        raise Fail(f"test(s) not registered in a TESTS manifest / {' / '.join(REGISTRIES)}: {', '.join(missing[:3])}")
    return f"{sum(is_test_file(p) for p in added)} new test file(s) registered"


def check_links(root: Path = ROOT) -> str:
    proc = subprocess.run([sys.executable, str(root / "tools/check_doc_links.py")], cwd=root,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        first = next((l for l in proc.stdout.splitlines() if "->" in l), "broken link(s)")
        raise Fail(f"doc links: {first}"[:160])
    return "links ok"


def ready_line(task: str, branch: str, sha: str, input_sha: str, evidence: str, ledger: str, cost: str,
               note: str = "", now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.timezone.utc)
    ledger = ledger if ledger.startswith("ledger:") else f"ledger: {ledger}"
    parts = [now.strftime("%Y-%m-%dT%H:%MZ"), task, "READY", f"{branch}@{sha[:7]}", f"input {input_sha[:7]}",
             f"ev {evidence}", ledger, cost]
    if note:
        parts.append(note)
    line = " | ".join(parts)
    if len(line) > MAX_LINE:
        raise Fail(f"READY line is {len(line)} chars (max {MAX_LINE}): shorten --evidence/--note")
    return line


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", required=True)
    parser.add_argument("--input", required=True, help="input SHA from the task prompt")
    parser.add_argument("--evidence", required=True, help="evidence/report path")
    parser.add_argument("--ledger", required=True, help='"build N · render N · tests N · ci N · wait N"')
    parser.add_argument("--cost", required=True, help='"$X / ctx Yk" from your own get_session usage')
    parser.add_argument("--note", default="")
    parser.add_argument("--branch", default="", help="default: current branch")
    parser.add_argument("--base", default="origin/main", help="base for the new-test check")
    args = parser.parse_args(argv)
    try:
        branch = args.branch or git("branch", "--show-current")
        if not branch:
            raise Fail("detached HEAD: check out the task branch")
        check_clean()
        sha = check_pushed(branch)
        check_claims(args.task)
        check_write_set(args.task)
        check_tests_registered(base=args.base)
        check_links()
        line = ready_line(args.task, branch, sha, args.input, args.evidence, args.ledger, args.cost, args.note)
    except Fail as exc:
        print(f"NOT READY: {exc}", file=sys.stderr)
        return 1
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
