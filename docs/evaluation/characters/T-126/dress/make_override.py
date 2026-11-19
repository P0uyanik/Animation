"""T-126c: the dress / tights / boots override of girl_white_hair_blue_dress (candidate input, nothing is published).

    python3 docs/evaluation/characters/T-126/dress/make_override.py [--plain]

Writes ``girl_white_hair_blue_dress.dress.override.json`` next to this file: generator pin ``garment/3`` and the whole
clothing block (the spec merger replaces arrays). It applies to any base spec of hers (the T-070 draft
``third.base.spec.json`` or T-126a's base spec): sizes are metres read off references 09 and 16 against a 1.10 m
figure and are my estimates, not fitted values. Colours are the medians of ``references/color_targets.json``; the
material presets are existing ones (her own preset file is T-126d's part).
``--plain`` writes ``plain.override.json``: the same outfit with garment/2-era fields only (no tights, pattern, knit
direction or pile), the first silhouette check of the readiness note."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
DRESS, COLLAR, CUFFS, TIGHTS, BOOTS = [154, 175, 186], [161, 178, 186], [149, 162, 169], [197, 187, 177], [162, 124, 90]
SOLE = [118, 88, 62]  # 16: the sole edge is a darker tan than the pile (my estimate)


def knit(colour, wale_m, uv, fuzz_mm=0.9, strength=0.4):
    """The existing ``cotton knit`` preset with overrides only (her own preset file is T-126d's part): ``wale_m`` is
    the width of one knit column (the preset's band wave has one column per 1/66 of the reference size), ``uv`` makes the columns follow the piece
    (``fibre_uv``) instead of object axes, and the preset's long fuzz and bright nap flecks are reduced to a short
    halo so stitches and relief stay readable, as in 16."""
    fibre = {"strength": strength, "distortion": 0.25}
    if uv:
        fibre["coordinates"] = "uv"
    return {"preset": "cotton knit", "base_color_srgb": colour, "reference_size_m": round(66 * wale_m, 4),
            "overrides": {"fibre": fibre, "nap": {"value_gain": 0.15, "sheen_gain": 0.2, "fibre_gloss": 0.2},
                          "fibres": {"length_mm": fuzz_mm, "density_per_cm2": 12.0, "color_variation": 0.2},
                          "surface_detail": {"lump_strength": 0.1}}}


def clothing(plain=False):
    dress = {
        "type": "dress", "name": "dress", "ease_m": 0.007, "thickness_m": 0.003,
        "sleeve_length": 0.97, "sleeve_start": 0.0, "armhole": "closed", "sleeve_puff_m": 0.014, "sleeve_puff_peak": 0.72,
        "waist_z_m": 0.467, "length_m": 0.203, "flare": 0.072,
        "gathers": {"count": 12, "depth_m": 0.014, "waist_depth_m": 0.004},
        "collar": {"type": "round", "width_m": 0.036, "gap_m": 0.003, "slope": 0.5, "tip_round": 0.85, "lift_m": 0.0},
        "collar_seat": {"over": [], "thickness_m": 0.004},
        "bands": {"cuff": True, "cuff_radius_m": 0.003,
                  "hem_rib": {"ridges": 90, "height_m": 0.018, "relief_m": 0.0016, "gather": 0.6, "thickness_m": 0.0025, "lift_m": 0.001}},
        "rib_cuff": {"height_m": 0.03, "ribs": 18, "depth_m": 0.0026, "thickness_m": 0.004, "tighten": 0.08},
        "material": knit(DRESS, 0.0036, not plain),
        "materials": {"collar": knit(COLLAR, 0.0036, not plain), "band": knit(CUFFS, 0.0036, not plain)},
        "edge_finish": "rounded",
        "drape": {"enabled": False, "fabric": "cotton", "gather": 0.2, "gravity": 0.4, "overrides": {"bending": 6.0},
                  "pin": ["edges", "volume"], "edge_band_m": 0.004, "volume_band_m": 0.003, "smooth": 3, "seed": 126},
    }
    boots = {
        "type": "boots", "name": "boots", "height": 0.46, "ease_m": 0.02, "cuff": True,
        "bands": {"cuff": True, "cuff_radius_m": 0.009}, "sole": {"thickness_m": 0.007, "width_m": 0.0},
        "material": {"preset": "boot fleece", "base_color_srgb": BOOTS, "reference_size_m": 0.15,
                     "overrides": {"surface": {"sheen_weight": 0.25}}},
        "materials": {"band": {"preset": "cuff fleece/3", "base_color_srgb": BOOTS, "reference_size_m": 0.15},
                      "sole": {"preset": "felt", "base_color_srgb": SOLE, "reference_size_m": 0.15}},
        "shaft_width_m": 0.014, "toe_volume_m": 0.016, "edge_finish": "rounded",
        "cuff_roll": {"height_m": 0.06, "thickness_m": 0.0065, "inner_m": 0.014, "lumps": 0.3},
    }
    items = [dress, boots]
    if not plain:
        dress["fibre_uv"] = True
        dress["skirt_pattern"] = {"panels": 12, "relief_m": 0.005, "cable_share": 0.4, "twists": 3.5, "leaf_rows": 5,
                                  "leaf_slope": 0.55, "top": 0.94, "bottom_m": 0.02, "subdivide": 2}
        dress["cloth_sim"] = {"pin_top": 0.03, "pin_blend": 0.05}
        tights = {"type": "tights", "name": "tights", "waist_z_m": 0.4, "ease_m": 0.0025, "thickness_m": 0.0012,
                  "fibre_uv": True, "material": knit(TIGHTS, 0.0022, True, fuzz_mm=0.8, strength=0.35)}
        boots["sole_stitch"] = {"pitch_m": 0.009, "radius_m": 0.0017, "length": 0.55, "above_m": 0.012}
        boots["materials"]["stitch"] = {"preset": "wool yarn", "base_color_srgb": [205, 178, 140], "reference_size_m": 0.05}
        items = [tights, dress, boots]
    return {
        "generator": "garment/2" if plain else "garment/3",
        "provenance": "T-126c: outfit read off references 09 (dress construction and deformation blueprint) and 16 "
                      "(W05: dress, tights, boots). Sizes are my estimates on a 1.10 m figure; colours are the medians "
                      "of references/color_targets.json (dress, collar, cuffs, tights, boots).",
        "description": ["powder-blue knit dress: stockinette bodice and sleeves, Peter Pan collar, rib cuffs, flared "
                        "cable/leaf-knit skirt with a rib hem", "cream cotton tights", "tan fleece boots, turned-down "
                        "long-pile cuff, stitched sole"],
        "hide_body_faces": True, "mask_margin_m": 0.015,
        "collision": {"enabled": True, "offset_m": 0.002, "radius_m": 0.08, "falloff_m": 0.02, "passes": 3},
        "max_influences": 4,
        "defaults": {"thickness_m": 0.002, "ease_m": 0.008, "seam_radius_m": 0.0012},
        "garments": items,
    }


def main():
    plain = "--plain" in sys.argv
    gen = "garment/2" if plain else "garment/3"
    override = {"generators": {"garment": gen}, "clothing": clothing(plain),
                "metadata": {"notes": "T-126c dress/tights/boots override (candidate input; not published, not current)"
                             + (", plain silhouette check" if plain else "")}}
    path = os.path.join(HERE, "plain.override.json" if plain else "girl_white_hair_blue_dress.dress.override.json")
    with open(path, "w") as f:
        json.dump({"override": override}, f, indent=1)
        f.write("\n")
    print(os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
