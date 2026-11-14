"""Enlarged 8-view review sheet of existing hair-experiment renders (no rendering).

    python3 pipeline/charsys/review_views.py --variants H00_reference,H26_... --out <dir> [--root renders/experiments/hair]

Writes review_views_1.jpg (views 1-4) and review_views_2.jpg (views 5-8): columns = reference + variants."""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import compare_sheet as CS  # noqa: E402

VIEWS = ["orig07_front", "val27_front", "val27_threequarter_right", "val27_side_right", "val27_back",
         "val27_back_threequarter", "canon29_threequarter_left", "canon29_back"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--root", default=os.path.join(ROOT, "renders", "experiments", "hair"))
    ap.add_argument("--refs", default=os.path.join(ROOT, "assets", "characters", "boy_yellow_hoodie", "references", "views"))
    ap.add_argument("--size", type=int, default=380)
    a = ap.parse_args()
    S = a.size
    names = a.variants.split(",")

    def crop(img, mask, frac=0.45):
        x0, y0, x1, y1 = CS.bbox(mask)
        h = (y1 - y0) * frac
        cx = (x0 + x1) / 2
        return img.crop((int(cx - h * 0.6), int(y0 - h * 0.06), int(cx + h * 0.6), int(y0 + h))).resize((S, S), Image.LANCZOS)

    def render(p):
        rgba = Image.open(p).convert("RGBA")
        g = Image.new("RGBA", rgba.size, (150, 150, 150, 255))
        g.alpha_composite(rgba)
        return crop(g.convert("RGB"), np.asarray(rgba)[:, :, 3] > 127)

    def ref(v):
        im = Image.open(os.path.join(a.refs, v + ".png")).convert("RGB")
        mp = os.path.join(a.refs, v + "_mask.png")
        m = (np.asarray(Image.open(mp)) > 127) if os.path.exists(mp) else (np.asarray(im.convert("L")) < 245)
        return crop(im, m)
    os.makedirs(a.out, exist_ok=True)
    for part, vs in (("1", VIEWS[:4]), ("2", VIEWS[4:])):
        img = Image.new("RGB", (S * (1 + len(names)), 28 + S * len(vs)), (25, 25, 25))
        d = ImageDraw.Draw(img)
        for j, t in enumerate(["reference"] + names):
            d.text((j * S + 8, 8), t, fill=(255, 255, 255))
        for i, v in enumerate(vs):
            img.paste(ref(v), (0, 28 + i * S))
            for j, n in enumerate(names):
                img.paste(render(os.path.join(a.root, n, "harness", v + ".png")), ((j + 1) * S, 28 + i * S))
            d.text((6, 28 + i * S + 6), v, fill=(255, 255, 0))
        img.save(os.path.join(a.out, f"review_views_{part}.jpg"), quality=88)
    print("[review_views] ->", a.out)


if __name__ == "__main__":
    main()
