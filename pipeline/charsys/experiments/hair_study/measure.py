"""T-049 hair study: geometric measurements and the 2 s head-turn test for one study build (headless Blender).

    blender -b --factory-startup -P measure.py -- <study.blend> <out_dir> [--frames 24] [--render]

1. Face visibility (no render): rays from the camera direction onto a grid over the face (brow top to mouth, eye
   corners +- margin, from the face landmarks); a ray is blocked when its first hit is a hair mesh. Reported for the
   front and a 35 deg three-quarter view, for the whole face window and for the eyes only, at rest and at the turn
   extremes.
2. Head turn: 2 s at 24 fps, head yaw psi(t) = 40 deg * sin(pi t) (a brisk left-right turn, peak 126 deg/s) on the rig's
   "head" control. Secondary motion PROXY (not the engine solver): every hair chain (DYN- bones from the shared groom
   dynamics) is a damped torsional spring about the vertical axis (stiffness/damping from the spec's chain params,
   omega = sqrt(stiffness), zeta = damping / (2 omega)); the lag theta - psi is spread evenly over the chain's bones.
   Approaches without chains (B) move rigidly with the head.
3. Collision: hair vertices deeper than 2 mm inside the head/face/ears/body meshes (nearest-surface normal test), at
   rest and every 4th frame of the turn (max reported); and the largest lag angle of any chain.
4. --render: 24 frames (12 fps over the 2 s) at 320 px, 8 samples + OIDN, calibrated lighting, a fixed head camera,
   written as <out>/turn/####.png for the contact strip / GIF.
Writes <out>/measure.json."""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import render_calibration as RC  # noqa: E402
import render_engine  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
blend, out = argv[0], argv[1]
FRAMES = int(argv[argv.index("--frames") + 1]) if "--frames" in argv else 48
RENDER = "--render" in argv
os.makedirs(out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
sc = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith("rig_"))
hair = [o for o in bpy.data.objects if o.name.startswith("hair_") and o.type == "MESH"]
BODY_NAMES = ("head", "body_skin", "ear.", "neck", "hood", "hoodie_torso", "garment.blouse.collar", "garment.vest.main",
              "garment.blouse.main")
body = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(BODY_NAMES)
        and not o.name.startswith("garment.collider")]
lm = {o.name: o.matrix_world.translation.copy() for o in bpy.data.objects if o.name.startswith("LM_")}
brow = [o for o in bpy.data.objects if o.name.startswith("brow.")]


def world_lm():
    bpy.context.view_layer.update()
    return {o.name: o.matrix_world.translation.copy() for o in bpy.data.objects if o.name.startswith("LM_")}


def brow_top():
    dg = bpy.context.evaluated_depsgraph_get()
    z = -1
    for b in brow:
        e = b.evaluated_get(dg)
        z = max(z, max((b.matrix_world @ v.co).z for v in e.data.vertices))
    return z


def visibility(yaw_head, view_yaw):
    """Fraction of face-window (and eye-window) rays whose first hit is not hair. view_yaw: camera yaw relative to
    the head's facing (0 = front)."""
    dg = bpy.context.evaluated_depsgraph_get()
    L = world_lm()
    eL, eR, mo = L["LM_eye_L"], L["LM_eye_R"], L["LM_mouth"]
    zt = brow_top() + 0.01
    zb = mo.z - 0.012
    ctr = (eL + eR) / 2
    half = (eL - eR).length / 2 + 0.045
    yaw = math.radians(yaw_head + view_yaw)
    d = Vector((-math.sin(yaw), math.cos(yaw), 0.0))  # ray direction (towards the face from the camera side)
    side = Vector((math.cos(yaw), math.sin(yaw), 0.0))
    face_n = eye_n = face_vis = eye_vis = 0
    eye_half = (eL - eR).length / 2 + 0.035
    for i in range(41):
        for j in range(41):
            x = -half + 2 * half * i / 40
            z = zb + (zt - zb) * j / 40
            hy = math.radians(yaw_head)
            p = ctr + Vector((math.cos(hy) * x, math.sin(hy) * x, 0)) + Vector((0, 0, z - ctr.z))
            origin = p - d * 1.0
            hit, loc, nrm, idx, ob, _ = sc.ray_cast(dg, origin, d, distance=2.0)
            if not hit:
                continue
            is_eye = abs(x) < eye_half and abs(z - eL.z) < 0.035
            blocked = ob.name.startswith("hair_")
            face_n += 1
            face_vis += not blocked
            if is_eye:
                eye_n += 1
                eye_vis += not blocked
    return {"face": round(face_vis / max(1, face_n), 4), "eyes": round(eye_vis / max(1, eye_n), 4)}


def penetration():
    """Hair vertices (every 3rd) more than 2 mm inside a body mesh, split into the head/scalp (roots and the base
    volume's inset sit there by design: compare against rest) and everything else (ears, neck, clothing, body)."""
    dg = bpy.context.evaluated_depsgraph_get()
    trees = []
    for o in body:
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        me.transform(o.matrix_world)
        trees.append((o.name in ("head", "body_skin"),
                      BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])))
        e.to_mesh_clear()
    n = 0
    bad = {"head": 0, "other": 0}
    deepest = {"head": 0.0, "other": 0.0}
    for o in hair:
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        mw = o.matrix_world
        for k, v in enumerate(me.vertices):
            if k % 3:
                continue
            p = mw @ v.co
            n += 1
            for is_head, t in trees:
                loc, nrm, _, dist = t.find_nearest(p, 0.03)
                if loc is not None and (p - loc).dot(nrm) < -0.002:
                    k2 = "head" if is_head else "other"
                    bad[k2] += 1
                    deepest[k2] = max(deepest[k2], dist)
                    break
        e.to_mesh_clear()
    return {"head_inside_frac": round(bad["head"] / max(1, n), 5), "other_inside_frac": round(bad["other"] / max(1, n), 5),
            "other_deepest_mm": round(deepest["other"] * 1000, 1), "sampled": n}


