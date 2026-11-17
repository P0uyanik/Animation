#!/usr/bin/env python3
"""T-045: body-mechanics channel curves from the engine bakes of the two evidence shots (needs matplotlib).

    python plot_curves.py <before bake.json> <after bake.json> <out image> [<summary.json>]

Per character (character space, degrees / millimetres): clavicle rotation relative to the chest (both sides), chest
lean / twist / side bend relative to the character, head pitch, pelvis lateral shift, right shoulder pivot height
and both knee bends. Dashed = body mechanics off (before), solid = on (after)."""
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load(path):
    bake = json.load(open(path))
    root = os.path.dirname(os.path.abspath(path))
    out = {}
    scene = json.load(open(bake["scene_path"])) if os.path.exists(bake.get("scene_path", "")) else None
    for ch in bake["characters"]:
        name, bones = ch["name"], ch["bones"]
        pkg = ch["package"] if os.path.isabs(ch["package"]) else os.path.join(root, ch["package"])
        pj = json.load(open(pkg if pkg.endswith(".json") else os.path.join(pkg, "character.json")))
        heads = {b["name"]: np.array(b["head"]) for b in pj["skeleton"]}
        yaw = 0.0
        if scene:
            yaw = next(c.get("yawDeg", 0) for c in scene["characters"] if c["name"] == name)
        cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        to_char = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])  # inverse of the yaw rotation
        series = {k: [] for k in ("frame", "clavL", "clavR", "lean", "twist", "side", "headPitch", "pelvisX", "shoulderY",
                                  "kneeL", "kneeR")}
        for fd in bake["frame_data"]:
            sk = fd["characters"][name]["skin"]

            def M(b):
                i = bones.index(b)
                return np.array(sk[16 * i:16 * i + 16]).reshape(4, 4).T  # column-major

            def R(b):
                return to_char @ M(b)[:3, :3]

            def P(b):
                m = M(b)
                return to_char @ (m[:3, :3] @ heads[b] + m[:3, 3])

            def ang(Ra, Rb):
                c = (np.trace(Ra.T @ Rb) - 1) / 2
                return math.degrees(math.acos(max(-1.0, min(1.0, c))))

            series["frame"].append(fd["frame"])
            for s in "LR":
                cl = f"DEF-shoulder.{s}"
                series["clav" + s].append(ang(R("chest"), R(cl)) if cl in bones else 0.0)
            up, fw = R("chest")[:, 1], R("chest")[:, 2]
            series["lean"].append(math.degrees(math.atan2(up[2], up[1])))
            series["side"].append(math.degrees(math.atan2(-up[0], up[1])))
            series["twist"].append(math.degrees(math.atan2(fw[0], fw[2])))
            hf = R("head")[:, 2]
            series["headPitch"].append(math.degrees(math.asin(max(-1, min(1, -hf[1])))))
            series["pelvisX"].append(1000 * P("hips")[0])
            series["shoulderY"].append(1000 * P("upperArm.R")[1])
            for s in "LR":
                a, b, c = P(f"thigh.{s}"), P(f"shin.{s}"), P(f"foot.{s}")
                u, v = (b - a) / np.linalg.norm(b - a), (c - b) / np.linalg.norm(c - b)
                series["knee" + s].append(math.degrees(math.acos(max(-1.0, min(1.0, float(u @ v))))))
        for k in ("pelvisX", "shoulderY"):  # relative to the first frame of the before/after pair (set below)
            series[k] = np.array(series[k])
        out[name] = series
    return out


def main():
    before, after = load(sys.argv[1]), load(sys.argv[2])
    names = list(after)
    panels = [("clavicle vs chest (deg)", [("clavR", "R"), ("clavL", "L")]),
              ("chest vs character (deg)", [("lean", "lean fwd"), ("twist", "twist"), ("side", "side bend")]),
              ("pelvis x / R shoulder y (mm, rel. frame 1 off)", [("pelvisX", "pelvis x"), ("shoulderY", "R shoulder y")]),
              ("knee bend (deg) / head pitch (deg)", [("kneeL", "knee L"), ("kneeR", "knee R"), ("headPitch", "head pitch")])]
    fig, axes = plt.subplots(len(names), len(panels), figsize=(20, 4.2 * len(names)), sharex=True)
    summary = {}
    for r, n in enumerate(names):
        b, a = before[n], after[n]
        ref = {k: b[k][0] for k in ("pelvisX", "shoulderY")}
        summary[n] = {}
        for c, (title, keys) in enumerate(panels):
            ax = axes[r][c]
            for i, (k, label) in enumerate(keys):
                col = f"C{i}"
                yb = np.array(b[k]) - ref.get(k, 0)
                ya = np.array(a[k]) - ref.get(k, 0)
                ax.plot(b["frame"], yb, "--", color=col, lw=1.0, alpha=0.7)
                ax.plot(a["frame"], ya, "-", color=col, lw=1.6, label=label)
                summary[n][k] = {"before_range": [round(float(yb.min()), 2), round(float(yb.max()), 2)],
                                 "after_range": [round(float(ya.min()), 2), round(float(ya.max()), 2)]}
            for f0, f1, lab in ((24, 62, "touch"), (66, 114, "wave")):
                ax.axvspan(f0, f1, color="0.92", zorder=0)
            ax.set_title(f"{n}: {title}", fontsize=10)
            ax.legend(fontsize=7, loc="upper left")
            ax.grid(alpha=0.3)
    for ax in axes[-1]:
        ax.set_xlabel("frame (24 fps); shaded: touch 24-62, wave 66-114; dashed = before (off), solid = after (on)")
    fig.tight_layout()
    fig.savefig(sys.argv[3], dpi=80)
    if len(sys.argv) > 4:
        json.dump(summary, open(sys.argv[4], "w"), indent=1)


if __name__ == "__main__":
    main()
