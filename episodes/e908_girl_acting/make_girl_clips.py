"""Writes the girl's gesture clips content/clips/girl_*.clip.json (T-097-girl; headless Blender, deterministic).

    blender -b --factory-startup -P episodes/e908_girl_acting/make_girl_clips.py -- \
        --mannequin <dir>/neutral_mannequin.blend --out content/clips

Same path as the shared validation clips (pipeline/clips/make_clips.py, read-only here: its pose helpers are loaded
from its source, nothing is copied or changed): poses are joint rotations in each role's reference frame, played with
the shared acting principles (pipeline/clips/clip_principles.py: anticipation, successive breaking, overshoot and
settle, whole-body support) and exported by the shared exporter (clip_tools.export_action). The arm poses are solved
on the girl's own proportions (girl_arm_ik.py), so the retargeted hand lands on her chin / points at the table.

Reference (docs/evaluation/animation/T-106/performance.csv, watertable girl, WT f = frames@24):
  hand at chin, eyes wide, rounded mouth      WT [0, 15)   15 f
  blink as the hand leaves the chin            WT [15, 22)   7 f
  lean and point down                          WT [22, 39)  17 f
  sustain the point                            WT [39, 61)  22 f
  draw the hand back                           WT [61, 81)  20 f
  straighten, settle to the soft smile         WT [81, 96)  15 f
  hold upright, arms down                      WT [96, 121) 25 f
Clip frames = playback frames x TEMPO: the engine plays a character's gesture clips at her tempo.action_speed (1.1,
content/personality/girl_auburn_bun_glasses.json), so a clip authored at 24 fps with WT durations x 1.1 plays back at
the reference durations.

Clips (24 fps, right arm, mirrorable; mask hips, spine, chest, right arm and fingers; rest = the shared stance arms):
  girl_chin_think   rest -> hand to chin (brisk 14 f) -> hold 15 f -> lower (14 f)                  invented rise / lower
  girl_point_down   rest -> lean and point down (17 f) -> hold 22 f -> draw back (20 f) -> straighten (15 f)
  girl_wonder_point the watertable sequence in one: rise to the chin, hold 15 f, leave the chin 7 f, lean and point
                    17 f, hold 22 f, draw back 20 f, straighten 15 f, rest
"""
import argparse
import math
import os
import sys

import bpy  # noqa: F401  (Blender)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CLIPS = os.path.join(ROOT, "pipeline", "clips")
sys.path.insert(0, CLIPS)
sys.path.insert(0, HERE)
import clip_principles as CP  # noqa: E402
import clip_tools as CT  # noqa: E402
import girl_arm_ik as K  # noqa: E402
import girl_beats as GB  # noqa: E402

# the shared pose helpers of make_clips.py (its module body without the trailing main() call)
_src = open(os.path.join(CLIPS, "make_clips.py")).read()
_src = _src[:_src.rindex("\nmain()")]
MC = {"__file__": os.path.join(CLIPS, "make_clips.py"), "__name__": "make_clips_helpers"}
exec(compile(_src, os.path.join(CLIPS, "make_clips.py"), "exec"), MC)

# Solver targets (left-side definition, girl rest frame), closed-loop calibrated on the girl's own bake by
# calibrate_clips.py (the engine's arm-body clearance and the gaze head pitch move the hand; clip_calibration.json).
CAL = {"chin_target": [0.012, 0.672, 0.11], "point_dir": [0.0, -0.46, 0.88]}
_cal = os.path.join(HERE, "clip_calibration.json")
if os.path.isfile(_cal):
    CAL.update({k: v for k, v in __import__("json").load(open(_cal)).items() if k in CAL})

TEMPO = GB.TEMPO  # tempo.action_speed of the girl's profile: clip frames = playback frames x TEMPO
S = "R"
FPS = 24


def cf(wt_frames):
    """Clip frames for a duration in playback (reference) frames."""
    return wt_frames * TEMPO


def arm(pose, params):
    """Sets the right arm (upperArm, forearm, hand) from left-side solver parameters (mirrored)."""
    up, fo, ha = K.arm_points(params)[5]
    MC["side"](pose, "upperArm", up, S)
    MC["side"](pose, "forearm", fo, S)
    MC["side"](pose, "hand", ha, S)


