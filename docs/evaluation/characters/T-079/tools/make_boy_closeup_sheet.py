"""T-079: boy hair vs the owner's close-up upload (assets/characters/boy_yellow_hoodie/references/uploads/01_*):
top-down view (whorl and petal rosette) and the crown close-up, each next to a render from a matching camera.

    blender ... preview.py -- <boy hairv3.blend> top.png 0,0.01,0.9 0.42 0 --el 80 --px 512 --spp 16
    blender ... preview.py -- <boy hairv3.blend> crown.png 0,0.01,0.93 0.36 0 --el 22 --px 512 --spp 16
    python3 make_boy_closeup_sheet.py top.png crown.png <out_dir>

Writes <out_dir>/sheets/boy_closeup_vs_upload.jpg and media/boy_top.jpg, media/boy_crown.jpg (JPEG q85)."""
import glob
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
UP = sorted(glob.glob(os.path.join(ROOT, "assets", "characters", "boy_yellow_hoodie", "references", "uploads", "01_*")))[0]
H = 560


def fit(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def main():
    top, crown, out = sys.argv[1], sys.argv[2], sys.argv[3]
    up = Image.open(UP).convert("RGB")
    w, h = up.size
    refs = [up.crop((0, 0, w // 2, int(h * 0.333))), up.crop((w // 2, 0, w, int(h * 0.333)))]
    rends = [Image.open(top).convert("RGB"), Image.open(crown).convert("RGB")]
    tiles = [fit(x, H) for pair in zip(refs, rends) for x in pair]
    W = sum(t.width for t in tiles) + 10 * (len(tiles) + 1)
    sheet = Image.new("RGB", (W, H + 40), (236, 236, 236))
    d = ImageDraw.Draw(sheet)
    d.text((8, 6), "boy_yellow_hoodie - hair v3 round 3 (T-079) vs the owner's close-up upload 01: top-down view "
                   "(upload | render, el 80) and crown close-up (upload | render, el 22). Cycles 16 spp + OIDN, ortho.",
           fill=(0, 0, 0))
    x = 10
    for t in tiles:
        sheet.paste(t, (x, 30))
        x += t.width + 10
    os.makedirs(os.path.join(out, "sheets"), exist_ok=True)
    os.makedirs(os.path.join(out, "media"), exist_ok=True)
    if sheet.width > 2048:
        k = 2048 / sheet.width
        sheet = sheet.resize((2048, round(sheet.height * k)), Image.LANCZOS)
    sheet.save(os.path.join(out, "sheets", "boy_closeup_vs_upload.jpg"), quality=85)
    rends[0].save(os.path.join(out, "media", "boy_top.jpg"), quality=85)
    rends[1].save(os.path.join(out, "media", "boy_crown.jpg"), quality=85)
    print("wrote", os.path.join(out, "sheets", "boy_closeup_vs_upload.jpg"))


if __name__ == "__main__":
    main()
