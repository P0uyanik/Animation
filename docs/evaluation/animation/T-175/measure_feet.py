"""T-175 feet-planted numbers from an engine bake (plush.shot_bake/1) of the review shot.

    python3 docs/evaluation/animation/T-175/measure_feet.py --bake <run>/bake.json --scene <shot>/shot.scene.json --out feet.json

For every clip action whose clip has foot_plant contacts, on the scene frames where a foot is fully planted (the
clip's contact frames, from foot_in frames into the plant to its end, mapped through the clip's tempo; the action's
blend-in and blend-out frames are left out, a hand-over between two clips is not a plant):
  slide_mm      worst horizontal distance of the ankle pivot from where it was when the plant began;
  vertical_mm   worst vertical distance from there;
  height_mm     planted ankle height relative to the character's rest ankle height (min .. max): floating (+) / sinking (-).
Uses the bake reader of tools/motion_checks (numpy)."""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "motion_checks"))
import shot as SHOT  # noqa: E402


def clip_of(action, scene_path):
    if "file" in action:
        return json.load(open(os.path.join(os.path.dirname(scene_path), "build", action["file"])))
    return json.load(open(os.path.join(ROOT, "content", "clips", action["clip"] + ".clip.json")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    scene = json.load(open(a.scene))
    sh = SHOT.Shot(a.bake)
    frames = list(sh.frames)
    fps = scene["frameRate"][0] / scene["frameRate"][1]
    rows = []
    for act in scene["actions"]:
        if act.get("type") != "clip":
            continue
        clip = clip_of(act, a.scene)
        plants = [c for c in clip.get("contacts", []) if c.get("type") == "foot_plant"]
        if not plants:
            continue
        st = clip.get("style", {})
        tempo, ease = st.get("tempo", 1.0), st.get("foot_in", 2.0)
        ch = next(c for c in sh.characters if c.name == act["character"])
        piv = ch.pivots()
        N, loop = clip["frame_count"], clip.get("loop", False)
        start, end = act["start"], act.get("end", 10 ** 9)
        # a later clip action of the same character takes the legs over from its start (the hand-over is not a plant)
        later = [o["start"] for o in scene["actions"] if o is not act and o.get("type") == "clip" and
                 o["character"] == act["character"] and act["start"] < o.get("start", -1) < end]
        if later:
            end = min(later)
        blend_in, blend_out = act.get("blendIn", 6), act.get("blendOut", 6)
        for role in ("foot.L", "foot.R"):
            if role not in ch.bones:
                continue
            b = ch.bones.index(role)
            rest_y = ch.head[b][1]
            res = {"slide_mm": 0.0, "vertical_mm": 0.0, "lo": 1e9, "hi": -1e9, "frames": 0, "plants": 0}
            cur, p0 = None, None
            for i, f in enumerate(frames):
                if f < start + blend_in or f > min(end - (0 if later else blend_out), frames[-1]):
                    cur = None
                    continue
                cf = (f - start) * tempo * clip["fps"] / fps
                if not loop:
                    cf = min(cf, N - 1)
                base = math.floor(cf / N) * N if loop else 0
                hit = None
                for p in plants:
                    if p["role"] != role:
                        continue
                    for k in ((0, -1) if loop else (0,)):
                        pa, pb = max(0.0, base + k * N + p["frames"][0]), base + k * N + p["frames"][1]
                        s0 = pa + (0.0 if pa <= 0 else min(ease, pb - pa))
                        if pb >= pa and s0 <= cf <= pb:
                            hit = (id(p), base + k * N)
                if hit is None:
                    cur = None
                    continue
                if hit != cur:
                    cur, p0 = hit, piv[i, b].copy()
                    res["plants"] += 1
                d = piv[i, b] - p0
                res["slide_mm"] = max(res["slide_mm"], float(np.hypot(d[0], d[2])) * 1000)
                res["vertical_mm"] = max(res["vertical_mm"], abs(float(d[1])) * 1000)
                res["lo"] = min(res["lo"], float(piv[i, b][1] - rest_y) * 1000)
                res["hi"] = max(res["hi"], float(piv[i, b][1] - rest_y) * 1000)
                res["frames"] += 1
            if res["frames"]:
                rows.append({"character": ch.name, "clip": clip["name"], "foot": role, "plants": res["plants"],
                             "planted_frames": res["frames"], "slide_mm": round(res["slide_mm"], 2),
                             "vertical_mm": round(res["vertical_mm"], 2),
                             "height_mm": [round(res["lo"], 2), round(res["hi"], 2)]})
    out = {"bake": os.path.relpath(a.bake, ROOT), "scene": os.path.relpath(a.scene, ROOT), "rows": rows,
           "worst": {"slide_mm": max(r["slide_mm"] for r in rows), "vertical_mm": max(r["vertical_mm"] for r in rows),
                     "height_mm": [min(r["height_mm"][0] for r in rows), max(r["height_mm"][1] for r in rows)]}}
    json.dump(out, open(a.out, "w"), indent=1)
    for r in rows:
        print(f"{r['character']:5s} {r['clip']:14s} {r['foot']} plants {r['plants']} frames {r['planted_frames']:3d} "
              f"slide {r['slide_mm']:6.2f} mm  vertical {r['vertical_mm']:6.2f} mm  height {r['height_mm'][0]:+.2f} .. {r['height_mm'][1]:+.2f} mm")
    print("worst", json.dumps(out["worst"]))


main()
