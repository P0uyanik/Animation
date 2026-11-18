#!/usr/bin/env python3
"""T-078: side-by-side composite (current approved | new shared systems) -> labelled frames, MP4 and a still sheet.

    python3 docs/evaluation/showcase/T-078/tools/compose.py <current frames dir> <new frames dir> <work dir> <out dir> \
        --still <frame number> [--step 2]

Each panel is a 640x720 run_shot render of the same shot (same camera, light, frames, bake settings). Every rendered
frame is held for <step> video frames (24 fps), so the timing is the shot's own. Needs Pillow and ffmpeg."""
import argparse
import glob
import os
import re
import subprocess

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
LEFT = ("CURRENT APPROVED", "boy 1.1.0  ·  girl 0.10.0")
RIGHT = ("NEW VERSIONS (not yet approved)", "boy 2.0.0  ·  girl 0.11.0")
CAPTION = [
    "Same shot, camera, light and animation (reach_touch_wave, principles + personality on); only the characters differ.",
    "New: face v2 on the fitted head, porcelain-peach felt skin, hair v3 round 3, sneakers/backpack/hood, vest details.",
    "Boy 2.0.0 and girl 0.11.0 await owner approval; nothing is published. Known gaps: see the T-078 README.",
]


def label(img, x, title, sub):
    d = ImageDraw.Draw(img, "RGBA")
    ft, fs = ImageFont.truetype(BOLD, 20), ImageFont.truetype(FONT, 14)
    w = max(d.textlength(title, font=ft), d.textlength(sub, font=fs)) + 24
    d.rounded_rectangle([x + 12, 12, x + 12 + w, 72], 8, fill=(30, 28, 26, 170))
    d.text((x + 24, 18), title, font=ft, fill=(255, 250, 240))
    d.text((x + 24, 46), sub, font=fs, fill=(225, 218, 205))


def frame(cur, new):
    a, b = Image.open(cur).convert("RGB"), Image.open(new).convert("RGB")
    img = Image.new("RGB", (1280, 720))
    img.paste(a, (0, 0))
    img.paste(b, (640, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([638, 0, 641, 720], fill=(250, 246, 238))
    label(img, 0, *LEFT)
    label(img, 640, *RIGHT)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cur")
    ap.add_argument("new")
    ap.add_argument("work")
    ap.add_argument("out")
    ap.add_argument("--still", type=int, required=True)
    ap.add_argument("--step", type=int, default=2)
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)
    nums = sorted(int(re.search(r"(\d+)\.png$", p).group(1)) for p in glob.glob(os.path.join(a.new, "frame_*.png")))
    nums = [n for n in nums if os.path.exists(os.path.join(a.cur, f"frame_{n:04d}.png"))]
    for i, n in enumerate(nums):
        frame(os.path.join(a.cur, f"frame_{n:04d}.png"), os.path.join(a.new, f"frame_{n:04d}.png")).save(
            os.path.join(a.work, f"c_{i:04d}.png"))
    mp4 = os.path.join(a.out, "T-078_progress_current_vs_new.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(24 / a.step), "-i",
                    os.path.join(a.work, "c_%04d.png"), "-r", "24", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4], check=True)
    # still sheet: the chosen frame plus the 3-line caption
    s = frame(os.path.join(a.cur, f"frame_{a.still:04d}.png"), os.path.join(a.new, f"frame_{a.still:04d}.png"))
    sheet = Image.new("RGB", (1280, 720 + 118), (34, 32, 30))
    sheet.paste(s, (0, 0))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 17)
    for i, line in enumerate(CAPTION):
        d.text((20, 734 + i * 27), line, font=f, fill=(240, 234, 222))
    sheet.save(os.path.join(a.out, "T-078_still_sheet.jpg"), quality=90)
    print("frames", len(nums), nums[0], nums[-1], "->", mp4)


if __name__ == "__main__":
    main()
