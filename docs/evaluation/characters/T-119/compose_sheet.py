"""T-119: lays the pose_shots.py tiles out as a strict sheet (T-087 tile style, tools/review/strict_sheet.py).

    python3 docs/evaluation/characters/T-119/compose_sheet.py <shots dir> <out.jpg> "<title>"

Columns: the labels of shots.json in the order rendered (current | candidate); one row per shot. Every tile of a row is
the same camera and light, rendered in the same run; tiles are only scaled, never cropped."""
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "review"))
import strict_sheet as SS  # noqa: E402


def main():
    src, out, title = sys.argv[1], sys.argv[2], sys.argv[3]
    rec = json.load(open(os.path.join(src, "shots.json")))
    cols = [c["label"] for c in rec["columns"]]
    w = h = 360 + SS.HEAD_H if rec["px"] >= 300 else 200 + SS.HEAD_H
    sheet = Image.new("RGB", (len(cols) * w, SS.TITLE_H + len(rec["shots"]) * h), SS.BG)
    d = ImageDraw.Draw(sheet)
    d.rectangle((0, 0, sheet.width, SS.TITLE_H - 1), fill=SS.BAR)
    d.text((6, 6), f"{title} | {rec['engine']} {rec['samples']} spp, {rec['px']} px, {rec['light']}"[:int(sheet.width / 6.2)],
           fill=SS.TXT)
    for r, shot in enumerate(rec["shots"]):
        for c, label in enumerate(cols):
            im = Image.open(os.path.join(src, label, shot["name"] + ".png"))
            sheet.paste(SS.tile(im, w, h, f"{label} | {shot['label']}"[:int(w / 6.2)]), (c * w, SS.TITLE_H + r * h))
    sheet.save(out, quality=90)
    print(out, sheet.size)


main()
