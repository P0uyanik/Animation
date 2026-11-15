"""T-002 pipeline tests: generated clip retarget data in engine packages and the exporter-versioned package cache.

    python3 pipeline/production/tests/test_clip_pipeline.py --blender <blender> [--out <dir>]

1. Every package of the repository shots (published boy 1.0.0, unpublished girl built from her spec) carries a
   "retarget" block equal to the data derived from its skeleton with the shared profile rules (Python, and the engine
   via plush_tests with PLUSH_TEST_PACKAGE: block vs engine derivation).
2. Cache key: a package is re-exported when the exporter's EXPORTER_VERSION changes (a wrapper exporter with another
   version, PLUSH_EXPORT_ENGINE), and reused otherwise.
Default run_shot behaviour is covered by test_run_shot_workflow.py (unchanged)."""
import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "clips"))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "production"))
import retarget as RT  # noqa: E402
import run_shot as RS  # noqa: E402

failures, results = [], {}


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}{(': ' + str(detail)) if detail else ''}")
    if not cond:
        failures.append(name)


def ang(a, b):
    return math.degrees(math.atan2(RT.length(RT.cross(a, b)), RT.dot(a, b)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    profile = json.load(open(os.path.join(ROOT, "pipeline", "charsys", "rig_profiles", "humanoid_rigify.json")))
    ref = RT.reference_pose(profile["reference_pose"])
    version = RS.exporter_version(RS.exporter_script())
    pkgs = []
    for shot in sorted(glob.glob(os.path.join(ROOT, "episodes", "*", "shots", "*", "shot.scene.json"))):
        r = subprocess.run([sys.executable, RS.__file__, "--shot", shot, "--blender", a.blender, "--stages", "prepare",
                            "--run-dir", f"t002-clip-pipeline-{os.getpid()}"], capture_output=True, text=True)
        check(f"prepare {os.path.relpath(shot, ROOT)}", r.returncode == 0, r.stderr[-400:])
        cast = json.load(open(os.path.join(os.path.dirname(shot), "build", "cast.json")))
        pkgs += [os.path.join(c["package"], "character.json") for c in cast.values()]
    pkgs = sorted(set(pkgs))
    res = {}
    for p in pkgs:
        man = json.load(open(p))
        name = os.path.relpath(p, ROOT)
        blk = man.get("retarget")
        check(f"retarget block present ({name})", blk is not None and man.get("exporter_version") == version)
        if not blk:
            continue
        der = RT.derive({s["name"]: s["head"] for s in man["skeleton"]}, ref)
        dmax = max(max(ang(blk["roles"][r]["dir"], der["roles"][r]["dir"]), ang(blk["roles"][r]["twist"], der["roles"][r]["twist"]))
                   for r in der["roles"])
        check(f"block == derived from the skeleton ({name})", set(blk["roles"]) == set(der["roles"]) and dmax < 1e-3
              and abs(blk["leg_length"] - der["leg_length"]) < 1e-6, f"{len(blk['roles'])} roles, max {dmax:.2e} deg")
        res[name] = {"roles": len(blk["roles"]), "height": blk["height"], "leg_length": blk["leg_length"],
                     "max_diff_vs_python_derivation_deg": dmax}
    # engine derivation vs block (C++)
    r = subprocess.run([os.path.join(ROOT, "build", "tests", "plush_tests"), "-tc=*retarget block*"],
                       env=dict(os.environ, PLUSH_TEST_PACKAGE=":".join(pkgs)), capture_output=True, text=True)
    msgs = [l for l in r.stdout.splitlines() if "block vs derived" in l]
    check("engine: block == engine derivation for every package (plush_tests)", r.returncode == 0 and len(msgs) == len(pkgs),
          "\n  " + "\n  ".join(m.split("MESSAGE: ")[-1] for m in msgs))
    results["packages"] = res
    results["engine_check"] = [m.split("MESSAGE: ")[-1] for m in msgs]
    # cache key: a different exporter version re-exports; the same version reuses
    tmp = tempfile.mkdtemp(prefix="plush_t002_")
    try:
        sdir = os.path.join(tmp, "episodes", "etest", "shots", "s001")
        os.makedirs(sdir)
        shutil.copy(os.path.join(ROOT, "episodes", "e900_workflow_test", "shots", "s010", "shot.scene.json"), sdir)
        shot = os.path.join(sdir, "shot.scene.json")
        wrapper = os.path.join(tmp, "export_engine_next.py")
        open(wrapper, "w").write('EXPORTER_VERSION = "test-next"\nimport runpy\nrunpy.run_path(%r, run_name="__main__")\n'
                                 % os.path.join(ROOT, "pipeline", "charsys", "export_engine.py"))
        runs = {}
        for i, env in enumerate([{}, {}, {"PLUSH_EXPORT_ENGINE": wrapper}]):
            r = subprocess.run([sys.executable, RS.__file__, "--shot", shot, "--blender", a.blender, "--stages", "prepare",
                                "--run-dir", f"r{i}"], capture_output=True, text=True, env=dict(os.environ, **env))
            check(f"prepare run {i} ok", r.returncode == 0, r.stderr[-400:])
            prep = json.load(open(os.path.join(sdir, "build", "runs", f"r{i}", "prepare.json")))
            runs[i] = {n: (c["package_state"], c["package"]) for n, c in prep["cast"].items()}
        st = [runs[i]["boy"] for i in range(3)]
        check("same exporter version: package reused", st[1][0] == "cached" and st[1][1] == st[0][1], st[:2])
        check("new exporter version: package re-exported into a new folder", st[2][0] == "built" and st[2][1] != st[0][1], st[2])
        results["cache_key"] = {"exporter_version": version, "runs": st}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    results["failures"] = failures
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        json.dump(results, open(os.path.join(a.out, "clip_pipeline_tests.json"), "w"), indent=1)
    print(f"[test_clip_pipeline] {'ALL PASS' if not failures else f'{len(failures)} FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
