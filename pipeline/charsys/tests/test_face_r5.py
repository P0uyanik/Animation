"""T-137: faces round 5 checks (closed-eye lash curve in face_v3/lids.py; F1a/F1b/F2 overrides stay overrides).

    python3 pipeline/charsys/tests/test_face_r5.py [--blender <exe or tools/bpy_blender.py>]

Plain checks (no Blender):
  * the lash curve is opt-in: fit_closed_lids calls curve_closed_lash only under closed_fit["lash_curve"], and no spec
    under assets/ sets it (default builds do not reach the new code; the mesh-hash evidence is in
    docs/evaluation/characters/T-137/checks/);
  * no character names in face_v3/lids.py;
  * the T-137 overrides only touch their sections (F1a: face.eyes; F1b: face.eyes and hair fringe/keepout) and pin no
    version; the F1b fringe override differs from T-126b's structures only in the fringe.
Unit check (--blender): curve_closed_lash on a synthetic lash (a tube on a sphere with Blink / in-between / EyeWide
keys): the basis and the open key do not move, a key above the seam does not move, the closed key ends on the target
curve (middle below the ends by sag + lift, at the seam + above), at rest radius + out_m, and a negative key factor
turns the curve over.

T-156 (opt-in lid yaw, lids.upper_yaw_deg / lower_yaw_deg): plain: guarded in lid_roll, no spec under assets/ sets it,
the T-156 eye overrides touch face.eyes only; unit: without the key lid_roll returns what it returned before (None, or
the roll matrix, bit for bit); with it a lid edge arc keeps its radius and its peak moves r sin(yaw) towards the outer
corner on both sides."""
import json
import math
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EV = os.path.join(ROOT, "docs", "evaluation", "characters", "T-137")
sys.path.insert(0, HERE)
import test_guard_allowlist as GA  # noqa: E402
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" ({detail})" if detail and not ok else ""))


def _find(d, key):
    if isinstance(d, dict):
        return key in d or any(_find(v, key) for v in d.values())
    if isinstance(d, list):
        return any(_find(v, key) for v in d)
    return False


