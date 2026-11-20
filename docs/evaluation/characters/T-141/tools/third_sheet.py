#!/usr/bin/env python3
"""T-141 strict sheet for girl_white_hair_blue_dress (no published version, so tools/review/recipe.py cannot run;
same approach as docs/evaluation/characters/T-126/hair/tools/sheet.py): reference | T-126b hair | + hair curves
(add) | hair curves replace the felt fibres | Higgsfield target, through the unchanged shared pieces
tools/review/blender_render.py (one Blender run, fixed cameras, character_neutral/1) and strict_sheet.make_sheet.

    python3 docs/evaluation/characters/T-141/tools/third_sheet.py --out <dir> [--preview] \
        base=<blend> add=<blend> replace=<blend>"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "review"))
import strict_sheet  # noqa: E402

REF = "assets/characters/girl_white_hair_blue_dress/references"
BODY = {"target": [0.0, 0.0, 0.54], "frame_height_m": 1.22, "aspect": 1.6}
FACE = {"target": [0.0, 0.0, 0.765], "frame_height_m": 0.32, "aspect": 1.0}
W04 = {"file": REF + "/uploads/17_higgsfield_W04_hair_back_waves_buns_2026-11-18.webp", "label": "W04 hair back"}
ROWS = [("front", "front", BODY, 0.0, "s02_front", None), ("threequarter", "3/4", BODY, -30.0, "s02_front_left", None),
        ("side", "side", BODY, 90.0, "s02_left", None), ("back", "back", BODY, 180.0, "s02_back", W04),
        ("face_front", "face front", FACE, 0.0, "id01_face", None),
        ("face_threequarter", "face 3/4", FACE, -30.0, "f14_head_3q", None)]
LABELS = {"base": "T-126b hair (felt fibres)", "add": "+ hair curves", "replace": "hair curves, felt fibres off"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("variants", nargs="+")
    a = ap.parse_args()
    samples, px = (2, 120) if a.preview else (16, 360)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    cols = [v.split("=", 1) for v in a.variants]
    views = [{"name": r, "yaw_deg": yaw, "elevation_deg": 5.0, "target": fr["target"],
              "frame_height_m": fr["frame_height_m"], "aspect": fr["aspect"]} for r, _, fr, yaw, _, _ in ROWS]
    job = {"out": out, "engine": "cycles", "samples": samples, "px": px, "lens_mm": 70.0, "sensor_mm": 36.0,
           "calibration": "character_neutral/1", "views": views,
           "columns": [{"tag": t, "blend": os.path.abspath(b), "comparison_pose": None} for t, b in cols]}
    jp = os.path.join(out, "job.json")
    json.dump(job, open(jp, "w"), indent=1)
    t = time.time()
    with open(os.path.join(out, "render_log.txt"), "w") as f:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup",
                        "-P", os.path.join(ROOT, "tools", "review", "blender_render.py"), "--", jp],
                       stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, check=True)
    secs = round(time.time() - t, 1)
    rs = {"engine": "cycles", "samples": samples}
    resolved = {
        "character": "girl_white_hair_blue_dress", "task": "T-141", "compare": {"variant": "master (A-pose)"},
        "light": {"calibration": "character_neutral/1"}, "render": rs, "preview": rs,
        "recipe_sha256": "no-recipe(T-141-driver)",
        "columns": [{"tag": t, "label": LABELS.get(t, t), "role": "baseline" if t == "base" else "candidate"}
                    for t, _ in cols],
        "cameras": {"lens_mm": 70.0, "views": [{"name": r, "label": lab, "elevation_deg": 5.0,
                                                 "framing": "face" if fr is FACE else "body"}
                                                for r, lab, fr, _, _, _ in ROWS]},
        "references": {r: {"file": f"{REF}/views/{v}.jpg", "label": v} for r, _, _, _, v, _ in ROWS},
        "ai_target": {"label": "Higgsfield target", "images": {r: t for r, _, _, _, _, t in ROWS if t}}}
    name = "preview.jpg" if a.preview else "strict.jpg"
    size = strict_sheet.make_sheet(resolved, out, os.path.join(out, name),
                                   title_note="T-141 experiment: reference | T-126b | + hair curves | replace | target")
    json.dump({"task": "T-141", "samples": samples, "px": px, "render_seconds": secs, "columns": [t for t, _ in cols],
               "rows": [r for r, *_ in ROWS]}, open(os.path.join(out, name.replace(".jpg", ".json")), "w"), indent=1)
    print(os.path.join(out, name), size, secs, "s")


if __name__ == "__main__":
    main()
