"""Uses a published character version in an episode shot without copying or modifying the master (headless Blender).

    blender -b --factory-startup -P pipeline/charsys/episode.py -- --version-dir assets/characters/boy_yellow_hoodie/versions/1.0.0 \
        --out episodes/<episode>/shots/<shot>.blend [--pose pose.json] [--face '{"face_Smile": 0.6}'] [--episode <id>]

How it isolates the master:
  * the character's root collection is LINKED from the version's master .blend (relative path), never appended;
  * a library override hierarchy is created; only the rig is made editable (pose, facial controls face_*), every
    mesh, material and the rig's rest data stay linked and read-only, so episode edits are stored in the shot file;
  * the shot records the version and the master's sha256; tests check the master is byte-identical afterwards.
pose.json: {"<pose bone>": [w, x, y, z] quaternion, ...}."""
import argparse
import hashlib
import json
import os
import sys

import bpy


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def link_character(version_dir, scene=None):
    """Links the character of a store version into the current file. Returns (override root collection, rig, info)."""
    scene = scene or bpy.context.scene
    man = json.load(open(os.path.join(version_dir, "manifest.json")))
    cid = man["character_id"]
    master = os.path.join(os.path.abspath(version_dir), f"{cid}_master.blend")
    if sha256_file(master) != man["files"][f"{cid}_master.blend"]["sha256"]:
        raise RuntimeError("master does not match its manifest; refusing to use it")
    ov, rig = link_master(master, cid, scene)
    info = {"character_id": cid, "version": man["version"], "master_sha256": man["files"][f"{cid}_master.blend"]["sha256"],
            "spec_sha256": man["spec_sha256"]}
    scene["ps_cast"] = json.dumps([info])
    return ov, rig, info


def link_master(master, cid, scene=None):
    """Links collection `cid` of a master .blend (never appended or modified) and makes a library-override hierarchy
    in which only the rig is editable. Returns (override root collection, rig). Used for published versions
    (link_character, manifest-checked) and for unpublished builds in shots (the caller records the master's hash)."""
    scene = scene or bpy.context.scene
    with bpy.data.libraries.load(master, link=True, relative=True) as (src, dst):
        if cid not in src.collections:
            raise RuntimeError(f"collection {cid} not in {master}")
        dst.collections = [cid]
    linked = dst.collections[0]
    scene.collection.children.link(linked)
    ov = linked.override_hierarchy_create(scene, bpy.context.view_layer, do_fully_editable=False)
    for ch in list(scene.collection.children):  # keep only the override instance in the scene
        if ch.library is not None:
            scene.collection.children.unlink(ch)
    rig = next(o for o in ov.all_objects if o.type == "ARMATURE")
    rig.override_library.is_system_override = False  # the rig is the episode's editable handle
    return ov, rig


def apply_pose(rig, pose=None, face=None, fk=True):
    """Poses FK controls (quaternions) and sets facial controls. fk=True switches Rigify limbs to FK (IK_FK = 1),
    otherwise the FK controls would be ignored by the IK chains."""
    if fk and pose:
        for pb in rig.pose.bones:
            if "IK_FK" in pb.keys():
                pb["IK_FK"] = 1.0
    for bone, q in (pose or {}).items():
        pb = rig.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = q
    for prop, v in (face or {}).items():
        if prop not in rig.keys():
            raise KeyError(f"rig has no facial control {prop}")
        rig[prop] = float(v)
    rig.update_tag()  # ID-property edits are not tagged automatically; drivers on the shape keys read them
    bpy.context.view_layer.update()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--version-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pose", default="")
    ap.add_argument("--face", default="")
    ap.add_argument("--episode", default="")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    if os.path.commonpath([out, os.path.abspath(a.version_dir)]) == os.path.abspath(a.version_dir):
        raise SystemExit("shot files must not be written into the asset store")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ov, rig, info = link_character(a.version_dir)
    apply_pose(rig, json.load(open(a.pose)) if a.pose else None, json.loads(a.face) if a.face else None)
    bpy.context.scene["ps_episode"] = a.episode
    bpy.ops.wm.save_as_mainfile(filepath=out, relative_remap=True)
    print("[episode]", json.dumps({"shot": out, **info}))


if __name__ == "__main__":
    main()
