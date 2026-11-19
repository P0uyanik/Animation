#!/usr/bin/env python3
"""Measures the girl's gesture contact points in a bake (T-097-girl evidence; read-only use of tools/animcheck).

    python3 episodes/e908_girl_acting/measure_girl.py --bake <bake.json> [--character girl] [--frames A-B] [--json out]

Per frame: the distance from her right hand's knuckle point (f2a.R head, the hand role's end) to her chin (a rest-frame point under the 0.11.0
face, carried by the head bone), the pointing direction of the index (f3a.R -> f3b.R, degrees below horizontal), the
head pitch and the wrist speed (mm/frame). The chin-hold and point-hold windows of the e908 shot are summarised
(mean / max chin distance, mean pointing angle, still frames)."""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "animcheck"))
import animcheck  # noqa: E402

CHIN = [0.0, 0.672, 0.092]  # girl 0.11.0 rest frame: just under the chin, on the midline (mesh profile, T-097-girl)


def measure(bake, who="girl"):
    entry = next(c for c in bake["characters"] if c["name"] == who)
    ch = animcheck.Character(entry)
    rows, prev = [], None
    for fd in bake["frame_data"]:
        kn, wr = ch.position(fd, "f2a.R"), ch.position(fd, "hand.R")
        ia, tip = ch.position(fd, "f3a.R"), ch.position(fd, "f3b.R")
        hm = ch.matrix(fd, "head")
        chin = animcheck.pivot(hm, CHIN)
        d = animcheck.vsub(tip, ia)
        ang = math.degrees(math.asin(max(-1.0, min(1.0, -d[1] / max(1e-9, animcheck.vlen(d))))))
        hp = animcheck.pivot(hm, [0.0, 0.69, 0.1])
        h0 = animcheck.pivot(hm, [0.0, 0.69, 0.0])
        pitch = math.degrees(math.atan2(-(hp[1] - h0[1]), hp[2] - h0[2]))
        speed = 0.0 if prev is None else animcheck.vlen(animcheck.vsub(wr, prev)) * 1000
        prev = wr
        rows.append({"frame": fd["frame"], "chin_mm": round(animcheck.vlen(animcheck.vsub(kn, chin)) * 1000, 1),
                     "index_down_deg": round(ang, 1), "head_pitch_deg": round(pitch, 1), "wrist_mm_per_f": round(speed, 2),
                     "fingertip_y": round(tip[1], 4)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", required=True)
    ap.add_argument("--character", default="girl")
    ap.add_argument("--frames", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    rows = measure(json.loads(Path(a.bake).read_text()), a.character)
    if a.frames:
        lo, hi = (int(x) for x in a.frames.split("-"))
        rows = [r for r in rows if lo <= r["frame"] <= hi]
    for r in rows:
        print(r)
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
