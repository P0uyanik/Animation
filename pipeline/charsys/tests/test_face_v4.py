"""T-109: face round 4 checks (lower-face fullness, lower-lid fit, mouth presets) on top of face_generic/3.

    python3 pipeline/charsys/tests/test_face_v4.py [--blender <exe>] [--boy <master.blend>] [--girl <master.blend>]
        [--unit]   also run test_face_v3's Blender unit checks

Plain checks (no Blender):
  * the new options are opt-in: face_v3/lower_face.py returns before touching the mesh when cheek_pad_m and
    jaw_round_m are 0/absent; face_generic_v3 calls the lower-lid fit only with eyes.lids.lower_fit and the socket
    pulls the skin in only for a side that carries "lo_fit";
  * the mouth presets SmileOpen and Pout are optional library presets (built only when a spec lists them) with engine
    names smileOpen / pout; no default preset changed;
  * the T-109 candidates pin face_generic/3 on the CURRENT versions (boy 2.1.0, girl 0.12.0, fidelity_baseline.json),
    both set face.shape.lower_face, only the girl sets eyes.lids.lower_fit, and each lists its mouth preset;
  * no character names in the shared v3 code (test_face_v3's check, now including lower_face.py).
Build checks (a master per character: --boy/--girl, else built from the current spec + T-109 candidate):
  * every test_face_v3 build check with T-089b's limits unchanged (felt eye; lid shells within their corner bounds;
    <= 10 % 3/4 socket rim; cheek folds <= 45 deg, eye-corner folds no sharper than the published limit; full blink
    closes in front and 3/4 within 1.25 x the published residue) and T-089b's lid-line-at-glance check;
  * fuller lower face: the head surface (largest distance from the head axis per 3 mm x 5 deg bin of head/jaw skin;
    the vertex count differs, since the eye-region refinement follows the shape) moves out against the published
    master: 95th percentile over the lower face (3-12 cm below the eye line, 15-80 deg off forward) >= LOWER_MIN_MM;
  * the face surface above the eyes (more than 1.2 eye radii above the eye line: forehead, brow region) does not move
    (<= DRIFT_MM); the socket smoothing may carry a lower-lid change into the upper socket, the eye and brow checks
    below cover that region;
  * no identity drift in eyes or brows: eye centres, eyeball scale and brow bounds within DRIFT_MM of the published
    master (the lower-face options act below the eyes);
  * girl lens shelf: the lower lid shell is hidden by the skin (lid_shell_exposed of lid_lower <= SHELF_MAX; 0.12.0:
    0.509) and the lid fit ran;
  * the candidate's mouth preset is built and exported to the engine map."""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_face_v3 as V3  # noqa: E402
import test_face_v3b as V3B  # noqa: E402  (its import points V3.CASES at T-089b; reset below)

CHARS = V3.CHARS
CANDIDATES = {
    "boy": (os.path.join(CHARS, "boy_yellow_hoodie", "spec", "boy_yellow_hoodie.2.2.0.spec.json"),
            os.path.join(CHARS, "boy_yellow_hoodie", "spec", "candidates", "T-109", "boy_face4.override.json"),
            os.path.join(CHARS, "boy_yellow_hoodie", "versions", "2.2.0", "boy_yellow_hoodie_master.blend"), "Pout"),
    "girl": (os.path.join(CHARS, "girl_auburn_bun_glasses", "spec", "girl_auburn_bun_glasses.0.13.0.spec.json"),
             os.path.join(CHARS, "girl_auburn_bun_glasses", "spec", "candidates", "T-109", "girl_face4.override.json"),
             os.path.join(CHARS, "girl_auburn_bun_glasses", "versions", "0.13.0", "girl_auburn_bun_glasses_master.blend"),
             "SmileOpen"),
}
V3.CASES = {k: (v[0], v[1]) for k, v in CANDIDATES.items()}
LOWER_MIN_MM = 3.0
DRIFT_MM = 0.5
SHELF_MAX = 0.05
check = V3.check

PROBE_SHAPE = r'''
import bpy, json, sys
import numpy as np
args = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=args[0])
head = next(o for o in bpy.data.objects if o.type == "MESH" and o.name in ("body_skin", "head"))
me = head.data
co = np.empty(len(me.vertices) * 3)
me.vertices.foreach_get("co", co)
mw = np.array(head.matrix_world)
p = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
# head skin only (head + jaw bone weight >= 0.5): the neck and the A-pose shoulders stay out
gis = {vg.index for vg in head.vertex_groups if vg.name in ("DEF-spine.006", "DEF-jaw")}
hw = np.zeros(len(me.vertices))
for v in me.vertices:
    for g in v.groups:
        if g.group in gis:
            hw[v.index] += g.weight
np.savez(args[1], p=p, head=hw >= 0.5 if gis else np.ones(len(p), bool))
out = {"eyes": {}, "brows": {}}
for s in "LR":
    e = bpy.data.objects[f"eye.{s}"]
    out["eyes"][s] = [list(e.matrix_world.translation), list(e.matrix_world.to_scale())]
    b = bpy.data.objects.get(f"brow.{s}")
    if b:
        vs = [b.matrix_world @ v.co for v in b.data.vertices]
        out["brows"][s] = [min(v.x for v in vs), max(v.x for v in vs), min(v.z for v in vs), max(v.z for v in vs)]
print("SHAPE " + json.dumps(out))
'''


