"""T-046 face contact sheet from the evidence render (run with any Python that has Pillow).

    python make_sheet.py <render dir> <out image>

Rows: boy, girl (face crops of the 640x360 frames); columns: the beats of the shot."""
import sys
from PIL import Image, ImageDraw

FRAMES = [(10, "idle"), (40, "happy"), (74, "surprise onset"), (90, "surprised"), (96, "girl blink"), (111, "boy blink"),
          (140, "sad, looks down")]
CROPS = {"boy": (40, 20, 300, 280), "girl": (330, 0, 600, 270)}
render, out = sys.argv[1], sys.argv[2]
cw, ch, pad, top = 200, 200, 4, 22
sheet = Image.new("RGB", (len(FRAMES) * (cw + pad) + pad + 50, 2 * (ch + pad) + pad + top), (30, 30, 30))
d = ImageDraw.Draw(sheet)
for i, (f, label) in enumerate(FRAMES):
    x = 50 + pad + i * (cw + pad)
    d.text((x + 2, 4), f"{f}: {label}", fill=(230, 230, 230))
    im = Image.open(f"{render}/frame_{f:04d}.png").convert("RGB")
    for r, (who, box) in enumerate(CROPS.items()):
        y = top + pad + r * (ch + pad)
        sheet.paste(im.crop(box).resize((cw, ch), Image.LANCZOS), (x, y))
        if i == 0:
            d.text((6, y + ch // 2), who, fill=(230, 230, 230))
sheet.save(out)
