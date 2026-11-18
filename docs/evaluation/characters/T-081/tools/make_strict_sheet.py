"""T-081 strict comparison sheet: original reference | 0.10.0 | 0.11.0, rendered by strict_render.py in one run with
identical cameras, lights, world, exposure, samples and resolution.

    python3 docs/evaluation/characters/T-081/tools/make_strict_sheet.py <strict_render out_dir> <out.jpg>

Rows: front, 3/4, side, back (full body), face front, face 3/4. References: sheet30 views (front, front_left, left,
back) and the ref_30 "Neutral" face tile / the ref_30 front-left head. Renders are not cropped or rescaled
differently: both versions' tiles of a row are the same pixels of the same camera."""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
REF = os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "references")
ROWS = [
    ("front", "body_front", ("views/sheet30_front.png", None), "sheet30 front"),
    ("3/4", "body_34", ("views/sheet30_front_left.png", None), "sheet30 front-left"),
    ("side", "body_side", ("views/sheet30_left.png", None), "sheet30 left"),
    ("back", "body_back", ("views/sheet30_back.png", None), "sheet30 back"),
    ("face front", "face_front", ("uploads/ref_30.webp", (440, 620, 712, 840)), "ref_30 Neutral"),
    ("face 3/4", "face_34", ("uploads/ref_30.webp", (345, 90, 490, 260)), "ref_30 front-left"),
]
COL_W, BODY_H, FACE_H = 400, 640, 400


def tile(im, w, h, text):
    im = im.convert("RGB")
    s = min(w / im.width, (h - 20) / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    c = Image.new("RGB", (w, h), (92, 92, 96))
    c.paste(im, ((w - im.width) // 2, 20 + (h - 20 - im.height) // 2))
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, w, 19), fill=(20, 20, 20))
    d.text((5, 4), text, fill=(240, 240, 240))
    return c


def main():
    src, out = sys.argv[1:3]
    rows = []
    for name, shot, (ref, crop), ref_label in ROWS:
        h = FACE_H if shot.startswith("face") else BODY_H
        r = Image.open(os.path.join(REF, ref))
        if crop:
            r = r.crop(crop)
        cells = [tile(r, COL_W, h, f"REFERENCE {name} ({ref_label})")]
        for tag, label in (("0.10.0", "0.10.0 current"), ("0.11.0", "0.11.0 candidate")):
            cells.append(tile(Image.open(os.path.join(src, tag, shot + ".png")), COL_W, h, f"{label} | {name}"))
        rows.append(cells)
    sheet = Image.new("RGB", (COL_W * 3, sum(r[0].height for r in rows)), (92, 92, 96))
    y = 0
    for r in rows:
        for i, c in enumerate(r):
            sheet.paste(c, (i * COL_W, y))
        y += r[0].height
    sheet.save(out, quality=90)
    print("wrote", out, sheet.size)


main()
