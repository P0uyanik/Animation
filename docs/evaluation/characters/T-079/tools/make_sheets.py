"""T-070/T-079 render-vs-reference sheets and evidence stills (DELIVERY_PLAN 9b: JPEG q85, long edge <= 2048 px).

    python3 make_sheets.py <renders_dir> <out_dir>

<renders_dir>/<key>_views.png: the 5-view strip from preview.py (turnaround-matched yaws, see VIEWS). Per character:
row 1 = the owner's 2026-11-17 turnaround (assets/references/owner_uploads/), row 2 = hair v3 round 3; an extra
column compares the character's own front reference with the face area of the front render (a crop of the same
still, not an extra render). Also writes media/<key>_<view>.jpg (one still per view)."""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
TURN = os.path.join(ROOT, "assets", "references", "owner_uploads", "turnaround_all_three_2026-11-17.webp")
CHAR = os.path.join(ROOT, "assets", "characters")
# turnaround crops (x ranges, y range in the 1493 x 2000 sheet), render yaw labels, own front reference + crop boxes
VIEWS = {
    "boy": {"title": "boy_yellow_hoodie", "x": [(20, 290), (320, 590), (620, 890), (920, 1190), (1220, 1490)],
            "y": (0, 275), "labels": ["front", "3/4 (yaw -45)", "3/4 other side (yaw +60)", "back 3/4 (yaw -120)",
                                      "back"],
            "own": ("boy_yellow_hoodie/references/views/val27_front.png", (0.0, 0.0, 1.0, 0.72)),
            "crop": (0.08, 0.1, 0.92, 0.95)},
    "girl": {"title": "girl_auburn_bun_glasses", "x": [(40, 300), (320, 570), (575, 810), (805, 1030), (1245, 1485)],
             "y": (1340, 1800), "labels": ["front", "back 3/4 (yaw -150)", "side (yaw -90)", "3/4 (yaw +60)",
                                           "back"],
             "own": ("girl_auburn_bun_glasses/references/views/sheet30_front.png", (0.15, 0.0, 0.85, 0.5)),
             "crop": (0.08, 0.14, 0.92, 0.62)},
    "third": {"title": "girl_white_hair_blue_dress (TEST base: stand-in body/face/outfit)",
              "x": [(20, 300), (330, 570), (590, 800), (1010, 1220), (1225, 1485)], "y": (670, 1100),
              "labels": ["front", "3/4 (yaw +30)", "side (yaw -100)", "side (yaw +95)", "back"],
              "own": ("girl_white_hair_blue_dress/references/views/c15_front.jpg", (0.1, 0.0, 0.9, 0.55)),
              "crop": (0.08, 0.14, 0.92, 0.62)},
}
H = 560


def fit(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def frac_crop(im, box):
    w, h = im.size
    return im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.join(out, "sheets"), exist_ok=True)
    os.makedirs(os.path.join(out, "media"), exist_ok=True)
    turn = Image.open(TURN).convert("RGB")
    for key, v in VIEWS.items():
        strip = Image.open(os.path.join(src, f"{key}_views.png")).convert("RGB")
        n = len(v["x"])
        tw = strip.width // n
        renders = [strip.crop((i * tw, 0, (i + 1) * tw, strip.height)) for i in range(n)]
        for lab, im in zip(["front", "threequarter", "side_a", "side_b", "back"], renders):
            im.save(os.path.join(out, "media", f"{key}_{lab}.jpg"), quality=85)
        refs = [turn.crop((x0, v["y"][0], x1, v["y"][1])) for x0, x1 in v["x"]]
        own = frac_crop(Image.open(os.path.join(CHAR, v["own"][0])).convert("RGB"), v["own"][1])
        mine = frac_crop(renders[0], v["crop"])
        cols = [(fit(r, H), fit(m, H)) for r, m in zip(refs, renders)] + [(fit(own, H), fit(mine, H))]
        widths = [max(a.width, b.width) for a, b in cols]
        lab_w, top = 120, 34
        sheet = Image.new("RGB", (lab_w + sum(widths) + 6 * len(cols), top + 2 * H + 10), (238, 238, 238))
        d = ImageDraw.Draw(sheet)
        d.text((8, 8), f"{v['title']} - hair v3 round 3 (groom/2, T-079) vs references. Row 1: owner turnaround "
                       "2026-11-17 (last column: the character's own front reference). Row 2: render, ortho, "
                       "character_neutral/1, Cycles 16 spp + OIDN (last column: crop of the front render).",
               fill=(0, 0, 0))
        x = lab_w
        for i, (a, b) in enumerate(cols):
            d.text((x + 4, top - 14), (v["labels"] + ["face / own reference"])[i], fill=(0, 0, 0))
            sheet.paste(a, (x + (widths[i] - a.width) // 2, top))
            sheet.paste(b, (x + (widths[i] - b.width) // 2, top + H + 6))
            x += widths[i] + 6
        d.text((8, top + H // 2), "reference", fill=(0, 0, 0))
        d.text((8, top + H + H // 2), "hair v3 r3", fill=(0, 0, 0))
        if max(sheet.size) > 2048:
            k = 2048 / max(sheet.size)
            sheet = sheet.resize((round(sheet.width * k), round(sheet.height * k)), Image.LANCZOS)
        sheet.save(os.path.join(out, "sheets", f"{key}_render_vs_reference.jpg"), quality=85)
        print("sheet", key, sheet.size)


if __name__ == "__main__":
    main()
