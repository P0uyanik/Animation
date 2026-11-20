#!/usr/bin/env python3
"""T-160: writes the hair round 6 overrides (plain Python, deterministic; hair only, opt-in).

    python3 docs/evaluation/characters/T-160/tools/make_overrides.py --base-dir <dir with the T-155 candidate specs>

Each override replaces spec.hair.structures of its T-155 candidate spec (boy 2.3.0, girl 0.14.0, third 0.1.0) with
the same list, edited by the functions below; nothing else of the spec is touched. Output: ../overrides/."""
import argparse
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "overrides")
BASE = {"boy": "boy_yellow_hoodie.2.3.0.spec.json", "girl": "girl_auburn_bun_glasses.0.14.0.spec.json",
        "third": "girl_white_hair_blue_dress.0.1.0.spec.json"}


def by_name(sts):
    return {s.get("name", s["type"]): s for s in sts}


def boy(sts):
    """B05 / val27 back: fewer, rounder locks with open channels at the whorl; taller, uneven crown petals.
    Fringe, sides, back and base are untouched (pickup sightline)."""
    s = by_name(sts)
    r = s["whorl"]["rows"][0]
    r.update(depth=0.9, lift=[0.0, 0.05, 0.042], channel={"gap": 0.28})
    r = s["top"]["rows"][0]
    r.update(depth=0.9, lift=[0.004, 0.05, 0.046], channel={"gap": 0.3})
    s["top_outer"]["rows"][0].update(channel={"gap": 0.22}, depth=0.82)
    s["crown"]["stand"] = {"smooth": 14}
    for k in ("whorl", "top", "top_outer"):
        s[k]["stand"] = {"smooth": 8}
    r = s["crown"]["rows"][0]
    r.pop("channel", None)
    r.update(count=5, ring={"radius_deg": 24, "around": [-88, 88]}, len_deg=14, width=0.095, depth=0.8,
             lift=[-0.004, 0.1], lift_power=1.3, hold=0.5, taper_power=2.1, root_width=0.7,
             stagger={"lift": [0.7, 1.25, 0.95, 0.6, 1.05], "len": [1.0, 1.25, 0.9, 0.8, 1.1],
                      "radius_deg": [3, -5, 6, -2, 4], "width": [0.95, 1.1, 0.85, 1.1, 1.0]})

def girl(sts):
    """G04 / ref_30: sweeps lower over the forehead (less bare arc above the brows), flower towards the front."""
    s = by_name(sts)
    inner_l, outer_l, inner_r, outer_r = s["fringe"]["items"]
    for it, sx in ((inner_l, 1), (inner_r, -1)):
        it.update(tip=[sx * 42, 5], sweep=sx * 0.42, width=0.155, lift=[0.008, 0.04, 0.012])
    for it, sx in ((outer_l, 1), (outer_r, -1)):
        it.update(root=[sx * 12, 68], tip=[sx * 72, -22], width=0.135, sweep=sx * -0.2)
    s["fringe"]["keepout"] = {"az": 30, "el_min": 1.5, "margin_deg": 1}
    s["flowers"]["items"][0].update(around_deg=36, height_frac=0.22, size=0.062, out=0.04,
                                    turn={"toward": [20, 26], "amount": 0.8})


    # G06 / ref_30: every ringlet thins to a soft, flat end and its last coil opens; ends stay staggered
    for st in sts:
        if st["type"] == "locks":
            st["tips"] = {"from": 0.5, "scale": 0.3, "power": 1.3, "flatten": 0.35}
            st["curl"]["tip"] = {"from": 0.65, "radius": 1.05, "pitch": 1.25, "ellipse": 1.0}
    # bun: fewer, broader wrapped strands (wide ridges between deep grooves) instead of fine combing lines
    b = s["bun"]
    b["felt"]["grooves"].update(count=7, depth=0.6, sharpness=0.42, wander=0.3)
    b["buns"][0]["turns"] = 1.3
    for lb in b["buns"][0]["felt_lobes"]:
        lb["swirl"] = round(lb["swirl"] * 1.35, 3)


def third(sts):
    """01 / 02 / 07 / 17_W04: softer, flatter locks with thin wispy ends, a finer and softer fringe edge, buns
    wound from broad strands, a plumper bow seated at the bun base."""
    s = by_name(sts)
    for st in sts:
        if st["type"] == "locks":
            st["tips"] = {"from": 0.58, "scale": 0.3, "power": 1.3, "flatten": 0.4, "calm": 0.5}
            st["thick"] = [round(x * 0.9, 5) for x in st["thick"]]
            st["felt"].update(irregularity=0.16, flatten=0.36)
            st["wave"]["tip_gain"] = 1.0
    f = s["fringe"]
    old = f["items"]
    n = 11
    items = []
    for k in range(n):  # 11 narrower clumps over the same span; ends at designed, uneven heights
        x = k / (n - 1) * (len(old) - 1)
        i = min(int(x), len(old) - 2)
        t = x - i
        a, b = old[i], old[i + 1]
        it = dict(a)
        it["root"] = [round(a["root"][0] + (b["root"][0] - a["root"][0]) * t, 3), a["root"][1]]
        it["tip"] = [round(a["tip"][0] + (b["tip"][0] - a["tip"][0]) * t, 3),
                     round(a["tip"][1] + (b["tip"][1] - a["tip"][1]) * t + (1.5, -1.0, 0.5, -1.5, 0.0)[k % 5], 3)]
        it.update(width=round(0.052 * (1.0, 0.88, 1.08, 0.92)[k % 4], 5), depth=0.5, taper_power=1.7, hold=0.5,
                  curl_deg=4 if it["tip"][0] > 0 else -4, layer=1 + k % 2)
        items.append(it)
    f["items"] = items
    f.update(grooves=3, groove_depth=0.1, tips={"from": 0.7, "scale": 0.7, "power": 1.0, "flatten": 0.3, "round": 0.5})
    s["temples"]["tips"] = {"from": 0.6, "scale": 0.5, "power": 1.2, "flatten": 0.3}
    b = s["buns"]
    b["felt"]["grooves"].update(count=5, depth=0.55, sharpness=0.4, wander=0.3)
    for x in b["buns"]:
        x["turns"] = 1.2
    bow = s["bow"]
    bow.update(knot=0.2)  # seat kept (T-126: on the hair below her right bun); side seats read worse from the front
    for lp in bow["loops"][:2]:
        lp.update(width=0.44, thick=0.34)


EDIT = {"boy": boy, "girl": girl, "third": third}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", required=True)
    ap.add_argument("--only")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for key, fn in EDIT.items():
        if a.only and key != a.only:
            continue
        spec = json.load(open(os.path.join(a.base_dir, BASE[key])))
        sts = copy.deepcopy(spec["hair"]["structures"])
        fn(sts)
        cid = BASE[key].split(".")[0]
        p = os.path.join(OUT, f"{cid}.hair_r6.override.json")
        json.dump({"override": {"generators": {"groom": "groom/5"}, "hair": {"generator": "groom/5", "structures": sts}},
                   "note": f"T-160 hair round 6, opt-in; on {BASE[key]} (T-155 candidate)"}, open(p, "w"), indent=1)
        print(os.path.relpath(p))


if __name__ == "__main__":
    main()
