"""T-081 owner sheet: reference | 0.10.0 (current) | 0.11.0 for front, 3/4, side, back and the face close-up.

    python3 docs/evaluation/characters/T-081/tools/make_sheet.py <renders_0.10.0> <renders_0.11.0> <out.jpg>

Renders come from render_views.py (body_0, body_35, body_90, body_180, face_0, face_30). References: the girl's
sheet30 views (front, front-left, left, back), the ref_30 "Neutral" face tile and the ref_34 "Neutral" tile, and the
girl row of the owner turnaround (2026-11-17)."""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
REF = os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "references")
TURN = os.path.join(ROOT, "assets", "references", "owner_uploads", "turnaround_all_three_2026-11-17.webp")
H = 400


def fit(im, h=H, w=None):
    im = im.convert("RGB")
    im = im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)
    if w:
        c = Image.new("RGB", (w, h), (92, 92, 96))
        c.paste(im, ((w - im.width) // 2, 0))
        im = c
    return im


def autocrop(im, margin=8):
    """Crops a render to the character (pixels that differ from the corner background colour)."""
    from PIL import ImageChops
    im = im.convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((0, 0)))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    if not box:
        return im
    return im.crop((max(box[0] - margin, 0), max(box[1] - margin, 0), min(box[2] + margin, im.width), min(box[3] + margin, im.height)))


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 18), fill=(20, 20, 20))
    d.text((4, 3), text, fill=(235, 235, 235))
    return im


def main():
    cur, new, out = sys.argv[1:4]
    notes = dict(a.split("=", 1) for a in sys.argv[4:] if "=" in a)  # optional <shot>=<label suffix>
    turn = Image.open(TURN)
    tw = turn.width / 6.0  # girl row: bottom third, six columns (front, back-left, left, right, front-right, back)
    girl_row = [turn.crop((int(i * tw), 1330, int((i + 1) * tw), 2000)) for i in range(6)]
    rows = [
        ("front", [Image.open(os.path.join(REF, "views", "sheet30_front.png")), girl_row[0]], "body_0"),
        ("3/4", [Image.open(os.path.join(REF, "views", "sheet30_front_left.png")), girl_row[4]], "body_35"),
        ("side", [Image.open(os.path.join(REF, "views", "sheet30_left.png")), girl_row[3]], "body_90"),
        ("back", [Image.open(os.path.join(REF, "views", "sheet30_back.png")), girl_row[5]], "body_180"),
        ("face", [Image.open(os.path.join(REF, "uploads", "ref_30.webp")).crop((440, 620, 712, 840)),
                  Image.open(os.path.join(REF, "uploads", "ref_34.webp")).crop((1066, 66, 1270, 286))], "face_0"),
        ("face 3/4", [Image.open(os.path.join(REF, "uploads", "ref_30.webp")).crop((345, 90, 490, 260))], "face_30"),
    ]
    tiles = []
    for name, refs, shot in rows:
        row = [label(fit(r, w=300 if name.startswith("face") else 230), f"REF {name}" + (" (sheet30/ref_30)" if i == 0 else " (turnaround/ref_34)"))
               for i, r in enumerate(refs)]
        while len(row) < 2:
            row.append(Image.new("RGB", (230 if not name.startswith("face") else 300, H), (92, 92, 96)))
        for tag, d in (("0.10.0 current", cur), ("0.11.0 candidate", new)):
            p = os.path.join(d, shot + ".png")
            im = Image.open(p) if os.path.exists(p) else None
            if im is not None and shot.startswith("body"):
                im = autocrop(im)
            row.append(label(fit(im, w=300) if im is not None else Image.new("RGB", (H, H), (60, 0, 0)), f"{tag} {name}" + (f" {notes[shot]}" if tag.startswith("0.11") and shot in notes else "")))
        tiles.append(row)
    w = max(sum(t.width for t in r) for r in tiles)
    sheet = Image.new("RGB", (w, H * len(tiles)), (92, 92, 96))
    for y, r in enumerate(tiles):
        x = 0
        for t in r:
            sheet.paste(t, (x, y * H))
            x += t.width
    sheet.save(out, quality=90)
    print("wrote", out, sheet.size)


main()
