"""T-160 turntable scene for the flicker check (Blender side; the input .blend is not changed).

    blender -b --factory-startup -P turntable_blend.py -- <master.blend> <out.blend> <target z> <frame height m>
        <aspect> <px> <frames> <deg per frame> <start yaw deg> <samples>

Opens a built master, parents every root object of the character to one empty and keys a slow, even turn of that
empty about the vertical axis (so the hair moves under a fixed camera and the fixed character_neutral/1 light, as a
head turn does in a shot). Production render settings: Cycles, OIDN, fixed seed (as the shots; samples as given).
Saves the scene as <out.blend> for tools/motion_checks/render_passes.py."""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:]
src, dst = a[0], a[1]
tz, fh, aspect, px, frames, step, yaw0, spp = (float(a[2]), float(a[3]), float(a[4]), int(a[5]), int(a[6]),
                                               float(a[7]), float(a[8]), int(a[9]))
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(src))
sc = bpy.context.scene
for o in list(sc.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
rig = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
if rig is not None:
    for k in [k for k in rig.keys() if k.startswith("face_")]:
        rig[k] = 0.0
turn = bpy.data.objects.new("turntable", None)
sc.collection.objects.link(turn)
bpy.context.view_layer.update()
for o in list(sc.objects):
    if o is not turn and o.parent is None:
        mw = o.matrix_world.copy()
        o.parent = turn
        o.matrix_world = mw
lrig = RC.apply(sc, RC.load(RC.DEFAULT))
d = Vector((0.0, -1.0, 0.0))
RC.orient(lrig, d)
render_engine.configure(sc, "cycles", spp, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
sc.cycles.seed = 0
sc.cycles.use_animated_seed = False
cam = bpy.data.objects.new("TurnCam", bpy.data.cameras.new("TurnCam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height, cam.data.clip_start = 70.0, "VERTICAL", 36.0, 0.01
el = math.radians(6.0)
dv = Vector((0.0, -math.cos(el), math.sin(el)))
cam.location = Vector((0.0, 0.0, tz)) + dv * (fh / 2 / math.tan(math.atan(36.0 / 2 / 70.0)))
cam.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = px, int(round(px * aspect)), 100
sc.frame_start, sc.frame_end = 1, frames
for f in range(0, frames + 2):  # one key before and after the range: even motion at both ends
    turn.rotation_euler = (0.0, 0.0, math.radians(yaw0 + step * (f - 1)))
    turn.keyframe_insert("rotation_euler", frame=f)
act = turn.animation_data.action
for fc in getattr(act, "fcurves", []):
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(dst), copy=True)
print("[turntable_blend] saved", dst, "frames", frames, "deg/frame", step)
