#!/usr/bin/env python3
"""T-117 contact sheet: 16 frames of the e910 s010 render with the beat each one shows (python3, Pillow).

    python3 docs/evaluation/animation/T-117/make_contact_sheet.py \
        --frames episodes/e910_showcase/shots/s010/build/render --out docs/evaluation/animation/T-117/contact_sheet.jpg

Frames are the shot's rendered PNGs (frame_NNNN.png, 640x360), shown at half size in a 4 x 4 grid."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

# (scene frame, label): the T-117 beats, read from the bake (README section 1)
MOMENTS = [
    (8, "bored, looks off; her hand at chin"),
    (18, "fidget: he looks back at the cup"),
    (30, "fidget: he looks off again"),
    (40, "she looks at him; his heavy lids"),
    (52, "his late notice: lids lift"),
    (66, "he reaches for the cup"),
    (78, "grasp: fingers on the cup"),
    (90, "he carries it up; her wonder"),
    (104, "he holds it out; she reaches"),
    (116, "shared hold: contact"),
    (128, "shared hold: both faces"),
    (140, "release; she looks at the cup"),
    (153, "delight: SmileOpen peak"),
    (166, "she looks at him; his late answer"),
    (180, "he looks away"),
    (192, "end hold"),
]
CELL = (320, 180)
LABEL_H = 18


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    cols = 4
    rows = (len(MOMENTS) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * CELL[0], rows * (CELL[1] + LABEL_H)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (f, label) in enumerate(MOMENTS):
        x, y = (i % cols) * CELL[0], (i // cols) * (CELL[1] + LABEL_H)
        im = Image.open(a.frames / f"frame_{f:04d}.png").convert("RGB").resize(CELL, Image.LANCZOS)
        sheet.paste(im, (x, y + LABEL_H))
        draw.text((x + 4, y + 3), f"f{f}  {label}", fill="black")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out, quality=90)
    print(a.out)


if __name__ == "__main__":
    main()
