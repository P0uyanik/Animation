"""Creates the T-003 emotion posture and gesture clips on the neutral mannequin and exports them (headless Blender).

    blender -b --factory-startup -P pipeline/clips/make_emotion_clips.py -- --mannequin <dir>/neutral_mannequin.blend \
        --out content/clips
    <python with bpy> pipeline/clips/make_emotion_clips.py --check   (forward-kinematics plausibility table, no scene)

Same authoring path as make_clips.py (its pose helpers and relaxed() pose are reused, its exporter clip_tools.export_action
writes plush.clip/1): poses are joint rotations in reference (T-pose, engine) axes relative to the semantic parent;
right-side motion is the mirror of the left-side definition. Script-made, technical quality (owner decision
Option 1). Masks name only the roles a posture changes, so the base idle keeps everything else (hips and legs are
never in an emotion mask: walking keeps them).

Postures (hold = 2 identical frames, held by playback; loop = cyclic):
  emo_happy (hold)  chest lifted, chin up, arms slightly open      emo_laugh (loop 20) happy + chest/head bounces
  emo_sad (hold)    slumped spine/chest, head down, arms forward   emo_sob (loop 36)   deeper sad + sob heaves
  emo_angry (hold)  forward lean, head jutting, tense bent arms    emo_surprised (hold) pulled back, hands raised
  emo_confused (hold) head tilt and turn                           emo_afraid (loop 12) hunched, arms guarding, tremble
  emo_sleepy (loop 120) slumped, head drooping and swaying         emo_curious (hold) lean in, head tilt
Gestures (one-shot, start and end in the relaxed pose):
  gest_shrug (52 frames) forearms out, palms up                gest_yawn (84 frames) head back, arms stretch up"""
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

TORSO = ["spine", "chest", "neck", "head"]
ARMS = [f"{r}.{s}" for r in ("upperArm", "forearm", "hand") for s in ("L", "R")]


def arms(p, upper, fore, hand=None):
    both(p, "upperArm", upper)
    both(p, "forearm", fore)
    if hand is not None:
        both(p, "hand", hand)


def torso(p, spine=0.0, chest=0.0, neck=0.0, head=None):
    p["spine"] = rx(spine)
    p["chest"] = rx(chest)
    p["neck"] = rx(neck)
    p["head"] = head if head is not None else MC.ID


# ------------------------------------------------------------------ postures
def happy(bounce=0.0):
    p = relaxed()
    torso(p, -2 - 0.6 * bounce, -4 - 2.5 * bounce, -2, rx(-5 - 3 * bounce))
    arms(p, seq(rx(-8), rz(-68)), ry(-20))
    return p


def laugh(t):
    s = math.sin(2 * math.pi * t)  # one bounce per cycle (20 frames: 1.5 per second)
    p = relaxed()
    torso(p, -1 + 1.2 * s, -7 + 3 * s, -3, rx(-12 + 3 * s))
    arms(p, seq(rx(-8), rz(-66), ry(-18)), ry(-55 + 4 * s), rz(-6))
    return p


def sad(k=1.0, heave=0.0):
    p = relaxed()
    torso(p, 7 * k + 1.2 * heave, 6 * k + 2.5 * heave, 6 * k, rx(14 * k - 2.5 * heave))
    arms(p, seq(rx(-8), rz(-82), ry(-22 * k)), ry(-12 - 10 * (k - 1)))
    return p


def sob(t):
    # two quick heaves, then a slower recovery (one 1.2 s cycle)
    h = math.exp(-((t - 0.15) / 0.07) ** 2) + 0.8 * math.exp(-((t - 0.38) / 0.08) ** 2)
    h += math.exp(-((t - 1.15) / 0.07) ** 2)  # wraps smoothly into the next cycle
    p = sad(1.35, heave=h)
    arms(p, seq(rx(-8), rz(-80), ry(-28)), ry(-38), rz(-8))
    return p


def angry():
    p = relaxed()
    torso(p, 6, -2, 8, rx(-6))
    arms(p, seq(rx(-8), rz(-64), ry(-8)), ry(-58), rz(-10))
    return p


def surprised():
    p = relaxed()
    torso(p, -4, -6, -3, rx(-7))
    arms(p, seq(rx(-8), rz(-58), ry(-16)), ry(-78), rz(22))
    return p


def confused():
    p = relaxed()
    torso(p, 0, 0, 0, seq(rz(12), ry(8)))
    p["neck"] = rz(4)
    return p


def afraid(t):
    s, c = math.sin(2 * math.pi * t), math.cos(2 * math.pi * 2 * t)
    p = relaxed()
    torso(p, 6, 5 + 0.6 * c, -5, seq(rx(10), ry(1.2 * s)))
    p["chest"] = seq(rx(5 + 0.6 * c), rz(0.8 * s))
    arms(p, seq(rx(-8), rz(-56), ry(-36)), ry(-104), rz(24))
    return p


def sleepy(t):
    s = math.sin(2 * math.pi * t)
    p = relaxed()
    torso(p, 6, 5, 9 + 1.5 * s, seq(rx(16 + 2 * s), rz(4 * math.sin(2 * math.pi * t + 0.7))))
    return p


def curious():
    p = relaxed()
    torso(p, 3, 4, 9, seq(rx(-5), rz(-10), ry(-6)))
    return p


# ------------------------------------------------------------------ gestures (start and end relaxed)
def shrug(k):
    p = relaxed()
    arms(p, seq(rx(-8 - 40 * k), rz(-76 + 14 * k), ry(-18 * k)), ry(-14 - 66 * k), rz(-4 + 22 * k))
    return p


def yawn(k):
    p = relaxed()
    torso(p, -3 * k, -6 * k, -6 * k, rx(-18 * k))
    arms(p, seq(rx(-8), rz(-76 + 116 * k)), ry(-14 - 16 * k), rz(-4))
    return p


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def hold(name, pose, mask, desc):
    return {0: pose, 1: pose}, {"name": name, "loop": False, "frame_count": 2, "fps": 30, "mask": mask,
                                "description": desc + " (posture: held)"}


def loop(name, fn, n, mask, desc, step=1):
    keys = {f: fn(f / n) for f in range(0, n, step)}
    return keys, {"name": name, "loop": True, "frame_count": n, "fps": 30, "mask": mask,
                  "description": desc + f" (posture: loops every {n / 30:.2f} s)"}


def one_shot(name, fn, n, rise, fall, mask, desc):
    """Relaxed (0-4), rise to the gesture (4-rise), hold, return (fall-(n-5)), relaxed to the end."""
    keys = {}
    for f in range(0, n, 2):
        k = ease((f - 4) / (rise - 4)) if f < fall else 1 - ease((f - fall) / (n - 5 - fall))
        keys[f] = fn(k)
    keys[n - 1] = fn(0)
    return keys, {"name": name, "loop": False, "frame_count": n, "fps": 30, "mask": mask, "description": desc}


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
        loop("emo_sleepy", sleepy, 120, TORSO, "Emotion sleepy: slumped, head drooping and swaying", step=4),
        hold("emo_curious", curious(), TORSO, "Emotion curious: leaning in, head tilted"),
        one_shot("gest_shrug", shrug, 52, 22, 32, ARMS, "Gesture shrug: forearms out, palms up"),
        one_shot("gest_yawn", yawn, 84, 30, 52, TORSO + ARMS, "Gesture yawn: head back, arms stretch up"),
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
