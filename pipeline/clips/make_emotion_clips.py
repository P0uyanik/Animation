"""Creates the T-003 emotion posture and gesture clips on the neutral mannequin and exports them (headless Blender).

    blender -b --factory-startup -P pipeline/clips/make_emotion_clips.py -- --mannequin <dir>/neutral_mannequin.blend \
        --out content/clips
    <python with bpy> pipeline/clips/make_emotion_clips.py --check   (forward-kinematics plausibility table, no scene)

Same authoring path as make_clips.py (its pose helpers and stance_arms() pose are reused, its exporter
clip_tools.export_action writes plush.clip/1): poses are joint rotations in reference (T-pose, engine) axes relative
to the semantic parent; right-side motion is the mirror of the left-side definition, with a small right-side
variation so postures are not mirror-symmetric. Script-made. T-027 acting pass (clip_principles.py): postures start
from the idle's asymmetric stance arms; loops travel up the chain with per-joint phase lags (overlap) and eased,
non-sinusoidal pulses; gestures use anticipation, overshoot and settle and successive breaking (trunk, shoulder,
elbow, wrist; the two arms out of sync). Masks name only the roles a posture changes, so the base idle keeps
everything else (hips and legs are never in an emotion mask: walking keeps them).

Postures (hold = 2 identical frames, held by playback; loop = cyclic):
  emo_happy (hold)  chest lifted, chin up, arms slightly open      emo_laugh (loop 20) happy + chest/head bounces
  emo_sad (hold)    slumped spine/chest, head down, arms forward   emo_sob (loop 36)   deeper sad + sob heaves
  emo_angry (hold)  forward lean, head jutting, tense bent arms    emo_surprised (hold) pulled back, hands raised
  emo_confused (hold) head tilt and turn                           emo_afraid (loop 12) hunched, arms guarding, tremble
  emo_sleepy (loop 120) slumped, head drooping and swaying         emo_curious (hold) lean in, head tilt
Gestures (one-shot, start and end in the stance; torso and arms):
  gest_shrug (52 frames) forearms out, palms up, chest / head  gest_yawn (84 frames) head back, arms stretch up"""
import argparse
import json
import math
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# make_clips.py's helpers (rot, seq, mirror, both, side, relaxed, build_action) without running its main()
_src = open(os.path.join(HERE, "make_clips.py")).read()
_src = _src[:_src.rindex("\nmain()")]
MC = types.ModuleType("make_clips_helpers")
MC.__file__ = os.path.join(HERE, "make_clips.py")
exec(compile(_src, MC.__file__, "exec"), MC.__dict__)
rx, ry, rz, seq, both, side, mirror, relaxed = MC.rx, MC.ry, MC.rz, MC.seq, MC.both, MC.side, MC.mirror, MC.relaxed
CP = MC.CP  # clip_principles (T-027): anticipation, overshoot / settle, overlap, eased spacing
RT_ = MC.RT

TORSO = ["spine", "chest", "neck", "head"]
ARMS = [f"{r}.{s}" for r in ("upperArm", "forearm", "hand") for s in ("L", "R")]


def arms(p, upper, fore, hand=None, asym=1.0):
    """Both arms from one left-side definition, then a small right-side variation (asym x a few degrees: the right
    arm a little more bent and closer) so postures are not mirror-symmetric."""
    both(p, "upperArm", upper)
    both(p, "forearm", fore)
    if hand is not None:
        both(p, "hand", hand)
    if asym:
        p["upperArm.R"] = RT_.qmul(p["upperArm.R"], mirror(seq(rz(-3 * asym), rx(-4 * asym))))
        p["forearm.R"] = RT_.qmul(p["forearm.R"], mirror(ry(-6 * asym)))
        p["hand.R"] = RT_.qmul(p.get("hand.R", MC.ID), mirror(rz(-4 * asym)))


def base_pose():
    """Postures start from the asymmetric stance arms of the idle (make_clips.stance_arms)."""
    return MC.stance_arms({})


def lag(t, role, turns):
    """Overlap in loops: the phase of a role lags its chain depth x turns (chest leads, neck / head / arms follow)."""
    return t - turns * CP.depth_of(role)


