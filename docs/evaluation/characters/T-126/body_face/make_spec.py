#!/usr/bin/env python3
"""T-126a: composes the base spec of girl_white_hair_blue_dress 0.1.0 (body, face, eyes) from read-only inputs.

    python3 docs/evaluation/characters/T-126/body_face/make_spec.py

Inputs (never edited): the auburn girl's 0.13.0 spec (face_generic/3 with the round-4 face options, T-113 closed-lid
fit and expression library, body_generic/2, rig), her measurements / landmarks / colour targets
(assets/characters/girl_white_hair_blue_dress/references/), and the T-070 hair draft for her (groom/2 cream felt,
placeholder until T-126b pins groom/4). Every number taken from her references is listed in PROVENANCE below.
Output: assets/characters/girl_white_hair_blue_dress/spec/girl_white_hair_blue_dress.0.1.0.spec.json
"""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
CID = "girl_white_hair_blue_dress"
GIRL = "assets/characters/girl_auburn_bun_glasses/spec/girl_auburn_bun_glasses.0.13.0.spec.json"
HAIR = "docs/evaluation/characters/T-070/candidates/third.hair_v3.json"
DRESS = "docs/evaluation/characters/T-068/candidates/girl.gathered_dress.override.json"
OUT = f"assets/characters/{CID}/spec/{CID}.0.1.0.spec.json"

# --- her measurements (references/measurements.json, landmarks.json; w01 front, ear_width = 315 px) -------------
SCALE = 0.972                      # 03 lineup: her height / girl height (sole to bun top), 1.069 / 1.10 m
EAR_W = 0.277 * 1.069              # 315 px of H = 1138 px -> 0.296 m ear centre to ear centre
EYE_X = 0.421 * EAR_W / 2          # eye_spacing / ear_width 0.421 (girl 0.365): wider set
MOUTH_BELOW = 0.175 * EAR_W        # 0.052 m
CHIN_BELOW = 0.34 * EAR_W          # 0.101 m: longer lower face than the girl (0.301)
NOSE_BELOW = 27 / 315 * EAR_W      # nose 27 px below the iris centres: 0.025 m (small, high button nose)
MOUTH_HALF = 0.121 * EAR_W / 2     # mouth_width / ear_width 0.121: 0.018 m half width
EAR_BELOW = 34 / 315 * EAR_W       # ear centres 34 px below the eye line: 0.032 m


