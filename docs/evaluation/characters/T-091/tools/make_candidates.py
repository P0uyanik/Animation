"""T-091: writes the hair round 4 (groom/3) candidate overrides (plain Python, deterministic).

    python3 docs/evaluation/characters/T-091/tools/make_candidates.py [boy|girl ...] [--directional]

Outputs assets/characters/<id>/spec/candidates/T-091/<id>.hair_r4.override.json (and .hair_r4_dirfibres.override.json
with --directional: the same candidate with the directional-fibre experiment flag on). The candidate replaces the
hair structures of the current approved spec (boy 2.0.0, girl 0.11.0) as a whole; fibres, dynamics and materials are
kept unless set here. Dynamics structure names are kept, so the spec's chain settings still apply."""
import copy
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
SPECS = {"boy": "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0.spec.json",
         "girl": "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.11.0.spec.json"}
WHORL = {"az": 180, "el": 78}


def boy(spec):
    h = spec["hair"]
    base = copy.deepcopy(next(s for s in h["structures"] if s["name"] == "base"))
    base.update(height=[0.016, 0.026, 0.03], grooves={"count": 14, "depth": 0.35, "sharpness": 0.7, "wander": 0.3,
                                                       "wavelength": 0.5})
    M = {"seg": 18, "grooves": 1, "groove_depth": 0.2, "irregularity": 0.05, "layer_lift_m": 0.006}
    T = {"hold": 0.32, "taper_power": 1.25, "root_width": 0.8}
    sts = [
        {"type": "scalp_cap", "name": "cap", "offset": 0.004},
        base,
        # layer 0: nape tuck row and the side masses over the ears (B05 lower row, B04 side tips flicking out)
        dict(M, type="masses", name="back", rows=[
            dict(T, count=6, az=[130, 230], el=[12, 20], flow="down", len_deg=[46, 52], width=[0.095, 0.105],
                 depth=0.55, lift=[0.0, 0.012, 0.018], flick_m=0.026, jitter_deg=5, layer=0)]),
        dict(M, type="masses", name="sides", rows=[
            dict(T, count=2, az=[72, 116], el=[16, 24], flow="down", len_deg=[34, 40], width=[0.085, 0.095],
                 depth=0.6, lift=[0.0, 0.02, 0.028], flick_m=0.04, jitter_deg=6, layer=0),
            dict(T, count=2, az=[-116, -72], el=[16, 24], flow="down", len_deg=[34, 40], width=[0.085, 0.095],
                 depth=0.6, lift=[0.0, 0.02, 0.028], flick_m=0.04, jitter_deg=6, layer=0)]),
        # fringe: few large masses hanging over the forehead to the brow line, pointed, with gaps (originals, B01)
        dict(M, type="masses", name="fringe", rows=[
            dict(T, count=4, az=[-50, 50], el=[60, 64], pole=WHORL, len_deg=[58, 64], width=[0.1, 0.11],
                 depth=0.58, lift=[0.0, 0.026, 0.008], flick_m=0.006, curl_deg=8, jitter_deg=4, layer=1)]),
        dict(M, type="masses", name="fringe_centre", items=[
            dict(T, root=[6, 68], tip=[-3, 4], width=0.11, depth=0.55, lift=[0.0, 0.018, 0.008], layer=2)]),
        # long petals from the whorl down over the crown, sides and back (B05)
        dict(M, type="masses", name="top", rows=[
            dict(T, count=9, az=[62, 298], el=[58, 64], pole=WHORL, len_deg=[52, 62], width=[0.105, 0.115],
                 depth=0.62, lift=[0.0, 0.034, 0.036], flick_m=0.04, jitter_deg=5, layer=1)]),
        # crown petals: a ring round the whorl that rises and flares outward, so their pointed tips stand up at the
        # top of the silhouette (B05, val27 front/back), deep channels between them
        dict(M, type="masses", name="crown", root_sink_m=0.016, items=[
            dict(T, root=[az, 76], tip=[az + 8, 60], width=0.08, depth=0.5, lift=[-0.004, 0.07], lift_power=1.8,
                 hold=0.38, taper_power=1.3, root_width=0.6, layer=0)
            for az in (-150, -90, -30, 30, 90, 150)]),
        dict(M, type="masses", name="whorl", root_sink_m=0.016, items=[
            dict(T, root=[az, 86], tip=[az + 12, 66], width=0.066, depth=0.5, lift=[0.0, 0.085], lift_power=1.8,
                 hold=0.34, taper_power=1.25, root_width=0.6, layer=0)
            for az in (-108, 36, 180)]),
    ]
    return {"generator": "groom/3", "structures": sts}


