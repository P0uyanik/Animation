"""Writes the T-058 sections into the boy 2.0.0-dev spec (kept as a script so iterations are reproducible)."""
import json, sys
P = "assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.2.0.0-dev.spec.json"
s = json.load(open(P))
order = ["schema", "generators", "identity", "proportions", "body", "face", "hair", "clothing", "accessories", "rig",
         "materials", "fur", "animation", "metadata", "components"]
s["generators"] = {"body": "body_generic/1", "face": "face_generic/1", "groom": "hair_clumps/1", "garment": "garment/1",
                   "accessories": "none", "rig": "rigify_human/1", "materials": "presets/1", "exporter": "export/4"}
SKIN = [196, 148, 126]
s["face"] = {
 "generator": "face_generic/1",
 "provenance": "T-058: from char_C (identity authority), #08 face tiles and #28 (three-quarter expression library); "
               "REFERENCE_BEHAVIOUR.md §1-2. Layout from the v6 boy's measured z targets (eye 0.778, nose 0.748, "
               "mouth 0.724, chin 0.698 m). Values are my estimates, tuned against renders.",
 "layout": {"mouth_below_eye_m": 0.056, "nose_below_eye_m": 0.031, "chin_below_eye_m": 0.082},
 "eyes": {
  "radius_m": 0.042, "protrusion_m": 0.006, "spacing_m": 0.136, "offset_z_m": 0.0,
  "scale": [1.0, 1.0, 1.0], "yaw_deg": 0.0, "pitch_deg": 0.0,
  "shader": "layered/1",
  "iris": {"srgb": [92, 60, 40], "inner_srgb": [128, 86, 54], "dark_srgb": [52, 32, 22], "limbal_srgb": [24, 14, 10],
           "glow_srgb": [140, 98, 62], "shade_srgb": [44, 28, 20], "pupil_srgb": [12, 8, 7],
           "radius": 0.64, "pupil": 0.27, "limbal_width": 0.08, "pupil_softness": 0.02, "streaks": 0.2,
           "vertical_gradient": 0.35},
  "sclera_srgb": [238, 232, 226], "sclera_edge_srgb": [212, 198, 192],
  "highlights": [[0.22, 0.12, 0.1], [-0.2, -0.05, 0.045, 0.7]],
  "catchlight_strength": 1.3, "catchlight_softness": 0.3,
  "wet_coat": {"weight": 1.0, "roughness": 0.05, "base_roughness": 0.35},
  "lids": {"upper_edge_deg": 6, "upper_back_tilt": 0.15, "upper_gap": 0.06, "upper_thickness_m": 0.0026,
           "lower_edge_deg": -46, "lower_tilt": 0.3, "lower_gap": 0.03, "lower_thickness_m": 0.0012,
           "upper_curve": -0.05, "lower_curve": 0.05},
  "lash": {"srgb": [30, 20, 18], "span_deg": 66, "thick_m": 0.0026, "depth_m": 0.0016, "flare": 0.5,
           "forward_m": 0.0004, "outer": {"count": 0}},
  "lid_tracking": 0.3,
  "note": "heavy upper lid at rest (char_C, #08, #28 r1c1: the lid line crosses the iris near its middle, nearly "
          "straight): upper_edge_deg 6 with little back tilt; large dark-brown iris; flat to the face"},
 "brows": {"style": "felt", "inner": 0.45, "outer": 0.95, "height": 1.12, "arch_m": 0.0005,
           "inner_drop_m": 0.0015, "outer_drop_m": 0.001, "thick_m": 0.0055, "depth_m": 0.0018, "taper": 0.3,
           "offset_m": 0.0008, "srgb": [52, 34, 28],
           "note": "low, flat, thin dark brows close to the lid line, slight downward slope to the inner end (char_C)"},
 "ears": {"radii_m": [0.014, 0.028, 0.036], "below_eye_m": 0.012, "y_m": 0.008, "out_m": 0.006, "yaw_deg": 22,
          "tilt_deg": -6},
 "nose": {"type": "small_round", "size_m": 0.009, "height_m": 0.0016, "offset_z_m": 0.0},
 "blush": {"srgb": [232, 140, 130], "below_eye_m": 0.034, "out_m": 0.022, "radius_m": 0.032, "nose": False,
           "intensity": 0.85, "softness": 0.8, "breakup": 0.2},
 "mouth": {
  "generator": "lips_jaw/2", "half_width_m": 0.0085, "lip_height_m": 0.0022, "frown_m": 0.0012,
  "smile_up_m": 0.004, "smile_widen": 1.15, "smile_intensity": 1.0, "smile_asymmetry": 0.0,
  "jaw_open_deg": 9.0, "pivot_drop_m": 0.015, "cavity_depth_m": 0.0,
  "cheek_falloff_m": [0.022, 0.045], "jaw_band_start": 0.45, "jaw_corner_center": 1.0, "jaw_floor_fade_m": 0.02,
  "jaw_lip_round": 0.9, "jaw_upper_lift_m": 0.0015,
  "lip_material": "lip", "lip_srgb": [214, 156, 146], "seam_half_m": 0.0006, "line_srgb": [110, 60, 56],
  "line_roughness": 0.9, "lip_edge_offset_m": 0.0002, "lip_bulge_m": 0.0012,
  "interior_rows": 9, "interior_follow_keys": True,
  "inner_srgb": [170, 64, 64], "throat_srgb": [80, 22, 26], "tongue_srgb": [214, 108, 112],
  "oral": {"teeth_upper": {"depth": 0.26, "width": 0.8, "srgb": [240, 235, 226], "forward_m": 0.0003},
           "tongue": {"t0": 0.6, "width": 0.6, "srgb": [214, 108, 112], "bulge_m": 0.0002}},
  "extra_shapes": [{"name": "MouthFrown", "frown_m": 0.0042, "widen": 0.92},
                   {"name": "MouthWide", "frown_m": -0.004, "widen": 1.45, "up_lift_m": 0.003, "lo_drop_m": 0.009},
                   {"name": "MouthO", "frown_m": 0.0, "widen": 0.62, "up_lift_m": 0.0022, "lo_drop_m": 0.0042}],
  "rest_shape": "pout", "rest_mix": {"MouthFrown": 0.45, "MouthPout": 0.55},
  "note": "small sulky pout at rest (char_C, #08 Neutral): tiny mouth, corners slightly down, lower lip forward"},
 "blink": {"generator": "lid_seam/1", "overlap_deg": 3, "closed_offset_m": 0.0012, "closed_thickness_m": 0.0012,
           "flatten": 0.0, "flatten_lash": False,
           "timing": {"close_s": 0.08, "hold_s": 0.05, "open_s": 0.16, "mean_interval_s": 2.5,
                      "note": "WT: 3 blinks in 121 f (REFERENCE_BEHAVIOUR §4)"}},
 "smile_coupling": {"cheek_raise_m": 0.0025, "cheek_forward_m": 0.0012, "cheek_radius_scale": 0.55,
                    "corner_follow": 0.8, "corner_radius_scale": 0.9, "eye_squint_deg": 5.0, "intensity": 1.0,
                    "asymmetry": 0.0},
 "action_units": {"wide_upper_deg": 30, "wide_lower_deg": 6, "squint_lower_deg": 14, "squint_upper_deg": 6,
                  "brow_up_m": 0.007, "brow_down_m": 0.009, "brow_in_m": 0.003, "brow_sad_m": 0.01,
                  "pout_m": 0.0025, "pout_lower": 0.6, "pout_narrow": 0.12,
                  "split": ["BrowDown", "EyeSquint", "MouthSmile", "MouthFrown"], "split_blend_m": 0.006,
                  "note": "T-058 controls the facial layer can drive: BrowUp.L/R, BrowDown(.L/.R), BrowSad, "
                          "MouthSmile(.L/.R) / MouthFrown(.L/.R) = mouth corners up/down, JawOpen + MouthO = mouth "
                          "open, MouthPout, Blink.L/R, EyeSquint(.L/.R), EyeWide. wide_upper 30 deg: from the heavy "
                          "rest lid to fully open round eyes (surprise, #28 r1c4)"},
 "expressions": {
  "intensity": 1.0, "scale": {},
  "override": {
   "Smile": {"Blink.L": 0.85, "Blink.R": 0.85, "EyeSquint": 1.0, "MouthSmile": 0.9, "MouthWide": 0.0,
             "JawOpen": 0.0, "MouthPout": -0.5},
   "Sadness": {"BrowSad": 0.8, "MouthFrown": 0.55, "Blink.L": 0.1, "Blink.R": 0.1},
   "Anger": {"BrowDown": 1.0, "EyeSquint": 0.45, "MouthFrown": 0.45, "MouthPout": 0.35},
   "Surprise": {"EyeWide": 1.0, "BrowUp.L": 0.75, "BrowUp.R": 0.75, "MouthO": 0.85, "JawOpen": 0.15,
                "MouthPout": -0.6}},
  "optional": ["Worried", "Curious"],
  "custom": {
   "Bored": {"Blink.L": 0.32, "Blink.R": 0.3, "BrowDown.R": 0.3, "BrowUp.L": 0.12, "MouthFrown.L": 0.35,
             "MouthPout": 0.35},
   "Skeptical": {"BrowUp.L": 0.5, "BrowDown.R": 0.35, "Blink.R": 0.1, "MouthSmile.L": 0.2, "MouthFrown.R": 0.3}},
  "note": "his expressions stay on top of the heavy rest lid (REFERENCE_BEHAVIOUR §2): Happy = eyes closed as arcs "
          "and a small closed smile (#08 Happy, #28 r1c2); Sad = inner brows up, corners down (#28 r1c3); Angry = "
          "brows down, flat pout (#28 r2c1); Surprised = round open eyes, small o (#28 r1c4); Bored = lids lower, "
          "one brow down, mouth pulled to one side (#28 r3c3 'Colfited', subtle per the owner decision)"},
 "expression_shape_keys": [],
 "expressions_reference": "#08 face tiles (Neutral, Happy, Sad, Surprised, Angry), #28 16-tile library",
 "skin": {"occlusion": {"distance_m": 0.15, "lift": 1.6, "warm_srgb": [252, 212, 192], "samples": 32, "bleed": 0.72,
                        "bleed_srgb": [255, 240, 232], "bleed_face_radius_m": 0.12, "bleed_body": 0.15}}}
