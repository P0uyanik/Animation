"""charsys: builds a character from its spec (headless Blender). The reusable successor of the v6 pilot builder.

    blender -b --factory-startup -P pipeline/charsys/build_character.py -- \
        --spec assets/characters/boy_yellow_hoodie/spec/boy_yellow_hoodie.spec.json --out <dir> \
        [--override <override.json> ...] [--no-glb] [--no-compare] [--fur-scale 1.0]

Outputs in --out (never inside assets/: publishing into the asset store is a separate, explicit step, asset_store.py):
  <id>_master.blend    A-pose, rigged, component collections, spec embedded, metadata stamped (no fur)
  <id>_compare.blend   arms lowered through the rig (as reference #27), fur on the posed surfaces (evaluation only)
  <id>.glb             meshes, deform skeleton, weights, morph targets
  build_report.json, components.json, animation_compat.json, spec.resolved.json

Master structure (collections under the root collection named after the character id):
  <id>.body  <id>.face  <id>.hair  <id>.clothing  <id>.accessories  <id>.rig  <id>.landmarks  (+ <id>.fur in compare)
Root collection custom properties: ps_character_id, ps_spec_sha256, ps_spec_version, ps_build, ps_role ("master").
"""
import argparse
import json
import math
import os
import sys
import time

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import body_v6 as B  # noqa: E402
import face as FACE  # noqa: E402
import hair as HAIR  # noqa: E402
import spec as S  # noqa: E402
from materials import builder as MATERIALS  # noqa: E402

G = B.G
COMPONENTS = {  # component -> object-name prefixes (exact names or prefixes ending with "." / "_")
    "body": ["head", "neck", "hand."],
    "face": ["eye.", "lid_", "lash.", "brow.", "mouth", "ear."],
    "hair": ["hair_"],
    "clothing": ["hood", "undershirt", "drawstring", "trouser", "sock.", "shoe", "sole."],
    "accessories": ["backpack", "buckle."],
    "rig": ["rig_"],
    "landmarks": ["LM_"],
    "fur": ["fur_"],
}
BUILD_ID = "charsys/1"


def component_of(name, components=None):
    for comp, prefixes in (components or COMPONENTS).items():
        for p in prefixes:
            if name == p or name.startswith(p):
                return comp
    return None


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--override", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--fur-scale", type=float, default=1.0)
    ap.add_argument("--no-glb", action="store_true")
    ap.add_argument("--no-compare", action="store_true")
    return ap.parse_args(argv)


def organise(C, cid, components=None):
    """Moves every object of the root collection into its component sub-collection. The component map comes from
    spec.components when given (generic characters); COMPONENTS is the legacy (boy) default."""
    components = components or COMPONENTS
    subs = {}
    for comp in components:
        sc = bpy.data.collections.get(f"{cid}.{comp}") or bpy.data.collections.new(f"{cid}.{comp}")
        if sc.name not in C.children:
            C.children.link(sc)
        subs[comp] = sc
    unassigned = []
    for ob in list(C.objects):
        comp = component_of(ob.name, components)
        if comp is None:
            unassigned.append(ob.name)
            continue
        subs[comp].objects.link(ob)
        C.objects.unlink(ob)
    for comp, sc in subs.items():
        sc["ps_component"] = comp
    return subs, unassigned


def stamp(C, spec, info, role):
    C["ps_character_id"] = spec["identity"]["id"]
    C["ps_spec_sha256"] = info["spec_sha256"]
    C["ps_spec_version"] = spec["metadata"].get("spec_version", "")
    C["ps_build"] = BUILD_ID
    C["ps_blender"] = bpy.app.version_string
    C["ps_role"] = role
    txt = bpy.data.texts.get("ps_character_spec.json") or bpy.data.texts.new("ps_character_spec.json")
    txt.clear()
    txt.write(S.canonical(spec))
    try:  # make the character show up in Blender's asset browser when this file is used as an asset library
        if C.asset_data is None:
            C.asset_mark()
        C.asset_data.description = f"{spec['identity'].get('display_name', '')} ({spec['identity']['id']}), spec {info['spec_sha256'][:12]}"
        for t in ("plush-studio", "character", spec["identity"]["id"]):
            if t not in C.asset_data.tags:
                C.asset_data.tags.new(t)
    except Exception as e:  # pragma: no cover
        print("[build_character] asset_mark failed:", e)


