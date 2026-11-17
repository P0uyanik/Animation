"""T-039 evidence: 640 px reference | body-render pairs plus a 5-view strip, from a tools/fidelity/run.py output.

    python3 docs/evaluation/characters/T-039/make_turnaround.py build/t039_it3 docs/evaluation/characters/T-039/turnaround
"""
import os
import sys

from PIL import Image, ImageDraw

VIEWS = ("val27_front", "val27_threequarter_right", "val27_side_right", "val27_back", "val27_back_threequarter")
REF = "assets/characters/boy_yellow_hoodie/references/views"


def panel(img, label, w=320, h=640, bg=(64, 64, 68)):
    p = Image.new("RGB", (w, h), bg)
    s = h / img.height
    im = img.convert("RGB").resize((round(img.width * s), h), Image.LANCZOS)
    p.paste(im, ((w - im.width) // 2, 0))
    d = ImageDraw.Draw(p)
    d.rectangle((0, 0, w, 26), fill=(30, 30, 32))
    d.text((8, 7), label, fill=(240, 240, 240))
    return p


def main(run, out):
    os.makedirs(out, exist_ok=True)
    strip = Image.new("RGB", (640 * len(VIEWS) // 2, 640), (64, 64, 68))
    for i, v in enumerate(VIEWS):
        ref = panel(Image.open(os.path.join(REF, v + ".png")), "REFERENCE " + v)
        ren = panel(Image.open(os.path.join(run, "renders", v + ".png")), "BODY 2.0.0-dev (no hair/face/garments)")
        pair = Image.new("RGB", (640, 640))
        pair.paste(ref, (0, 0))
        pair.paste(ren, (320, 0))
        pair.save(os.path.join(out, v + ".png"), optimize=True)
        strip.paste(ren.resize((128, 256)), (128 * i, 384))
        strip.paste(ref.resize((128, 256)), (128 * i, 128))
    d = ImageDraw.Draw(strip)
    d.text((8, 100), "top: reference views   bottom: body 2.0.0-dev (same views, shared calibration)", fill=(240, 240, 240))
    strip.crop((0, 90, 640, 640)).save(os.path.join(out, "turnaround_strip.png"), optimize=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
