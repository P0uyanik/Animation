"""T-134 E1b: arc of wrist moves in bakes of the same shot, and a plot of the paths (numpy + Pillow).

arc = largest deviation of the wrist pivot's path from its chord / chord length (0 = a straight line).
Usage: python3 measure_arcs.py --bake name=<bake.json> [--bake ...] --move boy:hand.R:81:97 [--move ...]
           [--out arcs.json] [--plot paths.jpg]
The plot shows each move seen along the direction that shows its bend best (chord horizontal), one colour per bake."""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "tools", "motion_checks"))
from shot import Shot  # noqa: E402

COLOURS = [(120, 120, 120), (200, 60, 40), (30, 110, 200), (40, 150, 70)]


def path(shot, spec):
    who, bone, a, b = spec.split(":")
    c = next(c for c in shot.characters if c.name == who)
    f0 = int(shot.frames[0])
    return c.pivots()[int(a) - f0:int(b) - f0 + 1, c.bones.index(bone)] * 1000.0


def arc(p):
    ch = p[-1] - p[0]
    L = np.linalg.norm(ch)
    off = p - p[0]
    dev = off - np.outer(off @ ch / (L * L), ch)
    return float(L), float(np.linalg.norm(dev, axis=1).max()), dev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bake", action="append", required=True)
    ap.add_argument("--move", action="append", required=True)
    ap.add_argument("--out")
    ap.add_argument("--plot")
    a = ap.parse_args()
    bakes = [(b.split("=", 1)[0], Shot(b.split("=", 1)[1])) for b in a.bake]
    doc = {"format": "plush.t134_arc_measures", "version": 1, "moves": []}
    cell, pad = 300, 30
    img = Image.new("RGB", (cell * len(a.move), cell), "white")
    draw = ImageDraw.Draw(img)
    for m, spec in enumerate(a.move):
        entry = {"move": spec, "bakes": {}}
        paths = [(name, path(shot, spec)) for name, shot in bakes]
        # plot frame: x along the last bake's chord, y along its largest deviation
        L, d, dev = arc(paths[-1][1])
        ref = paths[-1][1]
        x = (ref[-1] - ref[0]) / L
        y = dev[np.argmax(np.linalg.norm(dev, axis=1))]
        y = y / np.linalg.norm(y) if np.linalg.norm(y) > 1e-6 else np.cross(x, [0, 0, 1.0])
        scale = (cell - 2 * pad) / max(L, 1e-6)
        for k, (name, p) in enumerate(paths):
            Lk, dk, _ = arc(p)
            v = np.linalg.norm(np.diff(p, axis=0), axis=1)
            entry["bakes"][name] = {"chord_mm": round(Lk, 1), "deviation_mm": round(dk, 1), "arc": round(dk / Lk, 3),
                                    "speed_mm_f": [round(float(s), 1) for s in v]}
            q = [(m * cell + pad + float((pt - ref[0]) @ x) * scale, cell * 0.62 - float((pt - ref[0]) @ y) * scale) for pt in p]
            draw.line(q, fill=COLOURS[k % len(COLOURS)], width=2)
            for pt in q:
                draw.ellipse([pt[0] - 2, pt[1] - 2, pt[0] + 2, pt[1] + 2], fill=COLOURS[k % len(COLOURS)])
            draw.text((m * cell + 6, 18 + 12 * k), f"{name}: arc {dk / Lk:.3f} ({dk:.1f} mm)", fill=COLOURS[k % len(COLOURS)])
        draw.text((m * cell + 6, 4), f"{spec}  chord {L:.0f} mm, one dot per frame", fill=(0, 0, 0))
        doc["moves"].append(entry)
        print(spec, {n: (e["arc"], e["deviation_mm"]) for n, e in entry["bakes"].items()})
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=1)
            f.write("\n")
    if a.plot:
        img.save(a.plot, quality=90)


if __name__ == "__main__":
    main()
