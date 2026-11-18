"""T-095 evidence: the strict frame sheet and the movie of the e907 exchange (python3, Pillow, ffmpeg).

    python3 docs/evaluation/animation/T-095/make_sheet_t095.py --frames <dir with shot_/side_/top_fNNNN.png> \
        [--movie <dir with m_fNNNN.png>] --out docs/evaluation/animation/T-095

Rows: shot camera, diagnostic side view (raised, from the girl's side), top view; columns: pick-up f18, approach f36,
both hands share the cup f48 (accepted frame), release f53. A reference row underneath: PB f12, PB f157, PB f272,
WT f24 (docs/references/*.mp4, zero-based frame indices). The movie: the shot camera f1..f66 at 24 fps."""
import argparse
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
COLS = [(18, "f18 pick-up (his contact)"), (36, "f36 approach (her reach)"), (48, "f48 both hands share the cup"),
        (53, "f53 release")]
ROWS = [("shot", "shot camera"), ("side", "side view (diagnostic)"), ("top", "top view (diagnostic)")]
REFS = [("video_paperboat.mp4", 12, "PB f12"), ("video_paperboat.mp4", 157, "PB f157"),
        ("video_paperboat.mp4", 272, "PB f272"), ("video_watertable.mp4", 24, "WT f24")]
W, H = 480, 270


def ref_frame(video, n, tmp):
    out = os.path.join(tmp, f"{video}_{n}.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(ROOT, "docs", "references", video),
                    "-vf", f"select=eq(n\\,{n})", "-vframes", "1", out], check=True)
    return Image.open(out).convert("RGB")


def fit(im):
    im = im.copy()
    im.thumbnail((W, H))
    c = Image.new("RGB", (W, H), "white")
    c.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    return c


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 8 + 6 * len(text), 16], fill=(255, 255, 255))
    d.text((4, 3), text, fill=(0, 0, 0))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--movie")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sheet = Image.new("RGB", (W * 4, H * 4 + 24), "white")
    for r, (tag, rname) in enumerate(ROWS):
        for c, (f, cname) in enumerate(COLS):
            im = fit(Image.open(os.path.join(a.frames, f"{tag}_f{f:04d}.png")).convert("RGB"))
            sheet.paste(label(im, f"{rname} | {cname}"), (c * W, r * H))
    with tempfile.TemporaryDirectory() as tmp:
        for c, (video, n, name) in enumerate(REFS):
            sheet.paste(label(fit(ref_frame(video, n, tmp)), f"reference {name}"), (c * W, 3 * H + 24))
    ImageDraw.Draw(sheet).text((6, 3 * H + 6), "References (owner videos, zero-based frames): the target for staging, "
                               "faces and spacing", fill=(0, 0, 0))
    out = os.path.join(a.out, "t095_exchange_strict_sheet.jpg")
    sheet.save(out, quality=90)
    print(out)
    if a.movie:
        mp4 = os.path.join(a.out, "t095_exchange_shot_camera.mp4")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "24", "-start_number", "1", "-i",
                        os.path.join(a.movie, "m_f%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
                        mp4], check=True)
        print(mp4)


if __name__ == "__main__":
    main()
