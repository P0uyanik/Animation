"""Make the T-014 frames 30-60 boy-eye contact strip from a 640x360 T-010 derivative render."""
import argparse
import os

from PIL import Image, ImageDraw

FRAMES = (30, 36, 42, 48, 54, 60)
# T-010 boy face crop (230,120,450,260 at 960x540), scaled to the requested 640x360 rerun.
BOY_FACE_640 = (153, 80, 300, 173)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cell = (320, 210)
    sheet = Image.new("RGB", (cell[0] * 3, cell[1] * 2), (0, 0, 0))
    for i, frame in enumerate(FRAMES):
        src = os.path.join(a.frames, f"frame_{frame:04d}.png")
        im = Image.open(src).convert("RGB")
        if im.size != (640, 360):
            raise ValueError(f"{src}: expected 640x360, got {im.size}")
        tile = im.crop(BOY_FACE_640).resize((cell[0], cell[1]), Image.Resampling.LANCZOS)
        d = ImageDraw.Draw(tile)
        d.rectangle((0, 0, 88, 22), fill=(0, 0, 0))
        d.text((6, 5), f"frame {frame}", fill=(255, 255, 255))
        sheet.paste(tile, ((i % 3) * cell[0], (i // 3) * cell[1]))
    path = os.path.join(a.out, "t010_frames_30_60_contact_strip.png")
    sheet.save(path)
    print("[t014_contact_sheet] ->", path)


if __name__ == "__main__":
    main()
