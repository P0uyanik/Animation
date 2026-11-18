"""T-093: writes the candidate overrides (garment/2 pin + garment data) from the published specs.

    python3 docs/evaluation/characters/T-093/make_overrides.py

Every garment keeps its published `material` entry unchanged (T-092 owns those; T-094 combines field by field).
Values are my estimates, read from the references named per field and tuned by eye on diagnostic renders."""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
CH = os.path.join(ROOT, "assets", "characters")


def load(cid, ver):
    return json.load(open(os.path.join(CH, cid, "spec", f"{cid}.{ver}.spec.json")))


def item(clothing, name):
    return next(g for g in clothing["garments"] if g["name"] == name)


def write(cid, ver, override, note):
    out = os.path.join(CH, cid, "spec", "candidates", "T-093")
    os.makedirs(out, exist_ok=True)
    override.setdefault("metadata", {})["notes"] = note
    path = os.path.join(out, f"{cid}.T-093.override.json")
    json.dump({"override": override}, open(path, "w"), indent=1)
    open(path, "a").write("\n")
    print(path)


def boy():
    spec = load("boy_yellow_hoodie", "2.0.0")
    cl = copy.deepcopy(spec["clothing"])
    cl["generator"] = "garment/2"
    hood = item(cl, "hoodie")
    # B01/B02 (owner decision 2026-11-18): plain felt cords with dark tips (not B08's braided cords with metal tips)
    hood["materials"]["drawstring"] = {"preset": "felt", "base_color_srgb": [226, 210, 184], "reference_size_m": 0.05}
    hood["materials"]["tip"] = {"preset": "felt", "base_color_srgb": [62, 52, 48], "reference_size_m": 0.02}
    tr = item(cl, "trousers")
    # inseam: the gusset hung 70 % of the way to the hem and joined the legs to the knee (Codex: crotch-to-sole gap
    # -31 %); val27 front/side show the legs separate just below the hoodie hem. Break: bunched on the shoe (B09, val27)
    tr["crotch"] = {"type": "gusset", "depth": 0.12}
    tr["length"] = 1.0
    tr["hem_break"] = {"height_m": 0.06, "flare_m": 0.004, "folds": 2, "fold_depth_m": 0.0025, "front_drop_m": 0.008}
    sh = item(cl, "shoes")
    # shoe volume: the shoe mask read 39 % larger than val27; slimmer, lower upper. Cream sole kept; white side
    # stripes (earlier references, B07); B09 only for laces, stitching and toe cap
    sh.update({"height_m": 0.06, "width_extra_m": 0.0015, "length_extra_m": 0.006, "toe_drop": 0.36})
    sh["sole"] = {"thickness_m": 0.014, "wrap_m": 0.007, "margin_m": 0.0015}
    sh["stripes"] = {"count": 2, "width_m": 0.007, "gap_m": 0.005, "slope": 0.75, "centre": -0.12,
                     "z_range": [0.2, 0.95], "side_min": 0.38}
    sh["materials"]["stripe"] = {"preset": "felt", "base_color_srgb": [240, 236, 228], "reference_size_m": 0.05}
    bp = item(cl, "backpack")
    # B06 (canonical): rounded lid flap with a tab closure, a front pocket with its own flap, top grab loop, navy
    # felt; B07 only for depth and strap path. Zips belong to B07's design, so none here.
    bp.update({"width_m": 0.17, "height_m": 0.21, "depth_m": 0.07, "top_drop_m": 0.07, "roundness": 3.8, "puff": 0.5})
    bp["zip"] = False
    bp["pocket"] = {"width": 0.66, "height": 0.34, "depth_m": 0.02, "drop": 0.27}
    bp["handle"] = {"radius_m": 0.0035, "width_m": 0.03}
    bp["flap"] = {"drop": 0.46, "corner": 0.6, "wrap": 0.7, "side_cover": 1.0, "thickness_m": 0.005, "lift_m": 0.0012,
                  "dip_m": 0.006}
    bp["tab"] = {"width_m": 0.013, "length_m": 0.022, "start": 0.3, "thickness_m": 0.0032, "buckle_m": 0.01}
    bp["pocket_flap"] = {"drop": 0.42, "corner": 0.55, "wrap": 0.3, "side_cover": 1.0, "thickness_m": 0.003}
    # navy felt (B06, owner decision 2026-11-18). The ONE `material` entry changed by this task: the bag colour is
    # a design point, not a fabric preset (preset and size unchanged); T-092 does not target the backpack.
    navy = {"preset": "felt", "base_color_srgb": [44, 48, 74], "reference_size_m": 0.2}
    bp["material"] = dict(bp["material"], base_color_srgb=list(navy["base_color_srgb"]))
    for part in ("flap", "tab", "pocket_flap", "pocket", "strap", "handle", "buckle"):
        bp["materials"][part] = dict(navy)
    write("boy_yellow_hoodie", "2.0.0",
          {"generators": {"garment": "garment/2"}, "clothing": cl},
          "T-093 candidate (unpublished): garment/2 outlines and accessories on boy 2.0.0. Never publish or approve "
          "without an owner decision (T-094).")


