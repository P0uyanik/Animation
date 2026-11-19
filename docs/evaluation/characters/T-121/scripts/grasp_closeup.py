"""Close-up of hand.L curled around a cup proxy: rigify finger FK controls at the T-051-like full-grasp curl."""
import sys, math, bpy
from mathutils import Vector, Matrix
master, out, curl_scale = sys.argv[-3], sys.argv[-2], float(sys.argv[-1])
bpy.ops.wm.open_mainfile(filepath=master)
rig = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
hand = bpy.data.objects["hand.L"]
for o in bpy.data.objects:  # keep the left hand, the forearm skin and the sleeve
    if o.type in ("MESH", "CURVES") and o.name != "hand.L":
        o.hide_render = True
sc = bpy.context.scene
curls = {".01": 40, ".02": 50, ".03": 35}
for n in ("f_index", "f_middle", "f_ring", "f_pinky"):
    for seg, a in curls.items():
        pb = rig.pose.bones.get(f"{n}{seg}.L")
        pb.rotation_mode = "XYZ"; pb.rotation_euler.x = math.radians(a * curl_scale)
for seg, a in ((".02", 25), (".03", 25)):
    pb = rig.pose.bones.get(f"thumb{seg}.L"); pb.rotation_mode = "XYZ"; pb.rotation_euler.x = math.radians(a * curl_scale)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = hand.evaluated_get(dg)
import numpy as np
co = np.array([tuple(hand.matrix_world @ v.co) for v in ev.data.vertices])
c = Vector(co.mean(axis=0)); ext = float(np.linalg.norm(co.max(0) - co.min(0)))
h = rig.pose.bones["hand_fk.L"] if "hand_fk.L" in rig.pose.bones else rig.pose.bones["hand_ik.L"]
d = (rig.matrix_world @ h.tail - rig.matrix_world @ h.head).normalized()
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
tips = Vector(np.mean([tuple(rig.matrix_world @ rig.pose.bones[f"{n}.03.L"].tail) for n in ("f_index", "f_middle", "f_ring", "f_pinky")], axis=0))
view = ((tips - c).normalized() * 0.8 + Vector((0, -1, 0)) * 0.6 + d * 0.3).normalized()
cam.location = c + view * ext * 4.2
cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = 85
for loc, e in (((1, -1, 1.5), 3.0), ((-1, -0.5, 0.5), 1.0)):
    l = bpy.data.objects.new("l", bpy.data.lights.new("l", "SUN")); l.data.energy = e; sc.collection.objects.link(l)
    l.rotation_euler = (-Vector(loc)).to_track_quat("-Z", "Y").to_euler()
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.3, 0.3, 0.32)
sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.device = "CPU"
sc.render.resolution_x = sc.render.resolution_y = 520; sc.render.film_transparent = False
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
