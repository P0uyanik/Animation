#!/usr/bin/env python3
"""R3 step 6: 100 % crops, current (published) master | R3 master, same cameras: face, eyes, eyes closed, ears, hair.

    python3 docs/evaluation/characters/R3/final_crops.py --char <boy|girl|third> --current <master.blend>
        --r3 <master.blend> --out <dir> [--labels "<current label>" "<R3 label>"] [--only face,eyes,closed,ears,hair]

Shared renderers, unchanged: T-109 face_probe.py (face 0.32 m and eyes 0.12 m frames, character_neutral/1 light,
70 mm; eyes closed = face_Blink 1.0), T-159 ear_views.py (full: hair and fibres on, 48 spp, left ear, front / 3/4 /
side, orthographic 0.22 m at 512 px), tools/review/blender_render.py with the T-167 hair cameras (front, 3/4, side,
back; 600 px, 16 spp). One Blender run at a time. Tiles are pasted 1:1 (100 %), never resampled.
Writes <out>/{face,eyes,eyes_closed,ears,hair}_100.jpg."""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "docs", "evaluation", "characters", "T-167", "tools"))
sys.path.insert(0, os.path.join(ROOT, "docs", "evaluation", "characters", "T-160", "tools"))
from hair_crops import VIEWS  # noqa: E402
from hair_views import FRAME  # noqa: E402

BG, BAR, TXT = (92, 92, 96), (20, 20, 20), (240, 240, 240)
IDS = {"boy": "boy_yellow_hoodie", "girl": "girl_auburn_bun_glasses", "third": "girl_white_hair_blue_dress"}


def run(script, args, log):
    with open(log, "w") as f:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup", "-t", "1",
                        "-P", os.path.join(ROOT, script), "--"] + args, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT,
                       check=True)


def compose(title, rows, labels, path):
    """rows: [(row label, [image path per column])]; columns side by side, 1:1."""
    ims = [[Image.open(p).convert("RGB") for p in ps] for _, ps in rows]
    w = max(sum(i.width for i in r) for r in ims)
    h = 20 + sum(max(i.height for i in r) + 18 for r in ims)
    sheet = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(sheet)
    d.rectangle((0, 0, w, 19), fill=BAR)
    d.text((4, 4), title + " | columns: " + " | ".join(labels) + " | 100 %", fill=TXT)
    y = 20
    for (name, _), r in zip(rows, ims):
        d.rectangle((0, y, w, y + 17), fill=BAR)
        d.text((4, y + 3), name, fill=TXT)
        x = 0
        for im in r:
            sheet.paste(im, (x, y + 18))
            x += im.width
        y += max(i.height for i in r) + 18
    sheet.save(path, quality=92)
    print(os.path.basename(path), sheet.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--char", required=True, choices=sorted(IDS))
    ap.add_argument("--current", required=True)
    ap.add_argument("--r3", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--labels", nargs=2, default=["current", "R3"])
    ap.add_argument("--only", default="face,eyes,closed,ears,hair")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    only = set(a.only.split(","))
    cols = [("current", os.path.abspath(a.current)), ("r3", os.path.abspath(a.r3))]
    title = f"R3 {IDS[a.char]}"
    probe = "docs/evaluation/characters/T-109/face_probe.py"
    for what, frame, px, views, controls, samples in (
            ("face", "face", 640, {"front": 0.0, "threequarter": -35.0}, {}, 16),
            ("eyes", "eyes", 1280, {"front": 0.0, "threequarter": -35.0}, {}, 16),
            ("closed", "eyes", 1280, {"front": 0.0, "threequarter": -35.0}, {"face_Blink": 1.0}, 16)):
        if what not in only:
            continue
        d = os.path.join(out, what)
        job = {"out": d, "engine": "cycles", "samples": samples, "px": px, "frame": frame, "views": views,
               "hide": ["fur"], "columns": [{"tag": t, "blend": b, "controls": controls} for t, b in cols]}
        os.makedirs(d, exist_ok=True)
        json.dump(job, open(os.path.join(d, "job.json"), "w"), indent=1)
        run(probe, [os.path.join(d, "job.json")], os.path.join(d, "render_log.txt"))
        name = {"face": "face_100.jpg", "eyes": "eyes_100.jpg", "closed": "eyes_closed_100.jpg"}[what]
        compose(f"{title} {what}" + (" (face_Blink 1.0)" if controls else "") + f" | Cycles {samples} spp",
                [(v, [os.path.join(d, t, v + ".png") for t, _ in cols]) for v in views], a.labels,
                os.path.join(out, name))
    if "ears" in only:
        for t, b in cols:
            d = os.path.join(out, "ears", t)
            os.makedirs(d, exist_ok=True)
            run("docs/evaluation/characters/T-159/tools/ear_views.py", [b, d, "full"], os.path.join(d, "render_log.txt"))
        compose(f"{title} left ear (hair on, 48 spp, ortho 0.22 m)",
                [(v, [os.path.join(out, "ears", t, f"ear_{v}.png") for t, _ in cols]) for v in ("front", "3q", "side")],
                a.labels, os.path.join(out, "ears_100.jpg"))
    if "hair" in only:
        d = os.path.join(out, "hair")
        rows = VIEWS[a.char]
        job = {"out": d, "engine": "cycles", "samples": 16, "px": 600, "lens_mm": 70.0, "sensor_mm": 36.0,
               "calibration": "character_neutral/1",
               "columns": [{"tag": t, "blend": b, "comparison_pose": None} for t, b in cols],
               "views": [dict(FRAME[a.char], name=n, yaw_deg=yaw, elevation_deg=el) for n, yaw, el, _, _ in rows]}
        os.makedirs(d, exist_ok=True)
        json.dump(job, open(os.path.join(d, "job.json"), "w"), indent=1)
        run("tools/review/blender_render.py", [os.path.join(d, "job.json")], os.path.join(d, "render_log.txt"))
        compose(f"{title} hair (T-167 cameras, 16 spp)",
                [(n, [os.path.join(d, t, n + ".png") for t, _ in cols]) for n, *_ in rows], a.labels,
                os.path.join(out, "hair_100.jpg"))


if __name__ == "__main__":
    main()
