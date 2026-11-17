"""Writes boy_A/B/C.json (T-049 study; experiment data only). One flow layout (whorl at the back of the crown, fringe
chunks to the brows, temple clumps to eye level, flared back); the approaches differ only in how it is built.
    python3 pipeline/charsys/experiments/hair_study/specs/make_boy_specs.py"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(HERE, "characters.json")))["boy"]["spec"]
POLE = {"az": 180, "el": 66}
KEEP = {"az": 35, "el_min": -11}  # face keep-out: no clump tip over the eyes (|az| < 35 deg) below the brows


def clumps(name, rows, keepout=None):
    st = {"type": "study_clumps", "name": name, "seg": 14, "grooves": 3, "groove_depth": 0.14, "irregularity": 0.08,
          "rows": rows}
    if keepout:
        st["keepout"] = keepout
    return st


def row(count, az, el, flow, len_deg, lift, width, thick, jitter=14, curl=15, **kw):
    r = {"count": count, "az": az, "el": el, "flow": flow, "pole": POLE, "len_deg": len_deg, "lift": lift,
         "width": width, "thick": thick, "jitter_deg": jitter, "curl_deg": curl}
    r.update(kw)
    return r


CLUMPS = [
    clumps("crown", [row(3, [-30, 40], [70, 80], "stand", [10, 16], [0.0, 0.1], [0.064, 0.078], [0.04, 0.05], 30, 0,
                         lift_power=0.85, taper_power=1.1),
                     row(3, [140, 220], [60, 72], "stand", [10, 16], [0.0, 0.09], [0.064, 0.078], [0.04, 0.05], 30, 0,
                         lift_power=0.85, taper_power=1.1)]),
    clumps("top", [row(14, [-180, 180], [42, 58], "away", [36, 50], [0.008, 0.05], [0.052, 0.066], [0.026, 0.034],
                       12, 14)]),
    clumps("fringe", [row(6, [-45, 45], [30, 40], "down", [48, 58], [0.01, 0.022], [0.05, 0.06], [0.026, 0.032], 10,
                          10, converge=0.12)], KEEP),
    clumps("sides", [row(5, [40, 112], [4, 24], "down", [34, 46], [0.008, 0.045], [0.045, 0.056], [0.024, 0.03]),
                     row(5, [-112, -40], [4, 24], "down", [34, 46], [0.008, 0.045], [0.045, 0.056], [0.024, 0.03])],
           KEEP),
    clumps("back", [row(10, [120, 240], [12, 32], "down", [30, 40], [0.008, 0.045], [0.048, 0.06], [0.024, 0.032], 16,
                        18),
                    row(9, [125, 235], [-16, 2], "down", [18, 26], [0.004, 0.03], [0.042, 0.054], [0.022, 0.028], 16,
                        18)]),
]
CAP = {"type": "scalp_cap", "name": "cap", "offset": 0.004}
BASE = {"type": "felt_volume", "name": "base", "shape": "gather", "az": [-180, 180],
        "hairline_el": [[0, 22], [35, 16], [65, 2], [95, -14], [130, -28], [180, -34]],
        "target": POLE, "tuck": 1.0, "height": [0.016, 0.04, 0.04], "inset": 0.004,
        "grooves": {"count": 30, "depth": 0.3, "sharpness": 0.6, "wander": 0.4, "wavelength": 0.5},
        "lumps": {"amount": 0.1, "scale": 1.2}, "soft": [0, 0, 0.25, 0.0], "rim": 0.2, "resolution": [160, 40]}
FIBRES = {"slots": ["hair"], "layers": [
    {"name": "felt", "overrides": {"fibres": {"density_per_cm2": 6.0, "length_mm": 2.6, "curl": 0.55, "lean": 0.5},
                                   "surface": {"saturation_compensation": 1.0}}},
    {"name": "flyaways", "overrides": {"fibres": {"density_per_cm2": 0.08, "length_mm": 8.0, "curl": 0.9, "lean": 0.7},
                                       "surface": {"saturation_compensation": 1.0}}}]}
DYN_DEFAULTS = {"stiffness": 140.0, "stiffness_tip": 100.0, "damping": 9.0, "gravity": 0.2, "drag": 0.8,
                "limit_deg": 18.0, "radius": 0.012}
COLLIDERS = [{"name": "head", "type": "sphere", "bone": "head", "head_offset": [0.0, 0.0, 0.0], "radius": 0.15}]


def study(approach, label, structures, dyn_structs, fuse=None):
    d = {"schema": "plush-studio.hair-study/1", "approach": approach, "label": label, "character_spec": SPEC,
         "head_object": "head", "frame": {"centre": [0.0, 0.008, 0.855], "radii": [0.16, 0.154, 0.159]},
         "materials": {"hair": {"preset": "felt hair", "base_color_srgb": [44, 38, 36], "reference_size_m": 0.32,
                                "source": "T-049 study: boy target_colors_srgb hair (48,39,35), slightly darker "
                                          "(#2D2D2D, blueprint 21)"}},
         "hair": {"generator": "groom/1", "seed": 49, "scalp_offset_m": 0.006, "finish": "felt", "fibres": FIBRES,
                  "structures": structures,
                  "dynamics": ({"enabled": True, "substep_hz": 240, "preroll_s": 1.0, "defaults": DYN_DEFAULTS,
                                "structures": dyn_structs, "colliders": COLLIDERS} if dyn_structs else
                               {"enabled": False})}}
    if fuse:
        d["fuse"] = fuse
    return d


chains = {n: {"bones": 2, "bone_length": 0.03} for n in ("fringe", "sides", "back")}
chains["crown"] = {"bones": 2, "bone_length": 0.03, "stiffness": 200.0}
C = study("C", "hybrid: felted base volume + 55 broad felt clumps (crown tufts, fringe chunks, temples, back)",
          [CAP, BASE] + CLUMPS, chains)
B = study("B", "sculpted: the same base volume and clump shapes fused by voxel remesh into one smoothed felt sculpt",
          [CAP, BASE] + CLUMPS, {}, {"voxel": 0.002, "smooth": 3, "exclude": ["cap"]})

# A: no base volume; every clump split into 2-3 narrower locks, plus an under-layer of thin locks for coverage
mult = {"crown": 2, "top": 3, "fringe": 2, "sides": 3, "back": 3}
a_clumps = copy.deepcopy(CLUMPS)
for st in a_clumps:
    st.update(seg=10, groove_depth=0.08)
    for r in st["rows"]:
        r["count"] = r["count"] * mult[st["name"]]
        r["width"] = [x * 0.5 for x in r["width"]]
        r["thick"] = [x * 0.6 for x in r["thick"]]
under = clumps("under", [row(40, [-180, 180], [20, 60], "away", [30, 44], [0.0, 0.014], [0.022, 0.03], [0.012, 0.016],
                             10, 0),
                         row(30, [50, 310], [-20, 20], "down", [24, 34], [0.0, 0.012], [0.022, 0.03], [0.012, 0.016],
                             10, 0)], KEEP)
under.update(seg=10, groove_depth=0.08)
a_chains = dict(chains, under={"bones": 1, "bone_length": 0.03, "stiffness": 240.0})
A = study("A", "strand/lock groom: scalp cap + ~220 narrow felt locks (each C clump split in 2-3, plus an under-layer)",
          [CAP, under] + a_clumps, a_chains)

for name, d in (("A", A), ("B", B), ("C", C)):
    json.dump(d, open(os.path.join(HERE, f"boy_{name}.json"), "w"), indent=1)
print("wrote boy_A/B/C.json")
