"""T-189 throwaway: contact sheet of render_models.py output (rows = models, cols = raw / tint / flat). Max 1024 px wide."""
import json, os, sys
from PIL import Image, ImageDraw
R, OUT = sys.argv[1], sys.argv[2]; S = json.load(open(os.path.join(R, "stats.json")))
ids = sys.argv[3].split(",") if len(sys.argv) > 3 else sorted(S)
cell, lab, cols = 112, 12, 2  # two models per row, 3 looks each
rows = (len(ids) + cols - 1) // cols; W = cols * 3 * cell + (cols - 1) * 8
img = Image.new("RGB", (W, rows * (cell + lab)), "white"); d = ImageDraw.Draw(img)
for i, m in enumerate(ids):
    x0 = (i % cols) * (3 * cell + 8); y0 = (i // cols) * (cell + lab)
    for j, look in enumerate(("raw", "tint", "flat")):
        p = os.path.join(R, "%s_%s.png" % (m, look))
        if os.path.exists(p):
            img.paste(Image.open(p).convert("RGB").resize((cell, cell)), (x0 + j * cell, y0 + lab))
    s = S[m]; d.text((x0 + 2, y0 + 1), "%s  %d tris  %.2fx%.2fx%.2f m" % (m, s["tris"], *s["dims_m"]), fill="black")
img.save(OUT, quality=88); print(OUT, img.size)