def load(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return json.load(f)


def scale_m(node, s, skip=("chin_taper", "lower_roundness", "lower_depth_roundness", "angle_deg", "finger_curl",
                           "front", "side", "front_eye_width", "voxel", "chin_t")):
    """Multiplies every metre value of body.params by s (dimensionless keys listed in skip stay)."""
    if isinstance(node, dict):
        return {k: (v if k in skip else scale_m(v, s, skip)) for k, v in node.items()}
    if isinstance(node, list):
        return [scale_m(v, s, skip) for v in node]
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return round(node * s, 5)
    return node


def compose():
    girl = load(GIRL)
    spec = copy.deepcopy(girl)
    spec["identity"] = {
        "id": CID,
        "display_name": "Girl with white hair and a blue knit dress",
        "identity_lock": "Changing identity (proportions, face, hair style, outfit colours) requires explicit owner approval",
        "approved_decisions": {
            "modelling_pose": "A-pose",
            "hair": "cream felt: two round top buns, fringe clumps, long separated locks with soft S-waves; dusty-blue felt bow (18_W02 canonical: a bow, not a flower)",
            "neutral_expression": "closed gentle smile (14 e1 neutral soft smile, 02 Neutral)",
            "scale": "0.972 x girl_auburn_bun_glasses (03 lineup, same floor): about 1.07 m sole to bun top",
        },
        "references": f"assets/characters/{CID}/references/reference_index.json",
    }
    spec["proportions"] = {
        "height_m": 1.069,
        "height_note": "sole to bun top (measurements.json scale, 03 lineup; estimate, owner to confirm)",
        "measured": "references/measurements.json",
        "fractions_from_top": {"notch_between_buns": 0.063, "eye_line": 0.282, "mouth": 0.33, "chin": 0.376,
                               "collar_top": 0.404, "waist_seam": 0.533, "fingertips": 0.683, "hem": 0.736,
                               "boot_top": 0.859},
        "face_ratios": {"eye_spacing/ear_width": 0.421, "mouth_below_eyes/ear_width": 0.175,
                        "chin_below_eyes/ear_width": 0.34, "iris_radius/ear_width": 0.075,
                        "mouth_width/ear_width": 0.121, "face_width/ear_width": 0.857},
    }

    # --- body: the girl's body_generic/2 body scaled to her height, then her own differences ----------------------
    body = spec["body"]
    p = scale_m(body["params"], SCALE)
    p["head"]["half_width"] = round(p["head"]["half_width"] * 0.96, 5)       # face_width/ear_width 0.857 x 0.296 m
    p["head"]["lower_half_height"] = round(p["head"]["lower_half_height"] + 0.006, 5)  # chin 0.101 m below the eyes
    p["eyes"]["x"] = round(EYE_X, 5)
    p["arm"]["upper_len"] = round(p["arm"]["upper_len"] * 1.08, 5)            # fingertips at 0.683 H (girl ~0.66)
    p["arm"]["fore_len"] = round(p["arm"]["fore_len"] * 1.08, 5)
    p["leg"]["radii"] = [0.040, 0.033, 0.028]                                  # slim tights legs (w01, 03)
    p["voxel"] = body["params"]["voxel"]
    body["params"] = p
    body["height_m"] = round(body["height_m"] * SCALE, 5)
    body["height_note"] = "sole to top of skull; the buns and hair volume add the rest of the 1.069 m"
    body["hands"] = "hands_r2/1"   # T-121 separated fingers (12 hand anatomy, 13 hands open/fist/pointing)
    body["provenance"] = ("T-126a: the auburn girl's 0.13.0 body_generic/2 body scaled by 0.972 (03 lineup), then: "
                          "head 4 % narrower and lower face 6 mm longer (w01 face ratios), eyes wider set "
                          f"(x {EYE_X:.4f} m), arms 8 % longer (fingertips 0.683 H), slimmer legs (tights, w01/03), "
                          "hands_r2/1. measured_m is the girl's and is not hers.")

    # --- face: face_generic/3 round 4 + T-113 (from 0.13.0), her layout, eyes and colours -------------------------
    f = spec["face"]
    f["provenance"] = ("T-126a: layout from her landmarks.json (w01 front, ear_width 315 px = 0.296 m): mouth "
                       f"{MOUTH_BELOW:.4f}, nose {NOSE_BELOW:.4f}, chin {CHIN_BELOW:.4f} m below the eye line; eye "
                       "and expression style from 01, 02 (face tiles), 04 (expression matrix), 14 (11 expressions, "
                       "10 mouth shapes) and 13 (face tests). Lid/fit options (round 4, T-113 closed_fit, T-115) "
                       "carried from the auburn girl's 0.13.0.")
    f["layout"] = {"mouth_below_eye_m": round(MOUTH_BELOW, 4), "nose_below_eye_m": round(NOSE_BELOW, 4),
                   "chin_below_eye_m": round(CHIN_BELOW, 4), "note": "w01 landmarks (T-126a)"}
    e = f["eyes"]
    e["iris"].update({"srgb": [58, 104, 158], "inner_srgb": [104, 152, 198], "dark_srgb": [24, 42, 74],
                      "limbal_srgb": [12, 20, 38], "glow_srgb": [128, 176, 218], "shade_srgb": [28, 48, 84],
                      "pupil_srgb": [8, 10, 14], "radius": 0.52})
    e["sclera_srgb"] = [244, 241, 236]
    e["note"] = ("T-126a: large round blue eyes (w01 iris (63,95,124) in shade, lighter at the bottom; w10 M_Eye_Glass), "
                 "iris 52 % of the eye radius (iris fills ~3/4 of the visible eye width in w01); lids from 0.13.0")
    lash = e["lash"]
    lash.update({"srgb": [46, 30, 26], "span_deg": 70})
    lash["strands"].update({"count": 5, "to_deg": 66, "outward": 0.45})
    lash["strands"]["note"] = "T-126a: no glasses, so the strands reach the outer corner (01/14 outer lash flick)"
    lash["outer"].update({"count": 3})
    f["brows"].update({"srgb": [196, 170, 146], "thick_m": 0.0019, "inner": 0.6, "outer": 0.92,
                       "note": "T-126a: thin, pale cream-beige brows mostly under the fringe (01, 14)"})
    f["ears"].update({"below_eye_m": round(EAR_BELOW * 0.85, 4)})
    f["nose"].update({"size_m": 0.012, "height_m": 0.005,
                      "note": "T-126a: small round button nose, barely tinted (01, 14 side)"})
    f["blush"].update({"srgb": [234, 146, 128], "below_eye_m": 0.04, "out_m": 0.04, "radius_m": 0.042,
                       "intensity": 0.85, "nose_intensity": 0.3,
                       "note": "T-126a: soft peach-pink felt blush (color_targets cheeks_blush 212,161,139 on the lit side)"})
    m = f["mouth"]
    m.update({"half_width_m": round(MOUTH_HALF, 4), "lip_srgb": [224, 150, 140], "inner_srgb": [168, 72, 64],
              "note": "T-126a: small closed gentle-smile rest (14 e1, 02 Neutral) on the 0.13.0 mouth (rest soft_smile)"})

    # --- hair: placeholder (T-070 groom/2 draft for her) until T-126b pins groom/4 --------------------------------
    hair_c = load(HAIR)["overrides"]
    spec["hair"] = hair_c["hair"]
    spec["generators"]["groom"] = hair_c["generators"]["groom"]

    # --- clothing: placeholder plain knit dress (T-068 type demo, garment/2) until T-126c --------------------------
    dress = load(DRESS)["override"]["clothing"]
    cl = copy.deepcopy(dress)
    cl["generator"] = spec["clothing"]["generator"]
    cl["provenance"] = "T-126a placeholder: T-068 gathered-dress type demonstration with her colours; T-126c replaces it (garment/3)"
    cl["description"] = ["powder-blue knit dress, Peter Pan collar, rib cuffs, flared skirt with rib hem",
                         "cream knit tights (not built yet)", "tan fleece boots with a fold-over cuff"]
    cl["garments"][0]["material"]["base_color_srgb"] = [154, 175, 186]
    boots = cl["garments"][1]
    boots["material"]["base_color_srgb"] = [176, 132, 92]
    boots["materials"]["band"]["base_color_srgb"] = [184, 140, 100]
    spec["clothing"] = cl
    spec["accessories"] = {"generator": "accessories/1", "items": []}

    # --- materials: her targets (color_targets.json); full set is T-126d ----------------------------------------
    ct = load(f"assets/characters/{CID}/references/color_targets.json")
    mat = spec["materials"]
    mat["target_colors_srgb"] = {k: v["srgb"] for k, v in ct.items() if isinstance(v, dict) and "srgb" in v}
    mat["albedo_srgb"] = {"skin": [244, 216, 198]}
    skin = mat["assignments"]["skin"]
    skin["base_color_srgb"] = [244, 216, 198]
    mat["assignments"] = {"skin": skin}
    mat["assignments"].update(hair_c["materials"]["assignments"])

    spec["animation"]["personality"] = {
        "profile": CID, "profile_version": "1.0.0", "path": f"content/personality/{CID}.json",
        "note": "personality profile (scenes opt in with \"personality\": \"" + CID + "\")"}
    spec["animation"]["gaze"] = {
        "legibility": "T-120 gazeLegibility (scene or character key, opt-in); rangeDeg = face.eyes.gaze_range_deg",
        "range_deg": e["gaze_range_deg"]}
    spec["metadata"] = {
        "spec_version": "0.1.0",
        "status": "T-126a base spec: work in progress, not published, not current. Hair (T-126b), dress (T-126c) "
                  "and materials (T-126d) are placeholders that their override files replace.",
        "scope": "body, face and eyes of girl_white_hair_blue_dress on face_generic/3 (round 4 + T-113) and body_generic/2",
        "parent_versions": [],
        "sources": {"face_and_body_base": GIRL, "hair_placeholder": HAIR, "dress_placeholder": DRESS,
                    "measurements": f"assets/characters/{CID}/references/measurements.json",
                    "composed_by": "docs/evaluation/characters/T-126/body_face/make_spec.py"},
        "owner_decisions": ["2026-11-19 ~13:10Z / ~15:20Z: start the third character (T-126)",
                            "2026-11-18: the 18_W02 blue felt bow is canonical"],
        "history": [],
    }
    return spec


if __name__ == "__main__":
    spec = compose()
    out = os.path.join(ROOT, OUT)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(spec, fh, indent=1)
        fh.write("\n")
    print(out)
