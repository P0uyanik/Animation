"""T-022 contact sheet of the e905 props test render: the beats of the hand-prop interaction, full frames plus a
close crop around the cup that follows it (its position projected from the bake).

    python3 pipeline/clips/t022_contact_sheet.py --frames <run>/render --bake <run>/bake.json --out <dir>

Beat frames are read from the shot's actions (grasp contact, hold end, hand-over contact, release, end)."""
import argparse
import json
import math
import os

from PIL import Image, ImageDraw


def project(cam, p, w, h):
    """Engine camera (position, target, focalMm, sensorWidthMm; +Y up) -> pixel of world point p."""
    c, t = cam["position"], cam["target"]
    f = [t[i] - c[i] for i in range(3)]
    n = math.sqrt(sum(x * x for x in f))
    f = [x / n for x in f]
    r = [-f[2], 0.0, f[0]]  # right = forward x up (+Y)
    rn = math.sqrt(sum(x * x for x in r))
    r = [x / rn for x in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]  # right x forward
    d = [p[i] - c[i] for i in range(3)]
    z = sum(d[i] * f[i] for i in range(3))
    x = sum(d[i] * r[i] for i in range(3)) / z
    y = sum(d[i] * u[i] for i in range(3)) / z
    k = cam["focalMm"] / cam.get("sensorWidthMm", 36.0) * w
    return w / 2 + x * k, h / 2 - y * k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--bake", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    bake = json.load(open(a.bake))
    scene = json.load(open(bake["scene_path"]))
    beats = [(scene["frameStart"], "start")]
    for act in scene["actions"]:
        t = act["type"]
        if t == "grasp":
            beats.append((act["contact"], f"{act['character']} grasps (contact)"))
        elif t == "hold" and act["character"] == "boy":
            beats.append((act["end"], f"{act['character']} lifts"))
        elif t == "handover":
            beats += [(act["contact"], f"hand-over contact -> {act['to']}"), (act["release"], f"{act['character']} lets go")]
    beats.append((scene["frameEnd"], "end"))
    frames = {fd["frame"]: fd for fd in bake["frame_data"]}
    full = (320, 180)
    crop = 200
    sheet = Image.new("RGB", (full[0] * len(beats), full[1] + crop), (20, 20, 20))
    for i, (f, label) in enumerate(beats):
        im = Image.open(os.path.join(a.frames, f"frame_{f:04d}.png")).convert("RGB")
        w, h = im.size
        tile = im.resize(full, Image.Resampling.LANCZOS)
        d = ImageDraw.Draw(tile)
        d.rectangle((0, 0, full[0], 16), fill=(0, 0, 0))
        d.text((4, 3), f"f{f}: {label}", fill=(255, 255, 255))
        sheet.paste(tile, (i * full[0], 0))
        m = frames[f]["props"]["cup"]
        cx, cy = project(frames[f]["camera"], (m[12], m[13] + 0.05, m[14]), w, h)
        half = 0.16 * w / 2
        box = (int(cx - half), int(cy - half), int(cx + half), int(cy + half))
        close = im.crop(box).resize((crop, crop), Image.Resampling.LANCZOS)
        sheet.paste(close, (i * full[0] + (full[0] - crop) // 2, full[1]))
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "e905_contact_sheet.png")
    sheet.save(path)
    print("[t022_contact_sheet] ->", path)


if __name__ == "__main__":
    main()
