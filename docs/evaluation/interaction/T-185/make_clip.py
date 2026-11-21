"""T-185 review clip: columns side by side (the same camera and frame per row of pixels, only labelled), encoded with
ffmpeg at 24 fps (real time) and 8 fps (3x slow). The kit has no clip tool; frames come from render_views.sh.
    python3 make_clip.py <out.mp4 stem> <from> <to> <label>=<views dir> [<label>=<views dir> ...] [--view shotz]"""
import argparse, os, subprocess, tempfile

from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("stem"); ap.add_argument("a", type=int); ap.add_argument("b", type=int); ap.add_argument("cols", nargs="+")
ap.add_argument("--view", default="shotz")
a = ap.parse_args()
cols = [c.split("=", 1) for c in a.cols]
HEAD = 18
with tempfile.TemporaryDirectory() as tmp:
    for i, f in enumerate(range(a.a, a.b + 1)):
        ims = [Image.open(os.path.join(d, f"v_{a.view}_f{f:04d}.png")).convert("RGB") for _, d in cols]
        w, h = ims[0].size
        out = Image.new("RGB", (w * len(ims) + 4 * (len(ims) - 1), h + HEAD), (20, 20, 20))
        dr = ImageDraw.Draw(out)
        for k, ((label, _), im) in enumerate(zip(cols, ims)):
            out.paste(im, (k * (w + 4), HEAD))
            dr.text((k * (w + 4) + 4, 3), f"{label}  f{f}", fill=(240, 240, 240))
        out.save(os.path.join(tmp, f"{i:04d}.png"))
    for fps in (24, 8):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(tmp, "%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", f"{a.stem}_{fps}fps.mp4"], check=True)
        print(f"{a.stem}_{fps}fps.mp4")
