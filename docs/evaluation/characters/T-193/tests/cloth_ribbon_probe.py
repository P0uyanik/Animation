"""T-193 feasibility probe: Blender Cloth (classic modifier) on one pinned ribbon per lock.

Same scene as gn_hair_dynamics_probe.py (its lines up to "# --- locks" are executed, minus the GN collider
modifiers): skinned torso bending over a table, head sphere. Each lock is a 2 cm wide ribbon (16 rows), pinned
at its top row to the head (vertex parent via an Armature-free "pin" group + object parent), Cloth with
self-collision off, collision objects: torso (deforming), table, head.
Run: python3 tools/bpy_blender.py -b --factory-startup -P <this> -- OUT.json [--q=quality] [--thick=m] [--png=..]
Throwaway research code.
"""
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "gn_hair_dynamics_probe.py")).read()
src = src.split("# --- locks")[0].replace('one_node_gn(o, COL,', 'pass  # (o, COL,')
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "cloth.json"
opt = {a[2:].split("=")[0]: (a.split("=")[1] if "=" in a else True) for a in argv[1:]}
sys.argv = [sys.argv[0], "--", "/dev/null"]
_OUT, _opt = OUT, opt
exec(compile(src, "scene", "exec"))
OUT, opt = _OUT, _opt
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

Q, THICK = int(opt.get("q", 10)), float(opt.get("thick", 0.006))
PNG = opt.get("png")
PF = [int(x) for x in opt.get("pf", "20,50,72,110").split(",")]

for o, thick in ((torso, THICK), (table, THICK)):  # the head is not a collider: the pinned roots sit in it
    o.modifiers.new("collision", "COLLISION")
    o.collision.thickness_outer = thick
    o.collision.cloth_friction = 5.0

# ribbons, built in world space at rest, then parented to the head (object level)
NPT, LEN, WID = 16, 0.32, 0.02
angles = [-30, 30, -75, 75, 150, 180, 210, 180]
verts, faces, pin = [], [], []
for i, a in enumerate(angles):
    a = math.radians(a)
    rz = 1.20 - (0.03 if i < 7 else 0.06)
    rr = math.sqrt(0.09 ** 2 - (rz - 1.20) ** 2) * 0.98
    r = Vector((rr * math.sin(a), rr * math.cos(a), rz))
    out = Vector((r.x, r.y, 0)).normalized()
    side = Vector((-out.y, out.x, 0)) * (WID / 2)
    base = len(verts)
    for k in range(NPT):
        t = k / (NPT - 1)
        c = r + out * (0.05 * min(1, t * 5)) + Vector((0, 0, -LEN * t))
        verts += [tuple(c - side), tuple(c + side)]
        if k == 0:
            pin += [base, base + 1]
        if k:
            j = base + 2 * k
            faces.append((j - 2, j - 1, j + 1, j))
me = bpy.data.meshes.new("ribbons")
me.from_pydata(verts, [], faces)
rib = bpy.data.objects.new("ribbons", me)
sc.collection.objects.link(rib)
vg = rib.vertex_groups.new(name="pin")
vg.add(pin, 1.0, "REPLACE")
rib.parent = head
rib.matrix_parent_inverse = head.matrix_world.inverted()
cl = rib.modifiers.new("cloth", "CLOTH")
s = cl.settings
s.quality = Q
s.vertex_group_mass = "pin"
s.mass = 0.02
s.tension_stiffness = s.compression_stiffness = 80
s.bending_stiffness = 2.0
s.air_damping = 1.0
cl.collision_settings.use_collision = True
cl.collision_settings.distance_min = 0.004
cl.collision_settings.collision_quality = 4
cl.point_cache.frame_start, cl.point_cache.frame_end = 1, FRAMES

