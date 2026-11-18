"""T-044/T-070/T-079: writes the hair v3 candidate specs (spec overrides a pin bump would apply) for the three characters into
docs/evaluation/characters/T-079/candidates/. Character data lives in candidates/characters.json (ids, specs,
colours); this script only lays out each hairstyle as groom/2 spec data, read from the references.

    python3 docs/evaluation/characters/T-079/tools/make_candidates.py"""
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
    # T-079 (round 3, against the turnaround and the boy close-up upload 01): the whorl sits at the TOP of the head
    # (pole el 80, slightly back) and every clump radiates from it as a long petal; the crown is a rosette of upright,
    # pointed petals (no fat hooked tufts); clumps are slimmer (thick ~0.45 x width), longer and pointed, with an
    # outward flick at the tips so the outline is jagged/star-like; the felt base and all lifts are lower (less
    # roundness and volume).
    pole = {"az": 180, "el": 80}
    G = {"seg": 18, "grooves": 2, "groove_depth": 0.06, "irregularity": 0.12}
    P = dict(taper_power=2.2, lift_peak=0.55, flick_m=0.014)
    st = [
        {"type": "scalp_cap", "name": "cap", "offset": 0.004},
        {"type": "felt_volume", "name": "base", "shape": "gather", "az": [-180, 180],
         "hairline_el": [[0, 22], [35, 16], [65, 2], [95, -14], [130, -28], [180, -34]], "target": pole, "tuck": 1.0,
         "height": [0.016, 0.028, 0.03], "inset": 0.004,
         "grooves": {"count": 30, "depth": 0.22, "sharpness": 0.6, "wander": 0.4, "wavelength": 0.5},
         "lumps": {"amount": 0.12, "scale": 1.2}, "soft": [0, 0, 0.25, 0.0], "rim": 0.2, "resolution": [160, 40]},
        dict(G, type="clumps", name="whorl", rows=[
            row(5, [-180, 180], [80, 86], "away", [16, 22], [0.028, 0.05, 0.04], [0.05, 0.058], [0.026, 0.03],
                jit=10, curl=40, lift_power=0.8, taper_power=2.0, lift_peak=0.5)]),
        dict(G, type="clumps", name="crown", rows=[
            row(6, [-180, 180], [66, 74], "away", [10, 14], [0.03, 0.12], [0.095, 0.105], [0.044, 0.05],
                jit=6, curl=4, lift_power=1.0, taper_power=1.6, az_list=[-38, 36, 100, 150, 205, 262]),
            row(3, [-180, 180], [66, 78], "away", [30, 40], [0.03, 0.07, 0.06], [0.01, 0.014], [0.008, 0.011],
                jit=25, curl=70, lift_power=1.0, taper_power=1.6, lift_peak=0.45, az_list=[-70, 20, 130])]),
        dict(G, type="clumps", name="top", rows=[
            row(14, [-180, 180], [50, 66], "away", [44, 58], [0.026, 0.056, 0.05], [0.068, 0.08], [0.03, 0.036],
                curl=16, lift_power=0.8, taper_power=2.2, lift_peak=0.5, flick_m=0.012)]),
        dict(G, type="clumps", name="fringe", rows=[
            row(4, [-46, 46], [28, 40], "down", [42, 52], [0.016, 0.026, 0.022], [0.064, 0.074], [0.03, 0.034],
                jit=8, curl=14, converge=0.1, taper_power=2.2, lift_peak=0.6)],
         keepout={"az": 34, "el_min": 1, "margin_deg": 2}),
        dict(G, type="clumps", name="fringe_centre", rows=[
            row(1, [-4, 4], [34, 38], "down", [56, 60], [0.018, 0.03, 0.022], [0.084, 0.084], [0.04, 0.04],
                jit=3, curl=6, taper_power=2.2, lift_peak=0.5, az_list=[3])],
         keepout={"az": 34, "el_min": 0, "margin_deg": 1}),
        dict(G, type="clumps", name="sides", rows=[
            row(2, [47, 66], [8, 22], "down", [34, 40], [0.008, 0.018, 0.018], [0.056, 0.062], [0.026, 0.03],
                jit=8, curl=10, **P),
            row(2, [-66, -47], [8, 22], "down", [34, 40], [0.008, 0.018, 0.018], [0.056, 0.062], [0.026, 0.03],
                jit=8, curl=10, **P),
            row(3, [66, 118], [6, 24], "down", [26, 36], [0.01, 0.026, 0.026], [0.064, 0.074], [0.028, 0.034],
                jit=14, curl=16, **P),
            row(3, [-118, -66], [6, 24], "down", [26, 36], [0.01, 0.026, 0.026], [0.064, 0.074], [0.028, 0.034],
                jit=14, curl=16, **P)]),
        dict(G, type="clumps", name="back", rows=[
            row(10, [118, 242], [14, 34], "down", [34, 46], [0.022, 0.044, 0.044], [0.068, 0.078], [0.03, 0.036],
                jit=14, curl=16, **P),
            row(9, [124, 236], [-16, 4], "down", [20, 28], [0.016, 0.032, 0.03], [0.06, 0.07], [0.028, 0.032],
                jit=14, curl=16, **P)]),
    ]
    dyn = {"enabled": True, "substep_hz": 240, "preroll_s": 1.0,
           "defaults": {"stiffness": 140.0, "stiffness_tip": 100.0, "damping": 9.0, "gravity": 0.2, "drag": 0.8,
                        "limit_deg": 18.0, "radius": 0.012},
           "structures": {"fringe": {"bones": 2, "bone_length": 0.03}, "sides": {"bones": 2, "bone_length": 0.03},
                          "fringe_centre": {"bones": 2, "bone_length": 0.03},
                          "back": {"bones": 2, "bone_length": 0.03},
                          "crown": {"bones": 2, "bone_length": 0.03, "stiffness": 200.0},
                          "whorl": {"bones": 2, "bone_length": 0.025, "stiffness": 220.0}},
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
        r["curl"].update(kw.pop("curl_override", {}))
        r.update(kw)
        return r
    grooves = lambda n, d=0.3: {"count": n, "depth": d, "sharpness": 0.6, "wander": 0.35, "wavelength": 0.5}
    LOOSE = {"curl_override": {"jitter": 0.22, "wobble": 0.2, "wobble_wavelength": 0.13, "sway": 0.008,
                               "start_jitter": 0.06}}
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
         "tip_el": [30, 25, 19, 14, 9, -3, -12], "tip_lift": [0.006, 0.008, 0.012, 0.016, 0.02, 0.024, 0.026],
         "bulge": 0.05, "thick": [0.034, 0.026], "tip_scallop": 0.16, "tip_jitter": 0.1, "resolution": [72, 40],
         "grooves": grooves(9, 0.32), "lumps": {"amount": 0.05}, "soft": [0.08, 0.08, 0.05, 0.14], "rim": 0.12,
         "clearance": 0.003},
        {"type": "felt_volume", "name": "fringe_part", "shape": "fringe", "root_az": [-22, -22, -23, -24, -25],
         "root_el": [48, 56, 64, 72, 80], "tip_az": [-34, -46, -58, -72, -86], "tip_el": [14, 9, 4, -2, -8],
         "tip_lift": [0.006, 0.01, 0.014, 0.018, 0.022], "bulge": 0.034, "thick": [0.03, 0.02], "tip_scallop": 0.16,
         "tip_jitter": 0.1, "resolution": [56, 40], "grooves": grooves(7, 0.32), "lumps": {"amount": 0.05},
         "soft": [0.08, 0.08, 0.05, 0.14], "rim": 0.12, "clearance": 0.003},
        # T-079: a soft swept fringe over the felt fringe base: slim felt strands from the part line that sweep across
        # the forehead towards the left temple with a rolled, curved edge (instead of one flat block)
        {"type": "clumps", "name": "fringe_sweep", "seg": 16, "grooves": 3, "groove_depth": 0.18, "irregularity": 0.1,
         "rows": [{"count": 7, "az": [-22, -4], "el": [50, 72], "flow": "toward", "pole": {"az": 84, "el": 8},
                   "len_deg": [40, 64], "lift": [0.016, 0.03, 0.022], "lift_peak": 0.45, "lift_power": 1.2,
                   "width": [0.044, 0.056], "thick": [0.02, 0.024], "jitter_deg": 6, "curl_deg": 18,
                   "taper_power": 1.8, "flick_m": 0.006}],
         "keepout": {"az": 34, "el_min": 7, "margin_deg": 2}},
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
        # T-079: looser, varied ringlets instead of identical rows of coils: every ringlet group is split into two
        # interleaved sets with different coil radius, pitch, length and turn direction, with strong per-lock jitter,
        # wobble and sway, so neighbouring curls never line up in rows.
        ringlets("ringlets_side", 2, [66, 96], [6, 18], -14, [0.49, 0.57], [0.036, 0.04], [0.033, 0.036], 0.02,
                 0.09, mirror=True, start=0.02, **LOOSE),
        ringlets("ringlets_side_b", 1, [74, 90], [8, 16], -14, [0.53, 0.6], [0.034, 0.038], [0.031, 0.034], 0.016,
                 0.07, mirror=True, start=0.05, **LOOSE),
        ringlets("ringlets_back", 7, [124, 236], [-14, -4], -30, [0.4, 0.47], [0.038, 0.042], [0.034, 0.038],
                 0.022, 0.095, hang_jitter=0.1, rest_radii=[0.2, 0.17], rest_z=0.62, start=0.0, **LOOSE),
        ringlets("ringlets_back_b", 6, [130, 230], [-10, 0], -26, [0.43, 0.5], [0.034, 0.038], [0.031, 0.034],
                 0.017, 0.075, hang_jitter=0.12, rest_radii=[0.2, 0.17], rest_z=0.62, start=0.04, **LOOSE),
        ringlets("ringlets_outer", 2, [100, 122], [-2, 10], -22, [0.42, 0.5], [0.038, 0.042], [0.034, 0.037],
                 0.021, 0.09, mirror=True, rest_radii=[0.21, 0.175], rest_z=0.62, start=0.02, **LOOSE),
        ringlets("ringlets_outer_b", 1, [106, 118], [0, 8], -22, [0.46, 0.52], [0.034, 0.038], [0.031, 0.034],
                 0.017, 0.072, mirror=True, rest_radii=[0.21, 0.175], rest_z=0.62, start=0.05, **LOOSE),
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
                          "ringlets_side_b": {"bones": [3, 4], "bone_length": 0.06},
                          "ringlets_back": {"bones": [3, 5], "bone_length": 0.07},
                          "ringlets_back_b": {"bones": [3, 5], "bone_length": 0.07},
                          "ringlets_outer": {"bones": [3, 5], "bone_length": 0.07},
                          "ringlets_outer_b": {"bones": [3, 5], "bone_length": 0.07},
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
    felt_lock = {"seg": 18, "irregularity": 0.14, "wavelength": 0.12, "flatten": 0.4, "flatten_twist": 0.5}
    grooves = lambda n, d=0.3: {"count": n, "depth": d, "sharpness": 0.55, "wander": 0.45, "wavelength": 0.5}

    def wavy(name, count, az, el_root, el_leave, z_end, width, thick, radius, pitch, mirror=False, **kw):
        """T-070: big soft S-waves (a flattened helix, ellipse < 1) ending in a soft curl, wide flat felt locks."""
        r = {"type": "locks", "name": name, "style": "curly", "count": count, "az": az, "el_root": el_root,
             "el_leave": el_leave, "lift": [0.006, 0.016], "hang_radii": [0.165, 0.16], "z_end": z_end, "flare": 0.16,
             "width": width, "thick": thick, "tip_frac": 0.5, "end_scale": 0.75,
             "curl": {"radius": radius, "pitch": pitch, "radius_growth": 0.1, "start": -0.07, "start_jitter": 0.04,
                      "direction": "alternate", "jitter": 0.22, "wobble": 0.14, "wobble_wavelength": 0.2,
                      "sway": 0.004, "ellipse": 0.14, "tip": {"from": 0.85, "radius": 0.7, "pitch": 0.9,
                                                              "ellipse": 0.25}},
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
         "part": {"az": 0, "width_deg": 3.0, "depth": 0.35, "length": 0.45}, "grooves": grooves(24, 0.06),
         "lumps": {"amount": 0.05, "scale": 1.2}, "soft": [0, 0, 0.3, 0.0], "rim": 0.15, "resolution": [220, 48]},
        # T-079: a soft fringe: overlapping, broad felt clumps with rounded (blunt) tips of uneven length in two
        # layers, instead of a row of pointed triangles
        {"type": "clumps", "name": "fringe", "seg": 18, "grooves": 3, "groove_depth": 0.1, "irregularity": 0.12,
         "rows": [{"count": 11, "az": [-50, 50], "el": [36, 46], "flow": "down", "pole": pole, "len_deg": [34, 42],
                   "lift": [0.012, 0.02, 0.016], "lift_peak": 0.5, "width": [0.064, 0.074], "thick": [0.02, 0.024],
                   "jitter_deg": 7, "curl_deg": 12, "converge": 0.03, "taper_power": 4.0},
                  {"count": 8, "az": [-44, 44], "el": [40, 50], "flow": "down", "pole": pole, "len_deg": [30, 38],
                   "lift": [0.016, 0.026, 0.022], "lift_peak": 0.5, "width": [0.056, 0.066], "thick": [0.018, 0.022],
                   "jitter_deg": 9, "curl_deg": 16, "converge": 0.03, "taper_power": 3.2}],
         "keepout": {"az": 34, "el_min": 6, "margin_deg": 2}},
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
        # T-079: fluffy soft S-waves: broader, flat felt ribbons (flatten 0.55) that overlap (more locks, less gap to
        # the curtain), with varied wave size and length, instead of separate round ropes
        wavy("side_locks", 3, [60, 84], [4, 14], -16, [0.55, 0.62], [0.064, 0.07], [0.036, 0.04], 0.034, 0.16,
             mirror=True, hang_radii=[0.165, 0.155]),
        wavy("back_locks", 12, [106, 254], [0, 16], -14, [0.44, 0.51], [0.08, 0.09], [0.04, 0.046], 0.044, 0.17,
             hang_jitter=0.08, rest_radii=[0.2, 0.165], rest_z=0.6),
        wavy("outer_locks", 2, [84, 108], [2, 14], -14, [0.49, 0.56], [0.074, 0.082], [0.038, 0.044], 0.042, 0.17,
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
            "fibres": dict(fibre_layers((40.0, 2.6, 0.12, 0.9, 0.6), (7.0, 6.0, 0.3, 0.85, 0.8), (0.16, 10.0, 0.6, 0.7, 0.9),
                                        shafts=(0.14, 0.09, 0.06)),
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
    out = {"schema": "plush-studio.hair-candidate/1", "task": "T-079", "character_spec": c["spec"],
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
