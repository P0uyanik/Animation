"""T-058 evidence sheets: reference | render pairs for the turnaround, the face close-ups and the expression set.

    python3 docs/evaluation/characters/T-058/make_sheets.py <fidelity run> <face dir> <expression dir> <out dir>

<fidelity run>: tools/fidelity/run.py output (renders/<view>.png); <face dir>: face_front.png, face_threequarter.png
(pipeline/charsys/tests/face_expression_sheet.py, Neutral); <expression dir>: expressions_<Preset>.png tiles.
"""
import os
import sys

from PIL import Image, ImageDraw

VIEWS = ("val27_front", "val27_threequarter_right", "val27_side_right", "val27_back", "val27_back_threequarter")
REF = "assets/characters/boy_yellow_hoodie/references/views"
SHEET08 = "docs/references/boy_pipeline/08_boy_turnaround_proportions_expressions_clothing_sheet.webp"
SHEET28 = "docs/references/boy_pipeline/28_boy_facial_expression_library.webp"
CHAR_C = "docs/references/char_C_boy.jpg"
# expression -> (render preset, crop of the reference tile as fractions of its sheet, sheet)
EXPRESSIONS = [("Neutral", "Neutral", (0.045, 0.085, 0.265, 0.27), SHEET28),
               ("Happy", "Smile", (0.29, 0.085, 0.51, 0.27), SHEET28),
               ("Sad", "Sadness", (0.535, 0.085, 0.755, 0.27), SHEET28),
               ("Surprised", "Surprise", (0.78, 0.085, 1.0, 0.27), SHEET28),
               ("Angry", "Anger", (0.045, 0.31, 0.265, 0.495), SHEET28),
               ("Bored", "Bored", (0.535, 0.535, 0.755, 0.72), SHEET28)]


def panel(img, label, w=320, h=640, bg=(64, 64, 68)):
    p = Image.new("RGB", (w, h), bg)
    s = min(h / img.height, w / img.width)
    im = img.convert("RGB").resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    p.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    d = ImageDraw.Draw(p)
    d.rectangle((0, 0, w, 22), fill=(30, 30, 32))
    d.text((6, 5), label, fill=(240, 240, 240))
    return p


def crop(path, box):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    return im.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)))


def main(run, face, expr, out):
    os.makedirs(out, exist_ok=True)
    strip = Image.new("RGB", (5 * 256, 2 * 512), (64, 64, 68))
    for i, v in enumerate(VIEWS):
        p = os.path.join(run, "renders", v + ".png")
        if not os.path.exists(p):
            continue
        ref = panel(Image.open(os.path.join(REF, v + ".png")), "REFERENCE " + v)
        ren = panel(Image.open(p), "2.0.0-dev (T-058)")
        pair = Image.new("RGB", (640, 640))
        pair.paste(ref, (0, 0))
        pair.paste(ren, (320, 0))
        pair.save(os.path.join(out, "turn_" + v + ".png"), optimize=True)
        strip.paste(ref.resize((256, 512)), (256 * i, 0))
        strip.paste(ren.resize((256, 512)), (256 * i, 512))
    strip.save(os.path.join(out, "turnaround_strip.png"), optimize=True)
    faces = [(Image.open(CHAR_C).crop((40, 60, 380, 330)), "REFERENCE char_C (front)"),
             (Image.open(os.path.join(face, "face_front.png")), "2.0.0-dev Neutral, front"),
             (crop(SHEET28, EXPRESSIONS[0][2]), "REFERENCE #28 r1c1 (3/4)"),
             (Image.open(os.path.join(face, "face_threequarter.png")), "2.0.0-dev Neutral, 3/4")]
    sheet = Image.new("RGB", (4 * 400, 400), (64, 64, 68))
    for i, (im, label) in enumerate(faces):
        sheet.paste(panel(im, label, 400, 400), (400 * i, 0))
    sheet.save(os.path.join(out, "face_closeup.png"), optimize=True)
    sheet = Image.new("RGB", (len(EXPRESSIONS) * 300, 600), (64, 64, 68))
    for i, (name, preset, box, src) in enumerate(EXPRESSIONS):
        sheet.paste(panel(crop(src, box), f"REF {name}", 300, 300), (300 * i, 0))
        p = os.path.join(expr, f"expressions_{preset}.png")
        if os.path.exists(p):
            sheet.paste(panel(Image.open(p), f"{name} ({preset})", 300, 300), (300 * i, 300))
    sheet.save(os.path.join(out, "expressions.png"), optimize=True)


if __name__ == "__main__":
    main(*sys.argv[1:5])
