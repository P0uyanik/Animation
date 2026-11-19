"""T-134 reach measures from two bakes of the same shot (before / after), numpy only.

Interim measures until T-135's tools/motion_checks/reach lands. Per reach (character, hand bone, start, contact):
  wrist   speed profile of the wrist pivot (mm/frame): first / peak / last frame, where the peak is (fraction of the
          reach), largest speed change between frames (mm/f^2) over the reach and the 4 frames after the contact,
          arc = largest deviation of the path from its chord / chord length
  lead    how far the bones moved against the `before` bake along the horizontal reach direction (mm): the counter
          move before the start, the lead at the start, at 10 % of the wrist travel and its maximum; frame of the maximum
  after   overlap after the contact: largest head / chest offset against `before` and the frame it has settled (< 0.5 mm)
  feet    largest foot offset against `before` (mm)

Usage: python3 measure_reach.py --before <bake.json> --after <bake.json> --reach boy:hand.R:57:77 [--reach ...] [--out x.json]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "tools", "motion_checks"))
from shot import Shot  # noqa: E402


def pivots(shot, who):
    c = next(c for c in shot.characters if c.name == who)
    return c, c.pivots() * 1000.0  # mm


def wrist_measures(p, f0, start, contact):
    a, b = start - f0, contact - f0
    path = p[a:b + 1]
    v = np.linalg.norm(np.diff(path, axis=0), axis=1)
    chord = path[-1] - path[0]
    L = np.linalg.norm(chord)
    off = path - path[0]
    dev = np.linalg.norm(off - np.outer(off @ chord / (L * L), chord), axis=1)
    vv = np.linalg.norm(np.diff(p[a:b + 5], axis=0), axis=1)
    dv = np.linalg.norm(np.diff(np.diff(p[a - 1:b + 5], axis=0), axis=0), axis=1)
    return {
        "chord_mm": round(float(L), 1),
        "speed_first_mm_f": round(float(v[0]), 2),
        "speed_peak_mm_f": round(float(v.max()), 2),
        "speed_last_mm_f": round(float(v[-1]), 2),
        "first_over_peak": round(float(v[0] / v.max()), 3),
        "last_over_peak": round(float(v[-1] / v.max()), 3),
        "peak_at": round(float((np.argmax(v) + 0.5) / len(v)), 2),
        "speed_after_contact_mm_f": round(float(vv[len(v):].max()), 2),
        "max_speed_change_mm_f2": round(float(dv.max()), 2),
        "max_speed_change_frame": int(start - 1 + np.argmax(dv) + 1),
        "arc": round(float(dev.max() / L), 3),
        "speed_mm_f": [round(float(x), 1) for x in v],
    }


def measure(before, after, who, bone, start, contact):
    cb, pb = pivots(before, who)
    ca, pa = pivots(after, who)
    f0 = int(before.frames[0])
    i = cb.bones.index(bone)
    out = {"character": who, "bone": bone, "start": start, "contact": contact,
           "wrist_before": wrist_measures(pb[:, i], f0, start, contact),
           "wrist_after": wrist_measures(pa[:, i], f0, start, contact)}
    a, b = start - f0, contact - f0
    d = pb[b, i] - pb[a, i]
    d[1] = 0
    d /= np.linalg.norm(d)
    travel = np.linalg.norm(pa[a:b + 1, i] - pa[a, i], axis=1)
    tenth = a + int(np.argmax(travel >= 0.1 * travel[-1]))
    side = bone.split(".")[-1]
    lead = {}
    for name in ("hips", "chest", "upperArm." + side, "head"):
        if name not in cb.bones:
            continue
        k = cb.bones.index(name)
        s = (pa[:, k] - pb[:, k]) @ d
        full = float(s[a:b + 1].max())
        lead[name] = {
            "counter_mm": round(float(s[max(0, a - 12):a + 1].min()), 2),
            "at_start_mm": round(float(s[a]), 2),
            "at_wrist_10pct_mm": round(float(s[tenth]), 2),
            "max_mm": round(full, 2),
            "max_frame": int(f0 + a + np.argmax(s[a:b + 1])),
            "first_moves_frame": int(f0 + np.argmax(np.linalg.norm(pa[:, k] - pb[:, k], axis=1) > 0.2)),
        }
    out["wrist_10pct_frame"] = int(f0 + tenth)
    out["lead"] = lead
    after_c = {}
    for name in ("head", "chest"):
        if name not in cb.bones:
            continue
        k = cb.bones.index(name)
        off = np.linalg.norm(pa[:, k] - pb[:, k], axis=1)
        tail = off[b:]
        settled = np.nonzero(tail > 0.5)[0]
        after_c[name] = {"max_offset_after_contact_mm": round(float(tail.max()), 2),
                         "settled_frame": int(f0 + b + (settled[-1] + 1 if len(settled) else 0))}
    out["after"] = after_c
    feet = [cb.bones.index(n) for n in ("foot.L", "foot.R") if n in cb.bones]
    out["feet_max_offset_mm"] = round(float(np.linalg.norm(pa[:, feet] - pb[:, feet], axis=2).max()), 3) if feet else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--reach", action="append", required=True, help="character:bone:start:contact")
    ap.add_argument("--out")
    args = ap.parse_args()
    before, after = Shot(args.before), Shot(args.after)
    res = []
    for r in args.reach:
        who, bone, s, c = r.split(":")
        res.append(measure(before, after, who, bone, int(s), int(c)))
    doc = {"format": "plush.t134_reach_measures", "version": 1, "reaches": res}
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=1)
            f.write("\n")
    for m in res:
        print(f"{m['character']} {m['bone']} f{m['start']}-{m['contact']}  (wrist at 10 % of travel: f{m['wrist_10pct_frame']})")
        for k in ("wrist_before", "wrist_after"):
            w = m[k]
            print(f"  {k:13s} first/peak/last {w['speed_first_mm_f']}/{w['speed_peak_mm_f']}/{w['speed_last_mm_f']} mm/f  "
                  f"peak at {w['peak_at']}  after contact {w['speed_after_contact_mm_f']}  "
                  f"max dv {w['max_speed_change_mm_f2']} (f{w['max_speed_change_frame']})  arc {w['arc']}  chord {w['chord_mm']} mm")
            print("    ", w["speed_mm_f"])
        for n, l in m["lead"].items():
            print(f"  lead {n:10s} first moves f{l['first_moves_frame']}  counter {l['counter_mm']}  at start {l['at_start_mm']}  "
                  f"at wrist 10 % {l['at_wrist_10pct_mm']}  max {l['max_mm']} mm (f{l['max_frame']})")
        print("  after", m["after"], " feet", m["feet_max_offset_mm"])


if __name__ == "__main__":
    main()
