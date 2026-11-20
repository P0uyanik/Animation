"""T-159 Part A: temple close-ups of a master (3/4 and side, 100 % pixels, no resampling).

    blender -b --factory-startup -P docs/evaluation/characters/T-159/tools/temple_views.py -- <master.blend> <out dir> [full,clay]

full: the master's own materials and hair. clay: skin only (hair and accessories hidden), one grey material and a
grazing key light, so the surface relief at the temple reads directly. Orthographic, 0.20 m frame, 640 px, centred
between the outer eye corner and the ear at the eye line. Read-only."""
import math
import os
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = a[1]
want = a[2].split(",") if len(a) > 2 else ["full", "clay"]
sc = bpy.context.scene
eye = bpy.data.objects["LM_eye_L"].matrix_world.translation
ear = bpy.data.objects["LM_ear_L"].matrix_world.translation
tgt = Vector((ear.x * 0.8, (eye.y + ear.y) / 2, eye.z + 0.01))
clay = bpy.data.materials.new("t159_clay")
clay.use_nodes = True
bsdf = clay.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.62, 0.55, 0.5, 1)
bsdf.inputs["Roughness"].default_value = 0.6
sc.render.engine = "CYCLES"
sc.cycles.samples = 32
sc.cycles.use_denoising = True
sc.cycles.seed = 0
sc.render.resolution_x = sc.render.resolution_y = 640
sc.render.resolution_percentage = 100
sc.render.threads_mode = "FIXED"
sc.render.threads = int(os.environ.get("T159_THREADS", "2"))
w = bpy.data.worlds.new("t159_world")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.3, 0.32, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.7
for o in bpy.data.objects:
    if o.type == "LIGHT":
        o.hide_render = True
ld = bpy.data.lights.new("t159_key", "SUN")
ld.energy = 3.0
ld.angle = 0.25
lo = bpy.data.objects.new("t159_key", ld)
sc.collection.objects.link(lo)
cd = bpy.data.cameras.new("t159_cam")
cd.type = "ORTHO"
cd.ortho_scale = 0.20
co = bpy.data.objects.new("t159_cam", cd)
sc.collection.objects.link(co)
sc.camera = co


def look(obj, frm, to):
    obj.location = frm
    obj.rotation_euler = (to - frm).to_track_quat("-Z", "Y").to_euler()


HIDE = {"full": ("LM_",), "clay": ("LM_", "hair_", "glasses", "garment.")}
for mode in want:
    for o in bpy.data.objects:
        if o.type in ("MESH", "CURVE", "CURVES"):
            o.hide_render = o.name.startswith(HIDE[mode])
    sc.view_layers[0].material_override = clay if mode == "clay" else None
    for name, az in (("3q", 45.0), ("side", 90.0)):
        r = math.radians(az)
        look(co, tgt + Vector((math.sin(r), -math.cos(r), 0.08)) * 1.5, tgt)
        g = r - (0.9 if mode == "clay" else 0.5)  # clay: grazing light from the front, across the temple
        look(lo, tgt + Vector((math.sin(g) * 2, -math.cos(g) * 2, 0.9)), tgt)
        sc.render.filepath = os.path.join(out, f"{mode}_{name}.png")
        bpy.ops.render.render(write_still=True)
