"""T-216 copy of T-202 face_views.py with one extra option: --face "Name=w,Name=w" sets those face_<Name> controls
after the neutral reset (expression strip). Otherwise identical (T-202 face close-ups of a released master: neutral expression, Cycles, camera/light as T-155 crops.py
(character_neutral/1 light, 70 mm lens, orient light to camera), no pose (master A-pose; head unaffected).

    blender -b --factory-startup -P docs/evaluation/characters/T-202/face_views.py -- <out dir> <master.blend> \
        <label> <target x,y,z> <frame_height_m> <yaw:elev>,... [--samples N] [--px N]

Writes <out>/<label>_<yaw>.png per view. Yaw convention: 0 = camera in front, +90 = camera on the character's left.)"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
out, blend, label = os.path.abspath(argv[0]), os.path.abspath(argv[1]), argv[2]
target = Vector([float(v) for v in argv[3].split(",")])
fh = float(argv[4])
views = [tuple(float(x) for x in v.split(":")) for v in argv[5].split(",")]
opt = {k: argv[argv.index(k) + 1] for k in ("--samples", "--px", "--face") if k in argv}
spp, px = int(opt.get("--samples", 64)), int(opt.get("--px", 1024))

bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for k in [k for k in rig.keys() if k.startswith("face_")]:
    rig[k] = 0.0  # neutral expression
for kv in filter(None, opt.get("--face", "").split(",")):
    name, w = kv.split("=")
    rig[f"face_{name}"] = float(w)
rig.update_tag()
bpy.context.view_layer.update()
for o in list(sc.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
lrig = RC.apply(sc, RC.load(RC.DEFAULT))
render_engine.configure(sc, "cycles", spp, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
sc.cycles.seed = 0
sc.render.threads_mode = "AUTO"  # configure() pins 1 thread for determinism; review renders use all cores
cam = bpy.data.objects.new("ShotCam", bpy.data.cameras.new("ShotCam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 70.0, "VERTICAL", 36.0
fov = 2 * math.atan(18.0 / 70.0)
os.makedirs(out, exist_ok=True)
for yaw, elev in views:
    a, el = math.radians(yaw), math.radians(elev)
    d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
    cam.location = target + d * (fh / 2 / math.tan(fov / 2))
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    RC.orient(lrig, d)
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = px, px, 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(out, "%s_%+04d.png" % (label, round(yaw)))
    bpy.ops.render.render(write_still=True)
