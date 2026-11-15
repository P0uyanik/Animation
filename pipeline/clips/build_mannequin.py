"""Builds the neutral authoring mannequin for body animation clips (headless Blender).

    blender -b --factory-startup -P pipeline/clips/build_mannequin.py -- --out <dir>

1. Body and Rigify rig from pipeline/clips/mannequin.json with the shared generators (body_generic/1, the shared
   Rigify fit profile): the same path every new character uses, with neutral proportions (not a character).
2. Converted to a plain FK deform rig for authoring: control and mechanism bones removed, deform-bone constraints
   and drivers cleared, each role bone parented to its SEMANTIC parent role from the rig profile's reference pose
   (helper deform bones keep their nearest deform ancestor), B-bones flattened (rigid segments, as in the engine).
   Clips are authored by rotating the role (DEF-) bones; export_clip.py turns the action into plush.clip/1.
3. Writes <out>/neutral_mannequin.blend (collection property ps_character_id, so export_engine.py exports it as an
   engine package for transfer tests) and mannequin_report.json. Read-only use of the shared charsys modules."""
import argparse
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
CHARSYS = os.path.join(HERE, "..", "charsys")
sys.path.insert(0, CHARSYS)
sys.path.insert(0, HERE)
import body_generic as BG  # noqa: E402
import body_v6 as B  # noqa: E402  (generic weight helpers only)
import geom as G  # noqa: E402
import retarget as RT  # noqa: E402


def expand_roles(profile):
    (el, er), (sl, sr) = profile["mirror"]["engine"], profile["mirror"]["source"]
    roles = {}
    for role, src in profile["roles"].items():
        roles[role] = src
        if role.endswith(el):
            roles[role[: -len(el)] + er] = src[: -len(sl)] + sr if src.endswith(sl) else src.replace(sl, sr)
    return roles


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    spec = json.load(open(os.path.join(HERE, "mannequin.json")))
    profile = json.load(open(os.path.join(CHARSYS, "rig_profiles", "humanoid_rigify.json")))
    ref = RT.reference_pose(profile["reference_pose"])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    C = bpy.data.collections.new(spec["id"])
    bpy.context.scene.collection.children.link(C)
    H = float(spec["body"]["height_m"])
    P = spec["body"]["params"]
    J = BG.joints(P, H)
    frames = BG.hand_frames(P, H, J)
    M = {"skin": G.material("M_mannequin", tuple(spec["skin_srgb"]), roughness=0.6)}
    parts = BG.build_body(C, M, P, H, J, frames)
    rig, rr = BG.rig_generic(C, "rig_" + spec["id"], parts, P, H, J, frames, spec["rig"]["weight_rules"], B,
                             spec["rig"].get("weight_smooth"))
    # ---- convert to a plain FK deform rig with the semantic role hierarchy
    roles = expand_roles(profile)
    src_of = {r: s for r, s in roles.items() if s in rig.data.bones and rig.data.bones[s].use_deform}
    sem_parent = {x["name"]: x["parent"] for x in ref}

    def deform_parent(b):
        p = b.parent
        while p is not None and not p.use_deform:
            p = p.parent
        return p.name if p else None
    new_parent = {b.name: deform_parent(b) for b in rig.data.bones if b.use_deform}
    role_of = {s: r for r, s in src_of.items()}
    for s, r in role_of.items():
        p = sem_parent.get(r)
        while p and p not in src_of:
            p = sem_parent.get(p)
        new_parent[s] = src_of[p] if p else None
    rig.animation_data_clear()
    for pb in rig.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    for name, parent in new_parent.items():
        e = eb[name]
        e.use_connect = False
        e.parent = eb[parent] if parent else None
        e.bbone_segments = 1
    for e in list(eb):
        if not e.use_deform:
            eb.remove(e)
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.custom_shape = None
    for k in list(rig.keys()):
        if k.startswith("rig_id") or k.startswith("rigify"):
            del rig[k]
    C["ps_character_id"] = spec["id"]
    C["ps_mannequin"] = json.dumps({"format": spec["format"], "version": spec["version"]})
    rig["ps_character_id"] = spec["id"]
    rig["ps_semantic_roles"] = json.dumps(src_of, sort_keys=True)
    bpy.context.scene.render.fps = 30
    path = os.path.join(out, f"{spec['id']}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    rep = {"blend": path, "blender": bpy.app.version_string, "rig": rr, "deform_bones": len(rig.data.bones),
           "role_bones": len(src_of), "roles": sorted(src_of), "parents": new_parent}
    json.dump(rep, open(os.path.join(out, "mannequin_report.json"), "w"), indent=1)
    print(f"[build_mannequin] {path}: {len(rig.data.bones)} deform bones, {len(src_of)} role bones")


main()
