#!/usr/bin/env python3
"""T-215 review sheet: 8 yaws, rows reference / before (release) / after (proposal build).

    python3 docs/evaluation/characters/T-215/sheet.py <before.blend> <after.blend> <work dir> <out.jpg> \
        [--samples 16] [--px 448] [--rerender]

Renders both blends with T-202's face_views.py (Cycles CPU + OIDN, character_neutral/1 light oriented to the camera,
70 mm, 36 mm vertical sensor, neutral face, auburn framing target (0, 0, 0.84), frame 0.66 m, elevation 5 deg), the
current release look settings. Reference tiles are square head crops (top of the figure) of the sheet30 views;
+45 and +135 have no reference, so the -45 and -135 tiles are mirrored and labelled."""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
REF = "assets/characters/girl_auburn_bun_glasses/references/views/"
YAWS = (0, -45, -90, -135, 180, 135, 90, 45)
REFS = {0: ("sheet30_front", False), -45: ("sheet30_front_left", False), 90: ("sheet30_left", False),
        -90: ("sheet30_right", False), -135: ("sheet30_back_right", False), 180: ("sheet30_back", False),
        45: ("sheet30_front_left", True), 135: ("sheet30_back_right", True)}
TARGET, FRAME, ELEV = "0,0,0.84", "0.66", 5


def font(n):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, n)
    return ImageFont.load_default()


def render(blend, label, work, samples, px):
    views = ",".join(f"{y}:{ELEV}" for y in YAWS)
    cmd = [sys.executable, os.path.join(ROOT, "tools/bpy_blender.py"), "-b", "--factory-startup", "-P",
           os.path.join(ROOT, "docs/evaluation/characters/T-202/face_views.py"), "--", work, blend, label, TARGET,
           FRAME, views, "--samples", str(samples), "--px", str(px)]
    with open(os.path.join(work, f"{label}.log"), "w") as log:
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT)


def ref_tile(name, mirror, size):
    im = Image.open(os.path.join(ROOT, REF + name + ".png")).convert("RGB")
    w = im.width
    im = im.crop((0, 0, w, w))
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def main():
    args = sys.argv[1:]
    opt = {k: args[args.index(k) + 1] for k in ("--samples", "--px") if k in args}
    before, after, work, out = (os.path.abspath(a) for a in args[:4])
    samples, px = int(opt.get("--samples", 16)), int(opt.get("--px", 448))
    os.makedirs(work, exist_ok=True)
    for blend, label in ((before, "before"), (after, "after")):
        if "--rerender" in args or not os.path.exists(os.path.join(work, f"{label}_{YAWS[-1]:+04d}.png")):
            render(blend, label, work, samples, px)
    t, bar, lab = 240, 46, 120
    sheet = Image.new("RGB", (lab + t * len(YAWS), bar + 3 * (t + 22)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    d.text((10, 8), "T-215 auburn 0.14.0, P2 proposal (override only)  |  Cycles %d spp + OIDN, 70 mm, "
           "character_neutral/1, neutral face" % samples, font=font(17), fill=(240, 240, 240))
    d.text((10, 27), "rows: reference (sheet30; front ref smiles) / before = release 0.14.0 / after = proposal build",
           font=font(14), fill=(190, 190, 190))
    for c, yaw in enumerate(YAWS):
        x = lab + c * t
        name, mirror = REFS[yaw]
        tiles = [(ref_tile(name, mirror, t), name + (" (mirrored)" if mirror else "")),
                 (Image.open(os.path.join(work, f"before_{yaw:+04d}.png")).convert("RGB").resize((t, t)), ""),
                 (Image.open(os.path.join(work, f"after_{yaw:+04d}.png")).convert("RGB").resize((t, t)), "")]
        for r, (im, cap) in enumerate(tiles):
            y = bar + r * (t + 22)
            sheet.paste(im, (x, y + 20))
            d.text((x + 4, y + 2), f"yaw {yaw:+d}" + (f"  {cap}" if cap else ""), font=font(12), fill=(220, 220, 220))
    for r, name in enumerate(("reference", "before", "after")):
        d.text((10, bar + r * (t + 22) + 20 + t // 2), name, font=font(18), fill=(240, 240, 240))
    sheet.save(out, quality=82, optimize=True)
    print(out, sheet.size, os.path.getsize(out))


if __name__ == "__main__":
    main()
