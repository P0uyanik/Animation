"""T-168: opt-in face options (cheek pad top fade in face_v3/lower_face.py, nose type "upturned" in face_features.py).

    python3 pipeline/charsys/tests/test_face_t168.py [--blender <exe or tools/bpy_blender.py>]

Plain checks (no Blender):
  * both options are opt-in: the pad fade defaults to the previous constant (0.015) and no spec under assets/ sets
    cheek_pad_top_fade_m or the nose type "upturned" (default builds do not reach the new code);
  * no character names in the two edited functions' modules' new code paths (face_v3/lower_face.py).
Unit checks (--blender) on a synthetic head (a sphere):
  * upturned nose: the tip stands out by height_m, nothing moves outside the footprint (beside the tip, above the
    bridge, below the underside, the back of the head), the bridge side slopes more gently than the underside;
  * cheek pad: cheek_pad_top_fade_m = 0.015 gives exactly the default result; a longer fade lowers the steepest
    vertical step of the pad and moves nothing above cheek_pad_top_below_eye_m."""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" ({detail})" if detail and not ok else ""))


def _walk(d, fn):
    if isinstance(d, dict):
        return any(fn(k, v) or _walk(v, fn) for k, v in d.items())
    if isinstance(d, list):
        return any(_walk(v, fn) for v in d)
    return False


def plain():
    lf = open(os.path.join(ROOT, "pipeline", "charsys", "face_v3", "lower_face.py")).read()
    check("cheek pad top fade defaults to the previous constant",
          '_f(cfg, "cheek_pad_top_fade_m", 0.015)' in lf and lf.count("cheek_pad_top_fade_m") == 2)
    check("no character names in face_v3/lower_face.py", not re.search(r"boy_|girl_|auburn|hoodie|white_hair", lf))
    ff = open(os.path.join(ROOT, "pipeline", "charsys", "face_features.py")).read()
    check("upturned nose is one branch of build_nose", ff.count('t == "upturned"') == 1)
    users = []
    for base, _, files in os.walk(os.path.join(ROOT, "assets")):
        for f in files:
            if not f.endswith(".json") or "references" in base:
                continue
            try:
                d = json.load(open(os.path.join(base, f)))
            except (ValueError, UnicodeDecodeError):
                continue
            if _walk(d, lambda k, v: k == "cheek_pad_top_fade_m" or (k == "nose" and isinstance(v, dict) and v.get("type") == "upturned")):
                users.append(os.path.relpath(os.path.join(base, f), ROOT))
    check("no spec under assets/ uses the new options", not users, str(users))