def plain_v4():
    src = open(os.path.join(V3.CHARSYS, "face_v3", "lower_face.py")).read()
    check("lower_face is opt-in (returns before touching the mesh without cheek_pad_m / jaw_round_m)",
          re.search(r'if not \(cp or jr\):\s*\n\s*return \{\}', src) is not None)
    gen = open(os.path.join(V3.CHARSYS, "face_generic_v3.py")).read()
    check("face_generic_v3 calls the lower-face options only with face.shape.lower_face",
          'if fs["shape"].get("lower_face"):' in gen)
    check("face_generic_v3 fits the lower lid only with eyes.lids.lower_fit",
          'if (ecfg.get("lids") or {}).get("lower_fit"):' in gen)
    sock = open(os.path.join(V3.CHARSYS, "face_v3", "socket.py")).read()
    check("socket pulls the skin in only for a side with lo_fit", 'if s.get("lo_fit") is not None:' in sock)
    lib = json.load(open(os.path.join(V3.CHARSYS, "face_library", "expressions.json")))
    check("SmileOpen / Pout are optional presets, not defaults",
          all(n in lib["optional_presets"] and n not in lib["presets"] for n in ("SmileOpen", "Pout")))
    check("engine names smileOpen / pout map to them",
          lib["engine_expressions"].get("smileOpen") == "SmileOpen" and lib["engine_expressions"].get("pout") == "Pout")
    base = json.load(open(os.path.join(V3.ROOT, "docs", "evaluation", "characters", "fidelity_baseline.json")))["characters"]
    for who, (spec, ov, _, preset) in CANDIDATES.items():
        cid = os.path.basename(os.path.dirname(os.path.dirname(spec)))
        rel = os.path.relpath(spec, V3.ROOT).replace(os.sep, "/")  # baseline stores POSIX paths (Windows gate)
        check(f"{who} candidate is on the current version", rel == base[cid]["build"], f"{rel} vs {base[cid]['build']}")
        if not os.path.exists(ov):
            check(f"{who} candidate exists", False, ov)
            continue
        s, info = V3.SPEC.load(spec, [ov])
        f = s["face"]
        check(f"{who} candidate pins face_generic/3", info["versions"]["generators"]["face"] == "face_generic/3")
        check(f"{who} candidate sets face.shape.lower_face", bool((f.get("shape") or {}).get("lower_face")))
        fit = bool((f["eyes"].get("lids") or {}).get("lower_fit"))
        check(f"{who} candidate {'sets' if who == 'girl' else 'does not set'} eyes.lids.lower_fit", fit == (who == "girl"))
        check(f"{who} candidate lists the {preset} preset", preset in (f.get("expressions") or {}).get("optional", []))
    # no character names in the shared v3 code (lower_face.py included by the glob)
    import glob
    ids = [os.path.basename(d) for d in glob.glob(os.path.join(CHARS, "*")) if os.path.isdir(d)]
    hits = []
    for fn in [os.path.join(V3.CHARSYS, "face_generic_v3.py")] + sorted(glob.glob(os.path.join(V3.CHARSYS, "face_v3", "*.py"))):
        low = open(fn).read().lower()
        hits += [f"{os.path.basename(fn)}:{w}" for w in ids + ["boy", "girl"] if w.lower() in low]
    check("shared v3 code names no character", not hits, ", ".join(hits))


def master_for(blender, who):
    m = V3.arg("--" + who)
    if m:
        return m
    spec, ov = V3.CASES[who]
    out = tempfile.mkdtemp(prefix=f"t109_{who}_")
    r = subprocess.run([blender, "-b", "--factory-startup", "-P", os.path.join(V3.CHARSYS, "build_character.py"), "--",
                        "--spec", spec, "--override", ov, "--out", out, "--no-glb", "--no-compare"], capture_output=True, text=True)
    check(f"{who} T-109 candidate builds", r.returncode == 0, r.stderr[-400:] if r.returncode else "")
    sys.argv += ["--" + who, os.path.join(out, next(f for f in os.listdir(out) if f.endswith("_master.blend")))]
    return sys.argv[-1]


def shape(blender, master):
    """(eye/brow data, world vertex coordinates of the head mesh, head-skin mask)."""
    import numpy as np
    probe = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    probe.write(PROBE_SHAPE)
    probe.close()
    npz = tempfile.NamedTemporaryFile(suffix=".npz", delete=False).name
    r = subprocess.run([blender, "-b", "--factory-startup", "-P", probe.name, "--", master, npz], capture_output=True, text=True)
    line = next((l for l in r.stdout.splitlines() if l.startswith("SHAPE ")), None)
    if line is None:
        return None
    d = np.load(npz)
    return json.loads(line[6:]), d["p"], d["head"]


