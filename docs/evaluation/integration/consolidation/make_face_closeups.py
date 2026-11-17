"""Consolidation evidence: girl face close-ups next to reference face crops (plain Python, Pillow).

    python3 docs/evaluation/integration/consolidation/make_face_closeups.py <reference_views_dir> <render_dir> <out_dir>

<render_dir> holds face_front.png and face_34.png rendered by groom_turnaround.py --closeup (orthographic, 0.34 m wide,
centred at the eye line). Reference crops: 150 px squares around the annotated eye line of sheet30_front and
sheet30_front_left (the references are 468 px tall, so the crops are upscaled; they are softer than the renders)."""
import os
import sys

from PIL import Image, ImageDraw

CROPS = {"face_front": ("sheet30_front", (43, 61, 193, 211)), "face_34": ("sheet30_front_left", (49, 62, 199, 212))}
SIZE = 512


def main():
    refs, renders, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    for name, (view, box) in CROPS.items():
        ref = Image.open(os.path.join(refs, view + ".png")).convert("RGB").crop(box).resize((SIZE, SIZE), Image.LANCZOS)
        ren = Image.open(os.path.join(renders, name + ".png")).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
        sheet = Image.new("RGB", (SIZE * 2 + 12, SIZE + 28), (245, 245, 245))
        sheet.paste(ref, (0, 28))
        sheet.paste(ren, (SIZE + 12, 28))
        d = ImageDraw.Draw(sheet)
        d.text((6, 8), f"reference {view} (crop, upscaled)", fill=(20, 20, 20))
        d.text((SIZE + 18, 8), "girl 0.9.0, Cycles, shared calibration", fill=(20, 20, 20))
        sheet.save(os.path.join(out, f"girl_{name}_vs_reference.png"))


if __name__ == "__main__":
    main()