# --- rest measurements
t0 = time.time()
res = {"blend": os.path.basename(blend), "rest": {"front": visibility(0, 0), "three_quarter": visibility(0, -35),
                                                   "penetration": penetration()}}

# --- head turn
head_ctrl = rig.pose.bones.get("head")
dyn = json.loads(rig.get("ps_dynamics", "{}")) if "ps_dynamics" in rig else {}
chains = []
for ob in hair:
    if "ps_dyn" not in ob:
        continue
    for ch in json.loads(ob["ps_dyn"])["chains"]:
        bones = [b.name for b in rig.pose.bones if b.name.startswith(f"DYN-{ch['name']}.")]
        bones.sort(key=lambda n: int(n.rsplit(".", 1)[1]))
        if bones:
            p = ch["params"]
            w = math.sqrt(float(p.get("stiffness", 100.0)))
            chains.append({"bones": bones, "omega": w, "zeta": float(p.get("damping", 8.0)) / (2 * w),
                           "limit": math.radians(float(p.get("limit_deg", 30.0))), "theta": 0.0, "vel": 0.0})
fps = 24.0
pivot = rig.matrix_world @ head_ctrl.head if head_ctrl else Vector((0, 0, 0.75))
rest_head = head_ctrl.matrix.copy() if head_ctrl else None


def psi(t):
    return math.radians(40.0) * math.sin(math.pi * t)


def set_world_rot(pb, angle, pivot_world):
    """Pre-multiply the pose bone's armature-space matrix by a rotation about the world Z axis through pivot."""
    piv = rig.matrix_world.inverted() @ pivot_world
    R = Matrix.Translation(piv) @ Matrix.Rotation(angle, 4, "Z") @ Matrix.Translation(-piv)
    pb.matrix = R @ pb.matrix


turn = {"frames": FRAMES, "max_lag_deg": 0.0, "penetration_max": {"head_inside_frac": 0.0, "other_inside_frac": 0.0,
                                                                  "other_deepest_mm": 0.0},
        "visibility_at_extremes": {}}
cam = None
if RENDER:
    for o in list(sc.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o, do_unlink=True)
    lrig = RC.apply(sc, RC.load(RC.DEFAULT))
    render_engine.configure(sc, "cycles", 8, cycles_device="CPU", cycles_denoiser="OPENIMAGEDENOISE")
    cam = bpy.data.objects.new("TurnCam", bpy.data.cameras.new("TurnCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    L0 = world_lm()
    c = (L0["LM_eye_L"] + L0["LM_eye_R"]) / 2 + Vector((0, 0, 0.02))
    big = "body_skin" in bpy.data.objects
    cam.data.ortho_scale = 0.66 if big else 0.6
    c.z += -0.07 if big else 0.06
    d = Vector((math.sin(math.radians(-20)), -math.cos(math.radians(-20)), 0.08)).normalized()
    cam.location = c + d * 1.5
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    if lrig:
        RC.orient(lrig, d)
    sc.render.resolution_x = sc.render.resolution_y = 320
    os.makedirs(os.path.join(out, "turn"), exist_ok=True)
sub = 10
render_every = max(1, int(round(FRAMES / 24)))
t_render = 0.0
for f in range(FRAMES + 1):
    t = f / fps
    # integrate the chain springs (substeps)
    for s in range(sub):
        tt = t - (sub - 1 - s) / (fps * sub)
        target = psi(tt)
        for ch in chains:
            acc = ch["omega"] ** 2 * (target - ch["theta"]) - 2 * ch["zeta"] * ch["omega"] * ch["vel"]
            ch["vel"] += acc / (fps * sub)
            ch["theta"] += ch["vel"] / (fps * sub)
    if head_ctrl:
        head_ctrl.matrix = rest_head
        bpy.context.view_layer.update()
        set_world_rot(head_ctrl, psi(t), pivot)
    bpy.context.view_layer.update()
    for b in [b for b in rig.pose.bones if b.name.startswith("DYN-")]:
        b.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    depth = max((len(ch["bones"]) for ch in chains), default=0)
    for k in range(depth):
        for ch in chains:
            if k < len(ch["bones"]):
                lag = max(-ch["limit"], min(ch["limit"], ch["theta"] - psi(t)))
                turn["max_lag_deg"] = max(turn["max_lag_deg"], abs(math.degrees(lag)))
                pb = rig.pose.bones[ch["bones"][k]]
                set_world_rot(pb, lag / len(ch["bones"]), rig.matrix_world @ pb.head)
        bpy.context.view_layer.update()
    if f % 4 == 0 and f:
        pen = penetration()
        pm = turn["penetration_max"]
        for k in pm:
            pm[k] = max(pm[k], pen[k])
    if f in (12, 36):  # the turn extremes (+40 / -40 deg)
        turn["visibility_at_extremes"][f"psi_{round(math.degrees(psi(t)))}"] = {
            "front": visibility(math.degrees(psi(t)), 0), "three_quarter": visibility(math.degrees(psi(t)), -35)}
    if RENDER and f % render_every == 0 and f < FRAMES:
        tr = time.time()
        sc.render.filepath = os.path.join(out, "turn", f"{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        t_render += time.time() - tr
turn["chains"] = len(chains)
turn["render_s_per_frame"] = round(t_render / max(1, FRAMES // render_every), 2) if RENDER else None
res["turn"] = turn
res["measure_s"] = round(time.time() - t0, 1)
json.dump(res, open(os.path.join(out, "measure.json"), "w"), indent=1)
print("MEASURE", json.dumps(res))
