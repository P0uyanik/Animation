"""T-044 render-vs-reference sheets: per character, row 1 = reference, row 2 = hair v3 render, columns front, 3/4,
side, back, face close-up (same reference cameras where the character has a calibrated reference index).

    python3 make_sheets.py <sheets.json> <out_dir>
sheets.json: {"<key>": {"title", "cols": [{"label", "ref": [path, crop_frac_or_box], "render": [path, crop]}]}}
crop: a number = keep the top fraction of the image; [l, t, r, b] = fractions of the box."""
import json
import os
import sys

from PIL import Image, ImageDraw

H = 420


def load(spec):
    path, crop = spec
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if isinstance(crop, (int, float)):
        im = im.crop((0, 0, w, int(h * crop)))
    else:
        im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    return im.resize((max(1, int(im.width * H / im.height)), H))


def main():
    cfg = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for key, c in cfg.items():
        rows = [[load(col["ref"]) for col in c["cols"]], [load(col["render"]) for col in c["cols"]]]
        widths = [max(rows[0][i].width, rows[1][i].width) for i in range(len(c["cols"]))]
        top, lab = 30, 110
        sheet = Image.new("RGB", (lab + sum(widths) + 6 * len(widths), top + 2 * H + 12), (240, 240, 240))
        d = ImageDraw.Draw(sheet)
        d.text((8, 8), c["title"], fill=(0, 0, 0))
        x = lab
        for i, col in enumerate(c["cols"]):
            d.text((x + 4, top - 14), col["label"], fill=(0, 0, 0))
            for r in range(2):
                sheet.paste(rows[r][i], (x, top + r * (H + 6)))
            x += widths[i] + 6
        d.text((8, top + H // 2), "reference", fill=(0, 0, 0))
        d.text((8, top + H + 6 + H // 2), "hair v3", fill=(0, 0, 0))
        sheet.save(os.path.join(out, f"{key}_render_vs_reference.jpg"), quality=88)
        print("sheet", key)


if __name__ == "__main__":
    main()
