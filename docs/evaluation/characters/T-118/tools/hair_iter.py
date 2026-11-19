"""T-118 iteration preview (NOT evidence): rebuilds only the hair of a built master and renders Workbench head views.

    blender -b --factory-startup -P hair_iter.py -- <master.blend> <spec.json> <out.jpg> [--override <o.json> ...]
        [--px 300] [--views "yaw:el,..."] [--pickup "yaw:el,..."] [--size 3.1] [--dz 0.02]

The hair objects of the .blend are removed and the hair of spec (+ overrides) is built on its head with the pinned
groom generator (no fibres, no binding: rest pose, geometry and silhouette only). Orthographic views "yaw:el" seen
from the head (yaw 0 = front, 180 = back). --pickup directions are the pickup-glance proxy: the shot camera as seen
from a head pitched down (el = camera height angle + head pitch); for each, the share of the camera-facing eye surface
that no hair covers is measured with ray casts and printed (PICKUP lines) and written to <out>.json."""
import json
import math
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import body_helpers as BH  # noqa: E402
import versions as V  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
blend, spec_path, out = argv[:3]
opt = {"--px": "300", "--size": "3.1", "--dz": "0.02", "--views": "0:6,35:6,90:6,180:6,180:45,0:60", "--pickup": "25:40,25:50"}
overrides = []
i = 3
while i < len(argv):
    if argv[i] == "--override":
        overrides.append(argv[i + 1])
    else:
        opt[argv[i]] = argv[i + 1]
    i += 2


def merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            merge(a[k], v)
        else:
            a[k] = v


spec = json.load(open(spec_path))
for o in overrides:
    merge(spec, json.load(open(o))["override"])
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.name.startswith("hair_"):
        bpy.data.objects.remove(o, do_unlink=True)
for o in bpy.data.objects:
    if o.type == "CURVES":
        o.hide_render = True
head = bpy.data.objects["body_skin"]
C = head.users_collection[0]
H = float(spec["body"]["height_m"])
hp = spec["body"]["params"]["head"]
frame = {"centre": (0, hp["forward"] * H, hp["centre_z"] * H),
         "radii": (hp["half_width"] * H, hp["half_depth"] * H, hp["half_height"] * H)}
mats = {}


def material(slot):
    if slot not in mats:
        rgb = spec["materials"].get("target_colors_srgb", {}).get(slot) or spec["materials"]["target_colors_srgb"].get(
            "hair") or (90, 60, 50)
        m = bpy.data.materials.new("iter_" + slot)
        m.diffuse_color = tuple((c / 255) ** 2.2 for c in rgb[:3]) + (1.0,)
        mats[slot] = m
    return mats[slot]


GROOM = V.load("groom", spec["generators"]["groom"])
objs, rep = GROOM.build(C, head, frame, spec["hair"], material, BH.face_y, None)
bpy.context.view_layer.update()
print("HAIR", json.dumps({k: v for k, v in rep.items() if k not in ("objects",)}))


def view_dir(yaw, el):
    a, e = math.radians(yaw), math.radians(el)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


# ---- pickup-glance proxy: share of the camera-facing eye surface not covered by hair
dg = bpy.context.evaluated_depsgraph_get()
trees = [(o, BVHTree.FromObject(o, dg)) for o in objs]
pickup = []
for token in [t for t in opt["--pickup"].split(",") if t]:
    yaw, el = [float(x) for x in token.split(":")]
    d = view_dir(yaw, el)
    row = {"yaw": yaw, "el": el}
    for name in ("eye.L", "eye.R"):
        eye = bpy.data.objects.get(name)
        if eye is None:
            continue
        ev = eye.evaluated_get(dg)
        mw = eye.matrix_world
        n3 = mw.to_3x3()
        seen = total = 0
        for v in ev.data.vertices:
            if (n3 @ v.normal).dot(d) <= 0.2:
                continue
            total += 1
            p = mw @ v.co + d * 0.002
            if not any(t.ray_cast(o.matrix_world.inverted() @ p, o.matrix_world.inverted().to_3x3() @ d)[0] is not None
                       for o, t in trees):
                seen += 1
        row[name] = round(seen / max(1, total), 3)
    pickup.append(row)
    print("PICKUP", json.dumps(row))

# ---- Workbench views
px = int(opt["--px"])
centre = Vector(frame["centre"]) + Vector((0, 0, float(opt["--dz"])))
size = float(opt["--size"]) * max(frame["radii"])
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
tiles = []
views = [t for t in (opt["--views"] + "," + opt["--pickup"]).split(",") if t]
for k, token in enumerate(views):
    yaw, el = [float(x) for x in token.split(":")]
    d = view_dir(yaw, el)
    cam.location = centre + d * 3.0
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = out + f".{k}.png"
    bpy.ops.render.render(write_still=True)
    tiles.append(sc.render.filepath)
from PIL import Image  # noqa: E402

ims = [Image.open(p).convert("RGB") for p in tiles]
strip = Image.new("RGB", (px * len(ims), px))
for k, im in enumerate(ims):
    strip.paste(im, (k * px, 0))
strip.save(out, quality=88)
for p in tiles:
    os.remove(p)
json.dump({"views": views, "pickup": pickup, "hair": {k: v for k, v in rep.items() if k != "objects"}},
          open(out + ".json", "w"), indent=1)
print("WB", out)
