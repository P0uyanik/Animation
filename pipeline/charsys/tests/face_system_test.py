"""Generic face-system test for any face_generic/1 master (headless Blender; read-only on the input).

    blender -b --factory-startup -P pipeline/charsys/tests/face_system_test.py -- <master.blend> <out_dir> [--no-render]

Parts come from the rig property ps_face_parts (written by the build), never from character names. For the rest
state, every action unit (AU) and every preset it measures:
  eye_visible_L/R_pct   front rays over each eye opening (radius 0.8 r) whose first hit (glasses ignored) is the eye
  glasses_block_pct     share of those rays stopped by the glasses frame first (lens ignored)
  mouth_open_mm, corner_lift_L/R_mm   lips at the centre / corners (relative to the centre)
  teeth_pct, tongue_pct, interior_pct shares of a ray grid over the mouth that land on each oral layer
  brow_dz_L/R_mm        mean brow height change
  face_stretch_max      max edge stretch of the head skin within 0.1 m of the mouth (mouth band excluded)
  glasses_overlaps      intersecting triangle pairs between the glasses (frame + lens) and the face parts / skin
  glasses_skin_gap_mm   smallest distance from the frame to the head skin
Gaze: eye controls rotated (yaw +-20 deg, pitch +-12 deg) at rest and with Blink: eyeball/lid and eyeball/glasses
overlaps, eye visibility. Writes face_system_test.json, an expression sheet (presets), an action-unit sheet and a
gaze sheet."""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
RENDER = "--no-render" not in argv
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
sc = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "ps_face_parts" in o.keys())
PARTS = json.loads(rig["ps_face_parts"])
OB = bpy.data.objects
head = OB[PARTS["head"]]
mouth, cavity = OB[PARTS["mouth"]], OB[PARTS["cavity"]]
eyes = {s: OB[f"eye.{s}"] for s in ("L", "R")}
acc = [OB[n] for n in PARTS.get("accessories", []) if n in OB]
frame_objs = [o for o in acc if not o.name.endswith("_lens")]
lens_objs = [o for o in acc if o.name.endswith("_lens")]
face_objs = [o for o in OB if o.type == "MESH" and o.name.startswith(("eye.", "lid_", "lash.", "brow.", "ear."))]
CONTROLS = sorted(k for k in rig.keys() if k.startswith("face_"))
deps = bpy.context.evaluated_depsgraph_get
LM = {o.name[3:]: o for o in OB if o.name.startswith("LM_")}


def setc(active=None):
    for k in CONTROLS:
        rig[k] = 0.0
    for k, v in (active or {}).items():
        rig[f"face_{k}"] = v
    rig.update_tag()
    bpy.context.view_layer.update()


def wverts(o):
    ev = o.evaluated_get(deps())
    me = ev.to_mesh()
    n = len(me.vertices)
    c = np.empty(n * 3)
    me.vertices.foreach_get("co", c)
    ev.to_mesh_clear()
    M = np.array(o.matrix_world)
    return c.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]


def bvh(objs):
    vs, fs, off = [], [], 0
    for o in objs:
        ev = o.evaluated_get(deps())
        me = ev.to_mesh()
        mw = o.matrix_world
        vs += [mw @ v.co for v in me.vertices]
        fs += [tuple(i + off for i in p.vertices) for p in me.polygons]
        off += len(me.vertices)
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(vs, fs) if fs else None


def cast(o, d, ignore=()):
    """First hit not in `ignore` (continues through ignored objects)."""
    o = Vector(o)
    for _ in range(12):
        ok, loc, nrm, idx, ob, _m = sc.ray_cast(deps(), o, d)
        if not ok:
            return None, None, None
        if ob.name in ignore:
            o = loc + d * 1e-5
            continue
        return ob, idx, loc
    return None, None, None


