"""T-068 evidence sheets: per item a reference | current | candidate comparison from the Cycles stills.

    python3 docs/evaluation/characters/T-068/make_sheets.py <renders dir> <out dir>

<renders dir> holds the groom_turnaround.py outputs in sub-folders boy_current, boy_candidate, girl_current,
girl_vest, girl_dress (one <view>.png per reference view). Crops are fractions of each image's own character height
(detected against the background), so the reference and the render line up although their framing differs (the
render cameras use the reference views' yaw/elevation/focal and frame the character's bounding box)."""
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
    "sneakers": [(f"{BOY_REF}/val27_front.png", "boy_current", "boy_candidate", "val27_front", 0.82, 1.0),
                 (f"{BOY_REF}/val27_side_right.png", "boy_current", "boy_candidate", "val27_side_right", 0.82, 1.0)],
    "backpack": [(f"{BOY_REF}/canon29_back.png", "boy_current", "boy_candidate", "val27_back", 0.3, 0.72),
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


def extent(im):
    """Vertical and horizontal extent of the character: rows/columns with enough pixels that differ from the
    background colour (median of the four corners)."""
    small = im.resize((im.width // 2, im.height // 2))
    px = small.load()
    w, h = small.size
    corners = [px[1, 1], px[w - 2, 1], px[1, h - 2], px[w - 2, h - 2]]
    bg = tuple(sorted(c[i] for c in corners)[1] for i in range(3))

    def fg(x, y):
        return sum(abs(a - b) for a, b in zip(px[x, y], bg)) > 60
    rows = [y for y in range(h) if sum(fg(x, y) for x in range(0, w, 2)) > 0.04 * w / 2]
    cols = [x for x in range(w) if sum(fg(x, y) for y in range(0, h, 2)) > 0.02 * h / 2]
    if not rows or not cols:
        return 0, 0, im.width, im.height
    return cols[0] * 2, rows[0] * 2, cols[-1] * 2 + 2, rows[-1] * 2 + 2


def tile(path, y0, y1):
    """Crop [y0, y1] of the character's own height (not the frame), scaled to a common height."""
    if path is None or not os.path.exists(path):
        im = Image.new("RGB", (H // 2, H // 2), (60, 60, 64))
        ImageDraw.Draw(im).text((10, H // 4), "n/a (new type)", fill=(220, 220, 220))
        return im
    im = Image.open(path).convert("RGB")
    x0, top, x1, bottom = extent(im)
    span = bottom - top
    a, b = top + y0 * span, top + y1 * span
    pad = 0.08 * span
    crop = im.crop((max(0, round(x0 - pad)), max(0, round(a - 0.02 * span)), min(im.width, round(x1 + pad)),
                    min(im.height, round(b + 0.02 * span))))
    out_h = round(H * 0.5 * max(0.35, (y1 - y0)) / 0.5) if y1 - y0 < 0.99 else H
    out_h = min(out_h, H)
    return crop.resize((max(1, round(crop.width * out_h / crop.height)), out_h))


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
        if sheet.height > 1300:  # keep the repository light
            sheet = sheet.resize((round(sheet.width * 1300 / sheet.height), 1300))
        sheet.save(os.path.join(out, f"{item}.png"))
        print("wrote", item)


if __name__ == "__main__":
    main()
