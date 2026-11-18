"""T-082 evidence: the review sheet and the side-by-side MP4 (needs Pillow, and ffmpeg for --video).

    python make_sheet_t082.py <stills dir> <out.jpg> <frame>
        Cycles stills of the boy from docs/evaluation/animation/T-047/render_t047.py (tags boy_<front|q34>_<variant>):
        old staging planning off | old staging T-047 | re-staged T-082, front and 3/4.
    python make_sheet_t082.py --video <frames dir> <out.mp4> <first> <last>
        whole-shot frames from render_frames.py (tags t047_f#### and new_f####), each shot through its own camera:
        T-047 (old staging) | T-082 (re-staged), side by side.
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

COLS = [("old staging, planning OFF", "off"), ("old staging, T-047 ON", "t047"), ("re-staged, T-082 ON", "new")]


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
    d.text((12, 10), f"T-082 boy, e905 f{frame}: old staging off | T-047 on | re-staged T-082 (Cycles 32 spp)", fill=(0, 0, 0),
           font=font(24))
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


def video(src, out, first, last, cell=(640, 360)):
    labels = [("T-047 (old staging)", "t047"), ("T-082 (re-staged)", "new")]
    with tempfile.TemporaryDirectory() as tmp:
        for f in range(first, last + 1):
            img = Image.new("RGB", (cell[0] * len(labels), cell[1] + 30), (245, 245, 245))
            d = ImageDraw.Draw(img)
            for c, (label, tag) in enumerate(labels):
                im = Image.open(os.path.join(src, f"{tag}_f{f:04d}.png")).convert("RGB").resize(cell, Image.LANCZOS)
                img.paste(im, (c * cell[0], 30))
                d.text((c * cell[0] + 8, 6), f"{label}  f{f}", fill=(0, 0, 0), font=font(16))
            img.save(os.path.join(tmp, f"f{f - first:04d}.png"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", os.path.join(tmp, "f%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", out], check=True)


if __name__ == "__main__":
    if sys.argv[1] == "--video":
        video(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
    else:
        sheet(sys.argv[1], sys.argv[2], int(sys.argv[3]))
