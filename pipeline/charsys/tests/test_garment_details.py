"""T-068: garment detail types of ``garment/1`` (sneakers, backpack, hood volume, closed armhole, vest patch pockets,
cross-stitch decals, gathered skirt with hem rib).

    python3 pipeline/charsys/tests/test_garment_details.py --blender <exe>
        [--boy-master <built boy 2.0.0-dev + T-068 candidate master.blend>]
        [--vest-master <girl + vest candidate>] [--dress-master <girl + gathered dress demo>]

Validation (inside Blender, the generator imports bpy): the T-068 candidate clothing blocks validate, bad values of
every new option are rejected, and the options are refused on item types that do not support them. Build checks on
the candidate masters (built from docs/evaluation/characters/T-068/candidates/ unless given):
  sneakers  every part per foot (upper, sole, toe cap, laces, collar, tongue); the sole is under the upper, the toe
            cap at the front, the collar around the ankle; the covered foot is masked
  backpack  bag, pocket, zips, pullers, handle, two straps; the bag lies on the back outside the hoodie; each strap
            crosses its shoulder and shows on the front of the chest; strap weights come only from torso bones
  hoodie    the full hood bag is deep (not collapsed); the closed armhole leaves no skin visible under the arm
  vest      patch pockets in front of the vest with rolled top edges; the cross-stitch decals exist
  dress     the hem rib band exists and wraps the skirt's lower edge; the skirt hem has gathers (radial folds)
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
CAND = os.path.join(ROOT, "docs", "evaluation", "characters", "T-068", "candidates")
BOY = os.path.join(ROOT, "assets", "characters", "boy_yellow_hoodie", "spec", "boy_yellow_hoodie.2.0.0-dev.spec.json")
GIRL_DIR = os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "spec")
GIRL = os.path.join(GIRL_DIR, "girl_auburn_bun_glasses.spec.json")
GIRL_OVR = os.path.join(GIRL_DIR, "girl_auburn_bun_glasses.0.10.0.override.json")
RESULTS = []


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_garment_details] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"))


def build(blender, spec, overrides, cid):
    out = tempfile.mkdtemp(prefix="t068_")
    cmd = [blender, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "build_character.py"), "--", "--spec", spec,
           "--out", out, "--no-glb", "--no-compare"]
    for o in overrides:
        cmd += ["--override", o]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.join(out, f"{cid}_master.blend")


def inspect(blender, blend, script):
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "probe.py"), os.path.join(tmp, "out.json")
        head = "bpy.ops.wm.open_mainfile(filepath=%r)\n" % blend if blend else ""
        open(src, "w").write("import bpy, json, sys\nsys.path.insert(0, %r)\n%sRESULT = {}\n%s\njson.dump(RESULT, open(%r, 'w'))\n"
                             % (CHARSYS, head, script, out))
        subprocess.run([blender, "-b", "--factory-startup", "-P", src, "--"], check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return json.load(open(out))


VALIDATE = r'''
import copy
from garments import generator as gen
def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False
def ovr(name):
    return json.load(open(%r + "/" + name))["override"]["clothing"]
boy, vest, dress = ovr("boy_2.0.0-dev.garment_details.override.json"), ovr("girl.vest_details.override.json"), \
    ovr("girl.gathered_dress.override.json")
out = [["boy candidate clothing validates", gen.validate(copy.deepcopy(boy)) is not None],
       ["vest candidate clothing validates", gen.validate(copy.deepcopy(vest)) is not None],
       ["gathered dress demo validates", gen.validate(copy.deepcopy(dress)) is not None]]
def bad(base, typ, path, value, label):
    c = copy.deepcopy(base)
    item = next(g for g in c["garments"] if g["type"] == typ)
    node = item
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value
    out.append([label, raises(lambda: gen.validate(c))])
bad(boy, "sneakers", ("sole", "thickness_m"), -0.01, "sneakers.sole.thickness_m < 0 rejected")
bad(boy, "sneakers", ("laces", "count"), 40, "sneakers.laces.count 40 rejected")
bad(boy, "sneakers", ("plan_n",), 9.0, "sneakers.plan_n 9 rejected")
bad(boy, "sneakers", ("opening",), False, "sneakers.opening false rejected")
bad(boy, "sneakers", ("toe_cap",), "yes", "sneakers.toe_cap must be an object or false")
bad(boy, "backpack", ("width_m",), 2.0, "backpack.width_m 2 rejected")
bad(boy, "backpack", ("straps", "shoulder"), 1.5, "backpack.straps.shoulder 1.5 rejected")
bad(boy, "backpack", ("mask_body",), True, "backpack.mask_body rejected")
bad(boy, "hoodie", ("hood", "bag_fullness"), 1.5, "hoodie.hood.bag_fullness 1.5 rejected")
bad(boy, "hoodie", ("hood", "bag_n"), 0.5, "hoodie.hood.bag_n 0.5 rejected")
bad(boy, "hoodie", ("armhole",), "open", "hoodie.armhole 'open' rejected")
bad(boy, "trousers", ("armhole",), "closed", "armhole on trousers rejected")
bad(vest, "vest", ("pockets", "shape"), "round", "vest.pockets.shape 'round' rejected")
bad(vest, "vest", ("pockets", "corner"), 2.0, "vest.pockets.corner 2 rejected")
c = copy.deepcopy(vest)
next(g for g in c["garments"] if g["type"] == "vest")["embroidery"]["motifs"][0]["pattern"] = ["xx", "x"]
out.append(["cross_stitch pattern rows of unequal length rejected", raises(lambda: gen.validate(c))])
c = copy.deepcopy(vest)
next(g for g in c["garments"] if g["type"] == "vest")["embroidery"]["motifs"][0]["pattern"] = ["x#x"]
out.append(["cross_stitch pattern with an unknown character rejected", raises(lambda: gen.validate(c))])
bad(dress, "dress", ("gathers", "count"), 2, "gathers.count 2 rejected")
bad(dress, "dress", ("gathers", "depth_m"), 0.2, "gathers.depth_m 0.2 rejected")
bad(dress, "dress", ("bands", "hem_rib", "ridges"), 1000, "hem_rib.ridges 1000 rejected")
bad(vest, "vest", ("gathers",), {"count": 8}, "gathers on a vest rejected")
bad(vest, "shorts", ("bands", "hem_rib"), {"height_m": 0.02}, "hem_rib on shorts rejected")
RESULT["validate"] = out
''' % CAND


BOY_PROBE = r'''
from mathutils import Vector
from mathutils.bvhtree import BVHTree
objs = {o.name: o for o in bpy.data.objects if o.name.startswith("garment.") and o.type == "MESH"}
RESULT["names"] = sorted(objs)
def bb(o):
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]
RESULT["bbox"] = {k: bb(o) for k, o in objs.items()}
RESULT["materials"] = {k: [m.name for m in o.data.materials if m] for k, o in objs.items()}
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
RESULT["shoulders"] = {s: list(rig.matrix_world @ rig.data.bones["DEF-upper_arm." + s].head_local) for s in "LR"}
RESULT["ankles"] = {s: list(rig.matrix_world @ rig.data.bones["DEF-foot." + s].head_local) for s in "LR"}
groups = {}
for s in "LR":
    o = objs["garment.backpack.strap." + s]
    names = set()
    for v in o.data.vertices:
        for g in v.groups:
            if g.weight > 1e-4:
                names.add(o.vertex_groups[g.group].name)
    groups[s] = sorted(n for n in names if not n.startswith("ps_"))
RESULT["strap_groups"] = groups
body = next(o for o in bpy.data.objects if o.type == "MESH" and o.modifiers.get("garment_body_mask"))
RESULT["mask_items"] = list(body.get("ps_garment_mask_items", []))
# underarm: rays from the rest-pose armpit area of the body outwards must hit the hoodie
dg = bpy.context.evaluated_depsgraph_get()
main = objs["garment.hoodie.main"]
tree = BVHTree.FromPolygons([main.matrix_world @ v.co for v in main.data.vertices], [tuple(p.vertices) for p in main.data.polygons])
misses = 0
total = 0
sh_z = RESULT["shoulders"]["L"][2]
for v in body.data.vertices:
    co = body.matrix_world @ v.co
    if sh_z - 0.09 < co.z < sh_z - 0.01 and 0.07 < abs(co.x) < 0.13 and abs(co.y) < 0.04:
        n = (body.matrix_world.to_3x3() @ v.normal).normalized()
        if abs(n.x) < 0.5:
            continue
        total += 1
        if tree.ray_cast(co + n * 0.001, n, 0.08)[0] is None:
            misses += 1
RESULT["underarm"] = [misses, total]
'''

GIRL_PROBE = r'''
objs = {o.name: o for o in bpy.data.objects if o.name.startswith("garment.") and o.type == "MESH"}
RESULT["names"] = sorted(objs)
def bb(o):
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]
RESULT["bbox"] = {k: bb(o) for k, o in objs.items()}
RESULT["verts"] = {k: len(o.data.vertices) for k, o in objs.items()}
import math
sk = objs.get("garment.dress.skirt")
if sk is not None:
    pts = [sk.matrix_world @ v.co for v in sk.data.vertices]
    zmin = min(p.z for p in pts)
    hem = [p for p in pts if p.z < zmin + 0.004]
    cx = sum(p.x for p in hem) / len(hem)
    cy = sum(p.y for p in hem) / len(hem)
    # radial spread inside narrow angular sectors (a gathered hem has folds: big local variation)
    sectors = {}
    for p in hem:
        a = int((math.atan2(p.y - cy, p.x - cx) + math.pi) / (2 * math.pi) * 180) % 180
        sectors.setdefault(a // 6, []).append(math.hypot(p.x - cx, p.y - cy))
    RESULT["hem_fold_m"] = max(max(r) - min(r) for r in sectors.values() if r)
'''


def main():
    blender = arg("--blender")
    if not blender:
        print("[test_garment_details] needs --blender (the garment generator imports bpy)")
        sys.exit(2)
    for name, ok in inspect(blender, None, VALIDATE)["validate"]:
        check(name, ok)
    boy = arg("--boy-master") or build(blender, BOY, [os.path.join(CAND, "boy_2.0.0-dev.garment_details.override.json")],
                                       "boy_yellow_hoodie")
    r = inspect(blender, os.path.abspath(boy), BOY_PROBE)
    n, bb = set(r["names"]), r["bbox"]
    for s in "LR":
        for part in ("main", "sole", "toe_cap", "collar", "tongue"):
            check(f"sneakers {part}.{s}", f"garment.shoes.{part}.{s}" in n)
        check(f"sneakers laces.{s}", any(x.startswith(f"garment.shoes.laces.{s}_") for x in n))
        up, sole, cap = bb[f"garment.shoes.main.{s}"], bb[f"garment.shoes.sole.{s}"], bb[f"garment.shoes.toe_cap.{s}"]
        check(f"sneaker sole under the upper ({s})", sole[0][2] < up[0][2] and sole[1][2] < up[1][2] * 0.6,
              (sole, up))
        check(f"toe cap at the front ({s})", cap[0][1] <= up[0][1] + 0.003 and cap[1][1] < (up[0][1] + up[1][1]) * 0.5,
              (cap, up))
        col = bb[f"garment.shoes.collar.{s}"]
        ank = r["ankles"][s]
        check(f"collar around the ankle ({s})", col[0][0] < ank[0] < col[1][0] and col[0][1] < ank[1] + 0.02 < col[1][1] + 0.04,
              (col, ank))
    check("sneakers mask the covered foot", "shoes" in r["mask_items"], r["mask_items"])
    for part in ("main", "pocket", "zip.main", "zip.pocket", "zip.puller.main", "zip.puller.pocket", "handle",
                 "strap.L", "strap.R"):
        check(f"backpack {part}", f"garment.backpack.{part}" in n)
    check("every T-068 part has a material", all(r["materials"][k] for k in n if ".shoes." in k or ".backpack." in k))
    hood_main = bb["garment.hoodie.main"]
    check("bag on the back, outside the hoodie", bb["garment.backpack.main"][0][1] > 0.0 and
          bb["garment.backpack.main"][1][1] > hood_main[1][1], (bb["garment.backpack.main"], hood_main[1]))
    for s, sx in (("L", 1), ("R", -1)):
        st = bb[f"garment.backpack.strap.{s}"]
        sh = r["shoulders"][s]
        check(f"strap {s} crosses the shoulder", st[1][2] > sh[2] and st[0][1] < -0.03 and st[1][1] > 0.03, (st, sh))
        check(f"strap {s} on its own side", (st[0][0] > 0) if sx > 0 else (st[1][0] < 0), st)
        arm = [g for g in r["strap_groups"][s] if any(k in g for k in ("arm", "hand", "neck", "head", "thigh", "shin"))]
        check(f"strap {s} weights only from torso bones", not arm, r["strap_groups"][s])
    hb = bb["garment.hoodie.hood.bag"]
    check("hood bag is full (depth > 4 cm)", hb[1][1] - hb[0][1] > 0.04, hb)
    misses, total = r["underarm"]
    check("closed armhole: no skin visible under the arm", total > 0 and misses <= 0.02 * total, r["underarm"])
    vest = arg("--vest-master") or build(blender, GIRL, [GIRL_OVR, os.path.join(CAND, "girl.vest_details.override.json")],
                                         "girl_auburn_bun_glasses")
    r = inspect(blender, os.path.abspath(vest), GIRL_PROBE)
    n, bb = set(r["names"]), r["bbox"]
    for s in "LR":
        check(f"vest patch pocket.{s} with a rolled top edge", f"garment.vest.pocket.{s}" in n and
              f"garment.vest.pocket_edge.{s}" in n)
        check(f"patch pocket.{s} lies in front of the vest", bb[f"garment.vest.pocket.{s}"][0][1] <
              bb["garment.vest.main"][0][1] + 0.02 and bb[f"garment.vest.pocket.{s}"][1][1] < 0)
    check("cross-stitch decals built", r["verts"].get("garment.vest.embroidery", 0) > 1000 and
          r["verts"].get("garment.vest.embroidery_accent", 0) > 1000, {k: v for k, v in r["verts"].items() if "embro" in k})
    dress = arg("--dress-master") or build(blender, GIRL, [GIRL_OVR, os.path.join(CAND, "girl.gathered_dress.override.json")],
                                           "girl_auburn_bun_glasses")
    r = inspect(blender, os.path.abspath(dress), GIRL_PROBE)
    n, bb = set(r["names"]), r["bbox"]
    check("dress hem rib band", "garment.dress.band.hem_rib" in n)
    if "garment.dress.band.hem_rib" in n:
        rb, sk = bb["garment.dress.band.hem_rib"], bb["garment.dress.skirt"]
        check("hem rib wraps the skirt's lower edge", rb[0][2] <= sk[0][2] + 0.002 and rb[1][2] < sk[0][2] + 0.05,
              (rb, sk))
    check("gathered hem (radial folds >= 3 mm)", r.get("hem_fold_m", 0) >= 0.003, r.get("hem_fold_m"))
    ok = all(RESULTS)
    print(f"[test_garment_details] {'ALL PASS' if ok else 'FAIL'} ({sum(RESULTS)}/{len(RESULTS)})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
