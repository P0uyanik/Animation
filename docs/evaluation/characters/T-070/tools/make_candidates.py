"""T-044: writes the hair v3 candidate specs (spec overrides a pin bump would apply) for the three characters into
docs/evaluation/characters/T-070/candidates/. Character data lives in candidates/characters.json (ids, specs,
colours); this script only lays out each hairstyle as groom/2 spec data, read from the references.

    python3 docs/evaluation/characters/T-070/tools/make_candidates.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(HERE, "..", "candidates")
CH = json.load(open(os.path.join(CAND, "characters.json")))


def fibre_layers(felt, halo, fly, shafts=None):
    """Three shared-GN fibre layers over the felt surface: dense short felt, a soft halo, sparse long flyaways.
    shafts (T-070): constant shaft radii in mm per layer (smooth roving: fine fibres that do not thicken with length)."""
    def lay(name, d, l, c, lean, lv):
        return {"name": name, "overrides": {"fibres": {"density_per_cm2": d, "length_mm": l, "curl": c, "lean": lean,
                                                        "lean_variation": lv},
                                            "surface": {"saturation_compensation": 1.0}}}
    layers = [lay("felt", *felt), lay("halo", *halo), lay("flyaways", *fly)]
    for layer, r in zip(layers, shafts or ()):
        layer["shaft_radius_mm"] = r
    return {"slots": ["hair"], "layers": layers}


def hair_material(rgb, ref_size, note):
    return {"preset": "felt hair", "base_color_srgb": rgb, "reference_size_m": ref_size, "source": note,
            "overrides": {"surface": {"saturation_compensation": 1.4, "sheen_weight": 0.15, "sheen_roughness": 0.6},
                          "nap": {"fibre_gloss": 0.1, "value_gain": 0.25, "sheen_gain": 0.3},
                          "fibres": {"color_variation": 0.35, "root_transparency": 0.2, "tip_transparency": 0.6}}}


# ------------------------------------------------------------------------------------------------------------- boy
def boy():
    c = CH["boy"]
    pole = {"az": 180, "el": 66}
    G = {"seg": 16, "grooves": 3, "groove_depth": 0.16, "irregularity": 0.09}

    def row(count, az, el, flow, len_deg, lift, width, thick, jit=12, curl=12, **kw):
        r = {"count": count, "az": az, "el": el, "flow": flow, "pole": pole, "len_deg": len_deg, "lift": lift,
             "width": width, "thick": thick, "jitter_deg": jit, "curl_deg": curl}
        r.update(kw)
        return r
    keep = {"az": 34, "el_min": -6}
    # T-070: puffy, rounded fleece clumps (thick ~0.6 x width, blunt tips via taper_power, shallow grooves) that arch
    # back towards the scalp ([root, peak, tip] lift), lower lifts (volume was 20-30 % too large, flared at the
    # temples), 4 fat crown tufts that curl back + thin flyaway loops, a broad central fringe clump to between the brows.
    G = {"seg": 18, "grooves": 2, "groove_depth": 0.05, "irregularity": 0.13}
    P = dict(taper_power=1.6, lift_peak=0.6, flick_m=0.01)
    st = [
        {"type": "scalp_cap", "name": "cap", "offset": 0.004},
        {"type": "felt_volume", "name": "base", "shape": "gather", "az": [-180, 180],
         "hairline_el": [[0, 22], [35, 16], [65, 2], [95, -14], [130, -28], [180, -34]], "target": pole, "tuck": 1.0,
         "height": [0.022, 0.04, 0.04], "inset": 0.004,
         "grooves": {"count": 30, "depth": 0.2, "sharpness": 0.6, "wander": 0.4, "wavelength": 0.5},
         "lumps": {"amount": 0.14, "scale": 1.2}, "soft": [0, 0, 0.25, 0.0], "rim": 0.2, "resolution": [160, 40]},
        dict(G, type="clumps", name="crown", rows=[
            row(4, [-180, 180], [64, 74], "away", [14, 18], [0.035, 0.115], [0.11, 0.12], [0.06, 0.066],
                jit=10, curl=6, lift_power=0.5, taper_power=1.5, az_list=[-28, 32, 150, 210]),
            row(3, [-180, 180], [62, 76], "away", [30, 40], [0.03, 0.07, 0.06], [0.012, 0.016], [0.009, 0.012],
                jit=25, curl=70, lift_power=1.0, taper_power=1.6, lift_peak=0.45, az_list=[-60, 10, 110])]),
        dict(G, type="clumps", name="top", rows=[
            row(12, [-180, 180], [42, 60], "away", [36, 50], [0.03, 0.07, 0.07], [0.08, 0.094], [0.04, 0.048],
                curl=14, lift_power=0.8, taper_power=1.6, lift_peak=0.6, flick_m=0.012)]),
        dict(G, type="clumps", name="fringe", rows=[
            row(4, [-46, 46], [28, 40], "down", [40, 50], [0.016, 0.026, 0.022], [0.074, 0.086], [0.036, 0.042],
                jit=8, curl=12, converge=0.1, taper_power=1.6, lift_peak=0.6)],
         keepout={"az": 34, "el_min": 1, "margin_deg": 2}),
        dict(G, type="clumps", name="fringe_centre", rows=[
            row(1, [-4, 4], [34, 38], "down", [56, 60], [0.018, 0.034, 0.024], [0.1, 0.1], [0.05, 0.05],
                jit=3, curl=6, taper_power=1.7, lift_peak=0.5, az_list=[3])],
         keepout={"az": 34, "el_min": -1, "margin_deg": 1}),
        dict(G, type="clumps", name="sides", rows=[
            row(2, [44, 64], [8, 22], "down", [32, 38], [0.008, 0.02, 0.02], [0.062, 0.07], [0.03, 0.036],
                jit=8, curl=10, **P),
            row(2, [-64, -44], [8, 22], "down", [32, 38], [0.008, 0.02, 0.02], [0.062, 0.07], [0.03, 0.036],
                jit=8, curl=10, **P),
            row(3, [66, 118], [6, 24], "down", [22, 32], [0.012, 0.03, 0.03], [0.074, 0.086], [0.034, 0.04],
                jit=14, curl=16, **P),
            row(3, [-118, -66], [6, 24], "down", [22, 32], [0.012, 0.03, 0.03], [0.074, 0.086], [0.034, 0.04],
                jit=14, curl=16, **P)]),
        dict(G, type="clumps", name="back", rows=[
            row(9, [118, 242], [14, 34], "down", [30, 42], [0.026, 0.05, 0.05], [0.08, 0.092], [0.04, 0.048],
                jit=14, curl=16, **P),
            row(8, [124, 236], [-16, 4], "down", [18, 26], [0.02, 0.038, 0.036], [0.07, 0.082], [0.036, 0.042],
                jit=14, curl=16, **P)]),
    ]
    dyn = {"enabled": True, "substep_hz": 240, "preroll_s": 1.0,
           "defaults": {"stiffness": 140.0, "stiffness_tip": 100.0, "damping": 9.0, "gravity": 0.2, "drag": 0.8,
                        "limit_deg": 18.0, "radius": 0.012},
           "structures": {"fringe": {"bones": 2, "bone_length": 0.03}, "sides": {"bones": 2, "bone_length": 0.03},
                          "fringe_centre": {"bones": 2, "bone_length": 0.03},
                          "back": {"bones": 2, "bone_length": 0.03},
                          "crown": {"bones": 2, "bone_length": 0.03, "stiffness": 200.0}},
           "colliders": [{"name": "head", "type": "sphere", "bone": "head", "head_offset": [0.0, 0.0, 0.0],
                          "radius": 0.15}]}
    hair = {"generator": "groom/2", "seed": 44, "finish": "felt", "face_keepout": keep, "structures": st,
            "fibres": fibre_layers((34.0, 1.9, 0.5, 0.6, 0.8), (1.6, 4.2, 0.6, 0.8, 0.9), (0.05, 10.0, 0.95, 0.7, 0.9)),
            "dynamics": dyn}
    return c, hair, {"hair": hair_material(c["hair_srgb"], 0.32, c["hair_note"])}


# ------------------------------------------------------------------------------------------------------------ girl
def girl():
    """High two-lobed bun with band and flowers, smooth felted crown with a side part, side-swept soft fringe, chunky
    separate ringlets over a thin sculpted back base (T-049 C layout, reworked against the references)."""
    c = CH["girl"]
    keep = {"az": 34, "el_min": 5}
    felt_lock = {"seg": 16, "irregularity": 0.12, "wavelength": 0.15, "flatten": 0.12, "flatten_twist": 1.2}

    def ringlets(name, count, az, el_root, el_leave, z_end, width, thick, radius, pitch, mirror=False, start=0.08, **kw):
        r = {"type": "locks", "name": name, "style": "curly", "count": count, "az": az, "el_root": el_root,
             "el_leave": el_leave, "lift": [0.008, 0.024], "hang_radii": [0.2, 0.18], "z_end": z_end, "flare": 0.05,
             "width": width, "thick": thick, "tip_frac": 0.7,
             "curl": {"radius": radius, "pitch": pitch, "radius_growth": 0.25, "start": start, "direction": "alternate",
                      "jitter": 0.12, "start_jitter": 0.03, "wobble": 0.1, "wobble_wavelength": 0.16, "sway": 0.004,
                      "ellipse": 1.0, "tip": {"from": 0.8, "radius": 1.15, "pitch": 0.8, "ellipse": 1.0}},
             "felt": felt_lock, "finish": "felt"}
        if mirror:
            r["mirror"] = True
        r.update(kw)
        return r
    grooves = lambda n, d=0.3: {"count": n, "depth": d, "sharpness": 0.6, "wander": 0.35, "wavelength": 0.5}
    st = [
        {"type": "scalp_cap", "name": "cap", "offset": 0.004, "face_cut": [-0.06, 0.9],
         "hairline": [[0, 0.905], [40, 0.88], [70, 0.8], [100, 0.74], [140, 0.71], [180, 0.7]]},
        {"type": "bun", "name": "bun", "buns": [{"az": 180, "el": 82, "lift": 0.0, "radius": 0.118, "height": 0.17,
         "tilt": 0.4, "wrap": "ccw", "turns": 0.9, "ropes": 5, "rope_thick": 0.046, "felt_radii": [0.62, 0.62, 0.9],
         "felt_lobes": [{"offset": [0.0, 0.5, 0.1], "radii": [0.62, 0.56, 0.9], "swirl": 1.1},
                        {"offset": [0.0, -0.5, 0.06], "radii": [0.62, 0.56, 0.88], "swirl": -1.0},
                        {"offset": [0.45, 0.05, 0.2], "radii": [0.56, 0.6, 0.86], "swirl": 0.9},
                        {"offset": [-0.35, 0.0, 0.55], "radii": [0.56, 0.58, 0.8], "swirl": -0.8}]}],
         "felt": {"grooves": {"count": 14, "depth": 0.45, "sharpness": 0.75, "wander": 0.45, "wavelength": 0.6},
                  "lumps": {"amount": 0.06, "scale": 1.1}, "resolution": [80, 44]}},
        {"type": "felt_volume", "name": "crown", "shape": "gather", "az": [-180, 180],
         "hairline_el": [[0, 40], [25, 36], [50, 20], [72, 2], [95, 0], [125, 10], [150, 14], [180, 14]],
         "target": {"bun": 0}, "tuck": 0.97, "height": [0.022, 0.05, 0.03], "inset": 0.004,
         "part": {"az": -18, "width_deg": 3.5, "depth": 0.5, "length": 0.55}, "grooves": grooves(30, 0.14),
         "lumps": {"amount": 0.05, "scale": 1.0}, "soft": [0, 0, 0.3, 0.0], "rim": 0.12, "resolution": [220, 48]},
        {"type": "felt_volume", "name": "fringe", "shape": "fringe", "root_az": [-14, -14, -15, -16, -17, -18, -19],
         "root_el": [46, 53, 60, 67, 74, 81, 88], "tip_az": [-4, 10, 24, 38, 52, 66, 82],
         "tip_el": [21, 15, 11, 9, 6, -3, -12], "tip_lift": [0.006, 0.008, 0.012, 0.016, 0.02, 0.024, 0.026],
         "bulge": 0.05, "thick": [0.034, 0.026], "tip_scallop": 0.16, "tip_jitter": 0.1, "resolution": [72, 40],
         "grooves": grooves(9, 0.32), "lumps": {"amount": 0.05}, "soft": [0.08, 0.08, 0.05, 0.14], "rim": 0.12,
         "clearance": 0.003},
        {"type": "felt_volume", "name": "fringe_part", "shape": "fringe", "root_az": [-22, -22, -23, -24, -25],
         "root_el": [48, 56, 64, 72, 80], "tip_az": [-34, -46, -58, -72, -86], "tip_el": [14, 9, 4, -2, -8],
         "tip_lift": [0.006, 0.01, 0.014, 0.018, 0.022], "bulge": 0.034, "thick": [0.03, 0.02], "tip_scallop": 0.16,
         "tip_jitter": 0.1, "resolution": [56, 40], "grooves": grooves(7, 0.32), "lumps": {"amount": 0.05},
         "soft": [0.08, 0.08, 0.05, 0.14], "rim": 0.12, "clearance": 0.003},
        {"type": "felt_volume", "name": "temple_l", "shape": "mass", "az": 84, "el": 0, "lift": -0.004,
         "radii": [0.05, 0.048, 0.08], "axis": "up", "swirl": 0.08, "grooves": grooves(10, 0.45),
         "lumps": {"amount": 0.05}, "resolution": [56, 32]},
        {"type": "felt_volume", "name": "temple_r", "shape": "mass", "az": -84, "el": 0, "lift": -0.004,
         "radii": [0.05, 0.048, 0.08], "axis": "up", "swirl": 0.08, "grooves": grooves(10, 0.45),
         "lumps": {"amount": 0.05}, "resolution": [56, 32]},
        {"type": "curtain", "name": "curtain", "az": [92, 268], "root_el": [[92, 14], [125, 24], [180, 30]],
         "leave_el": -14, "z_end": [[92, 0.6], [130, 0.56], [180, 0.54]], "rest_radii": [0.17, 0.145], "rest_z": 0.62,
         "columns": 13, "thick": 0.022, "column_depth": 0.15, "lobe": {"pitch": 0.05, "depth": 0.0, "twist": 0.7},
         "scallop": 0.04, "resolution": [180, 100], "inset": 0.004},
        ringlets("ringlets_side", 3, [66, 96], [6, 18], -14, [0.5, 0.58], [0.032, 0.036], [0.03, 0.033], 0.019,
                 0.078, mirror=True, start=0.06),
        ringlets("ringlets_back", 10, [124, 236], [-14, -4], -30, [0.42, 0.47], [0.032, 0.036], [0.03, 0.034],
                 0.02, 0.08, hang_jitter=0.06, rest_radii=[0.2, 0.17], rest_z=0.62, start=0.06),
        ringlets("ringlets_outer", 3, [100, 122], [-2, 10], -22, [0.44, 0.5], [0.032, 0.036], [0.03, 0.033], 0.02,
                 0.08, mirror=True, rest_radii=[0.21, 0.175], rest_z=0.62, start=0.06),
        {"type": "tie", "name": "band", "bun": 0, "height_frac": 0.16, "radius_scale": 1.04, "tube": 0.011,
         "width_scale": 1.7, "material": "hair_band"},
        {"type": "flowers", "name": "flowers", "bun": 0, "petals": 5, "material": "hair_flower",
         "centre_material": "hair_flower_centre",
         "items": [{"around_deg": 50, "height_frac": 0.22, "size": 0.04, "out": 0.026},
                   {"around_deg": 85, "height_frac": 0.34, "size": 0.034, "out": 0.026},
                   {"around_deg": 22, "height_frac": 0.4, "size": 0.03, "out": 0.026}]},
    ]
    dyn = {"enabled": True, "substep_hz": 240, "preroll_s": 1.0,
           "defaults": {"stiffness": 90.0, "stiffness_tip": 60.0, "damping": 7.0, "gravity": 0.5, "drag": 0.8,
                        "limit_deg": 30.0, "radius": 0.014},
           "structures": {"ringlets_side": {"bones": [3, 4], "bone_length": 0.06},
                          "ringlets_back": {"bones": [3, 5], "bone_length": 0.07},
                          "ringlets_outer": {"bones": [3, 5], "bone_length": 0.07},
                          "bun": {"bones": 3, "stiffness": 140.0, "stiffness_tip": 120.0, "damping": 9.0,
                                  "gravity": 0.3, "limit_deg": 12.0, "radius": 0.0}},
           "colliders": [{"name": "head", "type": "sphere", "bone": "head", "head_offset": [0.0, 0.0, -0.004],
                          "radius": 0.128},
                         {"name": "torso", "type": "capsule", "bone": "chest", "a": [0.0, 0.004, 0.4],
                          "b": [0.0, 0.004, 0.56], "radius": 0.082},
                         {"name": "shoulder_l", "type": "sphere", "bone": "chest", "head_offset": [0.1, 0.0, -0.24],
                          "radius": 0.045},
                         {"name": "shoulder_r", "type": "sphere", "bone": "chest", "head_offset": [-0.1, 0.0, -0.24],
                          "radius": 0.045}]}
    hair = {"generator": "groom/2", "seed": 30, "finish": "felt", "face_keepout": keep, "structures": st,
            "binding": {"blend_z": [0.6, 0.72]},
            "fibres": fibre_layers((28.0, 2.2, 0.45, 0.6, 0.8), (1.8, 4.8, 0.6, 0.8, 0.9), (0.05, 9.0, 0.95, 0.7, 0.9)),
            "dynamics": dyn}
    m = hair_material(c["hair_srgb"], 0.29278, c["hair_note"])
    m["overrides"]["surface"]["saturation_compensation"] = 1.0
    return c, hair, {"hair": m}


# ----------------------------------------------------------------------------------------------- third character
def third():
    """Off-white felt: two round top buns, fringe clumps to the brows, wavy side locks framing the face, a long wavy
    back mass, the blue felt bow at the base of her right bun (owner decision 2026-11-17: the bow, not the flower).
    Built from her hair blueprints (07 geometry/groom, 08 rig/secondary motion) and the identity sheets."""
    c = CH["third"]
    keep = {"az": 34, "el_min": 4, "margin_deg": 1}
    pole = {"az": 0, "el": 90}
    felt_lock = {"seg": 16, "irregularity": 0.07, "wavelength": 0.16, "flatten": 0.35, "flatten_twist": 0.8}
    grooves = lambda n, d=0.3: {"count": n, "depth": d, "sharpness": 0.55, "wander": 0.45, "wavelength": 0.5}

    def wavy(name, count, az, el_root, el_leave, z_end, width, thick, radius, pitch, mirror=False, **kw):
        """T-070: big soft S-waves (a flattened helix, ellipse < 1) ending in a soft curl, wide flat felt locks."""
        r = {"type": "locks", "name": name, "style": "curly", "count": count, "az": az, "el_root": el_root,
             "el_leave": el_leave, "lift": [0.006, 0.016], "hang_radii": [0.165, 0.16], "z_end": z_end, "flare": 0.16,
             "width": width, "thick": thick, "tip_frac": 0.5, "end_scale": 0.75,
             "curl": {"radius": radius, "pitch": pitch, "radius_growth": 0.1, "start": -0.07, "start_jitter": 0.04,
                      "direction": "alternate", "jitter": 0.15, "wobble": 0.08, "wobble_wavelength": 0.2,
                      "sway": 0.004, "ellipse": 0.14, "tip": {"from": 0.85, "radius": 0.85, "pitch": 0.8,
                                                              "ellipse": 0.35}},
             "felt": felt_lock, "finish": "felt"}
        if mirror:
            r["mirror"] = True
        r.update(kw)
        return r
    st = [
        {"type": "scalp_cap", "name": "cap", "offset": 0.004, "face_cut": [-0.06, 0.9],
         "hairline": [[0, 0.905], [40, 0.88], [70, 0.8], [100, 0.74], [140, 0.71], [180, 0.7]]},
        {"type": "bun", "name": "buns", "buns": [
            {"az": 54, "el": 54, "lift": 0.006, "radius": 0.072, "height": 0.124, "tilt": 0.55, "wrap": "ccw",
             "turns": 0.6, "felt_radii": [1.0, 1.0, 1.0]},
            {"az": -54, "el": 54, "lift": 0.006, "radius": 0.072, "height": 0.124, "tilt": 0.55, "wrap": "cw",
             "turns": 0.6, "felt_radii": [1.0, 1.0, 1.0]}],
         "felt": {"grooves": {"count": 14, "depth": 0.12, "sharpness": 0.4, "wander": 0.7, "wavelength": 0.5},
                  "lumps": {"amount": 0.05, "scale": 1.3}, "resolution": [64, 40]}},
        {"type": "felt_volume", "name": "crown", "shape": "gather", "az": [-180, 180],
         "hairline_el": [[0, 30], [30, 28], [55, 14], [80, 0], [100, -4], [130, 4], [180, 6]],
         "target": pole, "tuck": 1.0, "height": [0.026, 0.05, 0.05], "inset": 0.004,
         "part": {"az": 0, "width_deg": 3.0, "depth": 0.35, "length": 0.45}, "grooves": grooves(40, 0.14),
         "lumps": {"amount": 0.05, "scale": 1.2}, "soft": [0, 0, 0.3, 0.0], "rim": 0.15, "resolution": [220, 48]},
        {"type": "clumps", "name": "fringe", "seg": 16, "grooves": 2, "groove_depth": 0.08, "irregularity": 0.08,
         "rows": [{"count": 14, "az": [-48, 48], "el": [34, 46], "flow": "down", "pole": pole, "len_deg": [36, 42],
                   "lift": [0.01, 0.016], "width": [0.046, 0.054], "thick": [0.016, 0.02], "jitter_deg": 6,
                   "curl_deg": 8, "converge": 0.04, "taper_power": 1.4}]},
        {"type": "clumps", "name": "temples", "seg": 16, "grooves": 2, "groove_depth": 0.08, "irregularity": 0.08,
         "rows": [{"count": 2, "az": [56, 72], "el": [12, 24], "flow": "down", "pole": pole, "len_deg": [26, 34],
                   "lift": [0.01, 0.02], "width": [0.04, 0.05], "thick": [0.018, 0.022], "jitter_deg": 6,
                   "curl_deg": 10, "taper_power": 1.5},
                  {"count": 2, "az": [-72, -56], "el": [12, 24], "flow": "down", "pole": pole, "len_deg": [26, 34],
                   "lift": [0.01, 0.02], "width": [0.04, 0.05], "thick": [0.018, 0.022], "jitter_deg": 6,
                   "curl_deg": 10, "taper_power": 1.5}]},
        {"type": "curtain", "name": "back_mass", "az": [76, 284], "root_el": [[76, 4], [120, 18], [180, 26]],
         "leave_el": -8, "z_end": [[76, 0.6], [120, 0.52], [180, 0.48]], "rest_radii": [0.215, 0.17], "rest_z": 0.6,
         "columns": 10, "thick": 0.016, "column_depth": 0.25, "lobe": {"pitch": 0.12, "depth": 0.0, "twist": 0.2},
         "scallop": 0.035, "resolution": [180, 100], "inset": 0.004},
        wavy("side_locks", 2, [62, 82], [4, 14], -16, [0.56, 0.62], [0.054, 0.06], [0.032, 0.036], 0.032, 0.16,
             mirror=True, hang_radii=[0.165, 0.155]),
        wavy("back_locks", 9, [108, 252], [0, 16], -14, [0.45, 0.5], [0.07, 0.078], [0.036, 0.042], 0.042, 0.18,
             hang_jitter=0.05, rest_radii=[0.2, 0.165], rest_z=0.6),
        wavy("outer_locks", 2, [84, 108], [2, 14], -14, [0.5, 0.56], [0.062, 0.068], [0.034, 0.04], 0.04, 0.18,
             mirror=True, rest_radii=[0.215, 0.17], rest_z=0.6),
        {"type": "felt_bow", "name": "bow", "az": -42, "el": 42, "out": 0.03, "size": 0.17, "tilt_deg": 20,
         "material": "hair_bow"},
    ]
    dyn = {"enabled": True, "substep_hz": 240, "preroll_s": 1.0,
           "defaults": {"stiffness": 90.0, "stiffness_tip": 60.0, "damping": 7.0, "gravity": 0.5, "drag": 0.8,
                        "limit_deg": 28.0, "radius": 0.014},
           "structures": {"fringe": {"bones": 2, "bone_length": 0.03, "stiffness": 140.0},
                          "temples": {"bones": [2, 3], "bone_length": 0.035},
                          "side_locks": {"bones": [3, 4], "bone_length": 0.06},
                          "back_locks": {"bones": [3, 5], "bone_length": 0.07},
                          "outer_locks": {"bones": [3, 5], "bone_length": 0.07},
                          "buns": {"bones": 3, "stiffness": 150.0, "stiffness_tip": 120.0, "damping": 9.0,
                                   "gravity": 0.3, "limit_deg": 12.0, "radius": 0.0}},
           "colliders": [{"name": "head", "type": "sphere", "bone": "head", "head_offset": [0.0, 0.0, -0.004],
                          "radius": 0.128},
                         {"name": "torso", "type": "capsule", "bone": "chest", "a": [0.0, 0.004, 0.4],
                          "b": [0.0, 0.004, 0.56], "radius": 0.082},
                         {"name": "shoulder_l", "type": "sphere", "bone": "chest", "head_offset": [0.1, 0.0, -0.24],
                          "radius": 0.045},
                         {"name": "shoulder_r", "type": "sphere", "bone": "chest", "head_offset": [-0.1, 0.0, -0.24],
                          "radius": 0.045}]}
    hair = {"generator": "groom/2", "seed": 52, "finish": "felt", "face_keepout": keep, "structures": st,
            "binding": {"blend_z": [0.6, 0.72]},
            "fibres": dict(fibre_layers((40.0, 2.6, 0.06, 0.9, 0.5), (4.0, 6.0, 0.08, 0.9, 0.6), (0.08, 10.0, 0.4, 0.7, 0.9),
                                        shafts=(0.14, 0.1, 0.07)),
                           slots=["hair", "hair_bow"]),
            "dynamics": dyn}
    m = hair_material(c["hair_srgb"], 0.29278, c["hair_note"])
    m["overrides"]["surface"]["saturation_compensation"] = 1.0
    # T-070: smooth roving instead of a speckled boucle: almost no nap/value blotches or per-fibre tone variation
    m["overrides"]["nap"]["value_gain"] = 0.05
    m["overrides"]["fibres"]["color_variation"] = 0.08
    m["overrides"]["micro_relief"] = {"color_strength": 0.2}
    m["overrides"]["fibre"] = {"strength": 0.25}
    bow = {"preset": "felt", "base_color_srgb": c["bow_srgb"], "reference_size_m": 0.06,
           "source": "references/color_targets.json bow: dusty denim-blue felt"}
    return c, hair, {"hair": m, "hair_bow": bow}


def write(key, fn):
    c, hair, asg = fn()
    out = {"schema": "plush-studio.hair-candidate/1", "task": "T-044", "character_spec": c["spec"],
           "head_object": c["head_object"], "frame": c["frame"],
           "overrides": {"generators": {"groom": "groom/2"}, "hair": hair, "materials": {"assignments": asg}}}
    p = os.path.join(CAND, f"{key}.hair_v3.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", p)


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["boy", "girl", "third"]
    for k in which:
        write(k, globals()[k])
