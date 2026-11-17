"""Integration batch 1: one contact sheet over several rendered shots (python3 + Pillow).

    python3 docs/evaluation/integration/batch1/contact_sheet.py --out <png> \
        --shot LABEL:<run dir>:<shot build dir>[:<measure_e905 json>] [--shot ...]

Per shot, one block of beats (the interaction beats when the scene has grasp/hand-over actions, else evenly spaced
frames). Under each full frame: per character an eye close-up, a head/hair close-up and a right forearm/hand
close-up, positioned by projecting the baked bones (T-030 contact_sheet.py / T-022 projection). With a measurement file
the arm tile carries that frame's arm-body gap."""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "animation", "T-030"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "pipeline", "clips"))
from contact_sheet import bone_world  # noqa: E402  (T-030)
from t022_contact_sheet import project  # noqa: E402

FULL, TILE = (320, 180), 106


def beats_for(scene, bake):
    f0, f1 = bake["frames"]
    b = [(f0, "start")]
    for act in scene.get("actions", []):
        if act.get("type") == "grasp":
            b.append((act["contact"], f"{act['character']} grasps"))
        elif act.get("type") == "handover":
            b += [(act["contact"], "hand-over"), (act["release"], "release")]
    if len(b) == 1:
        n = 6
        b += [(round(f0 + (f1 - f0) * k / (n - 1)), "") for k in range(1, n - 1)]
    b.append((f1, "end"))
    return b


def crop(im, cx, cy, half, label):
    c = im.crop((int(cx - half), int(cy - half), int(cx + half), int(cy + half))).resize((TILE, TILE), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, TILE, 12), fill=(0, 0, 0))
    d.text((2, 0), label, fill=(255, 255, 255))
    return c


def block(label, run, build, meas_path):
    bake = json.load(open(os.path.join(run, "bake.json")))
    scene = json.load(open(bake["scene_path"]))
    cast = json.load(open(os.path.join(build, "cast.json")))
    meas = json.load(open(meas_path)) if meas_path else {}
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    chars = [c["name"] for c in bake["characters"] if c.get("supported", True)]
    bones = {c["name"]: c["bones"] for c in bake["characters"]}
    heads = {}
    for n in chars:
        pk = json.load(open(os.path.join(cast[n]["package"], "character.json")))
        heads[n] = {b["name"]: b["head"] for b in pk["skeleton"]}
    beats = beats_for(scene, bake)
    sub_w = FULL[0] // 3
    rows_h = len(chars) * (TILE + 2)
    img = Image.new("RGB", (FULL[0] * len(beats), 18 + FULL[1] + rows_h), (20, 20, 20))
    ImageDraw.Draw(img).text((4, 3), label, fill=(255, 220, 120))
    for i, (f, lab) in enumerate(beats):
        im = Image.open(os.path.join(run, "render", f"frame_{f:04d}.png")).convert("RGB")
        w, h = im.size
        top = im.resize(FULL, Image.Resampling.LANCZOS)
        d = ImageDraw.Draw(top)
        d.rectangle((0, 0, FULL[0], 14), fill=(0, 0, 0))
        d.text((4, 1), f"f{f} {lab}", fill=(255, 255, 255))
        img.paste(top, (i * FULL[0], 18))
        cam = frames[f]["camera"]
        y = 18 + FULL[1] + 2
        for n in chars:
            fd = frames[f]
            e = [bone_world(fd, n, bones[n], heads[n], s) for s in ("eye.L", "eye.R")]
            mid = [(e[0][k] + e[1][k]) / 2 for k in range(3)]
            cx, cy = project(cam, mid, w, h)
            x = i * FULL[0] + (sub_w - TILE) // 2
            img.paste(crop(im, cx, cy, 0.075 * w / 2, f"{n} eyes"), (x, y))
            img.paste(crop(im, cx, cy, 0.22 * w / 2, f"{n} head/hair"), (x + sub_w, y))
            el = bone_world(fd, n, bones[n], heads[n], "forearm.R")
            ha = bone_world(fd, n, bones[n], heads[n], "hand.R")
            m = [(el[k] + ha[k]) / 2 for k in range(3)]
            ax, ay = project(cam, m, w, h)
            row = next((r for r in meas.get("clearance", {}).get(n, {}).get("R", {}).get("per_frame", []) if r["f"] == f), None)
            txt = f"{n} R arm" + (f" {row['gap_mm']:+.1f}mm ik{row['ik']:.1f}" if row else "")
            img.paste(crop(im, ax, ay, 0.16 * w / 2, txt), (x + 2 * sub_w, y))
            y += TILE + 2
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", action="append", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    blocks = []
    for s in a.shot:
        parts = s.split(":")
        blocks.append(block(parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else None))
    W = max(b.width for b in blocks)
    sheet = Image.new("RGB", (W, sum(b.height + 6 for b in blocks)), (10, 10, 10))
    y = 0
    for b in blocks:
        sheet.paste(b, (0, y))
        y += b.height + 6
    sheet.save(a.out)
    print(a.out, sheet.size)


if __name__ == "__main__":
    main()
