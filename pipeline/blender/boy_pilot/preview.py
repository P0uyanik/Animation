"""Close-up previews of a pilot .blend (face front / three-quarter / side, full figure), same studio lighting as
the comparison harness.  blender -b -P pipeline/blender/boy_pilot/preview.py --
<subject.blend> <out_dir> [samples] [views] [max_width]"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
argv = sys.argv[sys.argv.index("--") + 1:]
subject, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
samples = int(argv[2]) if len(argv) > 2 else 32
wanted = argv[3].split(",") if len(argv) > 3 else None
max_width = int(argv[4]) if len(argv) > 4 else None
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(subject, link=False) as (src, dst):
    dst.objects = list(src.objects)
for o in dst.objects:
    if o is not None:
        bpy.context.scene.collection.objects.link(o)
scene = bpy.context.scene
world = bpy.data.worlds.new("Neutral")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.5, 0.5, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
for name, loc, energy, size in (("Key", (-1.6, -2.2, 2.4), 260, 1.6), ("Fill", (2.0, -1.8, 1.2), 90, 2.0), ("Rim", (0.6, 2.2, 2.0), 160, 1.2)):
    lt = bpy.data.lights.new(name, "AREA")
    lt.energy, lt.size = energy, size
    ob = bpy.data.objects.new(name, lt)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0, 0, 0.5)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.render.film_transparent = False
cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
scene.collection.objects.link(cam)
scene.camera = cam
views = {  # name: (yaw, elev, target, distance, focal, res)
    "face_front": (0, 4, (0, -0.05, 0.80), 0.95, 70, (600, 600)),
    "face_threequarter": (-35, 6, (0, -0.04, 0.82), 1.0, 70, (600, 600)),
    "face_side": (-90, 4, (0, 0.0, 0.82), 1.05, 70, (600, 600)),
    "full_front": (0, 6, (0, 0, 0.55), 2.3, 70, (500, 900)),
    "full_threequarter": (-35, 6, (0, 0, 0.55), 2.3, 70, (500, 900)),
    "full_back": (180, 6, (0, 0, 0.55), 2.3, 70, (500, 900)),
}
for name, (yaw, el, tgt, dist, focal, res) in views.items():
    if wanted and name not in wanted:
        continue
    d = Vector((math.sin(math.radians(yaw)) * math.cos(math.radians(el)), -math.cos(math.radians(yaw)) * math.cos(math.radians(el)),
                math.sin(math.radians(el))))
    cam.location = Vector(tgt) + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = focal
    if max_width and res[0] > max_width:
        scale = max_width / res[0]
        res = (max_width, round(res[1] * scale))
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = os.path.join(out, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("[preview]", name, flush=True)
