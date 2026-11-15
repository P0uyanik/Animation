"""Creates the technical validation clips on the neutral mannequin and exports them (headless Blender).

    blender -b --factory-startup -P pipeline/clips/make_clips.py -- --mannequin <dir>/neutral_mannequin.blend \
        --out content/clips [--blend-out <dir>/mannequin_clips.blend]

Script-made (option 1 of the owner decision: script clips first, licensed motion capture later). Poses are written as
joint rotations in the REFERENCE (T-pose) frame of each role, relative to its semantic parent: e.g. the left upper
arm hangs down by rotating -78 degrees about z; a left elbow flexes forward about y; a hip flexes about -x. Right-side
motion is the mirror of the left-side definition (one definition, M · q · M). Every clip is a Blender action on the
mannequin, exported by the shared exporter (clip_tools.export_action), so a future artist-made clip goes the same way.

Clips (mechanical, for technical validation; acting quality is out of scope):
  idle_relaxed  loop, 90 frames: arms down, breathing (chest/spine), slight sway, small head drift
  wave          right arm wave (mirrorable), starts and ends in the relaxed arm pose
  point         right arm and index finger pointing forward (mirrorable), other fingers curled
  sit_down      standing -> seated with root motion (seat contact: height ratio measured on the mesh)
  stand_up      seated -> standing (exact reverse of sit_down's poses)
  dense_test    60 fps, dense per-frame samples on several roles (mocap-like data; fps resampling test)"""
import argparse
import json
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clip_tools as CT  # noqa: E402
import retarget as RT  # noqa: E402

ID = [1.0, 0.0, 0.0, 0.0]


def rot(axis, deg):
    a = math.radians(deg) / 2
    n = RT.normalize(axis)
    return [math.cos(a), n[0] * math.sin(a), n[1] * math.sin(a), n[2] * math.sin(a)]


def rx(d):
    return rot([1, 0, 0], d)


def ry(d):
    return rot([0, 1, 0], d)


def rz(d):
    return rot([0, 0, 1], d)


def seq(*qs):
    """Applies rotations in order (first argument first), in the role's reference axes."""
    out = ID
    for q in qs:
        out = RT.qmul(q, out)
    return out


def mirror(q):
    return [q[0], q[1], -q[2], -q[3]]


def both(pose, role, q_left):
    pose[role + ".L"] = q_left
    pose[role + ".R"] = mirror(q_left)


def side(pose, role, q_left, s):
    """Left-side definition q_left applied to side s ('L' or 'R', mirrored for R)."""
    pose[f"{role}.{s}"] = q_left if s == "L" else mirror(q_left)


def lerp_pose(a, b, t):
    out = {}
    for k in set(a) | set(b):
        out[k] = CT._slerp(a.get(k, ID), b.get(k, ID), t)
    return out


# ------------------------------------------------------------------ poses (left-side definitions)
def relaxed():
    p = {}
    both(p, "upperArm", seq(rx(-8), rz(-76)))          # twist palm inward a little, arm down at the side
    both(p, "forearm", ry(-14))                       # elbow slightly bent forward
    both(p, "hand", rz(-4))
    for f, c in (("f0", 22), ("f1", 18), ("f2", 15), ("f3", 12)):
        both(p, f + "a", rz(-c))
        both(p, f + "b", rz(-c * 1.2))
    both(p, "thumbA", ry(12))
    both(p, "thumbB", ry(10))
    p["spine"] = rx(1.0)
    p["neck"] = rx(-1.0)
    return p


def arm_pose(base, s, upper, fore, hand, fingers=None, thumb=None):
    p = dict(base)
    side(p, "upperArm", upper, s)
    side(p, "forearm", fore, s)
    side(p, "hand", hand, s)
    for k, q in (fingers or {}).items():
        side(p, k, q, s)
    for k, q in (thumb or {}).items():
        side(p, k, q, s)
    return p


def seated(base, k=1.0, lean=6.0):
    """Hip flexion 88 deg and knee flexion 88 deg (shin back to vertical: feet flat), torso leaning `lean`."""
    p = dict(base)
    both(p, "thigh", seq(rz(-2 * k), rx(-88 * k)))
    both(p, "shin", rx(88 * k))
    both(p, "foot", ID)
    p["spine"] = rx(1.0 + lean)
    p["chest"] = rx(-0.4 * lean)
    p["neck"] = rx(-1.0 - 0.4 * lean)
    return p


