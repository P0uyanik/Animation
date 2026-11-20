#!/usr/bin/env python3
"""T-167: writes the hair round 7 overrides (plain Python, deterministic; hair only, opt-in).

    python3 docs/evaluation/characters/T-167/tools/make_overrides.py --base-dir <T-155 candidate specs> [--only boy|girl|third]

Each override is the T-160 round 6 override of the character (../../T-160/overrides, the opt-in base), edited by the
functions below. As in T-160 an override replaces generators.groom, hair.generator and hair.structures of the T-155
candidate spec; the girls' overrides also set hair.fibres / materials.assignments.hair values where named below.
Output: ../overrides/."""
import argparse
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "overrides")
R6 = os.path.join(HERE, "..", "..", "T-160", "overrides")
IDS = {"boy": "boy_yellow_hoodie", "girl": "girl_auburn_bun_glasses", "third": "girl_white_hair_blue_dress"}
BASE = {"boy": "2.3.0", "girl": "0.14.0", "third": "0.1.0"}


def by_name(sts):
    return {s.get("name", s["type"]): s for s in sts}


def boy(sts, extra):
    """val27 (front, 3/4, side, back), B04: chunky clumps with blunt ends that differ from their neighbours, a
    round mop without long side spikes, an uneven fringe, a few short crown tufts instead of a fan of petals.
    The fringe never reaches lower than in round 6 (pickup sightline)."""
    s = by_name(sts)
    blunt = {"hold": 0.5, "taper_power": 2.6}  # mass profile: full width for longer, then a short rounded end

    def nat(seed, bend=0.008, twist=24):
        return {"bend_m": bend, "twist_deg": twist, "lumps": 0.07, "lump_wavelength": 0.7, "seed": seed}
    # fringe: same five clumps, shorter by different amounts, plus two short tufts between them
    f = s["fringe"]["items"]
    f[0].update(tip=[12, 12], width=0.096)
    f[1].update(tip=[-15, 11], width=0.106)
    f[2].update(tip=[47, 0], width=0.104, flick_m=0.004)
    f[3].update(tip=[-52, -1], width=0.108, flick_m=0.004)
    for az, el, w, lay in ((27, 16, 0.066, 2), (-30, 13, 0.074, 2)):
        f.append(dict(f[0], root=[az * 0.8, 62], tip=[az, el], width=w, layer=lay))
    for it in f + s["fringe_centre"]["items"]:
        it.update(hold=0.42, taper_power=1.5)
    s["fringe"]["clump"] = nat(3, 0.005, 16)
    s["fringe_centre"]["clump"] = nat(0, 0.003, 10)
    # sides and back: hang down around the head (no long outward flicks), blunt, uneven
    for r in s["sides"]["rows"]:
        r.update(blunt, count=3, flick_m=0.016, len_deg=[37, 47], width=[0.085, 0.115], jitter_deg=9)
    s["sides"]["clump"] = nat(1)
    s["back"]["rows"][0].update(blunt, count=7, flick_m=0.014, len_deg=[40, 52], width=[0.09, 0.115], jitter_deg=8)
    s["back"]["clump"] = nat(5)
    # whorl tiers: shorter, thicker clumps of clearly different lengths; narrower channels
    s["top_outer"]["rows"][0].update(blunt, len_deg=38, width=0.095, flick_m=0.016, channel={"gap": 0.14},
                                     stagger={"len": [1.0, 0.72, 1.14, 0.84, 1.06, 0.66, 0.94],
                                              "width": [1.0, 0.82, 1.12, 0.9], "lift": [1.0, 1.25, 0.8, 1.1, 0.9]})
    s["top"]["rows"][0].update(blunt, len_deg=38, width=0.09, flick_m=0.016, channel={"gap": 0.16},
                               stagger={"len": [1.0, 0.7, 1.12, 0.82, 0.94], "lift": [1.0, 1.25, 0.8],
                                        "radius_deg": [0, 6, -4, 3], "width": [1.0, 0.85, 1.1]})
    s["whorl"]["rows"][0].update(blunt, count=5, len_deg=27, width=0.08, flick_m=0.012, channel={"gap": 0.16},
                                 stagger={"len": [1.0, 0.7, 1.15, 0.85], "lift": [1.0, 1.25, 0.8, 1.1],
                                          "width": [1.0, 0.85, 1.1]})
    for k, sd in (("top_outer", 2), ("top", 7), ("whorl", 4)):
        s[k]["clump"] = nat(sd, 0.009, 26)
    # crown: three short tufts of different heights (val27 front / side) instead of five broad petals
    r = s["crown"]["rows"][0]
    r.update(count=3, ring={"radius_deg": 20, "around": [-70, 62]}, len_deg=12, width=0.07, depth=0.85,
             lift=[-0.004, 0.07], taper_power=1.9,
             stagger={"lift": [1.15, 0.6, 0.9], "len": [1.1, 0.8, 1.0], "radius_deg": [-3, 6, 2],
                      "width": [1.05, 0.85, 1.0]})
    s["crown"]["clump"] = nat(2, 0.006, 14)