def plain():
    src = open(os.path.join(ROOT, "pipeline", "charsys", "face_v3", "lids.py")).read()
    calls = re.findall(r"^.*curve_closed_lash\(.*$", src, re.M)
    check("lash curve: one call site, guarded by closed_fit['lash_curve']",
          len(calls) == 2 and 'if fit.get("lash_curve") and lash is not None' in src, str(calls))
    check("no character names in face_v3/lids.py", not re.search(r"boy_|girl_|auburn|hoodie|white_hair", src))
    users = []
    for base, _, files in os.walk(os.path.join(ROOT, "assets", "characters")):
        for f in files:
            if f.endswith(".json") and os.sep + "spec" in base + os.sep:
                try:
                    if _find(json.load(open(os.path.join(base, f))), "lash_curve"):
                        users.append(os.path.relpath(os.path.join(base, f), ROOT))
                except ValueError:
                    pass
    users, _allowed, aerr = GA.split(users, "lash_curve")  # T-154 owner-approved candidate allowlist
    check("owner-approved candidate allowlist is valid (T-154)", not aerr, aerr[:3])
    check("no spec under assets/ opts into lash_curve (except listed owner-approved candidates)", not users, str(users))
    check("lid yaw: opt-in branch in lid_roll, the roll-only return unchanged",
          'if abs(yaw) > 1e-9:' in src and
          'return Matrix.Rotation(math.radians(-sx * deg), 3, "Y") if abs(deg) > 1e-9 else None' in src)
    users = []
    for base, _, files in os.walk(os.path.join(ROOT, "assets", "characters")):
        for f in files:
            if f.endswith(".json") and os.sep + "spec" in base + os.sep:
                try:
                    d = json.load(open(os.path.join(base, f)))
                    if _find(d, "upper_yaw_deg") or _find(d, "lower_yaw_deg") or _find(d, "sink_m") \
                            or _find(d, "shell_occlusion_tint") or _find(d, "closed_fill"):
                        users.append(f)
                except ValueError:
                    pass
    check("no spec under assets/ opts into lid yaw, closed_fit.sink_m, shell_occlusion_tint or socket.closed_fill", not users, str(users))
    check("closed_fit.sink_m: default 0, guarded, upper shell only",
          'sink = _f(fit, "sink_m", 0.0)' in src and 'if sink > 0.0 and ob is up:' in src)
    check("closed_fit.shell_occlusion_tint: guarded, the shell_subsurface call unchanged without it",
          'if fit.get("shell_occlusion_tint") is not None:' in src and
          'elif fit.get("shell_subsurface") is not None:\n'
          '        rep["shell_material"] = _shell_material(up, float(fit["shell_subsurface"]))' in src and
          'def _shell_material(ob, factor, occlusion_tint=None):' in src and 'if occlusion_tint is not None:' in src)
    sock = open(os.path.join(ROOT, "pipeline", "charsys", "face_v3", "socket.py")).read()
    check("socket.closed_fill: opt-in (absent = no fill data, no attribute), written after the basis",
          'fill = cfg.get("closed_fill")' in sock and 'if fill is not None:' in sock and
          sock.index("    write(p)\n    if fill_sel:") < sock.index('me.attributes.new(f"ps_socket_fill.{side}"'))
    check("skin closed fill: only where the socket stored its attribute; the attribute is removed",
          'if head is None:\n        return None' in src and 'me.attributes.remove(me.attributes[name])' in src)
    for sub, name in (("auburn", "girl_auburn_bun_glasses"), ("third", "girl_white_hair_blue_dress")):
        ov = os.path.join(ROOT, "docs", "evaluation", "characters", "T-156", sub, name + ".eyes.override.json")
        if os.path.exists(ov):
            d = json.load(open(ov))
            check(f"T-156 {sub} override: face.eyes only, no version pin",
                  set(d) == {"face"} and set(d["face"]) == {"eyes"} and not _find(d, "spec_version"), str(list(d)))
    f1a = os.path.join(EV, "f1a", "girl_auburn_bun_glasses.eyes.override.json")
    if os.path.exists(f1a):
        d = json.load(open(f1a))
        check("F1a override: face.eyes only", set(d) == {"face"} and set(d["face"]) == {"eyes"}, str(list(d)))
        check("F1a override: no lash_curve, no version pin", not _find(d, "lash_curve") and not _find(d, "spec_version"))
    eyes = os.path.join(EV, "f1b", "girl_white_hair_blue_dress.eyes.override.json")
    fringe = os.path.join(EV, "f1b", "girl_white_hair_blue_dress.fringe.override.json")
    if os.path.exists(eyes) and os.path.exists(fringe):
        d = json.load(open(eyes))
        check("F1b eyes override: face.eyes only, opts into lash_curve",
              set(d) == {"face"} and set(d["face"]) == {"eyes"} and "lash_curve" in d["face"]["eyes"]["lids"]["closed_fit"])
        h = json.load(open(fringe))["override"]
        base = json.load(open(os.path.join(ROOT, "docs/evaluation/characters/T-126/hair/candidates/"
                                                 "girl_white_hair_blue_dress.hair.override.json")))["override"]["hair"]
        check("F1b fringe override: hair.face_keepout + hair.structures only",
              set(h) == {"hair"} and set(h["hair"]) == {"face_keepout", "structures"})
        other = [(a["name"], a == b) for a, b in zip(base["structures"], h["hair"]["structures"]) if a["name"] != "fringe"]
        check("F1b fringe override: every structure but the fringe equals T-126b's",
              len(base["structures"]) == len(h["hair"]["structures"]) and all(ok for _, ok in other), str(other))