rest = np.array(verts).reshape(len(angles), NPT, 2, 3).mean(2)
rest_len = np.linalg.norm(np.diff(rest, axis=1), axis=2).sum(1)
rows, h, frames_xy = [], hashlib.sha256(), {}
t0 = time.time()
for f in range(1, FRAMES + 1):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    re = rib.evaluated_get(dg)
    m = re.to_mesh()
    p = np.zeros(len(m.vertices) * 3, dtype=np.float32)
    m.vertices.foreach_get("co", p)
    re.to_mesh_clear()
    mw = np.array(re.matrix_world)
    w = p.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    h.update(w.astype(np.float32).tobytes())
    te = torso.evaluated_get(dg)
    tm = te.to_mesh()
    tw = np.array(te.matrix_world)
    tv = [Vector(tw[:3, :3] @ np.array(v.co) + tw[:3, 3]) for v in tm.vertices]
    bvh = BVHTree.FromPolygons(tv, [tuple(pl.vertices) for pl in tm.polygons])
    depth_t = []
    for q in w:
        co, nrm, _i, dist = bvh.find_nearest(Vector(q))
        depth_t.append(dist if (Vector(q) - co).dot(nrm) < 0 else 0.0)
    te.to_mesh_clear()
    depth_t = np.array(depth_t)
    in_fp = (np.abs(w[:, 0]) < 0.6) & (w[:, 1] > TABLE_Y0) & (w[:, 1] < TABLE_Y1)
    depth_tab = np.where(in_fp, TABLE_Z - w[:, 2], 0)
    hcw = np.array(head.evaluated_get(dg).matrix_world.translation)
    depth_h = 0.09 - np.linalg.norm(w - hcw, axis=1)
    cen = w.reshape(len(angles), NPT, 2, 3).mean(2)
    L = np.linalg.norm(np.diff(cen, axis=1), axis=2).sum(1)
    rows.append({"frame": f, "torso_n": int((depth_t > 0.001).sum()), "torso_mm": round(float(depth_t.max()) * 1e3, 2),
                 "table_n": int((depth_tab > 0.001).sum()), "table_mm": round(float(max(0, depth_tab.max())) * 1e3, 2),
                 "head_n": int((depth_h > 0.001).sum()), "head_mm": round(float(max(0, depth_h.max())) * 1e3, 2),
                 "stretch_max": round(float((L / rest_len).max()), 3)})
    if PNG and f in PF:
        frames_xy[f] = (cen.reshape(-1, 3), np.array(tv), hcw)
el = time.time() - t0


def summ_key(k):
    return {"frames": sum(r[k + "_n"] > 0 for r in rows), "worst_mm": max(r[k + "_mm"] for r in rows),
            "most_points": max(r[k + "_n"] for r in rows)}


summ = {"blender": bpy.app.version_string, "mode": "cloth-ribbon", "locks": len(angles), "points": int(len(w)),
        "frames": FRAMES, "quality": Q, "collision_thickness_m": THICK, "seconds_incl_measure": round(el, 2),
        "sha256": h.hexdigest(), "torso": summ_key("torso"), "table": summ_key("table"), "head": summ_key("head"),
        "stretch_max": max(r["stretch_max"] for r in rows)}
json.dump({"summary": summ, "rows": rows}, open(OUT, "w"), indent=1)
print(json.dumps(summ))

if PNG:
    from PIL import Image, ImageDraw
    S, W, H = 250 / 1.05, 250, 300
    img = Image.new("RGB", (W * len(PF), H + 20), "white")
    dr = ImageDraw.Draw(img)

    def px(y, z, ox):
        return (ox + (y + 0.30) * S, H - (z - 0.35) * S)

    cols = ["#d62728", "#ff7f0e", "#2ca02c", "#17becf", "#1f77b4", "#9467bd", "#8c564b", "#e377c2"]
    for i, (f, (w, tv, hcw)) in enumerate(sorted(frames_xy.items())):
        ox = i * W
        x0, y0 = px(TABLE_Y0, TABLE_Z, ox)
        x1, y1 = px(TABLE_Y1, 0.35, ox)
        dr.rectangle([x0, y0, min(x1, ox + W - 2), y1], fill="#d9c9a8")
        for v in tv[::3]:
            dr.point(px(v[1], v[2], ox), fill="#aaaaaa")
        c = px(hcw[1], hcw[2], ox)
        dr.ellipse([c[0] - 0.09 * S, c[1] - 0.09 * S, c[0] + 0.09 * S, c[1] + 0.09 * S], outline="#555555")
        for k in range(len(angles)):
            dr.line([px(q[1], q[2], ox) for q in w.reshape(len(angles), NPT, 3)[k]], fill=cols[k], width=2)
        dr.text((ox + 6, H + 4), f"f{f}  cloth ribbon q{Q} thick{THICK}", fill="black")
        dr.line([ox + W - 1, 0, ox + W - 1, H + 20], fill="#cccccc")
    img.save(PNG)
