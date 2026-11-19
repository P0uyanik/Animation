"""T-091 iteration preview (NOT evidence): Workbench head views of a built character (geometry and silhouette only).

    blender -b --factory-startup -P wb_preview.py -- <blend> <out.jpg> [--yaws 0,35,90,180] [--px 300]
        [--fibres] [--head-yaw DEG]

Orthographic, studio matcap-free solid shading with cavity (channels read as dark creases); the camera is fitted to
the bounds of the hair + head objects. --head-yaw turns the head bone (head-turn check)."""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
blend, out = argv[0], argv[1]
opt = {"--yaws": "0,35,90,180", "--px": "300", "--head-yaw": "0"}
flags = set()
i = 2
while i < len(argv):
    if argv[i] in ("--fibres",):
        flags.add(argv[i])
        i += 1
    else:
        opt[argv[i]] = argv[i + 1]
        i += 2
yaws = [float(x) for x in opt["--yaws"].split(",")]
px = int(opt["--px"])
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
sc = bpy.context.scene
for o in bpy.data.objects:
    if o.type == "CURVES" and "--fibres" not in flags:
        o.hide_render = True
hy = float(opt["--head-yaw"])
rig = next((o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith("rig_")), None)
if hy and rig:
    pb = rig.pose.bones.get("head") or rig.pose.bones.get("DEF-spine.006") or rig.pose.bones.get("spine.006")
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = (0, math.radians(hy), 0)
    bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
pts = []
for o in bpy.data.objects:
    if o.type == "MESH" and (o.name.startswith("hair_") or o.name in ("body_skin", "head")) and not o.hide_render:
        e = o.evaluated_get(dg)
        mw = o.matrix_world
        vs = e.data.vertices
        step = max(1, len(vs) // 4000)
        pts += [mw @ vs[k].co for k in range(0, len(vs), step)]
hair_pts = []
for o in bpy.data.objects:
    if o.type == "MESH" and o.name.startswith("hair_"):
        e = o.evaluated_get(dg)
        mw = o.matrix_world
        vs = e.data.vertices
        step = max(1, len(vs) // 4000)
        hair_pts += [mw @ vs[k].co for k in range(0, len(vs), step)]
zmin = min(p.z for p in hair_pts) if hair_pts else 0.6
src = [p for p in pts if p.z > zmin - 0.05] or pts
lo = Vector((min(p.x for p in src), min(p.y for p in src), min(p.z for p in src)))
hi = Vector((max(p.x for p in src), max(p.y for p in src), max(p.z for p in src)))
centre = (lo + hi) / 2
size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z) * 1.08
if "--frame" in opt:  # fixed framing "cx,cy,cz,size" (same camera for every build)
    f = [float(x) for x in opt["--frame"].split(",")]
    centre, size = Vector(f[:3]), f[3]
print("FRAME", ",".join(f"{x:.3f}" for x in centre), f"{size:.3f}")
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.cavity_ridge_factor = 0.6
sh.cavity_valley_factor = 1.6
sh.show_shadows = True
sh.shadow_intensity = 0.4
sc.display.render_aa = "8"
sc.render.resolution_x = sc.render.resolution_y = px
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.world = sc.world or bpy.data.worlds.new("w")
cam = bpy.data.objects.new("pv", bpy.data.cameras.new("pv"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = size
sc.collection.objects.link(cam)
sc.camera = cam
el = math.radians(float(opt.get("--el", 6)))
tiles = []
for k, yaw in enumerate(yaws):
    a = math.radians(yaw)
    d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el))).normalized()
    cam.location = centre + d * 3.0
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    p = out + f".{k}.png"
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    tiles.append(p)
from PIL import Image  # noqa: E402

ims = [Image.open(p).convert("RGB") for p in tiles]
strip = Image.new("RGB", (px * len(ims), px))
for k, im in enumerate(ims):
    strip.paste(im, (k * px, 0))
strip.save(out, quality=88)
for p in tiles:
    os.remove(p)
print("WB", out)
