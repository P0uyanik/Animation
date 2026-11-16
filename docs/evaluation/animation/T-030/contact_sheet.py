"""T-030 contact sheet of the e905 render: the interaction beats (full frames), then close-ups that follow the
characters (positions projected from the bake): each character's eyes, and the hand/forearm of the arm that is
working against its body. Each close-up is labelled with the frame's measured clearance when a measurement file is
given (measure_e905.cpp output).

    python3 docs/evaluation/animation/T-030/contact_sheet.py --frames <run>/render --bake <run>/bake.json \
        --cast <shot build>/cast.json [--measurements e905_measurements.json] --out <dir>"""
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "pipeline", "clips"))
from t022_contact_sheet import project  # noqa: E402  (engine camera projection)


def bone_world(fd, ch, bones, heads, name, offset=(0.0, 0.0, 0.0)):
    """World position of a point given relative to a bone's rest head (offset in rest/character axes)."""
    i = bones.index(name)
    s = fd["characters"][ch]["skin"][i * 16:(i + 1) * 16]  # column-major skinning matrix
    p = [heads[name][k] + offset[k] for k in range(3)]
    return [s[0 + r] * p[0] + s[4 + r] * p[1] + s[8 + r] * p[2] + s[12 + r] for r in range(3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--bake", required=True)
    ap.add_argument("--cast", required=True)
    ap.add_argument("--measurements")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    bake = json.load(open(a.bake))
    cast = json.load(open(a.cast))
    meas = json.load(open(a.measurements)) if a.measurements else {}
    scene = json.load(open(bake["scene_path"]))
    beats = [(scene["frameStart"], "start")]
    for act in scene["actions"]:
        t = act["type"]
        if t == "grasp":
            beats.append((act["contact"], f"{act['character']} grasps"))
        elif t == "hold" and act["character"] == "boy":
            beats.append((act["end"], f"{act['character']} lifts"))
        elif t == "handover":
            beats += [(act["contact"], f"hand-over -> {act['to']}"), (act["release"], f"{act['character']} lets go")]
    beats.append((scene["frameEnd"], "end"))
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    chars = [c["name"] for c in bake["characters"] if c["supported"]]
    bones = {c["name"]: c["bones"] for c in bake["characters"]}
    heads = {}
    for n in chars:
        pk = json.load(open(os.path.join(cast[n]["package"], "character.json")))
        heads[n] = {b["name"]: b["head"] for b in pk["skeleton"]}
    # the working arm per frame: the character whose right-hand IK is active (from the measurements), else none
    def working(f):
        best = None
        for n in chars:
            rows = meas.get("clearance", {}).get(n, {}).get("R", {}).get("per_frame", [])
            row = next((r for r in rows if r["f"] == f), None)
            if row and row["ik"] > 0.5 and (best is None or row["ik"] > best[1]["ik"]):
                best = (n, row)
        return best
    full = (320, 180)
    tile = 160
    rows = 1 + len(chars) + 1
    sheet = Image.new("RGB", (full[0] * len(beats), full[1] + tile * (rows - 1) + 4 * (rows - 1)), (20, 20, 20))
    for i, (f, label) in enumerate(beats):
        im = Image.open(os.path.join(a.frames, f"frame_{f:04d}.png")).convert("RGB")
        w, h = im.size
        top = im.resize(full, Image.Resampling.LANCZOS)
        d = ImageDraw.Draw(top)
        d.rectangle((0, 0, full[0], 16), fill=(0, 0, 0))
        d.text((4, 3), f"f{f}: {label}", fill=(255, 255, 255))
        sheet.paste(top, (i * full[0], 0))
        x0 = i * full[0] + (full[0] - tile) // 2
        y = full[1] + 4
        cam = frames[f]["camera"]
        for n in chars:  # eyes: a crop centred between the two eye bones
            e = [bone_world(frames[f], n, bones[n], heads[n], s) for s in ("eye.L", "eye.R")]
            mid = [(e[0][k] + e[1][k]) / 2 for k in range(3)]
            cx, cy = project(cam, mid, w, h)
            half = 0.075 * w / 2
            close = im.crop((int(cx - half), int(cy - half), int(cx + half), int(cy + half))).resize((tile, tile), Image.Resampling.LANCZOS)
            d = ImageDraw.Draw(close)
            d.rectangle((0, 0, tile, 13), fill=(0, 0, 0))
            d.text((3, 1), f"{n} eyes", fill=(255, 255, 255))
            sheet.paste(close, (x0, y))
            y += tile + 4
        wk = working(f)
        if wk:  # arm: a crop around the forearm (elbow -> hand) of the working arm, with the body beside it
            n, row = wk
            el = bone_world(frames[f], n, bones[n], heads[n], "forearm.R")
            ha = bone_world(frames[f], n, bones[n], heads[n], "hand.R")
            mid = [(el[k] + ha[k]) / 2 for k in range(3)]
            cx, cy = project(cam, mid, w, h)
            half = 0.16 * w / 2
            close = im.crop((int(cx - half), int(cy - half), int(cx + half), int(cy + half))).resize((tile, tile), Image.Resampling.LANCZOS)
            d = ImageDraw.Draw(close)
            d.rectangle((0, 0, tile, 13), fill=(0, 0, 0))
            d.text((3, 1), f"{n} arm: gap {row['gap_mm']:+.1f} mm", fill=(255, 255, 255))
            sheet.paste(close, (x0, y))
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "e905_contact_sheet.png")
    sheet.save(path)
    print("[t030_contact_sheet] ->", path)


if __name__ == "__main__":
    main()