def v4_checks(blender, who, master):
    spec, ov, published, preset = CANDIDATES[who]
    face = json.load(open(os.path.join(os.path.dirname(os.path.abspath(master)), "build_report.json")))["face"]
    lf = (face.get("shape") or {}).get("lower_face") or {}
    check(f"{who}: lower-face options ran", bool(lf.get("cheek_pad_m")) and bool(lf.get("jaw_round_m")), json.dumps(lf))
    import numpy as np
    pa, pb = shape(blender, published), shape(blender, master)
    if pa is None or pb is None:
        check(f"{who}: shape probe ran", False)
        return
    (a, P0, H0), (b, P1, H1) = pa, pb
    ez = a["eyes"]["L"][0][2]
    hb = H0 & (np.abs(P0[:, 2] - ez) < 0.08)
    yc = 0.5 * (P0[hb, 1].min() + P0[hb, 1].max())  # head axis: middle of the head's depth (as lower_face.py)

    def surface(P, H):
        """Largest horizontal distance from the head axis per (3 mm height, 5 deg azimuth) bin of the head skin: the
        surface, independent of the mesh's vertex count (the eye-region refinement follows the shape)."""
        az = np.degrees(np.arctan2(P[:, 0], yc - P[:, 1]))
        key = np.round((P[:, 2] - ez) / 0.003).astype(int) * 1000 + np.round(az / 5.0).astype(int)
        rad = np.hypot(P[:, 0], P[:, 1] - yc)
        out = {}
        for k, r_ in zip(key[H], rad[H]):
            if r_ > out.get(k, -1.0):
                out[k] = r_
        return out
    s0, s1 = surface(P0, H0), surface(P1, H1)
    common = [k for k in s0 if k in s1]
    zb = np.array([k // 1000 if k >= 0 else -((-k + 999) // 1000) for k in common]) * 0.003  # bin height - eye line
    azb = np.array([k - (k // 1000 if k >= 0 else -((-k + 999) // 1000)) * 1000 for k in common]) * 5.0
    d = np.array([s1[k] - s0[k] for k in common])
    low = (zb < -0.03) & (zb > -0.12) & (np.abs(azb) >= 15) & (np.abs(azb) <= 80)  # lower face, front, off the mouth
    full = float(np.percentile(d[low], 95)) * 1000 if low.any() else 0.0
    check(f"{who}: fuller lower face (95th percentile outward move of the lower-face surface >= {LOWER_MIN_MM} mm)",
          full >= LOWER_MIN_MM, f"{full:.2f} mm over {int(low.sum())} bins")
    r_eye = float(V3.SPEC.load(spec, [ov])[0]["face"]["eyes"].get("radius_m", 0.03))
    up = (zb > 1.2 * r_eye) & (np.abs(azb) <= 80)  # above the eyes and their sockets: forehead, brows
    upper = float(np.abs(d[up]).max()) * 1000 if up.any() else 0.0
    wi = int(np.argmax(np.where(up, np.abs(d), -1.0))) if up.any() else 0
    check(f"{who}: face surface above the eyes unchanged (> 1.2 eye radii above the eye line; <= {DRIFT_MM} mm)", upper <= DRIFT_MM,
          f"{upper:.3f} mm (at {zb[wi] * 1000:+.0f} mm from the eye line, {azb[wi]:+.0f} deg)")
    drift = 0.0
    for s_ in "LR":
        drift = max(drift, max(abs(x - y) for x, y in zip(a["eyes"][s_][0], b["eyes"][s_][0])) * 1000,
                    max(abs(x - y) for x, y in zip(a["eyes"][s_][1], b["eyes"][s_][1])) * 1000)
        if s_ in a["brows"]:
            drift = max(drift, max(abs(x - y) for x, y in zip(a["brows"][s_], b["brows"][s_])) * 1000)
    check(f"{who}: no identity drift in eyes or brows (<= {DRIFT_MM} mm)", drift <= DRIFT_MM, f"{drift:.3f} mm")
    if who == "girl":
        ex = face.get("lid_shell_exposed", {})
        lo = max(ex.get("lid_lower.L", 1.0), ex.get("lid_lower.R", 1.0))
        check(f"girl lens shelf: lower lid shell hidden (exposed <= {SHELF_MAX}; 0.12.0 0.509)", lo <= SHELF_MAX, f"{lo}")
        check("girl lower-lid fit ran", set((face.get("lower_fit") or {}).keys()) == {"L", "R"})
    check(f"{who}: {preset} preset built", preset in face.get("presets", []), str(face.get("presets")))


def main():
    plain_v4()
    blender = V3.arg("--blender")
    if blender:
        if "--unit" in sys.argv:
            V3.unit(blender)
        for who in V3.CASES:
            m = master_for(blender, who)
            V3.build_checks(blender, who)
            V3B.lash_check(blender, who, m)
            v4_checks(blender, who, m)
    R = V3.RESULTS
    print(f"[test_face_v4] {'ALL PASS' if all(R) else 'FAIL'} {sum(R)}/{len(R)}")
    return 0 if all(R) else 1


if __name__ == "__main__":
    sys.exit(main())
