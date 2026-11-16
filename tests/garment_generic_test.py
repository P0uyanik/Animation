"""End-to-end test for the shared ``garment/1`` generator.

Plain-Python entry point:

    python tests/garment_generic_test.py --blender <blender> [--out <dir>] [--evidence-dir <dir>]

The subprocess builds the neutral body_generic mannequin, shirt + vest +
shorts + boots, a dress variant and outfit B (puffed sleeves, round collar,
embroidered vest, bloomers, thick boot cuffs). It transfers body weights, applies six
repository clips through the shared retargeter, and measures signed garment to
body clearance in rest and posed states. Optional evidence is two 640 px
four-view Cycles/OIDN turnaround sheets.
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
    a = ap.parse_args()
    owned = tempfile.TemporaryDirectory(prefix="garment_generic_test_") if not a.out else None
    out = os.path.abspath(a.out or owned.name)
    os.makedirs(out, exist_ok=True)
    cmd = [a.blender, "-b", "--factory-startup", "-P", os.path.abspath(__file__), "--", "--internal", "--out", out]
    if a.evidence_dir:
        cmd += ["--evidence-dir", os.path.abspath(a.evidence_dir)]
    log_path = os.path.join(out, "blender.log")
    with open(log_path, "w") as log:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    result_path = os.path.join(out, "garment_generic_test.json")
    result = json.load(open(result_path)) if os.path.exists(result_path) else {"pass": False}
    print(f"[garment_generic_test] {'PASS' if result.get('pass') else 'FAIL'}; log={log_path}")
    if result_path:
        print(json.dumps(result, indent=1))
    if owned:
        owned.cleanup()
    raise SystemExit(0 if proc.returncode == 0 and result.get("pass") else 1)


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
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    PUFF, RELIEF, CUFF_R = 0.016, 0.0018, 0.009
    neutral = json.load(open(os.path.join(ROOT, "pipeline", "clips", "mannequin.json")))
    H, P = float(neutral["body"]["height_m"]), neutral["body"]["params"]
    clothing = {
        "generator": "garment/1",
        "hide_body_faces": True,
        "mask_margin_m": 0.015,
        "collision": {"enabled": True, "offset_m": 0.002, "radius_m": 0.08, "falloff_m": 0.02, "passes": 3},
        "max_influences": 4,
        "defaults": {"thickness_m": 0.002, "ease_m": 0.009, "seam_radius_m": 0.00115},
        "garments": [
            {"type": "top", "name": "shirt", "sleeve_length": 0.74, "collar": "shirt",
             "buttons": {"count": 4, "radius_m": 0.005},
             "bands": {"hem": True, "cuff": True, "rib_ridges": 2}, "seam_lines": True,
             "material": {"preset": "woven cotton", "base_color_srgb": [211, 201, 190]},
             "materials": {"buttons": {"preset": "buttons/plastic", "base_color_srgb": [142, 104, 69]}}},
            {"type": "vest", "name": "vest", "ease_m": 0.015, "open_front_m": 0.023,
             "pockets": {"width_m": 0.030, "height_m": 0.027, "depth_m": 0.0035},
             "bands": {"hem": True}, "seam_lines": True,
             "material": {"preset": "felt", "base_color_srgb": [137, 89, 88]}},
            {"type": "shorts", "name": "shorts", "length": 0.38, "cuff": True,
             "bands": {"waist": True, "cuff": True}, "seam_lines": True,
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
            # bloomers with gathered cuffs, a thick boot cuff). Same sleeve/leg lengths as outfit A for comparison.
            {"type": "top", "name": "puff_top", "sleeve_length": 0.74, "sleeve_puff_m": PUFF, "sleeve_puff_peak": 0.6,
             "collar": {"type": "round", "width_m": 0.028, "gap_m": 0.008, "slope": 0.5, "tip_round": 0.35},
             "bands": {"cuff": True, "cuff_radius_m": 0.004},
             "material": {"preset": "cotton knit", "base_color_srgb": [214, 206, 196]}},
            {"type": "vest", "name": "emb_vest", "ease_m": 0.022, "open_front_m": 0.023,
             "embroidery": {"size_m": 0.03, "relief_m": RELIEF,
                            "motifs": [{"u": 0.55, "v": 0.7}, {"u": -0.55, "v": 0.7, "petals": 6},
                                       {"u": 0.5, "v": 0.35, "style": "sprig", "rotation_deg": 25},
                                       {"u": 0.0, "v": 0.6, "face": "back", "style": "sprig", "leaves": 5}],
                            "material": {"preset": "felt", "base_color_srgb": [60, 40, 44]},
                            "accent_material": {"preset": "wool yarn", "base_color_srgb": [200, 190, 180]}},
             "material": {"preset": "felt", "base_color_srgb": [150, 96, 96]}},
            {"type": "shorts", "name": "bloomers", "length": 0.38, "ease_m": 0.012, "puff_m": PUFF, "puff_inner": 0.3,
             "cuff": True, "bands": {"waist": True, "cuff": True, "cuff_radius_m": 0.004},
             "material": {"preset": "woven cotton", "base_color_srgb": [120, 140, 112]}},
            {"type": "boots", "name": "fur_boots", "height": 0.5, "ease_m": 0.012, "cuff": True,
             "bands": {"cuff": True, "cuff_radius_m": CUFF_R}, "sole": {"thickness_m": 0.007},
             "material": {"preset": "fleece", "base_color_srgb": [120, 82, 64]}},
        ],
    }

    bpy.ops.wm.read_factory_settings(use_empty=True)
    C = bpy.data.collections.new("garment_test")
    bpy.context.scene.collection.children.link(C)
    J = BG.joints(P, H)
    frames = BG.hand_frames(P, H, J)
    skin_mat = G.material("M_test_skin", (185, 161, 148), roughness=0.72)
    parts = BG.build_body(C, {"skin": skin_mat}, P, H, J, frames)
    body = parts[0][0]
    garment_objects, build_report = GAR.build(C, body, clothing, P, H, J, G)
    rig, rig_report = BG.rig_generic(C, "rig_garment_test", parts, P, H, J, frames,
                                     neutral["rig"]["weight_rules"], B, neutral["rig"].get("weight_smooth"))
    bind_report = GAR.bind_to_body(rig, body, garment_objects, max_influences=clothing["max_influences"])

    # Convert Rigify to the same plain semantic FK deform rig used to author the repository clips.
    clip_rig = EV.semantic_fk_rig(rig, ROOT)
    player = EV.ClipPlayer(rig, clip_rig, os.path.join(ROOT, "content", "clips"))
    reset_pose, apply_clip, world_mesh = player.reset, player.apply, EV.world_mesh

    def clearance(objects, floor):
        return EV.clearance(body, objects, floor, contact_gap, contact_floor=clearance_floor)

    items = {
        "outfit_a": ["shirt", "vest", "shorts", "boots"],
        "dress": ["dress", "boots"],
        "outfit_b": ["puff_top", "emb_vest", "bloomers", "fur_boots"],
    }
    outfits = {name: [ob for ob in garment_objects if ob.get("ps_garment_item") in worn] for name, worn in items.items()}
    result = {"blender": bpy.app.version_string, "body_generator": "body_generic/1", "garment_generator": "garment/1",
              "build": build_report, "rig": rig_report, "weight_transfer": bind_report, "checks": {}, "poses": {},
              "rest": {}, "masks": {}}

    # Volume, collar and decoration parameters, rest pose: outfit B against the plain outfit A pieces (outer half of
    # each limb), the collar's front gap, embroidery relief over the vest and the boot cuff tube radius.
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

    J0 = BG.joints(P, H)
    sh, wr = J0["shoulder.L"], J0["wrist.L"]
    arm_bins = [(0.40, 0.48), (0.66, 0.72)]  # puff peak (t 0.10 + 0.6 * 0.64 = 0.48) / just above the cuff
    plain = limb_profile(by_item("shirt", "main")[0], sh, wr, arm_bins, 0.07, sh.x + 0.01)
    puffed = limb_profile(by_item("puff_top", "main")[0], sh, wr, arm_bins, 0.07, sh.x + 0.01)
    hip, ankle = Vector((J0["hip.L"].x, 0, P["leg"]["hip_z"] * H)), Vector((J0["hip.L"].x, 0, P["leg"]["ankle_z"] * H))
    leg_bins = [(0.08, 0.16), (0.33, 0.37)]  # bloomer peak (s = 1/3 of the length 0.38) / just above the cuff
    shorts_plain = limb_profile(by_item("shorts", "main")[0], hip, ankle, leg_bins, 0.09, hip.x)
    shorts_puff = limb_profile(by_item("bloomers", "main")[0], hip, ankle, leg_bins, 0.09, hip.x)
    result["checks"]["sleeve_puff"] = {
        "plain_m": [round(x, 5) for x in plain], "puffed_m": [round(x, 5) for x in puffed], "puff_m": PUFF,
        "pass": puffed[0] - plain[0] >= 0.8 * PUFF and abs(puffed[1] - plain[1]) <= 0.5 * PUFF}
    result["checks"]["bloomers_puff"] = {
        "plain_m": [round(x, 5) for x in shorts_plain], "puffed_m": [round(x, 5) for x in shorts_puff], "puff_m": PUFF,
        "pass": shorts_puff[0] - shorts_plain[0] >= 0.6 * PUFF and shorts_puff[1] - shorts_plain[1] <= 0.5 * PUFF}
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
    vest_bvh = BVHTree.FromPolygons(*world_mesh(vest_main), all_triangles=False)
    emb = by_item("emb_vest", "embroidery") + by_item("emb_vest", "embroidery_accent")
    motifs = next(i for i in build_report["items"] if i["name"] == "emb_vest").get("embroidery_motifs", [])
    heights = []
    for ob in emb:
        for v in world_mesh(ob)[0]:
            loc, nrm, _, _ = vest_bvh.find_nearest(v)
            heights.append((v - loc).length)
    try:
        GAR.validate({"generator": "garment/1", "garments": [
            {"type": "boots", "name": "b", "material": "felt", "embroidery": {"motifs": [{"u": 0}]}}]})
        rejects_footwear = False
    except ValueError:
        rejects_footwear = True
    result["checks"]["embroidery"] = {
        "objects": [o.name for o in emb], "motifs": len(motifs),
        "max_height_over_vest_m": round(max(heights), 5) if heights else None,
        "rejects_embroidery_on_footwear": rejects_footwear,
        "pass": len(emb) == 2 and len(motifs) == 4 and max(heights) <= 0.02 and rejects_footwear and
                {o.get("ps_material_preset") for o in emb} == {"felt", "wool yarn"}}
    cuffs = by_item("fur_boots", "band")
    tube = []
    for ob in cuffs:
        zs = [p.z for p in world_mesh(ob)[0]]  # horizontal ring: its height is the tube diameter
        tube.append((max(zs) - min(zs)) / 2)
    result["checks"]["cuff_radius"] = {"tube_radius_m": [round(t, 5) for t in tube], "requested_m": CUFF_R,
                                       "pass": len(cuffs) == 2 and all(abs(t - CUFF_R) < 0.002 for t in tube)}

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

    # Rest pose keeps the 0.5 mm clearance floor. Posed: no garment vertex may be inside visible skin.
    clearance_floor = 0.0005
    contact_gap = 2 * clothing["collision"]["offset_m"] + clearance_floor
    samples = [("idle_relaxed", 45), ("wave", 52), ("point", 46), ("gest_shrug", 26),
               ("sit_down", 50), ("emo_happy", 30)]
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
    result["worst_pose"] = worst
    result["checks"]["garments_follow_skinning"] = {
        "minimum_max_rms_motion_m": round(min(movement.values()), 6),
        "maximum_rms_motion_m": round(max(movement.values()), 6),
        "pass": min(movement.values()) > 0.001,
    }

    reset_pose()
    if a.evidence_dir:
        evidence = os.path.abspath(a.evidence_dir)
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
                path = os.path.join(views, f"{prefix}_{view_name}.png")
                scene.render.filepath = path
                bpy.ops.render.render(write_still=True)
                paths.append(path)
            make_sheet(paths, destination)
            return os.path.basename(destination)

        for outfit in outfits:
            GAR.set_active_items(body, garment_objects, items[outfit])
            reset_pose()
            render_info[outfit] = render_views(outfit, os.path.join(evidence, f"synthetic_{outfit}_turnaround.png"),
                                               target)
        # Worst measured pose (lowest visible clearance), same four views, framed on the posed body.
        GAR.set_active_items(body, garment_objects, items[worst["outfit"]])
        apply_clip(worst["clip"], worst["frame"])
        posed = world_mesh(body)[0]
        lo = Vector((min(p.x for p in posed), min(p.y for p in posed), min(p.z for p in posed)))
        hi = Vector((max(p.x for p in posed), max(p.y for p in posed), max(p.z for p in posed)))
        render_info["worst_pose"] = render_views(
            "worst", os.path.join(evidence, "synthetic_worst_pose.png"), (lo + hi) * 0.5)
        render_info["worst_pose_source"] = {k: worst[k] for k in ("outfit", "clip", "frame", "min_clearance_m")}
        reset_pose()
        result["evidence"] = render_info

    all_clear = all(entry["pass"] for entry in result["rest"].values()) and all(
        entry["pass"] for pose in result["poses"].values() for entry in pose["outfits"].values())
    result["checks"]["clearance"] = {"rest_floor_m": clearance_floor, "pose_floor_m": 0.0,
                                     "worst_pose": {k: worst.get(k) for k in ("outfit", "clip", "frame", "min_clearance_m")},
                                     "pass": all_clear}
    result["pass"] = all(check["pass"] for check in result["checks"].values())
    json.dump(result, open(os.path.join(out, "garment_generic_test.json"), "w"), indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "garment_generic_test.blend"), compress=True)
    print("[garment_generic_test]", json.dumps(result))
    raise SystemExit(0 if result["pass"] else 1)


if "--internal" in sys.argv:
    _internal()
else:
    _driver()
