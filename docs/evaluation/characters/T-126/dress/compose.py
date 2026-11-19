"""T-126c: lays render tiles out as sheets (T-087 tile style, tools/review/strict_sheet.py); tiles are only scaled.

    python3 docs/evaluation/characters/T-126/dress/compose.py strict <shots dir> <out.jpg>   # reference | candidate
    python3 docs/evaluation/characters/T-126/dress/compose.py crops  <shots dir> <out.jpg>
    python3 docs/evaluation/characters/T-126/dress/compose.py sim    <sim shots dir> <out.jpg>

``strict``: her references (01 identity front, the primary target; 16 W05; 09 panel 01) next to the candidate's
figure tiles. The references are other cameras and lights; the candidate tiles are one camera and light per tile."""
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "review"))
import strict_sheet as SS  # noqa: E402

REFS = os.path.join(ROOT, "assets", "characters", "girl_white_hair_blue_dress", "references", "uploads")
T = 420


def tile(im, label):
    im = im.convert("RGB")
    k = min(T / im.width, T / im.height)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    out = Image.new("RGB", (T, T + SS.HEAD_H), SS.BG)
    out.paste(im, ((T - im.width) // 2, SS.HEAD_H + (T - im.height) // 2))
    d = ImageDraw.Draw(out)
    d.rectangle((0, 0, T - 1, SS.HEAD_H - 1), fill=SS.BAR)
    d.text((5, 4), label[:66], fill=SS.TXT)
    return out


def sheet(rows, title, out):
    cols = max(len(r) for r in rows)
    im = Image.new("RGB", (cols * T, SS.TITLE_H + len(rows) * (T + SS.HEAD_H)), SS.BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, SS.TITLE_H - 1), fill=SS.BAR)
    d.text((6, 6), title[:int(im.width / 6.2)], fill=SS.TXT)
    for r, row in enumerate(rows):
        for c, t in enumerate(row):
            im.paste(t, (c * T, SS.TITLE_H + r * (T + SS.HEAD_H)))
    im.save(out, quality=90)
    print(out, im.size)


def ref(name, box, label):
    im = Image.open(os.path.join(REFS, name)).convert("RGB")
    w, h = im.size
    return tile(im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h))), "REFERENCE " + label)


def main():
    mode, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
    if mode == "sim":
        rec = json.load(open(os.path.join(src, "sim_shots.json")))
        shots = []
        for t in rec["tiles"]:
            if t["shot"] not in shots:
                shots.append(t["shot"])
        rows = [[tile(Image.open(os.path.join(src, f"{s}.{kind}.png")), f"{kind} | {s}") for s in shots]
                for kind in ("simulated", "skinned")]
        return sheet(rows, f"T-126c skirt cloth simulation (baked) against the build's skinned skirt | cycles "
                           f"{rec['samples']} spp, {rec['px']} px, seed {rec['seed']} | arms in A-pose, seat not rendered",
                     out)
    rec = json.load(open(os.path.join(src, f"shots_{'sheet' if mode == 'strict' else 'crops'}.json")))
    tiles = {s["name"]: tile(Image.open(os.path.join(src, s["name"] + ".png")), "CANDIDATE " + s["label"])
             for s in rec["shots"]}
    head = f"cycles {rec['samples']} spp, {rec['px']} px, {rec['light']}"
    if mode == "strict":
        rows = [[ref("01_identity_front.webp", (0.1, 0.36, 0.9, 1.0), "01 identity front (primary target)"),
                 tiles["figure_front"], tiles["figure_34"]],
                [ref("09_dress_construction_deformation_blueprint.webp", (0.02, 0.04, 0.5, 0.33), "09 panel 01"),
                 tiles["figure_side"], tiles["figure_back"]],
                [ref("16_higgsfield_W05_dress_tights_boots_2026-11-18.webp", (0.0, 0.0, 1.0, 1.0), "16 W05"),
                 tiles["w05"]]]
        return sheet(rows, f"T-126c dress, tights, boots | girl_white_hair_blue_dress candidate vs references | {head}", out)
    rows = [[ref("16_higgsfield_W05_dress_tights_boots_2026-11-18.webp", (0.0, 0.0, 0.55, 0.2), "16 collar"),
             tiles["collar"], tiles["collar_34"]],
            [ref("16_higgsfield_W05_dress_tights_boots_2026-11-18.webp", (0.4, 0.3, 0.85, 0.55), "16 sleeve, rib cuff"),
             tiles["cuff"], ref("16_higgsfield_W05_dress_tights_boots_2026-11-18.webp", (0.0, 0.3, 0.6, 0.8), "16 skirt, rib hem")],
            [tiles["hem"], tiles["boots"], tiles["boots_side"]],
            [ref("16_higgsfield_W05_dress_tights_boots_2026-11-18.webp", (0.45, 0.42, 1.0, 0.98), "16 boot"),
             ref("01_identity_front.webp", (0.3, 0.8, 0.72, 1.0), "01 boots, tights")]]
    sheet(rows, f"T-126c crops: collar, cuffs, hem, boots | {head}", out)


if __name__ == "__main__":
    main()
