"""T-044: head-turn clip (GIF, 12 fps, 2 s) and a strip (every 3rd frame) from measure.py --render frames.

    python3 make_turn.py <frames_dir> <out_prefix>"""
import os
import sys

from PIL import Image

src, out = sys.argv[1], sys.argv[2]
files = sorted(f for f in os.listdir(src) if f.endswith(".png"))
ims = [Image.open(os.path.join(src, f)).convert("RGB") for f in files]
g = [im.convert("P", palette=Image.ADAPTIVE, colors=128) for im in ims]
g[0].save(out + "_head_turn.gif", save_all=True, append_images=g[1:], duration=83, loop=0, optimize=True)
sel = ims[::3]
h = 220
sel = [im.resize((int(im.width * h / im.height), h)) for im in sel]
strip = Image.new("RGB", (sum(i.width for i in sel), h))
x = 0
for i in sel:
    strip.paste(i, (x, 0))
    x += i.width
strip.save(out + "_head_turn.jpg", quality=85)
print(out, len(ims), "frames")
