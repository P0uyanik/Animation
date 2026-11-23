#!/usr/bin/env python3
"""T-215 front difference overlay: release (before) vs proposal (after) outlines and T-204 trace points.

    python3 docs/evaluation/characters/T-215/diff.py <before measure dir> <after measure dir> <out.jpg>

Inputs are T-214 measurer output directories (`measurer.py measure`, keeping the view-*.npz arrays). Two panels:
neutral front (y+000) and the scored front reference view (ref-front, matched open smile). Each panel draws the
class-boundary outlines of the full Workbench pass (skin silhouette, eyes, mouth, brows, ears, glasses) for before
(cyan) and after (magenta) over the after pass in grey, plus the T-204 points (iris span, mouth box, chin, ear box)."""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

CLASSES = ("background", "skin", "lid", "lash", "eye_L", "eye_R", "brow", "ear", "mouth", "cavity", "glasses",
           "hair", "bun", "hair_acc", "other")
C = {n: i for i, n in enumerate(CLASSES)}
PARTS = {"head": ["skin", "lid", "lash", "eye_L", "eye_R", "brow", "ear", "mouth", "cavity"], "eyes": ["eye_L", "eye_R"],
         "mouth": ["mouth", "cavity"], "brow": ["brow"], "ear": ["ear"], "glasses": ["glasses"]}
CROP = (96, 140, 416, 460)  # px of the 512 px pass: the face and neck at the T-202 framing
K = 2.4


def font(n):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, n)
    return ImageFont.load_default()


def edges(mask):
    e = np.zeros_like(mask)
    e[:-1] |= mask[:-1] != mask[1:]
    e[:, :-1] |= mask[:, :-1] != mask[:, 1:]
    return e


def points(folder, name):
    r = json.load(open(os.path.join(folder, "measures.json")))
    return next(v["points"] for v in r["views"] if v["name"] == name)


def panel(before, after, name, title):
    fb = np.load(os.path.join(before, f"view-{name}.npz"))["full_cls"]
    fa = np.load(os.path.join(after, f"view-{name}.npz"))["full_cls"]
    x0, y0, x1, y1 = CROP
    grey = np.where(fa > 0, 70 + 12 * (fa % 6), 28).astype(np.uint8)[y0:y1, x0:x1]
    im = Image.fromarray(np.stack([grey] * 3, -1)).resize((int((x1 - x0) * K), int((y1 - y0) * K)),
                                                          Image.Resampling.NEAREST)
    rgb = np.asarray(im).copy()
    for cls, colour in ((fb, (0, 230, 255)), (fa, (255, 60, 220))):
        for part, names in PARTS.items():
            m = np.isin(cls, [C[n] for n in names])[y0:y1, x0:x1]
            big = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize(im.size, Image.Resampling.NEAREST)) > 0
            e = edges(big)
            rgb[e] = colour
    im = Image.fromarray(rgb)
    d = ImageDraw.Draw(im)
    s = 512 / 400

    def xy(p):
        return ((p[0] * s - x0) * K, (p[1] * s - y0) * K)
    for folder, colour in ((before, "#00e6ff"), (after, "#ff3cdc")):
        p = points(folder, name)
        if p.get("iris"):
            l, y, r = p["iris"]
            d.line([xy((l, y)), xy((r, y))], fill=colour, width=3)
        for key in ("mouth", "ear"):
            b = p.get(key)
            if b:
                d.rectangle([*xy(b[:2]), *xy(b[2:])], outline=colour, width=2)
        if p.get("chin"):
            cx, cy = xy(p["chin"])
            d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], outline=colour, width=3)
    d.text((10, 8), title, font=font(20), fill=(255, 255, 255))
    return im


def main():
    before, after, out = sys.argv[1:4]
    a = panel(before, after, "y+000", "neutral front (yaw 0)")
    b = panel(before, after, "ref-front", "scored front: matched open smile (face_SmileOpen 1)")
    sheet = Image.new("RGB", (a.width + b.width + 10, a.height + 60), (20, 20, 20))
    sheet.paste(a, (0, 0))
    sheet.paste(b, (a.width + 10, 0))
    d = ImageDraw.Draw(sheet)
    d.text((10, a.height + 8), "T-215 auburn front difference (Workbench masks, 512 px pass, crop x2.4):  cyan = before "
           "(release 0.14.0)   magenta = after (proposal)", font=font(17), fill=(240, 240, 240))
    d.text((10, a.height + 32), "outlines: head silhouette, eyes, mouth, brows, ears, glasses rim;  lines: iris span;  "
           "boxes: mouth and near-ear (T-204);  circles: chin", font=font(15), fill=(190, 190, 190))
    sheet.save(out, quality=85, optimize=True)
    print(out, sheet.size, os.path.getsize(out))


if __name__ == "__main__":
    main()
