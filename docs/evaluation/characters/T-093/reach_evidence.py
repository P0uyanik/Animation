"""T-093 criterion 3 evidence: the girl's vest in the reach pose, published 0.11.0 against the garment/2 candidate.

    blender -b --factory-startup -P docs/evaluation/characters/T-093/reach_evidence.py -- <out dir>
        <label>=<master.blend>[:muted] ... [--samples 16] [--px 360]

Each column opens one master, poses the reach (FK upper arms rotated -75 deg about world X: forward), optionally
mutes the corrective keys (":muted"), measures the vest and renders it from the side (yaw 90) and at 3/4 front
(yaw 40). Measures (garments_v2.evaluate): ``flare`` = distance of garment.vest.main to the posed torso skin
(max / p99, m); ``penetration`` = vest vertices on the inner side of the posed blouse (count, max and p95 depth, m).
Rest and arms-down (compare rotation) values and the corrective key values are recorded too. Hair is hidden in
these renders only (the curls cover the vest in the side view). Writes <out>/reach.json and
<out>/reach_before_after.jpg (columns as given)."""
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
out = os.path.abspath(argv[0])
spp = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 16
px = int(argv[argv.index("--px") + 1]) if "--px" in argv else 360
cols = []
for a in argv[1:]:
    if a.startswith("--") or a.isdigit():
        continue
    label, rest = a.split("=", 1)
    muted = rest.endswith(":muted")
    cols.append((label, os.path.abspath(rest[:-6] if muted else rest), muted))
os.makedirs(out, exist_ok=True)
VIEWS = (("side", 90.0), ("threequarter", 40.0))
res = {"reach": {"axis": "X", "deg": -75.0}, "columns": [],
       "metrics": {"flare": "distance of garment.vest.main vertices (evaluated) to the posed torso skin, m",
                   "penetration": "vest main vertices on the inner side of the posed blouse main piece, depth in m"}}
shots = []
for label, blend, muted in cols:
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    body = next(o for o in bpy.data.objects if o.name.startswith("body_skin") and o.type == "MESH")
    vest = [o for o in bpy.data.objects if o.get("ps_garment_item") == "vest" and o.type == "MESH"]
    blouse = [o for o in bpy.data.objects if o.get("ps_garment_item") == "blouse" and o.type == "MESH"
              and o.get("ps_garment_part") == "main"]
    main = bpy.data.objects["garment.vest.main"]
    for k in [k for k in rig.keys() if k.startswith("face_")]:
        rig[k] = 0.0
    col = {"label": label, "blend": os.path.basename(os.path.dirname(blend)) + "/" + os.path.basename(blend),
           "keys_muted": muted, "blender": bpy.app.version_string}
    col["rest"] = {"keys": EV.key_values(vest), "flare": EV.flare(body, main),
                   "penetration": EV.penetration(main, blouse)}
    EV.rotate_upper_arms(rig, 35.0, axis="Y", mirror=True)
    col["arms_down"] = {"keys": EV.key_values(vest), "flare": EV.flare(body, main)}
    EV.rest(rig)
    EV.rotate_upper_arms(rig, -75.0, axis="X")
    EV.mute(vest, muted)
    col["reach"] = {"keys": EV.key_values(vest), "flare": EV.flare(body, main),
                    "penetration": EV.penetration(main, blouse)}
    res["columns"].append(col)
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
    for view, yaw in VIEWS:
        a, el = math.radians(yaw), math.radians(6.0)
        d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
        cam.location = target + d * (frame_h / 2 / math.tan(fov / 2))
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        RC.orient(lrig, d)
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = px, px, 100
        sc.render.image_settings.file_format = "PNG"
        path = os.path.join(out, f"reach_{label}_{view}.png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        shots.append((label, view, path))
json.dump(res, open(os.path.join(out, "reach.json"), "w"), indent=1)

from PIL import Image, ImageDraw  # noqa: E402
ims = {(l, v): Image.open(p).convert("RGB") for l, v, p in shots}
W = H = px
TOP = 30
sheet = Image.new("RGB", (len(cols) * W, TOP + len(VIEWS) * (H + 34)), (30, 30, 30))
dr = ImageDraw.Draw(sheet)
dr.text((6, 8), "T-093 vest in reach (FK upper arms -75 deg about X), hair hidden, same cameras/lights", fill=(255, 255, 255))
for c, (label, _, _) in enumerate(cols):
    col = res["columns"][c]
    f, pen = col["reach"]["flare"], col["reach"]["penetration"]
    for r, (view, _) in enumerate(VIEWS):
        y = TOP + r * (H + 34)
        dr.text((c * W + 6, y + 2), f"{label} | {view}", fill=(255, 255, 255))
        dr.text((c * W + 6, y + 16), f"flare max {f['max'] * 100:.1f} cm | into blouse: {pen['inside']} v, "
                f"p95 {pen['p95_depth'] * 100:.1f} cm", fill=(220, 220, 220))
        sheet.paste(ims[(label, view)], (c * W, y + 34))
sheet.save(os.path.join(out, "reach_before_after.jpg"), quality=90)
print("REACH", json.dumps([{k: c[k] for k in ("label", "reach")} for c in res["columns"]]))
