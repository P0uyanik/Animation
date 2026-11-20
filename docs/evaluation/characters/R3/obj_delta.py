"""R3 step 4: per-object world-space vertex displacement between two masters (headless Blender, read-only).

    blender -b --factory-startup -P docs/evaluation/characters/R3/obj_delta.py -- <a_master.blend> <b_master.blend>

Prints one line "DELTA {object: [max_mm, p95_mm] | ["vcount", n_a, n_b]}" for every mesh present in both whose
vertices moved (same vertex count: per-vertex distance; different count: the two counts). Complements the strict
hashes of chain_build.sh with a size."""
import bpy, sys, json, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
def load(p):
    bpy.ops.wm.open_mainfile(filepath=p)
    out = {}
    for o in bpy.data.objects:
        if o.type == "MESH":
            co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co)
            mw = np.array(o.matrix_world); p3 = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
            out[o.name] = p3
    return out
A, B = load(a[0]), load(a[1])
res = {}
for k in sorted(set(A) & set(B)):
    if len(A[k]) == len(B[k]) and len(A[k]):
        d = np.linalg.norm(A[k] - B[k], axis=1)
        if d.max() > 0: res[k] = [round(float(d.max()) * 1000, 3), round(float(np.percentile(d, 95)) * 1000, 3)]
    elif k in A and k in B:
        res[k] = ["vcount", len(A[k]), len(B[k])]
print("DELTA " + json.dumps(res))
