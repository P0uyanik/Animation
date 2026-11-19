#!/usr/bin/env python3
"""T-126a expression sheet: the shared expression library (04 matrix, 15 presets incl. the optional SmileOpen) on her
build, each next to her own reference tile (04 matrix, 14 mouth shape). Rendering is the T-113 renderer
(docs/evaluation/characters/T-113/expr_sheet.py, read-only, unchanged): T-087 light rig, 70 mm, Cycles + OIDN.

    python3 docs/evaluation/characters/T-126/body_face/expr.py --blend <master.blend> --out <dir> [--samples 12 --px 300]
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
VIEWS = os.path.join(ROOT, "assets/characters/girl_white_hair_blue_dress/references/views")
ROWS = [("Neutral", "m04_neutral"), ("Smile", "m04_smile"), ("Laugh", "m04_laugh"), ("SmileOpen", "f14_m3_open_smile_teeth"),
        ("Surprise", "m04_surprise"), ("Sadness", "m04_sadness"), ("Anger", "m04_anger"), ("Frown", "m04_frown"),
        ("Confusion", "m04_confusion"), ("MouthOpen", "m04_mouth_open"), ("Blink", "m04_blink_both"),
        ("LeftEyeClosed", "m04_blink_l"), ("RightEyeClosed", "m04_blink_r"), ("Squint", "m04_squint"),
        ("WideOpen", "m04_wide_open")]
T, HEAD, PER_ROW = 200, 16, 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--px", type=int, default=300)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    job = {"out": out, "samples": a.samples, "px": a.px, "frame": "face", "yaw": 0.0, "elev": 5.0,
           "columns": [{"tag": "c", "blend": os.path.abspath(a.blend)}],
           "rows": [{"tag": n, "controls": {} if n == "Neutral" else {"face_" + n: 1.0}, "gaze_deg": [0.0, 0.0]}
                    for n, _ in ROWS]}
    jp = os.path.join(out, "job.json")
    json.dump(job, open(jp, "w"), indent=1)
    with open(os.path.join(out, "render_log.txt"), "w") as f:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup", "-P",
                        os.path.join(ROOT, "docs/evaluation/characters/T-113/expr_sheet.py"), "--", jp],
                       stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, check=True)
    nrow = -(-len(ROWS) // PER_ROW)
    sheet = Image.new("RGB", (2 * T * PER_ROW, 22 + nrow * (T + HEAD)), (92, 92, 96))
    d = ImageDraw.Draw(sheet)
    d.text((6, 5), f"T-126a girl_white_hair_blue_dress 0.1.0 expressions | pairs: reference (04 / 14) | build | "
                   f"character_neutral/1, Cycles {a.samples} spp", fill=(240, 240, 240))
    for i, (name, ref) in enumerate(ROWS):
        x, y = (i % PER_ROW) * 2 * T, 22 + (i // PER_ROW) * (T + HEAD)
        for j, p in enumerate((os.path.join(VIEWS, ref + ".jpg"), os.path.join(out, name, "c.png"))):
            if os.path.exists(p):
                im = Image.open(p).convert("RGB")
                s = min(T / im.width, T / im.height)
                im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
                sheet.paste(im, (x + j * T + (T - im.width) // 2, y + HEAD + (T - im.height) // 2))
        d.rectangle((x, y, x + 2 * T - 1, y + HEAD - 1), fill=(20, 20, 20))
        d.text((x + 4, y + 2), f"{name}  (ref {ref})", fill=(240, 240, 240))
    path = os.path.join(out, "expressions.jpg")
    sheet.save(path, quality=88)
    print(path, sheet.size, "missing:", open(os.path.join(out, "missing.json")).read().strip())


if __name__ == "__main__":
    main()
