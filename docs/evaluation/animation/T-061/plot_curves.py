#!/usr/bin/env python3
"""T-061 evidence plots from two engine bakes of the evidence shot (before: animPrinciples false, after: default).

    python3 plot_curves.py --before before.bake.json --after after.bake.json [--scene shot_after/shot.scene.json]

Writes speed_profiles.png (wrist speed per frame for every gesture), wrist_paths.png (the wrist path as the camera
sees it, one dot per frame: the dot spacing is the spacing an animator reads; and from the side) and
curves_summary.json (the animcheck report of both). Needs matplotlib.
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "tools" / "animcheck"))
import animcheck  # noqa: E402

BEFORE, AFTER = "#9a9a9a", "#d9480f"


def report(bake_path, scene_path):
    bake = json.loads(Path(bake_path).read_text())
    scene = json.loads(Path(scene_path).read_text())
    return bake, animcheck.analyse(bake, scene, Path(scene_path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--scene", default=str(HERE / "shot_after" / "shot.scene.json"))
    a = ap.parse_args()
    bb, rb = report(a.before, a.scene)
    ba, ra = report(a.after, a.scene)
    n = len(ra["gestures"])

    fig, axs = plt.subplots(n, 1, figsize=(9, 2.3 * n), sharex=False)
    for i in range(n):
        for r, col, lab in ((rb, BEFORE, "before"), (ra, AFTER, "after")):
            g = r["gestures"][i]
            x = list(range(g["window"][0], g["window"][0] + len(g["speed_mm_per_frame"])))
            axs[i].plot(x, g["speed_mm_per_frame"], color=col, marker="o", ms=2.5, lw=1.4, label=lab)
        axs[i].set_title(ra["gestures"][i]["label"] + " — wrist speed (mm / frame, 24 fps)", fontsize=9)
        axs[i].grid(alpha=0.3)
        axs[i].legend(fontsize=8, loc="upper right")
    axs[-1].set_xlabel("frame")
    fig.tight_layout()
    fig.savefig(HERE / "speed_profiles.png", dpi=110)

    fig, axs = plt.subplots(2, n, figsize=(3.3 * n, 6.4))
    frames = {fd["frame"]: fd for fd in ba["frame_data"]}
    for i in range(n):
        for r, col, lab in ((rb, BEFORE, "before"), (ra, AFTER, "after")):
            g = r["gestures"][i]
            e = g["entry"]
            w0 = g["window"][0]
            lo, hi = e["frames"][0] - w0, e["frames"][1] - w0 + 1
            if "exit" in g:
                hi = max(hi, g["exit"]["frames"][1] - w0 + 1)
            pts = g["wrist"][lo:hi]
            scr = [animcheck.project(frames[w0 + lo + k]["camera"], p) for k, p in enumerate(pts)]
            axs[0, i].plot([s[0] for s in scr], [s[1] for s in scr], color=col, marker="o", ms=2.5, lw=1, label=lab)
            axs[1, i].plot([p[2] for p in pts], [p[1] for p in pts], color=col, marker="o", ms=2.5, lw=1, label=lab)
        axs[0, i].set_title(ra["gestures"][i]["label"] + "\ncamera view (entry + hold + exit)", fontsize=8)
        axs[1, i].set_title("side view (z forward, y up), m", fontsize=8)
        for ax in axs[:, i]:
            ax.set_aspect("equal", adjustable="datalim")
            ax.grid(alpha=0.3)
            ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(HERE / "wrist_paths.png", dpi=110)

    def strip(r):
        out = []
        for g in r["gestures"]:
            g = {k: v for k, v in g.items() if k not in ("wrist",)}
            out.append(g)
        return out

    thresholds = json.loads((HERE.parents[3] / "tools/animcheck/thresholds.json").read_text())
    summary = {"before": strip(rb), "after": strip(ra),
               "failures_before": animcheck.check(rb, thresholds), "failures_after": animcheck.check(ra, thresholds)}
    (HERE / "curves_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print("wrote speed_profiles.png, wrist_paths.png, curves_summary.json")
    print("failures before:", len(summary["failures_before"]), "after:", len(summary["failures_after"]))


if __name__ == "__main__":
    main()
