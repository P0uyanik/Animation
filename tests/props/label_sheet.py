"""T-163: adds the legend to the rendered sheet. python3 tests/props/label_sheet.py <raw.png> <out.png>"""
import sys
from PIL import Image, ImageDraw
im = Image.open(sys.argv[1]).convert("RGB"); W, H = im.size
out = Image.new("RGB", (W, H + 70), (250, 247, 240)); out.paste(im, (0, 0)); d = ImageDraw.Draw(out)
for k, t in enumerate(["T-163 starter felt props, Cycles render with the 'felt' preset, one scale (cup 100 mm tall). Back to front, left to right:",
                       "back row: cup (existing), bowl, plate, spoon, book  |  middle row: ball, box, box_lid, toy, apple  |  front row: pencil, block, basket"]):
    d.text((12, H + 10 + 22 * k), t, fill=(70, 50, 35))
out.save(sys.argv[2])
