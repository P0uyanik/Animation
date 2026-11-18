"""T-098L evidence: the f48 comparison sheet (grey studio vs water_table_corner set, review and final settings, with
the references) and the measured render costs (python3, Pillow, ffmpeg).

    python3 docs/evaluation/rendering/T-098L/make_sheet_t098l.py --studio <studio shot build dir> \
        --set <set shot build dir> --out docs/evaluation/rendering/T-098L

<build dir>/runs/{review,final}/render/ hold frame_0048.png and shot_render.json (pipeline/production/run_shot.py
--run-dir review|final). Rows: review settings, final settings; columns: grey studio | set. A reference row: PB f12,
PB f231 (docs/references/video_paperboat.mp4), WT f24 (video_watertable.mp4), zero-based frame indices.
Writes t098l_f48_studio_vs_set_sheet.jpg and costs.json (seconds per frame, per-minute projection at 24 fps)."""
import argparse
import json
import os
import platform
import subprocess
import tempfile

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
REFS = [("video_paperboat.mp4", 12, "PB f12"), ("video_paperboat.mp4", 231, "PB f231"),
        ("video_watertable.mp4", 24, "WT f24")]
W, H = 960, 540
FRAME = 48


def ref_frame(video, n, tmp):
    out = os.path.join(tmp, f"{video}_{n}.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(ROOT, "docs", "references", video),
                    "-vf", f"select=eq(n\\,{n})", "-vframes", "1", out], check=True)
    return Image.open(out).convert("RGB")


def fit(im, w, h):
    im = im.copy()
    im.thumbnail((w, h), Image.LANCZOS)
    c = Image.new("RGB", (w, h), "white")
    c.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return c


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 8 + 6 * len(text), 16], fill=(255, 255, 255))
    d.text((4, 3), text, fill=(0, 0, 0))
    return im


def run_info(build, run):
    d = os.path.join(build, "runs", run, "render")
    rep = json.load(open(os.path.join(d, "shot_render.json")))
    return d, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--studio", required=True)
    ap.add_argument("--set", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    costs = {"frame": FRAME, "fps": 24, "machine": {"cpu_count": os.cpu_count(), "platform": platform.platform(),
                                                     "processor": _cpu()}, "runs": {}}
    sheet = Image.new("RGB", (2 * W, 2 * H + 24 + H * 2 // 3), "white")
    for r, run in enumerate(("review", "final")):
        for c, (tag, build) in enumerate((("grey studio", a.studio), ("water_table_corner set", a.set))):
            d, rep = run_info(build, run)
            frames = rep["frames"][1] - rep["frames"][0] + 1
            spf = rep["render_s"] / frames
            costs["runs"][f"{run}/{'studio' if c == 0 else 'set'}"] = {
                "resolution": rep["resolution"], "samples": rep["samples"], "denoise": True, "engine": rep["engine"],
                "frames": rep["frames"], "render_s": rep["render_s"], "s_per_frame": round(spf, 1),
                "setup_s": rep["setup_s"], "per_minute_cpu_h": round(spf * 24 * 60 / 3600, 2)}
            im = fit(Image.open(os.path.join(d, f"frame_{FRAME:04d}.png")).convert("RGB"), W, H)
            sheet.paste(label(im, f"f{FRAME} {tag} | {run}: {rep['resolution'][0]}x{rep['resolution'][1]}, "
                                  f"{rep['samples']} spp, denoise | {spf:.1f} s/frame"), (c * W, r * H))
    rw, rh = 2 * W // 3, H * 2 // 3
    with tempfile.TemporaryDirectory() as tmp:
        for c, (video, n, name) in enumerate(REFS):
            sheet.paste(label(fit(ref_frame(video, n, tmp), rw, rh), f"reference {name}"), (c * rw, 2 * H + 24))
    ImageDraw.Draw(sheet).text((6, 2 * H + 6), "References (owner videos, zero-based frames): window key, rim on the "
                               "wool, focus and a set", fill=(0, 0, 0))
    out = os.path.join(a.out, "t098l_f48_studio_vs_set_sheet.jpg")
    sheet.save(out, quality=90)
    json.dump(costs, open(os.path.join(a.out, "costs.json"), "w"), indent=1)
    print(out)
    print(json.dumps(costs["runs"], indent=1))


def _cpu():
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


if __name__ == "__main__":
    main()
