#!/usr/bin/env python3
"""T-136 E2: blink timeline of an engine bake (plush.shot_bake/1).

Per character: every blink (run of blink-morph frames > 0.1 that reaches 0.5, as tools/animcheck/personality.py
counts them) as [first, last] frame, and the frames of the e910 key beats it touches.
Usage: blink_timeline.py --bake bake.json --scene shot.resolved.scene.json [--json out.json]
"""
import argparse
import json
from pathlib import Path

WATCH = {"grasp f76-79": (76, 79), "her smile f152-155": (152, 155), "look away f171-181": (171, 181)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    bake = json.loads(Path(a.bake).read_text())
    scene_dir = Path(a.scene).parent
    scene = json.loads(Path(a.scene).read_text())
    frames = sorted(bake["frame_data"], key=lambda f: f["frame"])
    out = {"bake": a.bake, "characters": {}}
    for ent in bake["characters"]:
        name = ent["name"]
        cd = next(c for c in scene["characters"] if c["name"] == name)
        pkg = json.loads((scene_dir / cd["asset"]).read_text())
        blink = pkg.get("expressions", {}).get("blink")
        if blink not in ent.get("morphs", []):
            continue
        k = ent["morphs"].index(blink)
        series = [(f["frame"], f["characters"][name]["morphs"][k]) for f in frames]
        runs, cur = [], None
        for fr, w in series:
            if w > 0.1:
                cur = cur or [fr, fr, 0.0]
                cur[1], cur[2] = fr, max(cur[2], w)
            elif cur:
                runs.append(cur)
                cur = None
        if cur:
            runs.append(cur)
        blinks = [[r[0], r[1]] for r in runs if r[2] >= 0.5]
        hits = {w: [b for b in blinks if b[0] <= e and b[1] >= s] for w, (s, e) in WATCH.items()}
        out["characters"][name] = {"blinks": blinks, "count": len(blinks), "in_watched_frames": hits}
        print(f"{name:5s} {len(blinks)} blinks: " + " ".join(f"f{b[0]}-{b[1]}" for b in blinks))
        for w, h in hits.items():
            print(f"      {w}: " + (", ".join(f"f{b[0]}-{b[1]}" for b in h) or "none"))
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
