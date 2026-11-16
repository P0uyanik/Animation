"""End-to-end test for the shared ``garment/1`` generator.

Plain-Python entry point:

    python tests/garment_generic_test.py --blender <blender> [--out <dir>] [--evidence-dir <dir>]

The subprocess builds the neutral body_generic mannequin, shirt + vest +
shorts + boots and a dress variant. It transfers body weights, applies six
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
    from mathutils import Quaternion, Vector
    from mathutils.bvhtree import BVHTree

    charsys = os.path.join(ROOT, "pipeline", "charsys")
    clips_dir = os.path.join(ROOT, "pipeline", "clips")
    sys.path.insert(0, charsys)
    sys.path.insert(0, clips_dir)
    import body_generic as BG
    import body_v6 as B
    import clip_tools as CT
    import garments as GAR
    import geom as G
    import retarget as RT

    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--internal", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence-dir", default="")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

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
    profile = json.load(open(os.path.join(charsys, "rig_profiles", "humanoid_rigify.json")))
    ref = RT.reference_pose(profile["reference_pose"])
    (el, er), (sl, sr) = profile["mirror"]["engine"], profile["mirror"]["source"]
    roles = {}
    for role, source in profile["roles"].items():
        roles[role] = source
        if role.endswith(el):
            roles[role[:-len(el)] + er] = source[:-len(sl)] + sr if source.endswith(sl) else source.replace(sl, sr)
    sources = {role: source for role, source in roles.items() if source in rig.data.bones and rig.data.bones[source].use_deform}
    semantic_parent = {entry["name"]: entry["parent"] for entry in ref}

    def deform_parent(bone):
        parent = bone.parent
        while parent is not None and not parent.use_deform:
            parent = parent.parent
        return parent.name if parent else None

    new_parent = {bone.name: deform_parent(bone) for bone in rig.data.bones if bone.use_deform}
    role_of = {source: role for role, source in sources.items()}
    for source, role in role_of.items():
        parent = semantic_parent.get(role)
        while parent and parent not in sources:
            parent = semantic_parent.get(parent)
        new_parent[source] = sources[parent] if parent else None
    rig.animation_data_clear()
    for pb in rig.pose.bones:
        for constraint in list(pb.constraints):
            pb.constraints.remove(constraint)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    edit = rig.data.edit_bones
    for name, parent in new_parent.items():
        edit[name].use_connect = False
        edit[name].parent = edit[parent] if parent else None
        edit[name].bbone_segments = 1
    for bone in list(edit):
        if not bone.use_deform:
            edit.remove(bone)
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.custom_shape = None
    clip_rig = CT.Rig(rig)

    def reset_pose():
        for pb in rig.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
            pb.scale = (1, 1, 1)
        bpy.context.view_layer.update()

    def sample(track, frame, quaternion=True):
        if "samples" in track:
            values = track["samples"][max(0, min(len(track["samples"]) - 1, frame))]
            return list(values)
        keys = track["keys"]
        if frame <= keys[0][0]:
            return list(keys[0][1:])
        if frame >= keys[-1][0]:
            return list(keys[-1][1:])
        for left, right in zip(keys, keys[1:]):
            if left[0] <= frame <= right[0]:
                t = (frame - left[0]) / max(1, right[0] - left[0])
                if quaternion:
                    return list(Quaternion(left[1:]).slerp(Quaternion(right[1:]), t))
                return [a + (b - a) * t for a, b in zip(left[1:], right[1:])]
        raise AssertionError("unreachable clip sample")

    def apply_clip(name, frame):
        clip = json.load(open(os.path.join(ROOT, "content", "clips", name + ".clip.json")))
        rotations = {role: sample(track, frame) for role, track in clip["tracks"].items()}
        root = [0.0, 0.0, 0.0]
        if clip.get("root", {}).get("translation"):
            root = sample(clip["root"]["translation"], frame, quaternion=False)
        reset_pose()
        clip_rig.pose_from_clip_rotations(rotations, root)
        bpy.context.view_layer.update()
        return {"clip": name, "frame": frame, "frame_count": clip["frame_count"]}

    def world_mesh(ob):
        deps = bpy.context.evaluated_depsgraph_get()
        evaluated = ob.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        verts = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        faces = [tuple(poly.vertices) for poly in mesh.polygons]
        evaluated.to_mesh_clear()
        return verts, faces

    mask_mod = body.modifiers.get(GAR.generator.MASK_MODIFIER)
    PROBES = [Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]

    def clearance(objects, floor):
        """Signed clearance of garment vertices over visible body faces (hidden regions reported for information).
        Passes when no vertex over visible skin is closer than ``floor`` (negative = inside the body)."""
        garment_points = [(ob.name, p) for ob in objects for p in world_mesh(ob)[0]]
        visible = GAR.visible_face_flags(body)
        enabled = mask_mod.show_viewport if mask_mod else False
        if mask_mod:
            mask_mod.show_viewport = False  # full posed body; face indices match body.data.polygons
        body_verts, body_faces = world_mesh(body)
        if mask_mod:
            mask_mod.show_viewport = enabled
            bpy.context.view_layer.update()
        assert len(body_faces) == len(visible)
        bvh = BVHTree.FromPolygons(body_verts, body_faces, all_triangles=False)
        best = {"visible": [float("inf"), None, None, None], "hidden": [float("inf"), None, None, None]}
        counted, inside, buried, buried_min = 0, 0, 0, float("inf")
        def crossings(origin, direction):
            count, start = 0, origin
            for _ in range(64):
                hit = bvh.ray_cast(start + direction * 1e-6, direction)
                if hit[0] is None:
                    break
                count, start = count + 1, hit[0]
            return count

        for name, point in garment_points:
            location, normal, index, distance = bvh.find_nearest(point)
            if location is None:
                continue
            signed = (point - location).dot(normal)
            if signed < 0 and distance > 1e-6:
                # Posed creases make the nearest-face sign unreliable (nearest point on an edge, or on a face that
                # the bent body itself has pushed inside another part). The body is one closed surface, so a point
                # is outside when every probe ray crosses it an even number of times.
                away = (point - location).normalized()
                if all(crossings(point, direction) % 2 == 0 for direction in (away, *PROBES)):
                    signed = distance
            if signed < clearance_floor and visible[index]:
                # Skin-to-skin contact is not visible skin: the pose has pushed this skin inside another body part,
                # or another body part faces it closer than a garment can fit (arm resting on the ribs).
                probe = location + normal * 1e-4
                facing = bvh.ray_cast(probe, normal, contact_gap)
                if facing[0] is not None or sum(crossings(probe, direction) % 2 for direction in PROBES) >= 4:
                    buried += 1
                    buried_min = min(buried_min, signed)
                    continue
            key = "visible" if visible[index] else "hidden"
            counted += key == "visible"
            inside += key == "visible" and signed < 0
            if signed < best[key][0]:
                best[key] = [signed, name, tuple(round(v, 6) for v in point), tuple(round(v, 6) for v in location)]
        value, closest, garment_point, body_point = best["visible"]
        return {"min_clearance_m": round(value, 6), "closest_object": closest,
                "garment_point_m": garment_point, "body_point_m": body_point,
                "vertices_over_visible_body": counted, "vertices_inside_visible_body": inside,
                "vertices_total": len(garment_points), "floor_m": floor,
                "hidden_region_min_m": round(best["hidden"][0], 6) if best["hidden"][1] else None,
                "skin_contact_vertices": buried,
                "skin_contact_min_m": round(buried_min, 6) if buried else None,
                "pass": value >= floor}

    items = {
        "outfit_a": ["shirt", "vest", "shorts", "boots"],
        "dress": ["dress", "boots"],
    }
    outfits = {name: [ob for ob in garment_objects if ob.get("ps_garment_item") in worn] for name, worn in items.items()}
    result = {"blender": bpy.app.version_string, "body_generator": "body_generic/1", "garment_generator": "garment/1",
              "build": build_report, "rig": rig_report, "weight_transfer": bind_report, "checks": {}, "poses": {},
              "rest": {}, "masks": {}}

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