def pulse(x, rise=0.3):
    """Periodic pulse in [-1, 1] with a fast rise and a slow fall (eased, not a sine): x in turns."""
    x = x % 1.0
    if x < rise:
        return -1 + 2 * CP.ease(x / rise, "inout", 2.0)
    return 1 - 2 * CP.ease((x - rise) / (1 - rise), "inout", 1.6)


def torso(p, spine=0.0, chest=0.0, neck=0.0, head=None):
    p["spine"] = rx(spine)
    p["chest"] = rx(chest)
    p["neck"] = rx(neck)
    p["head"] = head if head is not None else MC.ID


# ------------------------------------------------------------------ postures
def happy(bounce=0.0):
    p = base_pose()
    torso(p, -2 - 0.6 * bounce, -4 - 2.5 * bounce, -2, rx(-5 - 3 * bounce))
    arms(p, seq(rx(-8), rz(-68)), ry(-20))
    return p


def laugh(t):
    # one bounce per cycle (20 frames: 1.5 per second): a quick "ha" (fast rise, slow fall) that travels up the chain
    s = lambda r: pulse(lag(t, r, 0.05))
    p = base_pose()
    torso(p, -1 + 1.2 * s("spine"), -7 + 3 * s("chest"), -3 + 0.8 * s("neck"), seq(rx(-12 + 3 * s("head")), rz(2.0)))
    arms(p, seq(rx(-8), rz(-66), ry(-18)), ry(-55 + 4 * s("forearm.L")), rz(-6))
    p["forearm.R"] = RT_.qmul(p["forearm.R"], mirror(ry(2 * (s("hand.R") - s("forearm.L")))))  # the right arm drags
    return p


def sad(k=1.0, heave=0.0):
    p = base_pose()
    torso(p, 5 * k + 1.2 * heave, 5 * k + 2.5 * heave, 2 * k, rx(4 * k - 2.5 * heave))
    arms(p, seq(rx(-8), rz(-82), ry(-22 * k)), ry(-12 - 10 * (k - 1)))
    return p


def sob(t):
    # two quick heaves, then a slower recovery (one 1.2 s cycle); the head and arms follow the chest a little later
    def heave(x):
        x = x % 1.0
        h = math.exp(-((x - 0.15) / 0.07) ** 2) + 0.8 * math.exp(-((x - 0.38) / 0.08) ** 2)
        return h + math.exp(-((x - 1.15) / 0.07) ** 2) + math.exp(-((x + 0.85) / 0.07) ** 2)  # wraps smoothly
    p = sad(1.2, heave=heave(t))
    hh = heave(lag(t, "head", 0.02))
    p["head"] = rx(4 * 1.2 - 2.5 * hh)
    p["neck"] = rx(2 * 1.2 + 0.6 * heave(lag(t, "neck", 0.02)))
    arms(p, seq(rx(-8), rz(-80), ry(-28)), ry(-38 - 3 * heave(lag(t, "forearm.L", 0.02))), rz(-8))
    return p


def angry():
    p = base_pose()
    torso(p, 6, -2, 8, rx(-6))
    arms(p, seq(rx(-8), rz(-64), ry(-8)), ry(-58), rz(-10))
    return p


def surprised():
    p = base_pose()
    torso(p, -4, -6, -3, rx(-7))
    arms(p, seq(rx(-8), rz(-58), ry(-16)), ry(-78), rz(22))
    return p


def confused():
    p = base_pose()
    torso(p, 0, 0, 0, seq(rz(12), ry(8)))
    p["neck"] = rz(4)
    return p


def afraid(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * 2 * t)
    sh = math.sin(2 * math.pi * lag(t, "head", 0.06))
    ca = math.cos(2 * math.pi * 2 * lag(t, "hand.L", 0.06))
    p = base_pose()
    torso(p, 6, 5 + 0.6 * c, -5, seq(rx(10), ry(1.2 * sh)))
    p["chest"] = seq(rx(5 + 0.6 * c), rz(0.8 * s))
    arms(p, seq(rx(-8), rz(-56), ry(-36)), ry(-104 + 0.8 * ca), rz(24))
    return p