s["hair"] = {"generator": "hair_clumps/1", "seed": 11, "params": {},
             "ellipsoid_centre_m": [0.0, 0.02, 0.88], "ellipsoid_radii_m": [0.176, 0.182, 0.168],
             "note": "T-058: the boy's current hair kept (hair_clumps/1, the v6/1.x layout, pinned); its ellipsoid is "
                     "the 1.x spec's hair_ellipsoid. Hair v3 (T-044) replaces it after owner approval."}
YEL = [204, 152, 62]
s["clothing"] = {
 "generator": "garment/1",
 "provenance": "T-058: char_C, #08 turnaround and clothing breakdown: mustard-yellow fleece hoodie (hood down, "
               "kangaroo pocket, cream drawstrings, ribbed cuffs and hem, loose), charcoal-black fleece joggers (loose, "
               "bunched at the ankle), yellow suede sneakers with cream soles and toe caps.",
 "hide_body_faces": True, "mask_margin_m": 0.015,
 "collision": {"enabled": True, "offset_m": 0.002, "radius_m": 0.08, "falloff_m": 0.02, "passes": 3},
 "max_influences": 4,
 "defaults": {"thickness_m": 0.0025, "ease_m": 0.012, "seam_radius_m": 0.0016},
 "garments": [
  {"type": "hoodie", "name": "hoodie", "ease_m": 0.02, "sleeve_length": 0.98, "sleeve_puff_m": 0.012,
   "sleeve_puff_peak": 0.55, "hem_z_m": 0.33,
   "bands": {"hem": True, "cuff": True, "rib_ridges": 3, "cuff_rib_ridges": 3, "cuff_radius_m": 0.0045},
   "shoulder_width": 1.0, "dropped_shoulder": {"start": 0.0, "margin_m": 0.04},
   "hood": {"rim_radius_m": 0.021, "rim_rise_m": 0.05, "rim_lift_m": 0.038, "bag_height_m": 0.1, "bag_drop_m": 0.035, "bag_depth_m": 0.024, "v_depth_m": 0.07},
   "pocket": {"width_bottom_m": 0.1, "width_top_m": 0.072, "height_m": 0.115, "above_hem_m": 0.02, "depth_m": 0.016, "rim_radius_m": 0.0045},
   "drawstrings": {"spacing_m": 0.02, "length_m": 0.1, "radius_m": 0.0034, "tip_length_m": 0.011, "tip_radius_m": 0.0042},
   "material": {"preset": "fleece", "base_color_srgb": YEL, "reference_size_m": 0.3},
   "materials": {"drawstring": {"preset": "cotton knit", "base_color_srgb": [222, 206, 182], "reference_size_m": 0.05},
                 "tip": {"preset": "buttons/plastic", "base_color_srgb": [204, 190, 168], "reference_size_m": 0.02}},
   "edge_finish": "rounded"},
  {"type": "trousers", "name": "trousers", "length": 0.97, "ease_m": 0.016, "puff_m": 0.006, "puff_inner": 0.6,
   "waist_z_m": 0.4, "cuff": False, "bands": {"waist": False, "cuff": False},
   "crotch": {"type": "gusset", "depth": 0.7},
   "material": {"preset": "fleece", "base_color_srgb": [38, 34, 34], "reference_size_m": 0.3},
   "edge_finish": "rounded"},
  {"type": "shoes", "name": "shoes", "height": 0.16, "ease_m": 0.014, "toe_volume_m": 0.012,
   "sole": {"thickness_m": 0.012, "width_m": 0.004},
   "bands": {"cuff": False},
   "material": {"preset": "felt", "base_color_srgb": [206, 156, 70], "reference_size_m": 0.15},
   "materials": {"sole": {"preset": "felt", "base_color_srgb": [232, 222, 206], "reference_size_m": 0.15},
                 "band": {"preset": "felt", "base_color_srgb": [232, 222, 206], "reference_size_m": 0.15}},
   "edge_finish": "rounded"}]}
