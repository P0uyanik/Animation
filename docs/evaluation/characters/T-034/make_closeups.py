"""T-034 close-up sheet: reference crop | before | after per garment area (Pillow).

    python3 docs/evaluation/characters/T-034/make_closeups.py <reference views dir> <before renders> <after renders> <out.png>

Reference crops are boxes on sheet30_front (231 x 468 px), upscaled to the render tile size; the renders are the
groom_turnaround.py close-ups named below (640 px, same calibration as the turnaround).
"""
import sys

from PIL import Image, ImageDraw

BOXES = {  # sheet30_front pixel boxes (left, top, right, bottom)
    "sleeve": (20, 185, 92, 282),
    "collar": (82, 176, 148, 214),
    "vest": (55, 185, 175, 310),
    "bloomers": (55, 260, 172, 350),
    "boots": (60, 392, 172, 462),
}
TILE = 300


def fit(img, size=TILE):
    img = img.convert("RGB")
    scale = size / max(img.size)
    img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    out = Image.new("RGB", (size, size), (96, 94, 100))
    out.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
    return out


def main(ref_dir, before, after, out):
    ref = Image.open(f"{ref_dir}/sheet30_front.png")
    rows = []
    for name, box in BOXES.items():
        tiles = [fit(ref.crop(box)), fit(Image.open(f"{before}/{name}.png")), fit(Image.open(f"{after}/{name}.png"))]
        row = Image.new("RGB", (TILE * 3, TILE + 18), (40, 40, 44))
        for k, (tile, label) in enumerate(zip(tiles, ("reference", "before (T-028b)", "after (T-034)"))):
            row.paste(tile, (k * TILE, 18))
            ImageDraw.Draw(row).text((k * TILE + 4, 3), f"{name}: {label}", fill=(235, 235, 235))
        rows.append(row)
    sheet = Image.new("RGB", (TILE * 3, sum(r.height for r in rows)))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.save(out)


if __name__ == "__main__":
    main(*sys.argv[1:5])
