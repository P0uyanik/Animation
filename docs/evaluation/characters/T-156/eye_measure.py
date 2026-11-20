"""T-156 eye-shape measure of one character master, in the T-150 image-plane definitions. Character-independent.

    blender -b --factory-startup -P docs/evaluation/characters/T-156/eye_measure.py -- <master.blend> <out.json>
        [--camera strict|probe] [--yaw 0] [--px 1280] [--overlay <render.png> <overlay.png>] [--mask]
        [--controls face_X=1 ...]  (last)

Camera: "strict" (default) = the strict sheet's face camera (T-087: 70 mm, 5 deg elevation, 0.32 m frame height, i.e.
0.62 m away), the standard neutral front image; "probe" = the T-109 face_probe "eyes" strip (6 deg, 0.12 m frame
height, 0.23 m away), whose traces line up 1:1 with the 100 % eye crops (--overlay draws them on such a strip). Both
sample the same 0.24 x 0.12 m window at the eye line, 1280 x 640 px. No render: one ray per pixel against the evaluated head, lid, lash and eyeball meshes. Glasses, hair and brows are not occluders (the lens is a
thin shell; its refraction is not modelled).
  opening   pixels whose first hit is the eyeball (inside the lash, as T-150), the part connected to the iris
  iris      the painted disc (spec.resolved.json next to the master: iris.radius, felt.round_iris), projected whole;
            D = its horizontal extent, centre = its bounding-box centre, also where a lid covers it
Per eye (T-150 README): W, H = opening bounding box; corners = the opening's extreme columns (mean row); peak = top
row (mean column); upper / lower lid at 10 % W inside each corner; white runs from the iris edge to the lid along the
iris centre's row and column. image_left / image_right follow the viewer; outer = away from the other eye."""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

FH, ASPECT, DZ, LENS, SENSOR = 0.12, 0.5, 0.005, 70.0, 36.0
CAMERAS = {"strict": (0.32, 5.0), "probe": (0.12, 6.0)}  # camera frame height at the target (m), elevation (deg)


def world_tree(ob, dg):
    e = ob.evaluated_get(dg)
    me = e.to_mesh()
    mw = e.matrix_world
    t = BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [p.vertices[:] for p in me.polygons])
    e.to_mesh_clear()
    return t


def angle(c, a, b):
    va, vb = np.subtract(a, c), np.subtract(b, c)
    return math.degrees(math.acos(float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))))


def connected(op, iris_box):
    """The part of the mask connected to its pixel nearest the iris centre (drops slivers of eyeball seen past a
    corner in turned views)."""
    ys, xs = np.nonzero(op)
    if not len(xs):
        return op
    k = int(np.argmin((xs - iris_box[0]) ** 2 + (ys - iris_box[1]) ** 2))
    out = np.zeros_like(op)
    out[ys[k], xs[k]] = True
    while True:
        g = out.copy()
        g[1:] |= out[:-1]
        g[:-1] |= out[1:]
        g[:, 1:] |= out[:, :-1]
        g[:, :-1] |= out[:, 1:]
        g &= op
        if g.sum() == out.sum():
            return out
        out = g


