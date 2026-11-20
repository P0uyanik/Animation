"""T-158: record the edge and face order of bmesh.ops.create_uvsphere once, as data for geom.uv_sphere.

    blender -b --factory-startup -P docs/evaluation/characters/T-158/record_uv_sphere_topology.py -- <out.json> SxR [SxR ...]

create_uvsphere returns the same vertices (same order) every run, but its faces and edges in a pointer-dependent
order and edge direction, which moves SUBSURF / bisect results by float ulps from run to run. geom.uv_sphere
replays one recorded natural run instead, so builds are repeatable and stay in the family of the published
masters (a sorted order does not: T-158 README). Read-only apart from <out.json>."""
import json
import sys

import bmesh

a = sys.argv[sys.argv.index("--") + 1:]
out = {"schema": "plush-studio.uv-sphere-topology/1",
       "source": "bmesh.ops.create_uvsphere(radius=1), one recorded run, Blender %s (T-158)" % __import__("bpy").app.version_string,
       "sizes": {}}
for key in a[1:]:
    s, r = (int(x) for x in key.split("x"))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=s, v_segments=r, radius=1.0)
    bm.verts.index_update()
    out["sizes"][key] = {"vertices": len(bm.verts),
                         "edges": [[v.index for v in e.verts] for e in bm.edges],
                         "faces": [[v.index for v in f.verts] for f in bm.faces]}
    bm.free()
with open(a[0], "w", encoding="utf-8") as f:
    json.dump(out, f, separators=(",", ":"), sort_keys=True)
    f.write("\n")
print("[record_uv_sphere_topology]", ", ".join(out["sizes"]), "->", a[0])