def describe_components(C, cid):
    out = {}
    for sc in C.children:
        objs = []
        for o in sorted(sc.objects, key=lambda o: o.name):
            d = {"name": o.name, "type": o.type}
            if o.type == "MESH":
                d.update(vertices=len(o.data.vertices), faces=len(o.data.polygons),
                         materials=[m.name for m in o.data.materials if m],
                         vertex_groups=len(o.vertex_groups),
                         shape_keys=[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [])
            elif o.type == "ARMATURE":
                d.update(bones=len(o.data.bones), deform_bones=sum(1 for b in o.data.bones if b.use_deform))
            elif o.type == "CURVES":
                d.update(curves=len(o.data.curves))
            objs.append(d)
        out[sc.name[len(cid) + 1:]] = objs
    return out


def animation_compat(rig, C, spec):
    deform = sorted(b.name for b in rig.data.bones if b.use_deform)
    controls = sorted(b.name for b in rig.data.bones if not b.name.startswith(("DEF-", "ORG-", "MCH-")))
    keys = {}
    for o in C.all_objects:
        if o.type == "MESH" and o.data.shape_keys:
            keys[o.name] = [k.name for k in o.data.shape_keys.key_blocks if k.name != "Basis"]
    return {"character_id": spec["identity"]["id"], "rest_pose": spec["animation"]["rest_pose"],
            "rig_generator": spec["rig"]["generator"], "armature_object": rig.name,
            "bones": len(rig.data.bones), "deform_bones": deform, "control_bones": controls,
            "shape_keys": keys, "expression_shape_keys": spec.get("face", {}).get("expression_shape_keys", []),
            "face_controls": sorted(k for k in rig.keys() if k.startswith("face_")),
            "head_bone": spec["rig"]["head_bone"], "chest_bone": spec["rig"]["chest_bone"],
            "interchange": spec["animation"]["interchange"], "not_carried_by_gltf": spec["animation"]["not_carried_by_gltf"],
            "note": "Animation written against these control/deform bone names and shape-key names can be reused by "
                    "any version with the same animation_compat signature."}


def add_face_controls(rig, C, names):
    """Facial controls on the rig: one 0-1 custom property per expression (face_<Name>), library-overridable, driving
    every shape key of that name. Episodes link the master and animate only the rig (an override), so expressions are
    animated without editing the master's mesh data."""
    made = {}
    for n in names:
        prop = f"face_{n}"
        rig[prop] = 0.0
        ui = rig.id_properties_ui(prop)
        ui.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, default=0.0, description=f"Expression {n} (0-1)")
        rig.property_overridable_library_set(f'["{prop}"]', True)
        made[prop] = []
        for o in C.all_objects:
            if o.type != "MESH" or not o.data.shape_keys or n not in o.data.shape_keys.key_blocks:
                continue
            fc = o.data.shape_keys.key_blocks[n].driver_add("value")
            drv = fc.driver
            drv.type = "AVERAGE"
            var = drv.variables.new()
            var.name = "v"
            var.type = "SINGLE_PROP"
            var.targets[0].id = rig
            var.targets[0].data_path = f'["{prop}"]'
            made[prop].append(o.name)
    return made


