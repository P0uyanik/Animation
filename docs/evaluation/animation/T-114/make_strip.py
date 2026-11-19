#!/usr/bin/env python3
"""T-114 evidence strip: the reference moments (top) against the e909 frames (current cast; and the T-113 candidate
copy, s010_t113, when its frames are given).

    python3 docs/evaluation/animation/T-114/make_strip.py --frames <s010 render> [--candidate <s010_t113 frames>] --out strip.jpg

Reference frames are decoded with ffmpeg from docs/references/video_watertable.mp4 (WT, cropped to the boy and the girl
with glasses) and video_paperboat.mp4 (PB, the reveal). Moments and frame ranges: docs/evaluation/animation/T-106
(README "Acting and timing targets"). e909 frames are the shot's rendered PNGs (frame_NNNN.png). Needs ffmpeg, Pillow."""
import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
WT, PB = ROOT / "docs/references/video_watertable.mp4", ROOT / "docs/references/video_paperboat.mp4"
WT_PAIR = (0, 150, 560, 760)  # the boy and the girl with glasses in the 828x1108 watertable frame
PB_ALL = (0, 0, 854, 480)
# (label, video, frame, crop, e909 frame, candidate frame or None)
MOMENTS = [
    ("WT f005 she notices: wonder, round mouth", WT, 5, WT_PAIR, 24, None),
    ("WT f030 she leans in and reaches", WT, 30, WT_PAIR, 57, None),
    ("WT f065 he answers late: blink, head lift", WT, 65, WT_PAIR, 118, None),
    ("PB f272 open smile (delight)", PB, 272, PB_ALL, 150, 232),
    ("WT f100 he holds his look on the object", WT, 100, WT_PAIR, 200, None),
    ("WT f110 settled smile, end hold", WT, 110, WT_PAIR, 275, 275),
]
CELL = (320, 240)


def grab(video, frame, tmp):
    out = Path(tmp) / f"{video.stem}_{frame}.png"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vf", f"select=eq(n\\,{frame})", "-vframes", "1",
                    str(out)], check=True)
    return Image.open(out).convert("RGB")


def fit(im):
    im = im.copy()
    im.thumbnail(CELL)
    cell = Image.new("RGB", CELL, (255, 255, 255))
    cell.paste(im, ((CELL[0] - im.width) // 2, (CELL[1] - im.height) // 2))
    return cell


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True, help="folder with frame_NNNN.png of the s010 render")
    ap.add_argument("--candidate", default="", help="folder with frame_NNNN.png of the s010_t113 render")
    ap.add_argument("--out", required=True)
    ap.add_argument("--crop", type=int, nargs=4, default=(80, 0, 560, 360), help="crop of the 640x360 e909 frame")
    a = ap.parse_args()
    rows = 3 if a.candidate else 2
    W, H, lab = CELL[0] * len(MOMENTS), (CELL[1] + 20) * rows, 20
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)

    def shot(folder, f):
        return fit(Image.open(Path(folder) / f"frame_{f:04d}.png").convert("RGB").crop(tuple(a.crop)))

    with tempfile.TemporaryDirectory() as tmp:
        for i, (label, video, f, crop, ef, cf) in enumerate(MOMENTS):
            x = i * CELL[0]
            sheet.paste(fit(grab(video, f, tmp).crop(crop)), (x, lab))
            d.text((x + 4, 4), label, fill=(0, 0, 0))
            y = CELL[1] + lab
            d.text((x + 4, y + 4), f"e909 s010 f{ef:03d} (current: boy 2.1.0, girl 0.12.0)", fill=(0, 0, 0))
            sheet.paste(shot(a.frames, ef), (x, y + lab))
            if a.candidate:
                y += CELL[1] + lab
                if cf:
                    d.text((x + 4, y + 4), f"s010_t113 f{cf:03d} (girl + T-113 override)", fill=(0, 0, 0))
                    sheet.paste(shot(a.candidate, cf), (x, y + lab))
                else:
                    d.text((x + 4, y + 4), "s010_t113: same as s010", fill=(120, 120, 120))
    sheet.save(a.out, quality=88)
    print(a.out)


if __name__ == "__main__":
    main()