UNIT = r'''
import json, math, sys
import bpy, bmesh
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, a[0])
import face_features as FF
from face_v3 import lower_face as LF
R, ZC = 0.15, 0.80


class Ctx:
    def face_y(self, _o, x, z):
        return -math.sqrt(max(R * R - x * x - (z - ZC) ** 2, 0.0))

    def invalidate(self):
        pass


def head():
    me = bpy.data.meshes.new("head")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=7, radius=R)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("head", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (0, 0, ZC)
    bpy.context.view_layer.update()
    return ob


def co(ob):
    return np.array([ob.matrix_world @ v.co for v in ob.data.vertices])


out = {}
# --- nose
h = head()
p0 = co(h)
nc = {"type": "upturned", "size_m": 0.011, "height_m": 0.007, "bridge_m": 0.024, "under_m": 0.008}
z = 0.77
FF.build_nose(None, {}, h, Ctx(), nc, z)
p1 = co(h)
d = np.linalg.norm(p1 - p0, axis=1)
dz = p0[:, 2] - z
mid = np.abs(p0[:, 0]) < 0.0015
outside = (np.abs(p0[:, 0]) > 0.0111) | (dz > 0.0241) | (dz < -0.0081) | (p0[:, 1] > 0)
out["nose"] = {"tip": float(d.max()), "outside": float(d[outside].max()),
               "above": float(d[mid & (np.abs(dz - 0.006) < 0.0015)].max()),
               "below": float(d[mid & (np.abs(dz + 0.006) < 0.0015)].max()),
               "asym_x": float(abs(d[p0[:, 0] > 0].max() - d[p0[:, 0] < 0].max()))}
# --- cheek pad
res = {}
for name, extra in (("default", {}), ("explicit", {"cheek_pad_top_fade_m": 0.015}), ("long", {"cheek_pad_top_fade_m": 0.045})):
    h = head()
    p0 = co(h)
    cfg = dict({"cheek_pad_m": 0.016, "cheek_pad_radius_m": 0.07, "cheek_pad_x": 1.3, "cheek_pad_below_eye_m": 0.035,
                "cheek_pad_top_below_eye_m": 0.015, "cheek_pad_forward": 0.0}, **extra)
    LF.shape_lower_face(h, Ctx(), cfg, 0.068, 0.80, 0.74, 0.70)
    res[name] = (p0, co(h))
dd = np.linalg.norm(res["default"][1] - res["default"][0], axis=1)
dl = np.linalg.norm(res["long"][1] - res["long"][0], axis=1)
p0 = res["default"][0]


def step(dv):  # steepest change of the displacement per metre of height, in the column through the pad centre
    m = (np.abs(p0[:, 0] - 0.0884) < 0.004) & (p0[:, 1] < 0)
    o = np.argsort(p0[m, 2])
    zz, vv = p0[m, 2][o], dv[m][o]
    zb = np.arange(0.74, 0.80, 0.003)
    prof = np.array([vv[np.abs(zz - b) < 0.003].max() if (np.abs(zz - b) < 0.003).any() else 0.0 for b in zb])
    return float(np.abs(np.diff(prof)).max() / 0.003)


out["pad"] = {"explicit_vs_default": float(np.abs(res["explicit"][1] - res["default"][1]).max()),
              "step_default": step(dd), "step_long": step(dl),
              "above_top_long": float(dl[p0[:, 2] > 0.80 - 0.015 + 1e-6].max()), "max_default": float(dd.max()), "max_long": float(dl.max())}
json.dump(out, open(a[1], "w"))
'''


def unit(blender):
    with tempfile.TemporaryDirectory() as tmp:
        script, out = os.path.join(tmp, "unit.py"), os.path.join(tmp, "out.json")
        open(script, "w").write(UNIT)
        cmd = ([sys.executable, blender] if blender.endswith(".py") else [blender]) + \
            ["-b", "--factory-startup", "-P", script, "--", os.path.join(ROOT, "pipeline", "charsys"), out]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if not os.path.exists(out):
            check("unit: ran", False, p.stdout[-600:] + p.stderr[-600:])
            return
        d = json.load(open(out))
    n, pad = d["nose"], d["pad"]
    check("unit nose: the tip stands out by height_m (7 mm)", 0.0062 < n["tip"] <= 0.0070001, str(n))
    check("unit nose: nothing moves outside the footprint", n["outside"] < 1e-9, str(n))
    check("unit nose: bridge slopes more gently than the underside", n["above"] > n["below"] * 1.5 and n["below"] > 0, str(n))
    check("unit nose: symmetric", n["asym_x"] < 2e-4, str(n))
    check("unit pad: cheek_pad_top_fade_m 0.015 == default", pad["explicit_vs_default"] == 0.0, str(pad))
    check("unit pad: a longer fade lowers the steepest vertical step", pad["step_long"] < 0.7 * pad["step_default"], str(pad))
    check("unit pad: nothing moves above cheek_pad_top_below_eye_m", pad["above_top_long"] < 1e-9, str(pad))


def main():
    plain()
    if "--blender" in sys.argv:
        unit(sys.argv[sys.argv.index("--blender") + 1])
    print(f"[test_face_t168] {'ALL PASS' if all(RESULTS) else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
