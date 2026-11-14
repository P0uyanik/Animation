"""Hair generator independence test (headless Blender): hair_clumps/2 with real-scalp placement on a SYNTHETIC head
that differs from the boy in shape, size and position (a tall egg, 0.20 m tall, centred at z = 1.30). No boy objects,
no boy proportions. Synthetic test configuration only, not a character.

    blender -b --factory-startup -P pipeline/charsys/tests/hair_generic_test.py -- <out.json>

Checks: the generator runs with its own fringe and family configuration; sampled lock roots lie on the synthetic
scalp at the configured offset (surface placement); rays towards the head centre over the upper scalp hit hair
(coverage >= 95%)."""
import json
import math
import os
import sys
import types

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import body_v6 as BV  # noqa: E402  (only its generic helpers: clump, face_y, geom)
import hair as HAIR  # noqa: E402

out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
C = bpy.data.collections.new("synthetic")
bpy.context.scene.collection.children.link(C)
G = BV.G
centre, radii = Vector((0.03, 0.02, 1.30)), Vector((0.11, 0.12, 0.20))
head = G.uv_sphere("head", centre, 1.0, C, 64, 32, tuple(radii))
M = {"hair": G.material("M_hair_felt", (40, 30, 25)), "skin": G.material("M_skin", (220, 180, 160))}
hair_c, hair_r = centre + Vector((0, 0, 0.02)), radii * 1.05


def on_ellipsoid(az, el, lift=0.0):  # projection origin and fallback only
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    p = hair_c + Vector((d.x * hair_r.x, d.y * hair_r.y, d.z * hair_r.z))
    return p + d * lift, d


B = types.SimpleNamespace(G=G, clump=BV.clump, face_y=BV.face_y, on_hair=on_ellipsoid, HAIR_C=hair_c, HAIR_R=hair_r)
offset = 0.012
fz = centre.z + 0.02
params = {"placement": "surface", "scalp_offset_m": offset, "base": "scalp",
          "scalp_cap": {"offset": 0.005, "hairline": [[0, fz + 0.05], [90, centre.z - 0.02], [180, centre.z - 0.08]],
                        "face_cut": [centre.y - 0.06, fz + 0.05]},
          "fringe": {"x": [centre.x - 0.05, centre.x, centre.x + 0.05], "tip_z": [fz, fz - 0.01, fz], "root_el": 30,
                     "az_depth": 0.12, "width": [0.04, 0.05], "thick": [0.025, 0.03]},
          "families": {"crown": {"count": 4, "length": [0.04, 0.05]}, "top": {"count": 5},
                       "side": {"count": 3, "az": [50, 130], "el_root": [30, 40], "el_tip": [0, 10]},
                       "back_hi": {"count": 5}, "back_lo": {"count": 4, "el_root": [10, 20], "el_tip": [-30, -20]}},
          "lock_curve": 0.15, "lock_splits": [0, 1]}
place = HAIR.scalp_surface_placement(head, hair_c, hair_r, offset, on_ellipsoid)
objs, stats = HAIR.build_hair_v2(C, M, head, B, params, seed=5)
R = {"stats": stats, "checks": {}}
# 1) roots on the scalp: sample the placement function and compare with the true surface distance
from mathutils.bvhtree import BVHTree  # noqa: E402
bvh = BVHTree.FromObject(head, bpy.context.evaluated_depsgraph_get())
errs = []
for az in range(-180, 180, 20):
    for el in range(10, 90, 15):
        p, n = place(az, el, 0.0)
        loc, nrm, idx, dist = bvh.find_nearest(p)
        errs.append(abs(dist - offset))
R["checks"]["roots_on_scalp_max_err_mm"] = round(max(errs) * 1000, 3)
# 2) coverage from above: rays from the head centre outwards over the upper scalp must hit hair
deps = bpy.context.evaluated_depsgraph_get()
hair_objs = {o.name for o in objs}
hit = tot = 0
for az in range(-180, 180, 15):
    for el in range(25, 89, 8):
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        o = centre + d * 0.5
        ok, loc, nrm, idx, ob, mat = bpy.context.scene.ray_cast(deps, o, -d)  # from outside towards the centre
        tot += 1
        hit += bool(ok and ob is not None and ob.name in hair_objs)
R["checks"]["upper_scalp_covered_pct"] = round(100 * hit / tot, 1)
R["checks"]["generator_ran"] = stats.get("locks", 0) > 0
R["pass"] = R["checks"]["roots_on_scalp_max_err_mm"] < 0.5 and R["checks"]["upper_scalp_covered_pct"] >= 95 and R["checks"]["generator_ran"]
json.dump(R, open(out, "w"), indent=1)
print("[hair_generic_test]", json.dumps(R))
