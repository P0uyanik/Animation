#!/usr/bin/env python3
"""T-141 render driver: the same views of several .blend variants through the unchanged shared review renderer
(tools/review/blender_render.py, fixed cameras, character_neutral/1 light).

    python3 docs/evaluation/characters/T-141/tools/shots.py --out <dir> --views <views.json key> \
        --samples 16 --px 600 tag=<a.blend> [tag=<b.blend> ...]
Writes <out>/<tag>/<view>.png, <out>/times.json (seconds per variant, whole Blender run) and <out>/strip.jpg
(rows = variants, columns = views, every pixel as rendered)."""
import argparse
import json
import os
import subprocess
import sys
import time

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--views", required=True, help="key in views.json")
    ap.add_argument("--only", nargs="*", help="view names to keep")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--px", type=int, default=600)
    ap.add_argument("variants", nargs="+")
    a = ap.parse_args()
    views = json.load(open(os.path.join(HERE, "views.json")))[a.views]
    if a.only:
        views = [v for v in views if v["name"] in a.only]
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    times = {}
    for item in a.variants:
        tag, blend = item.split("=", 1)
        job = {"out": out, "engine": "cycles", "samples": a.samples, "px": a.px, "lens_mm": 70.0, "sensor_mm": 36.0,
               "calibration": "character_neutral/1",
               "columns": [{"tag": tag, "blend": os.path.abspath(blend), "comparison_pose": None}], "views": views}
        jp = os.path.join(out, f"job_{tag}.json")
        json.dump(job, open(jp, "w"), indent=1)
        t = time.time()
        with open(os.path.join(out, f"render_{tag}.log"), "w") as f:
            subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup",
                            "-P", os.path.join(ROOT, "tools", "review", "blender_render.py"), "--", jp],
                           stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, check=True)
        times[tag] = round(time.time() - t, 1)
        print(tag, times[tag], "s", flush=True)
    tags = [v.split("=", 1)[0] for v in a.variants]
    ims = [[Image.open(os.path.join(out, t, v["name"] + ".png")).convert("RGB") for v in views] for t in tags]
    w, h = sum(i.width for i in ims[0]), ims[0][0].height
    strip = Image.new("RGB", (w, (h + 18) * len(tags)), (30, 30, 32))
    d = ImageDraw.Draw(strip)
    for r, row in enumerate(ims):
        d.text((4, r * (h + 18) + 3), f"{tags[r]}  ({a.samples} spp, {a.px} px, {times[tags[r]]} s)", fill=(235, 235, 235))
        x = 0
        for im in row:
            strip.paste(im, (x, r * (h + 18) + 18))
            x += im.width
    strip.save(os.path.join(out, "strip.jpg"), quality=92)
    json.dump({"samples": a.samples, "px": a.px, "views": [v["name"] for v in views], "seconds": times},
              open(os.path.join(out, "times.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
