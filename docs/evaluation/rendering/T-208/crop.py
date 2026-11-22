"""Make a matched 1:1 crop, Cycles on the left and EEVEE on the right."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

shot, frame, name = sys.argv[1:4]
box = tuple(map(int, sys.argv[4:8]))
w, h = box[2] - box[0], box[3] - box[1]
work = Path("build/t208-run")
docs = Path(__file__).resolve().parent
sheet = Image.new("RGB", (2*w, h+34), "#202328")
font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 18)
for i, (engine, label) in enumerate((("cycles", "Cycles CPU"), ("eevee", "EEVEE OpenGL"))):
    png, = work.glob(f"{shot}-{engine}-*/frame_{int(frame):04d}.png")
    with Image.open(png) as image:
        assert 0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height
        sheet.paste(image.convert("RGB").crop(box), (i*w,34))
    ImageDraw.Draw(sheet).text((i*w+12,5),f"{shot}   /   Frame {frame}   /   {label}",font=font,fill="white")
assert max(sheet.size) <= 2048
sheet.save(docs / name, quality=94, subsampling=0)
