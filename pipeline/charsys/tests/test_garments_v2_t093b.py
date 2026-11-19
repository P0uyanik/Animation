"""T-093b: the opt-in crotch arch of ``garment/2`` ``leg_split`` (shorts) and the T-093b candidates.

    python3 pipeline/charsys/tests/test_garments_v2_t093b.py --blender <exe> [--quick]
        [--girl-t093-master <built girl 0.11.0 + T-093 master.blend>]
        [--girl-master <built girl 0.11.0 + T-093b master.blend>]

Checks (each line PASS/FAIL; exit code 1 on any FAIL):
  validate  the T-093b candidate overrides pin garment/2 and validate; leg_split.crotch_lift / arch_width /
            arch_power out of range are rejected; the T-093 candidate carries none of
            them (its output is unchanged: the defaults are neutral).
  neutral   (build) girl + T-093 with the new keys written out at their defaults builds exactly the T-093 shorts
            (vertex hash of every shorts piece).
  arch      (build) girl + T-093b: the hem at the front/back centre rises (the lowest shorts point within 1 cm of the
            centre line is at least 1.5 cm above the T-093 one), a ray along the view axis at the front centre a
            centimetre above the leg hem meets no shorts piece (T-093: it does, the crotch bridge), and the legs
            keep their T-093 hem (outer leg hem height within 3 mm), split gap and pieces.
--quick runs only validate (no builds). The T-093 test (test_garments_v2.py) is unchanged and still covers the
T-093 candidates."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_garments_v2 as T  # noqa: E402  (helpers: build, inspect, check, RESULTS)

CH = T.CH
GIRL = T.GIRL
GIRL_T093 = T.GIRL_OVR
GIRL_T093B = os.path.join(CH, "girl_auburn_bun_glasses", "spec", "candidates", "T-093b",
                          "girl_auburn_bun_glasses.T-093b.override.json")
BOY_T093B = os.path.join(CH, "boy_yellow_hoodie", "spec", "candidates", "T-093b",
                         "boy_yellow_hoodie.T-093b-T090b.override.json")
NEW_KEYS = ("crotch_lift", "arch_width", "arch_power")

VALIDATE = r'''
import copy
import garments_v2 as V2
def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False
girl = json.load(open(%r))["override"]
boy = json.load(open(%r))["override"]
out = []
for label, o in (("girl", girl), ("boy", boy)):
    out.append([f"{label} T-093b candidate pins garment/2", o["generators"]["garment"] == "garment/2"
                and o["clothing"]["generator"] == "garment/2"])
    out.append([f"{label} T-093b candidate clothing validates", V2.validate(copy.deepcopy(o["clothing"])) is not None])
for key, value in (("crotch_lift", 1.2), ("crotch_lift", -0.1), ("arch_width", 0.0), ("arch_power", 9.0)):
    c = copy.deepcopy(girl["clothing"])
    sh = next(g for g in c["garments"] if g["type"] == "shorts")
    sh["leg_split"] = dict(sh["leg_split"], **{key: value})
    out.append([f"leg_split.{key} {value} rejected", raises(lambda: V2.validate(c))])
RESULT["validate"] = out
'''

SHORTS = r'''
import hashlib
from mathutils import Vector
objs = {o.name: o for o in bpy.data.objects if o.name.startswith("garment.shorts.") and o.type == "MESH"}
RESULT["hash"] = {}
for n, o in sorted(objs.items()):
    h = hashlib.sha256()
    for v in o.data.vertices:
        h.update(("%.5f %.5f %.5f;" % tuple(o.matrix_world @ v.co)).encode())
    RESULT["hash"][n] = h.hexdigest()
pts = [o.matrix_world @ v.co for o in objs.values() for v in o.data.vertices]
hem = min(p.z for p in pts)
RESULT["hem"] = hem
RESULT["centre_low"] = min(p.z for p in pts if abs(p.x) < 0.01)
xs = [abs(p.x) for p in pts]
xmax = max(xs)
RESULT["outer_hem"] = min(p.z for p in pts if abs(p.x) > 0.75 * xmax)
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene
hits = {}
for side, d in (("front", 1.0), ("back", -1.0)):
    z = hem + 0.01
    o, k = Vector((0.0, -2.0 * d, z)), []
    while True:  # every surface along the ray (garments, body), nearest first
        ok, loc, n, i, ob, m = sc.ray_cast(dg, o, Vector((0.0, d, 0.0)))
        if not ok or len(k) > 40:
            break
        k.append(ob.name)
        o = loc + Vector((0.0, d * 1e-4, 0.0))
    hits[side] = k
RESULT["hits"] = hits
RESULT["names"] = sorted(objs)
'''


def test_validate(blender):
    r = T.inspect(blender, None, VALIDATE % (GIRL_T093B, BOY_T093B))
    for label, ok in r["validate"]:
        T.check(label, ok)
    t093 = json.load(open(GIRL_T093))["override"]["clothing"]["garments"]
    ls = next(g for g in t093 if g["type"] == "shorts").get("leg_split", {})
    T.check("the T-093 candidate uses none of the new leg_split keys", not any(k in ls for k in NEW_KEYS), ls)


def test_neutral(blender, t093_master):
    o = json.load(open(GIRL_T093))
    sh = next(g for g in o["override"]["clothing"]["garments"] if g["type"] == "shorts")
    sh["leg_split"] = dict(sh["leg_split"], crotch_lift=0.0, arch_width=0.6, arch_power=2.0)
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "neutral.override.json")
        json.dump(o, open(p, "w"))
        neutral = T.inspect(blender, T.build(blender, GIRL, [p], "girl_auburn_bun_glasses"), SHORTS)
    base = T.inspect(blender, t093_master, SHORTS)
    T.check("neutral defaults build exactly the T-093 shorts (every piece, vertex hash)",
            neutral["hash"] == base["hash"], f"{len(base['hash'])} pieces")
    return base


def test_arch(blender, master, base):
    r = T.inspect(blender, master, SHORTS)
    rise = r["centre_low"] - base["centre_low"]
    T.check("the hem rises at the centre line (inverted V, >= 1.5 cm over T-093)", rise >= 0.015,
            f"T-093 {base['centre_low']:.4f} T-093b {r['centre_low']:.4f} (+{rise:.4f} m)")
    shorts = lambda k: [n for n in k if n.startswith("garment.shorts.")]
    T.check("T-093: the front-centre ray above the hem meets the crotch bridge (the one band)",
            bool(shorts(base["hits"]["front"])), base["hits"]["front"][:4])
    for side in ("front", "back"):
        T.check(f"T-093b: the {side}-centre ray a centimetre above the hem meets no shorts piece",
                not shorts(r["hits"][side]), r["hits"][side][:4])
    T.check("the outer leg hem is kept (within 3 mm of T-093)", abs(r["outer_hem"] - base["outer_hem"]) < 0.003,
            f"{base['outer_hem']:.4f} -> {r['outer_hem']:.4f}")
    T.check("same shorts pieces as T-093", r["names"] == sorted(base["hash"]), r["names"])


def main():
    blender = T.arg("--blender", "blender")
    test_validate(blender)
    if "--quick" not in sys.argv:
        t093 = T.arg("--girl-t093-master") or T.build(blender, GIRL, [GIRL_T093], "girl_auburn_bun_glasses")
        base = test_neutral(blender, t093)
        girl = T.arg("--girl-master") or T.build(blender, GIRL, [GIRL_T093B], "girl_auburn_bun_glasses")
        test_arch(blender, girl, base)
    print(f"[test_garments_v2_t093b] {sum(T.RESULTS)}/{len(T.RESULTS)} passed")
    sys.exit(0 if all(T.RESULTS) else 1)


if __name__ == "__main__":
    main()
