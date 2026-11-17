"""T-049 hair study: swap a character's hair for one study approach (headless Blender; experiment only).

    blender -b --factory-startup -P pipeline/charsys/experiments/hair_study/study_build.py -- \
        --base <character master.blend> --study <specs/<char>_<A|B|C>.json> --out <dir>

Opens a master built by build_character.py (unchanged), removes its hair objects and hair chain bones, builds the
study hair with the SHARED groom/1 builder (groom.build / groom.bind, called as a library) plus the experiment
primitives of primitives.py (registered at runtime), optionally fuses the volume (approach B), adds the shared GN
fibres from the material presets, binds to the rig and saves <out>/<id>_study.blend + build.json
(timings, vertex/face counts, fibre points, peak memory). No shared file is modified."""
import argparse
import json
import os
import resource
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
sys.path.insert(0, HERE)
import groom as GROOM  # noqa: E402
from materials import builder as MATERIALS  # noqa: E402
import primitives as P  # noqa: E402


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--study", required=True)
    ap.add_argument("--out", required=True)
    return ap.parse_args(argv)


def main():
    a = parse()
    study = json.load(open(a.study))
    cspec = json.load(open(os.path.join(ROOT, study["character_spec"])))
    cid = cspec["identity"]["id"]
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.base))
    t0 = time.time()
    rig = bpy.data.objects[f"rig_{cid}"]
    head = bpy.data.objects[study["head_object"]]
    hair_coll = bpy.data.collections[f"{cid}.hair"]
    # remove the character's current hair and its chain bones
    old = [o for o in bpy.data.objects if o.name.startswith("hair_")]
    for o in old:
        bpy.data.objects.remove(o, do_unlink=True)
    dyn_bones = [b.name for b in rig.data.bones if b.name.startswith(GROOM.DYN_BONE_PREFIX)]
    if dyn_bones:
        bpy.context.view_layer.objects.active = rig
        rig.hide_set(False)
        bpy.ops.object.mode_set(mode="EDIT")
        for n in dyn_bones:
            rig.data.edit_bones.remove(rig.data.edit_bones[n])
        bpy.ops.object.mode_set(mode="OBJECT")
    if "ps_dynamics" in rig:
        del rig["ps_dynamics"]
    P.register()
    mats = dict(cspec.get("materials", {}).get("assignments") or {})
    mats.update(study.get("materials") or {})
    cache = {}

    def material(slot):
        if slot not in cache:
            cache[slot] = MATERIALS.build_from_assignment(f"M_study_{slot}", mats.get(slot) or mats["hair"])
        return cache[slot]

    def fibres(ob, slot, overrides):
        asg = mats.get(slot)
        if not asg:
            return None
        asg = dict(asg, overrides=MATERIALS.deep_merge(asg.get("overrides") or {}, overrides))
        return MATERIALS.add_fibres_from_assignment(ob, asg)

    dg = bpy.context.evaluated_depsgraph_get()
    from mathutils.bvhtree import BVHTree
    head_bvh = BVHTree.FromObject(head, dg)
    hm = head.matrix_world

    def face_y(_head, x, z):
        loc, _, _, _ = head_bvh.ray_cast(hm.inverted() @ Vector((x, -5.0, z)), hm.inverted().to_3x3() @ Vector((0, 1, 0)))
        return (hm @ loc).y if loc is not None else -0.14

    hs = study["hair"]
    fuse = study.get("fuse")
    C = hair_coll
    frame = study["frame"]
    t_build = time.time()
    objs, rep = GROOM.build(C, head, frame, hs, material, face_y, None if fuse else fibres)
    if fuse:
        keep_sep = set(fuse.get("exclude", []))
        to_fuse = [o for o in objs if o.name not in keep_sep and o.name.replace("hair_", "") not in keep_sep]
        rest = [o for o in objs if o not in to_fuse]
        fused = P.fuse(to_fuse, "hair_sculpt", C, float(fuse.get("voxel", 0.0022)), int(fuse.get("smooth", 4)))
        GROOM.HAIR_G().assign(fused, material("hair"))
        objs = [fused] + rest
        fb = hs.get("fibres") or {}
        nfo = 0
        for layer in fb.get("layers", [{}]):
            fo = fibres(fused, "hair", layer.get("overrides") or {})
            if fo is not None:
                fo.parent = fused
                fo.matrix_parent_inverse = fused.matrix_world.inverted()
                nfo += 1
        rep["fused"] = {"objects": len(to_fuse), "voxel_m": float(fuse.get("voxel", 0.0022)), "fibre_objects": nfo}
    build_s = time.time() - t_build
    GROOM.bind(rig, objs, cspec["rig"]["head_bone"], cspec["rig"].get("chest_bone", cspec["rig"]["head_bone"]),
               hs.get("binding"))
    for o in list(bpy.data.objects):
        if o.name.startswith("hair_") and C not in o.users_collection:
            for uc in list(o.users_collection):
                uc.objects.unlink(o)
            C.objects.link(o)
    dg = bpy.context.evaluated_depsgraph_get()
    verts = faces = fibre_pts = 0
    for o in bpy.data.objects:
        if not o.name.startswith("hair_"):
            continue
        e = o.evaluated_get(dg)
        if o.type == "MESH":
            verts += len(e.data.vertices)
            faces += len(e.data.polygons)
        elif o.type == "CURVES":
            fibre_pts += len(e.data.points)
    rep_out = {"character": cid, "approach": study["approach"], "label": study.get("label", ""),
               "hair_build_s": round(build_s, 2), "total_s": round(time.time() - t0, 2),
               "hair_vertices": verts, "hair_faces": faces, "fibre_points": fibre_pts,
               "chain_bones": sum(1 for b in rig.data.bones if b.name.startswith(GROOM.DYN_BONE_PREFIX)),
               "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1),
               "structures": rep.get("structures"), "fused": rep.get("fused"),
               "spec_lines": sum(1 for _ in open(a.study))}
    path = os.path.join(a.out, f"{cid}_study.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    rep_out["blend_mb"] = round(os.path.getsize(path) / 1e6, 2)
    json.dump(rep_out, open(os.path.join(a.out, "build.json"), "w"), indent=1, default=str)
    print("STUDY", json.dumps({k: v for k, v in rep_out.items() if k != "structures"}))


if __name__ == "__main__":
    main()
