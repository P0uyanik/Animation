#!/usr/bin/env python3
"""Run the quality-gate acceptance simulations (T-023, extended by T-041) on temporary local branches.

Nothing is pushed. Every branch created by this script has a unique
``t023-sim-<pid>-`` prefix and only those branches are deleted afterwards.
Run this from a clean, committed branch.

Each simulation asserts the check it targets (from check_all.json), so a full-tier change that also needs the
Blender tier does not hide or fake the result. T-041 simulations:
  claim overlap             tools/integrate.py claims --check on a claims table with an overlapping row -> FAIL
  write-set violation       a file outside the task's claim -> gate check "Write-set" FAIL (inside -> PASS)
  unknown path              a path no rule in tools/regression_paths.txt knows -> tier "full" (docs only -> "fast")
  changed fingerprint       shared code changes the boy's geometry without a spec change -> unchanged-character
                            guard FAIL (tools/regression/run.py; needs --blender and the approved baselines)

    python tools/simulate_quality_gate.py [--blender <blender>] [--only name,name] [--task T-NNN]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
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
    def __init__(self, blender, task):
        self.start_branch = git("branch", "--show-current", capture=True).stdout.strip()
        self.start_commit = git("rev-parse", "HEAD", capture=True).stdout.strip()
        self.prefix = f"t023-sim-{os.getpid()}-"
        self.created = []
        self.results = []
        self.blender = str(Path(blender).resolve()) if blender else ""
        self.task = task
        self.env = dict(os.environ)
        # Gate runs do not get Blender: every simulation asserts its own check, and a full-tier change then reports
        # "Blender executable not found" in the Blender tier instead of running a 20-minute regression per case.
        self.env.pop("BLENDER", None)

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

    def gate(self, label, base, expected, check=None, extra=()):
        """Run the gate; compare the overall verdict, or only the named check when `check` is given."""
        slug = label.lower().replace(" ", "-")
        command = [
            sys.executable, "tools/check_all.py", "--base", base,
            "--build-dir", "build/t023-sim/cpp", "--artifacts-dir", f"build/t023-sim/{slug}", *extra,
        ]
        proc = run(command, check=False, env=self.env)
        report = json.loads((ROOT / "build" / "t023-sim" / slug / "check_all.json").read_text(encoding="utf-8"))
        if check:
            found = [c for c in report["checks"] if c["name"] == check]
            actual = "PASS" if found and found[0]["ok"] else "FAIL"
            label = f"{label} [{check}]"
        else:
            actual = "PASS" if proc.returncode == 0 else "FAIL"
        self.record(label, expected, actual)
        return report

    def record(self, label, expected, actual):
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
        self.gate("frozen file", self.start_commit, "FAIL", "Frozen assets")
        self.reset()

    def shared_name(self):
        self.branch("shared-name")
        path = Path("engine/t023_shared_name_probe.cpp")
        path.write_text('static const char* probe = "boy_yellow_hoodie";\n', encoding="utf-8")
        self.commit([str(path)], "T-023 simulation: character name in shared code")
        self.gate("shared character name", self.start_commit, "FAIL", "Shared-systems lint")
        self.reset()

    def threshold(self):
        self.branch("threshold")
        path = Path("docs/references/VISUAL_TARGET.md")
        path.write_text(path.read_text(encoding="utf-8") + "\n<!-- T-023 threshold simulation -->\n", encoding="utf-8")
        self.commit([str(path)], "T-023 simulation: change guarded threshold")
        self.gate("threshold unapproved", self.start_commit, "FAIL", "Guarded paths")
        git("commit", "--allow-empty", "-m", "T-023 simulation: supervisor approval", "-m",
            "Supervisor-Approved: docs/references/VISUAL_TARGET.md")
        self.gate("threshold approved", self.start_commit, "PASS", "Guarded paths")
        self.reset()

    def broken_cpp(self):
        self.branch("broken-cpp")
        path = Path("tests/test_engine.cpp")
        addition = '\nTEST_CASE("T-023 simulated C++ failure") { CHECK(false); }\n'
        path.write_text(path.read_text(encoding="utf-8") + addition, encoding="utf-8")
        self.commit([str(path)], "T-023 simulation: broken C++ test", [str(path).replace("\\", "/")])
        self.gate("broken C++ test", self.start_commit, "FAIL", "C++ tests")
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
        self.gate("hidden conflict branch alone", self.start_commit, "PASS", "Shared-systems lint")
        git("merge", "--no-commit", main_branch)
        self.gate("hidden conflict after merge", main_branch, "FAIL", "Shared-systems lint")
        git("merge", "--abort")
        self.reset()

    # ----------------------------------------------------------------- T-041

    def claim_overlap(self):
        self.branch("claim-overlap")
        ownership = Path("docs/process/OWNERSHIP.md")
        text = ownership.read_text(encoding="utf-8")
        rows = ("| T-990 | B | `t-990-sim-a` | `pipeline/charsys/{spec,hair}.py` | — | — |\n"
                "| T-991 | D | `t-991-sim-b` | `content/sim_only/**` | — | — |\n")
        ownership.write_text(_insert_rows(text, rows), encoding="utf-8")
        self.commit([str(ownership)], "T-041 simulation: claims with an overlapping task")
        for task, expected in (("T-990", "FAIL"), ("T-991", "PASS")):
            proc = run([sys.executable, "tools/integrate.py", "claims", "--check", task], check=False, capture=True)
            print(proc.stdout)
            self.record(f"claim {'overlap' if expected == 'FAIL' else 'disjoint'} {task}", expected,
                        "PASS" if proc.returncode == 0 else "FAIL")
        self.reset()

    def write_set(self):
        self.branch("write-set")
        inside = Path("docs/evaluation/process") / self.task / "simulation_probe.md"
        inside.parent.mkdir(parents=True, exist_ok=True)
        inside.write_text("T-041 simulation: inside the claim\n", encoding="utf-8")
        self.commit([str(inside)], "T-041 simulation: file inside the write-set")
        self.gate("write-set inside", self.start_commit, "PASS", "Write-set", ["--task", self.task])
        outside = Path("docs/write_set_simulation_probe.md")
        outside.write_text("T-041 simulation: outside the claim\n", encoding="utf-8")
        self.commit([str(outside)], "T-041 simulation: file outside the write-set")
        self.gate("write-set violation", self.start_commit, "FAIL", "Write-set", ["--task", self.task])
        self.reset()

    def unknown_path(self):
        self.branch("unknown-path")
        known = Path("docs/tier_simulation_probe.md")
        known.write_text("T-041 simulation: docs only\n", encoding="utf-8")
        self.commit([str(known)], "T-041 simulation: docs-only change")
        report = self.gate("docs-only change", self.start_commit, "PASS", "Blender tier")
        self.record("docs-only change is fast tier", "fast", report.get("tier"))
        unknown = Path("sim_unknown_folder/probe.dat")
        unknown.parent.mkdir(parents=True, exist_ok=True)
        unknown.write_text("T-041 simulation: unknown path\n", encoding="utf-8")
        self.commit([str(unknown)], "T-041 simulation: unknown path")
        report = self.gate("unknown path", self.start_commit, "FAIL", "Blender tier")
        self.record("unknown path is full tier", "full", report.get("tier"))
        self.record("unknown path listed", "sim_unknown_folder/probe.dat",
                    ",".join(report.get("tier_unknown_paths", [])))
        shutil.rmtree(unknown.parent, ignore_errors=True)
        self.reset()

    def changed_fingerprint(self):
        if not self.blender:
            self.record("changed unchanged-character fingerprint (needs --blender)", "FAIL", "NOT RUN")
            return
        self.branch("changed-fingerprint")
        path = Path("pipeline/charsys/build_character.py")
        text = path.read_text(encoding="utf-8")
        # Before every save of the master (legacy and generic build paths), shift one mesh by 1 mm.
        pattern = re.compile(r'^(\s*)(bpy\.ops\.wm\.save_as_mainfile\(filepath=(master|os\.path\.join\(out, f"\{cid\}_master\.blend"\)).*)$',
                             re.M)
        probe = ('{0}_sim = sorted((o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("WGT")), key=lambda o: o.name)[0]\n'
                 '{0}_sim.data.transform(__import__("mathutils").Matrix.Translation((0.001, 0.0, 0.0)))'
                 '  # T-041 simulation: 1 mm shared-code geometry change\n')
        patched, count = pattern.subn(lambda m: probe.format(m.group(1)) + m.group(0), text)
        if count < 1:
            raise RuntimeError("build_character.py master save not found")
        path.write_text(patched, encoding="utf-8")
        self.commit([str(path)], "T-041 simulation: shared code shifts one boy mesh by 1 mm (no spec change)")
        out = ROOT / "build" / "t023-sim" / "changed-fingerprint"
        shutil.rmtree(out, ignore_errors=True)
        proc = run([sys.executable, "tools/regression/run.py", "--blender", self.blender, "--character",
                    "boy_yellow_hoodie", "--no-fidelity", "--base", self.start_commit, "--against", self.start_commit,
                    "--out", str(out)],
                   check=False, capture=True)
        print(proc.stdout)
        result = json.loads((out / "boy_yellow_hoodie" / "result.json").read_text(encoding="utf-8"))
        fingerprint = [c for c in result["checks"] if c["name"].startswith("fingerprint vs ")
                       and not c["name"].endswith("baseline")]
        self.record("unchanged character treated as unchanged", True, result.get("unchanged"))
        self.record("changed unchanged-character fingerprint", "FAIL",
                    "PASS" if fingerprint and fingerprint[0]["ok"] else "FAIL")
        self.record("regression run verdict", "FAIL", "PASS" if proc.returncode == 0 else "FAIL")
        self.reset()


def _insert_rows(text, rows):
    lines = text.split("\n")
    last = max(i for i, line in enumerate(lines) if line.startswith("| T-"))
    return "\n".join(lines[:last + 1] + rows.rstrip("\n").split("\n") + lines[last + 1:])


SIMULATIONS = ("frozen", "shared_name", "threshold", "broken_cpp", "textual_conflict", "hidden_conflict",
               "claim_overlap", "write_set", "unknown_path", "changed_fingerprint")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", default="", help="Blender for the changed-fingerprint simulation")
    parser.add_argument("--only", default="", help="comma-separated subset of: " + ", ".join(SIMULATIONS))
    parser.add_argument("--task", default="", help="task whose claim the write-set simulation uses (default: branch)")
    args = parser.parse_args()
    if git("status", "--porcelain", capture=True).stdout.strip():
        raise SystemExit("working tree must be clean")
    if not git("branch", "--show-current", capture=True).stdout.strip():
        raise SystemExit("run from a named branch, not detached HEAD")

    sys.path.insert(0, str(ROOT / "tools"))
    import integrate
    branch = git("branch", "--show-current", capture=True).stdout.strip()
    task = args.task or getattr(integrate.claim_for_branch(branch), "task", "") or "T-041"
    simulations = Simulations(args.blender, task)
    chosen = [name for name in (args.only.split(",") if args.only else SIMULATIONS) if name]
    unknown = sorted(set(chosen) - set(SIMULATIONS))
    if unknown:
        raise SystemExit(f"unknown simulations: {', '.join(unknown)}")
    try:
        if not args.only:
            simulations.gate("baseline", simulations.start_commit, "PASS")
        for name in chosen:
            getattr(simulations, name)()
    finally:
        simulations.delete_created()

    print("\nSimulation results")
    for label, expected, actual, ok in simulations.results:
        print(f"{'PASS' if ok else 'FAIL'} {label}: expected {expected}, got {actual}")
    return 0 if all(item[3] for item in simulations.results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
