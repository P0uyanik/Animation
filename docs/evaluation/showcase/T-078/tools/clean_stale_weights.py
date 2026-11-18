"""T-078 evaluation post-step (no shared system changed).

    blender -b --factory-startup -P docs/evaluation/showcase/T-078/tools/clean_stale_weights.py -- <in.blend> <out.blend>

Hair v3 (groom/2, via T-070's build_candidate.py) builds `scalp_cap` from the head mesh with bmesh, so the cap keeps
the head's vertex-weight entries. On a generic-path head (`body_skin`, many groups) these entries point at group
indices the cap object does not have (it gets only the head-bone group from groom_hybrid.bind), and
export_engine.eye_pivots fails with IndexError. This drops weight entries whose group index does not exist on the
object; valid entries (the bind) are kept unchanged. Prints what it removed."""
import sys

import bmesh
import bpy

a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    n = len(o.vertex_groups)
    if not any(g.group >= n for v in o.data.vertices for g in v.groups):
        continue
    bm = bmesh.new()
    bm.from_mesh(o.data)
    dl = bm.verts.layers.deform.active
    removed = 0
    for v in bm.verts:
        dv = v[dl]
        for k in [k for k in dv.keys() if k >= n]:
            del dv[k]
            removed += 1
    bm.to_mesh(o.data)
    bm.free()
    left = sum(1 for v in o.data.vertices if any(g.weight > 0 for g in v.groups))
    print(f"CLEANED {o.name}: {removed} stale entries removed, {n} group(s), {left}/{len(o.data.vertices)} verts weighted")
bpy.ops.wm.save_as_mainfile(filepath=a[1], compress=True)
