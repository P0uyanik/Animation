"""T-159: accessories glasses temples.rest_on_ear (opt-in).

    python3 pipeline/charsys/tests/test_glasses_rest.py --blender <exe>

Builds glasses inside Blender on a stub head (flat face at y = -0.12, head sides at x = +-0.14) with two ellipsoid
ears as obstacles:
  * default (no key): the lifted route (report temple_lift_m > 0, no temple_rest_m);
  * rest_on_ear: no lift, the report records the rest point; the arm's straight part is a straight line in the side
    view; no ear vertex in the arm's corridor is above the arm's underside; the arm touches the ear (smallest gap
    between the ear and the arm's underside < 1 mm); the hook ends below the straight part, behind the ear;
  * rest_on_ear without an ear in the corridor falls back to the default route.
Without --blender nothing can run (accessories needs bpy): the test reports SKIP and exits 0."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
RESULTS = []
TAG = "[test_glasses_rest]"

PROBE = r'''
import json, sys
import bpy
from mathutils import Vector
sys.path.insert(0, sys.argv[sys.argv.index("--") + 1])
import accessories as ACC
import geom as G

WIRE = 0.0016


class Ctx:
    def side_x(self, sx, y, z):
        return sx * 0.14

    def face_y(self, _o, x, z):
        return -0.12


def scene(with_ears=True):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    C = bpy.context.scene.collection
    eyes = [G.uv_sphere(f"eye.{s}", (sx * 0.058, -0.10, 0.77), 0.03, C, 16, 8) for sx, s in ((1, "L"), (-1, "R"))]
    ears = [G.uv_sphere(f"ear.{s}", (sx * 0.15, 0.005, 0.755), 1.0, C, 32, 16, (0.014, 0.028, 0.036))
            for sx, s in ((1, "L"), (-1, "R"))] if with_ears else []
    bpy.context.view_layer.update()
    lm = {"eye_L": Vector((0.058, -0.13, 0.77)), "eye_R": Vector((-0.058, -0.13, 0.77)),
          "ear_L": Vector((0.15, 0.005, 0.755)), "ear_R": Vector((-0.15, 0.005, 0.755))}
    return C, eyes, ears, lm


def run(temples, with_ears=True):
    C, eyes, ears, lm = scene(with_ears)
    cfg = {"type": "glasses/1", "name": "glasses", "rim": {"radius_eye_spacing": 0.43}, "wire_radius_m": WIRE,
           "temples": dict({"enabled": True, "skin_offset_m": 0.004, "past_ear_m": 0.012, "above_ear_m": 0.022, "drop_m": 0.008}, **temples),
           "lens": {"enabled": False}}
    frame, lens, rep = ACC.build_glasses(C, cfg, lm, Ctx(), eyes, "head", ears)
    ear = [e.matrix_world @ v.co for e in ears[:1] for v in e.data.vertices]
    return rep, ear, cfg


out = {}
rep, ear, cfg = run({})
out["default_lift"] = rep["temple_lift_m"]["L"]
out["default_rest"] = "temple_rest_m" in rep
rep, ear, cfg = run({"rest_on_ear": True})
out["rest_lift"] = rep["temple_lift_m"]["L"]
out["rest_point"] = rep.get("temple_rest_m", {}).get("L")
# the path itself (same call the builder makes), for the geometric checks
hinge = Vector((0.058 + 0.43 * 0.116, -0.13, 0.77))
obs = [q for q in ear if q.x > 0]
path = ACC._temple_rest(hinge, 1, obs, Ctx(), cfg["temples"], WIRE)
ys, zs = [p.y for p in path], [p.z for p in path]
slope = (zs[-1] - zs[0]) / (ys[-1] - ys[0])
out["straight_dev_m"] = max(abs(z - (zs[0] + slope * (y - ys[0]))) for y, z in zip(ys, zs))
gaps = [zs[0] + slope * (q.y - ys[0]) - WIRE - q.z for q in obs if abs(q.x - 0.144) <= 0.004 and ys[0] + 0.02 <= q.y <= ys[-1]]
out["min_gap_m"] = min(gaps)
out["corridor_vertices"] = len(gaps)
out["end_behind_ear_top"] = bool(ys[-1] > max(obs, key=lambda q: q.z).y - 0.02)
rep2, _, _ = run({"rest_on_ear": True}, with_ears=False)
out["no_ear_rest"] = "temple_rest_m" in rep2
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
        print(f"{TAG} SKIP (no --blender: accessories needs bpy)")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "probe.py")
        with open(script, "w") as f:
            f.write(PROBE)
        res = subprocess.run([blender, "-b", "--factory-startup", "-P", script, "--", CHARSYS], capture_output=True, text=True)
    line = [ln for ln in res.stdout.splitlines() if ln.startswith("PROBE ")]
    if not line:
        print(res.stdout[-2000:], res.stderr[-3000:])
        check("probe ran", False)
        return 1
    o = json.loads(line[-1][6:])
    check("default: lifted route, no rest point", o["default_lift"] > 0.005 and not o["default_rest"], f"lift {o['default_lift'] * 1000:.1f} mm")
    check("rest_on_ear: no lift, rest point reported", o["rest_lift"] == 0.0 and o["rest_point"] is not None, str(o["rest_point"]))
    check("rest_on_ear: straight in the side view", o["straight_dev_m"] < 1e-6, f"{o['straight_dev_m']:.1e} m")
    check("rest_on_ear: no ear vertex above the arm's underside", o["min_gap_m"] > 0 and o["corridor_vertices"] > 3,
          f"{o['corridor_vertices']} corridor vertices, smallest gap {o['min_gap_m'] * 1000:.2f} mm")
    check("rest_on_ear: the arm touches the ear", o["min_gap_m"] < 0.001, f"{o['min_gap_m'] * 1000:.2f} mm")
    check("rest_on_ear: the straight part ends behind the contact", o["end_behind_ear_top"])
    check("rest_on_ear without an ear: default route", not o["no_ear_rest"])
    print(f"{TAG} {'ALL PASS' if all(RESULTS) else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
