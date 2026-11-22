"""T-193 feasibility probe: stateless per-frame contact projection on lock centre lines (no simulation).

Same scene as gn_hair_dynamics_probe.py (skinned torso bending over a table, head). The locks are kinematic: they
follow the head rigidly, so in the lean they pass through the table and the torso (this stands in for whatever the
engine bake delivers). Each frame, each lock is walked from the root (follow-the-leader): the next point keeps its
segment length; if it is inside a collider mesh (BVH nearest point + face normal side) or within MARGIN of it,
it is pushed out to MARGIN along the normal and the segment length is restored (3 passes). Colliders are the
evaluated meshes themselves (deforming torso, table), so props need no hand-made spheres.
Run: python3 tools/bpy_blender.py -b --factory-startup -P <this> -- OUT.json [--mode=guide|ringlet] [--png=..]
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
_OUT = argv[0] if argv else "proj.json"
_opt = {a[2:].split("=")[0]: (a.split("=")[1] if "=" in a else True) for a in argv[1:]}
sys.argv = [sys.argv[0], "--", "/dev/null"]
exec(compile(src, "scene", "exec"))
OUT, opt = _OUT, _opt
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

MODE = opt.get("mode", "guide")
PNG = opt.get("png")
PF = [int(x) for x in opt.get("pf", "20,50,72,110").split(",")]
MARGIN = 0.003
NPT = 16 if MODE == "guide" else 48
LEN, HR, TURNS = float(opt.get("len", 0.32)), 0.015, 5.0
angles = [-30, 30, -75, 75, 150, 180, 210, 180]
rest = []
for i, a in enumerate(angles):
    a = math.radians(a)
    rz = 1.20 - (0.03 if i < 7 else 0.06)
    rr = math.sqrt(0.09 ** 2 - (rz - 1.20) ** 2) * 0.98
    r = Vector((rr * math.sin(a), rr * math.cos(a), rz))
    out = Vector((r.x, r.y, 0)).normalized()
    for k in range(NPT):
        t = k / (NPT - 1)
        off = out * (0.05 * min(1, t * 5))
        if MODE == "ringlet":
            ang = 2 * math.pi * TURNS * t
            off += Vector((math.cos(ang), math.sin(ang), 0)) * HR * min(1, t * 4)
        rest.append((r.x + off.x, r.y + off.y, r.z - LEN * t))
rest = np.array(rest).reshape(len(angles), NPT, 3)
seg = np.linalg.norm(np.diff(rest, axis=1), axis=2)
head_rest_inv = np.linalg.inv(np.array(head.matrix_world))


def world_bvh(obj, dg):
    e = obj.evaluated_get(dg)
    m = e.to_mesh()
    mw = np.array(e.matrix_world)
    vs = [Vector(mw[:3, :3] @ np.array(v.co) + mw[:3, 3]) for v in m.vertices]
    b = BVHTree.FromPolygons(vs, [tuple(p.vertices) for p in m.polygons])
    e.to_mesh_clear()
    return b, np.array(vs)


def depth(bvhs, q):
    """Signed penetration (>0 inside) of point q against the closest collider, with the push target."""
    best = (-1e9, None)
    for b in bvhs:
        co, nrm, _i, dist = b.find_nearest(Vector(q), 0.2)
        if co is None:
            continue
        inside = (Vector(q) - co).dot(nrm) < 0
        d = dist if inside else -dist
        if d > best[0]:
            best = (d, np.array(co + nrm * MARGIN))
    return best


def project(lock, L, bvhs):
    p = lock.copy()
    for _ in range(3):
        for k in range(1, len(p)):
            d = p[k] - p[k - 1]
            p[k] = p[k - 1] + d / max(np.linalg.norm(d), 1e-9) * L[k - 1]
            dd, target = depth(bvhs, p[k])
            if dd > -MARGIN and target is not None:
                p[k] = target
                d = p[k] - p[k - 1]
                p[k] = p[k - 1] + d / max(np.linalg.norm(d), 1e-9) * L[k - 1]
    return p


rows, h, frames_xy = [], hashlib.sha256(), {}
t_proj = 0.0
for f in range(1, FRAMES + 1):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    hm = np.array(head.evaluated_get(dg).matrix_world) @ head_rest_inv
    kin = rest @ hm[:3, :3].T + hm[:3, 3]  # rigid follow of the head (what a stiff bake would give)
    bt, tv = world_bvh(torso, dg)
    bb, _ = world_bvh(table, dg)
    t0 = time.time()
    out = np.array([project(kin[i], seg[i], [bt, bb]) for i in range(len(angles))])
    t_proj += time.time() - t0
    h.update(out.astype(np.float32).tobytes())
    row = {"frame": f}
    for tag, P in (("before", kin), ("after", out)):
        dt = np.array([max(0.0, depth([bt], q)[0]) for q in P.reshape(-1, 3)])
        db = np.array([max(0.0, depth([bb], q)[0]) for q in P.reshape(-1, 3)])
        row[tag] = {"torso_n": int((dt > 0.001).sum()), "torso_mm": round(float(dt.max()) * 1e3, 2),
                    "table_n": int((db > 0.001).sum()), "table_mm": round(float(db.max()) * 1e3, 2)}
    L = np.linalg.norm(np.diff(out, axis=1), axis=2).sum(1)
    row["stretch_max"] = round(float((L / seg.sum(1)).max()), 4)
    row["tip_shift_mm_max"] = round(float(np.linalg.norm(out[:, -1] - kin[:, -1], axis=1).max()) * 1e3, 1)
    rows.append(row)
    if PNG and f in PF:
        frames_xy[f] = (kin.copy(), out.copy(), tv, np.array(head.evaluated_get(dg).matrix_world.translation))


def summ(tag, k):
    return {"frames": sum(r[tag][k + "_n"] > 0 for r in rows), "worst_mm": max(r[tag][k + "_mm"] for r in rows)}


S_ = {"blender": bpy.app.version_string, "mode": MODE, "points": int(rest.size // 3), "frames": FRAMES,
      "margin_m": MARGIN, "projection_seconds": round(t_proj, 2), "sha256": h.hexdigest(),
      "before": {"torso": summ("before", "torso"), "table": summ("before", "table")},
      "after": {"torso": summ("after", "torso"), "table": summ("after", "table")},
      "stretch_max": max(r["stretch_max"] for r in rows), "tip_shift_mm_max": max(r["tip_shift_mm_max"] for r in rows)}
json.dump({"summary": S_, "rows": rows}, open(OUT, "w"), indent=1)
print(json.dumps(S_))

if PNG:
    from PIL import Image, ImageDraw
    S, W, H = 250 / 1.05, 250, 300
    img = Image.new("RGB", (W * len(PF), H + 20), "white")
    dr = ImageDraw.Draw(img)

    def px(y, z, ox):
        return (ox + (y + 0.30) * S, H - (z - 0.35) * S)

    for i, (f, (kin, out, tv, hcw)) in enumerate(sorted(frames_xy.items())):
        ox = i * W
        x0, y0 = px(TABLE_Y0, TABLE_Z, ox)
        x1, y1 = px(TABLE_Y1, 0.35, ox)
        dr.rectangle([x0, y0, min(x1, ox + W - 2), y1], fill="#d9c9a8")
        for v in tv[::3]:
            dr.point(px(v[1], v[2], ox), fill="#aaaaaa")
        c = px(hcw[1], hcw[2], ox)
        dr.ellipse([c[0] - 0.09 * S, c[1] - 0.09 * S, c[0] + 0.09 * S, c[1] + 0.09 * S], outline="#555555")
        for k in range(len(angles)):
            dr.line([px(q[1], q[2], ox) for q in kin[k]], fill="#f4a3a3", width=1)
            dr.line([px(q[1], q[2], ox) for q in out[k]], fill="#1f4e9c", width=2)
        dr.text((ox + 6, H + 4), f"f{f}  {MODE}: pink before, blue after", fill="black")
        dr.line([ox + W - 1, 0, ox + W - 1, H + 20], fill="#cccccc")
    img.save(PNG)
