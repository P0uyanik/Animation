"""T-175 sheet helper: crops rendered frames around one character (the crop follows the character through the shot).

    python3 docs/evaluation/animation/T-175/track_crops.py --bake <run>/bake.json --frames-dir <run>/render \
        --character boy --out <dir> --frames 1,7,13,19

Writes <out>/frame_NNNN.png: a square of `--size` metres (default 0.9) centred on the character's hips, projected with
the bake's camera (tools/motion_checks/shot.py), scaled to 360 px. The sheets themselves are made by
tools/review/shot_sheet.py (columns: full frame | tracked crop)."""
import argparse
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "motion_checks"))
import shot as SHOT  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", required=True)
    ap.add_argument("--frames-dir", required=True)
    ap.add_argument("--character", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--size", type=float, default=0.9)
    a = ap.parse_args()
    sh = SHOT.Shot(a.bake)
    ch = next(c for c in sh.characters if c.name == a.character)
    piv = ch.pivots()
    hips = ch.bones.index("hips")
    frames = list(sh.frames)
    os.makedirs(a.out, exist_ok=True)
    for f in (int(x) for x in a.frames.split(",")):
        im = Image.open(os.path.join(a.frames_dir, f"frame_{f:04d}.png")).convert("RGB")
        i = frames.index(f)
        p = piv[i, hips].copy()
        p[1] = 0.33  # a fixed height, so the crop shows the body rising and sinking
        c = SHOT.project(sh.cameras[i], p, im.width, im.height)
        up = SHOT.project(sh.cameras[i], p + [0, a.size / 2, 0], im.width, im.height)
        half = abs(c[1] - up[1])
        box = [round(c[0] - half), round(c[1] - half), round(c[0] + half), round(c[1] + half)]
        im.crop(box).resize((360, 360), Image.LANCZOS).save(os.path.join(a.out, f"frame_{f:04d}.png"))
    print(a.out)


main()
