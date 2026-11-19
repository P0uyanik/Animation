"""T-120 evidence: before/after strips of the e911 gaze check in the shot camera (not part of the pipeline).

    python3 docs/evaluation/animation/T-120/make_strip.py

Reads the run_shot frames of episodes/e911_gaze_check/shots/s010_default and s010_legible (build/render/, 640x360,
Cycles 10 spp) and writes t120_before_after_strip.jpg (whole frames) and t120_faces_strip.jpg (both faces, the same
pixels enlarged 2x). Top row: engine default gaze; bottom row: "gazeLegibility" on.
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SHOTS = os.path.join(ROOT, "episodes", "e911_gaze_check", "shots")
FRAMES = [(18, "f18 cup look: he picks up"), (24, "f24 cup look: she notices"), (36, "f36 partner look: he looks at her"),
          (48, "f48 shared hold: he looks at the cup"), (54, "f54 partner looks: both"), (58, "f58 she looks at him; he blinks")]
ROWS = [("s010_default", "default"), ("s010_legible", "gazeLegibility")]
FACES = (120, 20, 540, 230)  # both heads in the 640x360 frame
BAR = 22


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def sheet(out, crop, scale):
    cells = []
    for shot, label in ROWS:
        row = []
        for frame, what in FRAMES:
            im = Image.open(os.path.join(SHOTS, shot, "build", "render", "frame_%04d.png" % frame)).convert("RGB")
            if crop:
                im = im.crop(crop)
            if scale != 1:
                im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
            row.append((im, "%s | %s" % (label, what)))
        cells.append(row)
    w, h = cells[0][0][0].size
    canvas = Image.new("RGB", (w * len(FRAMES), (h + BAR) * len(ROWS)), (24, 24, 24))
    draw, f = ImageDraw.Draw(canvas), font(13)
    for r, row in enumerate(cells):
        for c, (im, text) in enumerate(row):
            canvas.paste(im, (c * w, r * (h + BAR) + BAR))
            draw.text((c * w + 6, r * (h + BAR) + 3), text, fill=(235, 235, 235), font=f)
    canvas.save(out, quality=90)
    print("wrote", os.path.relpath(out, ROOT), canvas.size)


if __name__ == "__main__":
    sheet(os.path.join(HERE, "t120_before_after_strip.jpg"), None, 0.75)
    sheet(os.path.join(HERE, "t120_faces_strip.jpg"), FACES, 2)
