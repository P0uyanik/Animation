"""T-093: ``garment/2`` (garment outlines and accessories) and its reach correctives.

    python3 pipeline/charsys/tests/test_garments_v2.py --blender <exe> [--quick]
        [--boy-master <built boy 2.0.0 + T-093 candidate master.blend>]
        [--girl-master <built girl 0.11.0 + T-093 candidate master.blend>] [--girl-base-master <girl 0.11.0>]
        [--boy-base-master <boy 2.0.0>]

Checks (each line PASS/FAIL; exit code 1 on any FAIL):
  pin       garment/2 is registered and loads garments_v2, which declares it (GENERATOR_VERSIONS); the published specs
            still pin garment/1; both T-093 candidate overrides pin garment/2 and set clothing.generator garment/2.
  validate  the candidate clothing blocks validate; garment/2 fields are refused on item types that do not take them
            and bad values are rejected; garment/1 refuses a garment/2 block; candidate overrides keep every
            published garment `material` entry (except the backpack colour, the one documented B06 change).
  garment/1 unchanged (criterion 4): the published boy 2.0.0 clothing, relabelled garment/2 without any new field,
            builds exactly the garment/1 geometry (per-object vertex hash) - garment/2 reuses garment/1 by import -
            and no file of pipeline/charsys/garments differs from the merge base with origin/main (when git is there).
  boy       candidate pieces: stripes on both uppers (outside the shoe, on its side walls), flap above the pocket on the
            outer face of the bag, tab and buckle on the flap's centre line, pocket flap on the pocket, no zips;
            the trouser legs separate higher than in 2.0.0 (gusset); the trouser hem reaches the shoe.
  girl      rolled cuff on both boots (proud of the shaft, over its rim); split bloomer legs (gap between the inner
            surfaces below the crotch); one flower on the bun.
  corrective (criterion 3): corrective.reach.L/R exist on the vest with drivers; arms down (compare rotation) keeps
            them at 0; in the reach pose they reach 1. Round 2: the vest flare in reach (max / p99 distance to the
            posed torso skin; arm-weight cap + keys) is below 0.11.0's and within 1 cm of rest; the driven keys reduce
            the vest's penetration into the blouse against the muted keys, and it is below 0.11.0's; no penetration
            at rest; no fibres on the collar or the vest edges.
--quick runs only pin + validate (no builds)."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(CHARSYS, "..", ".."))
CH = os.path.join(ROOT, "assets", "characters")
BOY = os.path.join(CH, "boy_yellow_hoodie", "spec", "boy_yellow_hoodie.2.0.0.spec.json")
GIRL = os.path.join(CH, "girl_auburn_bun_glasses", "spec", "girl_auburn_bun_glasses.0.11.0.spec.json")
BOY_OVR = os.path.join(CH, "boy_yellow_hoodie", "spec", "candidates", "T-093", "boy_yellow_hoodie.T-093.override.json")
GIRL_OVR = os.path.join(CH, "girl_auburn_bun_glasses", "spec", "candidates", "T-093",
                        "girl_auburn_bun_glasses.T-093.override.json")
RESULTS = []


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(name, ok, detail=None):
    RESULTS.append(bool(ok))
    print(f"[test_garments_v2] {'PASS' if ok else 'FAIL'} {name}" + ("" if detail is None else f" {detail}"),
          flush=True)


def build(blender, spec, overrides, cid, compare=False):
    out = tempfile.mkdtemp(prefix="t093_")
    cmd = [blender, "-b", "--factory-startup", "-P", os.path.join(CHARSYS, "build_character.py"), "--", "--spec", spec,
           "--out", out, "--no-glb"] + ([] if compare else ["--no-compare"])
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


def test_pin():
    sys.path.insert(0, CHARSYS)
    import versions as V
    e = V.REGISTRY.entry("garment", "garment/2")
    check("garment/2 is registered to the garments_v2 module", e["module"] == "garments_v2", e["module"])
    src = open(os.path.join(CHARSYS, "garments_v2", "__init__.py")).read()
    check("garments_v2 declares garment/2", 'GENERATOR_VERSIONS = ("garment/2",)' in src)
    for path in (BOY, GIRL):
        spec = json.load(open(path))
        check(f"published {os.path.basename(path)} still pins garment/1",
              spec["generators"]["garment"] == "garment/1" and spec["clothing"]["generator"] == "garment/1")
    for path in (BOY_OVR, GIRL_OVR):
        o = json.load(open(path))["override"]
        check(f"{os.path.basename(path)} pins garment/2",
              o["generators"]["garment"] == "garment/2" and o["clothing"]["generator"] == "garment/2")
    # the candidate resolves to garment/2 through the shared pin rules
    import spec as SPEC
    for base, ovr in ((BOY, BOY_OVR), (GIRL, GIRL_OVR)):
        merged = SPEC.deep_merge(json.load(open(base)), json.load(open(ovr))["override"]) \
            if hasattr(SPEC, "deep_merge") else None
        if merged is not None:
            pins, _ = V.resolve_pins(merged)
            check(f"{os.path.basename(ovr)} resolves garment/2", pins["garment"] == "garment/2", pins["garment"])
    # every published garment `material` entry is kept (T-092 owns them; T-094 combines field by field)
    for base, ovr in ((BOY, BOY_OVR), (GIRL, GIRL_OVR)):
        pub = {g["name"]: g.get("material") for g in json.load(open(base))["clothing"]["garments"]}
        cand = {g["name"]: g.get("material") for g in json.load(open(ovr))["override"]["clothing"]["garments"]}
        changed = sorted(n for n in pub if pub[n] != cand.get(n))
        check(f"{os.path.basename(ovr)} keeps the published garment material entries (backpack colour excepted)",
              set(pub) == set(cand) and changed in ([], ["backpack"]), changed)
        if changed == ["backpack"]:
            a, b = pub["backpack"], cand["backpack"]
            check("backpack: only base_color_srgb differs (B06 navy)",
                  {k: v for k, v in a.items() if k != "base_color_srgb"} ==
                  {k: v for k, v in b.items() if k != "base_color_srgb"})
    # git: no garment/1 file differs from the merge base with origin/main
    try:
        base = subprocess.run(["git", "-C", ROOT, "merge-base", "HEAD", "origin/main"], check=True,
                              capture_output=True, text=True).stdout.strip()
        diff = subprocess.run(["git", "-C", ROOT, "diff", "--name-only", base, "--", "pipeline/charsys/garments"],
                              check=True, capture_output=True, text=True).stdout.split()
        check("pipeline/charsys/garments unchanged against the merge base with origin/main", not diff, diff)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[test_garments_v2] SKIP git check (no origin/main here)")


VALIDATE = r'''
import copy
import garments_v2 as V2
from garments import generator as G1
def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False
boy = json.load(open(%r))["override"]["clothing"]
girl = json.load(open(%r))["override"]["clothing"]
out = [["boy candidate clothing validates (garment/2)", V2.validate(copy.deepcopy(boy)) is not None],
       ["girl candidate clothing validates (garment/2)", V2.validate(copy.deepcopy(girl)) is not None],
       ["garment/1 refuses a garment/2 block", raises(lambda: G1.validate(copy.deepcopy(boy)))],
       ["garment/2 refuses a garment/1 block", raises(lambda: V2.validate(dict(copy.deepcopy(boy), generator="garment/1")))]]
v1 = V2.v1_view(boy)
out.append(["the garment/1 view drops every garment/2 field",
            not any(f in g for g in v1["garments"] for f in V2.core.V2_FIELDS) and v1["generator"] == "garment/1"])
gv1 = V2.v1_view(girl)
boots = next(g for g in gv1["garments"] if g["type"] == "boots")
out.append(["a boot with cuff_roll drops its garment/1 cuff tube", boots.get("cuff") is False and boots["bands"]["cuff"] is False])
def bad(base, typ, path, value, label):
    c = copy.deepcopy(base)
    item = next(g for g in c["garments"] if g["type"] == typ)
    node = item
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value
    out.append([label, raises(lambda: V2.validate(c))])
bad(boy, "sneakers", ("stripes", "count"), 9, "stripes.count 9 rejected")
bad(boy, "sneakers", ("stripes", "z_range"), [0.8, 0.2], "stripes.z_range reversed rejected")
bad(boy, "sneakers", ("stripes", "sides"), "inner", "stripes.sides 'inner' rejected")
bad(boy, "backpack", ("flap", "drop"), 2.0, "flap.drop 2 rejected")
bad(boy, "backpack", ("flap", "colour"), 1, "flap unknown field rejected")
bad(boy, "backpack", ("tab", "buckle_m"), 0.5, "tab.buckle_m 0.5 rejected")
bad(boy, "trousers", ("hem_break", "folds"), 1.5, "hem_break.folds 1.5 rejected")
bad(boy, "trousers", ("hem_break", "flare_m"), 0.5, "hem_break.flare_m 0.5 rejected")
bad(boy, "hoodie", ("stripes",), {}, "stripes on a hoodie rejected")
bad(boy, "trousers", ("cuff_roll",), {}, "cuff_roll on trousers rejected")
bad(boy, "backpack", ("correctives",), {"reach": {}}, "correctives on a backpack rejected")
bad(girl, "boots", ("cuff_roll", "height_m"), 0.5, "cuff_roll.height_m 0.5 rejected")
bad(girl, "shorts", ("leg_split", "amount"), 1.5, "leg_split.amount 1.5 rejected")
bad(girl, "vest", ("correctives", "reach", "gate"), 1.0, "correctives.reach.gate 1 rejected")
bad(girl, "vest", ("correctives", "reach", "arm_bone"), "DEF-upper_arm.L", "arm_bone without {side} rejected")
bad(girl, "vest", ("correctives", "twist"), {}, "unknown corrective rejected")
bad(girl, "vest", ("correctives", "reach", "arm_hi"), 0.2, "arm_hi below arm_lo rejected")
bad(girl, "vest", ("correctives", "arm_weights", "cap"), 1.5, "arm_weights.cap 1.5 rejected")
bad(girl, "vest", ("correctives", "arm_weights", "to"), "DEF-shoulder.L", "arm_weights.to without {side} rejected")
bad(girl, "vest", ("correctives", "reach", "over"), "blouse", "reach.over must be a list")
bad(girl, "vest", ("clean_fibres",), [], "empty clean_fibres rejected")
bad(girl, "top", ("collar_clear", "over"), [], "collar_clear.over empty rejected")
bad(girl, "top", ("collar_clear", "max_lift_m"), 0.5, "collar_clear.max_lift_m 0.5 rejected")
bad(girl, "vest", ("collar_clear",), {"over": ["blouse"]}, "collar_clear on a vest rejected")
bad(girl, "shorts", ("hem_break", "pleats"), 2.5, "hem_break.pleats 2.5 rejected")
bad(boy, "backpack", ("tab", "buckle"), "zip", "tab.buckle 'zip' rejected")
bad(boy, "backpack", ("flap", "edge_m"), 0.5, "flap.edge_m 0.5 rejected")
RESULT["validate"] = out
import versions
mod = versions.load("garment", "garment/2")
RESULT["load"] = [mod.__name__, list(getattr(mod, "GENERATOR_VERSIONS", ()))]
''' % (BOY_OVR, GIRL_OVR)


HASH = r'''
import hashlib
out = {}
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type == "MESH" and o.name.startswith("garment.") and "ps_garment_item" in o:
        h = hashlib.sha256()
        for v in o.data.vertices:
            h.update(("%.5f %.5f %.5f;" % tuple(o.matrix_world @ v.co)).encode())
        out[o.name] = [len(o.data.vertices), h.hexdigest(), o.get("ps_garment_generator")]
RESULT["garments"] = out
RESULT["report"] = None
'''

BOY_PROBE = r'''
from mathutils import Vector
objs = {o.name: o for o in bpy.data.objects if o.name.startswith("garment.") and o.type == "MESH"}
RESULT["names"] = sorted(objs)
def bb(o):
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]
RESULT["bbox"] = {k: bb(o) for k, o in objs.items()}
RESULT["gen"] = sorted({o.get("ps_garment_generator") for o in objs.values() if "ps_garment_item" in o})
gus = objs.get("garment.trousers.gusset")
RESULT["gusset_bottom"] = bb(gus)[0][2] if gus else None
'''

GIRL_PROBE = r'''
import math
from mathutils import Vector
sys.path.insert(0, %r)
from garments_v2 import evaluate as EV
objs = {o.name: o for o in bpy.data.objects if o.name.startswith("garment.") and o.type == "MESH"}
RESULT["names"] = sorted(objs)
def bb(o):
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]
RESULT["bbox"] = {k: bb(o) for k, o in objs.items()}
sh = objs["garment.shorts.main"]
pts = [sh.matrix_world @ v.co for v in sh.data.vertices]
lo = min(p.z for p in pts); hi = max(p.z for p in pts)
z = lo + 0.06 * (hi - lo)  # just above the hem: 0.11.0's bloomer shell crosses the centre here (gap 0)
band = [p for p in pts if abs(p.z - z) < 0.003 and abs(p.y) < 0.015]
RESULT["split"] = {"z": z, "inner_L": min((p.x for p in band if p.x > 0), default=None),
                   "inner_R": max((p.x for p in band if p.x < 0), default=None)}
fl = [o for o in bpy.data.objects if "flower" in o.name.lower() and o.type == "MESH"]
RESULT["flowers"] = {o.name: len(o.data.polygons) for o in fl}
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.name.startswith("body_skin") and o.type == "MESH")
vest = [o for o in bpy.data.objects if o.get("ps_garment_item") == "vest" and o.type == "MESH"]
main = objs["garment.vest.main"]
keys = EV.corrective_keys(vest)
RESULT["keys"] = sorted({k.name for _, k in keys})
RESULT["drivers"] = sorted({k.name for ob, k in keys
                            if ob.data.shape_keys.animation_data and any(d.data_path == 'key_blocks["%%s"].value' %% k.name
                                                                          for d in ob.data.shape_keys.animation_data.drivers)})
blouse = [o for o in bpy.data.objects if o.get("ps_garment_item") == "blouse" and o.get("ps_garment_part") == "main"]
RESULT["rest"] = {"values": EV.key_values(vest), "flare": EV.flare(body, main), "pen": EV.penetration(main, blouse)}
EV.rotate_upper_arms(rig, 35.0, axis="Y", mirror=True)  # the compare variant's arms-down rotation
RESULT["arms_down"] = {"values": EV.key_values(vest)}
EV.rest(rig)
EV.rotate_upper_arms(rig, -75.0, axis="X")  # reach
RESULT["reach"] = {"values": EV.key_values(vest)}
EV.mute(vest, True)
RESULT["reach"]["before"] = EV.flare(body, main)
RESULT["reach"]["pen_before"] = EV.penetration(main, blouse)
EV.mute(vest, False)
RESULT["reach"]["after"] = EV.flare(body, main)
RESULT["reach"]["pen_after"] = EV.penetration(main, blouse)
col = objs.get("garment.blouse.collar")
RESULT["collar_fibres"] = len([c for c in col.children if c.get("ps_fibres_source") == col.name]) if col else None
RESULT["edge_fibres"] = sum(len([c for c in o.children if c.get("ps_fibres_source") == o.name])
                            for o in vest if o.get("ps_garment_part") in ("edge", "pocket_edge"))
''' % CHARSYS


def test_validate(blender):
    r = inspect(blender, None, VALIDATE)
    for label, ok in r["validate"]:
        check(label, ok)
    check("versions.load('garment', 'garment/2') loads garments_v2 declaring garment/2",
          r["load"][0] == "garments_v2" and "garment/2" in r["load"][1], r["load"])


def test_v1_parity(blender):
    """The published boy clothing relabelled garment/2 (no new field) builds exactly the garment/1 geometry."""
    spec = json.load(open(BOY))
    cl = dict(spec["clothing"], generator="garment/2")
    with tempfile.TemporaryDirectory() as tmp:
        ovr = os.path.join(tmp, "relabel.override.json")
        json.dump({"override": {"generators": {"garment": "garment/2"}, "clothing": cl}}, open(ovr, "w"))
        v1 = inspect(blender, build(blender, BOY, [], "boy_yellow_hoodie"), HASH)["garments"]
        v2 = inspect(blender, build(blender, BOY, [ovr], "boy_yellow_hoodie"), HASH)["garments"]
    same = sorted(v1) == sorted(v2) and all(v1[k][:2] == v2[k][:2] for k in v1)
    check("garment/2 without new fields builds the garment/1 geometry (every piece, vertex hash)", same,
          f"{len(v1)} pieces; differing: {[k for k in v1 if k in v2 and v1[k][:2] != v2[k][:2]][:5]}")
    check("pieces are tagged with their generator", {x[2] for x in v1.values()} == {"garment/1"} and
          {x[2] for x in v2.values()} == {"garment/2"})


def test_boy(blender, blend, base_blend):
    r = inspect(blender, blend, BOY_PROBE)
    base = inspect(blender, base_blend, BOY_PROBE)
    n, bb = r["names"], r["bbox"]
    check("boy candidate pieces are garment/2", r["gen"] == ["garment/2"], r["gen"])
    for s in "LR":
        up = bb.get(f"garment.shoes.main.{s}")
        st = [v for k, v in bb.items() if k.startswith(f"garment.shoes.stripe.{s}.")]
        ok = len(st) >= 2 and up is not None
        if ok:
            xc = 0.5 * (up[0][0] + up[1][0])
            ok = all(up[0][2] - 0.01 < b[0][2] and b[1][2] < up[1][2] + 0.003 and b[1][2] - b[0][2] > 0.015 and
                     min(abs(b[0][0] - xc), abs(b[1][0] - xc)) > 0.25 * (up[1][0] - up[0][0]) for b in st)
            # both side walls carry stripes
            ok = ok and any(b[0][0] > xc for b in st) and any(b[1][0] < xc for b in st)
        check(f"stripes on the {s} upper, on both side walls", ok, f"{len(st)} stripes")
    fl, bag, pk = bb.get("garment.backpack.flap"), bb.get("garment.backpack.main"), bb.get("garment.backpack.pocket")
    check("flap covers the top of the bag, on its outer face",
          fl is not None and fl[1][2] >= bag[1][2] - 0.002 and fl[0][2] > pk[1][2] - 0.01 and fl[1][1] >= bag[1][1])
    tab, buckle = bb.get("garment.backpack.tab"), bb.get("garment.backpack.buckle")
    check("tab and buckle on the flap's centre line, below its edge",
          tab is not None and buckle is not None and abs(0.5 * (tab[0][0] + tab[1][0])) < 0.005
          and buckle[0][2] < fl[0][2] + 0.01)
    pf = bb.get("garment.backpack.pocket_flap")
    check("pocket flap on the pocket", pf is not None and pf[1][2] >= pk[1][2] - 0.002 and pf[1][1] >= pk[1][1])
    check("no zips on the flap pack (B06)", not any(".zip" in x for x in n))
    check("trouser legs separate higher than 2.0.0 (gusset)", r["gusset_bottom"] > base["gusset_bottom"] + 0.03,
          f"{base['gusset_bottom']:.4f} -> {r['gusset_bottom']:.4f}")
    tr, sh = bb["garment.trousers.main"], bb["garment.shoes.main.L"]
    check("the trouser hem reaches the shoe (break)", tr[0][2] <= sh[1][2] + 0.01, f"hem {tr[0][2]:.4f} shoe top {sh[1][2]:.4f}")


def test_girl(blender, blend, base_blend):
    r = inspect(blender, blend, GIRL_PROBE)
    base = inspect(blender, base_blend, GIRL_PROBE)
    bb = r["bbox"]
    for s in "LR":
        cuff, shaft = bb.get(f"garment.boots.cuff.{s}"), bb[f"garment.boots.main.{s}"]
        ok = cuff is not None and cuff[1][2] > shaft[1][2] and (cuff[1][0] - cuff[0][0]) > (shaft[1][0] - shaft[0][0])
        check(f"rolled cuff on the {s} boot, proud of the shaft and over its rim", ok)
    sp = r["split"]
    gap = (sp["inner_L"] - sp["inner_R"]) if sp["inner_L"] is not None and sp["inner_R"] is not None else 0.0
    check("bloomer legs split (gap between the inner surfaces near the hem, front/back centre)", gap > 0.008,
          f"gap {gap:.4f} m at z {sp['z']:.3f}")
    check("one flower on the bun", len(r["flowers"]) >= 1 and sum(r["flowers"].values()) <= 600, r["flowers"])
    check("corrective.reach.L/R on the vest", r["keys"] == ["corrective.reach.L", "corrective.reach.R"], r["keys"])
    check("every corrective key is driven", r["drivers"] == r["keys"], r["drivers"])
    check("rest pose: correctives at 0", all(v == 0 for v in r["rest"]["values"].values()), r["rest"]["values"])
    check("arms down (compare rotation): correctives stay at 0", all(v == 0 for v in r["arms_down"]["values"].values()),
          r["arms_down"]["values"])
    check("reach pose: correctives at 1", all(v > 0.95 for v in r["reach"]["values"].values()),
          sorted(set(r["reach"]["values"].values())))
    b0, a = base["reach"]["after"], r["reach"]["after"]
    check("reach: the vest flare (max and p99 to the torso skin) is below 0.11.0's and at most 1 cm above rest",
          a["max"] < b0["max"] and a["p99"] < b0["p99"] and a["max"] <= r["rest"]["flare"]["max"] + 0.01,
          f"0.11.0 {b0} candidate {a} rest {r['rest']['flare']}")
    pb, pm, pa = base["reach"]["pen_after"], r["reach"]["pen_before"], r["reach"]["pen_after"]
    check("reach: the driven keys reduce the vest's penetration into the blouse (count and p95 depth)",
          pa["inside"] < pm["inside"] and pa["p95_depth"] < pm["p95_depth"], f"muted {pm} driven {pa}")
    check("reach: the vest's penetration into the blouse is below 0.11.0's",
          pa["inside"] < pb["inside"] and pa["p95_depth"] < pb["p95_depth"], f"0.11.0 {pb} candidate {pa}")
    check("rest: no new penetration (p95 depth under 2 mm)", r["rest"]["pen"]["p95_depth"] < 0.002, r["rest"]["pen"])
    check("the collar and the vest edges are cleanly finished (no fibres)",
          r["collar_fibres"] == 0 and r["edge_fibres"] == 0, f"collar {r['collar_fibres']} edges {r['edge_fibres']}")
    print("[test_garments_v2] reach", json.dumps({"rest": r["rest"], "0.11.0": base["reach"], "candidate": r["reach"]}))


def main():
    blender = arg("--blender", "blender")
    test_pin()
    test_validate(blender)
    if "--quick" not in sys.argv:
        test_v1_parity(blender)
        boy = arg("--boy-master") or build(blender, BOY, [BOY_OVR], "boy_yellow_hoodie")
        boy_base = arg("--boy-base-master") or build(blender, BOY, [], "boy_yellow_hoodie")
        test_boy(blender, boy, boy_base)
        girl = arg("--girl-master") or build(blender, GIRL, [GIRL_OVR], "girl_auburn_bun_glasses")
        girl_base = arg("--girl-base-master") or build(blender, GIRL, [], "girl_auburn_bun_glasses")
        test_girl(blender, girl, girl_base)
    print(f"[test_garments_v2] {sum(RESULTS)}/{len(RESULTS)} passed")
    sys.exit(0 if all(RESULTS) else 1)


if __name__ == "__main__":
    main()