# ------------------------------------------------------------------ clips
def clip_idle(R):
    n = 90
    keys = {}
    for f in range(0, n + 1, 6):
        t = 2 * math.pi * f / n
        p = relaxed()
        b = math.sin(t)                     # one breath per 3 s
        p["chest"] = rx(-1.2 * b)
        p["spine"] = RT.qmul(rx(-0.5 * b), p["spine"])
        p["neck"] = RT.qmul(rx(1.0 * b), p["neck"])
        w = math.sin(t + 1.1)               # weight shift (hips sway, legs compensate)
        p["hips"] = rz(0.9 * w)
        both(p, "thigh", rz(-0.9 * w))
        p["thigh.R"] = rz(-0.9 * w)         # both thighs counter-rotate the same way (feet stay put)
        p["head"] = seq(rx(0.8 * math.sin(2 * t + 0.4)), ry(1.6 * math.sin(t + 2.0)))
        both(p, "upperArm", seq(rx(-8), rz(-76 + 0.8 * b)))
        p["upperArm.R"] = mirror(seq(rx(-8), rz(-76 + 0.8 * b)))
        keys[f] = p
    return keys, {"name": "idle_relaxed", "loop": True, "frame_count": n, "fps": 30,
                  "description": "Relaxed stance with arms down, breathing, slight weight shift and head drift; loops every 3 s",
                  "mask": None}


def clip_wave(R):
    s = "R"
    base = relaxed()
    up = seq(rx(-90), rz(25))                         # external twist (palm forward), arm 25 deg above horizontal
    keys = {0: base, 10: arm_pose(base, s, up, ry(-75), rz(0)), 46: None, 56: base}
    for i, f in enumerate(range(14, 43, 4)):
        keys[f] = arm_pose(base, s, up, ry(-75 + (14 if i % 2 == 0 else -14)), ry(8 if i % 2 == 0 else -8))
    keys[46] = arm_pose(base, s, up, ry(-75), rz(0))
    mask = [f"{r}.{s}" for r in ("upperArm", "forearm", "hand")]
    return keys, {"name": "wave", "loop": False, "frame_count": 57, "fps": 30, "mask": mask,
                  "description": "Right-arm wave (palm forward, forearm swinging in the frontal plane); mirror for the left arm"}


def clip_point(R):
    s = "R"
    base = relaxed()
    curl = {f"{f}a": rz(-85) for f in ("f0", "f1", "f2")}
    curl.update({f"{f}b": rz(-95) for f in ("f0", "f1", "f2")})
    curl.update({"f3a": rz(-2), "f3b": rz(-2)})
    pt = arm_pose(base, s, seq(rx(-10), ry(-72), rz(-8)), ry(-8), rz(-4), curl, {"thumbA": ry(35), "thumbB": ry(30)})
    keys = {0: base, 14: pt, 40: pt, 54: base}
    mask = [f"{r}.{s}" for r in ("upperArm", "forearm", "hand", "thumbA", "thumbB", "f0a", "f0b", "f1a", "f1b", "f2a",
                                    "f2b", "f3a", "f3b")]
    return keys, {"name": "point", "loop": False, "frame_count": 55, "fps": 30, "mask": mask,
                  "description": "Right arm points forward with the index finger, other fingers curled; mirror for the left"}


SIT_ROOT = None  # set from the mannequin's proportions in main()


def sit_keys():
    base = relaxed()
    p8 = seated(base, 0.25, lean=16)
    p20 = seated(base, 0.6, lean=20)
    p32 = seated(base, 1.0, lean=9)
    p40 = seated(base, 1.0, lean=6)
    dz, dy = SIT_ROOT
    return {0: (base, [0, 0, 0]), 8: (p8, [0, dy * 0.12, dz * 0.25]), 20: (p20, [0, dy * 0.55, dz * 0.7]),
            32: (p32, [0, dy, dz]), 40: (p40, [0, dy, dz])}


def clip_sit_down(R):
    return sit_keys(), {"name": "sit_down", "loop": False, "frame_count": 41, "fps": 30, "mask": None,
                        "description": "Standing to seated on a seat behind the character (root moves down and back)"}


def clip_stand_up(R):
    k = sit_keys()
    rev = {40 - f: v for f, v in k.items()}
    return rev, {"name": "stand_up", "loop": False, "frame_count": 41, "fps": 30, "mask": None,
                 "description": "Seated to standing (the reverse of sit_down; starts in its final pose)"}


