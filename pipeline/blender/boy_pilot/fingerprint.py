"""Geometry fingerprint of a pilot master .blend, for comparing builds made with different Blender installations.

    blender -b --factory-startup -P pipeline/blender/boy_pilot/fingerprint.py -- <master.blend> <out.json>

Per mesh object: vertex and face counts, bounding box, vertex-order-independent hash of the coordinates rounded to
0.01 mm, vertex-group names, shape-key names, materials. Plus armature bone counts and the Blender version. Read-only."""
import hashlib
import json
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
src, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
bpy.ops.wm.open_mainfile(filepath=src)
fp = {"blender": bpy.app.version_string, "file": os.path.basename(src), "objects": {}}
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.name.startswith("WGT-"):
        continue
    if o.type == "MESH":
        n = len(o.data.vertices)
        co = np.empty(n * 3, np.float64)
        o.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        q = np.round(co * 1e5).astype(np.int64)  # 0.01 mm grid
        q = q[np.lexsort(q.T[::-1])]
        fp["objects"][o.name] = {
            "type": "MESH", "vertices": n, "faces": len(o.data.polygons),
            "bbox": [np.round(co.min(0), 4).tolist(), np.round(co.max(0), 4).tolist()] if n else None,
            "coords_hash": hashlib.sha256(q.tobytes()).hexdigest()[:16],  # exact match test (sensitive to float noise)
            "centroid": np.round(co.mean(0), 6).tolist() if n else None,       # numeric comparison
            "rms_radius": round(float(np.sqrt(((co - co.mean(0)) ** 2).sum(1).mean())), 6) if n else None,
            "vertex_groups": sorted(g.name for g in o.vertex_groups),
            "shape_keys": [k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],
            "materials": [m.name if m else None for m in o.data.materials],
        }
    elif o.type == "ARMATURE":
        fp["objects"][o.name] = {"type": "ARMATURE", "bones": len(o.data.bones),
                                 "deform_bones": sum(1 for b in o.data.bones if b.use_deform)}
json.dump(fp, open(out, "w"), indent=1)
print(f"[fingerprint] {len(fp['objects'])} objects -> {out}")
