"""T-159: face.shape.front_fade_m (opt-in) of face_features.shape_face_v2.

    python3 pipeline/charsys/tests/test_face_front_fade.py --blender <exe>

Runs shape_face_v2 (face_width_m and jaw_depth_roundness only) on a dense sphere head inside Blender:
  * front_weight: fade 0 is the boolean hard cut; fade > 0 is 1 in front, 0 behind, 0.5 at the cut, monotone;
  * without front_fade_m the result equals the pre-T-159 formula (hard cut) exactly, and the side profile has the
    ledge (a step in the widening across the cut);
  * with front_fade_m the widening has no step (largest change between neighbouring depth bins is a fraction of the
    hard cut's), is unchanged in front of the fade zone and zero behind it;
  * the report records front_fade_m only when it is set.
Without --blender nothing can run (face_features needs bpy): the test reports SKIP and exits 0."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
RESULTS = []

PROBE = r'''
import json, sys
import bpy
import numpy as np
sys.path.insert(0, sys.argv[sys.argv.index("--") + 1])
import face_features as FF

FY, EZ, ZCHIN = -0.12, 0.0, -0.09
CUT = FY + 0.6 * abs(FY)


class Ctx:
    def face_y(self, _o, _x, _z):
        return FY

    def invalidate(self):
        pass


def run(cfg):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=256, ring_count=128, radius=0.12)
    head = bpy.context.object
    n = len(head.data.vertices)
    before = np.empty(n * 3); head.data.vertices.foreach_get("co", before)
    rep = FF.shape_face_v2(head, Ctx(), cfg, 0.05, EZ, 0.04, ZCHIN)
    after = np.empty(n * 3); head.data.vertices.foreach_get("co", after)
    bpy.data.objects.remove(head)
    return before.reshape(n, 3), after.reshape(n, 3), rep


def widening(b, a):
    """Mean sideways displacement per 2 mm depth bin on the +x side, in the face-width band."""
    m = (b[:, 0] > 0.04) & (np.abs(b[:, 2] + 0.035) < 0.01)
    dx = (a - b)[m, 0]
    y = b[m, 1]
    bins = np.arange(-0.11, 0.06, 0.002)
    return [float(dx[(y >= lo) & (y < lo + 0.002)].mean()) if ((y >= lo) & (y < lo + 0.002)).any() else None for lo in bins], bins.tolist()


out = {"cut": CUT}
y = np.linspace(-0.12, 0.06, 181)
hard = FF.front_weight(y, CUT, 0.0)
soft = FF.front_weight(y, CUT, 0.08)
out["hard_is_bool"] = bool(hard.dtype == bool and np.array_equal(hard, y < CUT))
out["soft_range"] = [float(soft.min()), float(soft.max())]
out["soft_monotone"] = bool(np.all(np.diff(soft) <= 1e-12))
out["soft_at_cut"] = float(FF.front_weight(np.array([CUT]), CUT, 0.08)[0])
out["soft_front"] = float(FF.front_weight(np.array([CUT - 0.04]), CUT, 0.08)[0])
out["soft_back"] = float(FF.front_weight(np.array([CUT + 0.04]), CUT, 0.08)[0])
base = {"face_width_m": 0.016, "face_width_below_eye_m": 0.035, "face_width_band_m": 0.035, "jaw_depth_roundness": 0.6}
b0, a0, r0 = run(dict(base))
b1, a1, r1 = run(dict(base, front_fade_m=0.08))
# the pre-T-159 formula, written out independently (hard cut)
p = b0.copy()
front = p[:, 1] < CUT
wz = np.exp(-((p[:, 2] - (EZ - 0.035)) / 0.035) ** 2)
hw = np.abs(p[:, 0]).max()
p[:, 0] += np.sign(p[:, 0]) * 0.016 * wz * front * np.clip(np.abs(p[:, 0]) / hw, 0, 1) ** 1.5
wz = np.exp(-((p[:, 2] - (EZ - 0.03)) / 0.05) ** 2) * (p[:, 2] < EZ + 0.01)
u = np.clip(np.abs(p[:, 0]) / max(np.abs(p[:, 0]).max(), 1e-4), 0, 1)
p[:, 1] += 0.6 * wz * (u ** 2) * np.clip(1 - (p[:, 1] - p[:, 1].min()) / 0.08, 0, 1) * 0.04 * front
out["default_max_dev_m"] = float(np.abs(p - a0).max())
w0, bins = widening(b0, a0)
w1, _ = widening(b1, a1)
step = lambda w: max(abs(w[i + 1] - w[i]) for i in range(len(w) - 1) if w[i] is not None and w[i + 1] is not None)
out["step_hard_m"], out["step_fade_m"] = step(w0), step(w1)
far_front = b0[:, 1] < CUT - 0.045
far_back = b0[:, 1] > CUT + 0.045
out["front_same_m"] = float(np.abs(a1[far_front] - a0[far_front]).max())
out["back_moved_m"] = float(np.abs(a1[far_back] - b1[far_back]).max())
out["report_default"] = "front_fade_m" in r0
out["report_fade"] = r1.get("front_fade_m")
print("PROBE " + json.dumps(out))
'''


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"[test_face_front_fade] {'PASS' if ok else 'FAIL'} {name}{(': ' + detail) if detail else ''}")


def main():
    blender = arg("--blender")
    if not blender:
        print("[test_face_front_fade] SKIP (no --blender: face_features needs bpy)")
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
    check("fade 0 is the boolean hard cut", o["hard_is_bool"])
    check("fade weight spans 1..0, monotone", o["soft_range"] == [0.0, 1.0] and o["soft_monotone"], str(o["soft_range"]))
    check("fade weight is 0.5 at the cut, 1 / 0 at its ends", abs(o["soft_at_cut"] - 0.5) < 1e-9 and o["soft_front"] == 1.0 and o["soft_back"] == 0.0)
    check("default (no key) equals the hard-cut formula", o["default_max_dev_m"] < 1e-6, f"{o['default_max_dev_m']:.2e} m")
    check("default has the ledge", o["step_hard_m"] > 0.004, f"{o['step_hard_m'] * 1000:.2f} mm step")
    check("fade removes the ledge", o["step_fade_m"] < 0.1 * o["step_hard_m"], f"{o['step_fade_m'] * 1000:.2f} mm per 2 mm bin")
    check("face in front of the fade zone unchanged", o["front_same_m"] < 1e-6, f"{o['front_same_m']:.2e} m")
    check("nothing moves behind the fade zone", o["back_moved_m"] < 1e-6, f"{o['back_moved_m']:.2e} m")
    check("report records front_fade_m only when set", o["report_default"] is False and o["report_fade"] == 0.08)
    print(f"[test_face_front_fade] {'ALL PASS' if all(RESULTS) else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
