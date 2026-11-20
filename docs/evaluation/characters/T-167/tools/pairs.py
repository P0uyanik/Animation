#!/usr/bin/env python3
"""T-167: r6 | r7 pair sheet from the tiles hair_crops.py rendered (no new render).

    python3 pairs.py --char boy --crops <hair_crops out dir> --out <file.jpg>

One row per view (front, threequarter, side, back), left hair r6, right hair r7, 100 % tiles, same camera and light."""
import argparse
import os

from PIL import Image, ImageDraw

VIEWS = ("front", "threequarter", "side", "back")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--char", required=True)
    ap.add_argument("--crops", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t = {c: [Image.open(os.path.join(a.crops, c, v + ".png")).convert("RGB") for v in VIEWS] for c in ("hair_r6", "hair_r7")}
    w, h = t["hair_r6"][0].size
    gap, head = 8, 22
    sheet = Image.new("RGB", (2 * w + gap, len(VIEWS) * (h + head)), "white")
    d = ImageDraw.Draw(sheet)
    for r, v in enumerate(VIEWS):
        y = r * (h + head)
        for c, tag in enumerate(("hair_r6", "hair_r7")):
            x = c * (w + gap)
            d.text((x + 4, y + 5), f"{a.char}: {tag.replace('_', ' ')}, {v}, 100 %", fill="black")
            sheet.paste(t[tag][r], (x, y + head))
    sheet.save(a.out, quality=90)
    print(a.out, sheet.size)


if __name__ == "__main__":
    main()
