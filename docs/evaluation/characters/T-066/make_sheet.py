"""T-066 review sheets: reference | current (approved version) | candidate (approved + presets/2 skin), one row per view.

    python make_sheet.py <out.jpg> <title> <row> [<row> ...]
    row = "<label>|<reference image>|<x0,y0,x1,y1 crop in reference pixels>|<current render>|<candidate render>"

Every cell is 512 x 512 (reference crops are letterboxed onto the neutral grey, never stretched). JPEG quality 85,
long edge <= 2048 px (DELIVERY_PLAN §9b). Needs Pillow.
"""
import sys

from PIL import Image, ImageDraw

CELL = 512
HEAD = 30
BG = (96, 96, 98)


def fit(im):
    im = im.convert("RGB")
    im.thumbnail((CELL, CELL), Image.LANCZOS) if max(im.size) > CELL else None
    if max(im.size) < CELL:
        s = CELL / max(im.size)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    cell = Image.new("RGB", (CELL, CELL), BG)
    cell.paste(im, ((CELL - im.width) // 2, (CELL - im.height) // 2))
    return cell


def main():
    out, title, rows = sys.argv[1], sys.argv[2], sys.argv[3:]
    sheet = Image.new("RGB", (3 * CELL, HEAD + len(rows) * (CELL + HEAD)), (245, 245, 245))
    d = ImageDraw.Draw(sheet)
    d.text((8, 8), title, fill=(0, 0, 0))
    for r, row in enumerate(rows):
        label, ref, box, cur, cand = row.split("|")
        y = HEAD + r * (CELL + HEAD)
        for c, text in enumerate((f"{label}: reference", "current (approved)", "candidate (presets/2 skin)")):
            d.text((c * CELL + 8, y + 8), text, fill=(0, 0, 0))
        x0, y0, x1, y1 = (int(v) for v in box.split(","))
        cells = [Image.open(ref).convert("RGB").crop((x0, y0, x1, y1)), Image.open(cur), Image.open(cand)]
        for c, im in enumerate(cells):
            sheet.paste(fit(im), (c * CELL, y + HEAD))
    sheet.save(out, quality=85)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