def clip_dense(R):
    n = 120
    keys = {}
    base = relaxed()
    for f in range(n):
        t = f / 60.0
        p = dict(base)
        p["head"] = seq(ry(18 * math.sin(2 * math.pi * 0.5 * t)), rx(6 * math.sin(2 * math.pi * 1.0 * t)))
        p["chest"] = rz(3 * math.sin(2 * math.pi * 0.5 * t))
        side(p, "upperArm", seq(rx(-8), rz(-76 + 25 * (0.5 - 0.5 * math.cos(2 * math.pi * 0.5 * t)))), "L")
        side(p, "forearm", ry(-14 - 40 * (0.5 - 0.5 * math.cos(2 * math.pi * 1.0 * t))), "L")
        side(p, "upperArm", seq(rx(-8), rz(-76 + 15 * math.sin(2 * math.pi * 0.25 * t) ** 2)), "R")
        keys[f] = p
    return keys, {"name": "dense_test", "loop": False, "frame_count": n, "fps": 60, "dense": True, "mask": None,
                  "description": "Technical test: 60 fps dense per-frame samples on several roles (mocap-like data)"}


def build_action(R, name, keys, meta):
    rig = R.rig
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = act
    for f in sorted(keys):
        v = keys[f]
        pose, root = v if isinstance(v, tuple) else (v, [0, 0, 0])
        R.pose_from_clip_rotations(pose, root)
        R.key(f)
    if meta.get("loop"):  # the loop seam: a key at frame N equal to frame 0 (frames 0..N-1 are exported)
        v = keys[0]
        pose, root = v if isinstance(v, tuple) else (v, [0, 0, 0])
        if meta["frame_count"] not in keys:
            R.pose_from_clip_rotations(pose, root)
            R.key(meta["frame_count"])
    for fc in act.fcurves if hasattr(act, "fcurves") else []:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
    meta = dict(meta, source="script", license="project", attribution="Plush Studio project (script-made, pipeline/clips/make_clips.py)")
    act["ps_clip_meta"] = json.dumps(meta)
    return act


def seat_ratio(R, frame):
    """Seat contact: lowest skin point under the pelvis in the seated pose, as a fraction of the leg length."""
    bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    hips = R.rig.pose.bones[R.src["hips"]]
    hp = R.rig.matrix_world @ hips.head
    low = None
    for o in bpy.data.objects:
        if o.type != "MESH" or not any(m.type == "ARMATURE" for m in o.modifiers):
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            w = o.matrix_world @ v.co
            if abs(w.x - hp.x) < 0.07 and hp.y - 0.02 < w.y < hp.y + 0.12:  # under the pelvis, behind/at the hip joint
                low = w.z if low is None else min(low, w.z)
        ev.to_mesh_clear()
    return low / R.leg


def main():
    global SIT_ROOT
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--mannequin", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--blend-out", default="")
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.mannequin))
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.get("ps_character_id"))
    R = CT.Rig(rig)
    # seated root: thigh horizontal over a vertical shin -> the hip moves down and back by about the thigh length
    th = R.data["roles"]["thigh.L"]["length"]
    k = math.radians(88)
    SIT_ROOT = (-th * math.sin(k) / R.leg, -th * (1 - math.cos(k)) / R.leg)
    sc = bpy.context.scene
    made = []
    for fn in (clip_idle, clip_wave, clip_point, clip_sit_down, clip_stand_up, clip_dense):
        keys, meta = fn(R)
        sc.render.fps = int(meta["fps"])
        act = build_action(R, meta["name"], keys, meta)
        sc.frame_start, sc.frame_end = 0, meta["frame_count"] - 1
        if meta["name"] == "sit_down":
            m = json.loads(act["ps_clip_meta"])
            m["contacts"] = [{"type": "seat", "frames": [32, 40], "height_ratio": round(seat_ratio(R, 40), 4),
                              "note": "seat top height = height_ratio x the character's leg length"},
                             {"type": "foot_plant", "role": "foot.L", "frames": [0, 40]},
                             {"type": "foot_plant", "role": "foot.R", "frames": [0, 40]}]
            act["ps_clip_meta"] = json.dumps(m)
            seat = m["contacts"][0]
        if meta["name"] == "stand_up":
            m = json.loads(act["ps_clip_meta"])
            m["contacts"] = [dict(seat, frames=[0, 8]), {"type": "foot_plant", "role": "foot.L", "frames": [0, 40]},
                             {"type": "foot_plant", "role": "foot.R", "frames": [0, 40]}]
            act["ps_clip_meta"] = json.dumps(m)
        made.append(CT.export_action(rig, act, os.path.abspath(a.out)))
        print("[make_clips]", made[-1])
    if a.blend_out:
        rig.animation_data.action = None
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend_out), compress=True)


main()
