#!/usr/bin/env python3
"""T-202: lays out one sheet per character, one row per (view, reference): "reference | current".

    python3 docs/evaluation/characters/T-202/compose.py        (from the repository root, after render_all.sh)

Reference tiles are square head crops of the reference view files (box = x0,y0,x1,y1 in that file, padded to a square
with the crop's border colour, then scaled to the tile). A reference whose face points the other way than the render is
mirrored horizontally and labelled "mirrored". Writes sheets/<character>_faces.jpg and crops/<ref tile>.png."""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
B = "assets/characters/boy_yellow_hoodie/references/views/"
G = "assets/characters/girl_auburn_bun_glasses/references/views/"
T = "assets/characters/girl_white_hair_blue_dress/references/views/"
TILE, BAR = 1000, 64

# (view label, yaw of the render, reference file, ref name, crop box, mirror)
SHEETS = {
    "boy": ("boy_yellow_hoodie", "2.3.0", "boy_2.3.0", [
        ("front", 0, B + "val27_front.png", "val27_front", (0, 0, 240, 240), False),
        ("front", 0, B + "hero24_front.png", "hero24_front", (0, 0, 590, 590), False),
        ("front", 0, B + "canon29_front.png", "canon29_front", (0, 0, 230, 230), False),
        ("3/4", -35, B + "val27_threequarter_right.png", "val27_threequarter_right", (0, 0, 230, 230), False),
        ("3/4", -35, B + "canon29_threequarter_left.png", "canon29_threequarter_left", (0, 0, 220, 220), True),
        ("side", -90, B + "val27_side_right.png", "val27_side_right", (0, 0, 210, 210), False),
        ("side", -90, B + "canon29_side_left.png", "canon29_side_left", (0, 0, 205, 205), True),
    ]),
    "girl": ("girl_auburn_bun_glasses", "0.14.0", "girl_0.14.0", [
        ("front", 0, G + "sheet30_front.png", "ref_30 / sheet30_front", (0, 0, 231, 231), False),
        ("3/4", -45, G + "sheet30_front_left.png", "ref_30 / sheet30_front_left", (0, 0, 205, 215), False),
        ("side", 90, G + "sheet30_left.png", "ref_30 / sheet30_left", (0, 0, 168, 215), False),
    ]),
    "third": ("girl_white_hair_blue_dress", "0.1.0", "third_0.1.0", [
        ("front", 0, T + "id01_full.jpg", "id01 (01_identity_front) / id01_full", (0, 0, 372, 400), False),
        ("front", 0, T + "f14_head_front.jpg", "f14_head_front", (0, 0, 373, 420), False),
        ("front", 0, T + "s02_front.jpg", "02 (02_character_sheet) / s02_front", (0, 0, 151, 160), False),
        ("3/4", -30, T + "f14_head_3q.jpg", "f14_head_3q", (0, 0, 373, 420), False),
        ("3/4", -30, T + "s02_front_left.jpg", "02 / s02_front_left", (0, 0, 134, 150), False),
        ("side", -90, T + "f14_head_side.jpg", "f14_head_side", (0, 0, 373, 420), False),
        ("side", -90, T + "s02_left.jpg", "02 / s02_left", (0, 0, 99, 140), True),
    ]),
}
for p in (os.path.join(HERE, "sheets"), os.path.join(HERE, "crops")):
    os.makedirs(p, exist_ok=True)


def font(n):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, n)
    return ImageFont.load_default()


def ref_tile(path, box, mirror):
    im = Image.open(os.path.join(ROOT, path)).convert("RGB").crop(box)
    a = np.asarray(im)
    bg = tuple(int(v) for v in np.median(np.concatenate([a[0], a[:, 0], a[:, -1]]), axis=0))
    s = max(im.size)
    sq = Image.new("RGB", (s, s), bg)
    sq.paste(im, ((s - im.width) // 2, 0))
    if mirror:
        sq = sq.transpose(Image.FLIP_LEFT_RIGHT)
    return sq


def main():
    for key, (cid, ver, prefix, rows) in SHEETS.items():
        sheet = Image.new("RGB", (2 * TILE, BAR + len(rows) * (TILE + BAR)), (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        d.text((16, 14), "T-202  %s %s  |  neutral face, Cycles 16 spp + OIDN, 70 mm, character_neutral/1 light  |  "
               "left: reference head crop, right: current release" % (cid, ver), font=font(26), fill=(240, 240, 240))
        y = BAR
        for view, yaw, path, name, box, mirror in rows:
            ref = ref_tile(path, box, mirror)
            ref.save(os.path.join(HERE, "crops", "%s_%s_%s.png" % (key, view.replace("/", ""), name.split(" / ")[-1])))
            cur = Image.open(os.path.join(HERE, "renders", "%s_%+04d.png" % (prefix, yaw))).convert("RGB")
            for i, im in enumerate((ref, cur)):
                sheet.paste(im.resize((TILE, TILE), Image.LANCZOS), (i * TILE, y + BAR))
            d.text((16, y + 16), "REFERENCE  %s  view: %s%s  (%s)" % (name, view, " (mirrored)" if mirror else "", os.path.basename(path)),
                   font=font(24), fill=(255, 220, 120))
            d.text((TILE + 16, y + 16), "CURRENT  %s %s  view: %s  yaw %d" % (cid, ver, view, yaw), font=font(24), fill=(150, 220, 255))
            y += TILE + BAR
        sheet.save(os.path.join(HERE, "sheets", "%s_faces.jpg" % key), quality=88)
        print(key, sheet.size)


main()
