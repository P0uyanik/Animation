#!/usr/bin/env python3
"""T-190: hand close-ups of a shot bake (evidence renders for the before / after sheet).

    python3 docs/evaluation/interaction/T-190/closeup.py --bake <bake.json> --cast <build>/cast.json \
        --scan <measure_t190 output .jsonl[.gz]> --tiles <label>=<who>:<L|R>:<frame>:<view>,... --out <dir> \
        [--samples 16] [--res 400 300] [--blender <exe>]

Writes a copy of the bake holding only the tiles' frames (renumbered 1..n; poses, props and lights unchanged) with
the camera of each replaced by a close-up of that hand, renders it with pipeline/charsys/shot_render.py (one Blender
run) and saves <out>/<label>.png. The camera looks at the hand (wrist + 35 mm along the fingers, from the scan) from
0.22 m, 80 mm lens; views (hand axes from the scan: n palm normal, r thumb side, d fingers, y world up):
    radial  0.2 n + r + 0.2 y + 0.2 d      (the thumb side)
    tip     0.1 n + 0.5 r + 0.3 y + d      (from the fingertips)
    palm    n + 0.4 r + 0.2 y + 0.2 d
    back    -n + 0.3 r + 0.3 y
The same tiles on two bakes (before / after) give the two columns of tools/review/shot_sheet.py.
"""
import argparse
import gzip
import json
import math
import os
import shutil
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
VIEWS = {"radial": (0.2, 1.0, 0.2, 0.2), "tip": (0.1, 0.5, 0.3, 1.0), "palm": (1.0, 0.4, 0.2, 0.2), "back": (-1.0, 0.3, 0.3, 0.0)}


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def camera(row, view, distance=0.22):
    w, d, n = row["wrist"], row["finger_dir"], row["palm_normal"]
    r = cross(n, d)
    if row["side"] == "R":
        r = [-x for x in r]
    a, b, c, e = VIEWS[view]
    o = [a * n[i] + b * r[i] + c * (1.0 if i == 1 else 0.0) + e * d[i] for i in range(3)]
    k = distance / math.sqrt(sum(x * x for x in o))
    target = [w[i] + 0.035 * d[i] for i in range(3)]
    return [target[i] + k * o[i] for i in range(3)], target


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", required=True)
    ap.add_argument("--cast", required=True)
    ap.add_argument("--scan", required=True)
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--res", type=int, nargs=2, default=[400, 300])
    ap.add_argument("--blender", default="/usr/local/bin/blender")
    a = ap.parse_args()
    opener = gzip.open if a.scan.endswith(".gz") else open
    rows = {}
    with opener(a.scan, "rt") as f:
        for line in f:
            r = json.loads(line)
            rows[(r["who"], r["side"], r["frame"])] = r
    bake = json.load(open(a.bake))
    by = {fd["frame"]: fd for fd in bake["frame_data"]}
    sub, labels = [], []
    for k, tile in enumerate(a.tiles.split(","), 1):
        label, spec = tile.split("=")
        who, side, frame, view = spec.split(":")
        fd = dict(by[int(frame)])
        pos, target = camera(rows[(who, side, int(frame))], view)
        fd["camera"] = dict(fd["camera"], position=pos, target=target, focalMm=80.0, fStop=0.0, focusDistance=-1.0)
        fd["frame"] = k
        sub.append(fd)
        labels.append(label)
    bake["frame_data"], bake["frames"] = sub, [1, len(sub)]
    os.makedirs(a.out, exist_ok=True)
    work = os.path.join(a.out, "_work")
    os.makedirs(work, exist_ok=True)
    path = os.path.join(work, "bake.json")
    json.dump(bake, open(path, "w"))
    cmd = [a.blender, "-b", "--factory-startup", "-P", os.path.join(ROOT, "pipeline", "charsys", "shot_render.py"), "--",
           "--bake", path, "--cast", a.cast, "--out", os.path.join(work, "render"), "--profile", "review",
           "--samples", str(a.samples), "--resolution", str(a.res[0]), str(a.res[1])]
    with open(os.path.join(work, "render.txt"), "w") as log:
        subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT)
    for k, label in enumerate(labels, 1):
        shutil.copyfile(os.path.join(work, "render", f"frame_{k:04d}.png"), os.path.join(a.out, f"{label}.png"))
    json.dump({"bake": a.bake, "scan": a.scan, "tiles": a.tiles, "samples": a.samples, "res": a.res},
              open(os.path.join(a.out, "closeup.json"), "w"), indent=1)
    print(f"{len(labels)} tiles -> {a.out}")


if __name__ == "__main__":
    main()
