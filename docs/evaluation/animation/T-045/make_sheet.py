#!/usr/bin/env python3
"""T-045: before/after keyframe sheet with the reference poses on top (needs Pillow).

    python make_sheet.py <out.jpg>

Top row: the reference stills the checklist names for T-045 (boy char_C: slouch, head pitched, shoulders forward;
boy #29 turnaround: weight on one leg; girl char_B: upright; girl ref_46: wave). Below: render frames, before (left)
and after (right), cropped to the two characters."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REFS = [("boy char_C", ROOT / "docs/references/char_C_boy.jpg"),
        ("boy #29 turnaround", next((ROOT / "docs/references/boy_pipeline").glob("29_*"), None)),
        ("girl char_B", ROOT / "docs/references/char_B_brown_hair.webp"),
        ("girl ref_46 (wave)", ROOT / "assets/characters/girl_auburn_bun_glasses/references/uploads/ref_46.webp")]
FRAMES = [(1, "idle"), (32, "reach starts (boy)"), (46, "touch"), (90, "wave"), (100, "wave"), (126, "settled idle")]
CROP = (150, 10, 490, 340)  # both characters
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 8 + 9 * len(text), 22), fill=(255, 255, 255))
    d.text((4, 2), text, fill=(0, 0, 0), font=font)
    return im


def main():
    w = (CROP[2] - CROP[0]) * 2
    h = CROP[3] - CROP[1]
    ref_h = 300
    refs = []
    for name, p in REFS:
        if p is None or not Path(p).exists():
            continue
        im = Image.open(p).convert("RGB")
        im = im.resize((int(im.width * ref_h / im.height), ref_h))
        refs.append(label(im, name))
    ref_w = sum(r.width for r in refs)
    cols = 2
    sheet_w = max(w * cols, ref_w)
    rows = (len(FRAMES) + cols - 1) // cols
    sheet = Image.new("RGB", (sheet_w, ref_h + rows * h), (255, 255, 255))
    x = 0
    for r in refs:
        sheet.paste(r, (x, 0))
        x += r.width
    for i, (f, what) in enumerate(FRAMES):
        b = Image.open(HERE / f"shot_before/build/render/frame_{f:04d}.png").convert("RGB").crop(CROP)
        a = Image.open(HERE / f"shot_after/build/render/frame_{f:04d}.png").convert("RGB").crop(CROP)
        pair = Image.new("RGB", (w, h))
        pair.paste(label(b, f"f{f} {what}: before"), (0, 0))
        pair.paste(label(a, "after"), (w // 2, 0))
        ImageDraw.Draw(pair).line((w // 2, 0, w // 2, h), fill=(0, 0, 0), width=2)
        sheet.paste(pair, ((i % cols) * w, ref_h + (i // cols) * h))
    sheet.save(sys.argv[1], quality=88)


if __name__ == "__main__":
    main()
