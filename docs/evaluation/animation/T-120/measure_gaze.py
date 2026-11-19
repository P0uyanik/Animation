"""T-120 evidence: head and eye angles of a run_shot bake (not part of the pipeline).

    python3 docs/evaluation/animation/T-120/measure_gaze.py [--out gaze_angles.json]

Reads build/bake.json of the two e911 shots and reports, per character: the largest eye travel relative to the head
(yaw / pitch, degrees, over all frames and both eyes) and, at the strip's frames, the head's world yaw / pitch and
each eye's yaw / pitch relative to the head (yaw + = the character's left, pitch + = up).
"""
import argparse
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SHOTS = os.path.join(ROOT, "episodes", "e911_gaze_check", "shots")
FRAMES = [18, 24, 36, 48, 54, 58]


def rotation(skin, index):
    m = skin[index * 16:index * 16 + 16]  # column-major 4x4
    cols = [m[0:3], m[4:7], m[8:11]]
    return [[c / math.sqrt(sum(x * x for x in col)) for c in col] for col in cols]


def angles(d):
    return math.degrees(math.atan2(d[0], d[2])), math.degrees(math.atan2(d[1], math.hypot(d[0], d[2])))


def measure(shot):
    bake = json.load(open(os.path.join(SHOTS, shot, "build", "bake.json")))
    out = {}
    for c in bake["characters"]:
        bones = c["bones"]
        head, eyes = bones.index("head"), [bones.index("eye.L"), bones.index("eye.R")]
        worst, rows = [0.0, 0.0], {}
        for fd in bake["frame_data"]:
            skin = fd["characters"][c["name"]]["skin"]
            h = rotation(skin, head)
            rel = []
            for e in eyes:
                z = rotation(skin, e)[2]
                a = angles([sum(h[k][i] * z[i] for i in range(3)) for k in range(3)])
                worst = [max(worst[0], abs(a[0])), max(worst[1], abs(a[1]))]
                rel.append([round(a[0], 1), round(a[1], 1)])
            if fd["frame"] in FRAMES:
                hy, hp = angles(h[2])
                rows["f%d" % fd["frame"]] = {"head_world_yaw_pitch": [round(hy, 1), round(hp, 1)], "eye_L": rel[0], "eye_R": rel[1]}
        out[c["name"]] = {"max_eye_travel_yaw_pitch": [round(worst[0], 2), round(worst[1], 2)], "frames": rows}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "gaze_angles.json"))
    a = ap.parse_args()
    result = {"gaze_range_deg": [16, 8], "default": measure("s010_default"), "gazeLegibility": measure("s010_legible")}
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=1)
        f.write("\n")
    for k in ("default", "gazeLegibility"):
        print(k, {who: v["max_eye_travel_yaw_pitch"] for who, v in result[k].items()})
