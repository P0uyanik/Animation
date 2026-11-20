#!/usr/bin/env python3
"""T-167 strict sheet, one driver for the three characters: reference | T-155 candidate + hair r6 | + hair r7 |
AI target. Rows, framings, references and AI targets are those of the T-160 sheets (its two recipes and
third_sheet.py); both render columns are A-pose masters (hair comparison).

tools/review/recipe.py compares a published current version with one candidate; here both columns are opt-in
candidates, so this driver calls the same shared pieces unchanged: tools/review/blender_render.py (one Blender run,
fixed cameras, character_neutral/1 light) and tools/review/strict_sheet.make_sheet.

    python3 docs/evaluation/characters/T-167/tools/strict_r7.py --char <boy|girl|third> --r6 <master.blend>
        --r7 <master.blend> --out <dir> [--preview]
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "review"))
import strict_sheet  # noqa: E402


def _ref(cid):
    return f"assets/characters/{cid}/references"


B, G, W = (_ref("boy_yellow_hoodie"), _ref("girl_auburn_bun_glasses"), _ref("girl_white_hair_blue_dress"))
# per character: id, elevation, body framing, face framing, rows (name, label, framing, yaw, reference, AI target)
CHARS = {
    "boy": ("boy_yellow_hoodie", 6.0, {"target": [0.0, 0.0, 0.56], "frame_height_m": 1.26, "aspect": 1.6},
            {"target": [0.0, 0.0, 0.83], "frame_height_m": 0.4, "aspect": 1.0}, [
        ("front", "front", "body", 0.0, {"file": B + "/views/val27_front.png"}, None),
        ("threequarter", "3/4", "body", -35.0, {"file": B + "/views/val27_threequarter_right.png"}, None),
        ("side", "side", "body", -90.0, {"file": B + "/views/val27_side_right.png"},
         {"file": B + "/uploads/02_higgsfield_B04_hair_side_2026-11-18.webp", "label": "B04"}),
        ("back", "back", "body", 180.0, {"file": B + "/views/val27_back.png"},
         {"file": B + "/uploads/02_higgsfield_B05_hair_back_crown_2026-11-18.webp", "label": "B05"}),
        ("face_front", "face front", "face", 0.0,
         {"file": B + "/views/hero24_front.png", "crop": [40, 60, 560, 620], "label": "hero24 face"},
         {"file": B + "/uploads/02_higgsfield_B01_face_front_2026-11-18.webp", "crop": [150, 300, 1345, 1295],
          "label": "B01"}),
        ("face_threequarter", "face 3/4", "face", -35.0,
         {"file": B + "/views/val27_threequarter_right.png", "crop": [10, 0, 230, 240]},
         {"file": B + "/uploads/02_higgsfield_B02_face_threequarter_2026-11-18.webp", "crop": [200, 200, 1300, 1300],
          "label": "B02"})]),
    "girl": ("girl_auburn_bun_glasses", 5.0, {"target": [0.0, 0.0, 0.56], "frame_height_m": 1.26, "aspect": 1.6},
             {"target": [0.0, 0.0, 0.775], "frame_height_m": 0.32, "aspect": 1.0}, [
        ("front", "front", "body", 0.0, {"file": G + "/views/sheet30_front.png"}, None),
        ("threequarter", "3/4", "body", -45.0, {"file": G + "/views/sheet30_front_left.png"}, None),
        ("side", "side", "body", 90.0, {"file": G + "/views/sheet30_left.png"},
         {"file": G + "/uploads/higgsfield_G06_ringlet_macro_2026-11-18.webp", "label": "G06"}),
        ("back", "back", "body", 180.0, {"file": G + "/views/sheet30_back.png"},
         {"file": G + "/uploads/higgsfield_G05_hair_back_bun_curls_2026-11-18.webp", "label": "G05"}),
        ("face_front", "face front", "face", 0.0,
         {"file": G + "/uploads/ref_30.webp", "crop": [440, 620, 712, 840], "label": "ref_30 Neutral"},
         {"file": G + "/uploads/higgsfield_G04_fringe_hairline_2026-11-18.webp", "label": "G04"}),
        ("face_threequarter", "face 3/4", "face", -45.0,
         {"file": G + "/uploads/ref_30.webp", "crop": [345, 90, 490, 260], "label": "ref_30 front-left"},
         {"file": G + "/uploads/higgsfield_G02_face_threequarter_2026-11-18.webp", "crop": [100, 300, 1393, 1500],
          "label": "G02"})]),
    "third": ("girl_white_hair_blue_dress", 5.0, {"target": [0.0, 0.0, 0.54], "frame_height_m": 1.22, "aspect": 1.6},
              {"target": [0.0, 0.0, 0.745], "frame_height_m": 0.32, "aspect": 1.0}, [
        ("front", "front", "body", 0.0, {"file": W + "/views/s02_front.jpg"},
         {"file": W + "/uploads/01_identity_front.webp", "label": "01 identity"}),
        ("threequarter", "3/4", "body", -30.0, {"file": W + "/views/s02_front_left.jpg"}, None),
        ("side", "side", "body", 90.0, {"file": W + "/views/s02_left.jpg"}, None),
        ("back", "back", "body", 180.0, {"file": W + "/views/s02_back.jpg"},
         {"file": W + "/uploads/17_higgsfield_W04_hair_back_waves_buns_2026-11-18.webp", "label": "W04 hair back"}),
        ("face_front", "face front", "face", 0.0, {"file": W + "/views/id01_face.jpg"},
         {"file": W + "/views/f14_e1_neutral_soft_smile.jpg", "label": "14 neutral soft smile"}),
        ("face_threequarter", "face 3/4", "face", -30.0, {"file": W + "/views/f14_head_3q.jpg"},
         {"file": W + "/uploads/18_higgsfield_W02_blue_felt_bow_2026-11-18.webp", "label": "W02 bow"})]),
}
BASE = {"boy": "2.3.0", "girl": "0.14.0", "third": "0.1.0"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--char", required=True, choices=sorted(CHARS))
    ap.add_argument("--r6", required=True)
    ap.add_argument("--r7", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview", action="store_true", help="cheap: Cycles 2 spp, 120 px")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--px", type=int, default=360)
    a = ap.parse_args()
    cid, elev, body, face, rows = CHARS[a.char]
    fr = {"body": body, "face": face}
    samples, px = (2, 120) if a.preview else (a.samples, a.px)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    views = [dict(fr[f], name=r, yaw_deg=yaw, elevation_deg=elev) for r, _, f, yaw, _, _ in rows]
    job = {"out": out, "engine": "cycles", "samples": samples, "px": px, "lens_mm": 70.0, "sensor_mm": 36.0,
           "calibration": "character_neutral/1",
           "columns": [{"tag": "r6", "blend": os.path.abspath(a.r6), "comparison_pose": None},
                       {"tag": "r7", "blend": os.path.abspath(a.r7), "comparison_pose": None}],
           "views": views}
    jp = os.path.join(out, "job.json")
    with open(jp, "w") as f:
        json.dump(job, f, indent=1)
    with open(os.path.join(out, "render_log.txt"), "w") as f:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "bpy_blender.py"), "-b", "--factory-startup",
                        "-P", os.path.join(ROOT, "tools", "review", "blender_render.py"), "--", jp],
                       stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, check=True)
    rs = {"engine": "cycles", "samples": samples}
    v = BASE[a.char]
    resolved = {
        "character": cid, "task": "T-167", "compare": {"variant": "master (A-pose)"},
        "light": {"calibration": "character_neutral/1"}, "render": rs, "preview": rs,
        "recipe_sha256": "no-recipe(T-167-driver)",
        "columns": [{"tag": "r6", "label": f"{v} cand. + hair r6", "role": "opt-in base"},
                    {"tag": "r7", "label": f"{v} cand. + hair r7", "role": "candidate"}],
        "cameras": {"lens_mm": 70.0, "views": [{"name": r, "label": lab, "elevation_deg": elev, "framing": f}
                                                for r, lab, f, _, _, _ in rows]},
        "references": {r: ref for r, _, _, _, ref, _ in rows},
        "ai_target": {"label": "AI target", "images": {r: t for r, _, _, _, _, t in rows if t}},
    }
    name = "preview.jpg" if a.preview else "strict.jpg"
    size = strict_sheet.make_sheet(resolved, out, os.path.join(out, name),
                                   title_note=f"reference | {v} + hair r6 | {v} + hair r7 | AI target")
    print(os.path.join(out, name), size)


if __name__ == "__main__":
    main()
