"""Build frame-labelled owner evidence directly from the two reference files."""

import argparse
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageOps

from measure import EVALUATION, ROOT, VIDEO_HASHES, bounds, digest, eye_anchor
from observations import EYELIDS
from reference import ANCHORS, DISPLAY

PAPER = "paperboat"
WATER = "watertable"
CAST = {"boy": "Boy", "girl": "Girl with glasses", "white_haired_girl": "White-haired girl"}
CONTEXT = {
    PAPER: [(0,"Paper at desk"), (64,"Corner creased"), (140,"Fold held"),
            (175,"Water contact"), (222,"Waterline glow"), (280,"Reaction revealed")],
    WATER: [(0,"Hand at chin"), (17,"Hand leaves chin"), (33,"Point extends"),
            (56,"Point sustained"), (83,"Straightening"), (120,"Arms at rest")],
}
DETAIL = {
    (PAPER,"boy"): [(0,"Heavy lids"), (25,"Gaze held low"), (128,"Partial lid dip"),
                    (267,"Looks into tub"), (288,"Light reaction")],
    (PAPER,"girl"): [(12,"Eyes on paper"), (123,"Lower eye line"), (132,"Eyes lift slightly"),
                     (265,"Open smile"), (288,"Leans on rim")],
    (PAPER,"white_haired_girl"): [(6,"First closure"), (125,"Second closure"),
                                 (146,"Watches fold"), (246,"Reveal blink"), (288,"Lips parted")],
    (WATER,"boy"): [(0,"Looks right"), (22,"First blink"), (62,"Second blink"),
                    (83,"Third blink"), (116,"Raised head hold")],
    (WATER,"girl"): [(0,"Rounded mouth"), (17,"Eyes close"), (42,"Points down"),
                     (82,"Recovery blink"), (120,"Settled smile")],
    (WATER,"white_haired_girl"): [(0,"Lips parted"), (21,"First closure"), (57,"Second closure"),
                                  (77,"Head raised"), (115,"More frontal gaze")],
}
BG, INK, SUB, LINE = "#f9f7f1", "#222c2d", "#465a58", "#c4c9c0"
WIDTH = 1440


def label(draw, xy, text, size, color=INK):
    draw.text(xy, text, font=ImageFont.load_default(size=size), fill=color)


def read_frames(directory, clip, indices):
    path = directory / f"video_{clip}.mp4"
    if digest(path) != VIDEO_HASHES[clip]:
        raise ValueError(f"{path}: video differs from the annotated reference")
    cap = cv2.VideoCapture(str(path))
    frames = {}
    try:
        for i in range(max(indices)+1):
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"{clip}: missing frame {i}")
            if i in indices:
                frames[i] = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    finally:
        cap.release()
    return frames


def face_crop(img, clip, cast, i, lids=False):
    scale = tuple(src/ref for src, ref in zip(img.size, DISPLAY[clip]))
    anchor = next(a for (name, _, who), knots in ANCHORS.items()
                  if (name, who) == (clip, cast) and (a := eye_anchor(knots, i, scale)))
    # For clipped foreheads, preserve the actual source border.
    margins = (.50, .20, .23) if lids else (.69, .45, .48)
    rect = bounds(anchor, (img.height, img.width), *margins)
    return img.crop(rect)


def panel(sheet, image, x, y, width, height):
    image = ImageOps.contain(image, (width, height), Image.Resampling.LANCZOS)
    sheet.paste(image, (x + (width-image.width)//2, y + (height-image.height)//2))


def acting_sheet(directory, clip, frames):
    sheet = Image.new("RGB", (WIDTH, 1200), BG)
    d = ImageDraw.Draw(sheet)
    label(d, (28, 17), clip.title() + "  /  Reference performance", 38)
    label(d, (30, 73), "Source frames at 24 fps   |   " + ("Shot sequence" if clip == PAPER else "One continuous shot"), 20, SUB)
    for col, (i, caption) in enumerate(CONTEXT[clip]):
        x = 28 + col*232
        panel(sheet, frames[i], x, 107, 221, 200)
        label(d, (x, 315), f"f{i:03d}   {caption}", 16)
    for row, (cast, title) in enumerate(CAST.items()):
        y = 360 + row*275
        d.line((28, y, WIDTH-28, y), fill=LINE, width=2)
        label(d, (28, y+9), title, 26)
        for col, (i, caption) in enumerate(DETAIL[clip,cast]):
            x = 28 + col*279
            face = face_crop(frames[i], clip, cast, i)
            panel(sheet, face, x, y+49, 262, 175)
            label(d, (x, y+234), f"f{i:03d}   {caption}", 18)
    sheet.save(directory / f"{clip}.jpg", quality=85, optimize=True)


def blink_sheet(directory, clips):
    events = [(clip, cast, *event) for (clip, cast), spans in EYELIDS.items() for event in spans]
    sheet = Image.new("RGB", (WIDTH, 110 + 210*((len(events)+2)//3)), BG)
    d = ImageDraw.Draw(sheet)
    label(d, (28, 15), "Eyelid closures and partial dips", 36)
    label(d, (30, 67), "Each triplet shows the preceding frame, minimum aperture and recovered frame. Partial dips are excluded from the rate.", 20, SUB)
    for index, (clip, cast, first, peak, end, kind) in enumerate(events):
        x, y = 28 + index%3*467, 111 + index//3*210
        d.line((x, y, x+442, y), fill=LINE, width=2)
        label(d, (x, y+10), clip.title()+"  /  "+CAST[cast], 21)
        label(d, (x, y+42), f"{kind.title()}   [{first}, {end})   {end-first} frames", 17, SUB)
        for col, i in enumerate((first-1, peak, end)):
            eye = face_crop(clips[clip][i], clip, cast, i, lids=True)
            panel(sheet, eye, x+col*149, y+72, 144, 79)
            label(d, (x+col*149, y+156), f"f{i:03d}", 17)
    sheet.save(directory / "eyelids.jpg", quality=87, optimize=True)


def render(references, directory):
    directory.mkdir(parents=True, exist_ok=True)
    clips = {}
    for clip in CONTEXT:
        indices = {i for i, _ in CONTEXT[clip]}
        for cast in CAST:
            indices.update(i for i, _ in DETAIL[clip,cast])
            for first, peak, end, _ in EYELIDS[clip,cast]:
                indices.update((first-1, peak, end))
        clips[clip] = read_frames(references, clip, indices)
        acting_sheet(directory, clip, clips[clip])
    blink_sheet(directory, clips)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, default=ROOT / "docs/references")
    parser.add_argument("--out", type=Path, default=EVALUATION)
    args = parser.parse_args()
    render(args.references, args.out)
