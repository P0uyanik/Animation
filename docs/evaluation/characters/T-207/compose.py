#!/usr/bin/env python3
"""T-207: one sheet per character, reference | current | V1 | V2 | V3 | D, rows front / 3/4 / side / back, and a
100 % close-up sheet (crown/fringe crops of the 768 px renders, one 384 px tile each, reference close-up scaled).

    python3 docs/evaluation/characters/T-207/compose.py <work dir of sheets.sh> [boy girl third]

Writes sheets/<character>_hair_looks.jpg, sheets/<character>_hair_100.jpg and results.json (seconds per frame,
strand counts and hashes from the render logs and build reports)."""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
A = os.path.join(ROOT, "assets", "characters")
B = A + "/boy_yellow_hoodie/references/"
G = A + "/girl_auburn_bun_glasses/references/"
T = A + "/girl_white_hair_blue_dress/references/"
LOOKS = [("current", "current (released)"), ("V1", "V1 flock"), ("V2", "V2 velvet shader"),
         ("V3", "V3 flock + edge fuzz"), ("D", "D combed (T-206)")]
TILE, BAR, HEAD, CROP = 480, 36, 64, 384
# view label, render yaw, reference file (None = no reference), crop box in that file, mirror
CHAR = {
    "boy": ("boy_yellow_hoodie 2.3.0", [
        ("front", 0, B + "views/canon29_front.png", (0, 0, 230, 260), False),
        ("3/4", -35, B + "views/canon29_threequarter_left.png", (0, 0, 220, 255), True),
        ("side", -90, B + "views/canon29_side_left.png", (0, 0, 205, 250), True),
        ("back", 180, B + "views/canon29_back.png", (0, 0, 230, 260), False)],
        B + "uploads/02_higgsfield_B04_hair_side_2026-11-18.webp", [(0, (192, 30, 576, 414)), (-90, (192, 30, 576, 414))]),
    "girl": ("girl_auburn_bun_glasses 0.14.0", [
        ("front", 0, G + "views/sheet30_front.png", (0, 0, 231, 231), False),
        ("3/4", -45, G + "views/sheet30_front_left.png", (0, 0, 205, 215), False),
        ("side", 90, G + "views/sheet30_left.png", (0, 0, 168, 215), False),
        ("back", 180, G + "views/sheet30_back.png", (0, 0, 227, 231), False)],
        G + "uploads/higgsfield_G04_fringe_hairline_2026-11-18.webp", [(0, (192, 40, 576, 424)), (-45, (200, 40, 584, 424))]),
    "third": ("girl_white_hair_blue_dress 0.1.0", [
        ("front", 0, T + "views/f14_head_front.jpg", (0, 0, 373, 420), False),
        ("3/4", -30, T + "views/f14_head_3q.jpg", (0, 0, 373, 420), False),
        ("side", -90, T + "views/f14_head_side.jpg", (0, 0, 373, 420), False),
        ("back", 180, T + "views/s02_back.jpg", (0, 0, 150, 160), False)],
        T + "uploads/17_higgsfield_W04_hair_back_waves_buns_2026-11-18.webp", [(0, (192, 30, 576, 414)), (180, (192, 60, 576, 444))]),
}


def font(n):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, n)
    return ImageFont.load_default()