def chin_pose():
    """Right hand at the chin, curled fingers against it (WT f000-f012: hand at chin, 'oh' mouth). Knuckle target: just
    in front of the girl's chin (0.11.0 mesh: face front z 0.08-0.10 m at y 0.67-0.69 m), a little to her right of the
    midline; the hand points up and in. Her arms are short (0.18 m) and her vest is full: forearm and wrist stay
    0.14 m in front of the body and the elbow comes up to shoulder height, otherwise the engine's clip-arm lift (T-047
    collision body) turns the whole arm out and the hand ends 5 cm off the chin (probe: README)."""
    p = MC["gesture_base"](S)
    params, err = K.solve_arm(CAL["chin_target"], [-1.0, 1.0, 0.3], [0, -40, -60, -120, 0, 0, 0], front=0.14, elbow_drop=0.0)
    arm(p, params)
    for f, c in (("f3", 35), ("f2", 45), ("f1", 55), ("f0", 60)):  # index (f3) loosest: the knuckle line under the chin
        MC["side"](p, f + "a", MC["rz"](-c), S)
        MC["side"](p, f + "b", MC["rz"](-c * 1.1), S)
    MC["side"](p, "thumbA", MC["ry"](30), S)
    MC["side"](p, "thumbB", MC["ry"](20), S)
    return p, err


LEAN = 8.0  # degrees forward (spine), WT f022-f039: she leans in as she points (face 22 px down)


def point_pose():
    """Right arm points down and forward at the task in front of her (WT f022-f060: leans and points down at the boat),
    index straight, other fingers curled (the shared point clip's hand). Solved with the lean applied to the chest."""
    p = MC["gesture_base"](S)
    chest_q = MC["rx"](LEAN)
    sh = [0.098, 0.614, 0.0]
    d = K.norm(CAL["point_dir"])  # left definition: a little across the body (towards the midline), down, forward
    reach = 0.94 * (K.GIRL["upper"] + K.GIRL["fore"] + K.GIRL["hand"])
    target = K.add(K.add([0.0, 0.536, 0.0], K.qrot(chest_q, K.sub(sh, [0.0, 0.536, 0.0]))), K.scale(d, reach))
    params, err = K.solve_arm(target, d, [-10, -30, -60, -10, 0, 0, 0], chest_q=chest_q, elbow_drop=0.0, point_dir=d)
    arm(p, params)
    curl = {f"{f}a": MC["rz"](-85) for f in ("f0", "f1", "f2")}
    curl.update({f"{f}b": MC["rz"](-95) for f in ("f0", "f1", "f2")})
    curl.update({"f3a": MC["rz"](-2), "f3b": MC["rz"](-2), "thumbA": MC["ry"](35), "thumbB": MC["ry"](30)})
    for kk, q in curl.items():
        MC["side"](p, kk, q, S)
    return p, err


def finish(keys, k_support, n, name, description):
    """Body support (lean in towards the point), a light breath; returns keys and the clip meta."""
    keys = MC["with_support"](keys, S, k_support, tilt=2.0, counter=0.45, chest=0.3, yaw=4.0, lean=LEAN)
    mask = ["hips", "spine", "chest"] + [f"{r}.{S}" for r in ("upperArm", "forearm", "hand") + MC["FINGERS"]]
    return keys, {"name": name, "loop": False, "frame_count": n, "fps": FPS, "mask": mask,
                  "mirror": {"suffix": [".L", ".R"], "axis": "x", "note": "mirrorable"},
                  "description": description,
                  "reference": "docs/evaluation/animation/T-106/performance.csv (watertable, girl); clip frames = "
                               "playback frames x 1.1 (tempo.action_speed)"}


def delays():
    rest = MC["gesture_base"](S)
    return {r: 1.0 * max(0, CP.depth_of(r) - 2) for r in rest if r.endswith("." + S)}


def clip_chin_think():
    rest = MC["gesture_base"](S)
    chin, _ = chin_pose()
    a = 2
    b = a + cf(GB.WONDER[0][1])   # brisk rise (girl_beats.WONDER)
    c = b + cf(15)   # WT chin hold [0, 15)
    d = c + cf(14)   # lower (invented, a short return)
    n = int(math.ceil(d + cf(3)))
    beats = [CP.Beat(a, rest, anticipation=0.06, ant=0.15, overshoot=0.03, settle=0.25, power=1.5),
             CP.Beat(b, chin, power=2.0), CP.Beat(c, chin, power=1.8), CP.Beat(d, rest)]
    keys = CP.perform(beats, n, delays())
    k = [(a, 0.0, dict(power=2.0)), (b, 0.25, dict(power=2.0)), (c, 0.25, dict(power=2.0)), (d, 0.0, None)]
    return finish(keys, k, n, "girl_chin_think",
                  "Girl: right hand rises briskly to the chin and holds there (thinking, wonder: WT f000-f015), then "
                  "lowers; solved on her proportions; mirror for the left")