def girl():
    spec = load("girl_auburn_bun_glasses", "0.11.0")
    cl = copy.deepcopy(spec["clothing"])
    cl["generator"] = "garment/2"
    bl = item(cl, "blouse")
    # sleeve reach (sheet30 front, #41): long puffed sleeves to the wrist; rounded blouse collar (earlier references,
    # owner decision 2026-11-18), broad rounded lobes lying flat over the vest
    bl.update({"sleeve_length": 1.0, "sleeve_puff_m": 0.03, "sleeve_puff_peak": 0.58})
    bl["collar"] = {"type": "round", "width_m": 0.05, "gap_m": 0.012, "slope": 0.3, "tip_round": 0.55, "lift_m": 0.026}
    vest = item(cl, "vest")
    # reach correctives (Codex: the vest flares in reach): the panels near the armhole copy the arm-root weights, so the
    # correction also reaches vertices carried entirely by the arm (arm_hi > 1)
    vest["correctives"] = {"reach": {"deg": -75.0, "strength": 1.0, "arm_lo": 0.4, "arm_hi": 2.0}}
    sh = item(cl, "shorts")
    # split bloomers (#41, G08): two gathered legs, the gusset short and high
    sh["crotch"] = {"type": "gusset", "depth": 0.25}
    sh["puff_inner"] = 0.35
    sh["leg_split"] = {"amount": 0.8, "start": 0.12}
    bt = item(cl, "boots")
    # cream turned-down fleece cuff (G08, #41 boots tile): shape here; the fleece material is T-092's
    bt["cuff_roll"] = {"height_m": 0.032, "thickness_m": 0.009, "inner_m": 0.014, "lumps": 0.2}
    bt["materials"]["cuff"] = {"preset": "boot fleece", "base_color_srgb": [232, 220, 198], "reference_size_m": 0.15,
                               "overrides": {"surface": {"sheen_weight": 0.25}}}
    # hair accessories (G04, ref_30): blue-grey scrunchie with one pink felt flower (groom/2 structure data only)
    hair = copy.deepcopy(spec["hair"])
    for st in hair["structures"]:
        if st["type"] == "tie":
            st.update({"tube": 0.017, "width_scale": 1.45, "radius_scale": 1.1, "height_frac": 0.15})
        if st["type"] == "flowers":
            st["items"] = [{"around_deg": 55, "height_frac": 0.24, "size": 0.05, "out": 0.03}]
    hair["components"]["accessories"] = ["one pink felt flower with a yellow centre",
                                         "blue-grey scrunchie at the bun base"]
    write("girl_auburn_bun_glasses", "0.11.0",
          {"generators": {"garment": "garment/2"}, "clothing": cl, "hair": {"structures": hair["structures"],
                                                                            "components": hair["components"]}},
          "T-093 candidate (unpublished): garment/2 outlines and accessories on girl 0.11.0. Never publish or approve "
          "without an owner decision (T-094).")


boy()
girl()