def girl(spec):
    h = spec["hair"]
    by = {s["name"]: copy.deepcopy(s) for s in h["structures"]}
    crown = by["crown"]
    # centre parting (owner 2026-11-18: G01/G02/G04); fewer, larger felt sections on the crown
    crown.update(part={"az": 0, "width_deg": 3.0, "depth": 0.6, "length": 0.62},
                 grooves={"count": 16, "depth": 0.22, "sharpness": 0.65, "wander": 0.3, "wavelength": 0.5})
    M = {"seg": 18, "grooves": 2, "groove_depth": 0.14, "irregularity": 0.05, "layer_lift_m": 0.006}

    def side(sx):  # two swept fringe sections per side of the parting (G04), mirrored
        return [dict(root=[sx * 4, 80], tip=[sx * 56, 8], width=0.13, depth=0.42, lift=[0.004, 0.026, 0.012],
                     lift_peak=0.45, hold=0.55, taper_power=1.8, root_width=0.85, sweep=sx * -0.2, layer=1),
                dict(root=[sx * 16, 64], tip=[sx * 76, -8], width=0.1, depth=0.42, lift=[0.002, 0.02, 0.012],
                     lift_peak=0.45, hold=0.5, taper_power=1.7, root_width=0.85, layer=0)]
    fringe = dict(M, type="masses", name="fringe", items=side(1) + side(-1))
    # soft back transition (ref_30, no G05 ridge): broad felt sections from the crown that run down over the
    # ringlet roots and taper into them, instead of a straight band where the curls start
    back = dict(M, type="masses", name="back_sections", rows=[
        {"count": 6, "az": [132, 228], "el": [38, 50], "flow": "down", "len_deg": [58, 80], "width": [0.11, 0.12],
         "depth": 0.38, "lift": [0.0, 0.01, 0.008], "lift_peak": 0.45, "hold": 0.55, "taper_power": 1.6,
         "jitter_deg": 4, "layer": 1},
        {"count": 2, "az": [98, 124], "el": [30, 38], "flow": "down", "len_deg": [42, 58], "width": [0.09, 0.1],
         "depth": 0.38, "lift": [0.0, 0.009, 0.008], "lift_peak": 0.45, "hold": 0.55, "taper_power": 1.6,
         "jitter_deg": 4, "layer": 0},
        {"count": 2, "az": [-124, -98], "el": [30, 38], "flow": "down", "len_deg": [42, 58], "width": [0.09, 0.1],
         "depth": 0.38, "lift": [0.0, 0.009, 0.008], "lift_peak": 0.45, "hold": 0.55, "taper_power": 1.6,
         "jitter_deg": 4, "layer": 0}])
    # narrower silhouette and tapered ringlets (G05/G06 shape, ref_30 width)
    cur = by["curtain"]
    cur.update(rest_radii=[0.15, 0.13], thick=0.018)
    rings = []
    for k in ("ringlets_side", "ringlets_side_b", "ringlets_back", "ringlets_back_b", "ringlets_outer",
              "ringlets_outer_b"):
        r = by[k]
        r["hang_radii"] = [0.17, 0.155]
        if "rest_radii" in r:
            r["rest_radii"] = [round(r["rest_radii"][0] - 0.03, 3), round(r["rest_radii"][1] - 0.02, 3)]
        r["flare"] = 0.02
        r["end_scale"] = 0.55
        r["tip_frac"] = 0.5
        r["curl"]["tip"] = {"from": 0.7, "radius": 0.8, "pitch": 0.75, "ellipse": 1.0}
        rings.append(r)
    scrunchie = {"type": "scrunchie", "name": "band", "bun": 0, "height_frac": 0.16, "radius_scale": 1.02,
                 "tube": 0.016, "gathers": 11, "gather_depth": 0.42, "width_scale": 1.45, "ruffle": 0.14,
                 "material": "hair_band"}
    sts = [by["cap"], by["bun"], crown, fringe, by["temple_l"], by["temple_r"], cur, back] + rings + \
          [scrunchie, by["flowers"]]
    return {"generator": "groom/3", "structures": sts}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for key in args or ["boy", "girl"]:
        spec = json.load(open(os.path.join(ROOT, SPECS[key])))
        hair = {"boy": boy, "girl": girl}[key](spec)
        cid = spec["identity"]["id"]
        ov = {"override": {"generators": {"groom": "groom/3"}, "hair": hair},
              "notes": f"T-091 hair round 4 candidate (groom/3) on {os.path.basename(SPECS[key])}; unpublished, "
                       "never publish or approve without an owner decision."}
        d = os.path.join(ROOT, "assets", "characters", cid, "spec", "candidates", "T-091")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"{cid}.hair_r4.override.json")
        json.dump(ov, open(p, "w"), indent=1)
        print(os.path.relpath(p, ROOT))
        if "--directional" in sys.argv:
            ov2 = copy.deepcopy(ov)
            ov2["override"]["hair"]["fibres"] = {"directional": {"enabled": True, "strength": 0.9}}
            ov2["notes"] += " Directional-fibre experiment flag on."
            p2 = p.replace(".hair_r4.", ".hair_r4_dirfibres.")
            json.dump(ov2, open(p2, "w"), indent=1)
            print(os.path.relpath(p2, ROOT))


if __name__ == "__main__":
    main()
