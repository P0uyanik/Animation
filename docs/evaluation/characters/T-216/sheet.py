#!/usr/bin/env python3
"""T-216 combined review sheet (T-215 sheet.py generalised to N build rows + an expression strip).

    python3 docs/evaluation/characters/T-216/sheet.py <work dir> <out.jpg> <label>=<blend> [<label>=<blend> ...] \
        [--samples 16] [--px 448] [--rerender] [--face | --expr]

Rows: reference, then one row per <label>=<blend> in the given order.
--expr: front close-up strip, one row per build, columns neutral / Smile / Blink 0.5 / Blink / Smile+Blink /
SmileOpen (face_views.py --face).

--face: face close-up (target (0, 0, 0.765), frame 0.34 m: eye-to-chin is 27 % of the frame) at -90, -45, 0, +45,
+90. Reference tiles are cropped from the sheet30 annotations (eye and chin landmarks) to the same eye position and
eye-to-chin fraction; -90 has no annotated reference, so the +90 tile is mirrored there and labelled.

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
FACE_YAWS = (-90, -45, 0, 45, 90)
FACE_REFS = {0: ("sheet30_front", False), -45: ("sheet30_front_left", False), 45: ("sheet30_front_left", True),
             90: ("sheet30_left", False), -90: ("sheet30_left", True)}
FACE_TARGET, FACE_FRAME, FACE_EYE, FACE_SPAN = "0,0,0.765", "0.34", 0.453, 0.272  # eye at 45.3 %, eye-chin 27.2 %


def font(n):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, n)
    return ImageFont.load_default()


def render(blend, label, work, samples, px, yaws=YAWS, target=TARGET, frame=FRAME, face=""):
    views = ",".join(f"{y}:{ELEV}" for y in yaws)
    cmd = [sys.executable, os.path.join(ROOT, "tools/bpy_blender.py"), "-b", "--factory-startup", "-P",
           os.path.join(HERE, "face_views.py"), "--", work, blend, label, target,
           frame, views, "--samples", str(samples), "--px", str(px)] + (["--face", face] if face else [])
    with open(os.path.join(work, f"{label}.log"), "w") as log:
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT)


def ref_tile(name, mirror, size):
    im = Image.open(os.path.join(ROOT, REF + name + ".png")).convert("RGB")
    w = im.width
    im = im.crop((0, 0, w, w))
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def face_ref_tile(name, mirror, size):
    """Square crop with the render's eye height and eye-to-chin fraction, from the reference annotations."""
    import json
    im = Image.open(os.path.join(ROOT, REF + name + ".png")).convert("RGB")
    lm = json.load(open(os.path.join(ROOT, REF.replace("views/", "annotations/") + name + ".json")))["landmarks"]
    eye_y = lm["eye_L"][1] if "eye_R" not in lm else (lm["eye_L"][1] + lm["eye_R"][1]) / 2
    side = (lm["chin"][1] - eye_y) / FACE_SPAN
    cx = lm["chin"][0] if "ear_top_L" not in lm or "eye_R" in lm else (lm["chin"][0] + lm["ear_top_L"][0]) / 2
    top = eye_y - FACE_EYE * side
    a = np.asarray(im)
    bg = tuple(int(v) for v in np.median(a[0], axis=0))
    canvas = Image.new("RGB", (im.width + 400, im.height + 400), bg)
    canvas.paste(im, (200, 200))
    tile = canvas.crop((int(cx - side / 2) + 200, int(top) + 200, int(cx + side / 2) + 200, int(top + side) + 200))
    if mirror:
        tile = tile.transpose(Image.FLIP_LEFT_RIGHT)
    return tile.resize((size, size), Image.Resampling.LANCZOS)


EXPR = (("neutral", ""), ("Smile", "Smile=1"), ("Blink 0.5", "Blink=0.5"), ("Blink", "Blink=1"),
        ("Smile+Blink", "Smile=1,Blink=1"), ("SmileOpen", "SmileOpen=1"))


