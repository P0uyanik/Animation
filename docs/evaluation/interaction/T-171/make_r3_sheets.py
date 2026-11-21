"""T-171 round 3 evidence from the frames of render_close.py (views hi, bk, shot; see ROUND.md). Tiles of a row share
one camera and one frame and are only scaled, never cropped, except the shot-size row: the same pixel box of the
shot-camera frame for every column, enlarged 3x with nearest-neighbour.

python3 make_r3_sheets.py <build dir> <out dir> --shot-crop x y w h
Columns: r3_base | r3_r3site | r3_r3 (folders under the build dir, each with views/v_<view>_f<frame>.png)."""
import argparse
import os
import subprocess
import tempfile

from PIL import Image

from make_sheets import grid, label

COLS = [("base", "current default"), ("r3site", "fixed, authored grasp point (thumb down)"), ("r3", "fixed, thumb up")]
STRICT = [64, 68, 70, 72, 74, 76, 80, 84]
BACK = [70, 76, 84]
SHOT = [76, 84]
CLIP = range(62, 85)


def tile(build, v, view, f, size):
    return Image.open(os.path.join(build, f"r3_{v}", "views", f"v_{view}_f{f:04d}.png")).convert("RGB").resize(size, Image.LANCZOS)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("build")
    ap.add_argument("out")
    ap.add_argument("--shot-crop", type=int, nargs=4, default=(330, 170, 160, 120))
    a = ap.parse_args()
    rows = [[label(tile(a.build, v, "hi", f, (400, 300)), f"f{f} {name}") for v, name in COLS] for f in STRICT]
    grid(rows, os.path.join(a.out, "r3_strict_pickup.jpg"), "T-171 round 3: e910 s010 pick-up, boy R. Cycles 12 spp, one camera (from above the boy's right), contact f76")
    rows = [[label(tile(a.build, v, "bk", f, (400, 300)), f"f{f} from behind: {name}") for v, name in COLS] for f in BACK]
    x, y, w, h = a.shot_crop
    for f in SHOT:
        row = []
        for v, name in COLS:
            im = Image.open(os.path.join(a.build, f"r3_{v}", "views", f"v_shot_f{f:04d}.png")).convert("RGB")
            box = im.crop((x, y, x + w, y + h)).resize((3 * w, 3 * h), Image.NEAREST).resize((400, 300), Image.NEAREST)
            row.append(label(box, f"f{f} shot camera, {w}x{h} px of 960x540: {name}"))
        rows.append(row)
    grid(rows, os.path.join(a.out, "r3_back_shot.jpg"), "T-171 round 3: from behind (the thumb-up hand's fingers) and what the shot camera shows")
    with tempfile.TemporaryDirectory() as d:
        for i, f in enumerate(CLIP):
            r = [label(tile(a.build, v, "hi", f, (400, 300)), f"f{f} {name}") for v, name in COLS]
            fr = Image.new("RGB", (1200, r[0].height))
            for c, t in enumerate(r):
                fr.paste(t, (400 * c, 0))
            fr.save(os.path.join(d, f"c{i:03d}.png"))
        os.makedirs(os.path.join(a.out, "clips"), exist_ok=True)
        for fps in (24, 8):
            out = os.path.join(a.out, "clips", f"r3_pickup_f62-84_{fps}fps.mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(d, "c%03d.png"), "-vf",
                            "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out], check=True)
            print(out)
