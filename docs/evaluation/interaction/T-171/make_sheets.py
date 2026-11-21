"""T-171 evidence sheets from render_views.sh output. Tiles of a row share one camera and one frame and are only scaled
(the same factor across the row), never cropped - except the shot-size sheet, whose point is the crop: the same pixel
box of the 1280x720 shot-camera frame for every column, enlarged 3x with nearest-neighbour (what the shot shows).

python3 make_sheets.py <build dir> <out dir> --cols base:"current default" r2s:"T-171 opt-in" ... \
    --frames 64,68,72,74,76,78,80,82 --crop x y w h --rest-crop x y w h [--ref docs/references/video_paperboat.mp4]
"""
import argparse
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw

BG, BAR, TXT = (92, 92, 96), (20, 20, 20), (240, 240, 240)
HEAD = 18


def label(im, text):
    c = Image.new("RGB", (im.width, im.height + HEAD), BG)
    c.paste(im, (0, HEAD))
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, im.width, HEAD - 1), fill=BAR)
    d.text((4, 3), text, fill=TXT)
    return c


def grid(rows, path, title):
    w = max(sum(t.width for t in r) for r in rows)
    h = sum(max(t.height for t in r) for r in rows)
    sheet = Image.new("RGB", (w, h + 24), BG)
    d = ImageDraw.Draw(sheet)
    d.rectangle((0, 0, w, 23), fill=BAR)
    d.text((6, 6), title, fill=TXT)
    y = 24
    for r in rows:
        x = 0
        for t in r:
            sheet.paste(t, (x, y))
            x += t.width
        y += max(t.height for t in r)
    sheet.save(path, quality=90)
    print(path, sheet.size)


def ref_frames(video, t0, n, step, crop):
    """n frames of the reference video from t0 (s), every `step` frames, cropped (x, y, w, h)."""
    out = []
    with tempfile.TemporaryDirectory() as d:
        x, y, w, h = crop
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-i", video, "-vf",
                        f"select='not(mod(n,{step}))',crop={w}:{h}:{x}:{y}", "-vsync", "0", "-frames:v", str(n),
                        os.path.join(d, "r%02d.png")], check=True)
        for i in range(1, n + 1):
            p = os.path.join(d, f"r{i:02d}.png")
            if os.path.exists(p):
                out.append(Image.open(p).convert("RGB").copy())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build")
    ap.add_argument("out")
    ap.add_argument("--cols", nargs="+", required=True, help="variant:label (variant dir = <build>/t171_<variant>)")
    ap.add_argument("--frames", required=True)
    ap.add_argument("--crop", type=int, nargs=4, default=None, help="shot-size crop box x y w h in the 1280x720 frame")
    ap.add_argument("--rest-crop", type=int, nargs=4, default=None, help="the same for the resting hand (f44)")
    ap.add_argument("--ref", default=None)
    ap.add_argument("--tile-w", type=int, default=400)
    a = ap.parse_args()
    cols = [c.split(":", 1) for c in a.cols]
    frames = [int(f) for f in a.frames.split(",")]
    os.makedirs(a.out, exist_ok=True)

    def view(variant, tag, name, f):
        d = os.path.join(a.build, "t171_site", "t171_r2site") if variant == "r2site" else os.path.join(a.build, f"t171_{variant}")
        return Image.open(os.path.join(d, "views", f"{tag}_{name}_f{f:04d}.png")).convert("RGB")

    def tiles(view_name, frames_, w):
        rows = []
        for f in frames_:
            row = []
            for v, text in cols:
                im = view(v, "v", view_name, f)
                row.append(label(im.resize((w, round(im.height * w / im.width)), Image.LANCZOS), f"f{f}  {text}"))
            rows.append(row)
        return rows

    head = "T-171 hands round 2 - e910 s010 boy R - one frame per row, same camera, tiles scaled only - "
    grid(tiles("left", frames, a.tile_w), os.path.join(a.out, "strict_reach_close.jpg"), head + "camera 'left' (fingers on the cup)")
    grid(tiles("close", [70, 76, 78, 81], a.tile_w) + tiles("rest", [44], a.tile_w), os.path.join(a.out, "strict_back_rest.jpg"),
         head + "camera 'close' (back of the hand), last row: the hand at rest f44")
    if a.crop:
        rows = []
        for f, (x, y, w, h) in ((44, a.rest_crop), (70, a.crop), (76, a.crop), (81, a.crop)):
            row = []
            for v, text in cols:
                im = view(v, "v", "shot", f).crop((x, y, x + w, y + h)).resize((w * 3, h * 3), Image.NEAREST)
                row.append(label(im, f"f{f}  {text}"))
            rows.append(row)
        grid(rows, os.path.join(a.out, "shot_size.jpg"), "T-171 shot size: a pixel box of the 1280x720 shot camera, 3x nearest (same box across a row)")
    if a.ref:
        # Reference-matched reach: the boy's hand comes in over the paper (video_paperboat.mp4, 1.95 s on, every frame).
        refs = ref_frames(a.ref, 1.95, 10, 1, (500, 180, 354, 266))
        rows = [[label(r.resize((a.tile_w, round(r.height * a.tile_w / r.width)), Image.LANCZOS), f"reference +{i} fr") for i, r in enumerate(refs[:5])],
                [label(r.resize((a.tile_w, round(r.height * a.tile_w / r.width)), Image.LANCZOS), f"reference +{i + 5} fr") for i, r in enumerate(refs[5:])]]
        grid(rows, os.path.join(a.out, "reference_reach.jpg"), "video_paperboat.mp4: the reach the timing is matched to (24 fps, consecutive frames)")


main()
