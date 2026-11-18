"""T-068 evidence sheets: per item a reference | current | candidate comparison from the Cycles stills.

    python3 docs/evaluation/characters/T-068/make_sheets.py <renders dir> <out dir>

<renders dir> holds the groom_turnaround.py outputs in sub-folders boy_current, boy_candidate, girl_current,
girl_vest, girl_dress (one <view>.png per reference view). Crops are fractions of the frame height; every image is
scaled to the same height first, so the reference and the render line up roughly (the cameras use the reference
views' yaw/elevation/focal and frame the character's bounding box)."""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
BOY_REF = os.path.join(ROOT, "assets/characters/boy_yellow_hoodie/references/views")
GIRL_REF = os.path.join(ROOT, "assets/characters/girl_auburn_bun_glasses/references/views")
DRESS_REF = os.path.join(ROOT, "assets/characters/girl_white_hair_blue_dress/references/views")
H = 640

# item -> (rows of (reference path, current folder or None, candidate folder, view, crop y0, y1))
ITEMS = {
    "sneakers": [(f"{BOY_REF}/val27_front.png", "boy_current", "boy_candidate", "val27_front", 0.78, 1.0),
                 (f"{BOY_REF}/val27_side_right.png", "boy_current", "boy_candidate", "val27_side_right", 0.78, 1.0)],
    "backpack": [(f"{BOY_REF}/val27_back.png", "boy_current", "boy_candidate", "val27_back", 0.3, 0.72),
                 (f"{BOY_REF}/val27_side_right.png", "boy_current", "boy_candidate", "val27_side_right", 0.3, 0.72),
                 (f"{BOY_REF}/val27_front.png", "boy_current", "boy_candidate", "val27_front", 0.3, 0.72)],
    "hoodie_hood_underarm": [
        (f"{BOY_REF}/val27_back.png", "boy_current", "boy_candidate", "val27_back", 0.26, 0.62),
        (f"{BOY_REF}/val27_back_threequarter.png", "boy_current", "boy_candidate", "val27_back_threequarter", 0.26, 0.62),
        (f"{BOY_REF}/val27_side_right.png", "boy_current", "boy_candidate", "val27_side_right", 0.26, 0.62)],
    "vest_details": [(f"{GIRL_REF}/sheet30_front.png", "girl_current", "girl_vest", "sheet30_front", 0.38, 0.74),
                     (f"{GIRL_REF}/sheet30_front_left.png", "girl_current", "girl_vest", "sheet30_front_left", 0.38, 0.74)],
    "gathered_skirt_hem_rib": [
        (f"{DRESS_REF}/c15_front.jpg", None, "girl_dress", "sheet30_front", 0.0, 1.0),
        (f"{DRESS_REF}/c15_side.jpg", None, "girl_dress", "sheet30_left", 0.0, 1.0),
        (f"{DRESS_REF}/c15_back.jpg", None, "girl_dress", "sheet30_back", 0.0, 1.0)],
}


def tile(path, y0, y1):
    if path is None or not os.path.exists(path):
        im = Image.new("RGB", (H // 2, H), (60, 60, 64))
        ImageDraw.Draw(im).text((10, H // 2), "n/a (new type)", fill=(220, 220, 220))
    else:
        im = Image.open(path).convert("RGB")
        im = im.resize((max(1, round(im.width * H / im.height)), H))
    return im.crop((0, round(y0 * H), im.width, round(y1 * H)))


def main():
    renders, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for item, rows in ITEMS.items():
        tiles = []
        for ref, cur, cand, view, y0, y1 in rows:
            tiles.append([("REFERENCE " + os.path.basename(ref), tile(ref, y0, y1)),
                          ("CURRENT " + (cur or "-"), tile(os.path.join(renders, cur, f"{view}.png") if cur else None, y0, y1)),
                          ("CANDIDATE T-068", tile(os.path.join(renders, cand, f"{view}.png"), y0, y1))])
        col_w = [max(r[c][1].width for r in tiles) for c in range(3)]
        row_h = [max(t.height for _, t in r) + 18 for r in tiles]
        sheet = Image.new("RGB", (sum(col_w) + 8 * 4, sum(row_h) + 30), (34, 34, 38))
        d = ImageDraw.Draw(sheet)
        d.text((8, 6), f"T-068 {item}: reference | current | candidate (Cycles, shared calibration)", fill=(240, 240, 240))
        y = 30
        for r, h in zip(tiles, row_h):
            x = 8
            for c, (label, t) in enumerate(r):
                d.text((x, y), label, fill=(230, 230, 230))
                sheet.paste(t, (x, y + 16))
                x += col_w[c] + 8
            y += h
        sheet.save(os.path.join(out, f"{item}.png"))
        print("wrote", item)


if __name__ == "__main__":
    main()