def girl(sts, extra):
    """ref_30, G04, G05, G06: open spiral ringlets (a ribbon wound round a wide coil, not a thick rope), longer at
    the back, less fuzz and more gloss; a smoother, tidier bun; sweeps that leave more forehead bare."""
    s = by_name(sts)
    inner_l, outer_l, inner_r, outer_r = s["fringe"]["items"]
    for it, sx in ((inner_l, 1), (inner_r, -1)):
        it.update(tip=[sx * 46, 16], sweep=sx * 0.5, width=0.14)
    for it, sx in ((outer_l, 1), (outer_r, -1)):
        it.update(root=[sx * 14, 66], tip=[sx * 74, -12], width=0.125)
    s["fringe"]["keepout"] = {"az": 30, "el_min": 8, "margin_deg": 1}
    for st in sts:
        if st["type"] != "locks":
            continue
        back = "back" in st["name"]
        st["width"] = [round(x * 0.9, 4) for x in st["width"]]
        st["thick"] = [round(x * 0.56, 4) for x in st["thick"]]
        c = st["curl"]
        c.update(radius=round(c["radius"] * 1.25, 4), pitch=round(c["pitch"] * 0.72, 4), jitter=0.12, wobble=0.1,
                 ellipse=0.9)
        c["tip"] = {"from": 0.7, "radius": 1.1, "pitch": 1.15, "ellipse": 1.0}
        st["felt"].update(irregularity=0.05, flatten=0.3, flatten_twist=0.6)
        st["tips"] = {"from": 0.7, "scale": 0.6, "power": 1.3, "flatten": 0.2}
        st["end_scale"] = 0.6
        if back:  # G05: the back curls reach the waist; the side curls keep their length (clear of the sleeves)
            st["z_end"] = [round(z - 0.06, 3) for z in st["z_end"]]
    s["curtain"]["z_end"] = [[az, round(z + 0.05, 3)] for az, z in s["curtain"]["z_end"]]  # more curl length shows
    b = s["bun"]
    b["felt"]["grooves"].update(count=12, depth=0.28, sharpness=0.5, wander=0.12)
    b["felt"]["lumps"]["amount"] = 0.03
    b["buns"][0]["turns"] = 1.0
    for lb in b["buns"][0]["felt_lobes"]:
        lb["swirl"] = round(lb["swirl"] / 1.35 * 0.8, 3)
    layers = copy.deepcopy(extra["base"]["hair"]["fibres"]["layers"])
    for ly in layers:  # shorter, sparser fuzz: the curl surface reads, the outline keeps a thin halo
        f = ly["overrides"]["fibres"]
        k = {"felt": (0.45, 0.6), "halo": (0.5, 0.75), "flyaways": (1.0, 1.0)}[ly["name"]]
        f.update(density_per_cm2=round(f["density_per_cm2"] * k[0], 3), length_mm=round(f["length_mm"] * k[1], 2))
    extra["hair"] = {"fibres": dict(extra["base"]["hair"]["fibres"], layers=layers)}
    extra["materials"] = {"assignments": {"hair": {"overrides": {
        "surface": {"roughness": 0.62, "specular_ior_level": 0.35}, "nap": {"fibre_gloss": 0.45, "sheen_gain": 0.5}}}}}


