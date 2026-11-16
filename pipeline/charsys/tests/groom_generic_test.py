"""Groom system (groom/1) independence test (headless Blender; no rendering, writes only <out.json>).

    blender -b --factory-startup -P pipeline/charsys/tests/groom_generic_test.py -- <out.json>

A SYNTHETIC egg head (0.20 m tall, centred at z = 1.30, off the origin), no character objects or proportions, and a
synthetic groom that uses the structures the girl does NOT use: two buns with opposite wrap directions, a bow,
straight long locks, wavy locks, plus a cap, sweep, fringe, curls, irregular draped ringlets (curl wobble/sway,
hang_jitter, rest_radii), a tie and flowers. Checks:
  1. every structure builds; object names are hair_<name>; two bun frames;
  2. long straight locks reach their z_end; curly locks have a helix (horizontal spread around the centre line);
  3. sweep roots lie on the scalp at the configured offset (surface placement);
  4. validation rejects an unknown type, a missing key and a reference to a bun that does not exist;
  5. every rope object carries the per-rope fibre UV map, with V increasing along the rope (metres);
  6. draped irregular ringlets (wobble, sway, hang_jitter) build and move inwards below rest_z.
Felted hair (T-033), a second groom on the same synthetic head with spec.hair.finish "felt" and felt_volume shapes:
  7. felt sweep (gather), felt fringe sheet, felt bun (mass on the bun frame), felt curly/straight locks and the
     felt_volume gather / fringe / mass shapes build; every felt shell is closed (each edge has exactly two faces);
  8. felt locks have no ply ridges: along-length radius variation < 25 % of the yarn rope on the same centre line;
  9. the gather volume lies on the head (inner surface under the skin by at most the inset, outer surface within the
     specified height), the felt fringe tips hang in front of the face at tip_z, the felt bun mass sits on its frame;
 10. dynamics records are kept with the felt finish (bun chain + every lock chain, same count as yarn);
 11. validation rejects a bad finish, an unknown felt shape and a felt shape without its keys;
 12. the shared GN fibre group ('felt hair' preset) grows fibre curves on the felt surfaces (two layers: felt fuzz
     and sparse flyaways), parented to their surface.
Exit code 1 on any failure."""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import geom as G  # noqa: E402
import groom as GROOM  # noqa: E402
import groom_felt as GROOM_FELT  # noqa: E402

out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
C = bpy.data.collections.new("synthetic")
bpy.context.scene.collection.children.link(C)
centre, radii = Vector((0.03, 0.02, 1.30)), Vector((0.11, 0.12, 0.10))
head = G.uv_sphere("head", centre, 1.0, C, 64, 32, tuple(radii))
cz = centre.z
curl = {"radius": 0.010, "pitch": 0.025, "jitter": 0.2}
spec = {"generator": "groom/1", "seed": 3, "scalp_offset_m": 0.006, "yarn": {"step_m": 0.004},
        "structures": [
            {"type": "scalp_cap", "name": "cap", "offset": 0.003, "face_cut": [centre.y - 0.05, cz + 0.02],
             "hairline": [[0, cz + 0.03], [90, cz - 0.02], [180, cz - 0.05]]},
            {"type": "bun", "name": "buns", "buns": [
                {"az": 90, "el": 55, "radius": 0.035, "height": 0.06, "wrap": "cw", "ropes": 4},
                {"az": -90, "el": 55, "radius": 0.035, "height": 0.06, "wrap": "ccw", "ropes": 4}]},
            {"type": "sweep", "name": "sweep", "count": 6, "az": [-60, 60], "el_root": [30, 40], "target": {"bun": 1},
             "width": 0.02, "thick": 0.012},
            {"type": "fringe", "name": "fringe", "root_az": [-10, 10], "root_el": 50, "tip_x": [0.0, 0.06],
             "tip_z": [cz + 0.02, cz + 0.02], "width": 0.02, "thick": 0.012},
            {"type": "locks", "name": "long", "style": "straight", "count": 5, "az": [130, 230], "el_root": [10, 20],
             "hang_radii": [0.12, 0.13], "z_end": [cz - 0.35, cz - 0.35], "width": 0.02, "thick": 0.012},
            {"type": "locks", "name": "wavy", "style": "wavy", "count": 2, "mirror": True, "az": [80, 110],
             "el_root": [0, 10], "hang_radii": [0.125, 0.12], "z_end": [cz - 0.2, cz - 0.18], "width": 0.018, "thick": 0.012,
             "wave": {"amplitude": 0.01, "wavelength": 0.05}},
            {"type": "locks", "name": "curls", "style": "curly", "count": 3, "az": [150, 210], "el_root": [-10, 0],
             "hang_radii": [0.10, 0.11], "z_end": [cz - 0.25, cz - 0.25], "width": 0.014, "thick": 0.012, "curl": curl},
            {"type": "locks", "name": "ringlets", "style": "curly", "count": 4, "az": [140, 220], "el_root": [-5, 5],
             "hang_radii": [0.13, 0.14], "hang_jitter": 0.1, "rest_radii": [0.07, 0.07], "rest_z": cz - 0.15,
             "z_end": [cz - 0.30, cz - 0.24], "width": 0.016, "thick": 0.014,
             "curl": {"radius": 0.010, "pitch": 0.03, "jitter": 0.2, "wobble": 0.3, "sway": 0.006}},
            {"type": "tie", "name": "tie", "bun": 0},
            {"type": "bow", "name": "bow", "bun": 1, "around_deg": 0, "height_frac": 0.15, "size": 0.04},
            {"type": "flowers", "name": "flowers", "bun": 0, "items": [{"around_deg": 0, "size": 0.015}]}]}
