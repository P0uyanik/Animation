"""T-093 criterion 3 evidence: the vest flare in reach, before (corrective keys muted) and after (driven by the pose).

    blender -b --factory-startup -P docs/evaluation/characters/T-093/reach_evidence.py -- <candidate master.blend> <out dir>
        [--samples 16] [--px 420]

Poses: rest (A-pose master), arms down (the compare rotation, keys must stay 0) and reach (FK upper arms rotated
-75 deg about world X: forward). Measures the vest flare (garments_v2.evaluate.flare: distance of the vest's main
piece to the posed torso skin; max / p99 / p95) and renders the reach pose from the side (yaw 90, the side the
owner asked for) and at 3/4 front, before and after. Hair is hidden in these renders only (the curls cover the vest
in the side view); nothing else changes. Writes <out>/reach.json and <out>/reach_before_after.jpg."""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402
from garments_v2 import evaluate as EV  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
blend, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
spp = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 16
px = int(argv[argv.index("--px") + 1]) if "--px" in argv else 420
os.makedirs(out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.name.startswith("body_skin") and o.type == "MESH")
vest = [o for o in bpy.data.objects if o.get("ps_garment_item") == "vest" and o.type == "MESH"]
main = bpy.data.objects["garment.vest.main"]
for k in [k for k in rig.keys() if k.startswith("face_")]:
    rig[k] = 0.0

res = {"blend": os.path.basename(blend), "blender": bpy.app.version_string, "reach": {"axis": "X", "deg": -75.0},
       "metric": "distance of garment.vest.main vertices (evaluated) to the posed torso skin, metres"}
res["rest"] = {"keys": EV.key_values(vest), "flare": EV.flare(body, main)}
EV.rotate_upper_arms(rig, 35.0, axis="Y", mirror=True)
res["arms_down"] = {"keys": EV.key_values(vest), "flare": EV.flare(body, main)}
EV.rest(rig)
EV.rotate_upper_arms(rig, -75.0, axis="X")
res["reach_keys"] = EV.key_values(vest)
EV.mute(vest, True)
res["before"] = EV.flare(body, main)
EV.mute(vest, False)
res["after"] = EV.flare(body, main)

# renders: reach pose, hair hidden, before / after
for o in bpy.data.objects:
    if o.name.startswith("hair") and o.type in ("MESH", "CURVES"):
        o.hide_render = True
for o in list(sc.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
lrig = RC.apply(sc, RC.load(RC.DEFAULT))
render_engine.configure(sc, "cycles", spp, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
sc.cycles.seed = 0
cam = bpy.data.objects.new("EvidenceCam", bpy.data.cameras.new("EvidenceCam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens, cam.data.sensor_fit, cam.data.sensor_height = 70.0, "VERTICAL", 36.0
fov = 2 * math.atan(18.0 / 70.0)
target, frame_h = Vector((0.0, -0.05, 0.5)), 0.42
shots = []
for state, muted in (("before", True), ("after", False)):
    EV.mute(vest, muted)
    for view, yaw in (("side", 90.0), ("threequarter", 40.0)):
        a, el = math.radians(yaw), math.radians(6.0)
        d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
        cam.location = target + d * (frame_h / 2 / math.tan(fov / 2))
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        RC.orient(lrig, d)
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = px, px, 100
        sc.render.image_settings.file_format = "PNG"
        path = os.path.join(out, f"reach_{view}_{state}.png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        shots.append((state, view, path))
json.dump(res, open(os.path.join(out, "reach.json"), "w"), indent=1)

try:
    from PIL import Image, ImageDraw
    ims = {(s, v): Image.open(p).convert("RGB") for s, v, p in shots}
    W = H = px
    sheet = Image.new("RGB", (2 * W, 2 * H + 28), (30, 30, 30))
    dr = ImageDraw.Draw(sheet)
    for c, view in enumerate(("side", "threequarter")):
        for r, state in enumerate(("before", "after")):
            sheet.paste(ims[(state, view)], (c * W, 28 + r * H))
            f = res[state]
            dr.text((c * W + 6, 28 + r * H + 6), f"{state} | {view} | max {f['max'] * 100:.1f} cm  p99 {f['p99'] * 100:.1f} cm",
                    fill=(255, 255, 255))
    dr.text((6, 8), "T-093 vest reach (arms -75 deg about X), hair hidden; before = corrective keys muted, after = driven",
            fill=(255, 255, 255))
    sheet.save(os.path.join(out, "reach_before_after.jpg"), quality=90)
except ImportError:
    pass
print("REACH", json.dumps({k: res[k] for k in ("rest", "before", "after")}))
