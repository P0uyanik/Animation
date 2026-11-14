"""Facial-control test on a master .blend (headless Blender; read-only on the input).

    blender -b --factory-startup -P pipeline/charsys/tests/face_test.py -- <master.blend> <out_dir>

Drives the rig's facial controls (face_*) and measures, per expression:
  eye_visible_pct   share of front rays over the eye opening that hit the eyeball (Blink should be ~0, open ~ v6)
  lid_proud_mm      how far the closed upper lid stands out of the eyeball surface (bulge)
  mouth_open_mm     vertical opening between the lips at the centre (JawOpen)
  corner_lift_mm    mouth-corner rise relative to the centre (Smile)
Renders a close-up grid (rows: neutral, Blink, Smile, JawOpen; columns: front, three-quarter) -> face_test.png,
numbers -> face_test.json."""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
sc = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "face_Blink" in o.keys())
eye = bpy.data.objects["eye.L"]
deps = bpy.context.evaluated_depsgraph_get


def setf(**kw):
    for k in ("face_Blink", "face_BrowDown", "face_Smile", "face_JawOpen"):
        rig[k] = float(kw.get(k, 0.0))
    rig.update_tag()
    bpy.context.view_layer.update()


def world_verts(name):
    o = bpy.data.objects[name]
    ev = o.evaluated_get(deps())
    me = ev.to_mesh()
    co = np.array([o.matrix_world @ v.co for v in me.vertices])
    ev.to_mesh_clear()
    return co


def eye_visible():
    c = eye.matrix_world.translation
    r = eye.dimensions.x / 2
    hit = tot = 0
    for i in range(-6, 7):
        for j in range(-6, 7):
            dx, dz = i / 6 * r * 0.8, j / 6 * r * 0.8
            if dx * dx + dz * dz > (0.8 * r) ** 2:
                continue
            o = Vector((c.x + dx, c.y - 0.5, c.z + dz))
            ok, loc, nrm, idx, ob, mat = sc.ray_cast(deps(), o, Vector((0, 1, 0)))
            tot += 1
            hit += bool(ok and ob is not None and ob.name == "eye.L")
    return 100.0 * hit / tot


def metrics():
    c = np.array(eye.matrix_world.translation)
    r = eye.dimensions.x / 2
    lid = world_verts("lid_upper.L")
    front = lid[(lid[:, 1] - c[1]) < -0.3 * r]
    proud = (np.linalg.norm(front - c, axis=1) - r).max() * 1000 if len(front) else 0.0
    m = world_verts("mouth")
    xs = m[:, 0]
    mid = m[np.abs(xs) < 0.002]
    corner = m[np.abs(xs) > xs.max() * 0.9]
    return {"eye_visible_pct": round(eye_visible(), 1), "lid_proud_mm": round(float(proud), 2),
            "mouth_open_mm": round(float((mid[:, 2].max() - mid[:, 2].min()) * 1000), 2),
            "corner_lift_mm": round(float((corner[:, 2].mean() - mid[:, 2].mean()) * 1000), 2)}


STATES = [("neutral", {}), ("Blink", {"face_Blink": 1}), ("Smile", {"face_Smile": 1}), ("JawOpen", {"face_JawOpen": 1})]
res = {}
for name, kw in STATES:
    setf(**kw)
    res[name] = metrics()
    print("[face_test]", name, res[name], flush=True)

# close-up renders
sc.render.engine = "CYCLES"
sc.cycles.samples = 24
sc.render.resolution_x = sc.render.resolution_y = 320
sc.render.film_transparent = False
if sc.world is None:
    sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.55, 0.55, 0.55)
for o in bpy.data.objects:
    if o.name.startswith(("WGT-", "fur_")):
        o.hide_render = True
cam = bpy.data.objects.new("face_cam", bpy.data.cameras.new("face_cam"))
cam.data.lens = 85
sc.collection.objects.link(cam)
sc.camera = cam
sun = bpy.data.objects.new("face_sun", bpy.data.lights.new("face_sun", "SUN"))
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(55), 0, math.radians(-25))
sc.collection.objects.link(sun)
target = Vector((0, -0.10, 0.765))
views = {"front": Vector((0, -1.0, 0.80)), "threequarter": Vector((0.62, -0.78, 0.82))}
tiles = []
for name, kw in STATES:
    setf(**kw)
    row = []
    for vn, pos in views.items():
        cam.location = pos
        cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
        p = os.path.join(OUT, f"_{name}_{vn}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        row.append(p)
    tiles.append(row)
try:
    from PIL import Image, ImageDraw
    W = 320
    img = Image.new("RGB", (W * 2, W * len(tiles)))
    d = ImageDraw.Draw(img)
    for i, row in enumerate(tiles):
        for j, p in enumerate(row):
            img.paste(Image.open(p).convert("RGB"), (j * W, i * W))
            os.remove(p)
        m = res[STATES[i][0]]
        d.text((6, i * W + 6), f"{STATES[i][0]}  eye {m['eye_visible_pct']}%  lid {m['lid_proud_mm']} mm  "
                               f"open {m['mouth_open_mm']} mm  corner {m['corner_lift_mm']} mm", fill=(255, 255, 255))
    img.save(os.path.join(OUT, "face_test.png"))
except ImportError:  # Pillow missing inside Blender's Python: keep the separate tiles
    pass
json.dump({"source": SRC, "blender": bpy.app.version_string, "states": res}, open(os.path.join(OUT, "face_test.json"), "w"), indent=1)
print("[face_test] ->", OUT)
