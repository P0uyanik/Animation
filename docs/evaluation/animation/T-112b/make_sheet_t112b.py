"""T-112b evidence: s010_calibrated (hand-authored primitives, T-104) vs s010_verbs (the same exchange as verbs, T-112b):
dope sheet and one row per shot at the same beats (python3, Pillow, ffmpeg). Adapted from T-104 make_sheet_t104.py.

    python3 docs/evaluation/animation/T-112b/make_sheet_t112b.py --calibrated <dir> --verbs <dir> --out <file.jpg> [--width 480]
    python3 docs/evaluation/animation/T-112b/make_sheet_t112b.py --frames      (prints the frames each shot needs)

<dir> holds <tag>_fNNNN.png renders of the shot camera (T-095 render_frames.py, tags "calibrated" / "verbs").
s010_calibrated's beats are its x_t095_staging block (make_shot.py); s010_verbs's come from the verb expander's phase
spans (s010_verbs.expanded.scene.json, x_t112b_phases)."""
import argparse
import json
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
TAGS = ("calibrated", "verbs")
REFS = [("video_paperboat.mp4", 157, "PB f157 lower"), ("video_paperboat.mp4", 172, "PB f172 contact"),
        ("video_paperboat.mp4", 272, "PB f272 hold"), ("video_watertable.mp4", 22, "WT f22 reach end"),
        ("video_watertable.mp4", 40, "WT f40 point hold"), ("video_watertable.mp4", 110, "WT f110 end hold")]
COLORS = {"reach": (70, 130, 200), "hold": (120, 180, 90), "shared_hold": (230, 160, 40), "release": (200, 90, 90),
          "end hold": (150, 150, 150)}


def beats(tag):
    if tag == "calibrated":
        s = json.load(open(os.path.join(ROOT, "episodes/e907_exchange/shots/s010_calibrated/shot.scene.json")))
        return s["x_t095_staging"]["beats"], s["frameEnd"]
    s = json.load(open(os.path.join(HERE, "s010_verbs.expanded.scene.json")))
    ph = {(p["action"], p["phase"], p["part"]): p for p in s["x_t112b_phases"]}
    r = lambda v: int(round(v))  # noqa: E731
    pick, pas, carry = 3, 4, 5
    b = {"grasp": r(ph[(pick, "approach", "")]["from"]), "his_contact": r(ph[(pick, "contact", "")]["to"]),
         "offer": (r(ph[(pas, "manipulate", "offer")]["from"]), r(ph[(pas, "manipulate", "offer")]["to"])),
         "her_reach": r(ph[(pas, "approach", "")]["from"]), "her_contact": r(ph[(pas, "contact", "")]["to"]),
         "his_release": r(ph[(pas, "manipulate", "shared")]["to"]), "his_end": r(ph[(pas, "release", "")]["to"]),
         "her_draw": (r(ph[(carry, "manipulate", "")]["from"]), r(ph[(carry, "manipulate", "")]["to"])),
         "end": s["frameEnd"]}
    return b, s["frameEnd"]


def columns(b):
    """(frame, label) of the compared beats in one shot."""
    shared = (b["her_contact"] + b["his_release"]) // 2
    return [(b["his_contact"], "his contact"), (b["offer"][1], "offer held"), (b["her_contact"], "her contact"),
            (shared, "shared hold"), (b["his_release"] + 2, "his release"), (b["end"], "end hold")]


def segments(b, end):
    return [("boy", "reach", b["grasp"], b["his_contact"]), ("boy", "reach", b["offer"][0], b["offer"][1]),
            ("girl", "reach", b["her_reach"], b["her_contact"]), ("both", "shared_hold", b["her_contact"], b["his_release"]),
            ("boy", "release", b["his_release"], b["his_end"]), ("girl", "reach", b["her_draw"][0], b["her_draw"][1]),
            ("both", "end hold", max(b["her_draw"][1], b["his_end"]), end)]


def frame_png(d, tag, f):
    return Image.open(os.path.join(d, f"{tag}_f{f:04d}.png")).convert("RGB")


def ref_frame(video, n, tmp):
    out = os.path.join(tmp, f"{video}_{n}.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(ROOT, "docs", "references", video),
                    "-vf", f"select=eq(n\\,{n})", "-vframes", "1", out], check=True)
    return Image.open(out).convert("RGB")


