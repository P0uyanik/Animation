#!/usr/bin/env python3
"""T-136 E3: per-frame gaze angle error on an engine bake (plush.shot_bake/1).

For every look action with "atProp" or "atCharacter", in every frame of the look, each eye's error is the angle
between its forward axis (the bone's +Z) and the line from the eye to the exact target:
- for "atProp", the prop's middle (cylinder: half its height above its base);
- for "atCharacter", the midpoint of the partner's two eyes (eye contact).
The report gives, per look, the error (mean of both eyes) and the vergence demand (the angle between the two eyes'
lines to the target: what the eyes must converge, against twice the yaw range) at every frame, and the mean over the look's settled part
(from 11 f after its start, the T-117 min_look_frames). With --expanded (an expanded scene that lists the generated
reaction looks too, e.g. T-117's s010.expanded.scene.json), a look ends where the character's next look (authored or
generated) starts, and generated looks are measured as well (marked "generated").
Usage: measure_gaze_error.py --bake bake.json --scene shot.resolved.scene.json [--expanded x.scene.json] [--json out.json]
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SETTLE = 11


def mat(m):
    return lambda p: [sum(m[c * 4 + r] * (p[c] if c < 3 else 1.0) for c in range(4)) for r in range(3)]


def norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--expanded")
    ap.add_argument("--json")
    a = ap.parse_args()
    bake = json.loads(Path(a.bake).read_text())
    scene = json.loads(Path(a.scene).read_text())
    sdir = Path(a.scene).parent
    frames = {f["frame"]: f for f in bake["frame_data"]}
    eyes = {}
    for c in bake["characters"]:
        cd = next(x for x in scene["characters"] if x["name"] == c["name"])
        pkg = json.loads((sdir / cd["asset"]).read_text())
        heads = {b["name"]: b["head"] for b in pkg["skeleton"]}
        eyes[c["name"]] = [(c["bones"].index(n), heads[n]) for n in ("eye.L", "eye.R")]
    mids = {}
    for p in scene.get("props", []):
        for f in ROOT.glob("content/assets/*.asset.json"):
            d = json.loads(f.read_text())
            if d.get("id") == p["id"]:
                h = d["mesh"].get("height", 0) * d.get("scale", 1.0)
                mids[p["name"]] = [0.0, 0.5 * h, 0.0]

    def eye_state(name, fr):
        skin = frames[fr]["characters"][name]["skin"]
        out = []
        for i, head in eyes[name]:
            m = skin[i * 16:i * 16 + 16]
            out.append((mat(m)(head), norm(m[8:11])))
        return out

    report = {"bake": a.bake, "looks": []}
    authored = [a for a in scene["actions"] if a.get("type") == "look"]
    looks = authored
    if a.expanded:
        looks = [x for x in json.loads(Path(a.expanded).read_text())["actions"] if x.get("type") == "look"]
    looks = sorted(looks, key=lambda x: (x["character"], float(x.get("start", 1))))
    for i, act in enumerate(looks):
        if not ("atProp" in act or "atCharacter" in act):
            continue
        who, s = act["character"], int(math.ceil(float(act["start"])))
        e = int(float(act.get("end", float(act["start"]) + 3)))
        nxt = [float(x["start"]) for x in looks if x["character"] == who and float(x.get("start", 1)) > float(act["start"])]
        if nxt:
            e = min(e, int(math.ceil(min(nxt))) - 1)
        generated = act.get("back", False) or not any(
            x.get("character") == who and float(x.get("start", 1)) == float(act["start"]) for x in authored)
        rows = []
        for fr in range(s, e + 1):
            if fr not in frames:
                continue
            if "atProp" in act:
                t = mat(frames[fr]["props"][act["atProp"]])(mids[act["atProp"]])
            else:
                ps = [p for p, _ in eye_state(act["atCharacter"], fr)]
                t = [(ps[0][k] + ps[1][k]) / 2 for k in range(3)]
            errs, dirs = [], []
            for pos, fwd in eye_state(who, fr):
                d = norm([t[k] - pos[k] for k in range(3)])
                dirs.append(d)
                errs.append(math.degrees(math.acos(max(-1.0, min(1.0, sum(fwd[k] * d[k] for k in range(3)))))))
            verg = math.degrees(math.acos(max(-1.0, min(1.0, sum(dirs[0][k] * dirs[1][k] for k in range(3))))))
            rows.append([fr, round(sum(errs) / 2, 2), round(verg, 1)])
        settled = [r[1] for r in rows if r[0] >= s + SETTLE]
        look = {"character": who, "target": act.get("atProp") or act.get("atCharacter"), "frames": [s, e],
                "generated": generated,
                "settled_mean_deg": round(sum(settled) / len(settled), 2) if settled else None,
                "settled_max_deg": max(settled) if settled else None,
                "settled_vergence_deg": round(sum(r[2] for r in rows if r[0] >= s + SETTLE) / len(settled), 1) if settled else None,
                "per_frame_deg": rows, "per_frame_columns": ["frame", "error_deg (mean of both eyes)", "vergence_deg"]}
        report["looks"].append(look)
        print(f"{who:5s} -> {look['target']:5s} f{s}-{e}{' (generated)' if generated else ''}: settled mean {look['settled_mean_deg']} max {look['settled_max_deg']} deg, vergence {look['settled_vergence_deg']} deg")
    if a.json:
        Path(a.json).write_text(json.dumps(report) + "\n")


if __name__ == "__main__":
    main()
