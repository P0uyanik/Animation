"""T-134 E1c: overlap and settle around a reach, from bakes of the same shot (numpy + Pillow).

Offsets are bone pivots against the `before` bake, in mm. Per reach (character:start:contact) and per bake:
  chest / head   largest offset, the frame it is reached, the frame the offset first passes half of it (rise) and the
                 frame after which it stays under 0.5 mm (settled)
  *_turn_deg     how far the chest's / head's rotation is from `before` (largest, at the contact, and every second
                 frame of the 12 after it)
  hair           the same for the spring-chain bones (names starting with "DYN-"): largest offset of any of them
  vs <ref>       against another bake (--ref, e.g. the one without overlap): largest head / chest / hair difference
                 after the contact and where
Usage: python3 measure_overlap.py --before <bake> --bake name=<bake> [--bake ...] [--ref name] --reach boy:57:76
           [--out x.json] [--plot x.jpg]"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "tools", "motion_checks"))
from shot import Shot  # noqa: E402

COLOURS = {"chest": (40, 150, 70), "head": (200, 60, 40), "hair": (30, 110, 200)}


def series(shot, before, who):
    c = next(c for c in shot.characters if c.name == who)
    b = next(c for c in before.characters if c.name == who)
    off = np.linalg.norm(c.pivots() - b.pivots(), axis=2) * 1000.0  # (F, B)
    hair = [i for i, n in enumerate(c.bones) if n.startswith("DYN-")]

    def turn(bone):  # angle between the bone's rotation here and in `before`, degrees
        i = c.bones.index(bone)
        R = np.einsum("fij,fkj->fik", c.M[:, i, :3, :3], b.M[:, i, :3, :3])
        return np.degrees(np.arccos(np.clip((np.trace(R, axis1=1, axis2=2) - 1) / 2, -1, 1)))

    rot = {"chest_turn_deg": turn("chest"), "head_turn_deg": turn("head")}
    return {"chest": off[:, c.bones.index("chest")], "head": off[:, c.bones.index("head")],
            "hair": off[:, hair].max(axis=1) if hair else np.zeros(len(off))}, c.pivots() * 1000.0, c.bones, hair, rot


def describe(s, f0, a, b):
    lo, hi = a - f0 - 12, min(len(s) - 1, b - f0 + 45)
    w = s[lo:hi + 1]
    peak = float(w.max())
    rise = int(np.argmax(w >= 0.5 * peak)) if peak > 0 else 0
    late = np.nonzero(s[b - f0:] > 0.5)[0]
    return {"max_mm": round(peak, 2), "max_frame": int(f0 + lo + np.argmax(w)), "half_rise_frame": int(f0 + lo + rise),
            "settled_frame": int(b + (late[-1] + 1 if len(late) else 0))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--bake", action="append", required=True)
    ap.add_argument("--ref")
    ap.add_argument("--reach", action="append", required=True)
    ap.add_argument("--out")
    ap.add_argument("--plot")
    a = ap.parse_args()
    before = Shot(a.before)
    f0 = int(before.frames[0])
    bakes = [(x.split("=", 1)[0], Shot(x.split("=", 1)[1])) for x in a.bake]
    doc = {"format": "plush.t134_overlap_measures", "version": 1, "reaches": []}
    W, H = 420, 200
    img = Image.new("RGB", (W * len(bakes), H * len(a.reach)), "white")
    draw = ImageDraw.Draw(img)
    for r, spec in enumerate(a.reach):
        who, s0, c0 = spec.split(":")
        s0, c0 = int(s0), int(c0)
        entry = {"character": who, "start": s0, "contact": c0, "bakes": {}}
        data = {name: series(shot, before, who) for name, shot in bakes}
        top = max(max(float(v[s0 - f0 - 12:c0 - f0 + 46].max()) for v in d[0].values()) for d in data.values()) or 1.0
        for k, (name, _) in enumerate(bakes):
            ser, piv, bones, hair, rot = data[name]
            e = {part: describe(v, f0, s0, c0) for part, v in ser.items()}
            for part, v in rot.items():
                lo_, hi_ = s0 - f0 - 12, c0 - f0 + 45
                e[part] = {"max_deg": round(float(v[lo_:hi_].max()), 2), "max_frame": int(f0 + lo_ + np.argmax(v[lo_:hi_])),
                           "at_contact_deg": round(float(v[c0 - f0]), 2),
                           "after_contact_deg": [round(float(x), 2) for x in v[c0 - f0:c0 - f0 + 13:2]]}
            if a.ref and a.ref != name:
                rp = data[a.ref][1]
                d = np.linalg.norm(piv - rp, axis=2)[c0 - f0:]
                for part, idx in (("head", [bones.index("head")]), ("chest", [bones.index("chest")]), ("hair", hair)):
                    if idx:
                        m = d[:, idx].max(axis=1)
                        e[f"{part}_vs_{a.ref}_after_contact"] = {"max_mm": round(float(m.max()), 2), "frame": int(c0 + np.argmax(m))}
            entry["bakes"][name] = e
            x0, y0 = k * W, r * H
            lo, hi = s0 - 12, c0 + 45
            draw.text((x0 + 6, y0 + 4), f"{who} reach f{s0}-{c0}, {name}: offset against before (mm), top {top:.1f}", fill=(0, 0, 0))
            for fr, lab in ((s0, "start"), (c0, "contact")):
                x = x0 + 10 + (fr - lo) / (hi - lo) * (W - 20)
                draw.line([x, y0 + 30, x, y0 + H - 12], fill=(200, 200, 200))
                draw.text((x + 2, y0 + H - 12), lab, fill=(120, 120, 120))
            for j, (part, v) in enumerate(ser.items()):
                pts = [(x0 + 10 + (f - lo) / (hi - lo) * (W - 20), y0 + H - 14 - v[f - f0] / top * (H - 50)) for f in range(lo, min(hi, f0 + len(v) - 1) + 1)]
                draw.line(pts, fill=COLOURS[part], width=2)
                draw.text((x0 + 6 + 60 * j, y0 + 16), part, fill=COLOURS[part])
            print(spec, name, json.dumps(e))
        doc["reaches"].append(entry)
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=1)
            f.write("\n")
    if a.plot:
        img.save(a.plot, quality=90)


if __name__ == "__main__":
    main()
