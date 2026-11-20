"""T-170 throwaway: build the evidence sheets (all <= 2048 px) from the reference videos, measurements.json and swatches/.

python3 docs/evaluation/world/T-170/scripts/make_sheets.py   (after measure_reference.py and render_swatches.py)
"""
import json, os
from PIL import Image, ImageDraw
import measure_reference as M

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
D = json.load(open(os.path.join(OUT, "measurements.json")))["patches"]
BG, FG = (28, 28, 28), (235, 235, 235)

def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def fit(im, w, h):
    s = min(w / im.width, h / im.height)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)

def context(name, w=170, h=120):
    p = D[name]; im = M.frame((p["clip"], p["frame"])); l, t, r, b = p["box"]
    cx, cy = (l + r) // 2, (t + b) // 2; w, h = max(w, r - l + 20), max(h, b - t + 20)
    x0 = min(max(0, cx - w // 2), im.width - w); y0 = min(max(0, cy - h // 2), im.height - h)
    c = im.crop((x0, y0, x0 + w, y0 + h)); ImageDraw.Draw(c).rectangle((l - x0, t - y0, r - x0, b - y0), outline=(255, 0, 255))
    return c

def swatch(n):
    return Image.open(os.path.join(OUT, "swatches", n + ".png")).convert("RGB")

# 01 overview --------------------------------------------------------------------------------------------------------
keys = [("pb", 0, "paperboat f0: wide, desk"), ("pb", 96, "paperboat f96: macro insert, worn table"), ("pb", 168, "paperboat f168: tray rim, mirror water"),
        ("pb", 192, "paperboat f192: ripples"), ("wt", 0, "watertable f0: oak table, rug, window"), ("wt", 96, "watertable f96")]
S = Image.new("RGB", (2040, 1010), BG); d = ImageDraw.Draw(S); x = 0
for i, (c, f, cap) in enumerate(keys[:4]):
    im = fit(M.frame((c, f)), 660, 371); px, py = (i % 2) * 665, (i // 2) * 395
    S.paste(im, (px, py + 16)); d.text((px + 4, py + 2), cap, fill=FG)
for i, (c, f, cap) in enumerate(keys[4:]):
    im = fit(M.frame((c, f)), 400, 780); px = 1335 + i * 355
    S.paste(fit(im, 350, 780), (px, 16)); d.text((px + 4, 2), cap, fill=FG)
S.crop((0, 0, 2040, 800)).save(os.path.join(OUT, "01_reference_frames.jpg"), quality=90)

# 02 reference crop | measured chip | swatch -------------------------------------------------------------------------
PAIRS = [("wood, light satin (oak/beech)", ["wood_oak_apron", "wood_shelf_bg"], "wood_oak_satin"),
         ("wood, worn plank", ["wood_worn_table"], "wood_worn"),
         ("painted toy (gloss)", ["toy_paint_red"], "wood_painted_toy"),
         ("plastic, semi-gloss (tray)", ["plastic_tray_blue"], "plastic_semigloss"),
         ("plastic, gloss (scissor handles)", ["plastic_scissor_yellow", "plastic_scissor_blue"], "plastic_gloss"),
         ("paper", ["paper_lit", "paper_cool_tray"], "paper"),
         ("water in tray", ["water_tray_pb"], "water_tray"),
         ("rug, loop pile", ["rug_sage", "rug_teal"], "rug_loop_pile"),
         ("canvas storage bin", ["bin_sage", "bin_coral"], "woven_cotton__existing"),
         ("wall, painted plaster", ["wall_cream"], "wall_plaster"),
         ("matte cup (card/ceramic)", ["cup_matte"], "ceramic_matte"),
         ("fleece garment", ["fleece_yellow", "fleece_blue"], "fleece__existing"),
         ("wool yarn hair", ["yarn_brown"], "wool_yarn__existing"),
         ("flocked skin", ["skin_hand"], "skin-flock-3__existing"),
         ("plush soft toy", ["teddy_plush", "plush_grey_toy"], "felt__existing"),
         ("wax crayon (no clean ref patch)", [], "wax_crayon"),
         ("metal wire, glasses (no clean ref patch)", [], "metal_wire")]
CW, CH = 678, 190
S = Image.new("RGB", (3 * CW, 6 * CH), BG); d = ImageDraw.Draw(S)
for i, (label, refs, sw) in enumerate(PAIRS):
    px, py = (i % 3) * CW, (i // 3) * CH
    d.text((px + 4, py + 3), label + "   | reference crop(s), measured median | T-170 swatch", fill=FG)
    x = px + 4
    for r in refs:
        c = fit(context(r), 190, 140); S.paste(c, (x, py + 18)); x += c.width + 3
        S.paste(Image.new("RGB", (34, 140), rgb(D[r]["hex"])), (x, py + 18)); d.text((x - 30, py + 160), D[r]["hex"], fill=FG); x += 40
    S.paste(swatch(sw).crop((30, 50, 310, 290)).resize((187, 160), Image.LANCZOS), (px + CW - 195, py + 18))
S.save(os.path.join(OUT, "02_reference_vs_swatches.jpg"), quality=90)

# 03 palette ---------------------------------------------------------------------------------------------------------
GROUPS = [("structure / wood (warm, low-mid chroma)", ["wall_cream", "floor_wood", "wood_shelf_bg", "wood_oak_apron", "wood_worn_table", "wood_oak_shadow_side", "cup_matte"]),
          ("soft pastels: textiles, rug, bins", ["bin_sage", "bin_coral", "rug_sage", "rug_teal", "rug_rose", "fleece_blue", "fleece_cream", "fleece_yellow"]),
          ("cool relief: plastic, water, paper", ["plastic_tray_blue", "water_tray_pb", "paper_lit", "paper_cool_tray", "paper_shade", "window_blown"]),
          ("saturated accents (small area only)", ["toy_paint_red", "plastic_scissor_yellow", "plastic_scissor_blue"]),
          ("characters / plush", ["skin_hand", "yarn_brown", "teddy_plush", "plush_grey_toy"])]
S = Image.new("RGB", (1280, len(GROUPS) * 150), BG); d = ImageDraw.Draw(S)
for g, (title, names) in enumerate(GROUPS):
    d.text((6, g * 150 + 4), title, fill=FG)
    for i, n in enumerate(names):
        S.paste(Image.new("RGB", (150, 90), rgb(D[n]["hex"])), (6 + i * 158, g * 150 + 20))
        d.text((6 + i * 158, g * 150 + 112), n.replace("plastic_", "")[:22], fill=FG)
        d.text((6 + i * 158, g * 150 + 124), "%s  S%.2f R/B %.2f" % (D[n]["hex"], D[n]["S50"], D[n]["R_over_B"]), fill=FG)
S.save(os.path.join(OUT, "03_palette_measured.png"))

# 04 bevel rule ------------------------------------------------------------------------------------------------------
S = Image.new("RGB", (4 * 320 + 420, 340), BG); d = ImageDraw.Draw(S)
for i, f in enumerate(("00", "03", "08", "16")):
    S.paste(swatch("bevel_" + f), (i * 320, 20)); d.text((i * 320 + 4, 4), "edge radius = 0.%s x smallest part dimension" % f, fill=FG)
ref = M.frame(("wt", 0)).crop((20, 800, 440, 1100)); S.paste(fit(ref, 420, 320), (1280, 20)); d.text((1284, 4), "reference: table rail / leg edges (watertable f0)", fill=FG)
S.save(os.path.join(OUT, "04_bevel_rule.jpg"), quality=90)
for f in ("01_reference_frames.jpg", "02_reference_vs_swatches.jpg", "03_palette_measured.png", "04_bevel_rule.jpg"):
    print(f, Image.open(os.path.join(OUT, f)).size)
