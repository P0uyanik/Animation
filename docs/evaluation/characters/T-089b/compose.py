"""T-089b: lays face_strip.py renders out as a labelled grid (rows = state, columns = column x view). Plain Python + PIL.

    python3 compose.py <strip_out_dir> <out.jpg> [--title TEXT]"""
import json
import os
import sys

from PIL import Image, ImageDraw

d, dst = sys.argv[1], sys.argv[2]
title = sys.argv[sys.argv.index("--title") + 1] if "--title" in sys.argv else ""
res = json.load(open(os.path.join(d, "strip_result.json")))
job = res["job"]
cols = [(c["tag"], v) for c in job["columns"] for v in job.get("views", {"front": 0, "threequarter": -35})]
states = job.get("states", ["neutral"])
tiles = {(t, v, s): Image.open(os.path.join(d, t, f"{s}_{v}.png")).convert("RGB") for t, v in cols for s in states}
w, h = next(iter(tiles.values())).size
lw, th = 90, 22 + (20 if title else 0)
im = Image.new("RGB", (lw + w * len(cols), th + h * len(states)), (28, 28, 28))
dr = ImageDraw.Draw(im)
if title:
    dr.text((6, 4), title, fill=(235, 235, 235))
for i, (t, v) in enumerate(cols):
    dr.text((lw + i * w + 6, th - 16), f"{t} {v}", fill=(235, 235, 235))
for j, s in enumerate(states):
    dr.text((6, th + j * h + h // 2), s, fill=(235, 235, 235))
    for i, (t, v) in enumerate(cols):
        im.paste(tiles[(t, v, s)], (lw + i * w, th + j * h))
im.save(dst, quality=90)
print(dst, im.size)
