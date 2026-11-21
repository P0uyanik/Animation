#!/usr/bin/env python3
"""T-182 test registry and guard rule: manifests, "no unregistered test", and the trailer rule for tests.

Adding a new test file (or appending its manifest entry) needs no Supervisor-Approved trailer; modifying, renaming
or deleting an existing test, or removing/changing an existing manifest line, still does. Plain Python, no Blender;
the guard cases run against scratch git repositories."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import check_all  # noqa: E402
import ready  # noqa: E402

FAILS: list[str] = []
PATTERNS = check_all.guarded_patterns()


def check(cond, what):
    if not cond:
        FAILS.append(what)
        print(f"FAIL {what}")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


# ---- manifest format ------------------------------------------------------------------------------------------

def test_parse():
    text = ("# comment\n\nrun test_a.py --selftest   # trailing comment\nblender sub/b_test.py face\n"
            "via test_c.py tools/x/run.py\nlocal test_d.py 'needs Blender'\n")
    entries, problems = check_all.parse_manifest_text("pkg/tests/TESTS", text)
    check(not problems, f"valid manifest parses: {problems}")
    check([(e.kind, e.path, e.rest) for e in entries] == [
        ("run", "pkg/tests/test_a.py", ("--selftest",)), ("blender", "pkg/tests/sub/b_test.py", ("face",)),
        ("via", "pkg/tests/test_c.py", ("tools/x/run.py",)), ("local", "pkg/tests/test_d.py", ("needs Blender",))],
        f"entries: {entries}")
    for bad, why in (("walk test_a.py", "unknown kind"), ("run ../test_a.py", "'..' path"),
                     ("run /abs/test_a.py", "absolute path"), ("local test_a.py", "local without reason"),
                     ("blender test_a.py", "blender without unit"), ("via test_a.py a b", "via with two runners"),
                     ("run", "missing file")):
        _, problems = check_all.parse_manifest_text("pkg/tests/TESTS", bad + "\n")
        check(len(problems) == 1, f"{why} is rejected: {bad!r} -> {problems}")


# ---- registry: every test on disk is in exactly one manifest -----------------------------------------------------

def scratch_repo(tmp: Path, files: dict[str, str]) -> Path:
    repo = tmp / "repo"
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "base")
    git(repo, "config", "user.email", "t@example.invalid")
    git(repo, "config", "user.name", "t")
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return repo


def test_registry(tmp: Path):
    base = {"pkg/tests/TESTS": "run test_a.py\nblender b_test.py face\nvia test_c.py pkg/run.py\n",
            "pkg/tests/test_a.py": "", "pkg/tests/b_test.py": "", "pkg/tests/test_c.py": "", "pkg/run.py": "",
            "pkg/tests/helper.py": "", "docs/x/test_notes.py": ""}
    repo = scratch_repo(tmp, base)
    entries, problems = check_all.test_registry(repo, ["face"])
    check(not problems and len(entries) == 3, f"complete registry passes (helpers, docs/ ignored): {problems}")
    (repo / "pkg/tests/test_new.py").write_text("")  # untracked counts too
    _, problems = check_all.test_registry(repo, ["face"])
    check(any("in no TESTS manifest" in p and "pkg/tests/test_new.py" in p for p in problems),
          f"a test on disk in no manifest fails: {problems}")
    (repo / "pkg/tests/test_new.py").unlink()
    (repo / "other/tests").mkdir(parents=True)
    (repo / "other/tests/test_a.py").write_text("")
    (repo / "other/tests/TESTS").write_text("run test_a.py\n")
    _, problems = check_all.test_registry(repo, ["face"])
    check(any("unique" in p and "test_a.py" in p for p in problems), f"duplicate module name fails: {problems}")
    shutil.rmtree(repo / "other")
    for text, why in (("run test_a.py\nrun test_a.py\nblender b_test.py face\nvia test_c.py pkg/run.py\n", "twice"),
                      ("run test_a.py\nblender b_test.py nope\nvia test_c.py pkg/run.py\n", "unknown unit"),
                      ("run test_a.py\nblender b_test.py face\nvia test_c.py pkg/none.py\n", "unknown runner"),
                      ("run test_a.py\nrun gone.py\nblender b_test.py face\nvia test_c.py pkg/run.py\n", "missing")):
        (repo / "pkg/tests/TESTS").write_text(text)
        _, problems = check_all.test_registry(repo, ["face"])
        check(len(problems) == 1, f"registry problem ({why}) reported once: {problems}")


# ---- guard rule ---------------------------------------------------------------------------------------------------

def test_free_change_rule():
    def free(path, status, statuses=None, old="", new=""):
        return check_all.free_test_change(path, status, PATTERNS, statuses or {path: status},
                                          lambda p: old, lambda p: new)
    check(free("pipeline/x/tests/test_new.py", "A"), "added test file is free")
    check(free("tools/x/foo_test.py", "A"), "added *_test.py is free")
    check(free("tests/test_new.cpp", "A"), "added C++ test source is free")
    check(free("tools/x/tests/TESTS", "A"), "added manifest is free")
    check(not free("pipeline/x/tests/test_old.py", "M"), "modified test needs approval")
    check(not free("pipeline/x/tests/test_old.py", "D"), "deleted test needs approval")
    check(not free("pipeline/x/tests/test_old.py", "T"), "type-changed test needs approval")
    check(not free("pipeline/x/tests/helper.py", "A"), "added helper in a tests dir needs approval (shadowing)")
    check(not free("pipeline/x/tests/json.py", "A"), "added module that could shadow an import needs approval")
    check(not free("tests/data/new.json", "A"), "added test data needs approval")
    check(not free("tools/regression/tests/test_new.py", "A"), "added test under the gate's own dir needs approval")
    check(not free("engine/render/tests/test_new.py", "A"), "added test in the frozen renderer needs approval")
    check(not free("tests/test_x_threshold.json", "A"), "added threshold file needs approval")
    check(not free("tools/check_all.py", "A"), "non-test guarded file is never free")
    old = "run test_a.py\n"
    statuses = {"p/tests/TESTS": "M", "p/tests/test_b.py": "A"}
    check(free("p/tests/TESTS", "M", statuses, old, old + "run test_b.py  # new\n"),
          "appending an entry for a new test is free")
    check(not free("p/tests/TESTS", "M", statuses, old, old + "run test_z.py\n"),
          "appending an entry for a file this change does not add needs approval")
    check(not free("p/tests/TESTS", "M", statuses, old + "run test_c.py\n", "run test_a.py\n"),
          "removing a manifest line needs approval")
    check(not free("p/tests/TESTS", "M", statuses, old, "run test_a.py --flag\n"),
          "changing a manifest line needs approval")
    check(not free("p/tests/TESTS", "M", statuses, old, "run test_b.py\n" + old),
          "inserting before existing lines needs approval")
    check(not free("p/tests/TESTS", "D", statuses), "deleting a manifest needs approval")


def guard_in(repo: Path) -> check_all.Result:
    saved = check_all.ROOT, check_all.GUARDED_PATHS
    check_all.ROOT, check_all.GUARDED_PATHS = repo, repo / "tools/guarded_paths.txt"
    try:
        return check_all.check_guarded("base", check_all.changed_paths("base"))
    finally:
        check_all.ROOT, check_all.GUARDED_PATHS = saved


def test_guard_git(tmp: Path):
    files = {"tools/guarded_paths.txt": check_all.GUARDED_PATHS.read_text(encoding="utf-8"),
             "pkg/tests/TESTS": "run test_a.py\nrun test_b.py\n",
             "pkg/tests/test_a.py": "print('a')\n", "pkg/tests/test_b.py": "print('b')\n"}
    repo = scratch_repo(tmp, files)

    def scenario(name, edit, needs, trailer_for=()):
        git(repo, "checkout", "-q", "-B", "work", "base")
        edit()
        git(repo, "add", "-A")
        msg = f"{name}" + "".join(f"\n\nSupervisor-Approved: {p}" for p in trailer_for)
        git(repo, "commit", "-q", "--allow-empty", "-m", msg)
        result = guard_in(repo)
        if needs:
            check(not result.ok and all(p in result.detail for p in needs), f"{name}: needs {needs}: {result.detail}")
        else:
            check(result.ok, f"{name}: passes without trailer: {result.detail}")
        return result

    def append_new():
        (repo / "pkg/tests/test_new.py").write_text("print('new')\n")
        with open(repo / "pkg/tests/TESTS", "a", encoding="utf-8") as fh:
            fh.write("run test_new.py\n")
    scenario("add test + append entry", append_new, [])

    def new_dir():
        (repo / "lib/tests").mkdir(parents=True)
        (repo / "lib/tests/test_lib.py").write_text("")
        (repo / "lib/tests/TESTS").write_text("run test_lib.py\n")
    scenario("add test in a new directory with a new manifest", new_dir, [])

    scenario("modify", lambda: (repo / "pkg/tests/test_a.py").write_text("print('changed')\n"),
             ["pkg/tests/test_a.py"])
    scenario("modify with trailer", lambda: (repo / "pkg/tests/test_a.py").write_text("print('changed')\n"),
             [], ["pkg/tests/test_a.py"])

    def rename():
        git(repo, "mv", "pkg/tests/test_a.py", "pkg/tests/test_c.py")
        (repo / "pkg/tests/TESTS").write_text("run test_c.py\nrun test_b.py\n")
    scenario("rename (even unchanged content)", rename, ["pkg/tests/test_a.py", "pkg/tests/TESTS"])

    def delete():
        (repo / "pkg/tests/test_b.py").unlink()
        (repo / "pkg/tests/TESTS").write_text("run test_a.py\n")
    scenario("delete", delete, ["pkg/tests/test_b.py", "pkg/tests/TESTS"])

    scenario("remove from manifest only", lambda: (repo / "pkg/tests/TESTS").write_text("run test_a.py\n"),
             ["pkg/tests/TESTS"])
    scenario("change a manifest entry", lambda: (repo / "pkg/tests/TESTS").write_text(
        "run test_a.py --skip-slow\nrun test_b.py\n"), ["pkg/tests/TESTS"])
    scenario("add helper module next to tests", lambda: (repo / "pkg/tests/json.py").write_text(""),
             ["pkg/tests/json.py"])

    git(repo, "checkout", "-q", "-B", "work", "base")
    (repo / "pkg/tests/test_new.py").write_text("")
    result = guard_in(repo)  # uncommitted new test: the existing "dirty" rule still applies
    check(not result.ok and "pkg/tests/test_new.py" in result.detail, f"uncommitted new test fails: {result.detail}")
    (repo / "pkg/tests/test_new.py").unlink()


# ---- this repository ------------------------------------------------------------------------------------------------

def test_repository():
    check(all(p in PATTERNS for p in check_all.TEST_GUARD_PATTERNS),
          "every test-only pattern is in tools/guarded_paths.txt")
    entries, problems = check_all.test_registry()
    check(not problems, f"repository registry is complete: {problems[:3]}")
    before = (ROOT / "docs/evaluation/process/T-182/commands_before.txt").read_text(encoding="utf-8").split("\n")
    after = {" ".join([Path(c[1]).relative_to(ROOT).as_posix(), *c[2:]])
             for c in check_all.registry_run_commands(entries)}
    dropped = [c for c in before if c and c not in after]
    check(not dropped, f"no pre-T-182 test command dropped: {dropped}")
    check("tools/tests/test_test_registry.py" in ready.manifest_paths(ROOT), "this test is registered")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="t182-"))
    try:
        test_parse()
        test_registry(tmp)
        test_free_change_rule()
        test_guard_git(tmp)
        test_repository()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"test_test_registry: {'FAIL ' + str(len(FAILS)) if FAILS else 'all checks pass'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
