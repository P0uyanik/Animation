"""T-065 criterion 0: measures a built master's face outline in the units of head_outlines.json.

    blender -b --factory-startup -P docs/evaluation/characters/T-065/outline_measure.py -- <master.blend> <out.json>

Rest shape of the body skin (basis, no pose). Eye line and eye spacing from the face landmarks (LM_eye_L/R). For
t = depth below the eye line in eye-spacing units: front = half width of the head slice (front half), side = forward
offset of the slice's front-most point relative to the eye line's; chin_t = the lowest front point."""
import json
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
skin = bpy.data.objects["body_skin"]
me = skin.data
co = np.empty(len(me.vertices) * 3)
(me.shape_keys.key_blocks[0].data if me.shape_keys else me.vertices).foreach_get("co", co)
co = co.reshape(-1, 3) @ np.array(skin.matrix_world)[:3, :3].T + np.array(skin.matrix_world)[:3, 3]
eL, eR = (bpy.data.objects[f"LM_eye_{s}"].matrix_world.translation for s in "LR")
ze, u = (eL.z + eR.z) / 2, abs(eL.x - eR.x)
sl = co[np.abs(co[:, 2] - ze) < 0.003, 1]
yc = float(0.5 * (sl.min() + sl.max()))  # the head's depth centre at the eye line (not a median: refined regions are dense)
front, side = [], []
y0 = None
for t in np.arange(0.0, 1.0, 0.02):
    z = ze - t * u
    m = (np.abs(co[:, 2] - z) < 0.0015) & (co[:, 1] < yc)
    if not m.any():
        continue
    yf = co[m, 1].min()
    y0 = yf if y0 is None else y0
    front.append([round(float(t), 3), round(float(np.abs(co[m, 0]).max() / u), 4)])
    side.append([round(float(t), 3), round(float((y0 - yf) / u), 4)])
# chin: rays along the midline from the front; the chin is where the profile reaches the neck (within 0.05 eye
# spacings of the neck front measured 1.3 eye spacings below the eye line)
from mathutils import Vector
from mathutils.bvhtree import BVHTree
polys = [p.vertices[:] for p in me.polygons]
tree = BVHTree.FromPolygons([Vector(c) for c in co], polys)
prof = []
for t in np.arange(0.2, 1.3, 0.005):
    hit = tree.ray_cast(Vector((0.0, -5.0, ze - t * u)), Vector((0, 1, 0)), 10.0)[0]
    if hit is not None:
        prof.append((t, hit.y))
neck_y = prof[-1][1]
chin_t = next((float(t) for t, y in prof if y > neck_y - 0.05 * u), float("nan"))
json.dump({"eye_z_m": ze, "unit_m": u, "chin_t": round(chin_t, 4), "front": front, "side": side}, open(argv[1], "w"), indent=1)
print("outline", argv[0], "chin_t", round(chin_t, 3))
