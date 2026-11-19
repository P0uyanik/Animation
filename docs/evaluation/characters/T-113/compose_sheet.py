"""T-113 sheet composer: one row per expression, the reference crop first, then each rendered column.

    python3 docs/evaluation/characters/T-113/compose_sheet.py <job.json> <refs dir> <out.jpg> [--title T] [--labels a=A,...]
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

LABELS = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("refs")
    ap.add_argument("out")
    ap.add_argument("--title", default="")
    ap.add_argument("--labels", default="")
    ap.add_argument("--ref-labels", default="")
    a = ap.parse_args()
    job = json.load(open(a.job))
    names = dict(x.split("=", 1) for x in a.labels.split(",") if x)
    rlab = json.load(open(a.ref_labels)) if a.ref_labels else {}
    cols = [c["tag"] for c in job["columns"]]
    first = Image.open(os.path.join(job["out"], job["rows"][0]["tag"], cols[0] + ".png"))
    w, h = first.size
    lw, th, cap = 210, 44, 30
    W, H = lw + w * (len(cols) + 1), th + cap + h * len(job["rows"])
    S = Image.new("RGB", (W, H), "#f9f7f1")
    d = ImageDraw.Draw(S)
    f, fs = ImageFont.load_default(size=20), ImageFont.load_default(size=13)
    d.text((10, 10), a.title, fill="#222", font=f)
    for j, t in enumerate(["reference"] + [names.get(c, c) for c in cols]):
        d.text((lw + j * w + 6, th + 6), t, fill="#333", font=fs)
    missing = json.load(open(os.path.join(job["out"], "missing.json"))) if os.path.isfile(os.path.join(job["out"], "missing.json")) else {}
    for i, r in enumerate(job["rows"]):
        y = th + cap + i * h
        ref = os.path.join(a.refs, r["tag"] + ".png")
        if os.path.isfile(ref):
            im = Image.open(ref).convert("RGB")
            im.thumbnail((w, h))
            S.paste(im, (lw + (w - im.width) // 2, y + (h - im.height) // 2))
        for j, c in enumerate(cols):
            p = os.path.join(job["out"], r["tag"], c + ".png")
            if os.path.isfile(p):
                S.paste(Image.open(p).convert("RGB"), (lw + (j + 1) * w, y))
            miss = missing.get(c, {}).get(r["tag"])
            if miss:
                d.text((lw + (j + 1) * w + 6, y + h - 20), "missing: " + ",".join(m[5:] for m in miss), fill="#b00", font=fs)
        txt = [r["tag"], f"intensity {r.get('intensity', 1.0)}", rlab.get(r["tag"], "")]
        for k, line in enumerate(txt):
            for m, chunk in enumerate([line[q:q + 28] for q in range(0, len(line), 28)][:3]):
                d.text((8, y + 8 + k * 22 + m * 15), chunk, fill="#222" if k == 0 else "#555", font=fs)
    S.save(a.out, quality=88)


if __name__ == "__main__":
    main()
