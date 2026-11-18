"""T-065 final owner sheets: reference | current approved version | face v2 + fitted head candidate, front and 3/4.

    python3 docs/evaluation/characters/T-065/make_final_sheets.py

Inputs (all in this folder or the repository): head_v2/renders/<who>/ (candidate stills), head_v2/renders/
current_boy_1.1.0/ (published boy 1.1.0, same framing and light), the girl 0.10.0 panels of T-055 (same calibration;
its own framing), the reference crops of make_sheets.py. Writes head_v2/<who>_owner_sheet.jpg and
head_v2/overview_owner_sheet.jpg (JPEG, at most 2048 px wide)."""
import os

from PIL import Image, ImageDraw

import make_sheets as MS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
R = os.path.join(HERE, "head_v2", "renders")
T055 = os.path.join(ROOT, "docs", "evaluation", "characters", "T-055")


def t055(name, box):
    return Image.open(os.path.join(T055, name)).convert("RGB").crop(box)


def current(who, view):
    if who == "boy":
        return Image.open(os.path.join(R, "current_boy_1.1.0", "Neutral_0.png" if view == "front" else "Neutral_30.png")), "current approved 1.1.0"
    if who == "girl":
        return (t055("girl_0.10.0_face_front_vs_reference.png", (392, 26, 780, 412)) if view == "front" else
                t055("girl_0.10.0_face_34_vs_reference.png", (390, 26, 776, 412))), "current approved 0.10.0 (T-055 still)"
    return None, "third character: not built yet"


def main():
    rows = []
    for who in ("boy", "girl", "third"):
        cfg = MS.SHEETS[who]
        (fsrc, _, flabel), (tsrc, _, tlabel) = cfg["faces"]
        if who == "girl":  # head crops of her turnaround views (ref_34/ref_30 are multi-panel sheets)
            V = "assets/characters/girl_auburn_bun_glasses/references/views/"
            fsrc, flabel = (V + "sheet30_front.png", (0.12, 0.13, 0.88, 0.45)), "front (sheet30)"
            tsrc, tlabel = (V + "sheet30_front_left.png", (0.05, 0.13, 0.95, 0.45)), "3/4 (sheet30)"
        tiles = []
        for view, src, label, shot in (("front", fsrc, flabel, "Neutral_0"), ("3/4", tsrc, tlabel, "Neutral_30" if who == "boy" else "Neutral_35")):
            tiles.append(MS.panel(MS.crop(src), "REFERENCE " + label, 340, 340))
            im, lab = current(who, "front" if view == "front" else "34")
            tiles.append(MS.panel(im if im is not None else Image.new("RGB", (10, 10), (64, 64, 68)), lab, 340, 340))
            tiles.append(MS.panel(Image.open(os.path.join(R, who, shot + ".png")), f"face v2 + fitted head, {view}", 340, 340))
        sheet = Image.new("RGB", (340 * len(tiles), 340), (64, 64, 68))
        for i, t in enumerate(tiles):
            sheet.paste(t, (340 * i, 0))
        sheet.save(os.path.join(HERE, "head_v2", f"{who}_owner_sheet.jpg"), quality=90)
        rows.append(sheet)
    W = min(2048, rows[0].width)
    rows = [r.resize((W, round(r.height * W / r.width)), Image.LANCZOS) for r in rows]
    ov = Image.new("RGB", (W, sum(r.height for r in rows) + 26), (40, 40, 44))
    ImageDraw.Draw(ov).text((6, 7), "T-065 face v2 + fitted head (body_generic/2): reference | current approved | candidate - front (left), 3/4 (right)",
                            fill=(240, 240, 240))
    y = 26
    for r in rows:
        ov.paste(r, (0, y))
        y += r.height
    ov.save(os.path.join(HERE, "head_v2", "overview_owner_sheet.jpg"), quality=90)
    print("owner sheets written", ov.size)


if __name__ == "__main__":
    main()
