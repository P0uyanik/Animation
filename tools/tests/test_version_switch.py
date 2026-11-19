#!/usr/bin/env python3
"""T-088 tests for tools/version_switch.py. Plain Python, no Blender: every case runs on a small fixture repository
in a temporary folder (two test characters, their stores, a fidelity baseline, golden baselines, a task claim and a
decision file) with a fake runner standing in for build_character.py, tools/fidelity/run.py and
tools/regression/run.py. The real repository is only read (and checked to be unchanged afterwards).

    python3 tools/tests/test_version_switch.py

1. --dry-run of a valid switch: exit 0, every step, command, file and the predicted trailer block are printed, and
   the fixture is byte-identical afterwards (no work folder either).
2. A full switch: publish, approve pointer with the decision note, baseline entry with the rebaseline note (other
   entry untouched), golden baseline copied, checks run in order after the writes, exact trailer block, other
   character and older versions byte-identical, the store verifies.
3. The inconsistencies found on 2026-11-18, each refused before anything is written: version spec name the
   regression gate refuses; presets/2 skin id without the presets/2 pin; missing golden baseline target clash
   (golden already there) and spec_version that would put it in the wrong folder; claim that does not cover the
   writes; owner decision missing or not recorded. Also: published / reused version, identity change without
   approval, unresolvable pin, another character's files, wrong identity, work folder inside a store.
4. Failures during the run: a failing tool stops the switch; a check that changes another character's files is
   reported; a second run of the same version is refused.
5. T-094: presets/3 ids (T-092 library) resolve to presets/3: accepted with the presets/3 pin (also mixed with a
   presets/2 skin id), refused with the presets/2 or default pin.
6. T-094 --publish-only: dry run writes nothing and marks approve/baseline/golden as skipped; a run publishes the
   version (status candidate) and copies the score to <task>/fidelity/<id>/, but the approved pointer, the whole
   fidelity_baseline.json and the golden root are byte-identical, the regression tool is never called, and only the
   version folder, the store index and the score evidence are written (exact trailer block); a second character of
   the same task publishes next to the first; a check that edits the baseline file is reported."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "pipeline" / "charsys"))
import version_switch as VS  # noqa: E402
import asset_store as AS  # noqa: E402
import spec as S  # noqa: E402

RESULTS: list[bool] = []
A, B = "tc_alpha", "tc_beta"
TASK = "T-900"
DECISION_REF = "docs/process/OWNER_DECISIONS.md 2099-01-01"


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"[test_version_switch] {'PASS' if ok else 'FAIL'} {name}" + (f" -- {detail}" if detail and not ok else ""))


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, indent=2) + "\n", encoding="utf-8")


def make_spec(cid, version, preset="felt", **extra):
    spec = {"schema": S.SCHEMA, "identity": {"id": cid, "display_name": cid}, "proportions": {"height_m": 0.5},
            "body": {}, "face": {"eyes": "brown"}, "hair": {}, "clothing": {}, "accessories": {}, "rig": {},
            "materials": {"assignments": {"skin": {"preset": preset, "base_color_srgb": [200, 180, 170]}}},
            "fur": {}, "animation": {}, "metadata": {"spec_version": version}}
    spec.update(extra)
    return spec


def fake_build(out: Path, spec: dict) -> None:
    cid = spec["identity"]["id"]
    out.mkdir(parents=True, exist_ok=True)
    write(out / "spec.resolved.json", spec)
    write(out / "build_report.json", {"character_id": cid, "spec_sha256": S.sha256(spec), "build": "fixture",
                                      "blender": "none",
                                      "rig": {"rigify_bones": 1, "deform_bones": 1, "unweighted_after_cleanup": 0}})
    for name in (f"{cid}_master.blend", f"{cid}.glb", "components.json", "animation_compat.json"):
        write(out / name, f"{name} of {cid} {spec['metadata']['spec_version']}\n")


GOLDEN_FILES = VS.golden_files()


def fixture(tmp: Path) -> Path:
    root = tmp / "repo"
    for cid in (A, B):
        write(root / f"assets/characters/{cid}/spec/{cid}.spec.json", make_spec(cid, "1.0.0"))
        build = tmp / f"build-{cid}"
        fake_build(build, make_spec(cid, "1.0.0"))
        store = root / f"assets/characters/{cid}/versions"
        with contextlib.redirect_stdout(io.StringIO()):
            AS.main(["publish", "--character", cid, "--store", str(store), "--build", str(build), "--version", "1.0.0",
                     "--notes", "fixture", "--without-glb"])
            AS.main(["approve", "--character", cid, "--store", str(store), "--version", "1.0.0", "--by", "owner"])
        for f in GOLDEN_FILES:
            write(root / f"docs/evaluation/regression/baselines/{cid}/1.0.0/{f}", f"{f}\n")
    write(root / f"assets/characters/{A}/spec/{A}.1.1.0.spec.json", make_spec(A, "1.1.0"))
    write(root / VS.FIDELITY_BASELINE, {
        "schema": "plush-studio.fidelity-baseline/1", "policy": {"maximum_score_drop": 2.0},
        "render": {"height": 64, "samples": 2},
        "characters": {cid: {"score": 60.0 + i, "build": f"assets/characters/{cid}/spec/{cid}.spec.json",
                             "overrides": [], "source": f"docs/evaluation/characters/T-001/{cid}.json"}
                       for i, cid in enumerate((A, B))}})
    write(root / "docs/process/OWNER_DECISIONS.md", "# Owner decisions\n\n## 2099-01-01\nAlpha 1.1.0 is current.\n")
    write(root / f"docs/tasks/{TASK}.md", f"# {TASK}\n\n## Write-set\n"
          f"`assets/characters/{A}/versions/**`, `{VS.FIDELITY_BASELINE}`, "
          f"`docs/evaluation/regression/baselines/{A}/**`, `docs/evaluation/characters/{TASK}/**`\n")
    for t in VS.AFFECTED_TESTS:  # stand-ins: the fake runner "runs" them
        write(root / t, "# fixture stand-in\n")
    write(root / "pipeline/charsys/tests/test_alpha_only.py", f"# names {A}\n")
    write(root / "pipeline/charsys/tests/test_alpha_render.py", f"import bpy\n# names {A}\n")
    write(root / "pipeline/charsys/tests/test_beta_only.py", f"# names {B}\n")
    write(root / "pipeline/charsys/tests/test_alpha_build.py", f"# names {A}; usage: --blender <exe>\n")
    return root


def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        h.update(p.relative_to(root).as_posix().encode() + b"\0")
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


class FakeRunner(VS.Runner):
    def __init__(self, fail=(), side_effect=None):
        self.calls: list[str] = []
        self.fail, self.side_effect = set(fail), side_effect

    def build_env(self):
        return {}

    def run(self, command, log, cwd, env=None):
        command = [str(c) for c in command]
        script = next((c for c in command if c.endswith(".py")), "")
        name = Path(script).name
        self.calls.append(name)
        if name in self.fail:
            return 1

        def opt(flag, many=False):
            vals = [command[i + 1] for i, c in enumerate(command[:-1]) if c == flag]
            return vals if many else (vals[0] if vals else None)
        if name == "build_character.py":
            spec, _ = S.load(opt("--spec"), opt("--override", many=True))
            fake_build(Path(opt("--out")), spec)
        elif name == "run.py" and "fidelity" in script:
            write(Path(opt("--out")) / "fidelity.json", {"overall": {"score": 61.23456}})
            write(Path(opt("--out")) / "report.md", "# fidelity\n")
        elif name == "run.py" and "regression" in script:
            cid = opt("--character")
            spec_path = Path(self.root) / f"assets/characters/{cid}/spec/{cid}.1.1.0.spec.json"
            ver = json.loads(spec_path.read_text())["metadata"]["spec_version"]
            dest = Path(opt("--out")) / "baselines" / cid / ver
            for f in GOLDEN_FILES:
                write(dest / f, json.dumps({"spec_version": ver}) if f == "golden.json" else f"new {f}\n")
        elif self.side_effect and name == self.side_effect[0]:
            self.side_effect[1]()
        return 0


def argv(root: Path, work: Path | None = None, **over):
    args = {"--character": A, "--version": "1.1.0", "--spec": f"assets/characters/{A}/spec/{A}.1.1.0.spec.json",
            "--task": TASK, "--decision": "I approve Alpha 1.1.0 as the new current version.",
            "--decision-ref": DECISION_REF, "--blender": "fake-blender", "--root": str(root)}
    if work is not None:
        args["--work"] = str(work)
    args.update(over)
    out = []
    for k, v in args.items():
        if v is None:
            continue
        if isinstance(v, list):
            out += [k, *v]
        else:
            out += [k, v]
    return out


def run_main(args, runner=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = VS.main(args, runner)
    return code, out.getvalue() + err.getvalue()


def expected_trailers(root: Path) -> list[str]:
    vdir = f"assets/characters/{A}/versions/1.1.0"
    files = [f"{vdir}/{n}" for n in (f"{A}_master.blend", "animation_compat.json", "build_report.json",
                                      "components.json", "manifest.json", "spec.json")]
    files += [f"assets/characters/{A}/versions/index.json", VS.FIDELITY_BASELINE]
    files += [f"docs/evaluation/regression/baselines/{A}/1.1.0/{f}" for f in GOLDEN_FILES]
    return [f"Supervisor-Approved: {p}" for p in sorted(files)]


def test_dry_run(tmp: Path):
    root = fixture(tmp)
    before = tree_hash(root)
    work = tmp / "work"
    code, out = run_main(argv(root, work, **{"--dry-run": []}))
    check("dry run: valid switch exits 0", code == 0, out)
    for marker in ("1. validate  OK", "2. build", "publish", "3. approve", "4. baseline", "5. golden", "6. checks",
                   "7. files", "trailers"):
        check(f"dry run shows {marker.strip()}", marker in out)
    check("dry run lists the predicted trailers", all(t in out for t in expected_trailers(root)))
    check("dry run lists the Blender test as not run", "test_alpha_render.py" in out.split("need Blender")[-1])
    check("dry run writes nothing (fixture byte-identical, no work folder)", tree_hash(root) == before
          and not work.exists())


def test_full_switch(tmp: Path):
    root = fixture(tmp)
    beta_before = tree_hash(root / f"assets/characters/{B}")
    old_before = tree_hash(root / f"assets/characters/{A}/versions/1.0.0")
    golden_before = tree_hash(root / f"docs/evaluation/regression/baselines/{A}/1.0.0")
    baseline_before = json.loads((root / VS.FIDELITY_BASELINE).read_text())
    runner = FakeRunner()
    runner.root = root
    code, out = run_main(argv(root, tmp / "work"), runner)
    check("full switch exits 0", code == 0, out)
    idx = json.loads((root / f"assets/characters/{A}/versions/index.json").read_text())
    check("published 1.1.0 (manifest, no .glb)", (root / f"assets/characters/{A}/versions/1.1.0/manifest.json").is_file()
          and not (root / f"assets/characters/{A}/versions/1.1.0/{A}.glb").exists())
    check("approved pointer moved with the decision note", idx["pointers"]["approved"] == "1.1.0"
          and idx["history"][-1]["action"] == "approve" and idx["history"][-1]["by"] == f"owner ({DECISION_REF})"
          and "I approve Alpha 1.1.0" in idx["history"][-1]["notes"], idx["history"][-1])
    base = json.loads((root / VS.FIDELITY_BASELINE).read_text())
    entry = base["characters"][A]
    check("baseline entry: build, score, source", entry["build"] == f"assets/characters/{A}/spec/{A}.1.1.0.spec.json"
          and entry["score"] == 61.2346 and entry["overrides"] == []
          and entry["source"] == f"docs/evaluation/characters/{TASK}/fidelity/fidelity.json", entry)
    check("baseline entry: rebaseline note", entry["rebaseline"] == {
        "task": TASK, "reason": f"owner decision ({DECISION_REF}): I approve Alpha 1.1.0 as the new current version.",
        "previous_version": "1.0.0", "previous_score": 60.0,
        "previous_source": f"docs/evaluation/characters/T-001/{A}.json"}, entry.get("rebaseline"))
    check("baseline: other entry and settings untouched", base["characters"][B] == baseline_before["characters"][B]
          and {k: v for k, v in base.items() if k != "characters"} ==
          {k: v for k, v in baseline_before.items() if k != "characters"})
    check("fidelity evidence copied", (root / f"docs/evaluation/characters/{TASK}/fidelity/fidelity.json").is_file())
    gdir = root / f"docs/evaluation/regression/baselines/{A}/1.1.0"
    check("golden baseline written", all((gdir / f).is_file() for f in GOLDEN_FILES))
    order = [c for c in runner.calls]
    check("tools run in order: build, fidelity, regression, then checks",
          order[:3] == ["build_character.py", "run.py", "run.py"] and "check_cast.py" in order[3:], order)
    check("checks: affected tests + tests naming the character; Blender test listed only",
          "test_alpha_only.py" in order and "test_beta_only.py" not in order and "test_alpha_render.py" not in order
          and "test_alpha_build.py" not in order and "test_alpha_render.py" in out and "test_alpha_build.py" in out,
          order)
    trailers = [line for line in out.splitlines() if line.startswith("Supervisor-Approved:")]
    check("exact trailer block for every guarded path written", trailers == expected_trailers(root),
          "\n".join(trailers))
    check("other character byte-identical", tree_hash(root / f"assets/characters/{B}") == beta_before)
    check("older version and golden byte-identical", tree_hash(root / f"assets/characters/{A}/versions/1.0.0") ==
          old_before and tree_hash(root / f"docs/evaluation/regression/baselines/{A}/1.0.0") == golden_before)
    check("store verifies", AS.verify_version(str(root / f"assets/characters/{A}/versions"), "1.1.0",
                                              require_readonly=False)["ok"])
    report = json.loads((tmp / "work" / "version_switch.json").read_text())
    check("run report written to the work folder", report["ok"] and report["trailers"] == expected_trailers(root))
    # a second run of the same version is refused before anything is written
    before = tree_hash(root)
    code, out = run_main(argv(root, tmp / "work2"), FakeRunner())
    check("second run of the same version refused", code == 1 and "already published" in out
          and "already exists" in out and tree_hash(root) == before, out)


def refused(tmp: Path, name: str, expect: str, prepare=None, **over):
    root = fixture(tmp / name)
    if prepare:
        prepare(root)
    before = tree_hash(root)
    runner = FakeRunner()
    runner.root = root
    code, out = run_main(argv(root, tmp / name / "work", **over), runner)
    check(f"refused: {name}", code == 1 and expect in out and not runner.calls and tree_hash(root) == before
          and not (tmp / name / "work").exists(), out)
    return root


def set_spec(root: Path, spec: dict, name: str | None = None):
    write(root / f"assets/characters/{A}/spec/{name or f'{A}.1.1.0.spec.json'}", spec)


def test_inconsistencies(tmp: Path):
    # 2026-11-18 #1: a version spec name the regression gate (tiers.py) refuses
    refused(tmp, "spec name the gate refuses", "regression gate would refuse",
            lambda r: set_spec(r, make_spec(A, "1.1.0"), f"{A}.v1.1.0.spec.json"),
            **{"--spec": f"assets/characters/{A}/spec/{A}.v1.1.0.spec.json"})
    # 2026-11-18 #2: presets/2 skin id without the presets/2 pin
    refused(tmp, "skin-felt/2 without presets/2 pin", "presets pin inconsistent",
            lambda r: set_spec(r, make_spec(A, "1.1.0", preset="skin-felt/2")))
    refused(tmp, "skin-felt/2 with presets/1 pin", "materials pin is presets/1",
            lambda r: set_spec(r, make_spec(A, "1.1.0", preset="skin-felt/2", generators={"materials": "presets/1"})))
    root = fixture(tmp / "pinned")
    set_spec(root, make_spec(A, "1.1.0", preset="skin-felt/2", generators={"materials": "presets/2"}))
    code, out = run_main(argv(root, tmp / "pinned" / "work", **{"--dry-run": [],  # materials is an identity section
                                                                "--identity-change-approved-by": "owner, 2099-01-01"}))
    check("accepted: skin-felt/2 with the presets/2 pin", code == 0, out)
    # 2026-11-18 #3: golden baseline: the target must be free and named by the spec_version
    refused(tmp, "golden baseline already there", "golden baseline is never overwritten",
            lambda r: write(r / f"docs/evaluation/regression/baselines/{A}/1.1.0/golden.json", "{}"))
    refused(tmp, "spec_version differs from --version", "metadata.spec_version is '1.2.0'",
            lambda r: set_spec(r, make_spec(A, "1.2.0")))
    refused(tmp, "override changes spec_version", "regression gate reads spec_version '1.3.0'",
                   lambda r: write(r / f"assets/characters/{A}/spec/{A}.ov.override.json",
                                   {"override": {"metadata": {"spec_version": "1.3.0"}}}),
                   **{"--overrides": [f"assets/characters/{A}/spec/{A}.ov.override.json"]})
    # 2026-11-18 #4: claim and approval timing
    refused(tmp, "claim does not cover the writes", f"the {TASK} claim does not cover: {VS.FIDELITY_BASELINE}",
            lambda r: write(r / f"docs/tasks/{TASK}.md", f"## Write-set\n`assets/characters/{A}/versions/**`, "
                            f"`docs/evaluation/regression/baselines/{A}/**`, `docs/evaluation/characters/{TASK}/**`\n"))
    refused(tmp, "no claim", "no claim for T-901", **{"--task": "T-901"})
    refused(tmp, "decision missing", "--decision is required", **{"--decision": ""})
    refused(tmp, "decision not recorded", "does not mention 1.1.0",
            lambda r: write(r / "docs/process/OWNER_DECISIONS.md", "# Owner decisions\n"))
    # immutability and identity
    refused(tmp, "version already published", "already published", **{"--version": "1.0.0"})
    refused(tmp, "identity change without approval", "identity sections changed vs 1.0.0: ['face']",
            lambda r: set_spec(r, make_spec(A, "1.1.0", face={"eyes": "green"})))
    root = fixture(tmp / "identity-ok")
    set_spec(root, make_spec(A, "1.1.0", face={"eyes": "green"}))
    code, out = run_main(argv(root, None, **{"--dry-run": [], "--identity-change-approved-by": "owner, 2099-01-01"}))
    check("accepted: identity change with the owner's approval", code == 0, out)
    refused(tmp, "unresolvable generator pin", "spec does not load",
            lambda r: set_spec(r, make_spec(A, "1.1.0", generators={"body": "body_generic/99"})))
    refused(tmp, "another character's spec", "build inputs must be in",
            **{"--spec": f"assets/characters/{B}/spec/{B}.spec.json"})
    refused(tmp, "wrong identity", "spec identity.id is 'tc_other'",
            lambda r: set_spec(r, make_spec("tc_other", "1.1.0")))
    root = fixture(tmp / "work-in-store")
    before = tree_hash(root)
    code, out = run_main(argv(root, root / f"assets/characters/{B}/versions/scratch"), FakeRunner())
    check("refused: work folder inside a store", code == 1 and "lies inside an asset store" in out
          and tree_hash(root) == before, out)
    code, out = run_main(argv(root, None, **{"--blender": ""}), FakeRunner())
    check("refused: no --blender outside --dry-run", code == 1 and "--blender is required" in out)


def test_failures(tmp: Path):
    root = fixture(tmp / "regfail")
    runner = FakeRunner(fail={"run.py"})
    runner.root = root
    code, out = run_main(argv(root, tmp / "regfail" / "work"), runner)
    check("a failing tool stops the switch and lists what was written", code == 1 and "FAILED" in out
          and f"assets/characters/{A}/versions/index.json" in out and runner.calls == ["build_character.py", "run.py"],
          out)
    root = fixture(tmp / "touch")
    runner = FakeRunner(side_effect=("test_alpha_only.py", lambda: write(
        root / f"assets/characters/{B}/versions/index.json", "{}")))
    runner.root = root
    code, out = run_main(argv(root, tmp / "touch" / "work"), runner)
    check("a change to another character is reported as a failure", code == 1
          and f"files outside this switch changed: assets/characters/{B}/versions/index.json" in out, out)
    check("trailers are still printed after a failed check", "Supervisor-Approved:" in out)


def test_presets3(tmp: Path):
    check("preset_family: presets/1, presets/2 skin, presets/3",
          VS.preset_family("felt") == ("presets", 1) and VS.preset_family("skin-felt/2") == ("presets", 2)
          and VS.preset_family("hoodie fleece/3") == ("presets", 3) and VS.preset_family("skin-felt/3") == ("presets", 3)
          and VS.preset_family("no such preset") is None)
    ok = {"--dry-run": [], "--identity-change-approved-by": "owner, 2099-01-01"}  # materials is an identity section
    for name, assignments, pin in [
            ("presets/3 spec with the presets/3 pin", {"skin": {"preset": "skin-felt/3"}}, "presets/3"),
            ("presets/3 + presets/2 + presets/1 ids with the presets/3 pin",
             {"skin": {"preset": "skin-felt/2"}, "hoodie": {"preset": "hoodie fleece/3"}, "felt": {"preset": "felt"}},
             "presets/3")]:
        root = fixture(tmp / name.replace("/", "_"))
        spec = make_spec(A, "1.1.0", generators={"materials": pin})
        spec["materials"]["assignments"] = {k: dict(v, base_color_srgb=[200, 180, 170]) for k, v in assignments.items()}
        set_spec(root, spec)
        code, out = run_main(argv(root, None, **ok))
        check(f"accepted: {name}", code == 0 and "1. validate  OK" in out, out)
    refused(tmp, "presets/3 id with the presets/2 pin", "belong(s) to presets/3, but the materials pin is presets/2",
            lambda r: set_spec(r, make_spec(A, "1.1.0", preset="hoodie fleece/3",
                                            generators={"materials": "presets/2"})))
    refused(tmp, "presets/3 id with the default pin", "belong(s) to presets/3",
            lambda r: set_spec(r, make_spec(A, "1.1.0", preset="skin-felt/3")))


def test_publish_only(tmp: Path):
    po = {"--publish-only": []}
    root = fixture(tmp / "dry")
    before = tree_hash(root)
    code, out = run_main(argv(root, tmp / "dry" / "work", **po, **{"--dry-run": []}))
    check("publish-only dry run exits 0", code == 0, out)
    check("publish-only dry run: approve, baseline and golden skipped", "3. approve   skipped" in out
          and "5. golden    skipped" in out and f"{VS.FIDELITY_BASELINE} not changed" in out
          and "--write-baseline" not in out and f"     {VS.FIDELITY_BASELINE}\n" not in out + "\n", out)
    check("publish-only dry run writes nothing", tree_hash(root) == before and not (tmp / "dry" / "work").exists())

    root = fixture(tmp / "run")
    store = root / f"assets/characters/{A}/versions"
    idx_before = json.loads((store / "index.json").read_text())
    baseline_before = (root / VS.FIDELITY_BASELINE).read_bytes()
    golden_before = tree_hash(root / "docs/evaluation/regression/baselines")
    beta_before = tree_hash(root / f"assets/characters/{B}")
    old_before = tree_hash(store / "1.0.0")
    runner = FakeRunner()
    runner.root = root
    code, out = run_main(argv(root, tmp / "run" / "work", **po), runner)
    check("publish-only run exits 0", code == 0, out)
    idx = json.loads((store / "index.json").read_text())
    check("publish-only: version published as candidate", (store / "1.1.0" / "manifest.json").is_file()
          and idx["versions"]["1.1.0"]["status"] == "candidate" and idx["versions"]["1.1.0"]["parent"] == "1.0.0",
          idx["versions"].get("1.1.0"))
    check("publish-only: pointers unchanged, no approve entry", idx["pointers"] == idx_before["pointers"]
          and not any(h["action"] == "approve" and h["version"] == "1.1.0" for h in idx["history"]), idx["pointers"])
    check("publish-only: fidelity_baseline.json byte-identical",
          (root / VS.FIDELITY_BASELINE).read_bytes() == baseline_before)
    check("publish-only: no golden baseline (golden root byte-identical)",
          tree_hash(root / "docs/evaluation/regression/baselines") == golden_before
          and not (root / f"docs/evaluation/regression/baselines/{A}/1.1.0").exists())
    ev = root / f"docs/evaluation/characters/{TASK}/fidelity/{A}"
    check("publish-only: score evidence in <task>/fidelity/<id>/",
          json.loads((ev / "fidelity.json").read_text())["overall"]["score"] == 61.23456 and (ev / "report.md").is_file())
    check("publish-only: the regression tool is never called; build, fidelity, then checks",
          runner.calls[:2] == ["build_character.py", "run.py"] and runner.calls.count("run.py") == 1
          and "check_cast.py" in runner.calls[2:], runner.calls)
    check("publish-only: score and skipped steps reported", "approve: skipped (--publish-only)" in out
          and "61.2346 (current 1.0.0: 60.0)" in out and "golden: skipped" in out, out)
    vdir = f"assets/characters/{A}/versions/1.1.0"
    expect = sorted([f"{vdir}/{n}" for n in (f"{A}_master.blend", "animation_compat.json", "build_report.json",
                                             "components.json", "manifest.json", "spec.json")]
                    + [f"assets/characters/{A}/versions/index.json"])
    trailers = [line for line in out.splitlines() if line.startswith("Supervisor-Approved:")]
    check("publish-only: exact trailer block (version folder + index only)",
          trailers == [f"Supervisor-Approved: {p}" for p in expect], "\n".join(trailers))
    report = json.loads((tmp / "run" / "work" / "version_switch.json").read_text())
    check("publish-only: written files are the version, the index and the score evidence only",
          report["ok"] and report["publish_only"] and sorted(report["written"]) == sorted(
              expect + [f"docs/evaluation/characters/{TASK}/fidelity/{A}/{n}" for n in ("fidelity.json", "report.md")]),
          report["written"])
    check("publish-only: other character and older version byte-identical",
          tree_hash(root / f"assets/characters/{B}") == beta_before and tree_hash(store / "1.0.0") == old_before)
    check("publish-only: store verifies", AS.verify_version(str(store), "1.1.0", require_readonly=False)["ok"])
    # a second character of the same task publishes next to the first (evidence per character)
    write(root / f"assets/characters/{B}/spec/{B}.2.0.0.spec.json", make_spec(B, "2.0.0"))
    write(root / f"docs/tasks/{TASK}.md", f"# {TASK}\n\n## Write-set\n`assets/characters/{A}/versions/**`, "
          f"`assets/characters/{B}/versions/**`, `docs/evaluation/characters/{TASK}/**`\n")
    write(root / "docs/process/OWNER_DECISIONS.md", "# Owner decisions\n\n## 2099-01-01\nAlpha 1.1.0, Beta 2.0.0.\n")
    code, out = run_main(argv(root, tmp / "run" / "work-b", **po, **{
        "--character": B, "--version": "2.0.0", "--spec": f"assets/characters/{B}/spec/{B}.2.0.0.spec.json"}), runner)
    check("publish-only: second character of the same task (narrow claim without baseline/golden paths)",
          code == 0 and (root / f"docs/evaluation/characters/{TASK}/fidelity/{B}/fidelity.json").is_file()
          and (root / f"docs/evaluation/characters/{TASK}/fidelity/{A}/fidelity.json").is_file()
          and (root / VS.FIDELITY_BASELINE).read_bytes() == baseline_before, out)
    # a check that edits the baseline file is reported
    root = fixture(tmp / "touch")
    runner = FakeRunner(side_effect=("test_alpha_only.py", lambda: write(root / VS.FIDELITY_BASELINE, {"x": 1})))
    runner.root = root
    code, out = run_main(argv(root, tmp / "touch" / "work", **po), runner)
    check("publish-only: a change to fidelity_baseline.json is reported", code == 1
          and f"files outside this switch changed: {VS.FIDELITY_BASELINE}" in out, out)
    root = fixture(tmp / "touch-golden")
    runner = FakeRunner(side_effect=("test_alpha_only.py", lambda: write(
        root / f"docs/evaluation/regression/baselines/{A}/1.1.0/golden.json", "{}")))
    runner.root = root
    code, out = run_main(argv(root, tmp / "touch-golden" / "work", **po), runner)
    check("publish-only: a golden written for the new version is reported", code == 1
          and f"docs/evaluation/regression/baselines/{A}/1.1.0/golden.json" in out, out)


def real_repo_hash() -> str:
    h = hashlib.sha256()
    for p in [ROOT / VS.FIDELITY_BASELINE, *sorted((ROOT / "assets" / "characters").glob("*/versions/index.json"))]:
        h.update(p.read_bytes())
    return h.hexdigest()


def main() -> int:
    real = real_repo_hash()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for test in (test_dry_run, test_full_switch, test_inconsistencies, test_failures, test_presets3,
                     test_publish_only):
            sub = tmp / test.__name__
            sub.mkdir()
            test(sub)
        # read-only stores: make them writable so the temporary folder can be removed
        for p in tmp.rglob("*"):
            with contextlib.suppress(OSError):
                os.chmod(p, 0o755 if p.is_dir() else 0o644)
    check("the real repository's baseline and store indexes are unchanged", real_repo_hash() == real)
    print(f"[test_version_switch] {sum(RESULTS)}/{len(RESULTS)} passed")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