def measure(op, iris_box, other_cx):
    """op: bool mask (rows down); iris_box: (cx, cy, D) px. Returns (metrics, trace) or None."""
    ys, xs = np.nonzero(op)
    if len(xs) < 50:
        return None
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    W, H = x1 - x0 + 1, y1 - y0 + 1
    col = lambda x: np.nonzero(op[:, int(round(x))])[0]
    cl, cr = (x0, float(col(x0).mean())), (x1, float(col(x1).mean()))
    peak = (float(np.nonzero(op[y0:y0 + 3].any(axis=0))[0].mean()), y0)  # top 3 rows: a flat arch has no single peak
    ul, ur = col(x0 + 0.1 * W), col(x1 - 0.1 * W)
    cx, cy, D = iris_box
    left_outer = (x0 + x1) / 2 < other_cx  # this eye is image-left of the other: its outer corner is image-left
    co, ci = (cl, cr) if left_outer else (cr, cl)
    uo, ui = (ul, ur) if left_outer else (ur, ul)
    xo, xi = (x0 + 0.1 * W, x1 - 0.1 * W) if left_outer else (x1 - 0.1 * W, x0 + 0.1 * W)
    rr = D / 2.0
    row, colm = op[int(round(cy))] if y0 <= cy <= y1 else np.zeros(op.shape[1], bool), op[:, int(round(cx))]
    above = int(colm[:max(int(round(cy - rr)), 0)].sum())
    below = int(colm[int(round(cy + rr)) + 1:].sum())
    wl = int(row[:max(int(round(cx - rr)), 0)].sum())
    wr = int(row[int(round(cx + rr)) + 1:].sum())
    chord = cl[1] + (cr[1] - cl[1]) * (peak[0] - cl[0]) / max(cr[0] - cl[0], 1)
    m = {"opening_h_w": H / W, "iris_d_w": D / W, "iris_x_from_outer_w": abs(cx - co[0]) / W,
         "iris_y_from_top_h": (cy - y0) / H, "white_above_w": above / W, "white_below_w": below / W,
         "white_inner_w": (wr if left_outer else wl) / W, "white_outer_w": (wl if left_outer else wr) / W,
         "arch_w": (chord - peak[1]) / W,
         "inner_angle_deg": angle(ci, (xi, ui.min()), (xi, ui.max())),
         "outer_angle_deg": angle(co, (xo, uo.min()), (xo, uo.max())),
         "inner_drop_w": (ci[1] - co[1]) / W, "apex_from_outer_w": abs(peak[0] - co[0]) / W}
    tr = {"box": [x0, y0, x1, y1], "corner_left": cl, "corner_right": cr, "peak": peak, "iris": [cx, cy, D]}
    return m, tr


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    blend, out = argv[0], argv[1]
    opt = lambda k, n, d: argv[argv.index(k) + 1:argv.index(k) + 1 + n] if k in argv else d
    yaw, px = float(opt("--yaw", 1, [0])[0]), int(opt("--px", 1, [1280])[0])
    overlay = opt("--overlay", 2, None)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    ecfg = json.load(open(os.path.join(os.path.dirname(bpy.data.filepath), "spec.resolved.json")))["face"]["eyes"]
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    for k in [k for k in rig.keys() if k.startswith("face_")]:
        rig[k] = 0.0
    if "--controls" in argv:
        for kv in argv[argv.index("--controls") + 1:]:
            if kv.startswith("--"):
                break
            rig[kv.split("=")[0]] = float(kv.split("=")[1])
    rig.update_tag()
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    eyes = {s: bpy.data.objects[f"eye.{s}"] for s in ("L", "R")}
    head = bpy.data.objects["body_skin"]  # the skin mesh that carries the lid sockets
    occ = [head] + [bpy.data.objects[n] for s in ("L", "R") for n in (f"lid_upper.{s}", f"lid_lower.{s}", f"lash.{s}")
                    if n in bpy.data.objects]
    trees = [(o.name, world_tree(o, dg)) for o in occ] + [(f"eye.{s}", world_tree(eyes[s], dg)) for s in eyes]
    c = sum((e.matrix_world.translation for e in eyes.values()), Vector()) / 2
    target = Vector((0.0, c.y, c.z + DZ))
    camera = opt("--camera", 1, ["strict"])[0]
    a, el = math.radians(yaw), math.radians(CAMERAS[camera][1])
    d = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
    dist = CAMERAS[camera][0] / 2 / math.tan(math.atan(SENSOR / 2 / LENS))
    cam = target + d * dist
    fwd = -d
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd).normalized()
    w, h = px, int(round(px * ASPECT))
    s = FH / h  # metres per pixel on the target plane

    def project(p):
        v = p - cam
        z = v.dot(fwd)
        return (w / 2 + v.dot(right) / z * dist / s - 0.5, h / 2 - v.dot(up) / z * dist / s - 0.5)

    sc = ecfg.get("scale", [1, 1, 1])
    ir = float(ecfg["iris"]["radius"])
    kx = float(sc[0]) / float(sc[2]) if (ecfg.get("felt") or {}).get("round_iris") and ecfg.get("shader") == "felt/1" else 1.0
    cls = np.zeros((h, w), np.uint8)  # 1 sclera, 2 iris, 3 lash, 4 upper lid, 5 lower lid, 6 skin
    res, boxes = {}, {}
    for side, e in eyes.items():
        mwi = e.matrix_world.inverted()
        r = float(ecfg.get("radius_m", 0.03))
        rim = []
        for i in range(360):  # the painted disc's rim, in the eyeball's unit space (rho = ir, front half)
            t = math.radians(i)
            x, z = ir * math.cos(t) / kx, ir * math.sin(t)
            rim.append(project(e.matrix_world @ (Vector((x, -math.sqrt(max(1 - x * x - z * z, 0.0)), z)) * r)))
        rim = np.array(rim)
        boxes[side] = ((rim[:, 0].min() + rim[:, 0].max()) / 2, (rim[:, 1].min() + rim[:, 1].max()) / 2,
                       rim[:, 0].max() - rim[:, 0].min())
        ecx, ecy = project(e.matrix_world.translation)
        half = int(1.25 * r * max(sc) / s)
        for j in range(max(int(ecy) - half, 0), min(int(ecy) + half, h)):
            for i in range(max(int(ecx) - half, 0), min(int(ecx) + half, w)):
                dirn = (fwd * dist + right * ((i + 0.5 - w / 2) * s) + up * ((h / 2 - j - 0.5) * s)).normalized()
                best, name, hit = 1e9, None, None
                for n, t in trees:
                    loc, _, _, dd = t.ray_cast(cam, dirn)
                    if loc is not None and dd < best:
                        best, name, hit = dd, n, loc
                if name == f"eye.{side}":
                    q = (mwi @ hit) / r
                    cls[j, i] = 2 if (q.y < 0 and math.hypot(q.x * kx, q.z) < ir) else 1
                elif name:
                    cls[j, i] = 3 if name.startswith("lash") else 4 if name.startswith("lid_upper") else \
                        5 if name.startswith("lid_lower") else 6
    ex = {sd: project(e.matrix_world.translation)[0] for sd, e in eyes.items()}
    for side in eyes:
        other = "R" if side == "L" else "L"
        mask = np.zeros_like(cls, bool)
        x_mid = (ex["L"] + ex["R"]) / 2
        half_plane = (np.arange(w)[None, :] < x_mid) == (ex[side] < x_mid)
        mask[:] = connected(((cls == 1) | (cls == 2)) & half_plane, boxes[side])
        got = measure(mask, boxes[side], boxes[other][0])
        if got:
            m, tr = got
            m["iris_d_spacing"] = boxes[side][2] / abs(boxes["L"][0] - boxes["R"][0])
            key = "image_left" if ex[side] < x_mid else "image_right"
            res[key] = {"side": side, "metrics": {k: round(float(v), 4) for k, v in m.items()}, "trace_px": tr,
                        "mm": {"W": round(1000 * s * (tr["box"][2] - tr["box"][0] + 1), 2),
                               "H": round(1000 * s * (tr["box"][3] - tr["box"][1] + 1), 2),
                               "D": round(1000 * s * tr["iris"][2], 2)}}
    json.dump({"blend": os.path.basename(os.path.dirname(os.path.abspath(blend))), "camera": camera, "yaw_deg": yaw, "px": [w, h],
               "mm_per_px": round(1000 * s, 4), "eyes": res}, open(out, "w"), indent=1)
    if "--mask" in argv:  # class map: 0 unsampled, 1 sclera, 2 iris, 3 lash, 4 upper lid, 5 lower lid, 6 skin
        np.save(os.path.splitext(out)[0] + ".mask.npy", cls)
    if overlay:
        from PIL import Image, ImageDraw
        im = Image.open(overlay[0]).convert("RGB").resize((w, h))
        edge = np.zeros_like(cls, bool)
        o = (cls == 1) | (cls == 2)
        edge[1:-1, 1:-1] = o[1:-1, 1:-1] & ~(o[:-2, 1:-1] & o[2:, 1:-1] & o[1:-1, :-2] & o[1:-1, 2:])
        arr = np.array(im)
        arr[edge] = (0, 255, 0)
        im = Image.fromarray(arr)
        dr = ImageDraw.Draw(im)
        for v in res.values():
            t = v["trace_px"]
            cx, cy, D = t["iris"]
            dr.ellipse((cx - D / 2, cy - D / 2, cx + D / 2, cy + D / 2), outline=(255, 0, 255))
            dr.line((*t["corner_left"], *t["corner_right"]), fill=(255, 210, 0), width=2)
            dr.rectangle(t["box"], outline=(0, 160, 255))
            px_, py_ = t["peak"]
            dr.line((px_, py_ - 8, px_, py_ + 8), fill=(255, 0, 0), width=2)
        im.save(overlay[1])
    for k, v in res.items():
        print(k, v["mm"], v["metrics"])


if __name__ == "__main__":
    main()
