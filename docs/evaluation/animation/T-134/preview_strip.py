"""T-134 preview strip: the same frames of two bakes of one shot (before above, after below), cheap Cycles previews.

Usage: python3 preview_strip.py --blender <blender> --cast <shot>/build/cast.json --before <bake.json> --after <bake.json>
           --frames 52,58,62 --work <scratch dir> --out strip.jpg [--label-after "E1a"] [--samples 8]
Frames already rendered in --work are reused."""
import argparse
import os
import subprocess

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def render(blender, cast, bake, out, frame, samples):
    png = os.path.join(out, f"frame_{frame:04d}.png")
    if not os.path.exists(png):
        os.makedirs(out, exist_ok=True)
        subprocess.run([blender, "-b", "--factory-startup", "-P", os.path.join(ROOT, "pipeline", "charsys", "shot_render.py"), "--",
                        "--bake", bake, "--cast", cast, "--out", out, "--samples", str(samples), "--resolution", "480", "270",
                        "--frames", f"{frame}-{frame}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return Image.open(png).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    for k in ("blender", "cast", "before", "after", "frames", "work", "out"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--label-after", default="after")
    ap.add_argument("--samples", type=int, default=8)
    a = ap.parse_args()
    frames = [int(f) for f in a.frames.split(",")]
    rows = [("before", a.before, os.path.join(a.work, "before")), (a.label_after, a.after, os.path.join(a.work, a.label_after))]
    w, h = 240, 135
    sheet = Image.new("RGB", (w * len(frames), h * len(rows)), "black")
    draw = ImageDraw.Draw(sheet)
    for r, (label, bake, out) in enumerate(rows):
        for c, f in enumerate(frames):
            sheet.paste(render(a.blender, a.cast, bake, out, f, a.samples).resize((w, h), Image.LANCZOS), (c * w, r * h))
            draw.rectangle([c * w, r * h, c * w + 78, r * h + 12], fill="black")
            draw.text((c * w + 2, r * h + 1), f"{label} f{f}", fill="white")
    sheet.save(a.out, quality=88)
    print(a.out)


if __name__ == "__main__":
    main()