s["accessories"] = {"generator": "none", "items": [],
                    "note": "backpack (char_C, #08) not built: no shared backpack accessory yet"}
s["fur"] = []
s["materials"] = {
 "albedo_srgb": {"skin": SKIN},
 "target_colors_srgb": {"hair": [48, 39, 35], "skin": [193, 144, 122], "hoodie": [192, 145, 80],
                        "trousers": [40, 33, 32], "shoe_yellow": [185, 138, 77], "cream": [210, 197, 188]},
 "assignments": {"skin": {"preset": "skin-felt", "base_color_srgb": SKIN, "reference_size_m": 0.32},
                 "hair": {"preset": "felt hair", "base_color_srgb": [30, 25, 24], "reference_size_m": 0.32}}}
s["components"] = {"body": ["body_skin", "hand."], "face": ["eye.", "lid_", "lash.", "brow.", "mouth", "ear."],
                   "rig": ["rig_"], "landmarks": ["LM_"], "hair": ["hair", "hair_"], "clothing": ["garment."]}
s["rig"].setdefault("weight_rules", {"skin": {"deny_prefixes": ["DEF-f_", "DEF-thumb", "DEF-palm", "DEF-eye"]},
                                     "hand": {"sided": True, "allow_prefixes": ["DEF-forearm", "DEF-hand", "DEF-f_",
                                                                                "DEF-thumb", "DEF-palm"]}})
s["metadata"] = {"spec_version": "2.0.0-dev", "status": "unpublished",
                 "scope": "T-039 body + T-058 face (brow/mouth controls), hoodie, trousers, shoes; pinned 1.x hair; "
                          "no backpack, no fur",
                 "parent_versions": ["1.0.0", "1.1.0"], "approval": None}
out = {k: s[k] for k in order if k in s}
out.update({k: v for k, v in s.items() if k not in out})
json.dump(out, open(P, "w"), indent=1)
open(P, "a").write("\n")
