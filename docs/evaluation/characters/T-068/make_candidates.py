"""Writes the T-068 candidate overrides (reproducible). Candidates only: no character spec or approved version is
changed. Run from the repository root: python3 docs/evaluation/characters/T-068/make_candidates.py

  candidates/boy_2.0.0-dev.garment_details.override.json   apply on boy_yellow_hoodie.2.0.0-dev.spec.json
  candidates/girl.vest_details.override.json                apply on girl spec + 0.10.0 override
  candidates/girl.gathered_dress.override.json              apply on girl spec + 0.10.0 override (type demo only)
"""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "candidates")
BOY = "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0-dev.spec.json"
GIRL = "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.spec.json"

CREAM = [232, 222, 206]
YELLOW_SHOE = [206, 156, 70]
PACK = [68, 56, 68]  # charcoal-plum (reference_index.json decisions.backpack; the 1.x backpack felt colour)


def load(path):
    return json.load(open(os.path.join(ROOT, path)))


def write(name, doc):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")


def boy():
    clothing = copy.deepcopy(load(BOY)["clothing"])
    items = []
    for g in clothing["garments"]:
        if g["type"] == "hoodie":
            g = copy.deepcopy(g)
            g["armhole"] = "closed"
            g["hood"].update({"rim_back_radius_m": 0.03, "bag_fullness": 0.7, "bag_width_m": 0.1,
                              "bag_height_m": 0.08, "bag_depth_m": 0.03, "bag_drop_m": 0.05, "bag_rise_m": 0.02,
                              "bag_taper": 0.45, "bag_n": 2.4, "edge_drop": 0.5, "edge_radius_m": 0.008})
            items.append(g)
        elif g["type"] == "trousers":
            g = copy.deepcopy(g)
            g["length"] = 0.985  # bunch onto the sneakers' collar (char_C, val27 front)
            items.append(g)
        elif g["type"] == "shoes":
            items.append({
                "type": "sneakers", "name": "shoes", "ease_m": 0.012, "thickness_m": 0.0035,
                "length_extra_m": 0.012, "width_extra_m": 0.006, "height_m": 0.072, "plan_n": 2.6, "dome_n": 2.6,
                "toe_flare": 0.1, "toe_drop": 0.3,
                "sole": {"thickness_m": 0.016, "wrap_m": 0.008, "margin_m": 0.002},
                "toe_cap": {"length": 0.27, "slope": 0.5, "thickness_m": 0.002},
                "laces": {"count": 3, "radius_m": 0.0026, "span": 0.6, "start": 0.08, "end": 0.75},
                "collar": {"radius_m": 0.0055, "rise_m": 0.06, "back_share": 0.15, "falloff_m": 0.05},
                "opening": {"length_m": 0.004, "offset_m": 0.004},
                "tongue": {"thickness_m": 0.003},
                "material": {"preset": "felt", "base_color_srgb": YELLOW_SHOE, "reference_size_m": 0.15},
                "materials": {"sole": {"preset": "felt", "base_color_srgb": CREAM, "reference_size_m": 0.15},
                              "laces": {"preset": "cotton knit", "base_color_srgb": CREAM, "reference_size_m": 0.05}}})
        else:
            items.append(g)
    items.append({
        "type": "backpack", "name": "backpack", "width_m": 0.19, "height_m": 0.2, "depth_m": 0.075,
        "top_drop_m": 0.075, "clearance_m": 0.003, "roundness": 3.2, "puff": 0.6,
        "pocket": {"width": 0.74, "height": 0.42, "depth_m": 0.022, "drop": 0.22},
        "zip": {"radius_m": 0.0018, "puller_m": 0.008},
        "straps": {"width_m": 0.022, "thickness_m": 0.005, "shoulder": 0.5, "lift_m": 0.005},
        "handle": {"radius_m": 0.003},
        "material": {"preset": "felt", "base_color_srgb": PACK, "reference_size_m": 0.2},
        "materials": {"zip": {"preset": "buttons/plastic", "base_color_srgb": [52, 44, 52], "reference_size_m": 0.02}}})
    clothing["garments"] = items
    clothing["provenance"] = (clothing.get("provenance", "") + " T-068 candidate: sneakers (sole, toe cap, laces, "
                              "collar, tongue), backpack (bag, straps over the shoulders, front pocket, zips), hood "
                              "volume and underarm fix; read from canon29 front/side/back/3-4 and val27; values are my "
                              "estimates, tuned by eye.")
    return {"override": {"clothing": clothing,
                         "generators": {"accessories": "none"},
                         "metadata": {"status": "T-068 candidate (unpublished, not approved): garment detail types"}}}


