"""T-109: per-object geometry hashes of a master (headless Blender; read-only). Used to show that face_generic/3
without the T-109 options builds the same geometry as before (vertex coordinates of every mesh and of every shape
key, rounded to 1e-7 m, and the vertex sets independent of order).

    blender -b --factory-startup -P docs/evaluation/characters/T-109/mesh_hash.py -- <master.blend> <out.json>"""
import hashlib
import json
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
out = {}
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type != "MESH":
        continue
    me = o.data
    sets = [("basis", me.vertices)] + ([(k.name, k.data) for k in me.shape_keys.key_blocks] if me.shape_keys else [])
    h = hashlib.sha256()
    for name, data in sets:
        co = np.empty(len(data) * 3)
        data.foreach_get("co", co)
        co = np.round(co.reshape(-1, 3), 7)
        co = co[np.lexsort(co.T[::-1])]  # vertex order independent
        h.update(name.encode())
        h.update(co.tobytes())
    out[o.name] = {"vertices": len(me.vertices), "keys": len(sets) - 1, "sha256": h.hexdigest()[:16]}
json.dump(out, open(a[1], "w"), indent=1, sort_keys=True)
