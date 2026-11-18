"""T-089 eye-opening measurement (headless Blender; read-only on the input). Character-independent.

    blender -b --factory-startup -P docs/evaluation/characters/T-089/measure_eyes.py -- <master.blend> <out.json>

For each view (front yaw 0, 3/4 yaw -35, side yaw -90; the reference index's convention) and each state (neutral,
blink = Blink.L/R at 0.5 and 1.0, glance = both eye bones turned 15 deg towards the camera side) it casts parallel
rays along the view direction on a 0.25 mm grid around each eye and keeps the rays whose FIRST hit (skin, lids,
lashes, brows, mouth, eyeballs; hair and clothing excluded, as the reference landmarks mark the eye opening itself) is
an eyeball. Reports per eye: visible width and height (mm, in the view plane), outer-corner lift (mm: outer corner
height minus inner corner height), and the ratios the reference landmarks give: width / eye spacing (front, 3/4) and
side width / front width."""
import json
import math
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for k in [k for k in rig.keys() if k.startswith("face_")]:
    rig[k] = 0.0
EXCL = ("hair", "groom", "garment", "clothing", "hood", "fur", "acc", "glasses")


def meshes():
    return [o for o in bpy.data.objects if o.type == "MESH" and o.visible_get() and not o.hide_render
            and not any(t in o.name.lower() for t in EXCL)
            and (o.name.startswith(("body_skin", "eye.", "lid_", "lash", "brow", "mouth", "ear", "nose")))]


def build_tree():
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, owner = [], [], []
    for o in meshes():
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        for p in me.polygons:
            polys.append([off + i for i in p.vertices])
            owner.append(o.name)
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys), owner


def eye_centres():
    out = {}
    for s in ("L", "R"):
        e = bpy.data.objects[f"eye.{s}"]
        out[s] = e.matrix_world.translation.copy()
    return out


def measure(yaw_deg, centres):
    tree, owner = build_tree()
    a = math.radians(yaw_deg)
    d = Vector((math.sin(a), -math.cos(a), 0.0))  # from the character towards the camera
    right = Vector((math.cos(a), math.sin(a), 0.0))  # screen x (camera right = character's left at yaw 0)
    up = Vector((0, 0, 1))
    res = {}
    step = 0.00025
    for s, c in centres.items():
        hits = []
        n = int(0.06 / step)
        for i in range(-n, n + 1):
            for j in range(-n // 2, n // 2 + 1):
                o = c + right * (i * step) + up * (j * step) + d * 0.5
                loc, nrm, idx, dist = tree.ray_cast(o, -d, 1.0)
                if loc is not None and owner[idx] == f"eye.{s}":
                    hits.append((i * step, j * step))
        if len(hits) < 4:
            res[s] = {"visible": False, "pixels": len(hits)}
            continue
        xs = [h[0] for h in hits]
        zs = [h[1] for h in hits]
        x0, x1 = min(xs), max(xs)
        # corner heights: mean z of the hits in the outermost/innermost 1 mm columns
        sx = 1 if s == "L" else -1
        sgn = sx if abs(yaw_deg) < 89 else 1
        lo_col = [h[1] for h in hits if h[0] < x0 + 0.001]
        hi_col = [h[1] for h in hits if h[0] > x1 - 0.001]
        outer_z, inner_z = (sum(hi_col) / len(hi_col), sum(lo_col) / len(lo_col)) if sx * math.cos(a) > 0 else (sum(lo_col) / len(lo_col), sum(hi_col) / len(hi_col))
        cols = {}
        for x, z in hits:
            k = round(x / step)
            lo, hi = cols.get(k, (z, z))
            cols[k] = (min(lo, z), max(hi, z))
        res[s] = {"visible": True, "width_mm": round((x1 - x0) * 1000, 2),
                  "height_mm": round(max(hi - lo for lo, hi in cols.values()) * 1000, 2),
                  "area_mm2": round(len(hits) * step * step * 1e6, 1),
                  "outer_corner_lift_mm": round((outer_z - inner_z) * 1000, 2),
                  "centre_screen_mm": [round(sum(xs) / len(xs) * 1000 + (c - Vector((0, 0, 0))).dot(right) * 1000, 2),
                                       round(sum(zs) / len(zs) * 1000 + c.z * 1000, 2)]}
    vis = [res[s] for s in ("L", "R") if res[s].get("visible")]
    if len(vis) == 2:
        res["spacing_mm"] = round(abs(vis[0]["centre_screen_mm"][0] - vis[1]["centre_screen_mm"][0]), 2)
        for s in ("L", "R"):
            res[s]["width_to_spacing"] = round(res[s]["width_mm"] / res["spacing_mm"], 4)
    return res


def eye_bones():
    names = [b.name for b in rig.pose.bones]
    for pat in ("eye.{s}", "MCH-eye.{s}", "DEF-eye.{s}"):
        if all(pat.format(s=s) in names for s in ("L", "R")):
            return [rig.pose.bones[pat.format(s=s)] for s in ("L", "R")]
    return []


views = {"front": 0.0, "threequarter": -35.0, "side": -90.0}
out = {"blend": argv[0], "views": {}}
centres = eye_centres()
for state in ("neutral", "blink50", "blink100", "glance"):
    for k in ("face_Blink.L", "face_Blink.R"):
        if k in rig.keys():
            rig[k] = {"blink50": 0.5, "blink100": 1.0}.get(state, 0.0)
    bones = eye_bones()
    for b in bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
    if state == "glance":
        for b in bones:  # 15 deg towards screen-left (the character's right): the 3/4 camera side
            b.rotation_euler = (0, 0, math.radians(-15)) if True else (0, 0, 0)
    rig.update_tag()
    bpy.context.view_layer.update()
    for vn, y in views.items():
        if state != "neutral" and vn == "side":
            continue
        out["views"].setdefault(vn, {})[state] = measure(y, centres)
out["eye_bones"] = [b.name for b in eye_bones()]
f = out["views"]["front"]["neutral"]
sd = out["views"]["side"]["neutral"]
if f["R"].get("visible") and sd["R"].get("visible"):
    out["side_width_to_front_width_R"] = round(sd["R"]["width_mm"] / f["R"]["width_mm"], 4)
json.dump(out, open(argv[1], "w"), indent=1)
print("MEASURE", json.dumps({v: {s: out["views"][v]["neutral"][s] for s in ("L", "R")} for v in views}))
