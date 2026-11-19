#!/usr/bin/env python3
"""T-126b sheet driver: reference | candidate | Higgsfield target (T-087 layout and render side, unchanged) plus
hair views at 100% (no scaling).

She has no published version, so tools/review/recipe.py (which needs a published baseline column) cannot run this
comparison; as T-126a's driver, this one calls the shared pieces without changing them: tools/review/blender_render.py
(one Blender run, fixed cameras, character_neutral/1 light) and tools/review/strict_sheet.make_sheet.

    python3 docs/evaluation/characters/T-126/hair/tools/sheet.py --blend <master.blend> --out <dir> [--preview]
        [--samples 16] [--px 360] [--crop-px 760]
--preview: one cheap frame of every view (Cycles 2 spp, 120 px) -> <out>/preview.jpg. Otherwise <out>/strict.jpg and
<out>/hair_crops.jpg (the hair views side by side, every pixel as rendered) and <out>/sheet.json."""
import argparse
import json
import os
import subprocess
import sys
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "review"))
import strict_sheet  # noqa: E402

REF = "assets/characters/girl_white_hair_blue_dress/references"
UP = REF + "/uploads"
BODY = {"target": [0.0, 0.0, 0.54], "frame_height_m": 1.22, "aspect": 1.6}
FACE = {"target": [0.0, 0.0, 0.765], "frame_height_m": 0.32, "aspect": 1.0}
W04 = {"file": UP + "/17_higgsfield_W04_hair_back_waves_buns_2026-11-18.webp", "label": "W04 hair back"}
W02 = {"file": UP + "/18_higgsfield_W02_blue_felt_bow_2026-11-18.webp", "label": "W02 bow"}
# (row, label, framing, yaw, reference view, Higgsfield target)
ROWS = [("front", "front", BODY, 0.0, "s02_front", None),
        ("threequarter", "3/4", BODY, -30.0, "s02_front_left", None),
        ("side", "side", BODY, 90.0, "s02_left", None),
        ("back", "back", BODY, 180.0, "s02_back", W04),
        ("face_front", "face front", FACE, 0.0, "id01_face", None),
        ("face_threequarter", "face 3/4", FACE, -30.0, "f14_head_3q", W02)]
HAIR = {"target": [0.0, 0.0, 0.7], "frame_height_m": 0.66, "aspect": 1.25}
BOW = {"target": [-0.087, -0.115, 0.875], "frame_height_m": 0.2, "aspect": 1.0}
# (name, framing, yaw, elevation)
CROPS = [("hair_front", HAIR, 0.0, 5.0), ("hair_bow_side", HAIR, -40.0, 8.0), ("hair_side", HAIR, 90.0, 5.0),
         ("hair_back", HAIR, 180.0, 5.0), ("bow", BOW, -35.0, 20.0)]


def render(out, blend, views, samples, px):
    os.makedirs(out, exist_ok=True)
    job = {"out": out, "engine": "cycles", "samples": samples, "px": px, "lens_mm": 70.0, "sensor_mm": 36.0,
           "calibration": "character_neutral/1",
           "columns": [{"tag": "candidate", "blend": os.path.abspath(blend), "comparison_pose": None}], "views": views}
    jp = os.path.join(out, "job.json")
    json.dump(job, open(jp, "w"), indent=1)
    t = time.time()
    with open(os.path.join(out, "render_log.txt"), "w") as f:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup",
                        "-P", os.path.join(ROOT, "tools", "review", "blender_render.py"), "--", jp],
                       stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, check=True)
    return round(time.time() - t, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="T-126b hair (groom/4)")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--px", type=int, default=360)
    ap.add_argument("--crop-px", type=int, default=600)
    a = ap.parse_args()
    samples, px = (2, 120) if a.preview else (a.samples, a.px)
    out = os.path.abspath(a.out)
    views = [{"name": r, "yaw_deg": yaw, "elevation_deg": 5.0, "target": fr["target"],
              "frame_height_m": fr["frame_height_m"], "aspect": fr["aspect"]} for r, _, fr, yaw, _, _ in ROWS]
    secs = {"sheet": render(out, a.blend, views, samples, px)}
    rs = {"engine": "cycles", "samples": samples}
    resolved = {
        "character": "girl_white_hair_blue_dress", "task": "T-126b", "compare": {"variant": "master (A-pose)"},
        "light": {"calibration": "character_neutral/1"}, "render": rs, "preview": rs,
        "recipe_sha256": "no-recipe(T-126b-driver)",
        "columns": [{"tag": "candidate", "label": a.label, "role": "candidate"}],
        "cameras": {"lens_mm": 70.0, "views": [{"name": r, "label": lab, "elevation_deg": 5.0,
                                                 "framing": "face" if fr is FACE else "body"}
                                                for r, lab, fr, _, _, _ in ROWS]},
        "references": {r: {"file": f"{REF}/views/{v}.jpg", "label": v} for r, _, _, _, v, _ in ROWS},
        "ai_target": {"label": "Higgsfield target", "images": {r: t for r, _, _, _, _, t in ROWS if t}}}
    name = "preview.jpg" if a.preview else "strict.jpg"
    size = strict_sheet.make_sheet(resolved, out, os.path.join(out, name),
                                   title_note=f"{a.label}: reference | candidate | Higgsfield target")
    print(os.path.join(out, name), size)
    if not a.preview:
        cdir = os.path.join(out, "crops")
        cviews = [{"name": n, "yaw_deg": yaw, "elevation_deg": el, "target": fr["target"],
                   "frame_height_m": fr["frame_height_m"], "aspect": fr["aspect"]} for n, fr, yaw, el in CROPS]
        secs["crops"] = render(cdir, a.blend, cviews, samples, a.crop_px)
        ims = [Image.open(os.path.join(cdir, "candidate", n + ".png")).convert("RGB") for n, _, _, _ in CROPS]
        strip = Image.new("RGB", (sum(i.width for i in ims), max(i.height for i in ims)), (92, 92, 96))
        x = 0
        for im in ims:
            strip.paste(im, (x, 0))  # 100%: pasted as rendered, never scaled
            x += im.width
        strip.save(os.path.join(out, "hair_crops.jpg"), quality=92)
        print(os.path.join(out, "hair_crops.jpg"), strip.size)
    json.dump({"task": "T-126b", "blend": os.path.basename(a.blend), "label": a.label, "samples": samples, "px": px,
               "crop_px": None if a.preview else a.crop_px, "render_seconds": secs, "rows": [r for r, *_ in ROWS],
               "crops": [] if a.preview else [n for n, *_ in CROPS]},
              open(os.path.join(out, "preview.json" if a.preview else "sheet.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
