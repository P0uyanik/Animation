"""Side-by-side comparison of several subjects rendered by the harness with the same cameras:
reference | subject 1 | subject 2 ... per view, plus a metrics caption.

    python3 pipeline/triptych.py --index <reference_index.json> --subject "It4 baseline=<dir>" --subject "Pilot=<dir>" \
        --views orig07_front,val27_front --out sheet.png [--row-height 420]"""
import argparse
import json
import os

from PIL import Image, ImageDraw


def fit(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--subject", action="append", required=True, help="label=harness render dir")
    ap.add_argument("--views", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--row-height", type=int, default=420)
    a = ap.parse_args()
    vdir = os.path.join(os.path.dirname(a.index), "views")
    subjects = [s.split("=", 1) for s in a.subject]
    H = a.row_height
    rows = []
    for vid in a.views.split(","):
        cells = [("reference " + vid, Image.open(os.path.join(vdir, vid + ".png")).convert("RGB"))]
        for label, d in subjects:
            p = os.path.join(d, vid + ".png")
            if os.path.exists(p):
                im = Image.open(p).convert("RGBA")
                bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
                bg.alpha_composite(im)
                cells.append((label, bg.convert("RGB")))
        parts = []
        for label, im in cells:
            im = fit(im, H)
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 8 + 6 * len(label), 16), fill=(20, 20, 20))
            d.text((4, 3), label, fill=(255, 255, 255))
            parts.append(im)
        w = sum(p.width for p in parts) + 6 * (len(parts) - 1)
        row = Image.new("RGB", (w, H), (255, 255, 255))
        x = 0
        for p in parts:
            row.paste(p, (x, 0))
            x += p.width + 6
        rows.append(row)
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, len(rows) * (H + 6)), (255, 255, 255))
    for i, r in enumerate(rows):
        sheet.paste(r, (0, i * (H + 6)))
    sheet.save(a.out)
    print("wrote", a.out, sheet.size)


if __name__ == "__main__":
    main()
