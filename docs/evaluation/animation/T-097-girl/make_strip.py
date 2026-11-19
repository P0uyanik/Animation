#!/usr/bin/env python3
"""T-097-girl evidence strip: the reference moments (top) against the e908 Cycles frames (bottom).

    python3 docs/evaluation/animation/T-097-girl/make_strip.py --frames <run>/render --out strip.jpg

Reference frames are decoded with ffmpeg from docs/references/video_watertable.mp4 (WT, the girl's crop) and
video_paperboat.mp4 (PB); e908 frames are the shot's rendered PNGs (frame_NNNN.png). Needs ffmpeg and Pillow."""
import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
WT, PB = ROOT / "docs/references/video_watertable.mp4", ROOT / "docs/references/video_paperboat.mp4"
WT_GIRL = (190, 120, 560, 760)  # the girl with glasses in the 828x1108 watertable frame (left, top, right, bottom)
PB_GIRL = (430, 0, 760, 330)  # her face and hands on the rim in the 854x480 paperboat reveal
# (label, video, frame, crop, e908 frame)
MOMENTS = [
    ("WT f005 hand at chin, eyes wide, rounded mouth", WT, 5, WT_GIRL, 40),
    ("WT f030 leans and points down", WT, 30, WT_GIRL, 66),
    ("WT f050 sustains the point, mouth closed", WT, 50, WT_GIRL, 82),
    ("PB f272 wide open smile (delighted)", PB, 272, PB_GIRL, 100),
    ("WT f088 straightens", WT, 88, WT_GIRL, 124),
    ("WT f110 upright, closed soft smile", WT, 110, WT_GIRL, 150),
]
CELL = (300, 300)


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
    ap.add_argument("--frames", required=True, help="folder with frame_NNNN.png of the e908 render")
    ap.add_argument("--out", required=True)
    ap.add_argument("--e908-crop", type=int, nargs=4, default=(120, 0, 520, 360), help="crop of the 640x360 e908 frame")
    a = ap.parse_args()
    W, H, top = CELL[0] * len(MOMENTS), CELL[1] * 2 + 44, 22
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (label, video, f, crop, ef) in enumerate(MOMENTS):
            ref = grab(video, f, tmp).crop(crop)
            sheet.paste(fit(ref), (i * CELL[0], top))
            shot = Image.open(Path(a.frames) / f"frame_{ef:04d}.png").convert("RGB").crop(tuple(a.e908_crop))
            sheet.paste(fit(shot), (i * CELL[0], top + CELL[1] + 22))
            d.text((i * CELL[0] + 4, 4), label, fill=(0, 0, 0))
            d.text((i * CELL[0] + 4, top + CELL[1] + 4), f"e908 f{ef:03d} (girl 0.11.0, Cycles)", fill=(0, 0, 0))
    sheet.save(a.out, quality=88)
    print(a.out)


if __name__ == "__main__":
    main()
