"""T-058: the shared hoodie garment type (garment/1, garments/hoodie.py).

    python3 pipeline/charsys/tests/test_hoodie.py --blender <exe> [--master <built boy 2.0.0-dev master.blend>]

Validation (no Blender): the type is accepted, its options are checked, bad values fail. With --blender: on the boy
2.0.0-dev build the hoodie has its parts (main with sleeves to the wrist, hood rim and bag, kangaroo pocket with
openings, two drawstrings with tips, rib ridges on hem and cuffs), every part has a material, the hood bag lies on the
back, the pocket and cords lie in front of the main shell, and the shoulders are covered (dropped shoulder)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import test_boy2_face as T  # noqa: E402  (shared build/probe helpers)

RESULTS = []


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_hoodie] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"))


def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


PROBE = r'''
from mathutils import Vector
objs = {o.name: o for o in bpy.data.objects if o.name.startswith("garment.hoodie") and o.type == "MESH"}
RESULT["names"] = sorted(objs)
def bb(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]
RESULT["bbox"] = {k: bb(o) for k, o in objs.items()}
RESULT["materials"] = {k: [m.name for m in o.data.materials if m] for k, o in objs.items()}
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
RESULT["shoulders"] = {s: list(rig.matrix_world @ rig.data.bones["DEF-upper_arm." + s].head_local) for s in ("L", "R")}
RESULT["wrists"] = {s: list(rig.matrix_world @ rig.data.bones["DEF-hand." + s].head_local) for s in ("L", "R")}
main = objs["garment.hoodie.main"]
from mathutils.bvhtree import BVHTree
dg = bpy.context.evaluated_depsgraph_get()
tree = BVHTree.FromObject(main, dg)
cover = {}
for s, sx in (("L", 1), ("R", -1)):
    p = Vector(RESULT["shoulders"][s])
    hit = tree.ray_cast(p + Vector((0, 0, 0.3)), Vector((0, 0, -1)), 0.5)
    cover[s] = hit[0] is not None and hit[0].z > p.z
RESULT["shoulder_covered"] = cover
'''


VALIDATE = r'''
import copy, sys
sys.path.insert(0, %r)
from garments import generator as gen
clothing = json.load(open(%r))["clothing"]
def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False
out = [["boy 2.0 clothing validates with a hoodie", gen.validate(copy.deepcopy(clothing)) is not None]]
for path, bad in ((("hood", "rim_radius_m"), -0.1), (("pocket", "height_m"), 3.0), (("drawstrings", "length_m"), "long"),
                  (("dropped_shoulder", "start"), 0.5), (("bands", "cuff_rib_ridges"), 40)):
    c = copy.deepcopy(clothing)
    item = next(g for g in c["garments"] if g["type"] == "hoodie")
    item.setdefault(path[0], {})
    item[path[0]][path[1]] = bad
    out.append([f"hoodie.{'.'.join(path)} = {bad!r} rejected", raises(lambda c=c: gen.validate(c))])
c = copy.deepcopy(clothing)
next(g for g in c["garments"] if g["type"] == "hoodie")["pocket"] = "yes"
out.append(["hoodie.pocket must be an object or false", raises(lambda: gen.validate(c))])
c = copy.deepcopy(clothing)
next(g for g in c["garments"] if g["type"] == "hoodie")["type"] = "parka"
out.append(["unknown garment type still rejected", raises(lambda: gen.validate(c))])
RESULT["validate"] = out
''' % (T.CHARSYS, T.SPEC)


def main():
    blender = T.arg("--blender")
    if not blender:
        print("[test_hoodie] needs --blender (the garment generator imports bpy)")
        sys.exit(2)
    for name, ok in T.inspect(blender, None, VALIDATE)["validate"]:
        check(name, ok)
    if blender:
        r = T.inspect(blender, T.master(blender), PROBE)
        n = r["names"]
        for part in ("main", "hood.rim", "hood.bag", "pocket", "pocket.opening.L", "pocket.opening.R",
                     "drawstring.L", "drawstring.R", "drawstring.tip.L", "drawstring.tip.R", "band.hem",
                     "band.cuff.L", "band.cuff.R"):
            check(f"part {part}", f"garment.hoodie.{part}" in n)
        check("rib ridges on hem and both cuffs", any(".rib.hem_" in x for x in n) and
              any(".rib.cuff.L_" in x for x in n) and any(".rib.cuff.R_" in x for x in n))
        check("every part has a material", all(r["materials"][k] for k in n), [k for k in n if not r["materials"][k]])
        bb = r["bbox"]
        main_lo, main_hi = bb["garment.hoodie.main"]
        check("hood bag on the back", bb["garment.hoodie.hood.bag"][1][1] > main_hi[1] * 0.8, bb["garment.hoodie.hood.bag"])
        check("pocket in front of the main shell", bb["garment.hoodie.pocket"][0][1] <= main_lo[1] + 0.002,
              (bb["garment.hoodie.pocket"][0][1], main_lo[1]))
        check("drawstrings hang in front and below the neckline",
              all(bb[f"garment.hoodie.drawstring.{s}"][0][1] < -0.05 and bb[f"garment.hoodie.drawstring.{s}"][0][2]
                  < bb["garment.hoodie.hood.rim"][0][2] + 0.02 for s in "LR"))
        reach = all(abs(main_hi[0]) >= abs(r["wrists"][s][0]) - 0.03 for s in "LR")
        check("sleeves reach the wrists", reach, (main_hi[0], r["wrists"]))
        check("shoulders covered (dropped shoulder)", all(r["shoulder_covered"].values()), r["shoulder_covered"])
    else:
        print("[test_hoodie] (no --blender: build checks skipped)")
    ok = all(RESULTS)
    print(f"[test_hoodie] {'ALL PASS' if ok else 'FAIL'} ({sum(RESULTS)}/{len(RESULTS)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
