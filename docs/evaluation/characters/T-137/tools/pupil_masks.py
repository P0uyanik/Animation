"""T-137 pupil ID masks of one character master at shot size (640 x 360), for tools/review/readability.py.

    blender -b --factory-startup <master.blend> -P pupil_masks.py -- <out dir>

Uses the T-123 ID material unchanged (docs/evaluation/tools/T-123/render_masks.material: the painted pupil disc on the
front half of each eyeball, from spec.resolved.json next to the master). Left pupil = 51, right = 102. The glasses lens
is hidden as in T-123 (rims and lids still occlude). Frame 1: medium shot, 0.60 m frame height; frame 2: wide, 1.30 m.
cup_only/ frames are black (no cup): the cup columns of the report are undefined."""
import importlib.util
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
spec = importlib.util.spec_from_file_location("render_masks", os.path.join(ROOT, "docs/evaluation/tools/T-123/render_masks.py"))
RM = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RM)

out = sys.argv[sys.argv.index("--") + 1]
cfg = json.load(open(os.path.join(os.path.dirname(bpy.data.filepath), "spec.resolved.json")))["face"]["eyes"]
sc = bpy.context.scene
for o in list(sc.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for k in [k for k in rig.keys() if k.startswith("face_")]:
    rig[k] = 0.0
for o in sc.objects:
    o.pass_index = 0
    o.hide_render = "fur" in o.name.lower() or "lens" in o.name.lower() or o.name.startswith(("WGT", "garment.collider"))
for side, label in (("L", 51), ("R", 102)):
    bpy.data.objects[f"eye.{side}"].pass_index = label
sc.view_layers[0].material_override = RM.material([((51, 102), cfg)])
sc.world = bpy.data.worlds.new("Black")
sc.world.use_nodes = True
sc.world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0
sc.render.engine = "CYCLES"
sc.cycles.samples, sc.cycles.device, sc.cycles.max_bounces = 1, "CPU", 0
sc.cycles.use_denoising = sc.cycles.use_adaptive_sampling = False
sc.cycles.pixel_filter_type, sc.cycles.seed = "BOX", 0
sc.render.use_motion_blur = sc.render.film_transparent = sc.render.use_compositing = False
sc.view_settings.view_transform, sc.view_settings.look = "Raw", "None"
sc.view_settings.exposure, sc.view_settings.gamma, sc.render.dither_intensity = 0, 1, 0
im = sc.render.image_settings
im.file_format, im.color_mode, im.color_depth = "PNG", "BW", "8"
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 640, 360, 100
cam = bpy.data.objects.new("ShotSizeCam", bpy.data.cameras.new("ShotSizeCam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 50.0, "VERTICAL", 24.0
c = sum((bpy.data.objects[f"eye.{s}"].matrix_world.translation for s in ("L", "R")), Vector()) / 2
fov = 2 * math.atan(24.0 / 2 / 50.0)
os.makedirs(os.path.join(out, "cup_only"), exist_ok=True)
for frame, fh in ((1, 0.60), (2, 1.30)):
    cam.location = Vector((0.0, c.y - fh / 2 / math.tan(fov / 2), c.z))
    cam.rotation_euler = (math.pi / 2, 0, 0)
    sc.render.filepath = os.path.join(out, "visible", f"frame_{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    Image.new("L", (640, 360), 0).save(os.path.join(out, "cup_only", f"frame_{frame:04d}.png"))
