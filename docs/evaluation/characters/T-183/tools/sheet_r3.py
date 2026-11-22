"""T-183 round 3: before / after sheet of crops of shot frames (released bake | candidate bake, same camera, same
render settings), at most --max-px (default 1024) on the long side.

    python3 sheet_r3.py <spec.json>

spec: {"title": str, "out": path, "max_px": 1024, "columns": [{"label": str}, ...],
       "rows": [{"label": str, "crop": [x0, y0, x1, y1] (pixels of the renders; optional),
                 "images": [path per column]}, ...]}
Paths are relative to the spec's folder. Every tile of a row is the same crop of the same camera; tiles are only
scaled (one factor for the whole sheet), never stretched. Writes the sheet and <out>.json (inputs, crops, size)."""
import json
import os
import sys

from PIL import Image, ImageDraw

BG, BAR, TXT = (92, 92, 96), (20, 20, 20), (240, 240, 240)
HEAD, TITLE = 18, 24


def main():
    spec_path = sys.argv[1]
    here = os.path.dirname(os.path.abspath(spec_path))
    spec = json.load(open(spec_path))
    cols, rows = spec["columns"], spec["rows"]
    tiles = []
    for r in rows:
        ims = []
        for p in r["images"]:
            im = Image.open(os.path.join(here, p)).convert("RGB")
            if r.get("crop"):
                im = im.crop(tuple(r["crop"]))
            ims.append(im)
        tiles.append(ims)
    tw = max(im.width for ims in tiles for im in ims)
    th = [max(im.height for im in ims) for ims in tiles]
    W, H = tw * len(cols), TITLE + HEAD + sum(t + HEAD for t in th)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.rectangle((0, 0, W, TITLE - 1), fill=BAR)
    d.text((6, 5), spec["title"], fill=TXT)
    for c, col in enumerate(cols):
        d.rectangle((c * tw, TITLE, (c + 1) * tw - 1, TITLE + HEAD - 1), fill=(50, 50, 54))
        d.text((c * tw + 6, TITLE + 3), col["label"], fill=TXT)
    y = TITLE + HEAD
    for r, ims, h in zip(rows, tiles, th):
        d.rectangle((0, y, W, y + HEAD - 1), fill=BAR)
        d.text((6, y + 3), r["label"], fill=TXT)
        y += HEAD
        for c, im in enumerate(ims):
            sheet.paste(im, (c * tw + (tw - im.width) // 2, y + (h - im.height) // 2))
        y += h
    s = min(1.0, spec.get("max_px", 1024) / max(W, H))
    if s < 1:
        sheet = sheet.resize((round(W * s), round(H * s)), Image.LANCZOS)
    out = os.path.join(here, spec["out"])
    sheet.save(out, quality=90)
    json.dump({"sheet": os.path.relpath(out, here), "size": list(sheet.size), "max_px": spec.get("max_px", 1024),
               "columns": [c["label"] for c in cols],
               "rows": [{"label": r["label"], "crop": r.get("crop"), "images": r["images"]} for r in rows]},
              open(out + ".json", "w"), indent=1)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
