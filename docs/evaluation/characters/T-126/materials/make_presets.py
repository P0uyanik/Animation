"""Writes pipeline/charsys/materials/presets_third.json (T-126d): the third character's opt-in presets/3 materials.

    python3 docs/evaluation/characters/T-126/materials/make_presets.py

Each preset starts from the closest existing preset (named in "derived_from") and changes only what refs 10 and 16_W05
call for. Older library files are read, never written. Base colours stay spec data (see patches.plan.json).
"""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 5))
MAT = os.path.join(ROOT, "pipeline", "charsys", "materials")
P1 = json.load(open(os.path.join(MAT, "presets.json"), encoding="utf-8"))["presets"]
R2 = json.load(open(os.path.join(MAT, "presets_r2.json"), encoding="utf-8"))
R3 = json.load(open(os.path.join(MAT, "skin_presets_r3.json"), encoding="utf-8"))["presets"]


def merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def derive(src, name, over):
    p = merge(src, over)
    p["derived_from"] = name
    return p


T = {
    "fuzz_felt": {"range": [3.0, 8.0], "source": "VISUAL_TARGET.md: Surface fuzz amount, felt/fleece"},
    "sheen_cloth": {"range": [1.08, 1.22], "source": "VISUAL_TARGET.md: Sheen/roughness read, cloth/felt"},
    "sat": {"range": [75.0, 110.0], "source": "VISUAL_TARGET.md: Material colour saturation"},
}

