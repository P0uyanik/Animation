"""Character geometry fingerprint, format 2 (T-038), shared by the build-determinism test and tools/check_all.py.

    blender -b --factory-startup -P pipeline/charsys/fingerprint_v2.py -- <master.blend> <out.json> [--grid-m <metres>]

Per mesh object: vertex and face counts, bounding box, vertex-order-independent hash of the coordinates quantized to
a grid (default 0.01 mm, the same precision as the frozen legacy tool), vertex-group names, shape-key names,
materials. Plus armature bone counts and the Blender version. Read-only.

Differences from the frozen pipeline/blender/boy_pilot/fingerprint.py (which stays the tool for the v6 baseline
comparison in verify_charsys and must not be edited):
  * the output carries "format" and "coordinate_grid_m", so fingerprints made at different precisions can never
    be compared by mistake;
  * quantization is explicit round-half-away-from-zero instead of NumPy's round-half-to-even, and the hashed bytes
    are forced to little-endian int64, so the hash is canonical across platforms;
  * --grid-m selects a coarser grid (at most 1 mm). The determinism test compares builds at BOTH 0.01 mm and
    0.1 mm and requires both to match: 0.01 mm keeps the legacy precision, the 0.1 mm pass is reported separately
    so that a 0.01 mm mismatch caused only by threaded geometry code landing either side of a rounding boundary
    can be told apart from a real geometry change. The coarser grid never replaces the 0.01 mm requirement.
"""
import hashlib
import json
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
src, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
grid_arg = argv.index("--grid-m") + 1 if "--grid-m" in argv else None
GRID_M = float(argv[grid_arg]) if grid_arg is not None else 1e-5
if not 0.0 < GRID_M <= 1e-3:
    raise SystemExit("--grid-m must be in (0, 0.001]")
bpy.ops.wm.open_mainfile(filepath=src)
fp = {"format": "character-geometry-fingerprint/2", "coordinate_grid_m": GRID_M,
      "blender": bpy.app.version_string, "file": os.path.basename(src), "objects": {}}
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.name.startswith("WGT-"):
        continue
    if o.type == "MESH":
        n = len(o.data.vertices)
        co = np.empty(n * 3, np.float64)
        o.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        # Explicit half-away-from-zero quantization avoids NumPy's platform-
        # dependent tie handling and keeps the serialized bytes canonical.
        scaled = co / GRID_M
        q = (np.sign(scaled) * np.floor(np.abs(scaled) + 0.5)).astype(np.int64)
        q = q[np.lexsort(q.T[::-1])]
        fp["objects"][o.name] = {
            "type": "MESH", "vertices": n, "faces": len(o.data.polygons),
            "bbox": [np.round(co.min(0), 4).tolist(), np.round(co.max(0), 4).tolist()] if n else None,
            "coords_hash": hashlib.sha256(q.astype("<i8", copy=False).tobytes()).hexdigest()[:16],
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
print(f"[fingerprint_v2] {len(fp['objects'])} objects -> {out}")
