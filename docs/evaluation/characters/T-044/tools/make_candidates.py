"""T-044: writes the hair v3 candidate specs (spec overrides a pin bump would apply) for the three characters into
docs/evaluation/characters/T-044/candidates/. Character data lives in candidates/characters.json (ids, specs,
colours); this script only lays out each hairstyle as groom/2 spec data, read from the references.

    python3 docs/evaluation/characters/T-044/tools/make_candidates.py"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(HERE, "..", "candidates")
CH = json.load(open(os.path.join(CAND, "characters.json")))


def fibre_layers(felt, halo, fly):
    """Three shared-GN fibre layers over the felt surface: dense short felt, a soft halo, sparse long flyaways."""
    def lay(name, d, l, c, lean, lv):
        return {"name": name, "overrides": {"fibres": {"density_per_cm2": d, "length_mm": l, "curl": c, "lean": lean,
                                                        "lean_variation": lv},
                                            "surface": {"saturation_compensation": 1.0}}}
    return {"slots": ["hair"], "layers": [lay("felt", *felt), lay("halo", *halo), lay("flyaways", *fly)]}


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
    st = [
        {"type": "scalp_cap", "name": "cap", "offset": 0.004},
        {"type": "felt_volume", "name": "base", "shape": "gather", "az": [-180, 180],
         "hairline_el": [[0, 22], [35, 16], [65, 2], [95, -14], [130, -28], [180, -34]], "target": pole, "tuck": 1.0,
         "height": [0.026, 0.055, 0.055], "inset": 0.004,
         "grooves": {"count": 30, "depth": 0.3, "sharpness": 0.6, "wander": 0.4, "wavelength": 0.5},
         "lumps": {"amount": 0.12, "scale": 1.2}, "soft": [0, 0, 0.25, 0.0], "rim": 0.2, "resolution": [160, 40]},
        dict(G, type="clumps", name="crown", rows=[
            row(5, [-180, 180], [68, 80], "away", [24, 32], [0.02, 0.15], [0.095, 0.11], [0.05, 0.06], jit=18,
                curl=8, lift_power=0.9, taper_power=1.9, az_list=[-15, 25, 140, 185, 225])]),
        dict(G, type="clumps", name="top", rows=[
            row(11, [-180, 180], [40, 58], "away", [34, 52], [0.035, 0.1], [0.088, 0.104], [0.036, 0.046], curl=16,
                flick_m=0.012)]),
        dict(G, type="clumps", name="fringe", rows=[
            row(5, [-44, 44], [28, 40], "down", [44, 56], [0.02, 0.03], [0.074, 0.088], [0.032, 0.038], jit=10,
                curl=12, converge=0.1)]),
        dict(G, type="clumps", name="sides", rows=[
            row(2, [40, 62], [8, 22], "down", [40, 50], [0.014, 0.045], [0.066, 0.078], [0.03, 0.036], jit=10, curl=12,
                flick_m=0.01),
            row(2, [-62, -40], [8, 22], "down", [40, 50], [0.014, 0.045], [0.066, 0.078], [0.03, 0.036], jit=10,
                curl=12, flick_m=0.01),
            row(3, [66, 118], [6, 24], "down", [20, 32], [0.03, 0.072], [0.078, 0.092], [0.03, 0.038], jit=14,
                curl=16, flick_m=0.016),
            row(3, [-118, -66], [6, 24], "down", [20, 32], [0.03, 0.072], [0.078, 0.092], [0.03, 0.038], jit=14,
                curl=16, flick_m=0.016)]),
        dict(G, type="clumps", name="back", rows=[
            row(8, [118, 242], [12, 34], "down", [28, 42], [0.04, 0.095], [0.088, 0.1], [0.032, 0.042], jit=14,
                curl=16, flick_m=0.01),
            row(7, [124, 236], [-18, 2], "down", [16, 28], [0.03, 0.07], [0.076, 0.09], [0.028, 0.036], jit=14,
                curl=16, flick_m=0.008)]),
    ]
    dyn = {"enabled": True, "substep_hz": 240, "preroll_s": 1.0,
           "defaults": {"stiffness": 140.0, "stiffness_tip": 100.0, "damping": 9.0, "gravity": 0.2, "drag": 0.8,
                        "limit_deg": 18.0, "radius": 0.012},
           "structures": {"fringe": {"bones": 2, "bone_length": 0.03}, "sides": {"bones": 2, "bone_length": 0.03},
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
    keep = {"az": 34, "el_min": 6}
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
        {"type": "bun", "name": "bun", "buns": [{"az": 180, "el": 76, "lift": 0.0, "radius": 0.1, "height": 0.16,
         "tilt": 0.65, "wrap": "ccw", "turns": 0.9, "ropes": 5, "rope_thick": 0.046, "felt_radii": [0.72, 0.6, 0.85],
         "felt_lobes": [{"offset": [0.0, 0.62, 0.2], "radii": [0.72, 0.6, 0.9], "swirl": 1.1},
                        {"offset": [0.0, -0.62, 0.14], "radii": [0.72, 0.6, 0.88], "swirl": -1.0}]}],
         "felt": {"grooves": {"count": 14, "depth": 0.45, "sharpness": 0.75, "wander": 0.45, "wavelength": 0.6},
                  "lumps": {"amount": 0.06, "scale": 1.1}, "resolution": [80, 44]}},
        {"type": "felt_volume", "name": "crown", "shape": "gather", "az": [-180, 180],
         "hairline_el": [[0, 40], [25, 36], [50, 20], [72, 2], [95, 0], [125, 10], [150, 14], [180, 14]],
         "target": {"bun": 0}, "tuck": 0.97, "height": [0.022, 0.05, 0.03], "inset": 0.004,
         "part": {"az": -18, "width_deg": 3.5, "depth": 0.5, "length": 0.55}, "grooves": grooves(44, 0.26),
         "lumps": {"amount": 0.05, "scale": 1.0}, "soft": [0, 0, 0.3, 0.0], "rim": 0.12, "resolution": [220, 48]},
        {"type": "felt_volume", "name": "fringe", "shape": "fringe", "root_az": [-14, -14, -15, -16, -17, -18, -19],
         "root_el": [46, 53, 60, 67, 74, 81, 88], "tip_az": [4, 20, 36, 52, 64, 74, 84],
         "tip_el": [24, 17, 12, 8, 4, 0, -4], "tip_lift": [0.006, 0.01, 0.014, 0.018, 0.022, 0.024, 0.024],
         "bulge": 0.04, "thick": [0.032, 0.022], "tip_scallop": 0.16, "tip_jitter": 0.1, "resolution": [72, 40],
         "grooves": grooves(9, 0.32), "lumps": {"amount": 0.05}, "soft": [0.08, 0.08, 0.05, 0.14], "rim": 0.12,
         "clearance": 0.003},
        {"type": "felt_volume", "name": "fringe_part", "shape": "fringe", "root_az": [-22, -22, -23, -24, -25],
         "root_el": [48, 56, 64, 72, 80], "tip_az": [-30, -44, -58, -72, -84], "tip_el": [26, 18, 11, 4, -2],
         "tip_lift": [0.006, 0.01, 0.014, 0.018, 0.022], "bulge": 0.034, "thick": [0.03, 0.02], "tip_scallop": 0.16,
         "tip_jitter": 0.1, "resolution": [56, 40], "grooves": grooves(7, 0.32), "lumps": {"amount": 0.05},
         "soft": [0.08, 0.08, 0.05, 0.14], "rim": 0.12, "clearance": 0.003},
        {"type": "felt_volume", "name": "temple_l", "shape": "mass", "az": 84, "el": 0, "lift": -0.004,
         "radii": [0.05, 0.048, 0.08], "axis": "up", "swirl": 0.08, "grooves": grooves(10, 0.45),
         "lumps": {"amount": 0.05}, "resolution": [56, 32]},
        {"type": "felt_volume", "name": "temple_r", "shape": "mass", "az": -84, "el": 0, "lift": -0.004,
         "radii": [0.05, 0.048, 0.08], "axis": "up", "swirl": 0.08, "grooves": grooves(10, 0.45),
         "lumps": {"amount": 0.05}, "resolution": [56, 32]},
        {"type": "curtain", "name": "curtain", "az": [96, 264], "root_el": [[96, 14], [125, 24], [180, 30]],
         "leave_el": -6, "z_end": [[96, 0.6], [130, 0.52], [180, 0.48]], "rest_radii": [0.165, 0.14], "rest_z": 0.62,
         "columns": 11, "thick": 0.016, "column_depth": 0.5, "lobe": {"pitch": 0.05, "depth": 0.0, "twist": 0.7},
         "scallop": 0.04, "resolution": [180, 100], "inset": 0.004},
        ringlets("ringlets_side", 2, [72, 92], [10, 20], -12, [0.56, 0.62], [0.026, 0.03], [0.024, 0.028], 0.018,
                 0.07, mirror=True, start=0.04),
        ringlets("ringlets_back", 8, [128, 232], [-12, -4], -28, [0.42, 0.48], [0.026, 0.03], [0.024, 0.028], 0.019,
                 0.072, hang_jitter=0.04, rest_radii=[0.19, 0.165], rest_z=0.62),
        ringlets("ringlets_outer", 3, [106, 126], [0, 10], -20, [0.45, 0.52], [0.026, 0.03], [0.024, 0.028], 0.019,
                 0.072, mirror=True, rest_radii=[0.2, 0.17], rest_z=0.62),
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
    keep = {"az": 34, "el_min": 4, "margin_deg": 3}
    pole = {"az": 0, "el": 90}
    felt_lock = {"seg": 16, "irregularity": 0.07, "wavelength": 0.16, "flatten": 0.35, "flatten_twist": 0.8}
    grooves = lambda n, d=0.3: {"count": n, "depth": d, "sharpness": 0.55, "wander": 0.45, "wavelength": 0.5}

    def wavy(name, count, az, el_root, el_leave, z_end, width, thick, amp, wl, mirror=False, **kw):
        r = {"type": "locks", "name": name, "style": "wavy", "count": count, "az": az, "el_root": el_root,
             "el_leave": el_leave, "lift": [0.006, 0.016], "hang_radii": [0.165, 0.16], "z_end": z_end, "flare": 0.16,
             "width": width, "thick": thick, "tip_frac": 0.45, "end_scale": 0.8,
             "wave": {"amplitude": amp, "wavelength": wl}, "felt": felt_lock, "finish": "felt"}
        if mirror:
            r["mirror"] = True
        r.update(kw)
        return r
    st = [
        {"type": "scalp_cap", "name": "cap", "offset": 0.004, "face_cut": [-0.06, 0.9],
         "hairline": [[0, 0.905], [40, 0.88], [70, 0.8], [100, 0.74], [140, 0.71], [180, 0.7]]},
        {"type": "bun", "name": "buns", "buns": [
            {"az": 60, "el": 46, "lift": 0.004, "radius": 0.064, "height": 0.112, "tilt": 0.6, "wrap": "ccw", "turns": 0.6,
             "felt_radii": [1.0, 1.0, 1.0]},
            {"az": -60, "el": 46, "lift": 0.004, "radius": 0.064, "height": 0.112, "tilt": 0.6, "wrap": "cw", "turns": 0.6,
             "felt_radii": [1.0, 1.0, 1.0]}],
         "felt": {"grooves": {"count": 12, "depth": 0.25, "sharpness": 0.5, "wander": 0.6, "wavelength": 0.5},
                  "lumps": {"amount": 0.08, "scale": 1.3}, "resolution": [64, 40]}},
        {"type": "felt_volume", "name": "crown", "shape": "gather", "az": [-180, 180],
         "hairline_el": [[0, 30], [30, 28], [55, 14], [80, 0], [100, -4], [130, 4], [180, 6]],
         "target": pole, "tuck": 1.0, "height": [0.024, 0.045, 0.04], "inset": 0.004,
         "part": {"az": 0, "width_deg": 3.0, "depth": 0.35, "length": 0.45}, "grooves": grooves(36, 0.28),
         "lumps": {"amount": 0.08, "scale": 1.2}, "soft": [0, 0, 0.3, 0.0], "rim": 0.15, "resolution": [220, 48]},
        {"type": "clumps", "name": "fringe", "seg": 16, "grooves": 3, "groove_depth": 0.14, "irregularity": 0.1,
         "rows": [{"count": 8, "az": [-44, 44], "el": [26, 40], "flow": "down", "pole": pole, "len_deg": [30, 42],
                   "lift": [0.012, 0.02], "width": [0.05, 0.062], "thick": [0.024, 0.03], "jitter_deg": 8,
                   "curl_deg": 10, "converge": 0.06, "taper_power": 1.9}]},
        {"type": "clumps", "name": "temples", "seg": 16, "grooves": 3, "groove_depth": 0.14, "irregularity": 0.1,
         "rows": [{"count": 2, "az": [58, 74], "el": [12, 24], "flow": "down", "pole": pole, "len_deg": [22, 30],
                   "lift": [0.01, 0.022], "width": [0.046, 0.056], "thick": [0.024, 0.03], "jitter_deg": 8,
                   "curl_deg": 10, "taper_power": 1.9},
                  {"count": 2, "az": [-74, -58], "el": [12, 24], "flow": "down", "pole": pole, "len_deg": [22, 30],
                   "lift": [0.01, 0.022], "width": [0.046, 0.056], "thick": [0.024, 0.03], "jitter_deg": 8,
                   "curl_deg": 10, "taper_power": 1.9}]},
        {"type": "curtain", "name": "back_mass", "az": [80, 280], "root_el": [[80, 4], [120, 16], [180, 24]],
         "leave_el": -8, "z_end": [[80, 0.6], [120, 0.5], [180, 0.46]], "rest_radii": [0.19, 0.155], "rest_z": 0.55,
         "columns": 10, "thick": 0.03, "column_depth": 0.3, "lobe": {"pitch": 0.075, "depth": 0.2, "twist": 0.2},
         "scallop": 0.035, "resolution": [180, 100], "inset": 0.004},
        wavy("side_locks", 2, [64, 82], [4, 14], -16, [0.6, 0.66], [0.04, 0.048], [0.024, 0.03], 0.012, 0.075,
             mirror=True, hang_radii=[0.16, 0.15]),
        wavy("back_locks", 8, [110, 250], [-10, 4], -26, [0.45, 0.52], [0.058, 0.07], [0.03, 0.036], 0.014, 0.085,
             hang_jitter=0.05, rest_radii=[0.185, 0.16], rest_z=0.62),
        wavy("outer_locks", 2, [76, 104], [0, 10], -20, [0.5, 0.58], [0.05, 0.06], [0.028, 0.034], 0.014, 0.08,
             mirror=True),
        {"type": "felt_bow", "name": "bow", "az": -40, "el": 40, "out": 0.026, "size": 0.14, "tilt_deg": 20,
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
            "fibres": dict(fibre_layers((36.0, 2.0, 0.25, 0.6, 0.8), (3.0, 4.2, 0.3, 0.8, 0.9), (0.08, 10.0, 0.7, 0.7, 0.9)),
                           slots=["hair", "hair_bow"]),
            "dynamics": dyn}
    m = hair_material(c["hair_srgb"], 0.29278, c["hair_note"])
    m["overrides"]["surface"]["saturation_compensation"] = 1.0
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
