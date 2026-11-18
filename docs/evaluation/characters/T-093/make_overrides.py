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
    # round 2 (owner: "still reads as the old rounded pouch"): a boxy, flat-fronted bag (roundness, little puff), a
    # thick flap with a piped edge, a ring closure on the tab, a rectangular front pocket with its own piped flap
    bp.update({"width_m": 0.175, "height_m": 0.22, "depth_m": 0.068, "top_drop_m": 0.07, "roundness": 5.5,
               "puff": 0.15})
    bp["zip"] = False
    bp["pocket"] = {"width": 0.64, "height": 0.33, "depth_m": 0.022, "drop": 0.28}
    bp["handle"] = {"radius_m": 0.004, "width_m": 0.034}
    bp["flap"] = {"drop": 0.5, "corner": 0.45, "wrap": 0.75, "side_cover": 1.0, "thickness_m": 0.006, "lift_m": 0.003,
                  "dip_m": 0.004, "edge_m": 0.0026}
    bp["tab"] = {"width_m": 0.014, "length_m": 0.03, "start": 0.3, "thickness_m": 0.0035, "buckle_m": 0.015,
                 "buckle": "ring"}
    bp["pocket_flap"] = {"drop": 0.45, "corner": 0.45, "wrap": 0.3, "side_cover": 1.0, "thickness_m": 0.0045,
                         "lift_m": 0.002, "edge_m": 0.002}
    bp["clean_fibres"] = ["flap_edge", "pocket_flap_edge", "tab", "buckle"]  # crisp piping and closure
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
    bl["collar"] = {"type": "round", "width_m": 0.048, "gap_m": 0.012, "slope": 0.5, "tip_round": 0.55, "lift_m": 0.034}
    # round 2 (owner: collar and vest edges cleanly finished, no fringe): no fibres on the collar, the collar lifted
    # off the vest (its surface and fibres no longer show through); the blouse keeps its panel under the sleeve
    # top (closed armhole), so no skin shows at the vest's armholes
    bl["clean_fibres"] = ["collar"]
    bl["collar_clear"] = {"over": ["vest"], "gap_m": 0.008, "smooth": 20, "max_lift_m": 0.02}
    bl["armhole"] = "closed"
    bl["sleeve_start"] = 0.0  # the sleeve covers the shoulder cap (skin showed between the vest and the sleeve)
    vest = item(cl, "vest")
    # reach correctives (Codex: the vest flares in reach): the panels near the armhole copy the arm-root weights, so the
    # correction also reaches vertices carried entirely by the arm (arm_hi > 1)
    # round 2 (owner: further reduce the vest in reach): the vest is no longer carried by the arm (arm-weight cap:
    # this alone removes the flare), and the reach keys keep the vest outside the posed blouse sleeve at the shoulder
    # (layer order; strength 0 = no extra pull towards the torso, which only fought the collision once capped)
    vest["correctives"] = {"arm_weights": {"cap": 0.2},
                           "reach": {"deg": -75.0, "strength": 0.0, "over": ["blouse"], "over_gap_m": 0.003}}
    vest["clean_fibres"] = ["edge", "pocket_edge"]
    vest["shoulder_width"] = 0.9  # a little more blouse at the shoulders (sheet30, #41)
    sh = item(cl, "shorts")
    # split bloomers (#41, G08): two gathered legs, the gusset short and high
    sh["crotch"] = {"type": "gusset", "depth": 0.25}
    sh["puff_inner"] = 0.35
    sh["leg_split"] = {"amount": 0.8, "start": 0.12}
    # gathered cuffs (G08, #41): vertical gathers puff above the cuff band
    sh["hem_break"] = {"height_m": 0.045, "flare_m": 0.0, "folds": 0, "fold_depth_m": 0.0, "front_drop_m": 0.0,
                       "pleats": 18, "pleat_depth_m": 0.0035}
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
