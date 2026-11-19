"""Writes the boy's acting clips content/clips/boy_*.clip.json (T-097-boy, python3, no Blender).

    python3 episodes/e908_boy_acting/make_clips.py

Both clips are derived from validated library data, not new hand keys, so they keep the library's rig conventions
(plush.clip/1 rotations in each role's T-pose reference frame, local to its semantic parent; reference_pose copied):

- boy_reluctant_shrug: the shared gest_shrug (pipeline/clips/make_emotion_clips.py) reduced to the right arm and
  chest at SHRUG_SCALE of its swing (slerp from its rest frame), and re-timed for the boy: a slow, reluctant rise
  (RISE_F), a short dwell (HOLD_F) and a quicker fall (FALL_F), as the guide's sigh "shoulders rise 2-3 f slower than they fall"
  (docs/characters/boy_yellow_hoodie/REFERENCE_BEHAVIOUR.md section 7, extrapolation: no shrug is shown). The head
  and neck are not in the mask, so the reaction's head lift (boy_head_lift) stays while he shrugs. The rest frame is
  idle_relaxed frame 0 for the masked roles, so the layer blends in from the base pose without a pop.
- boy_head_lift: the posture of the boy_interested emotion: a small head lift with a counter-clockwise roll
  (T-106 WT [60, 81): upper face 58 px left, 29 px up, about 5 deg counter-clockwise; held [87, 121) with < 1 px net
  motion). A two-frame held posture like the shared emo_* clips; the emotion's onset / release time the move.
"""
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLIPS = os.path.join(ROOT, "content", "clips")

SHRUG_SCALE = 0.45  # share of gest_shrug's swing: energy.gesture_amplitude 0.3 (small, low energy)
# frames@24: rest, slow reluctant rise, short dwell, quicker fall. The reaction planner (T-097D) starts the gesture with
# the emotion at the notice frame; the reluctant beat (the head lift rises 21 f and settles 10 f first, T-106 WT [60, 81))
# is the clip's rest lead: 31 f + 2 rest frames, so the arm leaves rest about 33 f after he notices
LEAD_F, RISE_F, HOLD_F, FALL_F = 33, 30, 10, 8
TAIL_F = 14  # rest frames after the fall: the layer's blend-out (no explicit end) happens over rest, not over the fall
SRC_PEAK, SRC_HOLD_END = 23, 38  # gest_shrug frames (30 fps): its rise ends f23, its peak dwell ends f38 (end f51)
SHRUG_ROLES = ["chest", "upperArm.R", "forearm.R", "hand.R"]
# degrees about the role's x / z axes at intensity 1; the boy expresses boy_interested at about 0.42 (event 0.7 x
# reaction.intensity_scale 0.6), which gives about -2.5 / -3.8 / -5 deg, the T-106 lift and roll
LIFT_NECK_PITCH, LIFT_HEAD_PITCH, LIFT_HEAD_ROLL = -6.0, -9.0, -12.0


def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return [aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw]


def qinv(q):
    return [q[0], -q[1], -q[2], -q[3]]


def norm(q):
    n = math.sqrt(sum(x * x for x in q))
    return [x / n for x in q]


def slerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = [-x for x in b], -d
    if d > 0.9995:
        return norm([x + t * (y - x) for x, y in zip(a, b)])
    th = math.acos(d)
    s0, s1 = math.sin((1 - t) * th) / math.sin(th), math.sin(t * th) / math.sin(th)
    return norm([s0 * x + s1 * y for x, y in zip(a, b)])


def scale_from(rest, q, k):
    """rest rotated by k of the way to q (the deviation rest^-1 q scaled by k)."""
    return slerp(rest, q, k)