BOW = ["x.......x",
       "xx.....xx",
       "xxx...xxx",
       ".xxxoxxx.",
       "..xooox..",
       ".xxxoxxx.",
       "xxx...xxx",
       "xx.....xx",
       "x.......x"]
MOUNTAINS = ["......o.......o......",
             ".....ooo.....ooo.....",
             "....oo.oo...oo.oo....",
             "...oo...oo.oo...oo...",
             "..oo.....ooo.....oo..",
             ".oo.......o.......oo."]


def girl_vest():
    clothing = copy.deepcopy(load(GIRL)["clothing"])
    for g in clothing["garments"]:
        if g["type"] != "vest":
            continue
        g["pockets"] = {"shape": "patch", "width_m": 0.025, "height_m": 0.026, "depth_m": 0.004,
                        "above_hem_m": 0.04, "corner": 0.55, "top_roll_m": 0.0042, "inset_m": 0.012}
        g["buttons"] = dict(g["buttons"], v0=0.62)  # the edge buttons run above the pockets (#41)
        emb = g["embroidery"]
        emb["motifs"] = [
            {"u": 0.55, "v": 0.74, "style": "cross_stitch", "pattern": BOW, "stitch_m": 0.0062},
            {"u": -0.55, "v": 0.74, "style": "cross_stitch", "pattern": BOW, "stitch_m": 0.0062},
            {"u": 0.6, "v": 0.08, "style": "cross_stitch", "pattern": MOUNTAINS, "stitch_m": 0.0042},
            {"u": -0.6, "v": 0.08, "style": "cross_stitch", "pattern": MOUNTAINS, "stitch_m": 0.0042},
            {"u": 0.0, "v": 0.45, "target": "pocket.L", "style": "cross_stitch", "pattern": MOUNTAINS[2:],
             "stitch_m": 0.003},
            {"u": 0.0, "v": 0.45, "target": "pocket.R", "style": "cross_stitch", "pattern": MOUNTAINS[2:],
             "stitch_m": 0.003}]
        g.setdefault("materials", {})["pocket_edge"] = {"preset": "felt", "base_color_srgb": [58, 32, 38],
                                                         "reference_size_m": 0.05}
    clothing["provenance"] = (clothing.get("provenance", "") + " T-068 candidate: vest details from #41 (exploded "
                              "view, seams & details tiles): flat patch pockets with rounded bottoms and a dark rolled "
                              "top edge; counted cross-stitch decals (dark bow motifs on the upper fronts, pale "
                              "zig-zag 'mountains' over the hem and on the pockets) instead of raised flowers. "
                              "Pattern grids and sizes are my estimates.")
    return {"override": {"clothing": clothing, "metadata": {
        "status": "T-068 candidate (unpublished, not approved): vest details"}}}


def girl_dress():
    """Type demonstration only: the gathered skirt with hem rib (the third character's dress, d09/c15) worn on the
    girl's body, because the third character has no spec yet. Not a proposal for the girl's outfit."""
    clothing = copy.deepcopy(load(GIRL)["clothing"])
    boots = [g for g in clothing["garments"] if g["type"] == "boots"]
    blue = [150, 178, 214]
    dress = {"type": "dress", "name": "dress", "ease_m": 0.012, "sleeve_length": 0.95, "sleeve_puff_m": 0.016,
             "sleeve_puff_peak": 0.6, "length": 0.42, "flare": 0.1,
             "shoulder_width": 1.0, "armhole": "closed",
             "collar": {"type": "round", "width_m": 0.032, "gap_m": 0.008, "slope": 0.45, "tip_round": 0.6},
             "gathers": {"count": 14, "depth_m": 0.014, "waist_depth_m": 0.002},
             "bands": {"cuff": True, "cuff_radius_m": 0.005, "waist": True,
                       "hem_rib": {"height_m": 0.02, "ridges": 72, "relief_m": 0.0012, "gather": 0.7, "lift_m": 0.0015}},
             "material": {"preset": "cotton knit", "base_color_srgb": blue, "reference_size_m": 0.2},
             "edge_finish": "rounded"}
    clothing["garments"] = [dress] + boots
    clothing["provenance"] = ("T-068 type demonstration: gathered skirt with hem rib (girl_white_hair_blue_dress "
                              "d09_dress / c15_front) on the girl's body; values are my estimates.")
    return {"override": {"clothing": clothing, "metadata": {
        "status": "T-068 type demonstration only (not an outfit proposal; unpublished, not approved)"}}}


if __name__ == "__main__":
    write("boy_2.0.0-dev.garment_details.override.json", boy())
    write("girl.vest_details.override.json", girl_vest())
    write("girl.gathered_dress.override.json", girl_dress())
    print("written", OUT)