def ref_tile(path, box, mirror):
    im = Image.open(path).convert("RGB").crop(box)
    a = np.asarray(im)
    bg = tuple(int(v) for v in np.median(np.concatenate([a[0], a[:, 0], a[:, -1]]), axis=0))
    s = max(im.size)
    sq = Image.new("RGB", (s, s), bg)
    sq.paste(im, ((s - im.width) // 2, 0))
    return sq.transpose(Image.FLIP_LEFT_RIGHT) if mirror else sq


def blank(text, size):
    im = Image.new("RGB", (size, size), (52, 52, 56))
    ImageDraw.Draw(im).text((size // 2 - 70, size // 2 - 12), text, font=font(22), fill=(200, 200, 200))
    return im


def load(path):
    try:
        return json.load(open(path))
    except OSError:
        return None


def main():
    work = os.path.abspath(sys.argv[1])
    keys = sys.argv[2:] or list(CHAR)
    os.makedirs(os.path.join(HERE, "sheets"), exist_ok=True)
    rpath = os.path.join(HERE, "results.json")
    results = load(rpath) or {}
    for key in keys:
        title, rows, closeup, crops = CHAR[key]
        rdir = os.path.join(work, key, "r")
        info = {}
        for look, _ in LOOKS:
            log = load(os.path.join(rdir, look + ".json")) or {}
            build = load(os.path.join(work, key, look + ".build.json")) or {}
            info[look] = {"seconds_per_frame": log.get("seconds"), "hair_strands_rendered": log.get("hair_strands"),
                          "added_strands_sha_render": log.get("added_strands_sha"),
                          "build_strands": build.get("strands_total"), "build_strand_sha": build.get("strand_sha"),
                          "build_evaluated": build.get("evaluated"), "build_seconds": build.get("seconds"),
                          "velvet_missing": sorted({m for v in (build.get("velvet") or {}).values()
                                                    for m in v.get("missing", [])})}
        results[key] = dict(results.get(key, {}), looks=info)
        cols = 1 + len(LOOKS)
        sheet = Image.new("RGB", (cols * TILE, HEAD + len(rows) * (TILE + BAR)), (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        d.text((12, 8), f"T-207  {title}  |  hair looks, Cycles 16 spp + OIDN, 768 px, 70 mm, character_neutral/1 light"
               "  |  s = seconds per frame (4 CPU threads)", font=font(20), fill=(230, 230, 230))
        for c, (look, name) in enumerate([("ref", "reference")] + LOOKS):
            d.text((c * TILE + 12, 36), name, font=font(20), fill=(255, 210, 120) if c == 0 else (150, 220, 255))
        for r, (view, yaw, path, box, mirror) in enumerate(rows):
            y = HEAD + r * (TILE + BAR)
            ref = ref_tile(path, box, mirror) if path else blank("no reference", TILE)
            sheet.paste(ref.resize((TILE, TILE), Image.LANCZOS), (0, y + BAR))
            d.text((12, y + 8), f"{view}  {os.path.basename(path) if path else ''}{' (mirrored)' if mirror else ''}",
                   font=font(18), fill=(255, 210, 120))
            for c, (look, _) in enumerate(LOOKS, start=1):
                f = os.path.join(rdir, "%s_%+04d.png" % (look, yaw))
                im = Image.open(f).convert("RGB") if os.path.exists(f) else blank("missing", TILE)
                sheet.paste(im.resize((TILE, TILE), Image.LANCZOS), (c * TILE, y + BAR))
                s = (info[look]["seconds_per_frame"] or {}).get("%+04d" % yaw)
                d.text((c * TILE + 12, y + 8), f"{view}  yaw {yaw}" + (f"  {s:.0f} s" if s else ""),
                       font=font(18), fill=(150, 220, 255))
        sheet.save(os.path.join(HERE, "sheets", f"{key}_hair_looks.jpg"), quality=88)
        # 100 % close-ups
        cs = Image.new("RGB", (cols * CROP, HEAD + len(crops) * (CROP + BAR)), (24, 24, 24))
        d = ImageDraw.Draw(cs)
        d.text((12, 8), f"T-207  {title}  |  crown / fringe at 100 % of the 768 px renders (reference close-up scaled)",
               font=font(18), fill=(230, 230, 230))
        for c, (look, name) in enumerate([("ref", "reference " + os.path.basename(closeup)[:28])] + LOOKS):
            d.text((c * CROP + 8, 36), name, font=font(16), fill=(255, 210, 120) if c == 0 else (150, 220, 255))
        ref = Image.open(closeup).convert("RGB")
        s = min(ref.size)
        ref = ref.crop((0, 0, s, s)).resize((CROP, CROP), Image.LANCZOS)
        for r, (yaw, box) in enumerate(crops):
            y = HEAD + r * (CROP + BAR)
            cs.paste(ref, (0, y + BAR))
            d.text((8, y + 8), f"yaw {yaw}  box {box}", font=font(16), fill=(255, 210, 120))
            for c, (look, _) in enumerate(LOOKS, start=1):
                f = os.path.join(rdir, "%s_%+04d.png" % (look, yaw))
                im = Image.open(f).convert("RGB").crop(box) if os.path.exists(f) else blank("missing", CROP)
                cs.paste(im, (c * CROP, y + BAR))
        cs.save(os.path.join(HERE, "sheets", f"{key}_hair_100.jpg"), quality=90)
        print("sheet", key)
    json.dump(results, open(rpath, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
