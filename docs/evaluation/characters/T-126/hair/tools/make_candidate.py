"""T-126b: writes the hair override of girl_white_hair_blue_dress (groom/4; plain Python, deterministic).

    python3 docs/evaluation/characters/T-126/hair/tools/make_candidate.py

Output: docs/evaluation/characters/T-126/hair/candidates/girl_white_hair_blue_dress.hair.override.json, an override
on T-126a's base spec (girl_white_hair_blue_dress.0.1.0.spec.json): spec.generators.groom and spec.hair only. The
structure names that carry dynamics settings in the base (buns, fringe, temples, side_locks, back_locks, outer_locks)
are kept, so the dict merge leaves no stale entry. Sizes below were first laid out on the T-070 draft head (FIXTURE)
and are scaled to her head (HEAD) by `fit`.
Read from uploads 07 (blueprint), 08 (rig), 17 (W04 back waves + buns), 18 (W02 bow, canonical), 01 (front)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "candidates")
CID = "girl_white_hair_blue_dress"

FIXTURE = {"centre_z": 0.825, "radius": 0.1407}  # T-070 third.base.spec draft: head centre height, mean half-axis
HEAD = {"centre_z": 0.82671 * 0.94284, "radius": (0.1366 + 0.13528 + 0.14529) / 3 * 0.94284}  # T-126a base spec 0.1.0
K = HEAD["radius"] / FIXTURE["radius"]
LENGTHS = ("hang_radii", "rest_radii", "width", "thick", "lift", "radius", "size", "amplitude", "wavelength",
           "start_m", "height")
HEIGHTS = ("rest_z",)


def fit(x, key=None, st=None):
    """Scales the lengths of a structure from the fixture head to her head; absolute heights move with the head."""
    def sc(v):
        return [sc(i) for i in v] if isinstance(v, list) else round(float(v) * K, 5)

    def zz(v):
        return [zz(i) for i in v] if isinstance(v, list) else round(HEAD["centre_z"] + (float(v) - FIXTURE["centre_z"]) * K, 5)

    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            if k == "z_end" and key == "stagger":
                out[k] = sc(v)
            elif k == "z_end":
                out[k] = [[a, zz(z)] for a, z in v] if x.get("type") == "curtain" else zz(v)
            elif k in HEIGHTS:
                out[k] = zz(v)
            elif k in LENGTHS and isinstance(v, (int, float, list)) and not (k == "lift" and x.get("type") == "bun"):
                out[k] = sc(v)
            elif k in ("wave", "buns", "items", "stagger"):  # other nested blocks hold relative values
                out[k] = fit(v, k, x)
            else:
                out[k] = v
        return out
    if isinstance(x, list):
        return [fit(i, key, st) for i in x]
    return x


FELT_LOCK = {"seg": 16, "irregularity": 0.1, "wavelength": 0.16, "flatten": 0.3, "flatten_twist": 0.5}
MASS = {"seg": 18, "grooves": 2, "groove_depth": 0.14, "irregularity": 0.1}


def wavy(name, **kw):
    base = {"type": "locks", "name": name, "style": "wavy", "finish": "felt", "felt": FELT_LOCK,
            "el_leave": -12, "lift": [0.008, 0.022], "tip_frac": 0.45, "end_scale": 0.58, "flare": 0.05}
    base.update(kw)
    return base


def fringe_items():
    # 07/01: chunky fringe clumps from the crown to the brow line, the outer ones longer (they frame the cheeks)
    items = []
    for az, tip_el, w in ((-44, -4, 0.058), (-30, 6, 0.064), (-15, 7.5, 0.066), (0, 6.5, 0.062), (15, 7.5, 0.066),
                          (30, 6, 0.064), (44, -4, 0.058)):
        items.append({"root": [round(az * 0.5, 2), 64], "tip": [az + (2 if az >= 0 else -2), tip_el], "width": w,
                      "depth": 0.55, "lift": [0.01, 0.034, 0.008], "hold": 0.6, "taper_power": 1.8, "layer": 1,
                      "curl_deg": 4 if az > 0 else -4})
    return items


def temple_items():
    return [{"root": [sx * 52, 44], "tip": [sx * 62, -20], "width": 0.056, "depth": 0.6, "lift": [0.008, 0.03, 0.014],
             "hold": 0.55, "taper_power": 1.5, "layer": 0, "curl_deg": sx * 6} for sx in (1, -1)]


def hair():
    bun = {"lift": 0.004, "radius": 0.082, "height": 0.14, "tilt": 0.5, "turns": 1.3, "felt_radii": [1.0, 1.0, 1.0]}
    structures = [
        {"type": "scalp_cap", "name": "cap", "offset": 0.004, "face_cut": [-0.06, 0.9],
         "hairline": [[0, 0.905], [40, 0.88], [70, 0.8], [100, 0.74], [140, 0.71], [180, 0.7]]},
        # 07, 17: two round top buns, strands wrapped round them (swirled grooves in the felt)
        {"type": "bun", "name": "buns",
         "buns": [dict(bun, az=56, el=54, wrap="ccw"), dict(bun, az=-56, el=54, wrap="cw")],
         "felt": {"grooves": {"count": 11, "depth": 0.34, "sharpness": 0.62, "wander": 0.5, "wavelength": 0.5},
                  "lumps": {"amount": 0.05, "scale": 1.2}, "resolution": [72, 44]}},
        # smooth scalp coverage combed up to the crown (07 "scalp coverage")
        {"type": "felt_volume", "name": "crown", "shape": "gather", "az": [-180, 180],
         "hairline_el": [[0, 30], [30, 28], [55, 14], [80, 0], [100, -4], [130, 4], [180, 6]],
         "target": {"az": 0, "el": 90}, "tuck": 1.0, "height": [0.014, 0.044, 0.046], "inset": 0.004,
         "part": {"az": 0, "width_deg": 3.0, "depth": 0.3, "length": 0.4},
         "grooves": {"count": 30, "depth": 0.2, "sharpness": 0.6, "wander": 0.45, "wavelength": 0.5},
         "lumps": {"amount": 0.05, "scale": 1.2}, "soft": [0, 0, 0.3, 0.0], "rim": 0.15, "resolution": [220, 48]},
        dict(MASS, type="masses", name="fringe", items=fringe_items()),
        dict(MASS, type="masses", name="temples", items=temple_items()),
        # 17: the felted back is one mass under the locks and splits into locks lower down
        {"type": "curtain", "name": "back_mass", "az": [78, 282], "root_el": [[78, 4], [120, 18], [180, 26]],
         "leave_el": -8, "z_end": [[78, 0.66], [120, 0.6], [180, 0.57]], "rest_radii": [0.2, 0.158], "rest_z": 0.62,
         "columns": 10, "thick": 0.016, "column_depth": 0.25, "lobe": {"pitch": 0.12, "depth": 0.0, "twist": 0.2},
         "scallop": 0.035, "resolution": [180, 100], "inset": 0.004},
        # 17: long separated locks, soft S-waves that run roughly together, staggered tapered tips
        wavy("back_under", count=7, az=[112, 248], el_root=[6, 16], lift=[0.02, 0.026], hang_radii=[0.176, 0.158],
             rest_radii=[0.196, 0.156], rest_z=0.62, z_end=[0.46, 0.49], width=[0.078, 0.086], thick=[0.042, 0.046],
             wave={"amplitude": 0.017, "wavelength": 0.145, "depth": 0.25, "tip_gain": 1.3, "start_m": -0.08},
             stagger={"z_end": [0.03, -0.02, 0.05, 0.0], "end_scale": [1.0, 0.85, 1.15],
                      "phase_deg": [190, 160, 215, 175, 200]}),
        wavy("back_locks", count=8, az=[104, 256], el_root=[30, 40], lift=[0.04, 0.046], hang_radii=[0.2, 0.182],
             rest_radii=[0.216, 0.176], rest_z=0.62, z_end=[0.44, 0.47], width=[0.08, 0.088], thick=[0.044, 0.05],
             wave={"amplitude": 0.019, "wavelength": 0.14, "depth": 0.3, "tip_gain": 1.35, "start_m": -0.1},
             stagger={"z_end": [0.0, 0.05, -0.02, 0.07, 0.02], "end_scale": [1.0, 0.8, 1.1],
                      "phase_deg": [0, 25, -15, 35, 10, -25, 20]}),
        wavy("outer_locks", count=2, mirror=True, az=[80, 104], el_root=[22, 32], lift=[0.036, 0.04], hang_radii=[0.226, 0.186],
             rest_radii=[0.236, 0.182], rest_z=0.62, z_end=[0.48, 0.51], width=[0.072, 0.08], thick=[0.04, 0.046],
             wave={"amplitude": 0.02, "wavelength": 0.135, "depth": 0.3, "tip_gain": 1.3, "start_m": -0.08},
             stagger={"z_end": [0.0, 0.04], "end_scale": [1.0, 0.85], "phase_deg": [30, -10], "mirror_shift": 1}),
        # 07: wavy side locks in front of the ears, down to the chest
        wavy("side_locks", count=2, mirror=True, az=[54, 80], el_root=[6, 16], el_leave=-16,
             hang_radii=[0.192, 0.166], z_end=[0.52, 0.56], width=[0.056, 0.062], thick=[0.034, 0.038],
             wave={"amplitude": 0.015, "wavelength": 0.12, "depth": 0.35, "tip_gain": 1.25, "start_m": -0.04},
             stagger={"z_end": [0.03, 0.0], "end_scale": [0.9, 1.0], "phase_deg": [60, 20], "mirror_shift": 1}),
        # 18 (canonical): dusty-blue felt bow, two rounded loops, wrapped knot, two short tails; on the character's
        # right in front of and below the bun, on the fringe roots (01), seated on the built hair surface
        {"type": "felt_bow", "name": "bow", "az": -37, "el": 33, "out": 0.004, "seat": "hair", "size": 0.122,
         "tilt_deg": -14, "knot": 0.15, "material": "hair_bow",
         "loops": [{"angle_deg": 22, "length": 0.56, "width": 0.38, "thick": 0.24},
                   {"angle_deg": 158, "length": 0.56, "width": 0.38, "thick": 0.24},
                   {"angle_deg": 248, "length": 0.5, "width": 0.2, "thick": 0.16},
                   {"angle_deg": 296, "length": 0.46, "width": 0.2, "thick": 0.16}],
         "grooves": {"count": 3, "depth": 0.12, "sharpness": 0.4, "wander": 0.3, "wavelength": 0.6},
         "turn": {"toward": [-20, 20], "amount": 0.35}},
    ]
    lock_dyn = {"bones": [3, 5], "bone_length": 0.07}
    return {
        "generator": "groom/4", "seed": 52, "finish": "felt", "scalp_offset_m": 0.008,
        "face_keepout": {"az": 34, "el_min": 4, "margin_deg": 1},
        "binding": {"blend_z": [0.6, 0.72]},
        "fibres": {"slots": ["hair", "hair_bow"], "layers": [
            {"name": "felt", "shaft_radius_mm": 0.14, "overrides": {
                "fibres": {"density_per_cm2": 40.0, "length_mm": 2.6, "curl": 0.06, "lean": 0.9, "lean_variation": 0.5},
                "surface": {"saturation_compensation": 1.0}}},
            {"name": "halo", "shaft_radius_mm": 0.1, "overrides": {
                "fibres": {"density_per_cm2": 4.0, "length_mm": 6.0, "curl": 0.08, "lean": 0.9, "lean_variation": 0.6},
                "surface": {"saturation_compensation": 1.0}}},
            {"name": "flyaways", "shaft_radius_mm": 0.07, "overrides": {
                "fibres": {"density_per_cm2": 0.08, "length_mm": 10.0, "curl": 0.4, "lean": 0.7, "lean_variation": 0.9},
                "surface": {"saturation_compensation": 1.0}}}]},
        "structures": [fit(s) for s in structures],
        "dynamics": {"enabled": True, "substep_hz": 240, "preroll_s": 1.0,
                     "defaults": {"stiffness": 90.0, "stiffness_tip": 60.0, "damping": 7.0, "gravity": 0.5, "drag": 0.8,
                                  "limit_deg": 28.0, "radius": 0.014},
                     "structures": {
                         "buns": {"bones": 3, "stiffness": 150.0, "stiffness_tip": 120.0, "damping": 9.0, "gravity": 0.3,
                                  "limit_deg": 12.0, "radius": 0.0},
                         "back_under": lock_dyn, "back_locks": lock_dyn, "outer_locks": lock_dyn,
                         "side_locks": {"bones": [3, 4], "bone_length": 0.06}},
                     "colliders": [
                         {"name": "head", "type": "sphere", "bone": "head", "head_offset": [0.0, 0.0, -0.004], "radius": 0.128},
                         {"name": "torso", "type": "capsule", "bone": "chest", "a": [0.0, 0.004, 0.4], "b": [0.0, 0.004, 0.56],
                          "radius": 0.082},
                         {"name": "shoulder_l", "type": "sphere", "bone": "chest", "head_offset": [0.1, 0.0, -0.24], "radius": 0.045},
                         {"name": "shoulder_r", "type": "sphere", "bone": "chest", "head_offset": [-0.1, 0.0, -0.24],
                          "radius": 0.045}]},
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {"task": "T-126b", "character": CID, "status": "candidate (not published, not current)"}
    json.dump({"override": {"generators": {"groom": "groom/4"}, "hair": hair()},
               "metadata": dict(meta, note="hair only: generators.groom and spec.hair; the base spec's hair block "
                                           "should carry no dynamics.structures of other hairstyles (dict merge)")},
              open(os.path.join(OUT, f"{CID}.hair.override.json"), "w"), indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
