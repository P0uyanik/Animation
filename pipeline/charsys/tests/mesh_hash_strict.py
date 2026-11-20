"""T-158: strict per-object geometry hash of a master, for the repeated-build check (test_determinism.py --strict).

    blender -b --factory-startup -P pipeline/charsys/tests/mesh_hash_strict.py -- <master.blend> <out.json>

Per mesh: vertex coordinates of the basis and of every shape key, rounded to 1e-7 m, sorted (vertex order
independent), hashed. Finer than fingerprint_v2 (0.01 mm, no shape-key coordinates): the T-137/T-158 run-to-run
drift (~1e-8 m on ears and lids) only shows here. Read-only. Same measure as docs/evaluation/characters/T-109/mesh_hash.py."""
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
        co = co[np.lexsort(co.T[::-1])]
        h.update(name.encode())
        h.update(co.tobytes())
    out[o.name] = {"vertices": len(me.vertices), "keys": len(sets) - 1, "sha256": h.hexdigest()[:16]}
with open(a[1], "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, sort_keys=True)
