#!/usr/bin/env python3
"""T-190: wrong-way table from measure_t190 output (one JSON line per character, hand and frame).

    python3 docs/evaluation/interaction/T-190/summarize.py <label>=<joints.jsonl> ... [--json out.json] [--from-to label a b]

A joint is out of range when (degrees, the anatomical frame of measure_t190.cpp):
  finger knuckle (f<k>a)      flex < -15 or > 95, |side| > 30, |twist| > 15
  finger middle / end joint   flex < -5 or > 115, |side| > 15, |twist| > 15
  thumb base (thumbA)         flex < -15 or > 75, |twist| > 45
  thumb end joint (thumbB)    flex < -10 or > 80, |side| > 30, |twist| > 30 (the keyed full thumb fold rolls it 22)
and "pop" = a joint angle that changes by more than 25 deg between two frames.
Rows: shot, hand, the frames (runs), joint, what is out and by how much (worst value), and the pose's driver read from
the hand tracks at those frames (clip = no hand track: a clip layer or the default hand).
"""
import collections
import json
import sys

LIMITS = {  # kind -> ((flex lo, hi), |side| max, |twist| max)
    "knuckle": ((-15, 95), 30, 15),
    "hinge": ((-5, 115), 15, 15),
    "thumbA": ((-15, 75), None, 45),
    "thumbB": ((-10, 80), 30, 30),
}


def kind(j):
    return j if j.startswith("thumb") else ("knuckle" if j.endswith("a") else "hinge")


def driver(r):
    if not r["owned"]:
        return "clip layer / default hand (no hand track)"
    if "grasp_w" not in r:
        return "hand pose (keyed shape, no grasp)"
    w = "grasp" if r["grasp_w"] > 0.001 else "grasp track, weight 0"
    if r.get("wrap", 0) >= 0.5:
        return w + ", wrap search (T-171 r3)"
    if "graspFace" in r:
        return w + ", per-finger box-face search (T-112c; wrap not keyed)"
    if "band" in r:
        return w + ", per-finger band search (T-051; wrap not keyed)"
    return w + ", single search"


def runs(frames):
    out, a, b = [], None, None
    for f in frames:
        if a is None:
            a = b = f
        elif f == b + 1:
            b = f
        else:
            out.append((a, b))
            a = b = f
    if a is not None:
        out.append((a, b))
    return out


def scan(rows, lo=None, hi=None):
    """[(hand, joint, what, driver)] -> {"frames": [...], "worst": value}; plus pops."""
    res = collections.OrderedDict()
    prev = {}
    for r in rows:
        f = r["frame"]
        if (lo is not None and f < lo) or (hi is not None and f > hi):
            continue
        hand = f'{r["who"]} {r["side"]}'
        for j, (flex, side, twist) in r["joints"].items():
            (flo, fhi), smax, tmax = LIMITS[kind(j)]
            bad = []
            if flex < flo:
                bad.append(("bent backwards", flex))
            if flex > fhi:
                bad.append(("over-flexed", flex))
            if smax is not None and abs(side) > smax:
                bad.append(("bent sideways", side))
            if abs(twist) > tmax:
                bad.append(("twisted about its length", twist))
            p = prev.get((hand, j))
            if p is not None and p[0] == f - 1 and max(abs(a - b) for a, b in zip(p[1], (flex, side, twist))) > 25:
                bad.append(("pop > 25 deg / frame", max(abs(a - b) for a, b in zip(p[1], (flex, side, twist)))))
            prev[(hand, j)] = (f, (flex, side, twist))
            for what, v in bad:
                e = res.setdefault((hand, j, what, driver(r)), {"frames": [], "worst": 0.0})
                e["frames"].append(f)
                if abs(v) > abs(e["worst"]):
                    e["worst"] = v
    return res


def main():
    args, out_json, windows = sys.argv[1:], None, {}
    if "--json" in args:
        i = args.index("--json")
        out_json = args[i + 1]
        del args[i:i + 2]
    while "--from-to" in args:
        i = args.index("--from-to")
        windows[args[i + 1]] = (int(args[i + 2]), int(args[i + 3]))
        del args[i:i + 4]
    table = []
    for a in args:
        label, path = a.split("=", 1)
        rows = [json.loads(line) for line in open(path)]
        lo, hi = windows.get(label, (None, None))
        for (hand, j, what, drv), e in scan(rows, lo, hi).items():
            table.append({"shot": label, "hand": hand, "joint": j, "what": what, "worst_deg": round(e["worst"], 1),
                          "frames": runs(e["frames"]), "n_frames": len(e["frames"]), "driver": drv})
    print("| shot | hand | joint | what | worst, deg | frames (count) | driven by |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for t in table:
        fr = ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in t["frames"][:6]) + (" ..." if len(t["frames"]) > 6 else "")
        print(f'| {t["shot"]} | {t["hand"]} | {t["joint"]} | {t["what"]} | {t["worst_deg"]} | {fr} ({t["n_frames"]}) | {t["driver"]} |')
    print(f"\n{len(table)} rows, {sum(t['n_frames'] for t in table)} joint-frames out of range")
    if out_json:
        json.dump(table, open(out_json, "w"), indent=1)


if __name__ == "__main__":
    main()
