"""T-170d throwaway: evidence sheets (<= 2048 px) from the scratch renders (same layout as T-170c make_sheets.py).

python3 make_sheets.py --renders <scratch renders dir> --tex <scratch downloads dir>
"""
import argparse, json, os, shutil, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
import measure_reference as M  # T-170 frame grabber (read-only import)

ap = argparse.ArgumentParser(); ap.add_argument("--renders", required=True); ap.add_argument("--tex", required=True)
ap.add_argument("--picks", default="Carpet016,Fabric045,Fabric030,Fabric030_coral"); A = ap.parse_args()
C = json.load(open(os.path.join(HERE, "candidates.json"))); D = json.load(open(os.path.join(OUT, "..", "..", "measurements.json")))["patches"]
RAW, TW = (json.load(open(os.path.join(A.renders, "results_%s.json" % m))) for m in ("raw", "tweak"))
BG, FG = (28, 28, 28), (235, 235, 235); PICKS = A.picks.split(","); BEST = ("Carpet016", "Fabric030")

def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
def fit(im, w, h):
    s = min(w / im.width, h / im.height); return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
def context(name, w, h):
    p = D[name]; im = M.frame((p["clip"], p["frame"])); l, t, r, b = p["box"]; cx, cy = (l + r) // 2, (t + b) // 2
    w, h = max(w, r - l + 20), max(h, b - t + 20); x0 = min(max(0, cx - w // 2), im.width - w); y0 = min(max(0, cy - h // 2), im.height - h)
    c = im.crop((x0, y0, x0 + w, y0 + h)); ImageDraw.Draw(c).rectangle((l - x0, t - y0, r - x0, b - y0), outline=(255, 0, 255)); return c
def sw(n, m):
    return Image.open(os.path.join(A.renders, "%s__%s.png" % (n, m))).convert("RGB")
def tgt(n):
    c = C["candidates"][n]; return c.get("target") or C["groups"][c["group"]]["target"]

G = list(C["groups"].items()); T = 232; RH = T + 44; RW = 330
S = Image.new("RGB", (RW + 6 * (T + 4), len(G) * RH), BG); d = ImageDraw.Draw(S)
for gi, (g, gd) in enumerate(G):
    y = gi * RH; p = D[gd["target"]]; d.text((4, y + 3), "%s | ref %s f%d, patch %s" % (gd["label"], p["clip"], p["frame"], p["hex"]), fill=FG)
    c = fit(context(gd["target"], 280, 200), RW - 50, T); S.paste(c, (4, y + 30)); S.paste(Image.new("RGB", (36, T), rgb(p["hex"])), (RW - 42, y + 30))
    for ci, n in enumerate([k for k, v in C["candidates"].items() if v["group"] == g and "src" not in v]):
        for mi, (m, R) in enumerate((("raw", RAW), ("tweak", TW))):
            x = RW + (2 * ci + mi) * (T + 4); S.paste(sw(n, m).resize((T, T), Image.LANCZOS), (x, y + 30))
            S.paste(Image.new("RGB", (22, 22), rgb(R[n]["display_hex"])), (x + T - 24, y + 32))
            d.text((x + 2, y + 16), "%s%s | %s %s" % ("* " if n in BEST else "", n, m, R[n]["display_hex"]), fill=(255, 220, 120) if n in BEST else FG)
S.save(os.path.join(OUT, "01_candidates_vs_reference.jpg"), quality=90)

P = 384; S = Image.new("RGB", (len(PICKS) * (P + 6), 20 + 250 + P + 20), BG); d = ImageDraw.Draw(S); os.makedirs(os.path.join(OUT, "swatches"), exist_ok=True)
for i, n in enumerate(PICKS):
    x = i * (P + 6); t = TW[n]; d.text((x + 4, 4), "ref patch " + tgt(n), fill=FG); S.paste(fit(context(tgt(n), 300, 190), P, 250), (x, 20))
    d.text((x + 4, 274), "%s (ambientCG, CC0) | target %s -> %s" % (n, t["target_hex"], t["display_hex"]), fill=FG)
    S.paste(sw(n, "tweak").resize((P, P), Image.LANCZOS), (x, 290))
    shutil.copy(os.path.join(A.renders, n + "__tweak.png"), os.path.join(OUT, "swatches", n + "__tweak.png"))
S.save(os.path.join(OUT, "02_picks.jpg"), quality=90)

man = json.load(open(os.path.join(A.tex, "manifest.json"))); used = {v.get("src", k) for k, v in C["candidates"].items()} | {"lebombo"}
json.dump({"downloaded": "2026-11-20", "note": "files are NOT in the repository; 1K JPG maps extracted from <id>_1K-JPG.zip; HDRI = T-170c lebombo (same SHA-256)",
           "files": {k: v for k, v in man.items() if v["asset"] in used},
           "previewed_only": sorted({v["asset"] for v in man.values()} - used), "results_raw": RAW, "results_tweak": TW},
          open(os.path.join(OUT, "sources.json"), "w"), indent=1, sort_keys=True)
for f in ("01_candidates_vs_reference.jpg", "02_picks.jpg"):
    print(f, Image.open(os.path.join(OUT, f)).size, os.path.getsize(os.path.join(OUT, f)))
