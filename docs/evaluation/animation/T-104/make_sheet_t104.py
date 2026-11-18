"""T-104 evidence: before/after timing sheet and side-by-side movie of the e907 exchange (python3, Pillow, ffmpeg).

    python3 docs/evaluation/animation/T-104/make_sheet_t104.py --before <dir> --after <dir> --out <file.jpg|.mp4>
        [--movie] [--width 480]

<dir> holds <tag>_fNNNN.png renders of the shot camera (T-095 render_frames.py, tags "before" / "after").
Sheet: the dope sheet (beats of both shots against the reference ranges, content/timing/reference_timing.json) on
top; then one row per shot at the same beats (his contact, offer held, her contact, the shared hold, his release, the
end hold), each column at that shot's own frame of the beat; a reference row underneath (PB f157, PB f172, PB f272,
WT f22, WT f40, WT f110). Movie (--movie): before | after side by side, same camera, 24 fps; the shorter shot holds
its last frame (marked "end")."""
import argparse
import glob
import json
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SHOTS = {"before": "episodes/e907_exchange/shots/s010/shot.scene.json",
         "after": "episodes/e907_exchange/shots/s010_calibrated/shot.scene.json"}
REFS = [("video_paperboat.mp4", 157, "PB f157 lower"), ("video_paperboat.mp4", 172, "PB f172 contact"),
        ("video_paperboat.mp4", 272, "PB f272 hold"), ("video_watertable.mp4", 22, "WT f22 reach end"),
        ("video_watertable.mp4", 40, "WT f40 point hold"), ("video_watertable.mp4", 110, "WT f110 end hold")]
COLORS = {"reach": (70, 130, 200), "hold": (120, 180, 90), "shared_hold": (230, 160, 40), "release": (200, 90, 90),
          "end hold": (150, 150, 150)}


def beats(tag):
    s = json.load(open(os.path.join(ROOT, SHOTS[tag])))
    return s["x_t095_staging"]["beats"], s["frameEnd"]


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
    rows = [("before", *beats("before")), ("after", *beats("after"))]
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
    for tag in ("before", "after"):
        b, _ = beats(tag)
        row = Image.new("RGB", (w * ncol, h), "white")
        for i, (f, name) in enumerate(columns(b)):
            row.paste(label(fit(frame_png(a.before if tag == "before" else a.after, tag, f), w, h), f"{tag}: f{f} {name}"), (i * w, 0))
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


def movie(a):
    def frames(d, tag):
        return sorted(glob.glob(os.path.join(d, f"{tag}_f*.png")))
    fb, fa = frames(a.before, "before"), frames(a.after, "after")
    n = max(len(fb), len(fa))
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            ims = []
            for fl, tag in ((fb, "before (T-095 timing)"), (fa, "after (T-104 calibrated)")):
                im = Image.open(fl[min(i, len(fl) - 1)]).convert("RGB")
                txt = f"{tag}  f{min(i, len(fl) - 1) + 1}" + ("  end" if i >= len(fl) else "")
                ims.append(label(im, txt))
            c = Image.new("RGB", (ims[0].width * 2 + 8, ims[0].height), "white")
            c.paste(ims[0], (0, 0))
            c.paste(ims[1], (ims[0].width + 8, 0))
            c.save(os.path.join(tmp, f"m_{i:04d}.png"))
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "24", "-i", os.path.join(tmp, "m_%04d.png"),
                        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
                        a.out], check=True)
    print(a.out, n, "frames")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--movie", action="store_true")
    ap.add_argument("--width", type=int, default=480)
    a = ap.parse_args()
    movie(a) if a.movie else sheet(a)


main()
