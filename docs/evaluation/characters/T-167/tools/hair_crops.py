#!/usr/bin/env python3
"""T-167 hair crops at 100 % next to the references: front, 3/4, side, back of the hair of the round 6 and round 7
masters (same cameras; the yaws are those of the character's reference views), under a row of the original
reference views and a row of the AI-target images (scaled to the tile, labelled).

    python3 docs/evaluation/characters/T-167/tools/hair_crops.py --char <boy|girl|third> --r6 <master.blend>
        --r7 <master.blend> --out <dir> [--samples 16] [--px 600]

Render side: tools/review/blender_render.py, unchanged (as T-160 hair_views.py, whose framing it reuses).
Writes <out>/<tag>/<view>.png, <out>/hair_crops.jpg and hair_crops.json."""
import argparse
import json
import os
import subprocess
import sys
import time

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "T-160", "tools"))
from hair_views import FRAME  # noqa: E402

A = "assets/characters/"
B, G, W = (A + "boy_yellow_hoodie/references/", A + "girl_auburn_bun_glasses/references/",
           A + "girl_white_hair_blue_dress/references/")
# view -> (yaw, elevation, original reference (file, head share of the image height), AI target or None)
VIEWS = {
    "boy": [("front", 0.0, 5.0, (B + "views/val27_front.png", 0.46), None),
            ("threequarter", -35.0, 5.0, (B + "views/val27_threequarter_right.png", 0.46), None),
            ("side", -90.0, 5.0, (B + "views/val27_side_right.png", 0.46),
             B + "uploads/02_higgsfield_B04_hair_side_2026-11-18.webp"),
            ("back", 180.0, 5.0, (B + "views/val27_back.png", 0.46),
             B + "uploads/02_higgsfield_B05_hair_back_crown_2026-11-18.webp")],
    "girl": [("front", 0.0, 5.0, (G + "views/sheet30_front.png", 0.62),
              G + "uploads/higgsfield_G04_fringe_hairline_2026-11-18.webp"),
             ("threequarter", -45.0, 5.0, (G + "views/sheet30_front_left.png", 0.62), None),
             ("side", 90.0, 5.0, (G + "views/sheet30_left.png", 0.62),
              G + "uploads/higgsfield_G06_ringlet_macro_2026-11-18.webp"),
             ("back", 180.0, 5.0, (G + "views/sheet30_back.png", 0.62),
              G + "uploads/higgsfield_G05_hair_back_bun_curls_2026-11-18.webp")],
    "third": [("front", 0.0, 5.0, (W + "views/s02_front.jpg", 0.6), W + "uploads/01_identity_front.webp"),
              ("threequarter", -30.0, 5.0, (W + "views/s02_front_left.jpg", 0.6), None),
              ("side", 90.0, 5.0, (W + "views/s02_left.jpg", 0.6), None),
              ("back", 180.0, 5.0, (W + "views/s02_back.jpg", 0.6),
               W + "uploads/17_higgsfield_W04_hair_back_waves_buns_2026-11-18.webp")],
}
BAR = 18


def fit(im, w, h):
    """im scaled to fit w x h (never cropped), centred on white."""
    k = min(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    t = Image.new("RGB", (w, h), (255, 255, 255))
    t.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--char", required=True, choices=sorted(VIEWS))
    ap.add_argument("--r6", required=True)
    ap.add_argument("--r7", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--px", type=int, default=600)
    ap.add_argument("--compose-only", action="store_true")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    rows = VIEWS[a.char]
    cols = [{"tag": "hair_r6", "blend": os.path.abspath(a.r6), "comparison_pose": None},
            {"tag": "hair_r7", "blend": os.path.abspath(a.r7), "comparison_pose": None}]
    job = {"out": out, "engine": "cycles", "samples": a.samples, "px": a.px, "lens_mm": 70.0, "sensor_mm": 36.0,
           "calibration": "character_neutral/1", "columns": cols,
           "views": [dict(FRAME[a.char], name=n, yaw_deg=yaw, elevation_deg=el) for n, yaw, el, _, _ in rows]}
    secs = None
    if not a.compose_only:
        jp = os.path.join(out, "job.json")
        json.dump(job, open(jp, "w"), indent=1)
        t = time.time()
        with open(os.path.join(out, "render_log.txt"), "w") as f:
            subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup",
                            "-P", os.path.join(ROOT, "tools", "review", "blender_render.py"), "--", jp],
                           stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, check=True)
        secs = round(time.time() - t, 1)
    tiles = [[Image.open(os.path.join(out, c["tag"], n + ".png")).convert("RGB") for n, *_ in rows] for c in cols]
    w, h = tiles[0][0].size
    refs, ais = [], []
    for n, yaw, el, (rf, head), ai in rows:
        im = Image.open(os.path.join(ROOT, rf)).convert("RGB")
        refs.append(fit(im.crop((0, 0, im.width, int(im.height * head))), w, h))
        ais.append(fit(Image.open(os.path.join(ROOT, ai)).convert("RGB"), w, h) if ai else None)
    has_ai = any(ais)
    bands = [("original reference (scaled to the tile)", refs)]
    if has_ai:
        bands.append(("AI target (scaled to the tile; none for an empty tile)", ais))
    bands += [("hair r6 (T-160, opt-in base): %s; Cycles %d spp, 100 %%" % (", ".join(n for n, *_ in rows), a.samples),
               tiles[0]),
              ("hair r7 (T-167): same cameras, 100 %", tiles[1])]
    sheet = Image.new("RGB", (w * len(rows), (h + BAR) * len(bands)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for r, (label, ims) in enumerate(bands):
        d.text((4, r * (h + BAR) + 3), f"{a.char}: {label}", fill=(0, 0, 0))
        for k, im in enumerate(ims):
            if im is not None:
                sheet.paste(im, (k * w, r * (h + BAR) + BAR))
    sheet.save(os.path.join(out, "hair_crops.jpg"), quality=90)
    meta = {"samples": a.samples, "px": a.px, "views": [[n, yaw, el] for n, yaw, el, _, _ in rows],
            "rows": [b[0] for b in bands]}
    if secs is not None:
        meta["render_s"] = secs
        json.dump(meta, open(os.path.join(out, "hair_crops.json"), "w"), indent=1)
    print("render_s", secs, os.path.join(out, "hair_crops.jpg"), sheet.size)


if __name__ == "__main__":
    main()