def sleepy(t):
    s = math.sin(2 * math.pi * t)
    sh = math.sin(2 * math.pi * lag(t, "head", 0.03))  # the head drops a little after the neck (overlap)
    p = base_pose()
    torso(p, 5, 4, 6 + 1.5 * s, seq(rx(8 + 2 * sh), rz(4 * math.sin(2 * math.pi * lag(t, "head", 0.03) + 0.7))))
    return p


def curious():
    p = base_pose()
    torso(p, 3, 4, 9, seq(rx(-5), rz(-10), ry(-6)))
    return p


# ------------------------------------------------------------------ gestures (start and end in the stance)
def shrug_pose(k=1.0):
    """Shrug: forearms out, palms up, shoulders up (chest lifts back), head tilts; the right side goes a little higher."""
    p = base_pose()
    torso(p, 0.0, -3.5 * k, 2 * k, seq(rz(7 * k), rx(-3 * k)))  # the spine stays with the layer underneath (not in the mask)
    arms(p, seq(rx(-8 - 40 * k), rz(-76 + 14 * k), ry(-18 * k)), ry(-14 - 66 * k), rz(-4 + 22 * k), asym=0.0)
    p["upperArm.R"] = RT_.qmul(p["upperArm.R"], mirror(rz(4 * k)))
    return p


def yawn_pose(k=1.0):
    """Yawn: head back, arms stretch up; the left arm reaches higher than the right."""
    p = base_pose()
    torso(p, -3 * k, -6 * k, -6 * k, seq(rx(-18 * k), rz(-3 * k)))
    arms(p, seq(rx(-8), rz(-76 + 116 * k)), ry(-14 - 16 * k), rz(-4), asym=0.0)
    p["upperArm.R"] = RT_.qmul(p["upperArm.R"], mirror(rz(-12 * k)))
    p["forearm.R"] = RT_.qmul(p["forearm.R"], mirror(ry(-10 * k)))
    return p


def gesture(beats, n, side_lead=1.0):
    """Plays gesture beats with successive breaking (trunk -> neck -> head and shoulder -> elbow -> wrist, 1.5 frames
    per joint) and the right side following the left by side_lead frames (the two arms are not in sync)."""
    roles = set().union(*(b.pose for b in beats))
    delay = {r: 1.5 * max(0, CP.depth_of(r) - (1 if r in ("neck", "head") else 2)) + (side_lead if r.endswith(".R") else 0.0)
             for r in roles}
    delay.update({r: 0.0 for r in ("spine", "chest")})
    return CP.perform(beats, n, delay)


def gesture_rest():
    p = base_pose()
    torso(p)  # upright trunk (identity): the gesture starts and ends at the idle's centre
    return p


def shrug_keys(n=52):
    rest = gesture_rest()
    up = shrug_pose()
    beats = [CP.Beat(3, rest, anticipation=0.08, ant=0.1, overshoot=0.05, settle=0.18, power=1.5),
             CP.Beat(24, up, power=2.0), CP.Beat(29, up, overshoot=0.03, settle=0.15, power=1.5,
                                                 per_role={"upperArm.L": {"overshoot": 0.0}, "upperArm.R": {"overshoot": 0.0}}),
             CP.Beat(47, rest)]
    return gesture(beats, n)


def yawn_keys(n=84):
    rest = gesture_rest()
    up = yawn_pose()
    beats = [CP.Beat(3, rest, anticipation=0.15, ant=0.12, overshoot=0.06, settle=0.2, power=1.5),
             CP.Beat(36, up, power=2.0), CP.Beat(50, up, overshoot=0.04, settle=0.3, power=1.8,
                                                 per_role={"upperArm.L": {"overshoot": 0.0}, "upperArm.R": {"overshoot": 0.0}}),
             CP.Beat(76, rest)]
    return gesture(beats, n, side_lead=3.0)


def hold(name, pose, mask, desc):
    return {0: pose, 1: pose}, {"name": name, "loop": False, "frame_count": 2, "fps": 30, "mask": mask,
                                "description": desc + " (posture: held)"}


def loop(name, fn, n, mask, desc, step=1):
    keys = {f: fn(f / n) for f in range(0, n, step)}  # step 1: every frame keyed (authored spacing)
    return keys, {"name": name, "loop": True, "frame_count": n, "fps": 30, "mask": mask,
                  "description": desc + f" (posture: loops every {n / 30:.2f} s)"}


