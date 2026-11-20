#!/usr/bin/env python3
"""T-137 F1b: writes the third girl's eye and fringe overrides (this folder), on top of T-126a's base spec and the
T-126 overrides. Hair: a copy of T-126b's structures with only the fringe changed (deep_merge replaces lists), so
groom_r5 and the T-126 hair override stay untouched.

    python3 docs/evaluation/characters/T-137/f1b/make_overrides.py"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
HAIR = os.path.join(ROOT, "docs/evaluation/characters/T-126/hair/candidates/girl_white_hair_blue_dress.hair.override.json")
FRINGE_DROP_DEG = 13.0   # every fringe tip this much lower (covers more forehead)
FRINGE_EVEN = 0.5       # tips pulled this far towards their mean elevation (a softer, less jagged line)
KEEPOUT_EL_MIN = -8.0   # was 4: the fringe may come down to the brows
FRINGE_TAPER = 1.1      # was 1.8: blunter, softer clump ends
FRINGE_WIDTH = 1.15     # clumps overlap more (fewer gaps)

EYES = {"face": {"eyes": {
    "yaw_deg": 0.0,
    "iris": {"radius": 0.462, "pupil": 0.231},
    "lids": {"upper_edge_deg": 38, "lower_edge_deg": -36, "upper_curve": 1.0, "lower_curve": 0.15, "upper_roll_deg": -18,
             "upper_gap": 0.012, "lower_thickness_m": 0.0005,
             "closed_fit": {"lash_curve": {"out_m": 0.002, "above_seam_deg": 14.0, "sag_deg": 5.0, "corner_lift_deg": 7.0,
                                            "span": [-0.45, 0.75],
                                            "keys": {"Laugh": -1.0, "Squint": 0.0}}}},
    "lash": {"srgb": [70, 44, 36], "span_deg": 56, "strands": {"from_deg": 24, "to_deg": 52}},
    "socket": {"ramp_deg": 12, "reach_deg": 36, "carve_reach": 0.42, "corner_deg": 46, "clearance_m": 0.002,
               "smooth_iterations": 24, "cover_softness": 0.3}}}}


def main():
    hair = json.load(open(HAIR))["override"]["hair"]
    structures = copy.deepcopy(hair["structures"])
    fringe = next(s for s in structures if s["name"] == "fringe")
    mean = sum(i["tip"][1] for i in fringe["items"]) / len(fringe["items"])
    for i in fringe["items"]:
        i["tip"][1] = round(i["tip"][1] + (mean - i["tip"][1]) * FRINGE_EVEN - FRINGE_DROP_DEG, 2)
        i["taper_power"] = FRINGE_TAPER
        i["width"] = round(i["width"] * FRINGE_WIDTH, 5)
    keep = dict(hair["face_keepout"], el_min=KEEPOUT_EL_MIN)
    out = {"override": {"hair": {"face_keepout": keep, "structures": structures}}}
    json.dump(out, open(os.path.join(HERE, "girl_white_hair_blue_dress.fringe.override.json"), "w"), indent=1)
    json.dump(EYES, open(os.path.join(HERE, "girl_white_hair_blue_dress.eyes.override.json"), "w"), indent=1)
    print("fringe tips el:", [i["tip"][1] for i in fringe["items"]])


if __name__ == "__main__":
    main()