def fit(im, w, h):
    im = im.copy()
    im.thumbnail((w, h))
    c = Image.new("RGB", (w, h), "white")
    c.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return c


def label(im, text, y=4):
    d = ImageDraw.Draw(im)
    d.rectangle([0, y - 2, 8 + 6 * len(text), y + 12], fill=(255, 255, 255))
    d.text((4, y), text, fill=(0, 0, 0))
    return im


def dope_sheet(width):
    ref = json.load(open(os.path.join(ROOT, "content", "timing", "reference_timing.json")))["beats"]
    rows = [(t, *beats(t)) for t in TAGS]
    longest = max(e for _, _, e in rows)
    px = (width - 150) / longest
    im = Image.new("RGB", (width, 40 + 70 * len(rows) + 40), "white")
    d = ImageDraw.Draw(im)
    d.text((8, 6), "dope sheet (scene frames at 24 fps); bar = beat, number = frames; red outline = shorter than the "
                   "reference minimum", fill=(0, 0, 0))
    for s in range(0, longest + 1, 24):
        x = 140 + s * px
        d.line([x, 24, x, im.height - 30], fill=(220, 220, 220))
        d.text((x - 6, im.height - 28), f"{s // 24}s", fill=(80, 80, 80))
    for i, (tag, b, end) in enumerate(rows):
        y0 = 36 + 70 * i
        d.text((8, y0 + 20), f"{tag}: {end} f = {end / 24:.2f} s", fill=(0, 0, 0))
        lanes = {"boy": 0, "both": 1, "girl": 2}
        for who, beat, a, e in segments(b, end):
            y = y0 + 20 * lanes[who]
            x0, x1 = 140 + (a - 1) * px, 140 + (e - 1) * px
            lo = ref["hold" if beat == "end hold" else beat]["frames"][0]
            d.rectangle([x0, y, x1, y + 16], fill=COLORS[beat], outline=(220, 0, 0) if e - a < lo else None,
                        width=3 if e - a < lo else 1)
            d.text((x0 + 3, y + 2), f"{e - a}", fill=(255, 255, 255))
        for k, lane in lanes.items():
            d.text((100, y0 + 20 * lane + 2), k, fill=(90, 90, 90))
    x = 8
    for k, c in COLORS.items():
        r = ref["hold" if k == "end hold" else k]["frames"]
        d.rectangle([x, im.height - 14, x + 10, im.height - 4], fill=c)
        d.text((x + 14, im.height - 16), f"{k} ref {r[0]}-{r[1]} f", fill=(0, 0, 0))
        x += 150
    return im


def sheet(a):
    w = a.width
    h = w * 9 // 16
    ncol = 6
    head = dope_sheet(w * ncol)
    rows = []
    for tag in TAGS:
        b, _ = beats(tag)
        row = Image.new("RGB", (w * ncol, h), "white")
        for i, (f, name) in enumerate(columns(b)):
            row.paste(label(fit(frame_png(getattr(a, tag), tag, f), w, h), f"{tag}: f{f} {name}"), (i * w, 0))
        rows.append(row)
    with tempfile.TemporaryDirectory() as tmp:
        ref = Image.new("RGB", (w * ncol, h), "white")
        for i, (v, n, name) in enumerate(REFS):
            ref.paste(label(fit(ref_frame(v, n, tmp), w, h), f"reference {name}"), (i * w, 0))
        rows.append(ref)
    out = Image.new("RGB", (w * ncol, head.height + h * len(rows)), "white")
    out.paste(head, (0, 0))
    for i, r in enumerate(rows):
        out.paste(r, (0, head.height + i * h))
    if out.width > 2048:
        out = out.resize((2048, out.height * 2048 // out.width), Image.LANCZOS)
    out.save(a.out, quality=88)
    print(a.out, out.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrated")
    ap.add_argument("--verbs")
    ap.add_argument("--out")
    ap.add_argument("--width", type=int, default=480)
    ap.add_argument("--frames", action="store_true")
    a = ap.parse_args()
    if a.frames:
        for t in TAGS:
            print(t, ",".join(str(f) for f, _ in columns(beats(t)[0])))
        return
    sheet(a)


main()
