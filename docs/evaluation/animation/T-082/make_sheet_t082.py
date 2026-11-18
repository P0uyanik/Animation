"""T-082 evidence: the off | T-047 on | T-082 on review sheet (JPEG, <= 2048 px) from the Cycles stills of
docs/evaluation/animation/T-047/render_t047.py (tags boy_<view>_<variant>), the side strip and the side-by-side MP4
of the boy's hand-over from Workbench frames seen from his right (tags boy_side_<variant>). Needs Pillow (and ffmpeg
for --video).

    python make_sheet_t082.py <stills dir> <out.jpg> <frame>
    python make_sheet_t082.py --strip <frames dir> <out.png> <frame>
    python make_sheet_t082.py --video <frames dir> <out.mp4> <first> <last>
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

COLS = [("planning OFF", "off"), ("T-047 ON (swing 84 deg)", "t047"), ("T-082 ON (swing 37 deg, lean 8 deg)", "t082")]


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # older Pillow
        return ImageFont.load_default()


def sheet(src, out, frame, cell=(512, 640)):
    rows = [("front", "front"), ("3/4", "q34")]
    head, lab = 70, 34
    W, H = cell[0] * len(COLS), head + len(rows) * (cell[1] + lab)
    img = Image.new("RGB", (W, H), (245, 245, 245))
    d = ImageDraw.Draw(img)
    d.text((12, 10), f"T-082 boy, e905 f{frame}: off | T-047 on | T-082 on (Cycles 32 spp)", fill=(0, 0, 0), font=font(26))
    for r, (row_label, view) in enumerate(rows):
        y = head + r * (cell[1] + lab)
        for c, (col_label, variant) in enumerate(COLS):
            x = c * cell[0]
            im = Image.open(os.path.join(src, f"boy_{view}_{variant}_f{frame:04d}.png")).convert("RGB").resize(cell, Image.LANCZOS)
            img.paste(im, (x, y + lab))
            colour = (170, 0, 0) if variant == "off" else (120, 80, 0) if variant == "t047" else (0, 110, 0)
            d.text((x + 8, y + 4), f"{row_label} | {col_label}", fill=colour, font=font(20))
            d.line([(x, y), (x, y + lab + cell[1])], fill=(255, 255, 255), width=3)
    img.save(out, "JPEG", quality=84)


def strip(src, f, cell=(320, 400)):
    img = Image.new("RGB", (cell[0] * len(COLS), cell[1] + 30), (245, 245, 245))
    d = ImageDraw.Draw(img)
    for c, (col_label, variant) in enumerate(COLS):
        im = Image.open(os.path.join(src, f"boy_side_{variant}_f{f:04d}.png")).convert("RGB").resize(cell, Image.LANCZOS)
        img.paste(im, (c * cell[0], 30))
        d.text((c * cell[0] + 6, 6), f"{col_label}  f{f}", fill=(0, 0, 0), font=font(15))
    return img


def video(src, out, first, last):
    with tempfile.TemporaryDirectory() as tmp:
        for f in range(first, last + 1):
            strip(src, f).save(os.path.join(tmp, f"f{f - first:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", os.path.join(tmp, "f%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", out], check=True)


if __name__ == "__main__":
    if sys.argv[1] == "--strip":
        strip(sys.argv[2], int(sys.argv[4])).save(sys.argv[3])
    elif sys.argv[1] == "--video":
        video(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
    else:
        sheet(sys.argv[1], sys.argv[2], int(sys.argv[3]))
