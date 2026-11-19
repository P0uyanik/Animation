"""T-094 exchange strip: the e907 exchange (T-095 s010) at the T-095 sheet beats, current versions (from T-095's own
movie, boy 2.0.0 / girl 0.11.0) above the T-094 re-render (boy 2.1.0 / girl 0.12.0, pinned). Both are the same shot,
shot camera, Cycles 10 spp, 640x360.

    python3 docs/evaluation/characters/T-094/exchange/make_strip.py [--render <dir with frame_NNNN.png>]

Default render dir: docs/evaluation/characters/T-094/exchange/build/render (run_shot output, not committed)."""
import argparse
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))  # exchange/T-094/characters/evaluation/docs
OLD_MOVIE = os.path.join(ROOT, "docs", "evaluation", "animation", "T-095", "t095_exchange_shot_camera.mp4")
FRAMES = [(18, "f18 pick-up"), (36, "f36 approach"), (48, "f48 both hands share the cup"), (53, "f53 release")]
W, H, LABEL = 480, 270, 22


def old_frame(n, tmp):
    out = os.path.join(tmp, f"old_{n:04d}.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", OLD_MOVIE, "-vf", f"select=eq(n\\,{n - 1})",
                    "-frames:v", "1", out], check=True)
    return Image.open(out).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", default=os.path.join(HERE, "build", "render"))
    a = ap.parse_args()
    rows = [("current: boy 2.0.0, girl 0.11.0 (T-095 movie)", None),
            ("T-094: boy 2.1.0, girl 0.12.0 (published, not current)", a.render)]
    sheet = Image.new("RGB", (W * len(FRAMES), (H + LABEL) * len(rows) + LABEL), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    d.text((6, 5), "e907 exchange (T-095 s010), shot camera, Cycles 10 spp; same shot, cast changed only", fill="white")
    with tempfile.TemporaryDirectory() as tmp:
        for r, (label, src) in enumerate(rows):
            y = LABEL + r * (H + LABEL)
            for c, (n, beat) in enumerate(FRAMES):
                img = old_frame(n, tmp) if src is None else Image.open(
                    os.path.join(src, f"frame_{n:04d}.png")).convert("RGB")
                sheet.paste(img.resize((W, H), Image.LANCZOS), (c * W, y + LABEL))
                d.text((c * W + 6, y + 5), f"{label} | {beat}", fill="white")
    out = os.path.join(HERE, "t094_exchange_strip.jpg")
    sheet.save(out, quality=88)
    print(out)


if __name__ == "__main__":
    main()