mats = {}
objs, rep = GROOM.build(C, head, {"centre": centre, "radii": radii}, spec,
                        lambda slot: mats.setdefault(slot, G.material("M_" + slot, (90, 60, 50))),
                        lambda h, x, z: (G.surface_point(h, (x, -1.0, z), (0, 1, 0))[0] or Vector((0, -0.1, 0))).y)
names = {o.name for o in objs}
R = {"report": rep, "checks": {}}
ok = True


def check(name, cond, val=None):
    global ok
    R["checks"][name] = {"pass": bool(cond), "value": val}
    ok &= bool(cond)
    print(f"[groom_generic_test] {'PASS' if cond else 'FAIL'} {name} {'' if val is None else val}")


expect = {"hair_cap", "hair_buns", "hair_sweep", "hair_fringe", "hair_long", "hair_wavy", "hair_curls", "hair_tie", "hair_bow",
          "hair_flowers_petals", "hair_flowers_centres"}
check("all structures built", expect <= names, sorted(names))
check("two bun frames", rep["structures"]["buns"]["buns"] == 2, rep["structures"]["buns"])
long_ob = bpy.data.objects["hair_long"]
zmin = min(v.co.z for v in long_ob.data.vertices)
check("long locks reach z_end (+-15 mm)", abs(zmin - (cz - 0.35)) < 0.015, round(zmin, 4))
cur = bpy.data.objects["hair_curls"]
low = [v.co for v in cur.data.vertices if v.co.z < cz - 0.12]
spread = max(p.x for p in low) - min(p.x for p in low) if low else 0.0
check("curls spiral (horizontal spread > 2 x curl radius)", spread > 2 * curl["radius"], round(spread, 4))
sc = GROOM.Scalp(head, centre, radii, 0.006)
from mathutils.bvhtree import BVHTree  # noqa: E402
bvh = BVHTree.FromObject(head, bpy.context.evaluated_depsgraph_get())
errs = [abs(bvh.find_nearest(sc.at(az, el)[0])[3] - 0.006) for az in range(-180, 180, 30) for el in range(0, 80, 20)]
check("roots on scalp (max error < 1 mm)", max(errs) < 0.001, round(max(errs) * 1000, 3))
bad = [{"structures": [{"type": "braid"}]},
       {"structures": [{"type": "locks", "count": 1}]},
       {"structures": [{"type": "tie", "bun": 0}]}]
errs_bad = [GROOM.validate(b) for b in bad]
check("validation rejects bad specs", all(errs_bad), errs_bad)
check("synthetic spec validates", GROOM.validate(spec) == [])
ropes = [o for o in objs if not o.name.startswith("hair_cap")]
uv_ok = all(GROOM.UV_NAME in o.data.uv_layers for o in ropes)
lo_ob = bpy.data.objects["hair_long"]
vmax = max(d.uv[1] for d in lo_ob.data.uv_layers[GROOM.UV_NAME].data)
check("ropes carry the fibre UV map; V runs along the rope in metres (long lock > 0.3 m)", uv_ok and vmax > 0.3,
      round(vmax, 3))
