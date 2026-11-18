"""T-044 face visibility (no render), T-049's grid metric plus an occlusion-corrected variant.

    blender -b --factory-startup -P face_visibility.py -- <blend> <out.json>

Grid: 41 x 41 rays over the face window (brow top + 1 cm to mouth - 12 mm, eye corners +- 45 mm) from the front and a
35 deg three-quarter view (both sides), as T-049 measure.py. "t049": a ray is blocked when its first hit is a hair
object (as in T-049). "occluding": a ray is blocked only when a hair object is hit BEFORE the head/face skin along
the same ray, i.e. hair in front of the face; rays that pass the face silhouette and only see hair behind the face
(the far side in 3/4) count as not covering the face."""
import json
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
sc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
L = {o.name: o.matrix_world.translation.copy() for o in bpy.data.objects if o.name.startswith("LM_")}
brow = [o for o in bpy.data.objects if o.name.startswith("brow.")]
zt = max((b.matrix_world @ v.co).z for b in brow for v in b.evaluated_get(dg).data.vertices) + 0.01
eL, eR, mo = L["LM_eye_L"], L["LM_eye_R"], L["LM_mouth"]
zb = mo.z - 0.012
ctr = (eL + eR) / 2
half = (eL - eR).length / 2 + 0.045
eye_half = (eL - eR).length / 2 + 0.035
SKIN = ("head", "body_skin")


def first_hits(origin, d):
    """(first hit object, first skin hit distance or None, first hair hit distance or None)."""
    o, t, first, skin_t, hair_t = origin.copy(), 0.0, None, None, None
    for _ in range(64):
        hit, loc, _, _, ob, _ = sc.ray_cast(dg, o, d, distance=2.0 - t)
        if not hit:
            break
        t += (loc - o).length
        first = first or ob.name
        if ob.name.startswith("hair_") and hair_t is None:
            hair_t = t
        if ob.name.startswith(SKIN) and skin_t is None:
            skin_t = t
            break
        o = loc + d * 1e-4
        t += 1e-4
    return first, skin_t, hair_t


def vis(view_yaw):
    yaw = math.radians(view_yaw)
    d = Vector((-math.sin(yaw), math.cos(yaw), 0.0))
    n = {"face": [0, 0, 0], "eyes": [0, 0, 0]}  # rays, t049-visible, occluding-visible
    for i in range(41):
        for j in range(41):
            x = -half + 2 * half * i / 40
            z = zb + (zt - zb) * j / 40
            p = ctr + Vector((x, 0, z - ctr.z))
            first, skin_t, hair_t = first_hits(p - d * 1.0, d)
            if first is None:
                continue
            keys = ["face"] + (["eyes"] if abs(x) < eye_half and abs(z - eL.z) < 0.035 else [])
            for k in keys:
                n[k][0] += 1
                n[k][1] += not first.startswith("hair_")
                n[k][2] += not (hair_t is not None and skin_t is not None and hair_t < skin_t)
    return {k: {"t049": round(v[1] / max(1, v[0]), 4), "occluding": round(v[2] / max(1, v[0]), 4)} for k, v in n.items()}


out = {"front": vis(0), "three_quarter_right": vis(35), "three_quarter_left": vis(-35)}
json.dump(out, open(argv[1], "w"), indent=1)
print("FACEVIS", json.dumps(out))
