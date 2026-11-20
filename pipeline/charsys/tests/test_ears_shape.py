"""T-159: face.ears.shape and face.ears.subsurface (opt-in) of face_generic.build_ears.

    python3 pipeline/charsys/tests/test_ears_shape.py --blender <exe>

Builds the two ears inside Blender with a stub face context (head side at x = +-0.14):
  * default (no new key): the pre-T-159 ear (1986 vertices, object at its seat, no stored landmark);
  * shape: the outer face has a bowl (its centre lies below the rim around it) and a rim (higher than the plain
    ellipsoid at the back of the ear), the C opens to the front (front rim lower than the back rim), left and right
    are mirror images;
  * subsurface: the ears get a copy of the face skin ("<name>.ear", one copy for both ears) with the subsurface
    weight scaled; the face skin itself is untouched; the geometry and the ear's seat are unchanged.
Without --blender nothing can run (face_generic needs bpy): the test reports SKIP and exits 0."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
RESULTS = []
TAG = "[test_ears_shape]"

PROBE = r'''
import json, sys
import bpy
import numpy as np
sys.path.insert(0, sys.argv[sys.argv.index("--") + 1])
import face_generic as FG

EZ = 0.77
BASE = {"radii_m": [0.014, 0.028, 0.036], "below_eye_m": 0.012, "y_m": 0.008, "out_m": 0.006, "yaw_deg": 22, "tilt_deg": -6}
SHAPE = {"subdiv": 2, "bowl_depth": 0.9, "rim": 0.3, "back_flat": 0.6, "bowl_size": [0.75, 0.62],
         "bowl_centre": [-0.5, -0.05], "bowl_edge": 0.7}


class Ctx:
    def side_x(self, sx, y, z):
        return sx * 0.14


def build(extra):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    mat = bpy.data.materials.new("skin")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.5
    ears = FG.build_ears(bpy.context.scene.collection, {"face_skin": mat}, Ctx(), dict(BASE, **extra), EZ)
    bpy.context.view_layer.update()
    res = []
    for e in ears:
        n = len(e.data.vertices)
        co = np.empty(n * 3)
        e.data.vertices.foreach_get("co", co)
        co = co.reshape(n, 3)
        mw = np.array(e.matrix_world)
        res.append({"local": co, "world": co @ mw[:3, :3].T + mw[:3, 3], "loc": list(e.location),
                    "mat": e.data.materials[0].name, "n": n,
                    "sss": e.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value,
                    "face_sss": mat.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value})
    return res


def outer_height(local, v, w, rad=BASE["radii_m"]):
    """Largest outward x (in thickness radii) of the left ear near the normalised position (v, w)."""
    m = (np.abs(local[:, 1] / rad[1] - v) < 0.12) & (np.abs(local[:, 2] / rad[2] - w) < 0.12)
    return float((local[m, 0] / rad[0]).max())


out = {}
d = build({})
s = build({"shape": SHAPE})
t = build({"shape": SHAPE, "subsurface": 0.3})
out["default_n"] = d[0]["n"]
out["default_mat"] = d[0]["mat"]
out["default_loc"] = d[0]["loc"]
out["shape_n"] = s[0]["n"]
L = s[0]["local"]
out["bowl"] = outer_height(L, -0.5, -0.05)
out["rim_back"] = outer_height(L, 0.55, 0.0)
out["rim_top"] = outer_height(L, 0.0, 0.7)
out["rim_front"] = outer_height(L, -0.85, 0.0)
out["plain_back"] = float(np.sqrt(max(1 - 0.55 ** 2, 0)))
R = s[1]["local"] * np.array([-1.0, 1.0, 1.0])
out["mirror_dev_m"] = float(np.abs(np.sort(L, axis=0) - np.sort(R, axis=0)).max())
out["sss_mats"] = [t[0]["mat"], t[1]["mat"]]
out["sss"] = [t[0]["sss"], t[0]["face_sss"]]
out["sss_world_dev_m"] = float(np.abs(t[0]["world"] - s[0]["world"]).max())
out["sss_loc_dev_m"] = float(np.abs(np.array(t[0]["loc"]) - np.array(s[0]["loc"])).max())
out["shape_mat"] = s[0]["mat"]
print("PROBE " + json.dumps(out))
'''


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"{TAG} {'PASS' if ok else 'FAIL'} {name}{(': ' + detail) if detail else ''}")


def main():
    blender = arg("--blender")
    if not blender:
        print(f"{TAG} SKIP (no --blender: face_generic needs bpy)")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "probe.py")
        with open(script, "w") as f:
            f.write(PROBE)
        res = subprocess.run([blender, "-b", "--factory-startup", "-P", script, "--", CHARSYS], capture_output=True, text=True)
    line = [ln for ln in res.stdout.splitlines() if ln.startswith("PROBE ")]
    if not line:
        print(res.stdout[-2000:], res.stderr[-2000:])
        check("probe ran", False)
        return 1
    o = json.loads(line[-1][6:])
    check("default ear unchanged in kind (1986 vertices, at its seat, the face skin itself)",
          o["default_n"] == 1986 and o["default_mat"] == "skin" and abs(o["default_loc"][0]) > 0.1)
    check("shape: finer mesh", o["shape_n"] > 4 * o["default_n"] - 100, str(o["shape_n"]))
    check("shape: bowl below the rim", o["bowl"] < o["rim_back"] - 0.5 and o["bowl"] < o["rim_top"] - 0.3,
          f"bowl {o['bowl']:.2f}, rim back {o['rim_back']:.2f}, top {o['rim_top']:.2f} (thickness radii)")
    check("shape: rim higher than the plain ellipsoid", o["rim_back"] > o["plain_back"] + 0.05, f"{o['rim_back']:.2f} > {o['plain_back']:.2f}")
    check("shape: the C opens to the front", o["rim_front"] < o["rim_back"] - 0.2, f"front {o['rim_front']:.2f}, back {o['rim_back']:.2f}")
    check("shape: left and right are mirror images", o["mirror_dev_m"] < 1e-6, f"{o['mirror_dev_m']:.1e} m")
    check("subsurface: both ears share one scaled copy, face skin untouched",
          o["sss_mats"] == ["skin.ear", "skin.ear"] and o["shape_mat"] == "skin" and abs(o["sss"][0] - 0.15) < 1e-6 and abs(o["sss"][1] - 0.5) < 1e-6,
          f"ear {o['sss'][0]:.2f}, face {o['sss'][1]:.2f}")
    check("subsurface: geometry and seat unchanged", o["sss_world_dev_m"] == 0.0 and o["sss_loc_dev_m"] == 0.0)
    print(f"{TAG} {'ALL PASS' if all(RESULTS) else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
