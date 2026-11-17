"""T-010 evidence sheets from the e903 run (python3 + Pillow + ffmpeg).

    python3 docs/evaluation/animation/T-010/t010_sheets.py --frames <run>/render --gaze <gaze_check.json> --out <dir>

Writes:
  contact_sheet.png       6 frames of the 960x540 render in a 3x2 grid, each labelled with the frame number, the
                          scripted beat and, per character, the largest eye angle relative to the head at that frame
                          (from gaze_check.json, the engine bake; signed, pitch + = up, yaw + = character left)
  eye_strips.png          every frame (1..60), per character, a face crop labelled with the baked eye pitch relative to
                          the head (evidence for "eyes visible in every frame"; crop boxes are for the e903 camera)
  benchmark_compare.png   2 render frames (top) next to 1 frame each of docs/references/video_watertable.mp4 and
                          video_paperboat.mp4 (bottom), each letterboxed into an equal cell, unretouched"""
import argparse
import json
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
REFS = os.path.join(ROOT, "docs", "references")
SHEET = [(1, "start: girl happy, wave begins; boy neutral"), (12, "girl raising arm; boy surprised (onset)"),
         (24, "girl waving; boy surprised -> laugh"), (36, "boy laugh, head pitching down"),
         (44, "boy head pitch down (max, -14 deg)"), (60, "end: wave lowered; boy laugh")]
COMPARE_OURS = [24, 44]
COMPARE_REFS = [("video_watertable.mp4", 60), ("video_paperboat.mp4", 144)]
CELL = (640, 360)
FACE = {"boy": (230, 120, 450, 260), "girl": (520, 105, 740, 245)}  # 960x540 e903 frame


def eye_max(gaze, who, frame):
    """Signed (pitch, yaw) of the eye with the larger angle relative to the head."""
    c = gaze["characters"][who]
    row = next(r for r in c["frames"] if r["frame"] == frame)
    return max(((row[e]["pitch_deg"], row[e]["yaw_deg"]) for e in c["eyes"]), key=lambda v: abs(v[0]) + abs(v[1]))


def label(im, lines, y0=None):
    d = ImageDraw.Draw(im)
    h = 16 * len(lines) + 6
    y0 = im.height - h if y0 is None else y0
    d.rectangle((0, y0, im.width, y0 + h), fill=(0, 0, 0))
    for i, t in enumerate(lines):
        d.text((6, y0 + 3 + 16 * i), t, fill=(255, 255, 255))
    return im


def fit(im, size):
    im = im.convert("RGB")
    s = min(size[0] / im.width, size[1] / im.height)
    r = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    cell = Image.new("RGB", size, (24, 24, 24))
    cell.paste(r, ((size[0] - r.width) // 2, (size[1] - r.height) // 2))
    return cell


def ref_frame(video, n, tmp):
    out = os.path.join(tmp, f"{os.path.splitext(video)[0]}_{n}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(REFS, video), "-vf", f"select=eq(n\\,{n})",
                    "-frames:v", "1", out], check=True)
    return Image.open(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--gaze", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    gaze = json.load(open(a.gaze))
    frame = lambda f: Image.open(os.path.join(a.frames, f"frame_{f:04d}.png")).convert("RGB")
    tiles = []
    for f, beat in SHEET:
        im = fit(frame(f), CELL)
        eyes = "  ".join(f"{w}: eye pitch {eye_max(gaze, w, f)[0]:+.1f} / yaw {eye_max(gaze, w, f)[1]:+.1f} deg" for w in sorted(gaze["characters"]))
        tiles.append(label(im, [f"frame {f}: {beat}", f"rel. head (bake) {eyes}"]))
    sheet = Image.new("RGB", (CELL[0] * 3, CELL[1] * 2))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 3) * CELL[0], (i // 3) * CELL[1]))
    sheet.save(os.path.join(a.out, "contact_sheet.png"))
    with tempfile.TemporaryDirectory() as tmp:
        top = [label(fit(frame(f), CELL), [f"Plush Studio T-010 render, frame {f} (Cycles 960x540)"], 0) for f in COMPARE_OURS]
        bottom = [label(fit(ref_frame(v, n, tmp), CELL), [f"benchmark {v}, frame {n}"], 0) for v, n in COMPARE_REFS]
    cmp_ = Image.new("RGB", (CELL[0] * 2, CELL[1] * 2))
    for i, t in enumerate(top + bottom):
        cmp_.paste(t, ((i % 2) * CELL[0], (i // 2) * CELL[1]))
    cmp_.save(os.path.join(a.out, "benchmark_compare.png"))
    frames = sorted(r["frame"] for r in next(iter(gaze["characters"].values()))["frames"])
    tw, th, cols = 165, 105, 10
    rows = -(-len(frames) // cols)
    strips = Image.new("RGB", (tw * cols, (th * rows + 18) * len(FACE)), (0, 0, 0))
    for k, (who, box) in enumerate(sorted(FACE.items())):
        y0 = k * (th * rows + 18)
        ImageDraw.Draw(strips).text((4, y0 + 3), f"{who}: face crop per frame, eye pitch relative to the head from the bake (+ = up)", fill=(255, 255, 255))
        for i, f in enumerate(frames):
            t = frame(f).crop(box).resize((tw, th), Image.LANCZOS)
            label(t, [f"f{f} eye {eye_max(gaze, who, f)[0]:+.1f}"], 0)
            strips.paste(t, ((i % cols) * tw, y0 + 18 + (i // cols) * th))
    strips.save(os.path.join(a.out, "eye_strips.png"))


if __name__ == "__main__":
    main()
