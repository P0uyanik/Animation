"""Diagnostic head close-ups (Workbench) + head-skin sections. args: blend outdir [hide_prefix,...]"""
import bpy, sys, math, json
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0]); out = a[1]; hide = a[2].split(",") if len(a) > 2 and a[2] else []
sc = bpy.context.scene
names = sorted(o.name for o in sc.objects)
print("OBJECTS", names)
for o in sc.objects:
    if any(o.name.startswith(h) for h in hide): o.hide_render = True
lm = {o.name: o.matrix_world.translation.copy() for o in sc.objects if o.name.startswith("LM_")}
print("LM", {k: [round(c, 4) for c in v] for k, v in lm.items()})
head = next(o for o in sc.objects if o.name in ("body_skin", "head"))
dg = bpy.context.evaluated_depsgraph_get(); ev = head.evaluated_get(dg); me = ev.to_mesh()
import numpy as np
P = np.array([ev.matrix_world @ v.co for v in me.vertices])
zs = [z for z in np.arange(0.69, 0.80, 0.01)]
sec = {}
for z in zs:
    m = (abs(P[:, 2] - z) < 0.004) & (P[:, 1] < 0.02)
    q = P[m]
    row = {}
    for yaw in (0, -35, -60, -90):
        t = math.radians(yaw)  # camera direction; screen x axis = (cos t, sin t)
        sx = q[:, 0] * math.cos(t) + q[:, 1] * math.sin(t)
        row[yaw] = [round(float(sx.min()), 4), round(float(sx.max()), 4)]
    row["ymin"] = round(float(q[:, 1].min()), 4); row["xmax"] = round(float(abs(q[:, 0]).max()), 4)
    sec[round(float(z), 3)] = row
json.dump(sec, open(out + "/sections.json", "w"), indent=1)
for z, r in sec.items(): print("SEC", z, r)
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "MATERIAL"
sc.display.shading.show_cavity = True; sc.display.shading.color_type = "SINGLE"; sc.display.shading.single_color = (0.8, 0.7, 0.65)
for o in sc.objects:
    for ps in getattr(o, "particle_systems", []): pass
    for m in o.modifiers:
        if m.type == "PARTICLE_SYSTEM": m.show_render = False
sc.render.resolution_x = 640; sc.render.resolution_y = 640; sc.render.film_transparent = False
cam = bpy.data.objects.new("dcam", bpy.data.cameras.new("dcam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 200
tgt = Vector((0, -0.02, 0.77)); dist = 2.6
YAWS = (0, -35, -60, -90)
for yaw in YAWS:
    t = math.radians(yaw)
    cam.location = tgt + Vector((-math.sin(t) * dist, -math.cos(t) * dist, 0.0))
    # yaw convention check: yaw 0 = front (camera at -y)
    d = tgt - cam.location; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{out}/yaw{yaw}.png"; bpy.ops.render.render(write_still=True)
