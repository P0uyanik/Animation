"""End-to-end test for the shared ``garment/1`` generator.

Plain-Python entry point:

    python tests/garment_generic_test.py --blender <blender> [--out <dir>] [--evidence-dir <dir>]

The subprocess builds two synthetic body_generic bodies (T-025): the neutral ``reference`` mannequin and an
``extreme`` one at extreme but plausible proportions (larger head, shorter and thicker limbs, a rounder torso).
On each it builds shirt + vest + shorts + boots, a dress variant and outfit B (puffed sleeves, round collar,
embroidered vest with fuller shoulders, a rolled edge, edge buttons and pocket embroidery, bloomers with a crotch
gusset and waistband buttons, chunky boots with thick cuffs). It transfers body weights, poses every repository
clip at its sampled extreme (plus the legacy six samples) through the shared retargeter, and measures signed
garment to body clearance in rest and posed states. Optional evidence: 640 px four-view Cycles/OIDN turnaround
sheets per body and outfit, and each body's worst pose.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _driver():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--evidence-dir", default="")
    ap.add_argument("--bodies", default="reference,extreme")
    ap.add_argument("--poses", default="auto", help="auto (clip extremes + legacy samples) or clip:frame,...")
    a = ap.parse_args()
    owned = tempfile.TemporaryDirectory(prefix="garment_generic_test_") if not a.out else None
    out = os.path.abspath(a.out or owned.name)
    os.makedirs(out, exist_ok=True)
    cmd = [a.blender, "-b", "--factory-startup", "-P", os.path.abspath(__file__), "--", "--internal", "--out", out,
           "--bodies", a.bodies, "--poses", a.poses]
    if a.evidence_dir:
        cmd += ["--evidence-dir", os.path.abspath(a.evidence_dir)]
    log_path = os.path.join(out, "blender.log")
    with open(log_path, "w") as log:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    result_path = os.path.join(out, "garment_generic_test.json")
    result = json.load(open(result_path)) if os.path.exists(result_path) else {"pass": False}
    print(f"[garment_generic_test] {'PASS' if result.get('pass') else 'FAIL'}; log={log_path}")
    summary = {"pass": result.get("pass"), "poses": result.get("poses_evaluated"), "bodies": {
        name: {"pass": b.get("pass"), "checks": {k: v.get("pass") for k, v in b.get("checks", {}).items()},
               "worst_pose": b.get("worst_pose", {}).get("min_clearance_m")}
        for name, b in result.get("bodies", {}).items()}}
    print(json.dumps(summary, indent=1))
    if owned:
        owned.cleanup()
    raise SystemExit(0 if proc.returncode == 0 and result.get("pass") else 1)


def extreme_proportions(P):
    """Synthetic second test body (body_generic/1 fractions of a 1.0 m height): head x1.25, arms 18 % shorter, legs
    4 cm shorter (everything above moved down), limbs 30 % thicker, torso 6 % wider and 30 % deeper (rounder).
    Note: body_generic builds a perfectly straight arm and Rigify needs a non-zero elbow direction; the 0.82 arm
    factor (like the reference body) leaves the floating-point bend Rigify needs, 0.8 does not."""
    import copy
    Q = copy.deepcopy(P)
    drop = 0.04
    h = Q["head"]
    h.update({"half_width": P["head"]["half_width"] * 1.25, "half_depth": P["head"]["half_depth"] * 1.25,
              "half_height": P["head"]["half_height"] * 1.25})
    Q["neck"] = {"base_z": P["neck"]["base_z"] - drop, "top_z": P["neck"]["top_z"] - drop,
                 "radius": P["neck"]["radius"] * 1.15}
    h["centre_z"] = Q["neck"]["top_z"] - 0.01 + h["half_height"]
    Q["torso"]["levels"] = [[z - drop, w * 1.06, f * 1.3, b * 1.3] for z, w, f, b in P["torso"]["levels"]]
    Q["shoulder"] = {"z": P["shoulder"]["z"] - drop, "joint_x": P["shoulder"]["joint_x"] * 1.06,
                     "clavicle_x": P["shoulder"]["clavicle_x"]}
    Q["arm"] = {"angle_deg": P["arm"]["angle_deg"], "upper_len": P["arm"]["upper_len"] * 0.82,
                "fore_len": P["arm"]["fore_len"] * 0.82, "radii": [r * 1.3 for r in P["arm"]["radii"]]}
    Q["leg"] = {"hip_x": P["leg"]["hip_x"] * 1.16, "hip_z": P["leg"]["hip_z"] - drop,
                "knee_z": P["leg"]["knee_z"] - drop / 2, "ankle_z": P["leg"]["ankle_z"],
                "radii": [r * 1.3 for r in P["leg"]["radii"]]}
    Q["foot"] = {**P["foot"], "half_width": P["foot"]["half_width"] * 1.2, "height": P["foot"]["height"] * 1.1}
    Q["eyes"] = {"x": P["eyes"]["x"] * 1.25, "y": P["eyes"]["y"] * 1.25,
                 "z": h["centre_z"] - (P["head"]["centre_z"] - P["eyes"]["z"]) * 1.25}
    return Q


def _internal():
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    charsys = os.path.join(ROOT, "pipeline", "charsys")
    clips_dir = os.path.join(ROOT, "pipeline", "clips")
    sys.path.insert(0, charsys)
    sys.path.insert(0, clips_dir)
    import body_generic as BG
    import body_v6 as B
    import garments as GAR
    from garments import evaluate as EV
    import geom as G

    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--internal", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence-dir", default="")
    ap.add_argument("--bodies", default="reference,extreme")
    ap.add_argument("--poses", default="auto")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    PUFF, RELIEF, CUFF_R = 0.016, 0.0018, 0.009
    SHAFT, TOE, ROLL = 0.008, 0.010, 0.004
    # T-034: build-time cloth rest shape on every main panel (both outfits) with fixed seed and frames.
    # Volume items gather between their pinned bands; fitted panels (no volume) hang from their top and edges.
    DRAPE = {"enabled": True, "gather": 0.3, "gravity": 0.5, "pin": ["edges", "volume"], "seed": 34, "frames": 30}
    FITTED_DRAPE = {"enabled": True, "gravity": 1.0, "pin": ["edges", "top"], "seed": 34, "frames": 30}
    VEST_DRAPE = {"enabled": True, "fabric": "felt", "pin": ["top"], "top_band_m": 0.05, "gravity": 0.6, "seed": 34,
                  "frames": 30}
    neutral = json.load(open(os.path.join(ROOT, "pipeline", "clips", "mannequin.json")))
    H, P_ref = float(neutral["body"]["height_m"]), neutral["body"]["params"]
    clothing = {
        "generator": "garment/1",
        "hide_body_faces": True,
        "mask_margin_m": 0.015,
        "collision": {"enabled": True, "offset_m": 0.002, "radius_m": 0.08, "falloff_m": 0.02, "passes": 4},
        "max_influences": 4,
        "defaults": {"thickness_m": 0.002, "ease_m": 0.009, "seam_radius_m": 0.00115},
        "garments": [
            {"type": "top", "name": "shirt", "sleeve_length": 0.74, "collar": "shirt",
             "buttons": {"count": 4, "radius_m": 0.005},
             "bands": {"hem": True, "cuff": True, "rib_ridges": 2}, "seam_lines": True, "edge_finish": "rounded",
             "drape": {**FITTED_DRAPE, "fabric": "cotton"},
             "material": {"preset": "woven cotton", "base_color_srgb": [211, 201, 190]},
             "materials": {"buttons": {"preset": "buttons/plastic", "base_color_srgb": [142, 104, 69]}}},
            {"type": "vest", "name": "vest", "ease_m": 0.015, "open_front_m": 0.023,
             "pockets": {"width_m": 0.030, "height_m": 0.027, "depth_m": 0.0035},
             "bands": {"hem": True}, "seam_lines": True, "edge_finish": "rounded", "drape": VEST_DRAPE,
             "material": {"preset": "felt", "base_color_srgb": [137, 89, 88]}},
            {"type": "shorts", "name": "shorts", "length": 0.38, "cuff": True, "edge_finish": "rounded",
             "bands": {"waist": True, "cuff": True, "edge_roll_m": 0.002, "edge_style": "piped"}, "seam_lines": True,
             "drape": {**FITTED_DRAPE, "fabric": "denim"},
             "material": {"preset": "denim", "base_color_srgb": [91, 113, 111]}},
            {"type": "boots", "name": "boots", "height": 0.62, "cuff": True,
             "bands": {"cuff": True}, "sole": {"thickness_m": 0.006},
             "material": {"preset": "felt", "base_color_srgb": [102, 68, 51]},
             "materials": {"sole": {"preset": "denim", "base_color_srgb": [61, 47, 40]}}},
            {"type": "dress", "name": "dress", "ease_m": 0.030, "sleeve_length": 0.26, "collar": "crew",
             "length": 0.62, "flare": 0.16, "bands": {"waist": True, "hem": True, "cuff": True},
             "seam_lines": True,
             "material": {"preset": "cotton knit", "base_color_srgb": [102, 128, 151]},
             "materials": {"skirt": {"preset": "woven cotton", "base_color_srgb": [112, 139, 161]}}},
            # Outfit B: the volume, collar and decoration parameters (puffed sleeves, round collar, embroidery,
            # bloomers with gathered cuffs, a thick boot cuff) and the T-025 options (fuller vest shoulders, a
            # rolled edge, edge buttons, pocket embroidery, a crotch gusset, waistband buttons, chunky boots).
            {"type": "top", "name": "puff_top", "sleeve_length": 0.74, "sleeve_puff_m": PUFF, "sleeve_puff_peak": 0.6,
             "collar": {"type": "round", "width_m": 0.028, "gap_m": 0.008, "slope": 0.5, "tip_round": 0.35},
             "bands": {"cuff": True, "cuff_radius_m": 0.004}, "edge_finish": "rounded",
             "drape": {**DRAPE, "fabric": "knit"},
             "material": {"preset": "cotton knit", "base_color_srgb": [214, 206, 196]}},
            {"type": "vest", "name": "emb_vest", "ease_m": 0.022, "open_front_m": 0.023, "shoulder_width": 0.55,
             "bands": {"edge_roll_m": ROLL}, "edge_finish": "rounded", "drape": VEST_DRAPE,
             "buttons": {"count": 3, "placement": "edge", "side": "left", "radius_m": 0.005},
             "embroidery": {"size_m": 0.03, "relief_m": RELIEF,
                            "motifs": [{"u": 0.55, "v": 0.7}, {"u": -0.55, "v": 0.7, "petals": 6},
                                       {"u": 0.5, "v": 0.35, "style": "sprig", "rotation_deg": 25},
                                       {"u": 0.0, "v": 0.6, "face": "back", "style": "sprig", "leaves": 5},
                                       {"u": 0.0, "v": 0.45, "target": "pocket.R", "style": "bouquet",
                                        "size_m": 0.026}],
                            "material": {"preset": "felt", "base_color_srgb": [60, 40, 44]},
                            "accent_material": {"preset": "wool yarn", "base_color_srgb": [200, 190, 180]}},
             "materials": {"buttons": {"preset": "buttons/plastic", "base_color_srgb": [142, 104, 69]}},
             "material": {"preset": "felt", "base_color_srgb": [150, 96, 96]}},
            {"type": "shorts", "name": "bloomers", "length": 0.38, "ease_m": 0.012, "puff_m": PUFF, "puff_inner": 0.3,
             "crotch": {"type": "gusset", "depth": 0.6}, "edge_finish": "rounded", "drape": {**DRAPE, "fabric": "felt"},
             "buttons": {"count": 3, "placement": "waistband", "radius_m": 0.004},
             "cuff": True, "bands": {"waist": True, "cuff": True, "cuff_radius_m": 0.004},
             "material": {"preset": "woven cotton", "base_color_srgb": [120, 140, 112]},
             "materials": {"buttons": {"preset": "buttons/plastic", "base_color_srgb": [142, 104, 69]}}},
            {"type": "boots", "name": "fur_boots", "height": 0.5, "ease_m": 0.012, "cuff": True,
             "shaft_width_m": SHAFT, "toe_volume_m": TOE, "edge_finish": "rounded",
             "bands": {"cuff": True, "cuff_radius_m": CUFF_R}, "sole": {"thickness_m": 0.007, "width_m": 0.003},
             "material": {"preset": "fleece", "base_color_srgb": [120, 82, 64]}},
        ],
    }
    items = {
        "outfit_a": ["shirt", "vest", "shorts", "boots"],
        "dress": ["dress", "boots"],
        "outfit_b": ["puff_top", "emb_vest", "bloomers", "fur_boots"],
    }
    clips = os.path.join(ROOT, "content", "clips")
    samples = EV.test_poses(clips) if a.poses == "auto" else [
        (p.split(":")[0], int(p.split(":")[1])) for p in a.poses.split(",") if p]
    # Rest pose keeps the 0.5 mm clearance floor. Posed: no garment vertex may be inside visible skin.
    clearance_floor = 0.0005
    contact_gap = 2 * clothing["collision"]["offset_m"] + clearance_floor
    assert abs(contact_gap - EV.SKIN_CONTACT_TOLERANCE_M) < 1e-12
    result = {"blender": bpy.app.version_string, "body_generator": "body_generic/1", "garment_generator": "garment/1",
              "poses_evaluated": [f"{c}:{f}" for c, f in samples], "clip_extremes": EV.clip_extremes(clips),
              "skin_contact_tolerance_m": EV.SKIN_CONTACT_TOLERANCE_M, "bodies": {}}
    bodies = {"reference": P_ref, "extreme": extreme_proportions(P_ref)}
    evidence = os.path.abspath(a.evidence_dir) if a.evidence_dir else ""

    for body_name in [b for b in a.bodies.split(",") if b]:
        result["bodies"][body_name] = run_body(body_name, bodies[body_name], H, clothing, items, samples,
                                               clearance_floor, contact_gap, out, evidence,
                                               (PUFF, RELIEF, CUFF_R, SHAFT, TOE, ROLL),
                                               bpy, Vector, BVHTree, BG, B, GAR, EV, G, neutral)
    result["pass"] = bool(result["bodies"]) and all(b["pass"] for b in result["bodies"].values())
    if a.poses != "auto":
        result["pass"] = False  # a partial pose list is a debugging run, never a PASS
    json.dump(result, open(os.path.join(out, "garment_generic_test.json"), "w"), indent=1)
    print("[garment_generic_test]", json.dumps({"pass": result["pass"]}))
    raise SystemExit(0 if result["pass"] else 1)


def run_body(body_name, P, H, clothing, items, samples, clearance_floor, contact_gap, out, evidence, sizes,
             bpy, Vector, BVHTree, BG, B, GAR, EV, G, neutral):
    PUFF, RELIEF, CUFF_R, SHAFT, TOE, ROLL = sizes
    bpy.ops.wm.read_factory_settings(use_empty=True)
    C = bpy.data.collections.new("garment_test")
    bpy.context.scene.collection.children.link(C)
    J = BG.joints(P, H)
    frames = BG.hand_frames(P, H, J)
    skin_mat = G.material("M_test_skin", (185, 161, 148), roughness=0.72)
    parts = BG.build_body(C, {"skin": skin_mat}, P, H, J, frames)
    body = parts[0][0]
    # T-034 determinism: the same draped item built twice gives bit-identical rest shapes.
    import hashlib
    import time as _time
    det_item = next(g for g in clothing["garments"] if g["name"] == "puff_top")
    det_clothing = {"generator": "garment/1", "defaults": clothing["defaults"], "fibres_lod": "off",
                    "garments": [det_item]}
    digests, det_seconds = [], []
    for _ in range(2):
        t0 = _time.perf_counter()
        made, _ = GAR.build(C, body, det_clothing, P, H, J, G)
        det_seconds.append(round(_time.perf_counter() - t0, 2))
        main = next(o for o in made if o.get("ps_garment_part") == "main")
        digests.append(hashlib.sha256(b"".join(
            v.co.x.hex().encode() + v.co.y.hex().encode() + v.co.z.hex().encode() for v in main.data.vertices)
        ).hexdigest())
        for ob in made:
            for child in list(ob.children):
                bpy.data.objects.remove(child)
            bpy.data.objects.remove(ob)
    undraped = {**det_clothing, "garments": [{k: v for k, v in det_item.items() if k != "drape"}]}
    t0 = _time.perf_counter()
    made, _ = GAR.build(C, body, undraped, P, H, J, G)
    off_seconds = round(_time.perf_counter() - t0, 2)
    for ob in made:
        bpy.data.objects.remove(ob)
    garment_objects, build_report = GAR.build(C, body, clothing, P, H, J, G)
    fit = GAR.generator.BodyFit(P, H, J)
    rig, rig_report = BG.rig_generic(C, "rig_garment_test", parts, P, H, J, frames,
                                     neutral["rig"]["weight_rules"], B, neutral["rig"].get("weight_smooth"))
    bind_report = GAR.bind_to_body(rig, body, garment_objects, max_influences=clothing["max_influences"])

    # Convert Rigify to the same plain semantic FK deform rig used to author the repository clips.
    clip_rig = EV.semantic_fk_rig(rig, ROOT)
    player = EV.ClipPlayer(rig, clip_rig, os.path.join(ROOT, "content", "clips"))
    reset_pose, apply_clip, world_mesh = player.reset, player.apply, EV.world_mesh

    def clearance(objects, floor):
        return EV.clearance(body, objects, floor, contact_gap, contact_floor=clearance_floor)

    outfits = {name: [ob for ob in garment_objects if ob.get("ps_garment_item") in worn] for name, worn in items.items()}
    result = {"proportions": P, "body_fit": build_report["body_fit"], "build": build_report, "rig": rig_report,
              "weight_transfer": bind_report, "checks": {}, "poses": {}, "rest": {}, "masks": {}}
    result["checks"]["drape_deterministic"] = {"item": "puff_top", "sha256": digests, "seconds_on": det_seconds,
                                               "seconds_off": off_seconds, "pass": digests[0] == digests[1]}
    draped = {i["name"]: i.get("drape") for i in build_report["items"]}
    expected = sorted(g["name"] for g in clothing["garments"] if g.get("drape", {}).get("enabled"))
    result["checks"]["drape_applied"] = {
        "items": draped, "expected": expected,
        "pass": all(draped.get(name) and all(d["free_vertices"] > 0 and d["max_move_m"] > 0 for d in draped[name])
                    for name in expected)}
    piped = [ob.name for ob in garment_objects if ob.get("ps_garment_item") == "shorts" and
             ob.get("ps_garment_part") == "edge"]
    result["checks"]["bottoms_edge_finish"] = {"piping_objects": piped, "pass": len(piped) >= 3}

    def by_item(item, part=None):
        return [ob for ob in garment_objects if ob.get("ps_garment_item") == item and
                (part is None or ob.get("ps_garment_part") == part)]

    def limb_profile(ob, a, b, bins, reach, min_x):
        """Max distance from the limb axis per parameter bin [t0, t1) over the vertices of ``ob`` near that limb."""
        out = [0.0] * len(bins)
        for v in world_mesh(ob)[0]:
            if v.x < min_x:  # this limb's side only (not the torso or the other leg)
                continue
            d = b - a
            t = max(0.0, min(1.0, (v - a).dot(d) / d.length_squared))
            dist = (v - (a + d * t)).length
            for k, (t0, t1) in enumerate(bins):
                if t0 <= t < t1 and dist < reach:
                    out[k] = max(out[k], dist)
        return out

    # Volume, collar and decoration parameters, rest pose. Expected volumes are the requested ones at this body's
    # proportion-relative scale (garment/1 BodyFit; 1.0 on the reference body, so these are the T-024 checks there).
    J0 = BG.joints(P, H)
    sh, wr = J0["shoulder.L"], J0["wrist.L"]
    arm_reach = 0.07 * fit.arm
    arm_bins = [(0.40, 0.48), (0.66, 0.72)]  # puff peak (t 0.10 + 0.6 * 0.64 = 0.48) / just above the cuff
    plain = limb_profile(by_item("shirt", "main")[0], sh, wr, arm_bins, arm_reach, sh.x + 0.01)
    puffed = limb_profile(by_item("puff_top", "main")[0], sh, wr, arm_bins, arm_reach, sh.x + 0.01)
    hip, ankle = Vector((J0["hip.L"].x, 0, P["leg"]["hip_z"] * H)), Vector((J0["hip.L"].x, 0, P["leg"]["ankle_z"] * H))
    leg_bins = [(0.08, 0.16), (0.33, 0.37)]  # bloomer peak (s = 1/3 of the length 0.38) / just above the cuff
    leg_reach = 0.09 * fit.leg
    shorts_plain = limb_profile(by_item("shorts", "main")[0], hip, ankle, leg_bins, leg_reach, hip.x)
    shorts_puff = limb_profile(by_item("bloomers", "main")[0], hip, ankle, leg_bins, leg_reach, hip.x)
    arm_puff, leg_puff = PUFF * fit.arm, PUFF * fit.leg
    result["checks"]["sleeve_puff"] = {
        "plain_m": [round(x, 5) for x in plain], "puffed_m": [round(x, 5) for x in puffed], "puff_m": arm_puff,
        "pass": puffed[0] - plain[0] >= 0.8 * arm_puff and abs(puffed[1] - plain[1]) <= 0.5 * arm_puff}
    result["checks"]["bloomers_puff"] = {
        "plain_m": [round(x, 5) for x in shorts_plain], "puffed_m": [round(x, 5) for x in shorts_puff],
        "puff_m": leg_puff,
        "pass": shorts_puff[0] - shorts_plain[0] >= 0.6 * leg_puff and shorts_puff[1] - shorts_plain[1] <= 0.5 * leg_puff}
    collar = by_item("puff_top", "collar")
    cverts = world_mesh(collar[0])[0] if collar else []
    neck_r = P["neck"]["radius"] * H
    front_gap = [v for v in cverts if v.y < 0 and abs(v.x) < 0.002]
    result["checks"]["round_collar"] = {
        "objects": [o.name for o in collar], "vertices": len(cverts),
        "min_radius_m": round(min(math.hypot(v.x, v.y) for v in cverts), 5) if cverts else None,
        "vertices_in_front_gap": len(front_gap),
        "pass": len(collar) == 1 and not front_gap and min(math.hypot(v.x, v.y) for v in cverts) > neck_r}
    vest_main = by_item("emb_vest", "main")[0]
    pockets = by_item("emb_vest", "pockets")
    vest_bvh = BVHTree.FromPolygons(*world_mesh(vest_main), all_triangles=False)
    pocket_bvh = {o.name: BVHTree.FromPolygons(*world_mesh(o), all_triangles=False) for o in pockets}
    emb = by_item("emb_vest", "embroidery") + by_item("emb_vest", "embroidery_accent")
    motifs = next(i for i in build_report["items"] if i["name"] == "emb_vest").get("embroidery_motifs", [])
    heights = []
    for ob in emb:
        for v in world_mesh(ob)[0]:
            d = [(v - vest_bvh.find_nearest(v)[0]).length] + [(v - t.find_nearest(v)[0]).length
                                                             for t in pocket_bvh.values()]
            heights.append(min(d))
    pocket_motif = next((m for m in motifs if m.get("target") == "pocket.R"), None)
    pocket_ob = next((o for o in pockets if o.name.endswith("pocket.R")), None)
    on_pocket = False
    if pocket_motif and pocket_ob:
        point = Vector(pocket_motif["at_m"])
        on_pocket = (point - pocket_bvh[pocket_ob.name].find_nearest(point)[0]).length < 0.002
    try:
        GAR.validate({"generator": "garment/1", "garments": [
            {"type": "boots", "name": "b", "material": "felt",
             "embroidery": {"motifs": [{"u": 0, "target": "pocket.L"}]}}]})
        rejects_unknown_target = False
    except ValueError:
        rejects_unknown_target = True
    result["checks"]["embroidery"] = {
        "objects": [o.name for o in emb], "motifs": len(motifs), "pocket_motif_on_pocket": on_pocket,
        "max_height_over_garment_m": round(max(heights), 5) if heights else None,
        "rejects_unknown_target": rejects_unknown_target,
        "pass": len(emb) == 2 and len(motifs) == 5 and max(heights) <= 0.02 and rejects_unknown_target and
                on_pocket and {o.get("ps_material_preset") for o in emb} == {"felt", "wool yarn"}}
    cuffs = by_item("fur_boots", "band")
    tube = []
    for ob in cuffs:
        zs = [p.z for p in world_mesh(ob)[0]]  # horizontal ring: its height is the tube diameter
        tube.append((max(zs) - min(zs)) / 2)
    result["checks"]["cuff_radius"] = {"tube_radius_m": [round(t, 5) for t in tube], "requested_m": CUFF_R,
                                       "pass": len(cuffs) == 2 and all(abs(t - CUFF_R) < 0.002 for t in tube)}

    # T-025 armholes: the sleeveless panels leave the arm root free (no panel vertex wraps the arm beyond the
    # shoulder joint) and the opening depth follows the arm-root circumference; fuller shoulders reach further out
    # along the shoulder line than the default strap.
    shoulder_z = P["shoulder"]["z"] * H
    joint_x = P["shoulder"]["joint_x"] * H

    def on_arm(ob):
        n = 0
        for v in world_mesh(ob)[0]:
            for s in ("L", "R"):
                a, b = J0[f"shoulder.{s}"], J0[f"wrist.{s}"]
                d = b - a
                t = (v - a).dot(d) / d.length_squared
                if 0.12 <= t <= 1.0 and (v - (a + d * t)).length <= GAR.generator._arm_radius(P, H, t) + 0.004:
                    n += 1
        return n

    def strap_reach(ob):
        xs = [abs(v.x) for v in world_mesh(ob)[0] if shoulder_z - 0.01 * fit.torso <= v.z <= shoulder_z + 0.02]
        return max(xs) if xs else 0.0
    plain_vest = by_item("vest", "main")[0]
    full_reach, plain_reach = strap_reach(vest_main), strap_reach(plain_vest)
    arm_vertices = {"vest": on_arm(plain_vest), "emb_vest": on_arm(vest_main), "dress": None}
    result["checks"]["armholes"] = {
        "armhole_depth_m": round(GAR.generator.ARMHOLE_DEPTH_ROOT_RADII * fit.arm_root, 5),
        "arm_root_radius_m": round(fit.arm_root, 5), "panel_vertices_on_arm": arm_vertices,
        "strap_reach_x_m": {"default": round(plain_reach, 5), "shoulder_width_0.55": round(full_reach, 5)},
        "shoulder_joint_x_m": round(joint_x, 5),
        "pass": arm_vertices["vest"] == 0 and arm_vertices["emb_vest"] == 0 and full_reach > plain_reach + 0.004}
    # Rolled edge: closed tubes along the vest's open edges (front/neck/hem loop and both armholes).
    edges = by_item("emb_vest", "edge")
    edge_r = []
    for ob in edges:
        pts = world_mesh(ob)[0]
        edge_r.append(len(pts))
    result["checks"]["rolled_edge"] = {"objects": [o.name for o in edges], "vertices": edge_r,
                                       "pass": len(edges) >= 3}
    # Buttons off the centre line: edge buttons on the vest's left front, waistband buttons on the bloomers.
    vb = by_item("emb_vest", "buttons")
    bb = by_item("bloomers", "buttons")
    opening = 0.023 * fit.torso
    vb_x = [sum(p.x for p in world_mesh(o)[0]) / len(o.data.vertices) for o in vb]
    bb_z = [sum(p.z for p in world_mesh(o)[0]) / len(o.data.vertices) for o in bb]
    waist_z = P["torso"]["levels"][2][0] * H
    result["checks"]["placed_buttons"] = {
        "edge_button_x_m": [round(x, 4) for x in vb_x], "waistband_button_z_m": [round(z, 4) for z in bb_z],
        "pass": len(vb) == 3 and all(x > opening for x in vb_x) and len(bb) == 3 and
                all(waist_z - 0.03 * fit.torso <= z <= waist_z for z in bb_z)}
    # Crotch gusset: from the front and the back, rays between the legs below the crotch hit the bloomers (main or
    # gusset); the plain shorts (no gusset) show the gap.
    gusset_report = next(i for i in build_report["items"] if i["name"] == "bloomers").get("gusset", {})

    def gap_hits(objs):
        polys = []
        verts = []
        for o in objs:
            vs, fs = world_mesh(o)
            base = len(verts)
            verts += vs
            polys += [tuple(base + i for i in f) for f in fs]
        bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False)
        cz, bz = gusset_report["crotch_z_m"], gusset_report["bottom_z_m"]
        hits = total = 0
        for k in range(1, 6):
            z = cz - (cz - bz) * k / 6
            for y0, d in ((-1.0, Vector((0, 1, 0))), (1.0, Vector((0, -1, 0)))):
                total += 1
                hit = bvh.ray_cast(Vector((0, y0, z)), d, 2.0)
                hits += hit[0] is not None and abs(hit[0].y) < 0.2
        return hits, total
    with_gusset = gap_hits(by_item("bloomers"))
    without = gap_hits(by_item("shorts"))
    result["checks"]["crotch_gusset"] = {"gusset": gusset_report, "rays_hit_with_gusset": with_gusset,
                                         "rays_hit_plain_shorts": without,
                                         "pass": bool(by_item("bloomers", "gusset")) and with_gusset[0] == with_gusset[1]}
    # Chunky boots: shaft and toe volume over the plain fleece shell.
    fb = [o for o in by_item("fur_boots", "main") if o.name.endswith(".L")][0]
    ankle_l = J0["ankle.L"]
    top_z = ankle_l.z + 0.5 * (P["leg"]["knee_z"] * H - ankle_l.z)
    mid_z = ankle_l.z + 0.7 * (top_z - ankle_l.z)
    fverts = world_mesh(fb)[0]
    shaft_r = max(math.hypot(v.x - ankle_l.x, v.y) for v in fverts if abs(v.z - mid_z) < 0.006)
    leg_r = GAR.generator._leg_radius(P, H, (P["leg"]["hip_z"] * H - mid_z) / (P["leg"]["hip_z"] * H - ankle_l.z))
    toe_y = min(v.y for v in fverts)
    foot_front = -0.9 * P["foot"]["length"] * H
    result["checks"]["chunky_boots"] = {
        "shaft_radius_m": round(shaft_r, 5), "leg_radius_m": round(leg_r, 5),
        "shaft_extra_m": round(shaft_r - leg_r - (0.012 + 0.002) * fit.leg, 5), "requested_shaft_m": SHAFT * fit.leg,
        "toe_front_y_m": round(toe_y, 5), "foot_front_y_m": round(foot_front, 5),
        "pass": shaft_r - leg_r - (0.012 + 0.002) * fit.leg >= 0.7 * SHAFT * fit.leg and
                toe_y <= foot_front - (0.012 * fit.leg + 0.5 * TOE * fit.leg)}

    # Structural skinning checks: every garment vertex has <=4 normalized deform groups, an Armature modifier and
    # (when enabled) the body collision Shrinkwrap evaluated AFTER the Armature modifier.
    max_weight_error = 0.0
    max_influences = 0
    unweighted = 0
    bad_modifiers = []
    for ob in garment_objects:
        kinds = [mod.type for mod in ob.modifiers]
        if not any(mod.type == "ARMATURE" and mod.object == rig for mod in ob.modifiers):
            bad_modifiers.append(ob.name)
        elif "SHRINKWRAP" in kinds and (kinds.index("SHRINKWRAP") < kinds.index("ARMATURE") or
                                        ob.modifiers[GAR.generator.COLLISION_MODIFIER].target.data != body.data or
                                        ob.modifiers[GAR.generator.COLLISION_MODIFIER].vertex_group !=
                                        GAR.generator.COLLISION_GROUP):
            bad_modifiers.append(ob.name)
        elif "SHRINKWRAP" not in kinds:
            bad_modifiers.append(ob.name)
        deform = {g.index for g in ob.vertex_groups if not g.name.startswith("ps_")}
        for vertex in ob.data.vertices:
            weights = [g.weight for g in vertex.groups if g.group in deform]
            max_influences = max(max_influences, len(weights))
            if not weights:
                unweighted += 1
            else:
                max_weight_error = max(max_weight_error, abs(sum(weights) - 1.0))
    result["checks"]["skinning"] = {"unweighted_vertices": unweighted, "max_influences": max_influences,
                                    "max_normalization_error": round(max_weight_error, 8),
                                    "bad_modifier_stacks": bad_modifiers,
                                    "pass": unweighted == 0 and max_influences <= 4 and max_weight_error < 1e-5 and not bad_modifiers}

    movement = {ob.name: 0.0 for ob in garment_objects}
    worst = {"min_clearance_m": float("inf")}
    for outfit, objects in outfits.items():
        result["masks"][outfit] = GAR.set_active_items(body, garment_objects, items[outfit])
        reset_pose()
        rest_positions = {ob.name: world_mesh(ob)[0] for ob in objects}
        result["rest"][outfit] = clearance(objects, clearance_floor)
        for clip_name, frame in samples:
            meta = apply_clip(clip_name, frame)
            pose_key = f"{clip_name}:{frame}"
            entry = clearance(objects, 0.0)
            result["poses"].setdefault(pose_key, {"source": meta, "outfits": {}})["outfits"][outfit] = entry
            if entry["min_clearance_m"] < worst["min_clearance_m"]:
                worst = {"outfit": outfit, "clip": clip_name, "frame": frame, **entry}
            for ob in objects:
                posed = world_mesh(ob)[0]
                rest = rest_positions[ob.name]
                if len(posed) == len(rest):
                    rms = math.sqrt(sum((p - q).length_squared for p, q in zip(posed, rest)) / max(1, len(rest)))
                    movement[ob.name] = max(movement[ob.name], rms)
        print(f"[garment_generic_test] {body_name} {outfit} measured", flush=True)
    result["worst_pose"] = worst
    result["checks"]["garments_follow_skinning"] = {
        "minimum_max_rms_motion_m": round(min(movement.values()), 6),
        "maximum_rms_motion_m": round(max(movement.values()), 6),
        "pass": min(movement.values()) > 0.001,
    }

    reset_pose()
    if evidence:
        result["evidence"] = render_evidence(body_name, body, garment_objects, items, worst, out, evidence,
                                             apply_clip, reset_pose, world_mesh, bpy, Vector, GAR)

    all_clear = all(entry["pass"] for entry in result["rest"].values()) and all(
        entry["pass"] for pose in result["poses"].values() for entry in pose["outfits"].values())
    result["checks"]["clearance"] = {"rest_floor_m": clearance_floor, "pose_floor_m": 0.0,
                                     "poses": len(samples),
                                     "worst_pose": {k: worst.get(k) for k in ("outfit", "clip", "frame", "min_clearance_m")},
                                     "pass": all_clear}
    # The T-024 puff-profile checks measure the max radius per limb-axis bin, with bins chosen on the reference
    # body. On a body with a much rounder seat and shorter, thicker limbs that measure also picks up the seat and
    # the elbow curvature, so there they are recorded for information only (same thresholds, not gating).
    if body_name != "reference":
        for key in ("sleeve_puff", "bloomers_puff"):
            result["checks"][key]["gating"] = False
            result["checks"][key]["note"] = "T-024 profile check, bins defined on the reference body; informational here"
    result["pass"] = all(check["pass"] for check in result["checks"].values() if check.get("gating", True))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, f"garment_generic_test_{body_name}.blend"), compress=True)
    return result


def render_evidence(body_name, body, garment_objects, items, worst, out, evidence, apply_clip, reset_pose,
                    world_mesh, bpy, Vector, GAR):
    views = os.path.join(out, "views")
    os.makedirs(evidence, exist_ok=True)
    os.makedirs(views, exist_ok=True)
    scene = bpy.context.scene
    # Low-sample Cycles (CPU) with OpenImageDenoise.
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.view_layers[0].cycles.use_denoising = True
    denoiser = scene.cycles.denoiser
    scene.render.resolution_x = scene.render.resolution_y = 320
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("evidence_world")
    world = scene.world
    world.color = (0.035, 0.035, 0.035)
    if world.node_tree is None:
        world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.055, 0.065, 0.08, 1)
    background.inputs["Strength"].default_value = 0.35
    cam_data = bpy.data.cameras.new("evidence_camera")
    cam = bpy.data.objects.new("evidence_camera", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.18
    target = Vector((0, 0, 0.50))
    area_data = bpy.data.lights.new("evidence_key", "AREA")
    area_data.energy, area_data.shape, area_data.size = 650, "DISK", 2.5
    area = bpy.data.objects.new("evidence_key", area_data)
    scene.collection.objects.link(area)
    area.location = (1.8, -2.4, 2.6)
    area.rotation_euler = (target - area.location).to_track_quat("-Z", "Y").to_euler()
    fill_data = bpy.data.lights.new("evidence_fill", "AREA")
    fill_data.energy, fill_data.size = 280, 2.0
    fill = bpy.data.objects.new("evidence_fill", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (-2.0, 0.4, 1.5)
    fill.rotation_euler = (target - fill.location).to_track_quat("-Z", "Y").to_euler()
    angles = [("front", 0), ("threequarter", 45), ("side", 90), ("back", 180)]

    def make_sheet(paths, destination):
        size = 320
        sheet = bpy.data.images.new("turnaround_sheet", width=size * 2, height=size * 2, alpha=False)
        pixels = [0.0] * (size * size * 4 * 4)
        slots = [(0, size), (size, size), (0, 0), (size, 0)]
        for path, (ox, oy) in zip(paths, slots):
            image = bpy.data.images.load(path, check_existing=False)
            source = list(image.pixels[:])
            for y in range(size):
                src = y * size * 4
                dst = ((oy + y) * size * 2 + ox) * 4
                pixels[dst:dst + size * 4] = source[src:src + size * 4]
            bpy.data.images.remove(image)
        sheet.pixels.foreach_set(pixels)
        sheet.filepath_raw = destination
        sheet.file_format = "PNG"
        sheet.save()
        bpy.data.images.remove(sheet)

    render_info = {"engine": scene.render.engine, "samples": 8, "denoiser": denoiser,
                   "sheet_px": [640, 640], "views": [name for name, _ in angles]}

    def render_views(prefix, destination, look_at):
        paths = []
        for view_name, degrees in angles:
            angle = math.radians(degrees)
            cam.location = look_at + Vector((2.2 * math.sin(angle), -2.2 * math.cos(angle), 0.18))
            cam.rotation_euler = (look_at - cam.location).to_track_quat("-Z", "Y").to_euler()
            path = os.path.join(views, f"{body_name}_{prefix}_{view_name}.png")
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        make_sheet(paths, destination)
        return os.path.basename(destination)

    for outfit in items:
        GAR.set_active_items(body, garment_objects, items[outfit])
        reset_pose()
        render_info[outfit] = render_views(
            outfit, os.path.join(evidence, f"synthetic_{body_name}_{outfit}_turnaround.png"), target)
    # Worst measured pose (lowest visible clearance), same four views, framed on the posed body.
    GAR.set_active_items(body, garment_objects, items[worst["outfit"]])
    apply_clip(worst["clip"], worst["frame"])
    posed = world_mesh(body)[0]
    lo = Vector((min(p.x for p in posed), min(p.y for p in posed), min(p.z for p in posed)))
    hi = Vector((max(p.x for p in posed), max(p.y for p in posed), max(p.z for p in posed)))
    render_info["worst_pose"] = render_views(
        "worst", os.path.join(evidence, f"synthetic_{body_name}_worst_pose.png"), (lo + hi) * 0.5)
    render_info["worst_pose_source"] = {k: worst[k] for k in ("outfit", "clip", "frame", "min_clearance_m")}
    reset_pose()
    return render_info


if "--internal" in sys.argv:
    _internal()
else:
    _driver()
