"""T-194 sheet crop: renders only a region of a shot.blend frame around a character's head (shot camera).

    python3 tools/bpy_blender.py -b --factory-startup -P crop_render.py -- <shot.blend> <frame> <rig substring> <out.png>
        [--half=0.12] [--samples=32] [--res=1920x1080] [--bone=head]

--half: half-size of the square around the head point, in metres at the head (projected)."""
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view

a = sys.argv[sys.argv.index("--") + 1:]
blend, frame, who, out = a[0], int(a[1]), a[2], a[3]
o = dict(x[2:].split("=", 1) for x in a[4:] if x.startswith("--"))
half = float(o.get("half", "0.12"))
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.frame_set(frame)
rig = next(ob for ob in sc.objects if ob.type == "ARMATURE" and who in ob.name)
pb = rig.pose.bones.get(o.get("bone", "head")) or rig.pose.bones.get("DEF-head") or rig.pose.bones.get("ORG-head")
p = rig.matrix_world @ ((pb.head + pb.tail) / 2)
cam = sc.camera
w, h = (int(x) for x in o.get("res", "1920x1080").split("x"))
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
c = world_to_camera_view(sc, cam, p)
right = cam.matrix_world.to_3x3().col[0].normalized()
c2 = world_to_camera_view(sc, cam, p + right * half)
dx = abs(c2.x - c.x)
dy = dx * w / h
sc.render.use_border, sc.render.use_crop_to_border = True, True
sc.render.border_min_x, sc.render.border_max_x = max(0.0, c.x - dx), min(1.0, c.x + dx)
sc.render.border_min_y, sc.render.border_max_y = max(0.0, c.y - dy), min(1.0, c.y + dy)
if sc.render.engine == "CYCLES":
    sc.cycles.samples = int(o.get("samples", "32"))
sc.render.filepath = out
sc.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
print("CROP", out, round(c.x, 3), round(c.y, 3), round(dx, 3))
