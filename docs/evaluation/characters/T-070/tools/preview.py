"""T-044 iteration previews (NOT evidence): head views of a hair v3 build with the shared character_neutral/1
lighting, fibres on, Cycles low samples + OIDN, orthographic.

    blender -b --factory-startup -P preview.py -- <blend> <out.png> <cx,cy,cz> <ortho_width> [yaw,...] [--px N]
        [--spp N] [--el DEG] [--tall H/W]
Yaw 0 = front, positive = camera towards the character's left. Tiles are stitched side by side (PIL)."""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
opt = {}
for k in ("--px", "--spp", "--el", "--tall"):
    if k in argv:
        i = argv.index(k)
        opt[k] = float(argv[i + 1])
        del argv[i:i + 2]
blend, out, centre, width = argv[0], argv[1], Vector([float(x) for x in argv[2].split(",")]), float(argv[3])
yaws = [float(x) for x in argv[4].split(",")] if len(argv) > 4 else [0, 35, 90, 180]
px = int(opt.get("--px", 360))
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
sc = bpy.context.scene
lrig = RC.apply(sc, RC.load(RC.DEFAULT))
render_engine.configure(sc, "cycles", int(opt.get("--spp", 8)), cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
tall = opt.get("--tall", 1.0)
sc.render.resolution_x = px
sc.render.resolution_y = int(px * tall)
sc.render.resolution_percentage = 100
cam = bpy.data.objects.new("pv", bpy.data.cameras.new("pv"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = width
sc.collection.objects.link(cam)
sc.camera = cam
el = math.radians(opt.get("--el", 4.0))
tiles = []
for i, yaw in enumerate(yaws):
    a = math.radians(yaw)
    d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el))).normalized()
    cam.location = centre + d * 2.0
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    RC.orient(lrig, d)
    p = out.replace(".png", f"_{i}.png")
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    tiles.append(p)
from PIL import Image  # noqa: E402,I001
ims = [Image.open(p) for p in tiles]
strip = Image.new("RGB", (px * len(ims), int(px * tall)))
for k, im in enumerate(ims):
    strip.paste(im.convert("RGB"), (k * px, 0))
strip.save(out)
for p in tiles:
    os.remove(p)
