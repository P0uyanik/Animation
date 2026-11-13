"""Side-by-side reference | iteration 3 | iteration 4 for characters A, B and C (full body, front view), plus a
face row. Same camera for iteration 3 and 4 (lineup front, 1280x960). Run from the repository root after
tools/render_iteration4_evidence.sh: python3 tools/make_it4_comparison.py"""
from PIL import Image, ImageDraw

REFS = {"A": "docs/references/char_A_white_hair.webp", "B": "docs/references/char_B_brown_hair.webp", "C": "docs/references/char_C_boy.jpg"}
IT3 = "docs/milestone03/lineup_front_1280x960.png"
IT4 = "renders/it4/lineup_front_1280x960.png"
CX = {"A": 391, "B": 640, "C": 889}  # character centres in the 1280-wide lineup (x = -0.42, 0, 0.42 m)
H = 760


def ref_crop(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (236, 233, 228, 255))
    im = Image.alpha_composite(bg, im) if path.endswith(".webp") else im
    rgb = im.convert("RGB")
    # bounding box of pixels that differ from the corner (background) colour
    corner = rgb.getpixel((3, 3))
    mask = Image.eval(rgb.convert("L"), lambda v: 0)
    px, mp = rgb.load(), mask.load()
    for y in range(0, rgb.height, 2):
        for x in range(0, rgb.width, 2):
            c = px[x, y]
            if sum(abs(c[i] - corner[i]) for i in range(3)) > 40:
                mp[x, y] = 255
    box = mask.getbbox()
    pad = 12
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(rgb.width, box[2] + pad), min(rgb.height, box[3] + pad))
    return rgb.crop(box)


def lineup_crop(path, cx):
    im = Image.open(path).convert("RGB")
    return im.crop((cx - 165, 40, cx + 165, 905))


def fit(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 12 + 7 * len(text), 22), fill=(20, 20, 20))
    d.text((6, 5), text, fill=(255, 255, 255))
    return im


panels = []
for n in ("A", "B", "C"):
    row = [label(fit(ref_crop(REFS[n]), H), f"{n} reference"),
           label(fit(lineup_crop(IT3, CX[n]), H), f"{n} iteration 3"),
           label(fit(lineup_crop(IT4, CX[n]), H), f"{n} iteration 4")]
    w = sum(p.width for p in row) + 8 * (len(row) - 1)
    out = Image.new("RGB", (w, H), (255, 255, 255))
    x = 0
    for p in row:
        out.paste(p, (x, 0))
        x += p.width + 8
    out.save(f"docs/iteration4/compare_{n}_ref_it3_it4.png")
    panels.append(out)
W = max(p.width for p in panels)
sheet = Image.new("RGB", (W, (H + 10) * 3), (255, 255, 255))
for i, p in enumerate(panels):
    sheet.paste(p, (0, i * (H + 10)))
sheet.save("docs/iteration4/compare_ABC_ref_it3_it4.png")
print("wrote docs/iteration4/compare_{A,B,C}_ref_it3_it4.png and compare_ABC_ref_it3_it4.png")
