"""T-124 banding sheet: the soft background gradient (and the hoodie) of decoded frames vs the 16-bit master, with
contrast stretched x8 around the master's mean so that 8-bit/10-bit steps and blocking become visible.
    python banding_sheet.py <master.png> <out.jpg> <label=decoded.png> ..."""
import sys

import numpy as np
from PIL import Image, ImageDraw

REGIONS = [(40, 380, 240, 240), (800, 560, 240, 150)]


def load(p):
    return np.asarray(Image.open(p)).astype(np.float64) / (65535.0 if Image.open(p).mode.startswith("I;16") or np.asarray(Image.open(p)).dtype == np.uint16 else 255.0)


def main():
    master, out, items = sys.argv[1], sys.argv[2], [("master 16-bit PNG", sys.argv[1])] + [tuple(a.split("=", 1)) for a in sys.argv[3:]]
    m = load(master)[..., :3]
    tiles = []
    for name, p in items:
        im = load(p)[..., :3]
        row = []
        for x, y, w, h in REGIONS:
            c, mc = im[y:y + h, x:x + w], m[y:y + h, x:x + w]
            s = np.clip((c - mc.mean(axis=(0, 1))) * 8 + 0.5, 0, 1)
            row.append(Image.fromarray((s * 255).astype(np.uint8)))
        tiles.append((name, row))
    W = sum(r[2] for r in REGIONS) + 4
    H = max(r[3] for r in REGIONS)
    sheet = Image.new("RGB", (W, (H + 18) * len(tiles)), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for i, (name, row) in enumerate(tiles):
        y = i * (H + 18)
        d.text((3, y + 3), name + "  (contrast x8)", fill=(255, 255, 255))
        x = 0
        for t in row:
            sheet.paste(t, (x, y + 16))
            x += t.width + 4
    sheet.save(out, quality=90)


if __name__ == "__main__":
    main()
