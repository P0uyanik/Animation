#!/usr/bin/env python3
"""T-155 strict sheet for the third character (copy of T-126/body_face/sheet.py, second column added):
reference | first version (T-126 build, never published; she has no current version) | candidate 0.1.0 | AI target.

tools/review/recipe.py needs a published current version as baseline, which she does not have. This driver uses the same shared pieces without changing them: tools/review/blender_render.py
(one Blender run, fixed cameras, character_neutral/1 light, face controls zeroed) and
tools/review/strict_sheet.make_sheet (same tiles and layout), with the candidate column only.

    python3 docs/evaluation/characters/T-155/third_sheet.py --first <first master.blend> --blend <candidate master.blend> --out <dir> [--preview]
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "review"))
import strict_sheet  # noqa: E402

REF = "assets/characters/girl_white_hair_blue_dress/references"
UP = REF + "/uploads"
BODY = {"target": [0.0, 0.0, 0.54], "frame_height_m": 1.22, "aspect": 1.6}
FACE = {"target": [0.0, 0.0, 0.745], "frame_height_m": 0.32, "aspect": 1.0}
# (row, label, framing, yaw, reference view, Higgsfield / AI target)
ROWS = [
    ("front", "front", BODY, 0.0, "s02_front", {"file": UP + "/16_higgsfield_W05_dress_tights_boots_2026-11-18.webp", "label": "W05 dress, tights, boots"}),
    ("threequarter", "3/4", BODY, -30.0, "s02_front_left", None),
    ("side", "side", BODY, 90.0, "s02_left", None),
    ("back", "back", BODY, 180.0, "s02_back", {"file": UP + "/17_higgsfield_W04_hair_back_waves_buns_2026-11-18.webp", "label": "W04 hair back"}),
    ("face_front", "face front", FACE, 0.0, "id01_face", {"file": REF + "/views/f14_e1_neutral_soft_smile.jpg", "label": "14 neutral soft smile"}),
    ("face_threequarter", "face 3/4", FACE, -30.0, "f14_head_3q", {"file": UP + "/18_higgsfield_W02_blue_felt_bow_2026-11-18.webp", "label": "W02 bow"}),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", required=True)
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="0.1.0")
    ap.add_argument("--preview", action="store_true", help="cheap: Cycles 2 spp, 120 px")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--px", type=int, default=360)
    a = ap.parse_args()
    samples, px = (2, 120) if a.preview else (a.samples, a.px)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    views = [{"name": r, "yaw_deg": yaw, "elevation_deg": 5.0, "target": fr["target"],
              "frame_height_m": fr["frame_height_m"], "aspect": fr["aspect"]} for r, _, fr, yaw, _, _ in ROWS]
    job = {"out": out, "engine": "cycles", "samples": samples, "px": px, "lens_mm": 70.0, "sensor_mm": 36.0,
           "calibration": "character_neutral/1",
           "columns": [{"tag": "first", "blend": os.path.abspath(a.first), "comparison_pose": None},
                       {"tag": "candidate", "blend": os.path.abspath(a.blend), "comparison_pose": None}],
           "views": views}
    jp = os.path.join(out, "job.json")
    with open(jp, "w") as f:
        json.dump(job, f, indent=1)
    with open(os.path.join(out, "render_log.txt"), "w") as f:
        subprocess.run(["blender", "-b", "--factory-startup",
                        "-P", os.path.join(ROOT, "tools", "review", "blender_render.py"), "--", jp],
                       stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, check=True)
    rs = {"engine": "cycles", "samples": samples}
    resolved = {
        "character": "girl_white_hair_blue_dress", "task": "T-155", "compare": {"variant": "master (A-pose)"},
        "light": {"calibration": "character_neutral/1"}, "render": rs, "preview": rs,
        "recipe_sha256": "no-recipe(T-155-third-driver)",
        "columns": [{"tag": "first", "label": "T-126 first", "role": "(unpublished, no current)"},
                    {"tag": "candidate", "label": a.label, "role": "candidate"}],
        "cameras": {"lens_mm": 70.0, "views": [{"name": r, "label": lab, "elevation_deg": 5.0,
                                                 "framing": "face" if fr is FACE else "body"}
                              for r, lab, fr, _, _, _ in ROWS]},
        "references": {r: {"file": f"{REF}/views/{v}.jpg", "label": v} for r, _, _, _, v, _ in ROWS},
        "ai_target": {"label": "Higgsfield target", "images": {r: t for r, _, _, _, _, t in ROWS if t}},
    }
    name = "preview.jpg" if a.preview else "strict.jpg"
    size = strict_sheet.make_sheet(resolved, out, os.path.join(out, name),
                                   title_note=f"reference | T-126 first version | candidate {a.label} | Higgsfield target")
    print(os.path.join(out, name), size)


if __name__ == "__main__":
    main()
