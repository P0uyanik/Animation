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
    r = s["crown"]["rows"][0]
    r.pop("channel", None)
    r.update(count=5, ring={"radius_deg": 24, "around": [-88, 88]}, len_deg=14, width=0.095, depth=0.8,
             lift=[-0.004, 0.125], lift_power=1.3, hold=0.5, taper_power=1.7, root_width=0.7,
             stagger={"lift": [0.8, 1.3, 0.65, 1.2, 0.95], "len": [1.0, 1.25, 0.8, 1.15, 0.9],
                      "radius_deg": [3, -5, 6, -2, 4], "width": [0.95, 1.1, 0.85, 1.1, 1.0]})

def girl(sts):
    """G04 / ref_30: sweeps lower over the forehead (less bare arc above the brows), flower towards the front."""
    s = by_name(sts)
    inner_l, outer_l, inner_r, outer_r = s["fringe"]["items"]
    for it, sx in ((inner_l, 1), (inner_r, -1)):
        it.update(tip=[sx * 42, 7], sweep=sx * 0.42, width=0.155, lift=[0.008, 0.04, 0.012])
    for it, sx in ((outer_l, 1), (outer_r, -1)):
        it.update(root=[sx * 12, 68], tip=[sx * 72, -22], width=0.135, sweep=sx * -0.2)
    s["fringe"]["keepout"] = {"az": 30, "el_min": 3, "margin_deg": 1}
    s["flowers"]["items"][0].update(around_deg=36, height_frac=0.22, size=0.062, out=0.04,
                                    turn={"toward": [20, 26], "amount": 0.8})


EDIT = {"boy": boy, "girl": girl}


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
        json.dump({"override": {"hair": {"structures": sts}},
                   "note": f"T-160 hair round 6, opt-in; on {BASE[key]} (T-155 candidate)"}, open(p, "w"), indent=1)
        print(os.path.relpath(p))


if __name__ == "__main__":
    main()
