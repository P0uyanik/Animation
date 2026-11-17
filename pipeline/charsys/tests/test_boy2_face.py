"""T-058: boy 2.0.0-dev face controls (face_generic/1 opt-in split action units, MouthPout, custom presets).

    python3 pipeline/charsys/tests/test_boy2_face.py --blender <exe> [--master <built 2.0.0-dev master.blend>]

Checks the controls the facial layer (T-046) can drive exist as rig controls and shape keys, that each per-side copy
is exactly its side of the symmetric unit (L + R = full), that MouthPout moves the lips forward, that the rest lids
are heavy (upper lid over the iris), and that the expression set is baked. Without --blender only the spec checks
run."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import spec as S  # noqa: E402

# --- shared with test_hoodie.py (build once or reuse --master; probe a master in Blender)
import subprocess  # noqa: E402
import tempfile  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
SPEC = os.path.join(ROOT, "assets", "characters", "boy_yellow_hoodie", "spec", "boy_yellow_hoodie.2.0.0-dev.spec.json")


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def master(blender):
    """Path of a built 2.0.0-dev master (--master, else a fresh build into a temp dir)."""
    m = arg("--master")
    if m:
        return os.path.abspath(m)
    out = tempfile.mkdtemp(prefix="t058_boy2_")
    subprocess.run([blender, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "build_character.py"), "--",
                    "--spec", SPEC, "--out", out, "--no-glb", "--no-compare"], check=True, stdout=subprocess.DEVNULL)
    return os.path.join(out, "boy_yellow_hoodie_master.blend")


def inspect(blender, blend, script):
    """Runs `script` (Python source using `bpy`, writing a JSON-safe dict into RESULT) on the master."""
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "probe.py"), os.path.join(tmp, "out.json")
        head = "bpy.ops.wm.open_mainfile(filepath=%r)\n" % blend if blend else ""
        open(src, "w").write("import bpy, json, sys\n%sRESULT = {}\n%s\njson.dump(RESULT, open(%r, 'w'))\n"
                             % (head, script, out))
        subprocess.run([blender, "-b", "--factory-startup", "-P", src, "--"], check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return json.load(open(out))

RESULTS = []
CONTROLS = ["BrowUp.L", "BrowUp.R", "BrowDown.L", "BrowDown.R", "BrowDown", "BrowSad", "MouthSmile.L", "MouthSmile.R",
            "MouthFrown.L", "MouthFrown.R", "MouthSmile", "MouthFrown", "JawOpen", "MouthO", "MouthPout", "Blink.L",
            "Blink.R", "EyeSquint", "EyeSquint.L", "EyeSquint.R", "EyeWide"]
EXPRESSIONS = ["Smile", "Sadness", "Surprise", "Anger", "Bored", "Skeptical"]


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_boy2_face] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"))


PROBE = r'''
import numpy as np
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
RESULT["controls"] = sorted(k for k in rig.keys() if k.startswith("face_"))
def keys(name):
    o = bpy.data.objects[name]
    kb = o.data.shape_keys.key_blocks
    n = len(o.data.vertices) * 3
    out = {}
    for k in kb:
        a = np.empty(n); k.data.foreach_get("co", a); out[k.name] = a.reshape(-1, 3)
    return out
m = keys("mouth")
b = m["Basis"]
split = {}
for au in ("MouthSmile", "MouthFrown"):
    d = (m[au + ".L"] - b) + (m[au + ".R"] - b) - (m[au] - b)
    left = m[au + ".L"] - b
    split[au] = {"sum_err": float(np.abs(d).max()), "left_on_right": float(np.abs(left[b[:, 0] < -0.003]).max()),
                 "full": float(np.abs(m[au] - b).max())}
RESULT["split"] = split
RESULT["pout_dy"] = float((m["MouthPout"] - b)[:, 1].min())
bl = keys("brow.L"); br = keys("brow.R")
RESULT["brow_down_L_on_R"] = float(np.abs(br["BrowDown.L"] - br["Basis"]).max())
RESULT["brow_down_L"] = float(np.abs(bl["BrowDown.L"] - bl["Basis"]).max())
up = bpy.data.objects["lid_upper.L"]; eye = bpy.data.objects["eye.L"]
c = eye.matrix_world.translation
low = min((up.matrix_world @ v.co).z for v in up.data.vertices if (up.matrix_world @ v.co).y < c.y)
RESULT["lid_edge_above_centre_m"] = float(low - c.z)
RESULT["eye_radius_m"] = float(max(eye.dimensions) / 2)
'''


def main():
    spec, info = S.load(SPEC)
    check("spec pins face_generic/1, garment/1, hair_clumps/1", info["versions"]["generators"]["face"] == "face_generic/1"
          and info["versions"]["generators"]["garment"] == "garment/1"
          and info["versions"]["generators"]["groom"] == "hair_clumps/1", info["versions"]["generators"])
    au = spec["face"]["action_units"]
    check("spec opts in to split units and MouthPout", au.get("split") and au.get("pout_m", 0) > 0)
    check("spec expression set (neutral/happy/sad/surprised/angry/bored)",
          all(p in spec["face"]["expressions"]["override"] for p in ("Smile", "Sadness", "Surprise", "Anger"))
          and "Bored" in spec["face"]["expressions"]["custom"])
    blender = arg("--blender")
    if blender:
        r = inspect(blender, master(blender), PROBE)
        have = set(c[5:] for c in r["controls"])
        missing = [c for c in CONTROLS + EXPRESSIONS if c not in have]
        check("rig controls for every face channel and expression", not missing, missing)
        for au_name, v in r["split"].items():
            check(f"{au_name}.L + {au_name}.R = {au_name}", v["sum_err"] < 1e-6 and v["full"] > 1e-4, v)
            check(f"{au_name}.L leaves the right corner", v["left_on_right"] < 0.05 * v["full"], v)
        check("BrowDown.L moves only the left brow", r["brow_down_L"] > 1e-3 and r["brow_down_L_on_R"] < 1e-9,
              (r["brow_down_L"], r["brow_down_L_on_R"]))
        check("MouthPout moves the lips forward", r["pout_dy"] < -0.001, r["pout_dy"])
        check("heavy rest lid: upper lid edge within 0.35 r above the eye centre",
              r["lid_edge_above_centre_m"] < 0.35 * r["eye_radius_m"], (r["lid_edge_above_centre_m"], r["eye_radius_m"]))
    else:
        print("[test_boy2_face] (no --blender: build checks skipped)")
    ok = all(RESULTS)
    print(f"[test_boy2_face] {'ALL PASS' if ok else 'FAIL'} ({sum(RESULTS)}/{len(RESULTS)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
