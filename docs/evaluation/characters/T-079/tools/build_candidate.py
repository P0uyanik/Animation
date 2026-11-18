"""T-044: build hair v3 (groom/2, pipeline/charsys/groom_hybrid.py) on a character master (headless Blender).

    blender -b --factory-startup -P docs/evaluation/characters/T-079/tools/build_candidate.py -- \
        --base <master.blend built by build_character.py from the character's published spec> \
        --candidate docs/evaluation/characters/T-079/candidates/<c>.hair_v3.json --out <dir>

The published spec files are not changed (pin bumps happen after owner approval). A candidate is the spec override a
pin bump would apply: {"character_spec", "head_object", "frame", "overrides": {"generators": {"groom": "groom/2"},
"hair": {...}, "materials": {"assignments": {...}}}}. The master's hair objects and hair chain bones are removed, the
candidate hair is built with groom_hybrid.build / bind (shared GN fibres from the material assignments) and the
result is saved as <out>/<id>_hairv3.blend with build.json (report, timings, counts)."""
import argparse
import json
import os
import resource
import sys
import time

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "charsys"))
import groom_hybrid as GH  # noqa: E402
from materials import builder as MATERIALS  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    cand = json.load(open(a.candidate))
    cspec = json.load(open(os.path.join(ROOT, cand["character_spec"])))
    ov = cand["overrides"]
    assert ov["generators"]["groom"] in GH.GENERATOR_VERSIONS
    cid = cspec["identity"]["id"]
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.base))
    t0 = time.time()
    rig = bpy.data.objects[f"rig_{cid}"]
    head = bpy.data.objects[cand["head_object"]]
    hair_coll = bpy.data.collections[f"{cid}.hair"]
    for o in [o for o in bpy.data.objects if o.name.startswith("hair_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    dyn_bones = [b.name for b in rig.data.bones if b.name.startswith(GH.G1.DYN_BONE_PREFIX)]
    if dyn_bones:
        bpy.context.view_layer.objects.active = rig
        rig.hide_set(False)
        bpy.ops.object.mode_set(mode="EDIT")
        for n in dyn_bones:
            rig.data.edit_bones.remove(rig.data.edit_bones[n])
        bpy.ops.object.mode_set(mode="OBJECT")
    if "ps_dynamics" in rig:
        del rig["ps_dynamics"]
    mats = dict(cspec.get("materials", {}).get("assignments") or {})
    mats.update((ov.get("materials") or {}).get("assignments") or {})
    cache = {}

    def material(slot):
        if slot not in cache:
            cache[slot] = MATERIALS.build_from_assignment(f"M_v3_{slot}", mats.get(slot) or mats["hair"])
        return cache[slot]

    def fibres(ob, slot, overrides):
        asg = mats.get(slot)
        if not asg:
            return None
        asg = dict(asg, overrides=MATERIALS.deep_merge(asg.get("overrides") or {}, overrides))
        return MATERIALS.add_fibres_from_assignment(ob, asg)

    dg = bpy.context.evaluated_depsgraph_get()
    head_bvh = BVHTree.FromObject(head, dg)
    hm = head.matrix_world

    def face_y(_head, x, z):
        loc, _, _, _ = head_bvh.ray_cast(hm.inverted() @ Vector((x, -5.0, z)), hm.inverted().to_3x3() @ Vector((0, 1, 0)))
        return (hm @ loc).y if loc is not None else -0.14

    hs = ov["hair"]
    t_build = time.time()
    objs, rep = GH.build(hair_coll, head, cand["frame"], hs, material, face_y, fibres)
    build_s = time.time() - t_build
    GH.bind(rig, objs, cspec["rig"]["head_bone"], cspec["rig"].get("chest_bone", cspec["rig"]["head_bone"]),
            hs.get("binding"))
    for o in list(bpy.data.objects):
        if o.name.startswith("hair_") and hair_coll not in o.users_collection:
            for uc in list(o.users_collection):
                uc.objects.unlink(o)
            hair_coll.objects.link(o)
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
    out = {"character": cid, "generator": GH.GENERATOR, "candidate": os.path.relpath(a.candidate, ROOT),
           "hair_build_s": round(build_s, 2), "total_s": round(time.time() - t0, 2), "hair_vertices": verts,
           "hair_faces": faces, "fibre_points": fibre_pts,
           "chain_bones": sum(1 for b in rig.data.bones if b.name.startswith(GH.G1.DYN_BONE_PREFIX)),
           "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), "report": rep}
    path = os.path.join(a.out, f"{cid}_hairv3.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    out["blend_mb"] = round(os.path.getsize(path) / 1e6, 2)
    json.dump(out, open(os.path.join(a.out, "build.json"), "w"), indent=1, default=str)
    print("HAIRV3", json.dumps({k: v for k, v in out.items() if k != "report"}), "keepout", rep.get("keepout"))


if __name__ == "__main__":
    main()