def grid(out, title, sub, cols, rows, t, fs=13):
    """rows: [(row label, [(PIL image, caption)] per column)]."""
    bar, lab = 46, 130
    sheet = Image.new("RGB", (lab + t * len(cols), bar + len(rows) * (t + 22)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    d.text((10, 8), title, font=font(17), fill=(240, 240, 240))
    d.text((10, 27), sub, font=font(14), fill=(190, 190, 190))
    for r, (name, tiles) in enumerate(rows):
        y = bar + r * (t + 22)
        d.text((10, y + 20 + t // 2), name, font=font(18), fill=(240, 240, 240))
        for c, (im, cap) in enumerate(tiles):
            x = lab + c * t
            sheet.paste(im.resize((t, t)), (x, y + 20))
            d.text((x + 4, y + 2), cols[c] + (f"  {cap}" if cap else ""), font=font(fs), fill=(220, 220, 220))
    sheet.save(out, quality=82, optimize=True)
    print(out, sheet.size, os.path.getsize(out))


def tile(work, label, yaw):
    return Image.open(os.path.join(work, f"{label}_{yaw:+04d}.png")).convert("RGB")


def main():
    args = sys.argv[1:]
    opt = {k: args[args.index(k) + 1] for k in ("--samples", "--px") if k in args}
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--samples", "--px"))]
    work, out = os.path.abspath(pos[0]), os.path.abspath(pos[1])
    builds = [(a.split("=", 1)[0], os.path.abspath(a.split("=", 1)[1])) for a in pos[2:]]
    samples = int(opt.get("--samples", 16))
    os.makedirs(work, exist_ok=True)
    rr = "--rerender" in args
    names = " / ".join(n for n, _ in builds)
    if "--expr" in args:
        px = int(opt.get("--px", 384))
        rows = []
        for n, blend in builds:
            tiles = []
            for i, (cap, face) in enumerate(EXPR):
                label = f"expr_{n}_{i}".replace(" ", "_").replace(".", "_")
                if rr or not os.path.exists(os.path.join(work, f"{label}_+000.png")):
                    render(blend, label, work, samples, px, (0,), FACE_TARGET, FACE_FRAME, face)
                tiles.append((tile(work, label, 0), ""))
            rows.append((n, tiles))
        return grid(out, "T-216 auburn expression strip (front close-up, frame 0.34 m) | Cycles %d spp + OIDN" % samples,
                    "rows: " + names + "; columns: face controls set on the rig (Blender evaluation)",
                    [c for c, _ in EXPR], rows, 300)
    if "--face" in args:
        px = int(opt.get("--px", 512))
        yaws, refs, t = FACE_YAWS, FACE_REFS, 330
        target, frame = FACE_TARGET, FACE_FRAME
    else:
        px = int(opt.get("--px", 448))
        yaws, refs, t = YAWS, REFS, 240
        target, frame = TARGET, FRAME
    pre = "face_" if "--face" in args else ""
    for n, blend in builds:
        label = pre + n.replace(" ", "_").replace(".", "_")
        if rr or not os.path.exists(os.path.join(work, f"{label}_{yaws[-1]:+04d}.png")):
            render(blend, label, work, samples, px, yaws, target, frame)
    reft = face_ref_tile if "--face" in args else ref_tile
    rows = [("reference", [(reft(refs[y][0], refs[y][1], t), refs[y][0] + (" (mirrored)" if refs[y][1] else ""))
                           for y in yaws])]
    for n, _ in builds:
        label = pre + n.replace(" ", "_").replace(".", "_")
        rows.append((n, [(tile(work, label, y), "") for y in yaws]))
    kind = "face close-up (frame 0.34 m)" if "--face" in args else "8 yaws"
    grid(out, f"T-216 auburn {kind} | Cycles {samples} spp + OIDN, 70 mm, character_neutral/1, neutral face",
         "rows: reference (sheet30; front ref smiles; mirrored where labelled) / " + names,
         [f"yaw {y:+d}" for y in yaws], rows, t, 12)


if __name__ == "__main__":
    main()
