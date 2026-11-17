"""T-040: contact sheet with arm close-ups (python3 + Pillow).

    python3 docs/evaluation/animation/T-040/contact_sheet_t040.py --run <run dir> --build <shot build dir> \
        --measure <measure_t040 json> --frames 1,8,23,44,73,75 --out <png>

Per frame: the full render, then per character a left and a right arm close-up (forearm/hand midpoint, projected
from the baked bones as in the batch-1 sheet), labelled with that frame's mesh distance of the arm (measure_t040.cpp,
rest-relative, post-pass on) and the post-pass shoulder correction."""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "T-030"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "pipeline", "clips"))
from contact_sheet import bone_world  # noqa: E402  (T-030)
from t022_contact_sheet import project  # noqa: E402

FULL, TILE = (320, 180), 150


def crop(im, cx, cy, half, label, bad):
    c = im.crop((int(cx - half), int(cy - half), int(cx + half), int(cy + half))).resize((TILE, TILE), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, TILE, 12), fill=(140, 0, 0) if bad else (0, 0, 0))
    d.text((2, 0), label, fill=(255, 255, 255))
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--build", required=True)
    ap.add_argument("--measure", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    bake = json.load(open(os.path.join(a.run, "bake.json")))
    cast = json.load(open(os.path.join(a.build, "cast.json")))
    meas = json.load(open(a.measure))["characters"]
    fdata = {fd["frame"]: fd for fd in bake["frame_data"]}
    chars = [c["name"] for c in bake["characters"] if c.get("supported", True)]
    bones = {c["name"]: c["bones"] for c in bake["characters"]}
    heads = {}
    for n in chars:
        pk = json.load(open(os.path.join(cast[n]["package"], "character.json")))
        heads[n] = {b["name"]: b["head"] for b in pk["skeleton"]}
    frames = [int(x) for x in a.frames.split(",")]
    col_w = max(FULL[0], 2 * (TILE + 2))
    rows_h = len(chars) * (TILE + 2)
    sheet = Image.new("RGB", (col_w * len(frames), 18 + FULL[1] + rows_h), (20, 20, 20))
    ImageDraw.Draw(sheet).text((4, 3), "T-040 e906 s010: arm close-ups (mesh distance, post-pass on; red = inside)",
                               fill=(255, 220, 120))
    for i, f in enumerate(frames):
        im = Image.open(os.path.join(a.run, "render", f"frame_{f:04d}.png")).convert("RGB")
        w, h = im.size
        top = im.resize(FULL, Image.Resampling.LANCZOS)
        d = ImageDraw.Draw(top)
        d.rectangle((0, 0, FULL[0], 14), fill=(0, 0, 0))
        d.text((4, 1), f"f{f}", fill=(255, 255, 255))
        sheet.paste(top, (i * col_w, 18))
        cam = fdata[f]["camera"]
        y = 18 + FULL[1] + 2
        for n in chars:
            for k, side in enumerate("LR"):
                el = bone_world(fdata[f], n, bones[n], heads[n], f"forearm.{side}")
                ha = bone_world(fdata[f], n, bones[n], heads[n], f"hand.{side}")
                m = [(el[j] + ha[j]) / 2 for j in range(3)]
                ax, ay = project(cam, m, w, h)
                row = next((r for r in meas[n][f"arm_{side}"]["frames"] if r["f"] == f), None)
                txt = f"{n} {side} {row['mesh_mm']:+.1f}mm sh{row['shoulder_deg']:.0f}d" if row else f"{n} {side}"
                sheet.paste(crop(im, ax, ay, 0.17 * w / 2, txt, bool(row and row["mesh_mm"] < 0)),
                            (i * col_w + k * (TILE + 2), y))
            y += TILE + 2
    sheet.save(a.out)
    print(a.out, sheet.size)


if __name__ == "__main__":
    main()
