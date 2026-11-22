"""T-207 review renders of one (possibly flock-processed) .blend: neutral face, Cycles, T-202 camera and light
(character_neutral/1, 70 mm, light oriented to the camera), master A-pose.

    blender -b --factory-startup -P docs/evaluation/characters/T-207/render_views.py -- <out dir> <file.blend> \
        <label> <target x,y,z> <frame_height_m> <yaw:elev>,... [--samples N] [--px N] [--crop x0,y0,x1,y1:name ...]

Writes <out>/<label>_<yaw>.png per view and <out>/<label>.json (seconds per frame, strand counts and hash of the
evaluated "*.flock*" / "*.hair_curves*" objects). Yaw 0 = camera in front, +90 = camera on the character's left,
180 = back. Renders use all cores and seed 0: for looking at, not bit-exact."""
import hashlib
import json
import math
import os
import sys
import time

import bpy
import numpy as np
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
opt = {k: argv[argv.index(k) + 1] for k in ("--samples", "--px") if k in argv}
spp, px = int(opt.get("--samples", 16)), int(opt.get("--px", 768))

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
sc.cycles.seed = 0
sc.render.threads_mode = "AUTO"
cam = bpy.data.objects.new("ShotCam", bpy.data.cameras.new("ShotCam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 70.0, "VERTICAL", 36.0
fov = 2 * math.atan(18.0 / 70.0)
dg = bpy.context.evaluated_depsgraph_get()
log = {"label": label, "blend": os.path.basename(blend), "px": px, "spp": spp, "hair_strands": 0, "seconds": {}}
h = hashlib.sha256()
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type == "CURVES" and o.name.startswith("hair") and not o.hide_render:
        ev = o.evaluated_get(dg).data
        log["hair_strands"] += len(ev.curves)
        if ".flock" in o.name or ".hair_curves" in o.name:
            p = np.zeros(len(ev.points) * 3, dtype=np.float32)
            ev.points.foreach_get("position", p)
            h.update(o.name.encode() + p.tobytes())
log["added_strands_sha"] = h.hexdigest()[:16]
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
print("T207", json.dumps(log))
