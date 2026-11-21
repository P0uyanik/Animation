"""R3 step 4: per-object surface displacement between two masters (headless Blender, read-only).

    blender -b --factory-startup -P docs/evaluation/characters/R3/obj_delta.py -- <a_master.blend> <b_master.blend>

Prints "DELTA {object: [max_mm, p95_mm, n_a, n_b]}" for every mesh present in both masters whose vertices differ.
Order-independent: per vertex, the distance to the nearest vertex of the other build (both directions, world space,
mathutils.kdtree), so re-ordered or re-meshed objects are measured by shape, not by index. Complements the strict
hashes of chain_build.sh with a size."""
import json
import sys

import bpy
import numpy as np
from mathutils import Vector, kdtree

a = sys.argv[sys.argv.index("--") + 1:]


def load(p):
    bpy.ops.wm.open_mainfile(filepath=p)
    out = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and len(o.data.vertices):
            co = np.empty(len(o.data.vertices) * 3)
            o.data.vertices.foreach_get("co", co)
            mw = np.array(o.matrix_world)
            out[o.name] = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    return out


def near(src, dst):
    t = kdtree.KDTree(len(dst))
    for i, v in enumerate(dst):
        t.insert(Vector(v), i)
    t.balance()
    return np.array([t.find(Vector(v))[2] for v in src])


A, B = load(a[0]), load(a[1])
res = {}
for k in sorted(set(A) & set(B)):
    if len(A[k]) == len(B[k]) and np.array_equal(A[k], B[k]):
        continue
    d = np.concatenate([near(A[k], B[k]), near(B[k], A[k])])
    if d.max() > 0:
        res[k] = [round(float(d.max()) * 1000, 3), round(float(np.percentile(d, 95)) * 1000, 3), len(A[k]), len(B[k])]
print("DELTA " + json.dumps(res))
