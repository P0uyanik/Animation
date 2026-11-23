"""T-219 H2: figure masks of a master .blend for the hair-silhouette measure (Workbench, flat, transparent film).

    blender -b --factory-startup -P docs/evaluation/characters/T-219/render_masks.py -- <out dir> <file.blend> \
        <label> <yaw>,<yaw>,... [--px 1024] [--lens 70] [--frame-height 1.25] [--target-z 0.55]

One camera distance and target for every view (a turnaround sheet has one scale): yaw 0 = camera in front, +90 = on
the character's left, 180 = behind. Writes <out>/<label>_<yaw>.png (alpha = figure) and <out>/<label>.json with the
projected eye centre (mean of the LM_eye_* landmarks, else of the eye.* meshes) per view, in pixels (y down)."""
import json
import math
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out, blend, label = os.path.abspath(argv[0]), os.path.abspath(argv[1]), argv[2]
yaws = [float(v) for v in argv[3].split(",")]
opt = {k: float(argv[argv.index(k) + 1]) for k in ("--px", "--lens", "--frame-height", "--target-z") if k in argv}
px, lens = int(opt.get("--px", 1024)), opt.get("--lens", 70.0)
fh, tz = opt.get("--frame-height", 1.25), opt.get("--target-z", 0.55)
os.makedirs(out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
rig = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
if rig is not None:
    for k in [k for k in rig.keys() if k.startswith("face_")]:
        rig[k] = 0.0
for o in list(sc.objects):
    if o.type in ("LIGHT", "CAMERA") or o.name.startswith(("LM_", "WGT-")) or "collider" in o.name:
        o.hide_render = True
cam = bpy.data.objects.new("T219_cam", bpy.data.cameras.new("T219_cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = lens, "VERTICAL", 36.0
fov = 2 * math.atan(18.0 / lens)
dist = fh / 2 / math.tan(fov / 2)
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"
sc.display.shading.color_type = "SINGLE"
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = px
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
lm = [o for o in bpy.data.objects if o.name.startswith("LM_eye")]
eyes = lm or [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("eye.")]
dg = bpy.context.evaluated_depsgraph_get()
pts = []
for o in eyes:
    if o.type == "MESH":
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        pts.append(sum(bb, Vector()) / 8)
    else:
        pts.append(o.matrix_world.translation.copy())
eye = sum(pts, Vector()) / len(pts)
target = Vector((0.0, 0.0, tz))
rep = {"blend": os.path.basename(blend), "px": px, "lens": lens, "frame_height_m": fh, "target_z": tz,
       "eye_sources": sorted(o.name for o in eyes), "eye_world": list(eye), "views": {}}
for y in yaws:
    a = math.radians(y)
    d = Vector((math.sin(a), -math.cos(a), 0.0))  # yaw 0: camera at -Y (front); +90: camera at +X (her left)
    cam.location = target + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    p = world_to_camera_view(sc, cam, eye)
    f = os.path.join(out, f"{label}_{int(y)}.png")
    sc.render.filepath = f
    bpy.ops.render.render(write_still=True)
    rep["views"][str(int(y))] = {"png": os.path.basename(f), "eye_px": [p.x * px, (1 - p.y) * px]}
json.dump(rep, open(os.path.join(out, f"{label}.json"), "w"), indent=1)
print("MASKS", json.dumps(rep["views"]))
