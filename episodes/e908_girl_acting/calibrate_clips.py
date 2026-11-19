#!/usr/bin/env python3
"""Closed-loop calibration of the girl's clip targets on her own bake (T-097-girl).

    python3 episodes/e908_girl_acting/calibrate_clips.py --bake <e908 bake.json> --scene <e908 shot.scene.json>

The clip poses are solved on her rest proportions (girl_arm_ik.py), but at playback the engine's arm-body clearance,
the gaze head pitch and the emotion postures move the hand and the chin. This reads the e908 bake and corrects the
solver targets of make_girl_clips.py (clip_calibration.json, left-side definition, chest frame):
- chin hold (x_t097_girl.beats chin .. leave_chin): the hand's knuckle point (f2a.R) should sit UNDER mm under her
  chin (the chin point carried by the head bone), measured in the chest frame;
- point hold (point .. point_hold_end): the index (f3a.R -> f3b.R) should aim at the cup's top.
Each run moves the targets by the mean error (mirrored to the left definition) and records it; re-make the clips,
re-bake, repeat until the errors are small (the README lists the iterations)."""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "animcheck"))
import animcheck  # noqa: E402

CHIN = [0.0, 0.672, 0.092]  # rest frame, under the 0.11.0 chin (measure_girl.CHIN)
UNDER = [-0.006, -0.012, 0.004]  # knuckle relative to the chin point: a little to her right, under it, in front
CUP_TOP = 0.05  # felt cup height (content/assets/felt_cup.asset.json)


def inv_point(m, p):
    """Rest-frame point whose skinning-matrix image is p (m column-major, rigid)."""
    t = [p[i] - m[12 + i] for i in range(3)]
    cols = [m[0:3], m[4:7], m[8:11]]  # rotation columns
    return [sum(cols[j][i] * t[i] for i in range(3)) for j in range(3)]  # R^T t


def inv_dir(m, d):
    cols = [m[0:3], m[4:7], m[8:11]]
    return [sum(cols[j][i] * d[i] for i in range(3)) for j in range(3)]


def norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--out", default=str(HERE / "clip_calibration.json"))
    ap.add_argument("--gain", type=float, default=1.0)
    ap.add_argument("--place-cup", action="store_true",
                    help="measure only; place the cup where the held index ray meets the table top (staging)")
    a = ap.parse_args()
    bake, scene = json.loads(Path(a.bake).read_text()), json.loads(Path(a.scene).read_text())
    beats = scene["x_t097_girl"]["beats"]
    cup = next(p for p in scene["props"] if p["name"] == "cup")["transform"]["translation"]
    cup_top = [cup[0], cup[1] + CUP_TOP, cup[2]]
    ch = animcheck.Character(next(c for c in bake["characters"] if c["name"] == "girl"))
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    chin_err, chin_mm, dir_err, dir_deg = [0.0] * 3, [], [0.0] * 3, []
    cw = [f for f in frames if beats["chin"] + 2 <= f <= beats["leave_chin"] - 1]
    pw = [f for f in frames if beats["point"] + 3 <= f <= beats["point_hold_end"] - 1]
    for f in cw:
        fd = frames[f]
        cm = ch.matrix(fd, "chest")
        chin_l = inv_point(cm, animcheck.pivot(ch.matrix(fd, "head"), CHIN))
        want = [chin_l[i] + UNDER[i] for i in range(3)]
        kn = inv_point(cm, ch.position(fd, "f2a.R"))
        for i in range(3):
            chin_err[i] += (want[i] - kn[i]) / len(cw)
        chin_mm.append(1000 * math.dist(want, kn))
    for f in pw:
        fd = frames[f]
        cm = ch.matrix(fd, "chest")
        ia, tip = ch.position(fd, "f3a.R"), ch.position(fd, "f3b.R")
        want = norm(inv_dir(cm, [cup[i] - ia[i] for i in range(3)]))  # at the cup foot (where --place-cup puts it)
        got = norm(inv_dir(cm, [tip[i] - ia[i] for i in range(3)]))
        for i in range(3):
            dir_err[i] += (want[i] - got[i]) / len(pw)
        dir_deg.append(math.degrees(math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(want, got)))))))
    out = Path(a.out)
    cal = json.loads(out.read_text()) if out.is_file() else {
        "chin_target": [0.012, 0.672, 0.11], "point_dir": [0.0, -0.46, 0.88], "iterations": []}
    mirror = lambda v: [-v[0], v[1], v[2]]  # noqa: E731  right -> left definition
    ce, de = mirror(chin_err), mirror(dir_err)
    pd = norm(cal["point_dir"])
    cal["iterations"].append({"chin_mean_mm": round(sum(chin_mm) / len(chin_mm), 1), "chin_max_mm": round(max(chin_mm), 1),
                              "point_mean_deg": round(sum(dir_deg) / len(dir_deg), 1),
                              "point_max_deg": round(max(dir_deg), 1),
                              "chin_target_before": cal["chin_target"], "point_dir_before": cal["point_dir"]})
    if a.place_cup:  # the staging follows the pose: the cup goes where the held index ray meets the table top
        hits = []
        for f in pw:
            ia, tip = ch.position(frames[f], "f3a.R"), ch.position(frames[f], "f3b.R")
            d = norm([tip[i] - ia[i] for i in range(3)])
            t = (cup[1] - ia[1]) / d[1]  # the table top: she points down at the cup's foot
            hits.append([ia[0] + t * d[0], cup[1], ia[2] + t * d[2]])
        cal["cup"] = [round(sum(h[i] for h in hits) / len(hits), 4) for i in range(3)]
    else:
        cal["chin_target"] = [round(cal["chin_target"][i] + a.gain * ce[i], 4) for i in range(3)]
        cal["point_dir"] = [round(x, 4) for x in norm([pd[i] + a.gain * de[i] for i in range(3)])]
    cal["note"] = ("make_girl_clips.py solver targets (left-side definition, girl rest / chest frame), closed-loop "
                   "calibrated on the e908 bake by calibrate_clips.py; iterations = errors measured before each update")
    out.write_text(json.dumps(cal, indent=1) + "\n")
    print(json.dumps(cal["iterations"][-1]), "->", cal["chin_target"], cal["point_dir"])


if __name__ == "__main__":
    main()
