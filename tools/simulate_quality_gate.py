#!/usr/bin/env python3
"""Run T-023 acceptance simulations on temporary local branches.

Nothing is pushed. Every branch created by this script has a unique
``t023-sim-<pid>-`` prefix and only those branches are deleted afterwards.
Run this only from a clean, committed T-023 branch after Supervisor approval
trailers have made its guarded-path check green.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run(command, *, check=True, capture=False, env=None):
    print("+", subprocess.list2cmdline([str(part) for part in command]), flush=True)
    return subprocess.run(
        command, cwd=ROOT, check=check, env=env,
        text=capture, stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def git(*args, **kwargs):
    return run(["git", *args], **kwargs)


class Simulations:
    def __init__(self, blender):
        self.start_branch = git("branch", "--show-current", capture=True).stdout.strip()
        self.start_commit = git("rev-parse", "HEAD", capture=True).stdout.strip()
        self.prefix = f"t023-sim-{os.getpid()}-"
        self.created = []
        self.results = []
        self.env = dict(os.environ)
        if blender:
            self.env["BLENDER"] = str(Path(blender).resolve())

    def branch(self, suffix, start=None):
        name = self.prefix + suffix
        git("switch", "--create", name, start or self.start_commit)
        self.created.append(name)
        return name

    def commit(self, paths, subject, trailers=()):
        git("add", "--", *paths)
        command = ["git", "commit", "-m", subject]
        if trailers:
            command.extend(["-m", "\n".join(f"Supervisor-Approved: {path}" for path in trailers)])
        run(command)

    def gate(self, label, base, expected):
        slug = label.lower().replace(" ", "-")
        command = [
            sys.executable, "tools/check_all.py", "--base", base,
            "--build-dir", "build/t023-sim/cpp", "--artifacts-dir", f"build/t023-sim/{slug}",
        ]
        proc = run(command, check=False, env=self.env)
        actual = "PASS" if proc.returncode == 0 else "FAIL"
        ok = actual == expected
        self.results.append((label, expected, actual, ok))
        print(f"SIMULATION {label}: expected {expected}, got {actual}")
        if not ok:
            raise RuntimeError(f"{label}: expected {expected}, got {actual}")

    def reset(self):
        if git("rev-parse", "--verify", "--quiet", "MERGE_HEAD", check=False).returncode == 0:
            git("merge", "--abort")
        git("switch", self.start_branch)

    def delete_created(self):
        self.reset()
        for name in reversed(self.created):
            if not name.startswith(self.prefix):
                raise RuntimeError(f"refusing to delete non-simulation branch {name}")
            git("branch", "--delete", "--force", name)

    def frozen(self):
        self.branch("frozen")
        path = Path("assets/characters/boy_yellow_hoodie/experiments/face/F09_jaw_corner_center.json")
        path.write_bytes(path.read_bytes() + b"\n")
        self.commit([str(path)], "T-023 simulation: change frozen file")
        self.gate("frozen file", self.start_commit, "FAIL")
        self.reset()

    def shared_name(self):
        self.branch("shared-name")
        path = Path("engine/t023_shared_name_probe.cpp")
        path.write_text('static const char* probe = "boy_yellow_hoodie";\n', encoding="utf-8")
        self.commit([str(path)], "T-023 simulation: character name in shared code")
        self.gate("shared character name", self.start_commit, "FAIL")
        self.reset()

    def threshold(self):
        self.branch("threshold")
        path = Path("docs/references/VISUAL_TARGET.md")
        path.write_text(path.read_text(encoding="utf-8") + "\n<!-- T-023 threshold simulation -->\n", encoding="utf-8")
        self.commit([str(path)], "T-023 simulation: change guarded threshold")
        self.gate("threshold unapproved", self.start_commit, "FAIL")
        git("commit", "--allow-empty", "-m", "T-023 simulation: supervisor approval", "-m",
            "Supervisor-Approved: docs/references/VISUAL_TARGET.md")
        self.gate("threshold approved", self.start_commit, "PASS")
        self.reset()

    def broken_cpp(self):
        self.branch("broken-cpp")
        path = Path("tests/test_engine.cpp")
        addition = '\nTEST_CASE("T-023 simulated C++ failure") { CHECK(false); }\n'
        path.write_text(path.read_text(encoding="utf-8") + addition, encoding="utf-8")
        self.commit([str(path)], "T-023 simulation: broken C++ test", [str(path).replace("\\", "/")])
        self.gate("broken C++ test", self.start_commit, "FAIL")
        self.reset()

    def textual_conflict(self):
        path = Path("docs/process/TASK_LOG.md")
        main_branch = self.branch("conflict-main")
        text = path.read_text(encoding="utf-8")
        path.write_text("# T-023 simulated main-side heading\n" + "\n".join(text.splitlines()[1:]) + "\n", encoding="utf-8")
        self.commit([str(path)], "T-023 simulation: main side of textual conflict")
        self.reset()
        self.branch("conflict-task")
        path.write_text("# T-023 simulated task-side heading\n" + "\n".join(text.splitlines()[1:]) + "\n", encoding="utf-8")
        self.commit([str(path)], "T-023 simulation: task side of textual conflict")
        proc = git("merge", "--no-commit", main_branch, check=False)
        conflicts = git("diff", "--name-only", "--diff-filter=U", capture=True).stdout.splitlines()
        actual = "FAIL" if proc.returncode != 0 and conflicts else "PASS"
        ok = actual == "FAIL"
        self.results.append(("textual merge conflict", "FAIL", actual, ok))
        if not ok:
            raise RuntimeError("textual conflict was not detected")
        git("merge", "--abort")
        self.reset()

    def hidden_conflict(self):
        main_branch = self.branch("hidden-main")
        spec = Path("assets/characters/quality_gate_hidden_character/spec/quality_gate_hidden_character.spec.json")
        spec.parent.mkdir(parents=True)
        spec.write_text(json.dumps({
            "schema": "plush-studio.character-spec/1",
            "identity": {"id": "quality_gate_hidden_character", "display_name": "Quality Gate Hidden Character"},
        }, indent=1) + "\n", encoding="utf-8")
        self.commit([str(spec)], "T-023 simulation: main adds a character")
        self.reset()
        self.branch("hidden-task")
        probe = Path("engine/t023_hidden_conflict_probe.cpp")
        probe.write_text('static const char* probe = "quality_gate_hidden_character";\n', encoding="utf-8")
        self.commit([str(probe)], "T-023 simulation: task uses a future identifier")
        self.gate("hidden conflict branch alone", self.start_commit, "PASS")
        git("merge", "--no-commit", main_branch)
        self.gate("hidden conflict after merge", main_branch, "FAIL")
        git("merge", "--abort")
        self.reset()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", default="", help="Blender executable used only when changed paths require it")
    args = parser.parse_args()
    if git("status", "--porcelain", capture=True).stdout.strip():
        raise SystemExit("working tree must be clean")
    if not git("branch", "--show-current", capture=True).stdout.strip():
        raise SystemExit("run from a named branch, not detached HEAD")

    simulations = Simulations(args.blender)
    try:
        simulations.gate("baseline", simulations.start_commit, "PASS")
        simulations.frozen()
        simulations.shared_name()
        simulations.threshold()
        simulations.broken_cpp()
        simulations.textual_conflict()
        simulations.hidden_conflict()
    finally:
        simulations.delete_created()

    print("\nSimulation results")
    for label, expected, actual, ok in simulations.results:
        print(f"{'PASS' if ok else 'FAIL'} {label}: expected {expected}, got {actual}")
    return 0 if all(item[3] for item in simulations.results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