def eye_rays(side):
    e = eyes[side]
    c = e.matrix_world.translation
    r = e.dimensions.x / 2
    vis = blk = tot = 0
    ign_all = {o.name for o in acc}
    ign_lens = {o.name for o in lens_objs}
    for i in range(-6, 7):
        for j in range(-6, 7):
            dx, dz = i / 6 * r * 0.8, j / 6 * r * 0.8
            if dx * dx + dz * dz > (0.8 * r) ** 2:
                continue
            o = (c.x + dx, c.y - 0.5, c.z + dz)
            tot += 1
            ob, _, _ = cast(o, Vector((0, 1, 0)), ign_all)
            vis += bool(ob is not None and ob.name == e.name)
            ob2, _, _ = cast(o, Vector((0, 1, 0)), ign_lens)
            blk += bool(ob2 is not None and ob2 in frame_objs)
    return 100.0 * vis / tot, 100.0 * blk / tot


SHADE = cavity.data.color_attributes.get("ps_mouth_shade")
COLS = np.array([c.color[:3] for c in SHADE.data]) if SHADE is not None else None


def mouth_rays():
    lm = LM["mouth"].matrix_world.translation
    w = max(abs(v.co.x) for v in mouth.data.vertices) * 1.3
    cnt = {"teeth": 0, "tongue": 0, "interior": 0}
    tot = 0
    for i in range(-10, 11):
        for j in range(-16, 7):
            o = (lm.x + i / 10 * w, lm.y - 0.3, lm.z + j * 0.001)
            tot += 1
            ob, idx, _ = cast(o, Vector((0, 1, 0)), {a.name for a in acc})
            if ob is None or ob.name != cavity.name or COLS is None:
                continue
            col = COLS[list(cavity.data.polygons[idx].vertices)].mean(axis=0)
            if col.mean() > 0.5:
                cnt["teeth"] += 1
            elif col[0] > 0.35 and col[1] < 0.3:
                cnt["tongue"] += 1
            else:
                cnt["interior"] += 1
    return {f"{k}_pct": round(100.0 * v / tot, 1) for k, v in cnt.items()}


def lips():
    m = wverts(mouth)
    xs = m[:, 0]
    mid = m[np.abs(xs) < 0.0015]
    corner = m[np.abs(xs) > xs.max() * 0.9]
    return {"mouth_open_mm": round(float((mid[:, 2].max() - mid[:, 2].min()) * 1000), 2),
            "corner_lift_L_mm": round(float((corner[corner[:, 0] > 0, 2].mean() - mid[:, 2].mean()) * 1000), 2),
            "corner_lift_R_mm": round(float((corner[corner[:, 0] < 0, 2].mean() - mid[:, 2].mean()) * 1000), 2)}


REST = {}


def stretch():
    hv = wverts(head)
    if "head" not in REST:
        lm = np.array(LM["mouth"].matrix_world.translation)
        REST["head"] = hv
        E = np.array([e.vertices[:] for e in head.data.edges])
        mid = (hv[E[:, 0]] + hv[E[:, 1]]) / 2
        near = np.linalg.norm(mid - lm, axis=1) < 0.1
        w = max(abs(v.co.x) for v in mouth.data.vertices)
        band = (np.abs(mid[:, 0] - lm[0]) < w * 1.05) & (np.abs(mid[:, 2] - lm[2]) < 0.004) & (mid[:, 1] < lm[1] + 0.01)
        REST["E"] = E[near & ~band]
        REST["l0"] = np.linalg.norm(hv[REST["E"][:, 0]] - hv[REST["E"][:, 1]], axis=1)
    E = REST["E"]
    l1 = np.linalg.norm(hv[E[:, 0]] - hv[E[:, 1]], axis=1)
    ok = REST["l0"] > 1e-4
    return round(float((l1[ok] / REST["l0"][ok]).max()), 3)


def brows():
    out = {}
    for s in ("L", "R"):
        b = OB.get(f"brow.{s}")
        if b is None:
            continue
        z = wverts(b)[:, 2].mean()
        REST.setdefault(f"brow{s}", z)
        out[f"brow_dz_{s}_mm"] = round(float((z - REST[f"brow{s}"]) * 1000), 2)
    return out


