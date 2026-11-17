"""T-049 hair study: cheap iteration previews of the head (Cycles, 4 samples + OIDN, 300 px, fibres hidden, one sun +
world light). Workbench/EEVEE need a GPU context that the headless container lacks. These are iteration aids, not
evidence: they are logged separately from the 24 evidence stills (tools/fidelity/run.py + groom_turnaround.py).

    blender -b --factory-startup -P preview.py -- <study.blend> <out.png> <centre_x,y,z> <ortho_width> [yaw,...]"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
blend, out, centre, width = argv[0], argv[1], Vector([float(x) for x in argv[2].split(",")]), float(argv[3])
yaws = [float(x) for x in argv[4].split(",")] if len(argv) > 4 else [0, -35, -90, 180]
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 4
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 3
sc.render.resolution_x = sc.render.resolution_y = 300
if sc.world is None:
    sc.world = bpy.data.worlds.new("pv")
sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.35, 0.37, 1)
sun = bpy.data.objects.new("pv_sun", bpy.data.lights.new("pv_sun", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
sc.collection.objects.link(sun)
for o in bpy.data.objects:
    if o.type == "CURVES":
        o.hide_render = True
cam_data = bpy.data.cameras.new("pv")
cam_data.type = "ORTHO"
cam_data.ortho_scale = width
cam = bpy.data.objects.new("pv", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
tiles = []
for i, yaw in enumerate(yaws):
    a = math.radians(yaw)
    d = Vector((math.sin(a), -math.cos(a), 0.12)).normalized()
    cam.location = centre + d * 2.0
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    p = out.replace(".png", f"_{i}.png")
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    tiles.append(p)
# stitch with Blender's image API (no PIL in the bpy venv guaranteed)
imgs = [bpy.data.images.load(p) for p in tiles]
W, H = imgs[0].size
strip = bpy.data.images.new("strip", W * len(imgs), H)
px = [0.0] * (W * len(imgs) * H * 4)
for k, im in enumerate(imgs):
    src = list(im.pixels)
    for y in range(H):
        row = src[y * W * 4:(y + 1) * W * 4]
        s = (y * W * len(imgs) + k * W) * 4
        px[s:s + W * 4] = row
strip.pixels = px
strip.filepath_raw = out
strip.file_format = "PNG"
strip.save()
for p in tiles:
    os.remove(p)
