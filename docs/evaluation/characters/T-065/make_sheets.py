"""T-065 evidence sheets: reference | render pairs per character (face front, 3/4, expression set).

    python3 docs/evaluation/characters/T-065/make_sheets.py <render root> <out dir> [<baseline dir>]

<render root>/<who>/<Preset>_<yaw>.png from render_face.py (who = boy, girl, third, third_parted). The optional
<baseline dir> holds the current-version stills (boy_2.0-dev_Neutral_0.png, ...) shown next to the candidate."""
import os
import sys

from PIL import Image, ImageDraw

BOY28 = "docs/references/boy_pipeline/28_boy_facial_expression_library.webp"
BOY08 = "docs/references/boy_pipeline/08_boy_turnaround_proportions_expressions_clothing_sheet.webp"
CHAR_C = "docs/references/char_C_boy.jpg"
G34 = "assets/characters/girl_auburn_bun_glasses/references/uploads/ref_34.webp"
G30 = "assets/characters/girl_auburn_bun_glasses/references/uploads/ref_30.webp"
W14 = "assets/characters/girl_white_hair_blue_dress/references/uploads/14_face_expression_mouth_shape_grid.webp"
W04 = "assets/characters/girl_white_hair_blue_dress/references/uploads/04_facial_rig_expression_blueprint.webp"
W02 = "assets/characters/girl_white_hair_blue_dress/references/uploads/02_character_sheet.webp"


def t28(r, c):  # #28 tile (row, column), 0-based
    xs = [(0.045, 0.265), (0.29, 0.51), (0.535, 0.755), (0.78, 1.0)]
    ys = [(0.085, 0.27), (0.31, 0.495), (0.535, 0.72), (0.76, 0.945)]
    return (xs[c][0], ys[r][0], xs[c][1], ys[r][1])


def g34(col, row):  # ref_34 blendshape matrix tile
    x0 = (0.715, 0.858)[col]
    y0 = 0.052 + row * 0.1172  # below the previous tile's label
    return (x0, y0, x0 + 0.137, y0 + 0.088)


SHEETS = {
    "boy": {"title": "Boy 2.0-dev + face_generic/2 candidate",
            "faces": [((CHAR_C, (40 / 421, 60 / 794, 380 / 421, 330 / 794)), "Neutral_0", "front"),
                      ((BOY28, t28(0, 0)), "Neutral_30", "3/4")],
            "expr": [("Neutral", (BOY28, t28(0, 0)), "Neutral_30"), ("Happy", (BOY28, t28(0, 1)), "Smile_25"),
                     ("Sad", (BOY28, t28(0, 2)), "Sadness_25"), ("Surprised", (BOY28, t28(0, 3)), "Surprise_25"),
                     ("Angry", (BOY28, t28(1, 0)), "Anger_25"), ("Bored/sleepy", (BOY28, t28(3, 0)), "Bored_25")]},
    "girl": {"title": "Girl next version + face_generic/2 candidate",
             "faces": [((G34, (0.12, 0.11, 0.40, 0.34)), "Neutral_0", "front (ref_34 Neutral)"),
                       ((G30, (0.0, 0.0, 1.0, 1.0)), "Neutral_35", "3/4 (ref_30)")],
             "expr": [("Neutral", (G34, g34(0, 0)), "Neutral_0"), ("Happy", (G34, g34(0, 3)), "Smile_0"),
                      ("Sad", (G34, g34(1, 5)), "Sadness_0"), ("Surprised", (G34, g34(1, 4)), "Surprise_0"),
                      ("Angry", (G34, g34(0, 6)), "Anger_0")]},
    "third": {"title": "Third character head-only test (face_generic/2)",
              "faces": [((W14, (0.0, 0.0, 0.25, 0.25)), "Neutral_0", "front (14)"),
                        ((W14, (0.25, 0.0, 0.5, 0.25)), "Neutral_35", "3/4 (14)")],
              "expr": [("Neutral (soft smile)", (W14, (0.0, 0.265, 0.2, 0.5)), "../third_workbench/Neutral_0"),
                       ("Happy", (W14, (0.36, 0.265, 0.5, 0.5)), "../third_workbench/Smile_0"),
                       ("Sad", (W14, (0.5, 0.265, 0.66, 0.5)), "../third_workbench/Sadness_0"),
                       ("Surprised", (W14, (0.4, 0.515, 0.6, 0.75)), "../third_workbench/Surprise_0"),
                       ("Angry (04 Anger)", (W04, (0.0, 0.875, 0.2, 0.98)), "../third_workbench/Anger_0"),
                       ("Sleepy", (W14, (0.6, 0.515, 0.8, 0.75)), "../third_workbench/Blinkx0.7_0"),
                       ("Parted lips rest (watching)", (W14, (0.0, 0.87, 0.2, 1.0)), "../third_parted/Neutral_0")]},
}


def panel(img, label, w, h, bg=(64, 64, 68)):
    p = Image.new("RGB", (w, h), bg)
    s = min(h / img.height, w / img.width)
    im = img.convert("RGB").resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    p.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    d = ImageDraw.Draw(p)
    d.rectangle((0, 0, w, 20), fill=(30, 30, 32))
    d.text((5, 4), label, fill=(240, 240, 240))
    return p


def crop(src):
    path, box = src
    im = Image.open(path).convert("RGB")
    W, H = im.size
    return im.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)))


def main(root, out, base=None):
    os.makedirs(out, exist_ok=True)
    for who, cfg in SHEETS.items():
        d = os.path.join(root, who)
        if not os.path.isdir(d):
            continue
        tiles = []
        for src, shot, label in cfg["faces"]:
            tiles.append(panel(crop(src), "REFERENCE " + label, 380, 380))
            p = os.path.join(d, shot + ".png")
            if base and os.path.exists(os.path.join(base, f"{who}_{shot}.png")):
                tiles.append(panel(Image.open(os.path.join(base, f"{who}_{shot}.png")), "current version " + label, 380, 380))
            if os.path.exists(p):
                tiles.append(panel(Image.open(p), "face v2 candidate " + label, 380, 380))
        sheet = Image.new("RGB", (380 * len(tiles), 380), (64, 64, 68))
        for i, t in enumerate(tiles):
            sheet.paste(t, (380 * i, 0))
        sheet.save(os.path.join(out, f"{who}_face_vs_reference.png"), optimize=True)
        ex = cfg["expr"]
        sheet = Image.new("RGB", (300 * len(ex), 600), (64, 64, 68))
        for i, (name, src, shot) in enumerate(ex):
            sheet.paste(panel(crop(src), "REF " + name, 300, 300), (300 * i, 0))
            p = os.path.normpath(os.path.join(d, shot + ".png"))
            if os.path.exists(p):
                sheet.paste(panel(Image.open(p), name + " (v2)", 300, 300), (300 * i, 300))
        sheet.save(os.path.join(out, f"{who}_expressions.png"), optimize=True)
        print("sheets:", who)


if __name__ == "__main__":
    main(*sys.argv[1:4])
