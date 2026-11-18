"""T-080 owner sheets: reference | 1.1.0 (current approved) | 2.0.0 (candidate).

    python3 docs/evaluation/characters/T-080/make_sheets.py <fid20_sheets_dir> <cu11_dir> <cu20_dir> <out_dir> \
        [<fid20_renders_dir>]

Body views: the reference and the aligned render panel of the fidelity tool's per-view sheets (tools/fidelity,
same cameras, 640 px / 32 spp, character_neutral/1, compare variant = arms down). 1.1.0 = the render panel of the
stored T-064 sheets (docs/evaluation/characters/T-064/boy/sheets, the current fidelity baseline renders); 2.0.0 =
this task's run. Face close-ups: groom_turnaround.py --closeup front / 3/4 (yaw -35), same camera; the 2.0.0
close-ups were rendered with the round-2 hair (face identical in round 3), so with <fid20_renders_dir> the face rows
also get head crops of the round-3 fidelity renders (320 x 640, upscaled; no extra still).
Reference strip: the 2026-11-17 owner turnaround (boy row) and the boy's close-up upload 01."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
T064 = os.path.join(ROOT, "docs/evaluation/characters/T-064/boy/sheets")
TURN = os.path.join(ROOT, "assets/references/owner_uploads/turnaround_all_three_2026-11-17.webp")
UP01 = os.path.join(ROOT, "assets/characters/boy_yellow_hoodie/references/uploads/"
                    "01_closeups_hair_top_crown_face_fleece_2026-11-17.webp")
VIEWS = [("val27_front", "front"), ("val27_threequarter_right", "3/4"), ("val27_side_right", "side"),
         ("val27_back", "back")]
H = 620


def font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def panel(sheet, i):
    """Panel i (0 reference, 1 render) of a fidelity sheet: 4 equal panels between the header and the legend."""
    im = Image.open(sheet).convert("RGB")
    w = im.width / 4
    # content rows: panels start below the 2 header lines and end above the legend (detect the grey/white body)
    box = (int(i * w) + 6, 46, int((i + 1) * w) - 6, im.height - 62)
    return im.crop(box)


def fit(im, h=H):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def row(cells, labels, title):
    cells = [fit(c) for c in cells]
    W = sum(c.width for c in cells) + 12 * (len(cells) + 1)
    out = Image.new("RGB", (W, H + 70), (238, 238, 238))
    d = ImageDraw.Draw(out)
    d.text((12, 8), title, fill=(20, 20, 20), font=font(22))
    x = 12
    for c, lab in zip(cells, labels):
        out.paste(c, (x, 64))
        d.text((x, 38), lab, fill=(40, 40, 40), font=font(18))
        x += c.width + 12
    return out


def stack(rows, path):
    W = max(r.width for r in rows)
    out = Image.new("RGB", (W, sum(r.height for r in rows)), (238, 238, 238))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height
    if out.width > 2048:
        out = out.resize((2048, round(out.height * 2048 / out.width)), Image.LANCZOS)
    out.save(path, quality=88)
    return path


def main():
    fid20, cu11, cu20, out = sys.argv[1:5]
    rend = sys.argv[5] if len(sys.argv) > 5 else None
    head = (50, 55, 270, 275)
    os.makedirs(out, exist_ok=True)
    labels = ["reference (val27, owner)", "1.1.0 current (approved)", "2.0.0 candidate (T-080)"]
    rows = []
    for vid, name in VIEWS:
        r = row([panel(os.path.join(fid20, vid + ".png"), 0), panel(os.path.join(T064, vid + ".png"), 1),
                 panel(os.path.join(fid20, vid + ".png"), 1)], labels, f"boy_yellow_hoodie - {name} ({vid})")
        rows.append(r)
        stack([r], os.path.join(out, f"sheet_{name.replace('/', '')}.jpg"))
    turn = Image.open(TURN).convert("RGB")
    up = Image.open(UP01).convert("RGB")
    face_ref = up.crop((0, 668, 746, 1330))  # upload 01, face close-up tile
    tfront = turn.crop((20, 0, 290, 275))
    t34 = turn.crop((320, 0, 590, 275))
    c20 = "2.0.0 face (close-up, round-2 hair)" if rend else "2.0.0 candidate"
    fcells = [face_ref, tfront, Image.open(os.path.join(cu11, "front.png")), Image.open(os.path.join(cu20, "front.png"))]
    flabs = ["reference: upload 01 close-up", "reference: turnaround front", "1.1.0 current", c20]
    qcells = [t34, Image.open(os.path.join(cu11, "q34.png")), Image.open(os.path.join(cu20, "q34.png"))]
    qlabs = ["reference: turnaround 3/4", "1.1.0 current", c20]
    if rend:
        fcells.append(Image.open(os.path.join(rend, "val27_front.png")).convert("RGB").crop(head))
        qcells.append(Image.open(os.path.join(rend, "val27_threequarter_right.png")).convert("RGB").crop(head))
        flabs.append("2.0.0 final (round-3 hair, crop)")
        qlabs.append("2.0.0 final 3/4 (val27 cam, crop)")
    fr = row(fcells, flabs, "face close-up, front")
    fq = row(qcells, qlabs, "face close-up, 3/4 (yaw -35; crop: val27 3/4 camera)")
    stack([fr, fq], os.path.join(out, "sheet_face.jpg"))
    stack(rows + [fr, fq], os.path.join(out, "owner_sheet.jpg"))
    strip = Image.new("RGB", (turn.width, 700), (238, 238, 238))
    strip.paste(turn.crop((0, 0, turn.width, 700)), (0, 0))
    strip.save(os.path.join(out, "reference_turnaround_boy.jpg"), quality=85)


if __name__ == "__main__":
    main()