def one_shot(name, keys_fn, n, mask, desc):
    """A gesture from the stance and back (clip_principles beats, every frame keyed)."""
    return keys_fn(n), {"name": name, "loop": False, "frame_count": n, "fps": 30, "mask": mask, "description": desc}


def clips():
    return [
        hold("emo_happy", happy(), TORSO + ARMS, "Emotion happy: chest lifted, chin up, arms slightly open"),
        loop("emo_laugh", laugh, 20, TORSO + ARMS, "Emotion laugh: happy posture with chest and head bounces"),
        hold("emo_sad", sad(), TORSO + ARMS, "Emotion sad: slumped spine and chest, head down, arms hanging forward"),
        loop("emo_sob", lambda t: sob(t), 36, TORSO + ARMS, "Emotion cry: deeper sad posture with sob heaves"),
        hold("emo_angry", angry(), TORSO + ARMS, "Emotion angry: forward lean, head jutting, tense bent arms"),
        hold("emo_surprised", surprised(), TORSO + ARMS, "Emotion surprised: pulled back, hands raised"),
        hold("emo_confused", confused(), ["neck", "head"], "Emotion confused: head tilt and turn"),
        loop("emo_afraid", afraid, 12, TORSO + ARMS, "Emotion afraid: hunched, arms guarding, slight tremble"),
        loop("emo_sleepy", sleepy, 120, TORSO, "Emotion sleepy: slumped, head drooping and swaying"),
        hold("emo_curious", curious(), TORSO, "Emotion curious: leaning in, head tilted"),
        one_shot("gest_shrug", shrug_keys, 52, ["chest", "neck", "head"] + ARMS,
                 "Gesture shrug: forearms out, palms up, shoulders up and head tilt (anticipation, overlap, overshoot and settle)"),
        one_shot("gest_yawn", yawn_keys, 84, TORSO + ARMS,
                 "Gesture yawn: head back, arms stretch up, the left arm leading (anticipation, overlap, overshoot and settle)"),
    ]


# ------------------------------------------------------------------ plausibility check (no Blender)
def check():
    import retarget as RT
    prof = json.load(open(os.path.join(HERE, "..", "charsys", "rig_profiles", "humanoid_rigify.json")))
    ref = {}
    for k, v in prof["reference_pose"]["roles"].items():
        ref[k] = v
        if k.endswith(".L"):
            ref[k[:-2] + ".R"] = dict(v, parent=(v["parent"][:-2] + ".R") if (v["parent"] or "").endswith(".L") else v["parent"],
                                      ref_dir=[-v["ref_dir"][0], v["ref_dir"][1], v["ref_dir"][2]])
    print(f"{'clip':14s} {'frame':>5s}  head dir (x,y,z)        hand.L - shoulder (x left, y up, z fwd; arm len 1)")
    for keys, meta in clips():
        for f in sorted(keys)[:: max(1, len(keys) // 3)]:
            pose = keys[f]
            R = {}

            def g(role):
                if role not in R:
                    par = ref[role]["parent"]
                    R[role] = RT.qmul(g(par) if par else MC.ID, pose.get(role, MC.ID))
                return R[role]
            hd = RT.qrot(g("head"), ref["head"]["ref_dir"])
            hand = [0.0, 0.0, 0.0]
            for r in ("upperArm.L", "forearm.L"):
                d = RT.qrot(g(r), ref[r]["ref_dir"])
                hand = [hand[i] + 0.5 * d[i] for i in range(3)]
            print(f"{meta['name']:14s} {f:5d}  ({hd[0]:+.2f},{hd[1]:+.2f},{hd[2]:+.2f})  ({hand[0]:+.2f},{hand[1]:+.2f},{hand[2]:+.2f})")


def main():
    if "--check" in sys.argv:
        return check()
    import bpy
    import clip_tools as CT
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--mannequin", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.mannequin))
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.get("ps_character_id"))
    R = CT.Rig(rig)
    sc = bpy.context.scene
    for keys, meta in clips():
        sc.render.fps = int(meta["fps"])
        act = MC.build_action(R, meta["name"], keys, meta)
        sc.frame_start, sc.frame_end = 0, meta["frame_count"] - 1
        print("[make_emotion_clips]", CT.export_action(rig, act, os.path.abspath(a.out)))


main()
