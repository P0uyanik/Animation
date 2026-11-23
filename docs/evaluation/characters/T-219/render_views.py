"""T-219 sheet renders of one master .blend with the DEFAULT FINAL render profile (render_profiles.json
"default_profile"; plush_soft once T-220 makes it the default), T-202/T-207 camera (70 mm) and character_neutral/1
light oriented to the camera, neutral face, master A-pose.

    blender -b --factory-startup -P docs/evaluation/characters/T-219/render_views.py -- <out dir> <file.blend> \
        <label> <target x,y,z> <frame_height_m> <yaw:elev>,... [--px N] [--profile NAME] [--samples N]

The profile's samples, Cycles/render blocks and compositor look are applied; the tile resolution is --px square
(the profile's 1280x720 frame is a shot format, not a sheet tile). --samples only for previews (recorded).
Writes <out>/<label>_<yaw>.png and <out>/<label>.json (profile, seconds per view)."""
import json
import math
import os
import sys
import time

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
opt = {k: argv[argv.index(k) + 1] for k in ("--px", "--profile", "--samples") if k in argv}
px = int(opt.get("--px", 768))
profiles = json.load(open(os.path.join(ROOT, "pipeline", "charsys", "render_profiles.json")))
pname = opt.get("--profile", profiles["default_profile"])
profile = profiles["profiles"][pname]
spp = int(opt.get("--samples", profile.get("samples", 128)))

bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for k in [k for k in rig.keys() if k.startswith("face_")]:
    rig[k] = 0.0
for o in list(sc.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
lrig = RC.apply(sc, RC.load(RC.DEFAULT))
render_engine.configure(sc, "cycles", spp, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
applied = render_engine.apply_profile(sc, profile)
sc.cycles.samples = spp
sc.cycles.seed = 0
sc.render.threads_mode = "AUTO"
cam = bpy.data.objects.new("ShotCam", bpy.data.cameras.new("ShotCam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 70.0, "VERTICAL", 36.0
fov = 2 * math.atan(18.0 / 70.0)
log = {"label": label, "blend": os.path.basename(blend), "px": px, "profile": pname, "spp": spp,
       "applied": {k: str(v)[:80] for k, v in applied.items()}, "seconds": {}}
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
    t = time.time()
    bpy.ops.render.render(write_still=True)
    log["seconds"]["%+04d" % round(yaw)] = round(time.time() - t, 1)
json.dump(log, open(os.path.join(out, label + ".json"), "w"), indent=1, sort_keys=True)
print("T219", json.dumps(log))
