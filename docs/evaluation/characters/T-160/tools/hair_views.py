#!/usr/bin/env python3
"""T-160 hair views: front, 3/4 and back of the hair of one or more built masters, same cameras for every column.

    python3 docs/evaluation/characters/T-160/tools/hair_views.py --char <boy|girl|third> --out <dir>
        --col <tag>=<master.blend> [--col ...] [--samples 16] [--px 600] [--views front,threequarter,back]

Calls the unchanged shared render side (tools/review/blender_render.py: fixed cameras, character_neutral/1 light).
Writes <out>/<tag>/<view>.png and <out>/hair_views.jpg (rows = columns, never scaled: every pixel as rendered)."""
import argparse
import json
import os
import subprocess
import sys
import time

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
# framing per character: target, frame height (m), aspect (w/h)
FRAME = {"boy": {"target": [0.0, 0.0, 0.86], "frame_height_m": 0.46, "aspect": 1.0},
         "girl": {"target": [0.0, 0.0, 0.76], "frame_height_m": 0.66, "aspect": 0.9},
         "third": {"target": [0.0, 0.0, 0.70], "frame_height_m": 0.70, "aspect": 0.9}}
VIEWS = {"front": (0.0, 5.0), "threequarter": (-35.0, 8.0), "side": (90.0, 5.0), "back": (180.0, 8.0),
         "back_high": (180.0, 40.0), "top_front": (0.0, 35.0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--char", required=True, choices=sorted(FRAME))
    ap.add_argument("--out", required=True)
    ap.add_argument("--col", action="append", required=True)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--px", type=int, default=600)
    ap.add_argument("--views", default="front,threequarter,back")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    names = a.views.split(",")
    views = [dict(FRAME[a.char], name=n, yaw_deg=VIEWS[n][0], elevation_deg=VIEWS[n][1]) for n in names]
    cols = [{"tag": c.split("=", 1)[0], "blend": os.path.abspath(c.split("=", 1)[1]), "comparison_pose": None}
            for c in a.col]
    job = {"out": out, "engine": "cycles", "samples": a.samples, "px": a.px, "lens_mm": 70.0, "sensor_mm": 36.0,
           "calibration": "character_neutral/1", "columns": cols, "views": views}
    jp = os.path.join(out, "job.json")
    json.dump(job, open(jp, "w"), indent=1)
    t = time.time()
    with open(os.path.join(out, "render_log.txt"), "w") as f:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup",
                        "-P", os.path.join(ROOT, "tools", "review", "blender_render.py"), "--", jp],
                       stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, check=True)
    secs = round(time.time() - t, 1)
    tiles = [[Image.open(os.path.join(out, c["tag"], n + ".png")).convert("RGB") for n in names] for c in cols]
    w, h = tiles[0][0].size
    sheet = Image.new("RGB", (w * len(names), (h + 18) * len(cols)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for r, c in enumerate(cols):
        d.text((4, r * (h + 18) + 3), f"{c['tag']}  ({a.char}; {', '.join(names)}; Cycles {a.samples} spp, 100%)",
               fill=(0, 0, 0))
        for k, im in enumerate(tiles[r]):
            sheet.paste(im, (k * w, r * (h + 18) + 18))
    sheet.save(os.path.join(out, "hair_views.jpg"), quality=92)
    json.dump({"render_s": secs, "samples": a.samples, "px": a.px, "views": names,
               "columns": [c["tag"] for c in cols]}, open(os.path.join(out, "hair_views.json"), "w"), indent=1)
    print("render_s", secs, os.path.join(out, "hair_views.jpg"))


if __name__ == "__main__":
    main()