def third(sts, extra):
    """01 / 02: a fringe of many thin, flat, soft-ended wisps with a gently uneven edge (no row of points); fuller
    side and back hair: wider, thicker locks that keep their body to the end, more of them beside the cheeks.
    Bow seat unchanged (owner decision pending)."""
    s = by_name(sts)
    f = s["fringe"]
    old = f["items"]
    n = 19
    items = []
    for k in range(n):
        x = k / (n - 1) * (len(old) - 1)
        i = min(int(x), len(old) - 2)
        t = x - i
        p, q = old[i], old[i + 1]
        it = dict(p)
        it["root"] = [round(p["root"][0] + (q["root"][0] - p["root"][0]) * t, 3), p["root"][1]]
        # the edge follows the round 6 line smoothed over its zigzag, with small designed steps
        base_el = sum(o["tip"][1] for o in old[max(0, i - 1):i + 3]) / len(old[max(0, i - 1):i + 3])
        it["tip"] = [round(p["tip"][0] + (q["tip"][0] - p["tip"][0]) * t, 3),
                     round(base_el + 5.0 + (0.9, -0.5, 0.3, -0.9, 0.6, 0.0, -0.3)[k % 7], 3)]
        it.update(width=round(0.04 * (1.0, 0.8, 1.15, 0.9, 1.05)[k % 5], 5), depth=0.42, hold=0.62, taper_power=2.6,
                  curl_deg=3 if it["tip"][0] > 0 else -3, layer=k % 3)
        items.append(it)
    f["items"] = items
    f.update(grooves=2, groove_depth=0.08, tips={"from": 0.55, "scale": 0.85, "power": 1.0, "flatten": 0.6},
             clump={"bend_m": 0.003, "twist_deg": 8, "lumps": 0.05, "lump_wavelength": 0.8, "seed": 1})
    s["temples"]["tips"] = {"from": 0.6, "scale": 0.7, "power": 1.2, "flatten": 0.4}
    for st in sts:
        if st["type"] != "locks":
            continue
        st["width"] = [round(x * 1.22, 5) for x in st["width"]]
        st["thick"] = [round(x * 1.3, 5) for x in st["thick"]]
        st["end_scale"] = 0.78
        st["tips"] = {"from": 0.72, "scale": 0.6, "power": 1.3, "flatten": 0.3, "calm": 0.3}
        st["felt"].update(irregularity=0.1, flatten=0.25)
        st["hang_radii"] = [round(x * 1.06, 5) for x in st["hang_radii"]]
        st["wave"]["amplitude"] = round(st["wave"]["amplitude"] * 1.15, 5)
        st["clump"] = {"bend_m": 0.006, "twist_deg": 20, "lumps": 0.06, "lump_wavelength": 0.5,
                       "seed": len(st["name"])}
    for k in ("side_locks", "outer_locks"):
        s[k]["count"] = 3
    s["back_locks"]["count"] = 9


EDIT = {"boy": boy, "girl": girl, "third": third}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--base-dir", required=True, help="directory with the T-155 candidate specs")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for key, fn in EDIT.items():
        if a.only and key != a.only:
            continue
        cid = IDS[key]
        r6 = json.load(open(os.path.join(R6, f"{cid}.hair_r6.override.json")))["override"]
        sts = copy.deepcopy(r6["hair"]["structures"])
        extra = {"base": json.load(open(os.path.join(a.base_dir, f"{cid}.{BASE[key]}.spec.json")))}
        fn(sts, extra)
        ov = {"generators": {"groom": "groom/5"}, "hair": dict({"generator": "groom/5", "structures": sts},
                                                               **extra.get("hair", {}))}
        if extra.get("materials"):
            ov["materials"] = extra["materials"]
        p = os.path.join(OUT, f"{cid}.hair_r7.override.json")
        json.dump({"override": ov, "note": f"T-167 hair round 7, opt-in; on {cid}.{BASE[key]}.spec.json (T-155 "
                                           f"candidate), from the T-160 round 6 override"}, open(p, "w"), indent=1)
        print(os.path.relpath(p))


if __name__ == "__main__":
    main()
