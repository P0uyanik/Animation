"""Eye-socket alignment of a rendered shot (T-030), both characters, every frame (plain Python driver; Blender as a
subprocess). Writes only into a temporary folder.

    python3 pipeline/charsys/tests/test_shot_eyes.py --blender <blender> [--shot <shot.scene.json>] [--max-mm 0.5]

Runs the shot's prepare and bake stages (run_shot.py, into a temporary run folder) and pipeline/charsys/shot_render.py
--blend-only over all frames. shot_render measures, as Blender evaluates the applied bake, the distance between each
eye's centre (sphere fit of the evaluated eyeball) and its socket (the rest eye centre carried by the head bone) and
reports the largest per character ("eye_socket_max_mm"). Every character must have eye objects and stay under
--max-mm (default 0.5 mm). Before T-030 the eyes of e905 were 61 mm (boy) and 48.5 mm (girl) off their sockets."""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
R = []


def check(name, ok, detail=None):
    R.append((name, bool(ok)))
    print(f"[test_shot_eyes] {'PASS' if ok else 'FAIL'} {name}{'' if detail is None else ' ' + str(detail)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--shot", default=os.path.join(ROOT, "episodes", "e905_props_test", "shots", "s010", "shot.scene.json"))
    ap.add_argument("--max-mm", type=float, default=0.5)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as t:
        run = os.path.join(t, "run")
        p = subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "production", "run_shot.py"), "--shot", a.shot,
                            "--blender", a.blender, "--stages", "prepare,bake", "--run-dir", run], capture_output=True, text=True)
        check("prepare and bake", p.returncode == 0, (p.stdout + p.stderr)[-600:] if p.returncode else None)
        if p.returncode:
            sys.exit(1)
        cast = os.path.join(os.path.dirname(a.shot), "build", "cast.json")
        out = os.path.join(t, "render")
        p = subprocess.run([a.blender, "-b", "--factory-startup", "-P", os.path.join(ROOT, "pipeline", "charsys", "shot_render.py"),
                            "--", "--bake", os.path.join(run, "bake.json"), "--cast", cast, "--out", out, "--blend-only"],
                           capture_output=True, text=True)
        check("shot_render --blend-only", p.returncode == 0, (p.stdout + p.stderr)[-600:] if p.returncode else None)
        if p.returncode:
            sys.exit(1)
        rep = json.load(open(os.path.join(out, "shot_render.json")))
        check("every frame applied", rep["frames"] == json.load(open(os.path.join(run, "bake.json")))["frames"], rep["frames"])
        for name, c in rep["characters"].items():
            check(f"{name}: eye objects found", len(c.get("eye_objects") or []) >= 2, c.get("eye_objects"))
            check(f"{name}: eye centre to socket <= {a.max_mm} mm over all frames", c.get("eye_socket_max_mm") is not None
                  and c["eye_socket_max_mm"] <= a.max_mm, f"{c.get('eye_socket_max_mm')} mm (worst frame {c.get('eye_socket_worst_frame')})")
            check(f"{name}: baked bones reproduced", c["max_bone_error_mm"] < 0.01, f"{c['max_bone_error_mm']} mm")
    ok = all(x for _, x in R)
    print(f"[test_shot_eyes] {'ALL PASS' if ok else 'FAILURES'} ({sum(x for _, x in R)}/{len(R)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
