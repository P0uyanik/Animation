"""Exporter tests (plain Python driver; Blender as a subprocess). Writes only into a temporary folder.

    python3 pipeline/charsys/tests/test_export_engine.py --blender <blender>

1. the engineering fixture (make_toy_fixture.py) exports through its own profile;
2. a profile whose required role cannot be resolved fails with a clear message;
3. capability reports (data availability) match the expected table for the fixture and the committed boy package."""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROF = os.path.join(ROOT, "pipeline", "charsys", "rig_profiles")
EXPECTED = {
 "toy_fixture": {"reach_ik": "available", "look_at": "available", "blink_life": "available", "expressions": "available",
                 "grasp": "missing", "walk": "available", "idle_life": "available"},
 "boy_yellow_hoodie": {"reach_ik": "available", "look_at": "available", "blink_life": "available", "expressions": "available",
                       "grasp": "available", "walk": "available", "idle_life": "available"}}
R = []


def check(name, ok, detail=None):
    R.append((name, bool(ok)))
    print(f"[test_export_engine] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    a = ap.parse_args()
    bl = lambda script, *args: subprocess.run([a.blender, "-b", "--factory-startup", "-P", script, "--", *args],  # noqa: E731
                                              cwd=ROOT, capture_output=True, text=True)
    with tempfile.TemporaryDirectory() as t:
        blend = os.path.join(t, "toy.blend")
        r = bl(os.path.join(ROOT, "pipeline/charsys/tests/fixtures/make_toy_fixture.py"), blend)
        check("fixture builds", r.returncode == 0 and os.path.exists(blend))
        exp = os.path.join(ROOT, "pipeline/charsys/export_engine.py")
        r = bl(exp, "--blend", blend, "--profile", os.path.join(PROF, "humanoid_toy_fixture.json"), "--out", os.path.join(t, "pkg"))
        check("fixture exports through its own profile", r.returncode == 0)
        man = json.load(open(os.path.join(t, "pkg", "character.json")))
        caps = {k: v["data"] for k, v in man["capabilities"].items()}
        check("fixture capability report", caps == EXPECTED["toy_fixture"], caps)
        check("fixture keeps helper and rig-specific bones", {"belly", "tail_1", "tail_2"} <= {b["name"] for b in man["skeleton"]})
        check("non-deform bones are not exported", "root_ctrl" not in {b["source_name"] for b in man["skeleton"]})
        bad = json.load(open(os.path.join(PROF, "humanoid_toy_fixture.json")))
        bad["roles"]["neck"] = "no_such_bone"
        bp = os.path.join(t, "bad_profile.json")
        json.dump(bad, open(bp, "w"))
        r = bl(exp, "--blend", blend, "--profile", bp, "--out", os.path.join(t, "pkg_bad"))
        msg = (r.stdout + r.stderr)
        check("missing required role fails clearly", r.returncode != 0 and "required roles missing" in msg and "neck" in msg)
        r = bl(exp, "--blend", blend, "--profile", os.path.join(PROF, "humanoid_rigify.json"), "--out", os.path.join(t, "pkg_wrong"))
        check("a profile that does not fit the rig is rejected", r.returncode != 0 and "required roles missing" in (r.stdout + r.stderr))
    boy = json.load(open(os.path.join(ROOT, "tests/data/imported/boy_yellow_hoodie_1.0.0/character.json")))
    caps = {k: v["data"] for k, v in boy["capabilities"].items()}
    check("boy package capability report", caps == EXPECTED["boy_yellow_hoodie"], caps)
    ok = all(x for _, x in R)
    print(f"[test_export_engine] {'ALL PASS' if ok else 'FAILURES'} ({sum(x for _, x in R)}/{len(R)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
