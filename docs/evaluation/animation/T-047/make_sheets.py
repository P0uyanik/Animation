"""T-047 evidence: composes the planning off | on review sheets (JPEG, <= 2048 px) and the side-by-side MP4 from the
stills of render_t047.py. Needs Pillow and ffmpeg.

    python make_sheets.py <render dir> <out dir>
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

CELL = (512, 640)


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # older Pillow
        return ImageFont.load_default()


def sheet(src, rows, cols, title, out):
    head, lab = 70, 34
    W = CELL[0] * len(cols)
    H = head + len(rows) * (CELL[1] + lab)
    img = Image.new("RGB", (W, H), (245, 245, 245))
    d = ImageDraw.Draw(img)
    d.text((12, 10), title, fill=(0, 0, 0), font=font(26))
    for r, (row_label, prefix, frame) in enumerate(rows):
        y = head + r * (CELL[1] + lab)
        for c, (col_label, suffix) in enumerate(cols):
            x = c * CELL[0]
            p = os.path.join(src, f"{prefix}_{suffix}_f{frame:04d}.png")
            im = Image.open(p).convert("RGB").resize(CELL, Image.LANCZOS)
            img.paste(im, (x, y + lab))
            colour = (170, 0, 0) if suffix.endswith("off") else (0, 110, 0)
            d.text((x + 8, y + 4), f"{row_label} | {col_label}", fill=colour, font=font(22))
            d.line([(x, y), (x, y + lab + CELL[1])], fill=(255, 255, 255), width=3)
    img.save(out, "JPEG", quality=84)
    print(out, img.size)


def video(src_off, src_on, out, frames):
    tmp = tempfile.mkdtemp()
    for f in frames:
        a = Image.open(os.path.join(src_off, f"girl_f{f:04d}.png")).convert("RGB")
        b = Image.open(os.path.join(src_on, f"girl_f{f:04d}.png")).convert("RGB")
        img = Image.new("RGB", (a.width + b.width, a.height + 40), (245, 245, 245))
        img.paste(a, (0, 40))
        img.paste(b, (a.width, 40))
        d = ImageDraw.Draw(img)
        d.text((10, 8), f"planning OFF   f{f}", fill=(170, 0, 0), font=font(22))
        d.text((a.width + 10, 8), f"planning ON (T-047)   f{f}", fill=(0, 110, 0), font=font(22))
        img.save(os.path.join(tmp, f"f{f:04d}.png"))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-start_number", str(frames[0]), "-i",
                    os.path.join(tmp, "f%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", out], check=True)
    print(out)


def main():
    src, out = sys.argv[1], sys.argv[2]
    cols = [("front, planning OFF", "front_off"), ("front, planning ON", "front_on"),
            ("3/4, planning OFF", "q34_off"), ("3/4, planning ON", "q34_on")]
    sheet(src, [("girl 0.10.0, e905 f42", "cy_e905_girl", 42), ("boy 1.1.0, e905 f42", "cy_e905_boy", 42)], cols,
          "T-047 arm planning off | on - e905 s010 frame 42 (largest corrections), Cycles 32 spp, other character and table hidden",
          os.path.join(out, "t047_e905_f42_cycles_sheet.jpg"))
    sheet(src, [("girl 0.10.0, e905 f35", "wb_e905_girl", 35), ("girl 0.10.0, e904 f6", "wb_e904_girl", 6)], cols,
          "T-047 arm planning off | on - e905 f35 (largest elbow swing, girl R) and e904 f6 (largest lift), Workbench",
          os.path.join(out, "t047_e905_f35_e904_f6_workbench_sheet.jpg"))
    video(os.path.join(src, "mp4_off"), os.path.join(src, "mp4_on"), os.path.join(out, "t047_e905_girl_off_on.mp4"),
          list(range(1, 73)))


if __name__ == "__main__":
    main()