UNIT = r'''
import json, math, sys
import bpy, numpy as np
from mathutils import Matrix
sys.path.insert(0, sys.argv[sys.argv.index("--") + 1])
from face_v3 import lids as LIDS
r, e_rest, a_close = 0.05, math.radians(40.0), math.radians(110.0)
verts, faces = [], []
xs = np.linspace(-0.6, 0.6, 25)
for i, u in enumerate(xs):  # a thin band on the sphere at elevation e_rest (the lash line), 2 rows
    for de in (0.0, 0.02):
        c = math.sqrt(1 - u * u)
        e = e_rest + de
        verts.append((u * r, -c * math.cos(e) * r, c * math.sin(e) * r))
    if i:
        faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
me = bpy.data.meshes.new("lash")
me.from_pydata(verts, [], faces)
ob = bpy.data.objects.new("lash.L", me)
bpy.context.scene.collection.objects.link(ob)
ob.shape_key_add(name="Basis")
def rot_key(name, deg):
    k = ob.shape_key_add(name=name)
    R = Matrix.Rotation(math.radians(deg), 3, "X")
    for i, v in enumerate(me.vertices):
        k.data[i].co = R @ v.co
rot_key("Blink.L@25", 27.5); rot_key("Blink.L", 110.0); rot_key("EyeWide", -10.0); rot_key("Laugh", 110.0)
def coords(name):
    return np.array([d.co[:] for d in me.shape_keys.key_blocks[name].data])
before = {k.name: coords(k.name) for k in me.shape_keys.key_blocks}
cfg = {"out_m": 0.002, "sag_deg": 6.0, "corner_lift_deg": 10.0, "above_seam_deg": 14.0, "keys": {"Laugh": -1.0}}
rep = LIDS.curve_closed_lash(ob, Matrix.Identity(4), r, cfg, a_close, -36.0)
after = {k.name: coords(k.name) for k in me.shape_keys.key_blocks}
def elev(p):
    return np.degrees(np.arctan2(p[:, 2], -p[:, 1]))
row = np.arange(0, len(verts), 2)
mid, end = row[len(row) // 2], row[0]
out = {"rep": rep,
       "moved": {n: float(np.abs(after[n] - before[n]).max()) for n in before},
       "blink_mid": float(elev(after["Blink.L"])[mid]), "blink_end": float(elev(after["Blink.L"])[end]),
       "laugh_mid": float(elev(after["Laugh"])[mid]), "laugh_end": float(elev(after["Laugh"])[end]),
       "radius": float(np.linalg.norm(after["Blink.L"][row], axis=1).mean())}
# T-156: lid yaw. A lid edge arc (a circle of 30 deg about the forward axis, upper half) before / after lid_roll's matrix
arc = [np.array((math.sin(math.radians(30)) * math.cos(t), -math.cos(math.radians(30)), math.sin(math.radians(30)) * math.sin(t))) * r
       for t in np.linspace(0.2, math.pi - 0.2, 181)]
yaw = {"none": LIDS.lid_roll({}, 1, "up") is None,
       "roll_only": [list(map(list, LIDS.lid_roll({"upper_roll_deg": -18.0, "lower_roll_deg": 5.0}, sx, z))) ==
                     list(map(list, Matrix.Rotation(math.radians(-sx * d), 3, "Y")))
                     for sx in (1, -1) for z, d in (("up", -18.0), ("lo", 5.0))],
       "lower_untouched": LIDS.lid_roll({"upper_yaw_deg": 8.0}, 1, "lo") is None, "peak_x": {}, "radius_err": 0.0}
for sx in (1, -1):
    for name, cfg in (("roll", {"upper_roll_deg": 14.0}), ("yaw", {"upper_roll_deg": 14.0, "upper_yaw_deg": 8.0})):
        R = np.array(LIDS.lid_roll(cfg, sx, "up"))
        q = np.array(arc) @ R.T
        yaw["peak_x"][f"{name}{sx}"] = float(q[np.argmax(q[:, 2]), 0])
        yaw["radius_err"] = max(yaw["radius_err"], float(np.abs(np.linalg.norm(q, axis=1) - r).max()))
out["yaw"] = yaw
json.dump(out, open(sys.argv[sys.argv.index("--") + 2], "w"))
'''


def unit(blender):
    with tempfile.TemporaryDirectory() as tmp:
        script, out = os.path.join(tmp, "unit.py"), os.path.join(tmp, "out.json")
        open(script, "w").write(UNIT)
        cmd = ([sys.executable, blender] if blender.endswith(".py") else [blender]) + \
            ["-b", "--factory-startup", "-P", script, "--", os.path.join(ROOT, "pipeline", "charsys"), out]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if not os.path.exists(out):
            check("unit: curve_closed_lash ran", False, p.stdout[-400:] + p.stderr[-400:])
            return
        d = json.load(open(out))
    m = d["moved"]
    check("unit: basis, open key and a key above the seam do not move",
          max(m["Basis"], m["EyeWide"], m["Blink.L@25"]) < 1e-9, str(m))
    check("unit: closed key moved and is reported", m["Blink.L"] > 0.01 and d["rep"]["keys"].get("Blink.L") == 1.0, str(d["rep"]))
    check("unit: closed lash middle at seam + above - sag (-28 deg)", abs(d["blink_mid"] - (-28.0)) < 0.6, f"{d['blink_mid']:.2f}")
    check("unit: closed lash ends at seam + above + lift (-12 deg)", abs(d["blink_end"] - (-12.0)) < 0.6, f"{d['blink_end']:.2f}")
    check("unit: key factor -1 turns the curve over (middle above the ends)",
          d["laugh_mid"] > d["laugh_end"] + 10.0, f"{d['laugh_mid']:.2f} / {d['laugh_end']:.2f}")
    check("unit: closed lash at rest radius + out_m", abs(d["radius"] - 0.052) < 2e-4, f"{d['radius']:.5f}")
    y = d["yaw"]
    check("unit: lid_roll without the yaw key is unchanged (None / the roll matrix)",
          y["none"] and all(y["roll_only"]) and y["lower_untouched"], str(y))
    shift = 0.05 * math.sin(math.radians(8.0))
    check("unit: a roll alone does not move the arc's peak; the yaw moves it r sin(yaw) outwards, radius kept",
          all(abs(y["peak_x"][f"roll{sx}"]) < 1e-3 and abs(y["peak_x"][f"yaw{sx}"] - y["peak_x"][f"roll{sx}"] - sx * shift) < 1e-3
              for sx in (1, -1)) and y["radius_err"] < 1e-6, str(y))


def main():
    plain()
    if "--blender" in sys.argv:
        unit(sys.argv[sys.argv.index("--blender") + 1])
    print(f"[test_face_r5] {'ALL PASS' if all(RESULTS) else 'FAIL'} {sum(RESULTS)}/{len(RESULTS)}")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
