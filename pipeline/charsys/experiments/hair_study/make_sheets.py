"""T-049 hair study: contact sheets (reference row + one row per approach; same cameras) and head-turn strips.

    python3 make_sheets.py <evidence_dir> <measure_dir> <out_dir>

evidence_dir/<char>_<A|B|C>/renders/<view>.png and closeup/closeup_face.png (render_evidence.sh);
measure_dir/<char>_<A|B|C>/turn/####.png (measure.py --render). Writes <out>/<char>_contact_sheet.jpg,
<out>/<char>_head_turn.jpg (every 3rd frame) and <out>/<char>_<A|B|C>_head_turn.gif (12 fps, 2 s)."""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
import json  # noqa: E402

CHARS = {k: dict(v, ref_close=(v["ref_close"][0], tuple(v["ref_close"][1])))
         for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "specs",
                                                 "characters.json"))).items() if k != "note"}
LABELS = {"A": "A strand/lock groom", "B": "B sculpted volume", "C": "C hybrid"}
H = 420


def fit(im, h=H):
    im = im.convert("RGB")
    return im.resize((max(1, int(im.width * h / im.height)), h), Image.LANCZOS)


def tile_row(ims, label):
    w = sum(i.width for i in ims) + 6 * (len(ims) - 1)
    row = Image.new("RGB", (w + 150, max(i.height for i in ims)), (240, 240, 240))
    ImageDraw.Draw(row).text((6, 8), label, fill=(0, 0, 0))
    x = 150
    for i in ims:
        row.paste(i, (x, 0))
        x += i.width + 6
    return row


def main():
    ev, ms, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    for c, cfg in CHARS.items():
        refdir = os.path.join(ROOT, "assets", "characters", cfg["id"], "references", "views")
        p, box = cfg["ref_close"]
        rows = [tile_row([fit(Image.open(os.path.join(refdir, v + ".png"))) for v in cfg["views"]]
                         + [fit(Image.open(os.path.join(ROOT, p)).convert("RGB").crop(box))], "reference")]
        for ap in "ABC":
            d = os.path.join(ev, f"{c}_{ap}")
            if not os.path.isdir(d):
                continue
            ims = [fit(Image.open(os.path.join(d, "renders", v + ".png"))) for v in cfg["views"]]
            ims.append(fit(Image.open(os.path.join(d, "closeup", "closeup_face.png"))))
            rows.append(tile_row(ims, LABELS[ap]))
        W = max(r.width for r in rows)
        sheet = Image.new("RGB", (W, sum(r.height + 6 for r in rows)), (255, 255, 255))
        y = 0
        for r in rows:
            sheet.paste(r, (0, y))
            y += r.height + 6
        sheet.save(os.path.join(out, f"{c}_contact_sheet.jpg"), quality=88)
        strips = []
        for ap in "ABC":
            td = os.path.join(ms, f"{c}_{ap}", "turn")
            if not os.path.isdir(td):
                continue
            fr = [Image.open(os.path.join(td, f)).convert("RGB") for f in sorted(os.listdir(td)) if f.endswith(".png")]
            g = [f.resize((240, 240), Image.LANCZOS).quantize(64) for f in fr]
            g[0].save(os.path.join(out, f"{c}_{ap}_head_turn.gif"), save_all=True, append_images=g[1:],
                       duration=83, loop=0)
            sel = [f.resize((200, 200)) for f in fr[::3]]
            strips.append(tile_row([s.resize((int(s.width * H / 200 / 2), H // 2)) for s in sel], LABELS[ap]))
        if strips:
            W = max(s.width for s in strips)
            st = Image.new("RGB", (W, sum(s.height + 4 for s in strips)), (255, 255, 255))
            y = 0
            for s in strips:
                st.paste(s, (0, y))
                y += s.height + 4
            st.save(os.path.join(out, f"{c}_head_turn.jpg"), quality=88)
    print("sheets written to", out)


if __name__ == "__main__":
    main()
