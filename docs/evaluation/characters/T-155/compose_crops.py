"""T-132 (T-155 copy): lays crops.py tiles out unscaled (100%): one row per shot, columns current | candidate.

    python3 docs/evaluation/characters/T-155/compose_crops.py <shots dir> <out.png> "<title>"
"""
import json
import os
import sys

from PIL import Image, ImageDraw

src, out, title = sys.argv[1], sys.argv[2], sys.argv[3]
rec = json.load(open(os.path.join(src, "shots.json")))
px, bar, gap = rec["px"], 18, 4
cols = [c["label"] for c in rec["columns"]]
W = len(cols) * (px + gap) + gap
H = 24 + len(rec["shots"]) * (px + bar + gap) + gap
sheet = Image.new("RGB", (W, H), (92, 92, 96))
d = ImageDraw.Draw(sheet)
d.rectangle((0, 0, W, 23), fill=(20, 20, 20))
d.text((6, 6), f"{title} | Cycles {rec['samples']} spp, {px} px tiles at 100%", fill=(240, 240, 240))
for r, s in enumerate(rec["shots"]):
    y = 24 + gap + r * (px + bar + gap)
    for c, label in enumerate(cols):
        x = gap + c * (px + gap)
        d.rectangle((x, y, x + px - 1, y + bar - 1), fill=(20, 20, 20))
        d.text((x + 4, y + 3), f"{label} | {s['label']}"[:64], fill=(240, 240, 240))
        sheet.paste(Image.open(os.path.join(src, label, s["name"] + ".png")).convert("RGB"), (x, y + bar))
sheet.save(out, optimize=True)
print(out, sheet.size)