rl = bpy.data.objects["hair_ringlets"]
low = [v.co for v in rl.data.vertices if v.co.z < cz - 0.2]
r_low = max((Vector((p.x - centre.x, p.y - centre.y)).length for p in low), default=1.0)
check("draped ringlets move inwards below rest_z (outer radius < hang radius)", r_low < 0.13, round(r_low, 4))
# ---------------------------------------------------------------------------------------------- felt (T-033)
sys.path.insert(0, os.path.join(HERE, "..", "materials"))
from materials import builder as MATERIALS  # noqa: E402
C2 = bpy.data.collections.new("synthetic_felt")
bpy.context.scene.collection.children.link(C2)
felt_curl = {"radius": 0.010, "pitch": 0.03, "jitter": 0.2, "wobble": 0.3, "sway": 0.006}
felt = {"generator": "groom/1", "seed": 5, "scalp_offset_m": 0.006, "finish": "felt", "yarn": {"step_m": 0.003},
        "fibres": {"slots": ["hair"], "layers": [{"name": "felt"},
                                                 {"name": "flyaways", "overrides": {"fibres": {
                                                     "density_per_cm2": 0.08, "length_mm": 12.0, "curl": 0.9}}}]},
        "dynamics": {"enabled": True, "structures": {"fbun": {"bones": 1}, "fcurls": {"bones": 3},
                                                     "fstraight": {"bones": 3}}},
        "structures": [
            {"type": "bun", "name": "fbun", "buns": [{"az": 180, "el": 60, "radius": 0.04, "height": 0.07,
                                                     "turns": 1.0, "felt_radii": [1.0, 0.95, 1.0]}]},
            {"type": "sweep", "name": "fsweep", "count": 6, "az": [-80, 80], "el_root": [30, 34],
             "target": {"bun": 0}, "lift": [0.003, 0.008], "width": 0.02, "thick": 0.012},
            {"type": "fringe", "name": "ffringe", "root_az": [-20, 0, 20], "root_el": 50, "tip_x": [-0.03, 0.03, 0.08],
             "tip_z": [cz + 0.02, cz + 0.025, cz + 0.02], "width": 0.02, "thick": 0.012},
            {"type": "locks", "name": "fcurls", "style": "curly", "count": 3, "az": [150, 210], "el_root": [-10, 0],
             "hang_radii": [0.12, 0.13], "z_end": [cz - 0.25, cz - 0.22], "width": 0.016, "thick": 0.014,
             "curl": felt_curl},
            {"type": "locks", "name": "fstraight", "style": "straight", "count": 2, "az": [120, 130],
             "el_root": [0, 5], "hang_radii": [0.125, 0.13], "z_end": [cz - 0.2, cz - 0.2], "width": 0.016,
             "thick": 0.014},
            {"type": "locks", "name": "ystraight", "finish": "yarn", "style": "straight", "count": 2,
             "az": [120, 130], "el_root": [0, 5], "hang_radii": [0.125, 0.13], "z_end": [cz - 0.2, cz - 0.2],
             "width": 0.016, "thick": 0.014},
            {"type": "felt_volume", "name": "vgather", "shape": "gather", "az": [-180, 180],
             "hairline_el": [[0, 20], [90, 5], [180, -10]], "target": {"az": 0, "el": 90}, "height": [0.006, 0.012, 0.01],
             "part": {"az": -25, "width_deg": 3, "depth": 0.5, "length": 0.6}, "grooves": {"count": 30}},
            {"type": "felt_volume", "name": "vfringe", "shape": "fringe", "root_az": [-30, -10, 10],
             "root_el": [44, 48], "tip_x": [-0.04, 0.02, 0.07], "tip_z": [cz + 0.01, cz + 0.015, cz + 0.01],
             "thick": [0.016, 0.01], "bulge": 0.015},
            {"type": "felt_volume", "name": "vmass", "shape": "mass", "az": 75, "el": 5, "lift": -0.01,
             "radii": [0.025, 0.02, 0.04], "axis": "up", "swirl": 0.2}]}
fobjs, frep = GROOM.build(C2, head, {"centre": centre, "radii": radii}, felt,
                          lambda slot: mats.setdefault(slot, G.material("M_" + slot, (90, 60, 50))),
                          lambda h, x, z: (G.surface_point(h, (x, -1.0, z), (0, 1, 0))[0] or Vector((0, -0.1, 0))).y,
                          lambda ob, slot, ov: MATERIALS.add_fibres_geometry(ob, "felt hair", (86, 54, 44), 0.2, ov))
R["felt_report"] = frep
fnames = {o.name for o in fobjs}
fexpect = {"hair_fbun", "hair_fsweep", "hair_ffringe", "hair_fcurls", "hair_fstraight", "hair_ystraight", "hair_vgather",
           "hair_vfringe", "hair_vmass"}
finished = all(frep["structures"][n].get("finish") == "felt" for n in ("fbun", "fsweep", "ffringe", "fcurls", "fstraight"))
check("felt structures build (finish felt on sweep, fringe, bun, locks; felt_volume gather/fringe/mass)",
      fexpect <= fnames and finished and "finish" not in frep["structures"]["ystraight"], sorted(fnames))


