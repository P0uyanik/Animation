import bpy, sys, json, numpy as np
a, b, out = sys.argv[sys.argv.index("--")+1:]
def co(p):
    bpy.ops.wm.open_mainfile(filepath=p)
    res = {}
    for o in bpy.data.objects:
        if o.type == "MESH":
            arr = np.empty(len(o.data.vertices)*3); o.data.vertices.foreach_get("co", arr); res[o.name] = arr.reshape(-1,3)
    return res
A = co(a); B = co(b)
r = {}
for n in sorted(A):
    if n in B and len(A[n]) == len(B[n]):
        if n != "hair_mass" and not np.array_equal(np.sort(A[n].round(9),axis=0), np.sort(B[n].round(9),axis=0)):
            r[n] = {"note": "coordinate multiset differs"}
        if n != "hair_mass": continue
        D = np.sqrt(((A[n][:, None, :] - B[n][None, :, :]) ** 2).sum(-1))
        d = np.maximum(D.min(1), 0)  # stored vertex -> nearest rebuilt vertex
        d2 = D.min(0)
        r[n + " (order-independent, nearest vertex)"] = {"max_stored_to_rebuilt_m": float(d.max()), "max_rebuilt_to_stored_m": float(d2.max()), "mean_m": float(d.mean())}
        if True:
            r[n] = {"verts": len(d), "max_m": float(d.max()), "p99_m": float(np.percentile(d,99)),
                    "moved_gt_1e-7_m": int((d>1e-7).sum()), "moved_gt_1e-5_m": int((d>1e-5).sum()), "moved_gt_1e-4_m": int((d>1e-4).sum())}
    elif n in B: r[n] = {"vertex_count": [len(A[n]), len(B[n])]}
json.dump(r, open(out,"w"), indent=1); print("RESULT", r)
