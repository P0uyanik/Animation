"""T-159: ear measures of a master with the T-161 definitions, taken from the geometry (orthographic projections).

    blender -b --factory-startup -P docs/evaluation/characters/T-159/tools/ear_measures.py -- <out.json> <master.blend> [...]

T-161 (docs/evaluation/characters/T-161/targets.json) traces these by hand in perspective images; here they are
computed, so compare them with the targets within the T-161 tolerances, not to the last digit:
  F    head width across the widest cheek contours (skin only: no ears, no hair), front view
  Hh   main hair crown (hair objects except buns, bows, flowers, bands) to the chin landmark
  ear_front_projection  (ear outer rim x - widest skin x within the ear's height band) / F, front view
  ear_width             (ear outer rim x - skin silhouette x at the ear's mid height) / F, front view
  ear_height            ear height / Hh
  ear_top_eye           (eye z - ear top z) / Hh      (positive = ear top below the iris centre)
  ear_base_mouth        (mouth z - ear bottom z) / Hh (positive = lobe below the mouth)
  ear_turn_projection   at a 30 and 45 degree turn towards the ear: width of the exposed ear at its mid height
                        (ear vertices outside the head skin, +-6 mm band) in the image plane / projected skin width
Left ear; read-only."""
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

a = sys.argv[sys.argv.index("--") + 1:]
out = {}
SKIP = ("bun", "bow", "flower", "band", "scrunch")
for path in a[1:]:
    bpy.ops.wm.open_mainfile(filepath=path)
    D = bpy.data.objects
    sk = D["body_skin"]
    P = np.array([sk.matrix_world @ v.co for v in sk.data.vertices])
    tree = BVHTree.FromPolygons([sk.matrix_world @ v.co for v in sk.data.vertices], [tuple(p.vertices) for p in sk.data.polygons])
    ear = D["ear.L"]
    E = np.array([ear.matrix_world @ v.co for v in ear.data.vertices])
    eye, chin, mouth = (D[n].matrix_world.translation for n in ("LM_eye_L", "LM_chin", "LM_mouth"))
    hair_top = max((max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in D
                    if o.type == "MESH" and o.name.startswith("hair_") and ".fibres" not in o.name
                    and not any(s in o.name for s in SKIP)), default=float("nan"))
    head = P[(P[:, 2] > chin.z - 0.005) & (P[:, 2] < eye.z + 0.12)]
    F = 2 * float(np.abs(head[:, 0]).max())
    Hh = hair_top - chin.z
    z0, z1 = E[:, 2].min(), E[:, 2].max()
    zm = 0.5 * (z0 + z1)
    band = head[(head[:, 2] > z0) & (head[:, 2] < z1)]
    mid = head[np.abs(head[:, 2] - zm) < 0.004]
    # exposed ear vertices at mid height: outside the skin (a ray towards the head axis hits the skin)
    axis_y = float(np.median(head[:, 1]))
    ring = E[np.abs(E[:, 2] - zm) < 0.006]
    exposed = []
    for q in ring:
        d = Vector((-q[0], axis_y - q[1], 0.0))
        if d.length > 1e-6 and tree.ray_cast(Vector(q), d.normalized(), d.length)[0] is not None:
            exposed.append(q)
    exposed = np.array(exposed) if exposed else ring
    turn = {}
    for az in (30, 45):
        r = math.radians(az)
        rv = np.array([math.cos(r), math.sin(r), 0.0])
        turn[str(az)] = round(float(((exposed @ rv).max() - (exposed @ rv).min()) / ((head @ rv).max() - (head @ rv).min())), 4)
    out[path.replace("\\", "/").split("/")[-2]] = {
        "F_m": round(F, 4), "Hh_m": round(float(Hh), 4),
        "ear_front_projection": round(float((E[:, 0].max() - band[:, 0].max()) / F), 4),
        "ear_width": round(float((E[:, 0].max() - mid[:, 0].max()) / F), 4),
        "ear_height": round(float((z1 - z0) / Hh), 4),
        "ear_top_eye": round(float((eye.z - z1) / Hh), 4),
        "ear_base_mouth": round(float((mouth.z - z0) / Hh), 4),
        "ear_turn_projection": turn,
        "ear_outer_x_over_eye_x": round(float(E[:, 0].max() / eye.x), 3),
    }
json.dump(out, open(a[0], "w"), indent=1)
print("MEASURES " + json.dumps(out))