def open_edges(ob):
    from collections import Counter
    cnt = Counter()
    for p in ob.data.polygons:
        for e in p.edge_keys:
            cnt[e] += 1
    return sum(1 for v in cnt.values() if v != 2)


shells = ["hair_fbun", "hair_fsweep", "hair_ffringe", "hair_vgather", "hair_vfringe", "hair_vmass"]
oe = {n: open_edges(bpy.data.objects[n]) for n in shells}
check("felt shells are closed (every edge has two faces)", not any(oe.values()), oe)


def ridge(ob, seg, ropes):
    """Mean along-length change of the section radius at a fixed section index, relative to the mean radius (first
    rope of the object: ropes of equal vertex count, each rings x seg + two cap centres; cap rings skipped)."""
    vs = [v.co for v in ob.data.vertices]
    n_r = (len(vs) // ropes - 2) // seg
    rings = []
    for i in range(n_r):
        ring = vs[i * seg:(i + 1) * seg]
        c = sum(ring, Vector()) / seg
        rings.append([(p - c).length for p in ring])
    rings = rings[6:-6]
    d = [abs(b[k] - a[k]) for a, b in zip(rings, rings[1:]) for k in range(seg)]
    mean_r = sum(sum(r) for r in rings) / (len(rings) * seg)
    return sum(d) / len(d) / mean_r


rf = ridge(bpy.data.objects["hair_fstraight"], GROOM_FELT.LOCK_DEFAULT["seg"], 2)
ry = ridge(bpy.data.objects["hair_ystraight"], GROOM.YARN_DEFAULT["seg"], 2)
check("felt locks have no ply ridges (radius variation along the lock < 25 % of the yarn rope's)", rf < 0.25 * ry,
      {"felt": round(rf, 4), "yarn": round(ry, 4)})
gv = bpy.data.objects["hair_vgather"]
dists = []
for v in gv.data.vertices:
    loc, nrm, _, _ = bvh.find_nearest(v.co)
    s_ = 1 if (v.co - loc).dot(nrm) >= 0 else -1
    dists.append(s_ * (v.co - loc).length)
check("gather volume lies on the head (inner <= 4.5 mm under the skin, outer < 1.4 x height)",
      min(dists) > -0.0045 and max(dists) < 0.012 * 1.4, [round(min(dists), 4), round(max(dists), 4)])
ff = bpy.data.objects["hair_ffringe"]
low = min(v.co.z for v in ff.data.vertices)
front = min(v.co.y for v in ff.data.vertices)
check("felt fringe tips hang at tip_z (+-12 mm) in front of the face", abs(low - (cz + 0.02)) < 0.012 and front < centre.y - 0.08,
      [round(low, 4), round(front, 4)])
fb = bpy.data.objects["hair_fbun"]
bc = sum((v.co for v in fb.data.vertices), Vector()) / len(fb.data.vertices)
bf0 = GROOM.Scalp(head, centre, radii, 0.006).at(180, 60)[0]
check("felt bun mass sits on its frame (centroid within 1.2 x height of the base)", (bc - bf0).length < 0.07 * 1.2,
      round((bc - bf0).length, 4))
nch = sum(len(json.loads(o.get("ps_dyn", "{}")).get("chains", [])) for o in fobjs)
check("dynamics records kept with the felt finish (1 bun + 3 curl + 2 straight chains)", nch == 6, nch)
bad = [{"structures": [{"type": "locks", "finish": "velvet", "count": 1, "az": [0, 1], "el_root": 0, "hang_radii": [1, 1],
                        "z_end": 0, "width": 1, "thick": 1}]},
       {"structures": [{"type": "felt_volume", "shape": "blob"}]},
       {"structures": [{"type": "felt_volume", "shape": "gather"}]},
       {"finish": "silk", "structures": [{"type": "scalp_cap"}]}]
errs_bad = [GROOM.validate(b) for b in bad]
check("validation rejects a bad finish, an unknown felt shape and missing felt keys", all(errs_bad), errs_bad)
check("felt spec validates", GROOM.validate(felt) == [])
fib = [o for o in bpy.data.objects if o.get("ps_groom_fibres")]
deps = bpy.context.evaluated_depsgraph_get()
ncurves = {o.name: len(o.evaluated_get(deps).data.curves) for o in fib}
expect_fib = 2 * sum(1 for o in fobjs)  # every felt object uses the "hair" slot
check("GN fibre group grows fibres on the felt surfaces (2 layers per object, parented, curves > 0)",
      len(fib) == expect_fib and all(o.parent is not None for o in fib) and all(v > 0 for v in ncurves.values()),
      {"objects": len(fib), "curves": sum(ncurves.values())})
R["pass"] = ok
json.dump(R, open(out, "w"), indent=1, default=str)
sys.exit(0 if ok else 1)