def sample(keys, f):
    """Track value at frame f (slerp between the neighbouring keys; keys = [frame, w, x, y, z])."""
    if f <= keys[0][0]:
        return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= f <= b[0]:
            t = (f - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
            return slerp(a[1:], b[1:], t)
    return keys[-1][1:]


def rot(axis, deg):
    h = math.radians(deg) / 2
    return [math.cos(h)] + [c * math.sin(h) for c in axis]


def r7(q):
    return [round(x, 7) for x in q]


def header(src, name, frame_count, desc, mask):
    return {"format": "plush.clip", "version": 1, "name": name, "fps": 24.0, "frame_count": frame_count, "loop": False,
            "source": "script", "license": "project",
            "attribution": "Plush Studio project (script-made from library clips, episodes/e908_boy_acting/make_clips.py, T-097-boy)",
            "description": desc, "mask": mask, "mirror": {"suffix": [".L", ".R"], "axis": "x", "note": "mirrorable"},
            "contacts": [], "reference_pose": src["reference_pose"]}


def shrug():
    src = json.load(open(os.path.join(CLIPS, "gest_shrug.clip.json")))
    idle = json.load(open(os.path.join(CLIPS, "idle_relaxed.clip.json")))
    sfps, last = src["fps"], src["frame_count"] - 1
    n = LEAD_F + RISE_F + HOLD_F + FALL_F + TAIL_F + 1
    tracks = {}
    for role in SHRUG_ROLES:
        sk = src["tracks"][role]["keys"]
        rest_src, rest = sk[0][1:], idle["tracks"][role]["keys"][0][1:]
        keys = []
        for f in range(n):
            if f <= LEAD_F:
                sf = 0.0
            elif f <= LEAD_F + RISE_F:  # rise: RISE_F frames cover gest_shrug f0..SRC_PEAK
                sf = (f - LEAD_F) / RISE_F * SRC_PEAK
            elif f <= LEAD_F + RISE_F + HOLD_F:  # dwell: SRC_PEAK..SRC_HOLD_END
                sf = SRC_PEAK + (f - LEAD_F - RISE_F) / HOLD_F * (SRC_HOLD_END - SRC_PEAK)
            else:  # fall: FALL_F frames cover SRC_HOLD_END..end, then the rest tail
                sf = min(last, SRC_HOLD_END + (f - LEAD_F - RISE_F - HOLD_F) / FALL_F * (last - SRC_HOLD_END))
            q = sample(sk, sf)
            dev = qmul(qinv(rest_src), q)  # gest_shrug's own deviation from its rest, applied to the idle rest
            keys.append(qmul(rest, scale_from([1, 0, 0, 0], dev, SHRUG_SCALE)))
        # [1, 2, 1] / 4 smoothing (twice): resampling the 30 fps source keys at 24 fps leaves a frame-to-frame
        # alternation of the speed; the ends stay at rest
        for _ in range(2):
            keys = [keys[0]] + [norm([(a + 2 * b + c) / 4 for a, b, c in zip(keys[i - 1], keys[i], keys[i + 1])])
                                for i in range(1, n - 1)] + [keys[-1]]
        tracks[role] = {"keys": [[f] + r7(q) for f, q in enumerate(keys)]}
    # face accent (T-046 channels): a flat, unimpressed mouth with the shoulder, no brow raise (heavy-lidded)
    peak, fall0 = LEAD_F + RISE_F, LEAD_F + RISE_F + HOLD_F
    face = {"note": "T-046 facial layer channels (clip frames): mouth corners down a little with the shoulder (unimpressed); "
                    "brows stay low (no browUp: the shared shrug's surprise brows do not fit him, REFERENCE_BEHAVIOUR.md section 2)",
            "tracks": {"mouthDown": [[0, 0.0], [LEAD_F + 4, 0.03], [peak, 0.22], [fall0, 0.2], [fall0 + FALL_F, 0.0], [n - 1, 0.0]],
                       "browDown": [[0, 0.0], [peak, 0.12], [fall0, 0.12], [fall0 + FALL_F, 0.0], [n - 1, 0.0]]}}
    out = header(src, "boy_reluctant_shrug", n,
                 f"Boy: reluctant one-sided shrug (right arm, palm turns up a little): gest_shrug at {SHRUG_SCALE:g} of its "
                 f"swing, slow rise {RISE_F} f, {HOLD_F} f dwell, quicker fall {FALL_F} f (T-097-boy)", SHRUG_ROLES)
    out["face"] = face
    out["x_rest_tail_frames"] = TAIL_F  # motion ends this many frames before the clip end (make_shot.py end hold)
    out["tracks"] = tracks
    return out


def head_lift():
    src = json.load(open(os.path.join(CLIPS, "emo_curious.clip.json")))
    idle = json.load(open(os.path.join(CLIPS, "idle_relaxed.clip.json")))
    neck = qmul(idle["tracks"]["neck"]["keys"][0][1:], rot([1, 0, 0], LIFT_NECK_PITCH))
    head = qmul(idle["tracks"]["head"]["keys"][0][1:], qmul(rot([0, 0, 1], LIFT_HEAD_ROLL), rot([1, 0, 0], LIFT_HEAD_PITCH)))
    out = header(src, "boy_head_lift", 2,
                 "Boy: posture of boy_interested: head lifts a little with a small counter-clockwise roll (T-106 WT [60, 81)), "
                 "held", ["neck", "head"])
    out["tracks"] = {"neck": {"keys": [[0] + r7(neck), [1] + r7(neck)]}, "head": {"keys": [[0] + r7(head), [1] + r7(head)]}}
    return out


def main():
    for clip in (shrug(), head_lift()):
        path = os.path.join(CLIPS, clip["name"] + ".clip.json")
        with open(path, "w") as f:
            json.dump(clip, f, indent=1)
            f.write("\n")
        print("wrote", os.path.relpath(path, ROOT), clip["frame_count"], "frames")


if __name__ == "__main__":
    main()