def clip_point_down():
    rest = MC["gesture_base"](S)
    pt, _ = point_pose()
    a = 2
    b = a + cf(17)   # WT lean and point [22, 39)
    c = b + cf(22)   # WT point hold [39, 61)
    d = c + cf(20)   # WT draw back [61, 81)
    e = d + cf(15)   # WT straighten [81, 96)
    n = int(math.ceil(e + cf(3)))
    beats = [CP.Beat(a, rest, anticipation=0.08, ant=0.14, overshoot=0.04, settle=0.3, power=1.8),
             CP.Beat(b, pt, power=1.8), CP.Beat(c, pt, power=1.6), CP.Beat(d, rest, power=1.6), CP.Beat(e, rest)]
    keys = CP.perform(beats, n, delays())
    k = [(a, 0.0, dict(power=2.0)), (b, 1.0, dict(power=2.0)), (c, 1.0, dict(power=1.6)), (d, 0.35, dict(power=1.6)),
         (e, 0.0, None)]
    return finish(keys, k, n, "girl_point_down",
                  "Girl: leans in and points down at the task with the right index (WT f022-f096 timing: point 17 f, "
                  "hold 22 f, draw back 20 f, straighten 15 f); mirror for the left")


def clip_wonder_point():
    rest = MC["gesture_base"](S)
    chin, _ = chin_pose()
    pt, _ = point_pose()
    t0 = GB.LEAD
    t1, t2, t3, t4, t5, t6, t7 = GB.wonder_clip_frames()  # chin, leave, off, point, hold end, drawn back, straight
    n = int(math.ceil(t7 + cf(4)))
    off = MC["lerp_pose"](chin, pt, 0.18)  # leaving the chin: the hand drops off it towards the point
    beats = [CP.Beat(t0, rest, anticipation=0.06, ant=0.15, overshoot=0.03, settle=0.25, power=1.5),
             CP.Beat(t1, chin, power=1.8), CP.Beat(t2, chin, power=1.6), CP.Beat(t3, off, power=1.6),
             CP.Beat(t4, pt, power=1.6), CP.Beat(t5, pt, power=1.6), CP.Beat(t6, rest, power=1.6), CP.Beat(t7, rest)]
    keys = CP.perform(beats, n, delays())
    k = [(t0, 0.0, dict(power=1.6)), (t1, 0.25, dict(power=2.0)), (t2, 0.25, dict(power=1.6)),
         (t3, 0.4, dict(power=1.6)), (t4, 1.0, dict(power=2.0)), (t5, 1.0, dict(power=1.6)),
         (t6, 0.35, dict(power=1.6)), (t7, 0.0, None)]
    return finish(keys, k, n, "girl_wonder_point",
                  "Girl, watertable signature: hand to chin in wonder, holds, leaves the chin, leans in and points "
                  "down, holds the point, draws back and straightens (T-106 WT f000-f096); mirror for the left")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--mannequin", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.mannequin))
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.get("ps_character_id"))
    R = CT.Rig(rig)
    heads = {r: CT.to_engine(rig.matrix_world @ rig.data.bones[b].head_local) for r, b in R.src.items()}
    MC["BODY"] = CP.Body.from_heads(heads, R.leg)
    print("[make_girl_clips] chin knuckle error %.2f mm, point %.2f mm" % (chin_pose()[1] * 1e3, point_pose()[1] * 1e3))
    sc = bpy.context.scene
    for fn in (clip_chin_think, clip_point_down, clip_wonder_point):
        keys, meta = fn()
        sc.render.fps = FPS
        act = MC["build_action"](R, meta["name"], keys, meta)
        act["ps_clip_meta"] = act["ps_clip_meta"].replace("pipeline/clips/make_clips.py",
                                                          "episodes/e908_girl_acting/make_girl_clips.py")
        sc.frame_start, sc.frame_end = 0, meta["frame_count"] - 1
        print("[make_girl_clips]", CT.export_action(rig, act, os.path.abspath(a.out)))


main()
