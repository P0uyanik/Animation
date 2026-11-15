"""T-003 evidence sheets from e902 renders (python3 + Pillow).

    python3 pipeline/clips/emotion_sheets.py --r320 <dir of 320x180 frames> --r640 <dir of 640x360 frames> --out <dir>

Inputs are run_shot.py renders of episodes/e902_emotion_test/shots/s010 at the peak frames listed in the shot's
"x_t003" block (frame_NNNN.png), plus frame 1 (neutral). Writes:
  contact_sheet.png        rows boy / girl, columns neutral + every emotion at its peak (320x180 renders, halves)
  faces_girl_vs_ref34.png  girl face crops (640x360 renders) beside the matching tile of reference #34
  faces_boy_vs_ref28.png   boy face crops beside the matching tile of reference #28
Reference tiles without a matching emotion are marked "nearest" or "none". Crop boxes are for the e902 camera."""
import argparse
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SHOT = os.path.join(ROOT, "episodes", "e902_emotion_test", "shots", "s010", "shot.scene.json")
REF34 = os.path.join(ROOT, "assets", "characters", "girl_auburn_bun_glasses", "references", "uploads", "ref_34.webp")
REF28 = os.path.join(ROOT, "docs", "references", "boy_pipeline", "28_boy_facial_expression_library.webp")
FACE = {"boy": (140, 20, 300, 180), "girl": (350, 15, 510, 175)}  # 640x360 e902 frame
# #34 blendshape matrix tiles (column, label y on the 597-wide preview; x2.5 for the 1493-wide original)
T34 = {"happy": (0, 411, "Smile"), "happy/laugh": (0, 790, "Laugh"), "sad": (1, 600, "Sadness"), "sad/cry": (1, 600, "Sadness"),
       "angry": (0, 695, "Anger"), "surprised": (1, 506, "Surprise"), "confused": (1, 695, "Confusion"),
       "afraid": (1, 317, "nearest: Wide-Open"), "sleepy": (0, 317, "nearest: Squint"), "curious": None}
# #28 grid tiles (row, column, label)
T28 = {"happy": (0, 1, "02 Happy"), "happy/laugh": (3, 1, "nearest: 10 Excited"), "sad": (0, 2, "03 Sad"),
       "sad/cry": (0, 2, "nearest: 03 Sad"), "angry": (1, 0, "05 Angry"), "surprised": (0, 3, "04 Surprised"),
       "confused": (1, 2, "07 Confused"), "afraid": (1, 1, "nearest: 06 Worried"), "sleepy": (3, 0, "09 Sleepy"),
       "curious": (1, 3, "08 Curious")}


def tile34(im, spec):
    col, ly, _ = spec
    x0 = (427, 512)[col]
    return im.crop((int(x0 * 2.5), int((ly - 86) * 2.5), int((x0 + 80) * 2.5), int((ly - 10) * 2.5)))


def tile28(im, spec):
    r, c, _ = spec
    x0, y0 = (33, 170, 307, 444)[c], (65, 248, 431, 614)[r]
    return im.crop((int(x0 * 2.5), int(y0 * 2.5), int((x0 + 127) * 2.5), int((y0 + 150) * 2.5)))


def label(img, text, h=16):
    out = Image.new("RGB", (img.width, img.height + h), "white")
    out.paste(img, (0, h))
    ImageDraw.Draw(out).text((3, 2), text, fill="black")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--r320", required=True)
    ap.add_argument("--r640", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    peaks = [(1, "neutral (frame 1)")] + [(p["peak"], p["emotion"]) for p in json.load(open(SHOT))["x_t003"]["peaks"]]
    # contact sheet: each 320x180 frame split into the boy (left) and girl (right) halves
    cw, ch = 160, 180
    sheet = Image.new("RGB", (cw * len(peaks), 2 * (ch + 16)), "white")
    for i, (f, name) in enumerate(peaks):
        im = Image.open(os.path.join(a.r320, f"frame_{f:04d}.png")).convert("RGB")
        for row, box in enumerate(((0, 0, 160, 180), (160, 0, 320, 180))):
            sheet.paste(label(im.crop(box), f"{name} f{f}" if row == 0 else f"{name}"), (i * cw, row * (ch + 16)))
    sheet.save(os.path.join(a.out, "contact_sheet.png"))
    for who, ref, table, tile in (("girl", REF34, T34, tile34), ("boy", REF28, T28, tile28)):
        rim = Image.open(ref).convert("RGB")
        cells = []
        for f, name in peaks[1:]:
            face = Image.open(os.path.join(a.r640, f"frame_{f:04d}.png")).convert("RGB").crop(FACE[who]).resize((240, 240))
            spec = table[name]
            r = tile(rim, spec).resize((240, 240)) if spec else Image.new("RGB", (240, 240), (235, 235, 235))
            pair = Image.new("RGB", (480, 240), "white")
            pair.paste(face, (0, 0))
            pair.paste(r, (240, 0))
            cells.append(label(pair, f"{name} (render f{f}) | ref: {spec[-1] if spec else 'none'}", 18))
        cols = 2
        rows = (len(cells) + cols - 1) // cols
        out = Image.new("RGB", (cols * 480, rows * 258), "white")
        for k, c in enumerate(cells):
            out.paste(c, ((k % cols) * 480, (k // cols) * 258))
        out.save(os.path.join(a.out, f"faces_{who}_vs_ref{'34' if who == 'girl' else '28'}.png"))
    print("written to", a.out)


if __name__ == "__main__":
    main()
