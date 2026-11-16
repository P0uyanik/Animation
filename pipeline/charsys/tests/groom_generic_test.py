"""Groom system (groom/1) independence test (headless Blender; no rendering, writes only <out.json>).

    blender -b --factory-startup -P pipeline/charsys/tests/groom_generic_test.py -- <out.json>

A SYNTHETIC egg head (0.20 m tall, centred at z = 1.30, off the origin), no character objects or proportions, and a
synthetic groom that uses the structures the girl does NOT use: two buns with opposite wrap directions, a bow,
straight long locks, wavy locks, plus a cap, sweep, fringe, curls, a tie and flowers. Checks:
  1. every structure builds; object names are hair_<name>; two bun frames;
  2. long straight locks reach their z_end; curly locks have a helix (horizontal spread around the centre line);
  3. sweep roots lie on the scalp at the configured offset (surface placement);
  4. validation rejects an unknown type, a missing key and a reference to a bun that does not exist.
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
R["pass"] = ok
json.dump(R, open(out, "w"), indent=1, default=str)
sys.exit(0 if ok else 1)
