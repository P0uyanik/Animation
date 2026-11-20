"""T-159 Part B: ear close-ups of a master (front, 3/4, side; orthographic, 100 % pixels).

    blender -b --factory-startup -P docs/evaluation/characters/T-159/tools/ear_views.py -- <master.blend> <out dir> [preview|full]

preview: hair fibre objects (*.fibres*) hidden, 16 samples (cheap; the felt hair volumes still show the coverage).
full: everything, 48 samples. Frame 0.22 m / 512 px centred on the character's left ear. Read-only."""
import math
import os
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = a[1]
mode = a[2] if len(a) > 2 else "preview"
sc = bpy.context.scene
ear = bpy.data.objects["LM_ear_L"].matrix_world.translation
tgt = Vector((ear.x * 0.85, ear.y - 0.02, ear.z))
sc.render.engine = "CYCLES"
sc.cycles.samples = 16 if mode == "preview" else 48
sc.cycles.use_denoising = True
sc.cycles.seed = 0
sc.render.resolution_x = sc.render.resolution_y = 512
sc.render.resolution_percentage = 100
sc.render.threads_mode = "FIXED"
sc.render.threads = int(os.environ.get("T159_THREADS", "2"))
w = bpy.data.worlds.new("t159_world")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.3, 0.32, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
for o in bpy.data.objects:
    if o.type == "LIGHT":
        o.hide_render = True
    elif o.name.startswith("LM_") or (mode == "preview" and ".fibres" in o.name):
        o.hide_render = True
ld = bpy.data.lights.new("t159_key", "SUN")
ld.energy = 3.0
ld.angle = 0.25
lo = bpy.data.objects.new("t159_key", ld)
sc.collection.objects.link(lo)
cd = bpy.data.cameras.new("t159_cam")
cd.type = "ORTHO"
cd.ortho_scale = 0.22
co = bpy.data.objects.new("t159_cam", cd)
sc.collection.objects.link(co)
sc.camera = co


def look(obj, frm, to):
    obj.location = frm
    obj.rotation_euler = (to - frm).to_track_quat("-Z", "Y").to_euler()


for name, az in (("front", 0.0), ("3q", 45.0), ("side", 90.0)):
    r = math.radians(az)
    look(co, tgt + Vector((math.sin(r), -math.cos(r), 0.05)) * 1.5, tgt)
    g = r - 0.5
    look(lo, tgt + Vector((math.sin(g) * 2, -math.cos(g) * 2, 0.9)), tgt)
    sc.render.filepath = os.path.join(out, f"ear_{name}.png")
    bpy.ops.render.render(write_still=True)
