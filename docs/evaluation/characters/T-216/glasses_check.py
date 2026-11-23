"""T-216: glasses seating on a built master (rigid, no Surface Deform; clearance to the skin and the eyes).

    blender -b --factory-startup -P docs/evaluation/characters/T-216/glasses_check.py -- <master.blend> [...]

Per master: the glasses objects' modifiers (only ARMATURE or none allowed: rigid to the head bone), parent, and the
minimum distance from the frame and lens vertices to the skin and the eyeballs (rest pose, BVH nearest)."""
import json
import sys

import bpy
from mathutils.bvhtree import BVHTree

out = {}
for path in sys.argv[sys.argv.index("--") + 1:]:
    bpy.ops.wm.open_mainfile(filepath=path)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()

    def bvh(name):
        o = bpy.data.objects[name].evaluated_get(dg)
        m = o.to_mesh()
        t = BVHTree.FromPolygons([o.matrix_world @ v.co for v in m.vertices], [p.vertices[:] for p in m.polygons])
        o.to_mesh_clear()
        return t
    trees = {"skin": bvh("body_skin"), "eye.L": bvh("eye.L"), "eye.R": bvh("eye.R")}
    rec = {}
    for o in bpy.data.objects:
        if not o.name.startswith("glasses") or o.type != "MESH":
            continue
        e = o.evaluated_get(dg)
        m = e.to_mesh()
        pts = [e.matrix_world @ v.co for v in m.vertices]
        e.to_mesh_clear()
        rec[o.name] = {"modifiers": [md.type for md in o.modifiers], "parent": o.parent.name if o.parent else None,
                       "parent_type": o.parent_type,
                       "rigid": all(md.type == "ARMATURE" for md in o.modifiers),
                       **{f"min_to_{k}_mm": round(min(t.find_nearest(p)[3] for p in pts) * 1000, 3) for k, t in trees.items()}}
    out[path] = rec
print("GLASSES " + json.dumps(out))
