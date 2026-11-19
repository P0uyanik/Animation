"""T-118: writes the hair round 5 (groom/4) candidate overrides (plain Python, deterministic).

    python3 docs/evaluation/characters/T-118/tools/make_candidates.py [boy|girl ...]

Outputs docs/evaluation/characters/T-118/candidates/<id>.hair_r5.override.json on the current specs (boy 2.1.0,
girl 0.12.0). Only spec.generators.groom, hair.generator and hair.structures change; structure names that carry
dynamics settings are kept."""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
OUT = os.path.join(HERE, "..", "candidates")
SPECS = {"boy": ("boy_yellow_hoodie", "boy_yellow_hoodie.2.1.0.spec.json"),
         "girl": ("girl_auburn_bun_glasses", "girl_auburn_bun_glasses.0.12.0.spec.json")}
WHORL = {"az": 180, "el": 62}


def by_name(sts, name):
    return next(s for s in sts if s.get("name") == name)


def boy(spec):
    sts = copy.deepcopy(spec["hair"]["structures"])
    M = {k: by_name(sts, "top")[k] for k in ("seg", "grooves", "groove_depth", "irregularity", "layer_lift_m")}
    T = {"hold": 0.45, "taper_power": 1.3}
    # fringe: the two clumps over the eyes end above the lids and lie close to the forehead (open pickup sightline);
    # the centre point and the temple clumps keep the brow line of B01
    fr = by_name(sts, "fringe")["items"]
    for it in fr:
        if abs(it["root"][0]) < 20:
            it.update(tip=[it["tip"][0], 5], lift=[0.008, 0.034, 0.004], width=0.105, flick_m=0.0)
        else:
            it.update(tip=[it["tip"][0] + (10 if it["tip"][0] > 0 else -10), -6], lift=[0.008, 0.04, 0.012])
    by_name(sts, "fringe_centre")["items"][0].update(lift=[0.01, 0.04, 0.006], width=0.085, tip=[-2, -3])
    new = [
        # tier 3: outer ring over the sides and the back (B05: long locks under the crown tiers)
        dict(M, type="masses", name="top_outer", rows=[
            dict(T, count=9, pole=WHORL, ring={"radius_deg": 50, "around": [62, 298]}, len_deg=44, width=0.085,
                 depth=0.72, lift=[0.004, 0.034, 0.034], flick_m=0.035, layer=0, swirl_deg=6, channel={"gap": 0.12},
                 stagger={"len": [1.0, 0.8, 1.12, 0.9, 1.05], "width": [1.0, 0.9, 1.05]})]),
        # tier 2: ring round the whorl, over the roots of tier 3; open channels run down between the petals
        dict(M, type="masses", name="top", rows=[
            dict(T, count=8, pole=WHORL, ring={"radius_deg": 24, "around": [-180, 180]}, len_deg=44, width=0.08,
                 depth=0.78, lift=[0.004, 0.042, 0.04], flick_m=0.04, layer=1, swirl_deg=10, channel={"gap": 0.2},
                 stagger={"len": [1.0, 0.78, 1.15, 0.88], "lift": [1.0, 1.2, 0.85], "radius_deg": [0, 5, -3]})]),
        # tier 1: the whorl itself
        dict(M, type="masses", name="whorl", root_sink_m=0.012, rows=[
            dict(T, count=6, pole=WHORL, ring={"radius_deg": 10, "around": [-180, 180]}, len_deg=30, width=0.07,
                 depth=0.8, lift=[0.0, 0.04, 0.036], flick_m=0.03, layer=2, swirl_deg=16, channel={"gap": 0.15},
                 stagger={"len": [1.0, 0.75, 1.2], "lift": [1.0, 1.25, 0.8, 1.1]})]),
        # crown petals: stand up in front of the whorl at different heights (B05, val27 back)
        dict(M, type="masses", name="crown", root_sink_m=0.016, rows=[
            dict(count=6, pole=WHORL, ring={"radius_deg": 22, "around": [-100, 100]}, len_deg=24, width=0.092,
                 depth=0.6, lift=[-0.004, 0.1], lift_power=1.5, hold=0.36, taper_power=1.3, root_width=0.6,
                 layer=3,
                 stagger={"lift": [0.75, 1.2, 0.6, 1.3, 0.9, 1.05], "len": [1.0, 1.3, 0.8, 1.1, 0.9, 1.2],
                          "radius_deg": [4, -6, 8, -2, 6, -4], "width": [0.9, 1.1, 0.85, 1.15, 1.0, 0.95]})]),
    ]
    keep = [s for s in sts if s["name"] not in ("top", "crown", "whorl")]
    return keep + new, ("whorl pole az 180 el 62; three ring tiers (6 + 8 + 9) with channels and staggered lengths; "
                        "6 standing crown petals of different heights; fringe clumps over the eyes end at el 5 and "
                        "lie closer to the forehead")


def girl(spec):
    sts = copy.deepcopy(spec["hair"]["structures"])
    fr = by_name(sts, "fringe")["items"]
    for it in fr:
        sx = 1 if it["tip"][0] > 0 else -1
        if abs(it["root"][0]) < 10:  # inner sweep: wider, ends lower at the temple
            it.update(tip=[sx * 40, 8], width=0.15, sweep=sx * 0.3)
        else:  # outer sweep: comes down over the outer forehead to the temple
            it.update(root=[sx * 16, 64], tip=[sx * 70, -14], width=0.125, sweep=-sx * 0.12)
    for name, z, mirror in (("ringlets_back", [0.0, 0.05, -0.03, 0.07, 0.02, -0.02, 0.06], 0),
                            ("ringlets_back_b", [0.04, -0.02, 0.06, 0.0, 0.05, -0.03], 0),
                            ("ringlets_outer", [0.0, 0.06], 1), ("ringlets_side", [0.03, -0.02], 1)):
        s = by_name(sts, name)
        s.update(stagger={"z_end": z, "end_scale": [1.0, 0.8, 1.1], "mirror_shift": mirror}, end_scale=0.36,
                 tip_frac=0.3)
    for name in ("ringlets_side_b", "ringlets_outer_b"):
        by_name(sts, name).update(end_scale=0.36, tip_frac=0.3)
    by_name(sts, "flowers")["items"] = [{"around_deg": 38, "height_frac": 0.2, "size": 0.056, "out": 0.034,
                                         "turn": {"toward": [22, 28], "amount": 0.6}}]
    return sts, ("outer sweeps lowered to the temples and widened; back, outer and side ringlets end at staggered "
                 "heights with tapered ends (end scale 0.36); flower at bearing 38 turned towards az 22 el 28")


def main(keys):
    os.makedirs(OUT, exist_ok=True)
    for key in keys:
        cid, f = SPECS[key]
        spec = json.load(open(os.path.join(ROOT, "assets", "characters", cid, "spec", f)))
        sts, note = {"boy": boy, "girl": girl}[key](spec)
        ov = {"override": {"generators": {"groom": "groom/4"}, "hair": {"generator": "groom/4", "structures": sts}},
              "metadata": {"task": "T-118", "base": f, "notes": "T-118 candidate (unpublished, evaluation only): " + note}}
        p = os.path.join(OUT, f"{cid}.hair_r5.override.json")
        with open(p, "w", newline="\n") as fh:
            json.dump(ov, fh, indent=1)
            fh.write("\n")
        print("wrote", os.path.relpath(p, ROOT))


if __name__ == "__main__":
    main(sys.argv[1:] or ["boy", "girl"])