presets = {
    # Ref 10 M_Hair_Felt: dense felted wool, natural fibre halo, off-white, matte (spec 0.1, rough 0.85). The brown
    # felt hair's saturation_compensation 2.1 would push cream to yellow; its nap value_gain 1.4 speckles a light dye.
    "felt hair cream/3": derive(P1["felt hair"], "felt hair (presets/1)", {
        "description": "Cream/off-white felted wool hair (ref 10 M_Hair_Felt, 17_W04): matte (spec 0.1, rough 0.85), a "
                       "fine even fibre halo, low nap contrast so a light dye does not speckle or yellow.",
        "swatch_srgb": [214, 202, 186],
        "surface": {"roughness": 0.85, "specular_ior_level": 0.1, "sheen_weight": 0.35, "sheen_roughness": 0.66,
                    "sheen_tint": 0.5, "saturation_compensation": 1.0, "shadow_transmission": 0.6},
        "micro_relief": {"color_strength": 0.25, "roughness_variation": 0.25},
        "nap": {"value_gain": 0.2, "sheen_gain": 0.35, "roughness_drop": 0.1, "fibre_gloss": 0.2},
        "fibres": {"density_per_cm2": 24.0, "length_mm": 4.2, "color_variation": 0.12, "lean_variation": 0.5},
        "silhouette": {"weight": 0.8},
        "targets": {"fuzz_rms_y255": T["fuzz_felt"],
                    "sheen_p90_p50": {"range": [1.1, 1.28], "source": "VISUAL_TARGET.md: plush hair"},
                    "saturation_retention_percent": None},
    }),
    # Ref 10 M_Skin_Flock: short-pile flocking / micro-fibre, SSS enabled, warm tint. skin-felt/3 already carries the
    # flock layer and SSS; the flock albedo is raised (visible micro-pile in the swatch) and the rim sheen kept low.
    "skin-flock/3": derive(R2["presets"]["skin-felt/3"], "skin-felt/3 (presets_r2.json)", {
        "description": "Porcelain-peach flocked skin (ref 10 M_Skin_Flock): short-pile flock with subsurface "
                       "scattering and a warm tint; a slightly stronger flock than skin-felt/3, lower rim sheen. "
                       "Non-emissive.",
        "swatch_srgb": [226, 196, 178],
        "surface": {"sheen_weight": 0.35},
        "skin": {"flock": {"albedo": 0.05}},
    }),
    # Ref 10 M_Dress_Knit + 16_W05: muted-blue stockinette/cable knit, visible yarn fibres. The shader gives the knit
    # loop relief and yarn halo; the cable/leaf motifs are garment geometry (T-126c), not this preset.
    "cable knit/3": derive(P1["cotton knit"], "cotton knit (presets/1)", {
        "description": "Muted-blue wool knit (ref 10 M_Dress_Knit, 16_W05): soft stockinette loop relief with a short, "
                       "even yarn halo; dye-tinted sheen, no bright nap speckle. Cable and leaf motifs come from the "
                       "garment geometry (T-126c).",
        "swatch_srgb": [140, 162, 180],
        "surface": {"roughness": 0.92, "sheen_weight": 0.35, "sheen_roughness": 0.64, "sheen_tint": 0.6},
        "fibre": {"strength": 0.36, "scale_per_reference": 40.0},
        "micro_relief": {"color_strength": 0.15, "roughness_variation": 0.2},
        "nap": {"value_gain": 0.12, "sheen_gain": 0.3, "roughness_drop": 0.08, "fibre_gloss": 0.15},
        "fibres": {"density_per_cm2": 22.0, "length_mm": 2.4, "color_variation": 0.12, "lean_variation": 0.4},
        "silhouette": {"weight": 0.6},
        "targets": {"fuzz_rms_y255": T["fuzz_felt"], "sheen_p90_p50": T["sheen_cloth"],
                    "saturation_retention_percent": T["sat"]},
    }),
    # Ref 10 M_Tights_Cotton: matte knitted cotton, dense fine weave, off-white; very little halo.
    "cotton tights/3": derive(P1["cotton knit"], "cotton knit (presets/1)", {
        "description": "Off-white cotton tights (ref 10 M_Tights_Cotton, 16_W05): matte, dense fine jersey; a fine "
                       "vertical knit read, almost no halo.",
        "swatch_srgb": [205, 195, 184],
        "surface": {"roughness": 0.9, "sheen_weight": 0.2, "sheen_roughness": 0.6, "sheen_tint": 0.4},
        "fibre": {"scale_per_reference": 90.0, "strength": 0.22, "distance_fraction": 0.002},
        "micro_relief": {"scale_per_reference": 140.0, "color_strength": 0.08, "roughness_variation": 0.15},
        "surface_detail": {"lump_strength": 0.12, "lump_albedo": 0.02, "fibre_strength": 0.08, "fibre_albedo": 0.02},
        "nap": {"enabled": False},
        "fibres": {"density_per_cm2": 10.0, "length_mm": 1.2, "color_variation": 0.08, "lean_variation": 0.3},
        "silhouette": {"weight": 0.35},
        "targets": {"fuzz_rms_y255": {"range": [1.0, 5.0], "source": "VISUAL_TARGET.md: fabric surface; T-126d fine "
                                      "jersey (lower ceiling)"},
                    "sheen_p90_p50": T["sheen_cloth"], "saturation_retention_percent": None},
    }),
    # Ref 10 M_Boots_Fleece: shaggy faux-fur, high-density pile, camel/brown; 16_W05 shows long leaning tufts.
    "boot shag/3": derive(P1["boot fleece"], "boot fleece (presets/1)", {
        "description": "Camel shaggy faux-fur boots (ref 10 M_Boots_Fleece, 16_W05): a dense, long, leaning pile in "
                       "soft tufts with a broad dye-tinted sheen.",
        "swatch_srgb": [150, 110, 78],
        "nap": {"value_gain": 0.18},
        "fibres": {"density_per_cm2": 44.0, "length_mm": 6.5, "curl": 0.5, "lean": 0.55, "color_variation": 0.2},
        "micro_relief": {"color_strength": 0.3},
    }),
    # Ref 10 BOW: felted fibre fabric, dusty blue, rough 0.9 (18_W02 canonical blue felt bow).
    "bow felt/3": derive(R2["presets"]["vest felt/3"], "vest felt/3 (presets_r2.json)", {
        "description": "Dusty-blue pressed felt for the bow (ref 10 BOW, 18_W02): rough 0.9, a fine even pebble and a "
                       "short fuzz halo.",
        "swatch_srgb": [92, 110, 132],
        "surface": {"roughness": 0.9, "saturation_compensation": 1.0},
    }),
}

data = {
    "schema": R2["schema"], "family": R2["family"], "kind": "fabric_and_skin",
    "note": "T-126d: the third character's (girl_white_hair_blue_dress) material set, one more self-contained library "
            "file of the presets/3 family (same schema and rules as presets_r2.json, its own defaults, new ids only; no "
            "id of an older library file is redefined). Opt-in only: a spec names an id of this file in "
            "materials.assignments.<slot>.preset; every other spec builds exactly as before. Sources: refs 10 "
            "(material spec) and 16_W05, colours from references/color_targets.json (base colours stay spec data). "
            "Generated by docs/evaluation/characters/T-126/materials/make_presets.py.",
    "reference_size_m": R2["reference_size_m"],
    "defaults": R2["defaults"],
    "presets": presets,
}
with open(os.path.join(MAT, "presets_third.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(data, fh, indent=1)
    fh.write("\n")
