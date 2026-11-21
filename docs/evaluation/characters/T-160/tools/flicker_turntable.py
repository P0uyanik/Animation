#!/usr/bin/env python3
"""T-160 flicker check on a slow turntable (tools/motion_checks render passes and flicker measure, unchanged).

    python3 docs/evaluation/characters/T-160/tools/flicker_turntable.py --char <boy|girl|third> --out <dir>
        --col <tag>=<master.blend> [--col ...] [--frames 10] [--step 2.0] [--yaw 150] [--samples 16] [--px 480]

Per column: turntable_blend.py makes the turning scene, tools/motion_checks/render_passes.py renders it with the
flicker passes and motion vectors, flicker.measure / flicker.find (thresholds.json, not changed) give the temporal
noise and sign-flip share per region. Writes <out>/flicker.json and prints one line per column and region.
The thresholds were set on the shots' framing (640 x 360, T-125); here they are a yardstick, and the comparison
between the columns (same camera, frames, samples, seed) is the result."""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
MC = os.path.join(ROOT, "tools", "motion_checks")
sys.path.insert(0, MC)
sys.path.insert(0, HERE)
import flicker  # noqa: E402
import frames as FR  # noqa: E402
from hair_views import FRAME  # noqa: E402


def blender(script, args, log):
    with open(log, "a") as f:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup",
                        "-P", script, "--"] + [str(x) for x in args], stdout=f, stderr=subprocess.STDOUT, cwd=ROOT,
                       check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--char", required=True, choices=sorted(FRAME))
    ap.add_argument("--out", required=True)
    ap.add_argument("--col", action="append", required=True)
    ap.add_argument("--frames", type=int, default=10)
    ap.add_argument("--step", type=float, default=2.0)
    ap.add_argument("--yaw", type=float, default=150.0, help="start yaw of the character (0 = faces the camera)")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--px", type=int, default=480)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    thr = json.load(open(os.path.join(MC, "thresholds.json")))["flicker"]
    fr = FRAME[a.char]
    rep = {"character": a.char, "frames": a.frames, "deg_per_frame": a.step, "start_yaw_deg": a.yaw,
           "samples": a.samples, "px": [a.px, int(round(a.px * fr["aspect"]))], "framing": fr,
           "thresholds": {k: thr[k] for k in ("held_noise", "flip_share", "tile_flip_share")}, "columns": {}}
    for c in a.col:
        tag, blend = c.split("=", 1)
        d = os.path.join(out, tag)
        os.makedirs(d, exist_ok=True)
        log = os.path.join(d, "log.txt")
        tb = os.path.join(d, "turntable.blend")
        if not os.path.exists(tb):
            blender(os.path.join(HERE, "turntable_blend.py"),
                    [os.path.abspath(blend), tb, fr["target"][2], fr["frame_height_m"], fr["aspect"], a.px, a.frames,
                     a.step, a.yaw, a.samples], log)
        blender(os.path.join(MC, "render_passes.py"), ["--blend", tb, "--out", os.path.join(d, "passes")], log)
        frames, data = FR.load_dir(os.path.join(d, "passes"))
        meas = flicker.measure(frames, data, thr)
        issues, stats = flicker.find(frames, data, thr, meas=meas)
        rep["columns"][tag] = {"blend": os.path.relpath(os.path.abspath(blend), ROOT), "issues": issues, "stats": stats}
        for name in ("hair", "fibres"):
            s = stats.get(name)
            if s:
                print(f"{a.char} {tag} {name}: noise median {s.get('denoised_noise_median')} max "
                      f"{s.get('denoised_noise_max')} (limit {thr['held_noise'][name]}); flip share median "
                      f"{s['denoised_flip_share_median']} max {s['denoised_flip_share_max']} (limit "
                      f"{thr['flip_share'][name]}); tile max {s['tile_flip_share_max']} (limit "
                      f"{thr['tile_flip_share'][name]}); mc {s['motion_compensated']}; issues "
                      f"{sum(1 for i in issues if i['region'] == name)}")
        if os.path.exists(tb):
            os.remove(tb)  # large; rebuilt from the master on demand
    json.dump(rep, open(os.path.join(out, "flicker.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