def glasses_checks():
    if not acc:
        return {}
    gb = bvh(acc)
    fb = bvh(frame_objs)
    out = {}
    tot = 0
    for o in face_objs + [head]:
        ov = len(gb.overlap(bvh([o])))
        if ov:
            out.setdefault("glasses_overlaps_by_part", {})[o.name] = ov
        tot += ov
    out["glasses_overlaps"] = tot
    hb = bvh([head])
    gap = min((hb.find_nearest(Vector(p))[3] for p in wverts(frame_objs[0])[::3]), default=None)
    out["glasses_skin_gap_mm"] = round(gap * 1000, 2) if gap is not None else None
    return out


def measure():
    m = {}
    for s in ("L", "R"):
        v, b = eye_rays(s)
        m[f"eye_visible_{s}_pct"] = round(v, 1)
        m[f"glasses_block_{s}_pct"] = round(b, 1)
    m.update(lips())
    m.update(mouth_rays())
    m.update(brows())
    m["face_stretch_max"] = stretch()
    m["eye_lid_overlaps"] = len(bvh(list(eyes.values())).overlap(bvh([o for o in face_objs if o.name.startswith(("lid_", "lash."))])))
    m.update(glasses_checks())
    return m


AUS, PRESETS = PARTS["action_units"], PARTS["presets"]
STATES = [("Neutral", {})] + [(p, {p: 1.0}) for p in PRESETS] + [(f"AU {a}", {a: 1.0}) for a in AUS]
STATES += [(f"Blink {v}", {"Blink": v}) for v in (0.15, 0.35, 0.5, 0.65, 0.85)]  # transitions (no render)
res = {}
for name, act in STATES:
    setc(act)
    res[name] = measure()
    print("[face_system_test]", name, res[name], flush=True)
setc()


# ---------------------------------------------------------------------------- gaze
def gaze(yaw, pitch):
    for s, e in eyes.items():
        pb = rig.pose.bones[f"eye.{s}"]
        c = rig.matrix_world @ pb.bone.head_local
        R = Matrix.Translation(c) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Rotation(math.radians(pitch), 4, "X") @ Matrix.Translation(-c)
        pb.matrix = rig.matrix_world.inverted() @ R @ rig.matrix_world @ pb.bone.matrix_local
    bpy.context.view_layer.update()


GAZE = [("centre", 0, 0), ("left", 20, 0), ("right", -20, 0), ("up", 0, -12), ("down", 0, 12)]
gz = {}
for blink in (0.0, 1.0):
    setc({"Blink": blink} if blink else {})
    for gname, yw, pt in GAZE:
        gaze(yw, pt)
        lidb = bvh([o for o in face_objs if o.name.startswith(("lid_", "lash."))])
        eb = bvh(list(eyes.values()))
        r = {"eye_lid_overlaps": len(eb.overlap(lidb)),
             "eye_visible_L_pct": round(eye_rays("L")[0], 1), "eye_visible_R_pct": round(eye_rays("R")[0], 1)}
        if acc:
            r["eye_glasses_overlaps"] = len(eb.overlap(bvh(acc)))
        eL = eyes["L"]
        idx = [v.index for v in eL.data.vertices if v.co.y < -0.9 * max(abs(w.co.y) for w in eL.data.vertices)]
        P = wverts(eL)[idx].mean(axis=0) - np.array(eL.matrix_world.translation)
        r["gaze_L_deg"] = [round(math.degrees(math.atan2(P[0], -P[1])), 1), round(math.degrees(math.atan2(P[2], -P[1])), 1)]
        gz[f"{'blink' if blink else 'open'}_{gname}"] = r
        print("[face_system_test] gaze", f"{'blink' if blink else 'open'}_{gname}", r, flush=True)
gaze(0, 0)
for pb in rig.pose.bones:
    pb.matrix_basis = Matrix()
setc()
json.dump({"source": SRC, "blender": bpy.app.version_string, "controls": CONTROLS, "states": res, "gaze": gz},
          open(os.path.join(OUT, "face_system_test.json"), "w"), indent=1)

