#!/usr/bin/env python3
"""Supervisor integration tool (delivery plan rev. 2, sections 3, 5 and 8.1).

    python tools/integrate.py claims --check T-NNN        # may T-NNN start? overlap = exit 1
    python tools/integrate.py claims --list               # the parsed claims table
    python tools/integrate.py writeset --task T-NNN [--base origin/staging]   # diff inside the claim? (gate check)
    python tools/integrate.py stage t-NNN-<agent>-<slug> [--dry-run] [--blender B]
    python tools/integrate.py promote [--dry-run]
    python tools/integrate.py backup <branch> [<branch> ...] [--dry-run]

Claims live in docs/process/OWNERSHIP.md: one table row per running task with the columns
Task | Lane | Branch | Write-set | Depends on | Versions bumped. Write-set and depends-on entries are back-ticked,
repository-relative globs (`*` stays inside one folder, `**` crosses folders, `{a,b}` expands, a trailing `/`
means the whole folder). A depends-on entry followed by "(stable)" only reads a stable interface and is reported
as a warning instead of a conflict. A task that is not in the table is read from the "## Write-set" and
"## Depends on" sections of docs/tasks/T-NNN.md (everything after "Not:" is excluded from the write-set).

stage: trial merge of origin/<branch> into origin/staging in a temporary worktree, gate (tools/check_all.py)
on the merge result, then (without --dry-run) a --no-ff merge commit pushed to staging.
promote: fast-forward main to staging. A backup of the current main is pushed first as the branch
archive/backup-<UTC date-time>-main; the backup workflow (.github/workflows/backup.yml) turns every push to
main/staging and every archive/backup-* branch into a durable backup/<UTC date-time>/<branch> tag (cloud sessions
cannot push tags themselves). Nothing here deletes branches or tags.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import functools
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
OWNERSHIP = ROOT / "docs" / "process" / "OWNERSHIP.md"
TASKS = ROOT / "docs" / "tasks"
STAGING = "staging"
MAIN = "main"


# --------------------------------------------------------------------------- globs

def expand_braces(pattern: str) -> list[str]:
    match = re.search(r"\{([^{}]*)\}", pattern)
    if not match:
        return [pattern]
    out = []
    for option in match.group(1).split(","):
        out.extend(expand_braces(pattern[:match.start()] + option + pattern[match.end():]))
    return out


def normalize_globs(pattern: str) -> list[str]:
    """Brace expansion, folder entries ('dir/' -> 'dir/**') and '**/' as zero or more folders."""
    pattern = pattern.strip().replace("\\", "/")
    while pattern.startswith("./"):
        pattern = pattern[2:]
    out: list[str] = []
    for item in expand_braces(pattern):
        if item.endswith("/"):
            item += "**"
        variants = [item]
        while any("**/" in v for v in variants):
            nxt = []
            for v in variants:
                k = v.find("**/")
                if k < 0:
                    nxt.append(v)
                    continue
                nxt.append(v[:k] + v[k + 3:])          # zero folders
                nxt.append(v[:k] + "\0" + v[k + 2:])   # '**' (marked) followed by '/'
            variants = nxt
        out.extend(v.replace("\0", "**") for v in variants)
    return sorted(set(out))


def tokens(glob: str) -> tuple:
    """Tokens: ('c', ch) literal, ('?', chars|None) one non-'/' char, ('*',) within a folder, ('**',) anything."""
    out = []
    i = 0
    while i < len(glob):
        ch = glob[i]
        if glob.startswith("**", i):
            out.append(("**",))
            i += 2
        elif ch == "*":
            out.append(("*",))
            i += 1
        elif ch == "?":
            out.append(("?", None))
            i += 1
        elif ch == "[" and glob.find("]", i + 2) > 0:
            end = glob.find("]", i + 2)
            body = glob[i + 1:end]
            negate = body.startswith(("!", "^"))
            body = body[1:] if negate else body
            chars = set()
            j = 0
            while j < len(body):
                if j + 2 < len(body) and body[j + 1] == "-":
                    chars.update(chr(c) for c in range(ord(body[j]), ord(body[j + 2]) + 1))
                    j += 3
                else:
                    chars.add(body[j])
                    j += 1
            if negate:  # approximation: printable ASCII not listed
                chars = {chr(c) for c in range(32, 127)} - chars
            out.append(("?", frozenset(chars - {"/"})))
            i = end + 1
        else:
            out.append(("c", ch))
            i += 1
    return tuple(out)


STARS = ("*", "**")


def _one_char_meets(a, b) -> bool:
    """Can single-character tokens a and b produce the same character?"""
    if a[0] == "c" and b[0] == "c":
        return a[1] == b[1]
    if a[0] == "c":
        a, b = b, a
    if b[0] == "c":
        return b[1] != "/" and (a[1] is None or b[1] in a[1])
    if a[1] is None or b[1] is None:
        return (a[1] is None or bool(a[1])) and (b[1] is None or bool(b[1]))
    return bool(a[1] & b[1])


def _intersects(p: tuple, q: tuple) -> bool:
    """Is there a string matched by both token sequences? (Overlapping star spans can always be dropped, so when
    both sides are stars it suffices to let one of them end.)"""
    @functools.lru_cache(maxsize=None)
    def go(i: int, j: int) -> bool:
        a = p[i] if i < len(p) else None
        b = q[j] if j < len(q) else None
        if a is None and b is None:
            return True
        if a is not None and a[0] in STARS:
            if go(i + 1, j):
                return True
            if b is not None and b[0] not in STARS and (a[0] == "**" or b != ("c", "/")) and go(i, j + 1):
                return True
        if b is not None and b[0] in STARS:
            if go(i, j + 1):
                return True
            if a is not None and a[0] not in STARS and (b[0] == "**" or a != ("c", "/")) and go(i + 1, j):
                return True
        if a is None or b is None or a[0] in STARS or b[0] in STARS:
            return False
        return _one_char_meets(a, b) and go(i + 1, j + 1)

    return go(0, 0)


def globs_overlap(a: str, b: str) -> bool:
    """True if at least one path can match both globs."""
    return any(_intersects(tokens(x), tokens(y)) for x in normalize_globs(a) for y in normalize_globs(b))


def path_matches(path: str, pattern: str) -> bool:
    path = path.replace("\\", "/")
    return any(_intersects(tokens(glob), tuple(("c", ch) for ch in path)) for glob in normalize_globs(pattern))


# --------------------------------------------------------------------------- claims

@dataclasses.dataclass
class Claim:
    task: str
    lane: str = ""
    branch: str = ""
    write_set: list[str] = dataclasses.field(default_factory=list)
    depends_on: list[str] = dataclasses.field(default_factory=list)
    stable_depends: list[str] = dataclasses.field(default_factory=list)
    versions: list[str] = dataclasses.field(default_factory=list)
    source: str = ""


def _ticked(cell: str) -> list[str]:
    return [item.strip() for item in re.findall(r"`([^`]+)`", cell) if item.strip()]


def _split_depends(cell: str) -> tuple[list[str], list[str]]:
    hard, stable = [], []
    for match in re.finditer(r"`([^`]+)`(\s*\(([^)]*)\))?", cell):
        (stable if match.group(3) and "stable" in match.group(3).casefold() else hard).append(match.group(1).strip())
    return hard, stable


def _versions(cell: str) -> list[str]:
    items = _ticked(cell) or [v.strip() for v in cell.split(",")]
    return [v for v in items if v and v not in {"—", "-", "none", "n/a"}]


def parse_ownership(text: str, source: str = "docs/process/OWNERSHIP.md") -> list[Claim]:
    claims: list[Claim] = []
    header: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            header = [] if not line else header
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and cells[0].casefold() == "task":
            header = [cell.casefold() for cell in cells]
            continue
        if not header or set(line) <= set("|-: "):
            continue
        row = dict(zip(header, cells))
        task = row.get("task", "").strip("* ")
        if not re.fullmatch(r"T-\d+[A-Za-z0-9]*", task):
            continue
        hard, stable = _split_depends(row.get("depends on", ""))
        branch = _ticked(row.get("branch", ""))
        claims.append(Claim(
            task=task, lane=row.get("lane", ""), branch=branch[0] if branch else row.get("branch", "").strip(),
            write_set=_ticked(row.get("write-set", "")), depends_on=hard, stable_depends=stable,
            versions=_versions(row.get("versions bumped", "")), source=source,
        ))
    return claims


def parse_task_file(text: str, task: str, source: str = "") -> Claim:
    def section(name: str) -> str:
        match = re.search(rf"(?ms)^##\s+{re.escape(name)}\s*$(.*?)(?=^##\s|\Z)", text)
        return match.group(1) if match else ""

    write = section("Write-set")
    write = re.split(r"(?m)(?:^|\s)Not:", write, maxsplit=1)[0]
    hard, stable = _split_depends(section("Depends on"))
    hard = [item for item in hard if "/" in item or "." in item]
    stable = [item for item in stable if "/" in item or "." in item]
    branch = re.search(r"branch `([^`]+)`", text)
    versions = _versions(section("Versions bumped")) if section("Versions bumped").strip() else []
    return Claim(task=task, branch=branch.group(1) if branch else "", write_set=_ticked(write),
                 depends_on=hard, stable_depends=stable, versions=versions, source=source)


def load_claims(ownership: Path = OWNERSHIP) -> list[Claim]:
    return parse_ownership(ownership.read_text(encoding="utf-8"), ownership.relative_to(ROOT).as_posix()
                           if ownership.is_relative_to(ROOT) else str(ownership))


def find_claim(task: str, claims: list[Claim] | None = None, tasks_dir: Path = TASKS) -> Claim | None:
    claims = load_claims() if claims is None else claims
    for claim in claims:
        if claim.task.casefold() == task.casefold():
            return claim
    path = tasks_dir / f"{task}.md"
    if path.is_file():
        return parse_task_file(path.read_text(encoding="utf-8"), task, path.as_posix())
    return None


def claim_for_branch(branch: str, claims: list[Claim] | None = None) -> Claim | None:
    claims = load_claims() if claims is None else claims
    for claim in claims:
        if claim.branch and claim.branch == branch:
            return claim
    task = task_from_branch(branch)
    return find_claim(task, claims) if task else None


def task_from_branch(branch: str) -> str:
    match = re.match(r"^(?:refs/heads/)?t-(\d+[a-z0-9]*?)(?:-|$)", branch or "")
    return f"T-{match.group(1)}" if match else ""


def check_claims(candidate: Claim, others: list[Claim]) -> tuple[list[str], list[str]]:
    """Return (conflicts, warnings) of `candidate` against every other running claim."""
    conflicts, warnings = [], []
    for other in others:
        if other.task.casefold() == candidate.task.casefold():
            continue
        for mine in candidate.write_set:
            for theirs in other.write_set:
                if globs_overlap(mine, theirs):
                    conflicts.append(f"write-set overlap with {other.task}: {mine} ~ {theirs}")
        for dep in candidate.depends_on:
            for theirs in other.write_set:
                if globs_overlap(dep, theirs):
                    conflicts.append(f"depends on {dep}, which {other.task} is changing ({theirs})")
        for dep in candidate.stable_depends:
            for theirs in other.write_set:
                if globs_overlap(dep, theirs):
                    warnings.append(f"reads the stable interface of {dep}; {other.task} changes it ({theirs})")
        for theirs_dep in other.depends_on:
            for mine in candidate.write_set:
                if globs_overlap(theirs_dep, mine):
                    conflicts.append(f"{other.task} depends on {theirs_dep}, which this task would change ({mine})")
        shared_versions = sorted(set(candidate.versions) & set(other.versions))
        conflicts.extend(f"version {v} is also bumped by {other.task}" for v in shared_versions)
    return conflicts, warnings


def write_set_violations(paths, claim: Claim) -> list[str]:
    return sorted(path for path in paths if not any(path_matches(path, pattern) for pattern in claim.write_set))


# --------------------------------------------------------------------------- git helpers

def git(*args: str, cwd: Path = ROOT, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    if not capture:
        print("+ git " + " ".join(args), flush=True)
    return subprocess.run(["git", *args], cwd=cwd, check=check, text=True,
                          stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None)


def changed_since_merge_base(base: str, head: str = "HEAD") -> set[str]:
    common = git("merge-base", base, head, check=False).stdout.strip() or base
    out = git("diff", "--name-only", "-z", common, head, "--").stdout
    return {p for p in out.split("\0") if p}


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


# --------------------------------------------------------------------------- commands

def cmd_claims(args) -> int:
    claims = load_claims()
    if args.list:
        for claim in claims:
            print(f"{claim.task} [{claim.lane}] {claim.branch}: write={claim.write_set} depends={claim.depends_on} "
                  f"stable={claim.stable_depends} versions={claim.versions}")
        return 0
    candidate = find_claim(args.check, claims)
    if candidate is None:
        print(f"FAIL claims: no claim or task file for {args.check}")
        return 1
    if not candidate.write_set:
        print(f"FAIL claims: {args.check} declares no write-set ({candidate.source})")
        return 1
    conflicts, warnings = check_claims(candidate, claims)
    for warning in warnings:
        print(f"WARN {warning}")
    for conflict in conflicts:
        print(f"CONFLICT {conflict}")
    print(f"{'FAIL' if conflicts else 'PASS'} claims {candidate.task}: {len(conflicts)} conflict(s), "
          f"{len(warnings)} warning(s) against {len([c for c in claims if c.task != candidate.task])} running task(s)")
    return 1 if conflicts else 0


def cmd_writeset(args) -> int:
    claim = find_claim(args.task)
    if claim is None or not claim.write_set:
        print(f"FAIL Write-set: no claim for {args.task}")
        return 1
    bad = write_set_violations(changed_since_merge_base(args.base), claim)
    for path in bad:
        print(f"outside {claim.task} write-set: {path}")
    print(f"{'FAIL' if bad else 'PASS'} Write-set {claim.task}: {len(bad)} path(s) outside the claim")
    return 1 if bad else 0


def gate(worktree: Path, base: str, task: str, blender: str, artifacts: Path) -> int:
    command = [sys.executable, str(worktree / "tools" / "check_all.py"), "--base", base, "--merge-status", "clean",
               "--build-dir", str(artifacts / "cpp"), "--artifacts-dir", str(artifacts / "gate")]
    if task:
        command += ["--task", task]
    if blender:
        command += ["--blender", blender]
    print("+ " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=worktree).returncode


def cmd_stage(args) -> int:
    branch = args.branch.removeprefix("origin/")
    git("fetch", "--no-tags", "origin", f"+refs/heads/{STAGING}:refs/remotes/origin/{STAGING}",
        f"+refs/heads/{branch}:refs/remotes/origin/{branch}", capture=False)
    task = claim_for_branch(branch)
    task_id = task.task if task else task_from_branch(branch)
    with tempfile.TemporaryDirectory(prefix="integrate-stage-") as temp:
        worktree = Path(temp) / "wt"
        git("worktree", "add", "--detach", str(worktree), f"origin/{STAGING}", capture=False)
        try:
            merge = git("merge", "--no-ff", "--no-commit", f"origin/{branch}", cwd=worktree, check=False)
            if merge.returncode:
                conflicts = git("diff", "--name-only", "--diff-filter=U", cwd=worktree, check=False).stdout.split()
                print(f"FAIL trial merge: conflicts in {', '.join(conflicts) or '(unknown)'}")
                return 1
            print("PASS trial merge: clean")
            artifacts = Path(args.artifacts or (ROOT / "build" / "integrate" / branch.replace("/", "_")))
            if gate(worktree, f"origin/{STAGING}", task_id, args.blender, artifacts):
                print("FAIL gate on the trial merge; staging unchanged")
                return 1
            if args.dry_run:
                print(f"DRY-RUN: would commit 'Stage {task_id or branch}' (--no-ff) and push it to {STAGING}")
                return 0
            git("commit", "-m", f"Stage {task_id or branch}: merge {branch} into {STAGING}", cwd=worktree, capture=False)
            git("push", "origin", f"HEAD:refs/heads/{STAGING}", cwd=worktree, capture=False)
            print(f"PASS staged {branch} into {STAGING}")
            return 0
        finally:
            git("merge", "--abort", cwd=worktree, check=False)
            git("worktree", "remove", "--force", str(worktree), check=False)


def push_backup_branches(branches: list[str], dry_run: bool) -> list[str]:
    stamp = utc_stamp()
    names = []
    for branch in branches:
        sha = git("rev-parse", f"origin/{branch}").stdout.strip()
        name = f"archive/backup-{stamp}-{branch.replace('/', '-')}"
        names.append(name)
        if dry_run:
            print(f"DRY-RUN: would push {sha[:12]} to {name} (tagged backup/<UTC>/{branch} by backup.yml)")
        else:
            git("push", "origin", f"{sha}:refs/heads/{name}", capture=False)
            print(f"backup {branch} {sha[:12]} -> {name}")
    return names


def cmd_promote(args) -> int:
    git("fetch", "--no-tags", "origin", f"+refs/heads/{MAIN}:refs/remotes/origin/{MAIN}",
        f"+refs/heads/{STAGING}:refs/remotes/origin/{STAGING}", capture=False)
    if git("merge-base", "--is-ancestor", f"origin/{MAIN}", f"origin/{STAGING}", check=False).returncode:
        print(f"FAIL promote: {STAGING} is not a fast-forward of {MAIN}")
        return 1
    ahead = git("rev-list", "--count", f"origin/{MAIN}..origin/{STAGING}").stdout.strip()
    if ahead == "0":
        print(f"PASS promote: {MAIN} already equals {STAGING}")
        return 0
    push_backup_branches([MAIN], args.dry_run)
    if args.dry_run:
        print(f"DRY-RUN: would fast-forward {MAIN} by {ahead} commit(s) to origin/{STAGING}")
        return 0
    git("push", "origin", f"origin/{STAGING}:refs/heads/{MAIN}", capture=False)
    print(f"PASS promoted: {MAIN} fast-forwarded by {ahead} commit(s)")
    return 0


def cmd_backup(args) -> int:
    git("fetch", "--no-tags", "origin", *[f"+refs/heads/{b}:refs/remotes/origin/{b}" for b in args.branches],
        capture=False)
    push_backup_branches(args.branches, args.dry_run)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    claims = sub.add_parser("claims", help="check or list file claims")
    group = claims.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", metavar="T-NNN")
    group.add_argument("--list", action="store_true")
    claims.set_defaults(func=cmd_claims)
    writeset = sub.add_parser("writeset", help="is the branch diff inside the task's claim?")
    writeset.add_argument("--task", required=True)
    writeset.add_argument("--base", default=f"origin/{STAGING}")
    writeset.set_defaults(func=cmd_writeset)
    stage = sub.add_parser("stage", help="trial merge + gate + --no-ff merge into staging")
    stage.add_argument("branch")
    stage.add_argument("--dry-run", action="store_true")
    stage.add_argument("--blender", default=os.environ.get("BLENDER", ""))
    stage.add_argument("--artifacts", default="")
    stage.set_defaults(func=cmd_stage)
    promote = sub.add_parser("promote", help="backup main, then fast-forward main to staging")
    promote.add_argument("--dry-run", action="store_true")
    promote.set_defaults(func=cmd_promote)
    backup = sub.add_parser("backup", help="push archive/backup-<UTC>-<branch> (tagged by backup.yml)")
    backup.add_argument("branches", nargs="+")
    backup.add_argument("--dry-run", action="store_true")
    backup.set_defaults(func=cmd_backup)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
