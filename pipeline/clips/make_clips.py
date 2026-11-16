"""Creates the technical validation clips on the neutral mannequin and exports them (headless Blender).

    blender -b --factory-startup -P pipeline/clips/make_clips.py -- --mannequin <dir>/neutral_mannequin.blend \
        --out content/clips [--blend-out <dir>/mannequin_clips.blend]

Script-made (option 1 of the owner decision: script clips first, licensed motion capture later). Poses are written as
joint rotations in the REFERENCE (T-pose) frame of each role, relative to its semantic parent: e.g. the left upper
arm hangs down by rotating -78 degrees about z; a left elbow flexes forward about y; a hip flexes about -x. Right-side
motion is the mirror of the left-side definition (one definition, M · q · M). Every clip is a Blender action on the
mannequin, exported by the shared exporter (clip_tools.export_action), so a future artist-made clip goes the same way.

Clips. The acting clips (T-027) use the shared principles in clip_principles.py: anticipation, overshoot and
settle, successive breaking along the arm chain (arcs), whole-body support and eased spacing; poses are evaluated
per frame (every frame keyed), so the spacing is the authored one and not Blender's interpolation:
  idle_relaxed  loop, 180 frames: asymmetric contrapposto stance (weight right, feet planted by IK), weight drift,
                breathing travelling up the chain, head drift, arm overlap
  wave          right arm wave (mirrorable) with hip / spine support; held rest frames at both ends, 90 frames
  point         right arm and index finger pointing forward (mirrorable) with support, 84 frames
The technical clips keep their mechanical definition:
  sit_down      standing (the idle's stance) -> seated with root motion (seat contact: height ratio measured on the mesh)
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
import clip_principles as CP  # noqa: E402
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
    return p  # torso, neck and head upright (the reference): arm-only clips then match any upright torso


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
    p["spine"] = rx(lean)
    p["chest"] = rx(-0.4 * lean)
    p["neck"] = rx(-0.4 * lean)
    return p


# ------------------------------------------------------------------ acting poses (T-027, clip_principles.py)
FINGERS = ("thumbA", "thumbB", "f0a", "f0b", "f1a", "f1b", "f2a", "f2b", "f3a", "f3b")
BODY = None  # leg geometry of the authoring rig (clip_principles.Body), set in main()
REST_CURL = (("f0", 22), ("f1", 18), ("f2", 15), ("f3", 12))


def stance_arms(p):
    """Relaxed arms with left / right asymmetry: the right elbow is more bent and that arm a little forward."""
    side(p, "upperArm", seq(rx(-7), rz(-77), ry(-2)), "L")
    side(p, "forearm", ry(-11), "L")
    side(p, "hand", seq(rz(-3), ry(2)), "L")
    side(p, "upperArm", seq(rx(-11), rz(-74), ry(-7)), "R")
    side(p, "forearm", seq(ry(-24), rx(4)), "R")
    side(p, "hand", seq(rz(-8), rx(-5)), "R")
    for s, k in (("L", 1.0), ("R", 1.25)):
        for f, c in REST_CURL:
            side(p, f + "a", rz(-c * k), s)
            side(p, f + "b", rz(-c * 1.2 * k), s)
        side(p, "thumbA", ry(12 * k), s)
        side(p, "thumbB", ry(10 * k), s)
    return p


STANCE_HEAD = (1.5, -1.5, 0.5)  # head tilt (rz), turn (ry), nod (rx) of the idle stance, degrees (small: look aims from it)


def breath(t):
    """Breathing shape, t in turns: a slightly faster inhale than exhale (not a pure sine), mean 0, amplitude 1."""
    x = t % 1.0
    return math.sin(2 * math.pi * (x + 0.08 * math.sin(2 * math.pi * x)))


def open_hand(p, s, spread=1.0, curl=4.0):
    """Fingers nearly straight and slightly spread (a greeting hand); thumb out."""
    for f, sp in (("f0", -6), ("f1", -2), ("f2", 2), ("f3", 6)):
        side(p, f + "a", seq(rz(-curl), ry(sp * spread)), s)
        side(p, f + "b", rz(-curl * 0.8), s)
    side(p, "thumbA", ry(24), s)
    side(p, "thumbB", ry(8), s)


def stance(p, k=1.0):
    """The idle's weight shift onto the right leg (k = 1 at the stance centre) on pose p: pelvis shifted right and
    hiked on that side, spine and chest countering, both feet planted (the free left knee bends). Returns the root."""
    root = CP.support(p, "R", k, tilt=1.0, counter=0.8, chest=0.4, shift=0.02)
    return CP.plant_legs(p, root, BODY)


# ------------------------------------------------------------------ clips
def clip_idle(R):
    """Asymmetric contrapposto stance (weight on the right leg, pelvis hiked on that side and the spine countering it,
    feet planted by IK, the free knee bent), slow weight drift, breathing that travels up the chain (spine, chest,
    neck, shoulders lag each other), head drift from several harmonics and arm overlap. Loops every 6 s."""
    n = 180
    keys = {}
    lag = 0.015  # overlap: phase lag per chain level, in loop turns
    for f in range(n):
        t = f / n
        p = stance_arms({})
        b = lambda d: breath(3 * t - 3 * lag * d)  # three breaths per loop (2 s each)
        p["spine"] = rx(-0.5 * b(0))
        p["chest"] = rx(-1.3 * b(1))
        p["neck"] = rx(0.9 * b(2))
        tilt, turn, nod = STANCE_HEAD
        p["head"] = seq(rz(tilt + 0.8 * math.sin(2 * math.pi * (t + 0.3))),
                        ry(turn + 1.6 * math.sin(2 * math.pi * (t + 0.15)) + 0.6 * math.sin(2 * math.pi * (2 * t + 0.55))),
                        rx(nod + 0.6 * math.sin(2 * math.pi * (2 * t + 0.1)) + 0.4 * b(3)))
        for s, amp in (("L", 1.0), ("R", 0.75)):  # shoulders rise with the breath, arms sway with the weight drift
            sway = math.sin(2 * math.pi * (t - 0.06 - lag * 2)) * amp
            p[f"upperArm.{s}"] = RT.qmul(p[f"upperArm.{s}"], (lambda q: q if s == "L" else mirror(q))(seq(rz(0.7 * b(2)), rx(-1.0 * sway))))
            p[f"forearm.{s}"] = RT.qmul(p[f"forearm.{s}"], (lambda q: q if s == "L" else mirror(q))(ry(-1.4 * math.sin(2 * math.pi * (t - 0.06 - lag * 3)) * amp - 0.6 * b(3))))
            p[f"hand.{s}"] = RT.qmul(p[f"hand.{s}"], (lambda q: q if s == "L" else mirror(q))(rz(-1.2 * math.sin(2 * math.pi * (t - 0.06 - lag * 4)) * amp)))
        k = 1.0 + 0.3 * math.sin(2 * math.pi * (t + 0.6))  # weight drift around the stance
        keys[f] = (p, stance(p, k))
    return keys, {"name": "idle_relaxed", "loop": True, "frame_count": n, "fps": 30, "mask": None,
                  "description": "Relaxed asymmetric stance: weight on the right leg (feet planted, free knee bent), slow weight "
                                 "drift, breathing travelling up the spine, head drift and arm overlap; loops every 6 s"}


def gesture_base(s):
    """Start / end pose of an arm gesture on side s: the stance arms and an upright trunk (the idle's centre)."""
    return stance_arms({"hips": ID, "spine": ID, "chest": ID})


def with_support(keys, side_, k_beats, breath_period=60, **kw):
    """Adds whole-body support (clip_principles.support, timed by the scalar beats k_beats) and a light breath on the
    chest to each frame; returns {frame: (pose, root)}. The legs stay with the layer underneath (not in the mask)."""
    out = {}
    for f, p in keys.items():
        p = dict(p)
        p["chest"] = RT.qmul(p.get("chest", ID), rx(-0.8 * breath(f / breath_period)))
        CP.support(p, side_, CP.scalar_track(k_beats, f), **kw)
        out[f] = p  # no root motion: a gesture must not slide the feet of the layer underneath
    return out


def clip_wave(R):
    """Right-arm wave with acting: the body leads (weight and pelvis towards the waving side, spine countering, chest
    opening), a small dip before the arm rises (anticipation), shoulder, elbow, wrist and fingers break in succession
    (arcs), overshoot and settle at the top, three waves led by the upper-arm twist with the forearm and hand
    dragging, and a lower with follow-through. Held rest frames at both ends for blending; 90 frames (3 s)."""
    s = "R"
    rest = gesture_base(s)

    def arm_up(tw, fl, hd):  # raised arm, palm forward; tw: upper-arm twist, fl: elbow, hd: wrist (degrees)
        p = dict(rest)
        side(p, "upperArm", seq(rx(-90 + tw), rz(25)), s)
        side(p, "forearm", ry(-75 + fl), s)
        side(p, "hand", ry(hd), s)
        open_hand(p, s)
        return p
    raised = arm_up(0, 0, 0)
    out_p, in_p = arm_up(5, 11, 7), arm_up(-5, -11, -7)
    swing = dict(power=1.5, overshoot=0.04, settle=0.4)
    beats = [CP.Beat(3, rest, anticipation=0.08, ant=0.1, overshoot=0.05, settle=0.2, power=1.5), CP.Beat(28, raised, **swing)]
    for i in range(5):  # three waves, 5.5 frames per swing; the lower starts from the last swing
        beats.append(CP.Beat(33.5 + 5.5 * i, out_p if i % 2 == 0 else in_p, **swing))
    beats += [CP.Beat(61, in_p, anticipation=0.05, ant=0.1, overshoot=0.05, settle=0.22, power=1.5,
                      per_role={f"upperArm.{s}": {"overshoot": 0.0}}),
              CP.Beat(86, rest)]
    roles = [r for r in rest if r.endswith("." + s)]
    delay = {r: 1.0 * max(0, CP.depth_of(r) - 2) for r in roles}  # shoulder 0, elbow 1, wrist 2, fingers 3 frames
    keys = CP.perform(beats, 90, delay)
    k = [(2, 0.0, dict(power=2.0)), (22, 1.0, dict(overshoot=0.12, settle=0.35)), (65, 1.0, dict(power=2.0)), (87, 0.0, None)]
    keys = with_support(keys, s, k, tilt=2.5, counter=0.45, chest=0.3, yaw=4.0, lean=-2.5)
    mask = ["hips", "spine", "chest"] + [f"{r}.{s}" for r in ("upperArm", "forearm", "hand") + FINGERS]
    return keys, {"name": "wave", "loop": False, "frame_count": 90, "fps": 30, "mask": mask,
                  "description": "Right-arm wave (palm forward) with anticipation, successive breaking, overshoot and settle, and "
                                 "hip / spine support; mirror for the left arm"}


def clip_point(R):
    """Right-arm point with acting: a small pull back before the arm shoots out (anticipation), shoulder, elbow, wrist
    and fingers in succession (the index straightens while the others curl a few frames later), overshoot and
    settle, a small emphasis push, then a relaxed lower with follow-through; the body shifts weight towards the
    pointing side, turns the chest towards the target and leans in. 84 frames."""
    s = "R"
    rest = gesture_base(s)
    curl = {f"{f}a": rz(-85) for f in ("f0", "f1", "f2")}
    curl.update({f"{f}b": rz(-95) for f in ("f0", "f1", "f2")})
    curl.update({"f3a": rz(-2), "f3b": rz(-2), "thumbA": ry(35), "thumbB": ry(30)})
    pt = dict(rest)
    side(pt, "upperArm", seq(rx(-10), ry(-72), rz(-8)), s)
    side(pt, "forearm", ry(-8), s)
    side(pt, "hand", rz(-4), s)
    for kk, q in curl.items():
        side(pt, kk, q, s)
    push = dict(pt)
    side(push, "upperArm", seq(rx(-10), ry(-75), rz(-6)), s)
    side(push, "forearm", ry(-3), s)
    beats = [CP.Beat(3, rest, anticipation=0.12, ant=0.14, overshoot=0.06, settle=0.2, power=1.6),
             CP.Beat(28, pt, power=2.0), CP.Beat(36, pt, overshoot=0.1, settle=0.4, power=2.0), CP.Beat(42, push, power=2.0),
             CP.Beat(50, pt, power=2.0), CP.Beat(54, pt, anticipation=0.04, ant=0.1, overshoot=0.04, settle=0.22, power=1.6,
                                                 per_role={f"upperArm.{s}": {"overshoot": 0.0}}),
             CP.Beat(79, rest)]
    roles = [r for r in rest if r.endswith("." + s)]
    delay = {r: 1.2 * max(0, CP.depth_of(r) - 2) for r in roles}
    keys = CP.perform(beats, 84, delay)
    k = [(1, 0.0, dict(anticipation=0.15, ant=0.25, power=2.0)), (24, 1.0, dict(overshoot=0.1, settle=0.4)), (40, 1.0, dict(power=2.0)),
         (44, 1.15, dict(power=2.0)), (54, 1.0, dict(power=2.0)), (80, 0.0, None)]
    keys = with_support(keys, s, k, tilt=2.5, counter=0.45, chest=0.3, yaw=6.0, lean=3.0)
    mask = ["hips", "spine", "chest"] + [f"{r}.{s}" for r in ("upperArm", "forearm", "hand") + FINGERS]
    return keys, {"name": "point", "loop": False, "frame_count": 84, "fps": 30, "mask": mask,
                  "description": "Right arm points forward with the index finger (anticipation, overlap, overshoot and settle, "
                                 "body support towards the target); mirror for the left"}


SIT_ROOT = None  # set from the mannequin's proportions in main()
# Roles a sit / stand clip animates (arms, hips and head stay with the layer underneath, e.g. the base idle).
SIT_MASK = ["spine", "chest", "neck"] + [f"{r}.{x}" for r in ("thigh", "shin", "foot") for x in ("L", "R")]


def sit_keys():
    """Hold standing (0-8), sit (8-48), hold seated (48-56). The standing frames are the idle's stance (trunk, legs and
    root, T-027), so the clip blends in from the base idle without a leg pop; the seated poses are unchanged."""
    base = relaxed()
    st = {}
    st_root = stance(st)
    stand = dict(base)
    stand.update({r: q for r, q in st.items() if r in SIT_MASK})
    p16 = seated(base, 0.25, lean=16)
    p28 = seated(base, 0.6, lean=20)
    p40 = seated(base, 1.0, lean=9)
    p48 = seated(base, 1.0, lean=6)
    dz, dy = SIT_ROOT
    return {0: (stand, st_root), 8: (stand, st_root), 16: (p16, [0, dy * 0.12, dz * 0.25]),
            28: (p28, [0, dy * 0.55, dz * 0.7]), 40: (p40, [0, dy, dz]), 48: (p48, [0, dy, dz]), 56: (p48, [0, dy, dz])}


def clip_sit_down(R):
    return sit_keys(), {"name": "sit_down", "loop": False, "frame_count": 57, "fps": 30, "mask": SIT_MASK,
                        "description": "Standing to seated on a seat behind the character (root moves down and back)"}


def clip_stand_up(R):
    k = sit_keys()
    rev = {56 - f: v for f, v in k.items()}
    return rev, {"name": "stand_up", "loop": False, "frame_count": 57, "fps": 30, "mask": SIT_MASK,
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
    global SIT_ROOT, BODY
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--mannequin", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--blend-out", default="")
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.mannequin))
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.get("ps_character_id"))
    R = CT.Rig(rig)
    heads = {r: CT.to_engine(rig.matrix_world @ rig.data.bones[b].head_local) for r, b in R.src.items()}
    BODY = CP.Body.from_heads(heads, R.leg)
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
            m["contacts"] = [{"type": "seat", "frames": [40, 56], "height_ratio": round(seat_ratio(R, 56), 4),
                              "note": "seat top height = height_ratio x the character's leg length"},
                             {"type": "foot_plant", "role": "foot.L", "frames": [0, 56]},
                             {"type": "foot_plant", "role": "foot.R", "frames": [0, 56]}]
            act["ps_clip_meta"] = json.dumps(m)
            seat = m["contacts"][0]
        if meta["name"] == "stand_up":
            m = json.loads(act["ps_clip_meta"])
            m["contacts"] = [dict(seat, frames=[0, 16]), {"type": "foot_plant", "role": "foot.L", "frames": [0, 56]},
                             {"type": "foot_plant", "role": "foot.R", "frames": [0, 56]}]
            act["ps_clip_meta"] = json.dumps(m)
        made.append(CT.export_action(rig, act, os.path.abspath(a.out)))
        print("[make_clips]", made[-1])
    if a.blend_out:
        rig.animation_data.action = None
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend_out), compress=True)


main()