# ---------------------------------------------------------------------------- renders
if RENDER:
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 24
    sc.render.resolution_x = sc.render.resolution_y = 300
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.55, 0.55, 0.55)
    cam = bpy.data.objects.new("fs_cam", bpy.data.cameras.new("fs_cam"))
    cam.data.lens = 85
    sc.collection.objects.link(cam)
    sc.camera = cam
    sun = bpy.data.objects.new("fs_sun", bpy.data.lights.new("fs_sun", "SUN"))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(55), 0, math.radians(-25))
    sc.collection.objects.link(sun)
    eL, eR = LM["eye_L"].matrix_world.translation, LM["eye_R"].matrix_world.translation
    mz = LM["mouth"].matrix_world.translation
    span = (eL - eR).length
    tgt = (eL + eR) / 2 * 0.7 + mz * 0.3 + Vector((0, 0, span * 0.15))
    dist = span * 7.4

    def shoot(path, az=0.0, el=5.0, d=dist):
        a, e = math.radians(az), math.radians(el)
        pos = tgt + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * d
        cam.location = pos
        cam.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)

    from PIL import Image, ImageDraw

    def sheet(tiles, cols, name):
        W = 300
        rows = (len(tiles) + cols - 1) // cols
        img = Image.new("RGB", (W * cols, W * rows), (40, 40, 40))
        d = ImageDraw.Draw(img)
        for i, (label, p) in enumerate(tiles):
            img.paste(Image.open(p).convert("RGB"), ((i % cols) * W, (i // cols) * W))
            d.text(((i % cols) * W + 6, (i // cols) * W + 6), label, fill=(255, 255, 255))
            os.remove(p)
        img.save(os.path.join(OUT, name))
    tiles = []
    for name, act in [s for s in STATES if not s[0].startswith(("AU ", "Blink 0"))]:
        setc(act)
        p = os.path.join(OUT, f"_x_{len(tiles)}.png")
        shoot(p)
        tiles.append((name, p))
    sheet(tiles, 4, "expressions_front.png")
    tiles = []
    for name, act in [s for s in STATES if s[0].startswith("AU ")]:
        setc(act)
        p = os.path.join(OUT, f"_a_{len(tiles)}.png")
        shoot(p)
        tiles.append((name, p))
    sheet(tiles, 4, "action_units_front.png")
    setc()
    tiles = []
    for vn, az in (("front", 0), ("three-quarter", 35), ("side", 90)):
        p = os.path.join(OUT, f"_v_{vn}.png")
        shoot(p, az=az)
        tiles.append((f"neutral {vn}", p))
    for vn, az in (("front", 0), ("three-quarter", 35)):
        setc({"Smile": 1.0})
        p = os.path.join(OUT, f"_vs_{vn}.png")
        shoot(p, az=az)
        tiles.append((f"Smile {vn}", p))
    setc({"Blink": 1.0})
    p = os.path.join(OUT, "_vb.png")
    shoot(p, az=35)
    tiles.append(("Blink three-quarter", p))
    sheet(tiles, 3, "views.png")
    tiles = []
    for blink in (0.0, 1.0):
        setc({"Blink": blink} if blink else {})
        for gname, yw, pt in GAZE:
            gaze(yw, pt)
            p = os.path.join(OUT, f"_g_{len(tiles)}.png")
            shoot(p)
            tiles.append((f"{'Blink ' if blink else ''}gaze {gname}", p))
    sheet(tiles, 5, "gaze.png")
for o in bpy.data.objects:  # report whether every driver is a simple expression (no Python auto-run needed)
    ad = getattr(getattr(o.data, "shape_keys", None), "animation_data", None) if o.type == "MESH" else None
    for fc in (ad.drivers if ad else []):
        if fc.driver.type == "SCRIPTED" and not fc.driver.is_simple_expression:
            print("[face_system_test] WARNING non-simple driver", o.name, fc.data_path, fc.driver.expression)
print("[face_system_test] ->", OUT)