def main_generic(a, spec, info, out):
    """Generic path (body_generic/1): body, joints, rig fitting and skinning entirely from the spec; the generic face
    (spec.face.generator face_generic/1) and reusable accessories (spec.accessories.items) when the spec has them.
    Hair through the shared groom system (spec.hair.generator groom/1). Shared garments are opt-in through
    clothing.generator garment/1. The legacy boy path (below) is the compatibility baseline."""
    import body_generic as BG
    cid = spec["identity"]["id"]
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    C = bpy.data.collections.new(cid)
    bpy.context.scene.collection.children.link(C)
    H = float(spec["body"]["height_m"])
    P = spec["body"]["params"]
    J = BG.joints(P, H, spec["rig"].get("joints"))
    frames = BG.hand_frames(P, H, J)
    mats = spec["materials"]
    skin_rgb = tuple(mats.get("albedo_srgb", {}).get("skin") or mats["target_colors_srgb"]["skin"])
    skin_assignment = MATERIALS.get_assignment(mats, "skin")
    if skin_assignment:
        M = {"skin": MATERIALS.build_from_assignment("M_skin", skin_assignment)}
    else:
        M = {"skin": G.material("M_skin", skin_rgb, roughness=0.55, subsurface=0.2, sss_radius=(1, 0.4, 0.25), sss_scale=0.01)}
    parts = BG.build_body(C, M, P, H, J, frames)
    garment_objects = []
    garment_report = None
    if spec.get("clothing", {}).get("generator") == "garment/1":
        import garments as GAR
        garment_objects, garment_report = GAR.build(C, parts[0][0], spec["clothing"], P, H, J, G)
    head_bone = spec["rig"]["head_bone"]
    report = {"blender": bpy.app.version_string, "build": BUILD_ID + "+body_generic/1", "character_id": cid, **info}
    if mats.get("assignments"):
        report["material_presets"] = {slot: cfg["preset"] for slot, cfg in mats["assignments"].items()}
    if garment_report is not None:
        report["garments"] = garment_report
    fc = None
    acc = []
    face_spec = spec.get("face", {})
    if face_spec.get("generator") == "face_generic/1":
        import accessories as ACC
        import face_generic as FG
        fc = FG.build(C, M, parts[0][0], spec, P, H, head_bone)  # also sets the eye-bone depth (P.eyes.y)
        report["face"] = fc["report"]
        face_parts = fc["eyes"] + [o for l in fc["lids"] for o in l[:3]]
        acc, report["accessories"] = ACC.build(C, spec.get("accessories", {}).get("items"), fc["landmarks"], fc["ctx"],
                                               face_parts, head_bone, fc["ears"], mats.get("assignments"))
    groom = []
    if spec.get("hair", {}).get("generator") == "groom/1":  # shared spec-driven groom (hair structures are spec data)
        import groom as GROOM
        hp = P["head"]
        frame = {"centre": (0, hp["forward"] * H, hp["centre_z"] * H),
                 "radii": (hp["half_width"] * H, hp["half_depth"] * H, hp["half_height"] * H)}
        hair_mats = {}

        def hair_material(slot):
            if slot not in hair_mats:
                asg = MATERIALS.get_assignment(mats, slot)
                rgb = (mats.get("target_colors_srgb", {}).get(slot) or mats.get("target_colors_srgb", {}).get("hair")
                       or (90, 60, 50))
                hair_mats[slot] = (MATERIALS.build_from_assignment(f"M_{slot}", asg) if asg else
                                   G.material(f"M_{slot}", tuple(rgb), roughness=0.9, sheen=0.4))
            return hair_mats[slot]
        groom, report["hair"] = GROOM.build(C, parts[0][0], frame, spec["hair"], hair_material, B.face_y)
    report["model_s"] = round(time.time() - t0, 1)
    rig, rr = BG.rig_generic(C, f"rig_{cid}", parts, P, H, J, frames, spec["rig"].get("weight_rules", {}), B,
                             spec["rig"].get("weight_smooth"))
    report["rig"] = rr
    if garment_objects:
        report["garment_skinning"] = GAR.bind_to_body(rig, parts[0][0], garment_objects,
                                                       max_influences=int(spec["clothing"].get(
                                                           "max_influences", spec["rig"].get("max_influences", 4))))
    names = list(face_spec.get("expression_shape_keys", []))
    if fc is not None:
        FG.bind_rigid(rig, fc["rigid"])
        empties = FG.add_landmarks(C, fc["landmarks"])
        for em in empties.values():
            em.parent = rig
            em.parent_type = "BONE"
            em.parent_bone = head_bone
            em.matrix_world = Matrix.Translation(em.location)
        for frame, lens in acc:
            ACC.attach(rig, frame, lens, head_bone)
        names = fc["controls"]
    if groom:
        GROOM.bind(rig, groom, head_bone, spec["rig"].get("chest_bone", head_bone), spec["hair"].get("binding"))

    report["face_controls"] = add_face_controls(rig, C, names)
    if fc is not None:
        skin = parts[0][0]
        report["jaw"] = FACE.add_jaw(rig, skin, fc["cavity"], fc["mouth"], fc["landmarks"], head_bone, fc["mouth_cfg"])
        FG.add_jaw_preset_drivers(rig, fc["jaw_preset_weights"], float(fc["mouth_cfg"].get("jaw_open_deg", 7.0)))
        report["inbetween_drivers"] = FG.add_inbetween_drivers(rig, [o for o in C.all_objects if o.type == "MESH"])
        bpy.ops.object.select_all(action="DESELECT")  # the jaw adds a fifth influence on some skin vertices
        skin.select_set(True)
        bpy.context.view_layer.objects.active = skin
        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
        report["rig"]["rigify_bones"] = len(rig.data.bones)
        report["rig"]["deform_bones"] = sum(1 for b in rig.data.bones if b.use_deform)
        rig["ps_face_parts"] = json.dumps({"head": skin.name, "eye_L": "eye.L", "lid_upper_L": "lid_upper.L",
                                           "mouth": fc["mouth"].name, "cavity": fc["cavity"].name,
                                           "action_units": fc["report"]["action_units"], "presets": fc["report"]["presets"],
                                           "accessories": [f.name for f, _ in acc] + [l.name for _, l in acc if l is not None]})
    if fc is None:
        hp = P["head"]
        chin_z = float(hp.get("chin_z", hp["centre_z"] - hp["half_height"])) * H
        chin_y = float(hp.get("chin_y", hp["forward"] - hp["half_depth"])) * H
        em = bpy.data.objects.new("LM_chin", None)
        em.location = Vector((0, chin_y, chin_z))
        em.empty_display_size = 0.01
        C.objects.link(em)
        em.parent = rig
        em.parent_type = "BONE"
        em.parent_bone = head_bone
        em.matrix_world = Matrix.Translation(em.location)
    components = {k: list(v) for k, v in (spec.get("components") or
                                           {"body": ["body_skin", "hand."], "rig": ["rig_"],
                                            "landmarks": ["LM_"]}).items()}
    if garment_objects:
        components.setdefault("clothing", ["garment."])
    subs, unassigned = organise(C, cid, components)
    if unassigned:
        raise SystemExit(f"objects without a component: {unassigned}")
    stamp(C, spec, info, "master")
    if fc is not None:
        C["ps_engine_expressions"] = json.dumps(fc["engine_expressions"], sort_keys=True)
        # expression -> bone rotations (the jaw follows JawOpen and every preset that contains it), for the engine
        jdeg = float(fc["mouth_cfg"].get("jaw_open_deg", 7.0))
        eb = {"JawOpen": [{"bone": "DEF-jaw", "axis_local": [1, 0, 0], "degrees": jdeg}]}
        eb.update({p: [{"bone": "DEF-jaw", "axis_local": [1, 0, 0], "degrees": round(jdeg * w, 4)}] for p, w in fc["jaw_preset_weights"].items()})
        C["ps_expression_bones"] = json.dumps(eb, sort_keys=True)
        if face_spec.get("blink", {}).get("timing"):
            C["ps_blink_timing"] = json.dumps(face_spec["blink"]["timing"], sort_keys=True)
    rig["ps_character_id"] = cid
    report["joints_m"] = {k: [round(c, 4) for c in v] for k, v in J.items()}
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, f"{cid}_master.blend"), compress=True)
    json.dump(describe_components(C, cid), open(os.path.join(out, "components.json"), "w"), indent=1)
    spec_r = json.loads(json.dumps(spec))  # resolved copy: the generated control list (the embedded spec stays as given)
    if "face" in spec_r:
        spec_r["face"]["expression_shape_keys"] = names
    json.dump(animation_compat(rig, C, spec_r), open(os.path.join(out, "animation_compat.json"), "w"), indent=1)
    json.dump(spec_r, open(os.path.join(out, "spec.resolved.json"), "w"), indent=1)
    if not a.no_glb:
        bpy.ops.object.select_all(action="DESELECT")
        for o in C.all_objects:
            if o.type in ("MESH", "ARMATURE"):
                o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(out, f"{cid}.glb"), export_format="GLB", export_skins=True,
                                  export_morph=True, export_def_bones=True, export_animations=False, use_selection=True)
    if not a.no_compare and spec.get("rig", {}).get("comparison_pose"):
        bpy.context.view_layer.objects.active = rig
        for pb in rig.pose.bones:
            if "IK_FK" in pb.keys():
                pb["IK_FK"] = 1.0
        bpy.ops.object.mode_set(mode="POSE")
        ang = float(spec["rig"]["comparison_pose"]["upper_arm_fk_rotation_y_deg"])
        for s, sx in (("L", 1), ("R", -1)):
            pb = rig.pose.bones.get(f"upper_arm_fk.{s}")
            if pb is None:
                continue
            head_w = rig.matrix_world @ pb.head
            rm = Matrix.Translation(head_w) @ Matrix.Rotation(math.radians(sx * ang), 4, "Y") @ Matrix.Translation(-head_w)
            pb.matrix = rig.matrix_world.inverted() @ rm @ rig.matrix_world @ pb.matrix
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()
        C["ps_role"] = "evaluation"
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, f"{cid}_compare.blend"))
    report["objects"] = sorted(o.name for o in C.all_objects)
    report["total_s"] = round(time.time() - t0, 1)
    json.dump(report, open(os.path.join(out, "build_report.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k not in ("objects", "joints_m")}, indent=1))


def main():
    a = parse()
    out = os.path.abspath(a.out)
    root = os.path.abspath(os.path.join(HERE, "..", ".."))
    if os.path.commonpath([out, os.path.join(root, "assets")]) == os.path.join(root, "assets"):
        raise SystemExit("refusing to build into assets/: build elsewhere, then publish with asset_store.py")
    os.makedirs(out, exist_ok=True)
    spec, info = S.load(a.spec, a.override)
    cid = spec["identity"]["id"]
    if spec["body"].get("generator") == "body_generic/1":  # generic body path (any character); the legacy path follows
        return main_generic(a, spec, info, out)
    B.configure(spec)
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    C = bpy.data.collections.new(cid)
    scene.collection.children.link(C)
    M = B.make_materials()
    head, neck = B.build_head(C, M)
    ears = B.build_ears(C, M, head)
    eyes, lids, lms = B.build_eyes(C, M, head)
    brows, mouth = B.build_brows_mouth(C, M, head)
    mcfg = spec["face"].get("mouth", {})
    if mcfg.get("generator") in ("lips_jaw/1", "lips_jaw/2"):  # lips with a seam (replaces the closed mouth patch)
        mouth = FACE.build_mouth_lips(C, M, head, B, mcfg)
    hair, hair_stats = HAIR.build(C, M, head, B, spec["hair"])
    hoodie, hoodie_bits = B.build_hoodie(C, M)
    hands = B.build_hands(C, M)
    trousers, socks = B.build_legs(C, M)
    shoes, shoe_bits = B.build_shoes(C, M)
    pack, straps = B.build_backpack(C, M, hoodie["torso"])
    empties = B.add_landmarks(C, lms, head, ears)
    report = {"blender": bpy.app.version_string, "build": BUILD_ID, "character_id": cid, **info,
              "hair": hair_stats, "model_s": round(time.time() - t0, 1)}
    report["face"] = FACE.add_expression_keys(lids, brows, mouth, head, B, spec["face"], eyes)
    for ob in list(C.objects):
        if ob.type == "MESH" and not ob.data.shape_keys and ob.modifiers:
            G.apply_mods(ob)
    cavity = FACE.cut_mouth_and_cavity(C, M, head, B, mcfg, mouth) if mcfg.get("generator") in ("lips_jaw/1", "lips_jaw/2") else None
    head_bone, chest = spec["rig"]["head_bone"], spec["rig"]["chest_bone"]
    rigid = [(o, head_bone) for o in [head] + ears + brows + [mouth] + hair]
    rigid += FACE.lid_bindings(lids, head_bone, tracking=spec["face"].get("eyes", {}).get("lid_tracking", 0.0))
    if cavity is not None:
        rigid.append((cavity, head_bone))
    rigid += [(e, f"DEF-eye.{s}") for e, s in zip(eyes, ("L", "R"))]
    rigid += [(s, f"DEF-foot.{side}") for s, side in zip(shoes, ("L", "R"))]
    rigid += [(o, f"DEF-foot.{'L' if o.name.endswith('.L') else 'R'}") for o in shoe_bits]
    rigid += [(o, chest) for o in pack]
    rigid += [(o, chest) for o in hoodie_bits + straps]
    deforming = [neck] + list(hoodie.values()) + list(hands.values()) + trousers + socks
    rig, rr = B.rig_character(C, deforming, rigid)
    report["rig"] = rr
    for em in empties.values():
        em.parent = rig
        em.parent_type = "BONE"
        em.parent_bone = head_bone
        em.matrix_world = Matrix.Translation(em.location)
    if spec["face"].get("smile_coupling") and mouth.data.shape_keys:  # cheeks and lower lids join the Smile
        report["smile_coupling"] = FACE.add_smile_coupling(head, lids, mouth, {k: v.matrix_world.translation.copy() for k, v in empties.items()},
                                                           spec["face"]["smile_coupling"])
    report["face_controls"] = add_face_controls(rig, C, spec["face"]["expression_shape_keys"])
    if cavity is not None:
        report["jaw"] = FACE.add_jaw(rig, head, cavity, mouth, {k: v.matrix_world.translation.copy() for k, v in empties.items()}, head_bone, mcfg)
        report["rig"]["rigify_bones"] = len(rig.data.bones)  # counts after the added jaw bone
        report["rig"]["deform_bones"] = sum(1 for b in rig.data.bones if b.use_deform)
    subs, unassigned = organise(C, cid)
    if unassigned:
        raise SystemExit(f"objects without a component: {unassigned}")
    stamp(C, spec, info, "master")
    rig["ps_character_id"] = cid
    master = os.path.join(out, f"{cid}_master.blend")
    bpy.ops.wm.save_as_mainfile(filepath=master, compress=True)
    report["master_s"] = round(time.time() - t0, 1)
    json.dump(describe_components(C, cid), open(os.path.join(out, "components.json"), "w"), indent=1)
    json.dump(animation_compat(rig, C, spec), open(os.path.join(out, "animation_compat.json"), "w"), indent=1)
    json.dump(spec, open(os.path.join(out, "spec.resolved.json"), "w"), indent=1)
    if not a.no_glb:
        glb = os.path.join(out, f"{cid}.glb")
        t = time.time()
        bpy.ops.object.select_all(action="DESELECT")
        for o in C.all_objects:
            if o.type in ("MESH", "ARMATURE"):
                o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_skins=True, export_morph=True,
                                  export_def_bones=True, export_animations=False, use_selection=True)
        report["gltf"] = {"mb": round(os.path.getsize(glb) / 1e6, 1), "s": round(time.time() - t, 1)}
    if not a.no_compare:  # evaluation file: comparison pose + fur on posed surfaces (not a reusable asset)
        bpy.context.view_layer.objects.active = rig
        for pb in rig.pose.bones:
            if "IK_FK" in pb.keys():
                pb["IK_FK"] = 1.0
        bpy.ops.object.mode_set(mode="POSE")
        ang = spec["rig"]["comparison_pose"]["upper_arm_fk_rotation_y_deg"]
        for s, sx in (("L", 1), ("R", -1)):
            pb = rig.pose.bones.get(f"upper_arm_fk.{s}")
            if pb is None:
                continue
            head_w = rig.matrix_world @ pb.head
            Rm = Matrix.Translation(head_w) @ Matrix.Rotation(math.radians(sx * ang), 4, "Y") @ Matrix.Translation(-head_w)
            pb.matrix = rig.matrix_world.inverted() @ Rm @ rig.matrix_world @ pb.matrix
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()
        groups = {"hair": hair, "hoodie": list(hoodie.values()), "trousers": trousers, "shoes": shoes}
        for f in spec["fur"]:
            G.add_fur(f["name"], groups[f["on"]], subs["fur"], M[f["material"]], f["density"] * a.fur_scale,
                      tuple(f["length_m"]), f["radius_m"], spread=f["spread"], gravity=f["gravity"], seed=sum(map(ord, f["name"])))
        C["ps_role"] = "evaluation"
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, f"{cid}_compare.blend"))
    report["landmarks_rest"] = {k: [round(c, 4) for c in v.location] for k, v in empties.items()}
    report["objects"] = sorted(o.name for o in C.all_objects)
    report["total_s"] = round(time.time() - t0, 1)
    json.dump(report, open(os.path.join(out, "build_report.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k not in ("objects", "landmarks_rest")}, indent=1))


main()
