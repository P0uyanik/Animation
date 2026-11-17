"""T-064: recover the T-049 study renders (A/B/C x 3 fidelity views) from the committed contact sheets.

T-049 did not commit its 640 px renders. The contact sheets hold every render scaled to 210x420 (LANCZOS, JPEG q88),
so the beauty images are cut out and scaled back to 320x640. They are blurrier than the originals (texture terms
read low for all three approaches alike); silhouettes, hair masks and colours are usable.

    python3 extract_t049_tiles.py <out_dir>      -> <out_dir>/<boy|girl>_<A|B|C>/<view>.png
"""
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CHARS = json.load(open(os.path.join(ROOT, "pipeline/charsys/experiments/hair_study/specs/characters.json")))
TILE_W, TILE_H, GAP, LABEL_W = 210, 420, 6, 150


def main():
    out = sys.argv[1]
    for c in ("boy", "girl"):
        sheet = Image.open(os.path.join(HERE, "..", "T-049", f"{c}_contact_sheet.jpg")).convert("RGB")
        for row, ap in enumerate("ABC", start=1):
            d = os.path.join(out, f"{c}_{ap}")
            os.makedirs(d, exist_ok=True)
            y = row * (TILE_H + GAP)
            for i, view in enumerate(CHARS[c]["views"]):
                x = LABEL_W + i * (TILE_W + GAP)
                tile = sheet.crop((x, y, x + TILE_W, y + TILE_H)).resize((320, 640), Image.LANCZOS)
                tile.save(os.path.join(d, view + ".png"))
    print("ok")


if __name__ == "__main__":
    main()
