#!/usr/bin/env python3
"""Assembles the T-061 evidence media from the run_shot render runs (not committed: shot_*/build/runs/*/render):
t061_before_after.mp4 (before | after, 24 fps) and before_after_sheet.jpg (key frames of the touch and the wave lift).

    python3 make_media.py --before <run>/render ... --after <run>/render ...   (frame_NNNN.png; later runs win)
Needs Pillow and ffmpeg.
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SHEET_FRAMES = [22, 26, 30, 34, 66, 69, 71, 73, 75, 104, 108, 112]


def collect(dirs):
    frames = {}
    for d in dirs:
        for p in sorted(Path(d).glob("frame_*.png")):
            frames[int(p.stem.split("_")[1])] = p
    return frames


def label(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 8 + 7 * len(text), 16], fill=(0, 0, 0))
    d.text((4, 2), text, fill=(255, 255, 255))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", nargs="+", required=True)
    ap.add_argument("--after", nargs="+", required=True)
    a = ap.parse_args()
    fb, fa = collect(a.before), collect(a.after)
    common = sorted(set(fb) & set(fa))
    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(common):
            l = label(Image.open(fb[f]).convert("RGB"), f"before (T-045 engine)  f{f}")
            r = label(Image.open(fa[f]).convert("RGB"), f"after (T-061)  f{f}")
            out = Image.new("RGB", (l.width + r.width, l.height))
            out.paste(l, (0, 0))
            out.paste(r, (l.width, 0))
            out.save(Path(tmp) / f"s_{i:04d}.png")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", str(Path(tmp) / "s_%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", str(HERE / "t061_before_after.mp4")], check=True)
    tiles = [f for f in SHEET_FRAMES if f in fb and f in fa]
    w, h = Image.open(fa[tiles[0]]).size
    s = 0.5
    tw, th = int(w * s), int(h * s)
    sheet = Image.new("RGB", (tw * len(tiles) // 2, th * 4), (255, 255, 255))
    half = len(tiles) // 2
    for i, f in enumerate(tiles):
        col, block = i % half, i // half
        for row, (src, name) in enumerate(((fb, "before"), (fa, "after"))):
            im = label(Image.open(src[f]).convert("RGB").resize((tw, th)), f"{name} f{f}")
            sheet.paste(im, (col * tw, (2 * block + row) * th))
    sheet.save(HERE / "before_after_sheet.jpg", quality=85)
    print("frames", len(common), "->", HERE / "t061_before_after.mp4", HERE / "before_after_sheet.jpg")


if __name__ == "__main__":
    shutil.which("ffmpeg") or SystemExit("ffmpeg not found")
    main()
