#!/usr/bin/env python3
"""T-163: schematic contact sheet (front view, x-y plane, same scale for every prop) drawn from the asset JSON.
Shows the mesh primitive silhouette, collision proxy (dashed), sockets and grasp sites. Not a render.
python3 tests/props/contact_sheet.py [out.png]"""
import json, pathlib, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[2]
NAMES = ["cup", "bowl", "plate", "spoon", "book", "ball", "box", "box_lid", "toy", "apple", "pencil", "block", "basket"]
S = 1200  # px per metre
CW, CH, COLS = 380, 330, 4
FELT = (214, 168, 120); LINE = (70, 50, 35)

def extent(a):
    m = a["mesh"]
    if m["primitive"] == "cylinder": return (-m["radius"], 0, m["radius"], m["height"])
    if m["primitive"] == "sphere": r = m["radius"]; return (-r, -r, r, r)
    sx, sy, _ = m["size"]; return (-sx / 2, -sy / 2, sx / 2, sy / 2)

def main(out):
    rows = (len(NAMES) + COLS - 1) // COLS
    img = Image.new("RGB", (CW * COLS, CH * rows + 40), (250, 247, 240))
    d = ImageDraw.Draw(img); f = ImageFont.load_default()
    d.text((10, 10), "T-163 starter felt props - schematic front view (x right, y up), one scale; red=grasp site, blue=place, green=contact, dashed=collision", fill=LINE, font=f)
    for i, n in enumerate(NAMES):
        a = json.loads((ROOT / f"content/assets/felt_{n}.asset.json").read_text())
        cx = (i % COLS) * CW + CW // 2; base = 40 + (i // COLS) * CH + CH - 70
        P = lambda x, y: (cx + x * S, base - y * S)
        x0, y0, x1, y1 = extent(a); m = a["mesh"]
        # mesh
        if m["primitive"] == "sphere": d.ellipse([*P(x0, y1), *P(x1, y0)], fill=FELT, outline=LINE, width=2)
        else: d.rectangle([*P(x0, y1), *P(x1, y0)], fill=FELT, outline=LINE, width=2)
        if m.get("open_top"):
            w = m.get("wall", 0.005); d.rectangle([*P(x0 + w, y1), *P(x1 - w, y1 - 0.012)], fill=(250, 247, 240), outline=LINE)
        # collision proxy
        c = a.get("collision")
        if c:
            ty = c.get("transform", {}).get("translation", [0, 0, 0])[1]
            if c["type"] == "box": hx, hy = c["size"][0] / 2, c["size"][1] / 2
            elif c["type"] == "sphere": hx = hy = c["radius"]
            else: hx, hy = c["radius"], c["height"] / 2
            r = [*P(-hx, ty + hy), *P(hx, ty - hy)]
            for k in range(int(r[0]), int(r[2]), 8): d.line([(k, r[1]), (k + 4, r[1])], fill=(110, 110, 110)); d.line([(k, r[3]), (k + 4, r[3])], fill=(110, 110, 110))
            for k in range(int(r[1]), int(r[3]), 8): d.line([(r[0], k), (r[0], k + 4)], fill=(110, 110, 110)); d.line([(r[2], k), (r[2], k + 4)], fill=(110, 110, 110))
        sk = a["sockets"]; af = a["affordances"]
        grasp = {s["socket"] for s in af["grasp_sites"]}
        for name, t in sk.items():
            x, y = P(t["translation"][0], t["translation"][1])
            col = (200, 40, 40) if name in grasp else (40, 90, 200) if name == "place" else (40, 150, 70) if name == "contact" else (120, 120, 120)
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=col)
        d.text((cx - CW // 2 + 12, base + 30), f"{a['id']}", fill=LINE, font=f)
        info = f"{af['hands']}-hand | {af['size_class']} | {af['mass_kg']} kg | sites {len(af['grasp_sites'])} sets {len(af['grasp_sets'])}"
        d.text((cx - CW // 2 + 12, base + 44), info, fill=LINE, font=f)
        d.text((cx - CW // 2 + 12, base + 58), ("(existing, unchanged) " if n == "cup" else "") + "shapes: " + ",".join(sorted({s["shape"] for s in af["grasp_sites"]})), fill=LINE, font=f)
    img.save(out)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs/evaluation/props/T-163/contact_sheet.png")
